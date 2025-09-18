import requests
import os
import json
import time
import pandas as pd
import sys
import os
import numpy as np
from datetime import date

def get_voting_record(df):
    num_of_votes = len(df.groupby('identifier'))

    #For each vote_identifier, get the count of how each party voted.
    #Group by identifier
    #
    #Create new table describing how dems and reps voted for that vote
    party_avg_df = df.groupby(['identifier', 'voteParty'])['voteCast'].agg(lambda x: x.mode()[0]).reset_index()
    party_mode_votes_wide = party_avg_df.pivot(
        index='identifier',
        columns='voteParty',
        values='voteCast'
    ).reset_index()

    # Rename columns for clarity
    party_mode_votes_wide.columns.name = None
    party_mode_votes_wide.rename(
        columns={'D': 'D_mode', 'R': 'R_mode'},
        inplace=True
    )

    # Bring the party mode votes into the individual votes table
    merged_df = pd.merge(df, party_mode_votes_wide, on='identifier', how='left')

    # Markers based on how they voted
    conditions = [
        # Voted with both parties (unlikely but possible)
        (merged_df['voteCast'] == merged_df['D_mode']) & (merged_df['voteCast'] == merged_df['R_mode']),
        # Voted with Democrats but not Republicans
        merged_df['voteCast'] == merged_df['D_mode'],
        # Voted with Republicans but not Democrats
        merged_df['voteCast'] == merged_df['R_mode'],
        #Absent
        merged_df['voteCast'] == "Not Voting",
        #Abstained
        merged_df['voteCast'] == "Present"
    ]

    choices = ['Both', 'with_D', 'with_R', 'Absent', 'Abstained']
    # Apply the conditions to create the new column
    merged_df['voted_with_party'] = np.select(conditions, choices, default='Neither')

    #To tabulate when creating the pivot table
    merged_df['votecount'] = 1

    #Create the new DF
    overall_df = pd.pivot_table(
        merged_df,
        index=['bioguideID'],
        columns='voted_with_party',
        values='votecount',
        aggfunc='sum',
        fill_value=0 # Fills NaN values with 0
    ).reset_index() # Resets the index to make person_id a regular column


    #get the count of votes each person has been in
    overall_df['vote_count'] = overall_df[['Absent', 'Abstained', 'Both', 'Neither', 'with_D', 'with_R']].sum(axis=1)
    #Create the missing_records col to check for any uncaught missing voters
    overall_df['missing_records'] = num_of_votes - overall_df['vote_count']


    return overall_df



def check_missing_votes(df):
    """
    Will scan for missing records that we don't expect. Only add to the acceptable_missing_votes list if
    manually checked that someone died or something.

    If was successful, will drop the whole missing_records column because they won't actually be missing.
    """

    acceptable_missing_votes = ["C001078", "G000551", "T000489", "G000590", "W000823", "F000484", "G000578", "P000622", "J000299", 
                                "H001103", "K000404", "M001219", "N000147", "P000610", "R000600"]

    missing_df = df[df['missing_records']!= 0]
    missing_filtered_df = missing_df[~missing_df['bioguideID'].isin(acceptable_missing_votes)]
    if len(missing_filtered_df) != 0:
        print(f"WARNING: Some congressmen are missing voter information unexpectedly.")
    else:
        df.drop('missing_records', axis=1, inplace=True)

    return df

def modify_votes(input_json_f):
    """
    Takes the congressmen.json file path and will save a congressmen_mod.json 
    
    Args: 
        input_json_f [str]: File path to congressmen.json

    """

        #Load in the JSON
    try: 
        df = pd.read_json(input_json_f)
    except Exception as e:
        print("There is an issue with the congressmen.json. Quitting.")
        sys.exit()
        
    overall_df = get_voting_record(df)
    overall_df = check_missing_votes(overall_df)

    print(f"Exporting {len(overall_df)} vote_avg.json")

    overall_df.to_json('vote_avg.json', indent=2, orient='records')

    print("Created vote_avg.json from voting_records.json")

