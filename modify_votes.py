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

    #Add a column that marks if they voted with the party or against the party for that vote
    df['party_voteCast'] = df.groupby(['identifier', 'voteParty'])['voteCast'].transform(lambda x: x.mode()[0])
    #Mark them as either with party or against party
    df['voted_with_party'] = np.where((df['voteCast']==df['party_voteCast']), "with_party", "against_party")
    #Mark if they were absent, will vote "Not Voting"
    df['voted_with_party'] = np.where((df['voteCast']=="Not Voting"), "absent", df['voted_with_party'])
    #Mark if they abstained, they will vote "Present". Be sure to exclude when that's the party average.
    df['voted_with_party'] = np.where((df['voteCast']=="Present") & (df['party_voteCast']!="Present"), "abstain", df['voted_with_party'])
    df['votecount'] = 1

    #Create the new DF
    overall_df = pd.pivot_table(
        df,
        index=['bioguideID'],
        columns='voted_with_party',
        values='votecount',
        aggfunc='sum',
        fill_value=0 # Fills NaN values with 0
    ).reset_index() # Resets the index to make person_id a regular column

    overall_df['missing_records'] = num_of_votes - overall_df[['absent', 'abstain', 'against_party', 'with_party']].sum(axis=1)
    overall_df['vote_count'] = num_of_votes

    return overall_df


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

    print(f"Exporting {len(overall_df)} vote_avg.json")

    overall_df.to_json('vote_avg.json', indent=2, orient='records')

    print("Created vote_avg.json from voting_records.json")

