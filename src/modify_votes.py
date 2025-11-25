import requests
import os
import json
import time
import pandas as pd
import sys
import os
import numpy as np
from datetime import date
import xml.etree.ElementTree as ET
from init_logger import my_logger

def get_voting_record(df):
    """
    Takes all votes, each line is an individual vote by a person.
    Aggregate by person to get how many times they voted with each party, absent, abstained, etc.
    Args:
        df [DataFrame]: DataFrame of all individual votes with columns including 'bioguideID', 'identifier', 'voteParty', 'voteCast', 'lis_member_id', etc.
    Returns:
        overall_df [DataFrame]: DataFrame aggregated by person with counts of how they voted.
    """
    all_votes = len(df.groupby('identifier'))
    house_vote_count = len(df[df['lis_member_id'].isna()].groupby('identifier'))
    senate_vote_count = all_votes - house_vote_count
    my_logger.info(f"{house_vote_count} house votes, {senate_vote_count} senate votes, for total of {all_votes} votes")

    total_people = len(df['bioguideID'].unique())
    house_people = len(df[df['lis_member_id'].isna()]['bioguideID'].unique())
    senate_people = len(df[df['lis_member_id'].notna()]['bioguideID'].unique())
    my_logger.info(f"{house_people} house reps, {senate_people} senators, for total of {total_people} people")

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
        index=['bioguideID', 'chamber'],
        columns='voted_with_party',
        values='votecount',
        aggfunc='sum',
        fill_value=0 # Fills NaN values with 0
    ).reset_index() # Resets the index to make person_id a regular column


    #get the count of votes each person has been in
    overall_df['vote_count'] =  overall_df[['Absent', 'Abstained', 'Both', 'Neither', 'with_D', 'with_R']].sum(axis=1)
    #Create the missing_records col to check for any uncaught missing voters
    overall_df['missing_records'] = np.where(overall_df['chamber'] == "house", house_vote_count, senate_vote_count)
    overall_df['missing_records'] = overall_df['missing_records'] - overall_df['vote_count']


    return overall_df



def check_missing_votes(df):
    """
    Will scan for missing records that we don't expect. Only add to the acceptable_missing_votes list if
    manually checked that someone died or something.

    If was successful, will drop the whole missing_records column because they won't actually be missing.
    Args:
        df [DataFrame]: DataFrame of aggregated voting records by person with 'missing_records' column.
    Returns:
        df [DataFrame]: Same DataFrame but with 'missing_records' column dropped if no unexpected missing votes.
    """

    acceptable_missing_votes = ["C001078", "G000551", "T000489", "G000590", "W000823", "F000484", "G000578", "P000622", "J000299", 
                                "H001103", "K000404", "M001219", "N000147", "P000610", "R000600", "V000137", "R000595"]

    missing_df = df[df['missing_records']!= 0]
    missing_filtered_df = missing_df[~missing_df['bioguideID'].isin(acceptable_missing_votes)]
    if len(missing_filtered_df) != 0:
        my_logger.warning(f"Some congressmen are missing voter information unexpectedly: {missing_filtered_df['bioguideID'].unique()}")
    else:
        df.drop('missing_records', axis=1, inplace=True)

    return df


def get_root(url):
    """Gets an XML from a given URL"""
    try:
        response = requests.get(url)
        xml_content = response.content  # The XML content as bytes
        root = ET.fromstring(xml_content)
        return root
    except requests.exceptions.ConnectionError as e:
        my_logger.error(f"Connection error: {e}")
    except requests.exceptions.HTTPError as e:
        my_logger.error(f"HTTP error: {e}")



def sen_id_to_bioguide_id():
    """
    Creates a mapping of senate_id to bioguide_id from senate XML data.
    Returns:
        sen_id_bioguide_id [dict]: Dictionary mapping senate_id to bioguide_id
    """
    xml_senate = "https://www.senate.gov/legislative/LIS_MEMBER/cvc_member_data.xml"
    senate_root = get_root(xml_senate)

    sen_id_bioguide_id = {}
    try:
        # Iterate through each <member> child of the <senator> list
        for member_element in senate_root.findall('senator'):
            # 1. Get the bioguideID
            bioguide_id = member_element.find('bioguideId').text
            senate_id = member_element.get('lis_member_id')
            
            # 3. Store the information in the dictionary
            sen_id_bioguide_id[senate_id] = bioguide_id
        my_logger.info("Success getting senate bioguide to senate_id dict")
        return sen_id_bioguide_id
    
    except ET.ParseError as e:
        my_logger.error(f"Error parsing XML: {e}")
        return None


def merge_house_and_senate(df1, df2):
    """
    Merges house voting record and senate voting record. Maps senate_id to bioguide_id to merge.
    Also accounts for some manual differences, will log a warning if there are missing bioguide_ids
    Creates new column, "chamber", which marks if they're in house or senate.
    
    Args:
        df1 [DataFrame]: House voting record DataFrame (from voting_records.json)
        df2 [DataFrame]: Senate voting record DataFrame (from voting_records_senate.json)
    Returns:
        df [DataFrame]: Merged DataFrame with bioguideID and chamber columns added.
    """

    senate_to_bioguide = sen_id_to_bioguide_id()
    df2['bioguideID'] = df2['lis_member_id'].map(senate_to_bioguide)
    #Merge the 2 dataframes together  
    df = pd.concat([df1, df2], ignore_index=True)

    df['bioguideID'] = np.where(df['lis_member_id'] == "S421", "V000137", df['bioguideID'])
    df['bioguideID'] = np.where(df['lis_member_id'] == "S350", "R000595", df['bioguideID'])
    # ['S350' is Marco Rubio (R000595), 'S421' is JD Vance (V000137)]
    if (len(df[df['bioguideID'].isna()] > 0)):
        my_logger.warning(f"There are some NA bioguides on the merged voting record: {df[df['bioguideID'].isna()]['lis_member_id'].unique()}")
    df['chamber'] = np.where(df['lis_member_id'].isna(), "house", "senate") 

    return df


def modify_votes(voting_records_json, voting_records_senate_json):
    """
    Takes the 2 voting record file paths and will save to vote_avg.json 
    1. Merge house and senate voting records on bioguideID, marks error if map fails
    2. Get aggregate voting records for each person
    3. Error check for missing votes, will report to the logger
    4. Export vote_avg.json
    
    Args: 
        voting_records_json [str]: File path to voting_records.json (House)
        voting_records_senate_json [str]: File path to voting_records_senate.json (Senate)
    """

    #Load in the JSON
    try: 
        df1 = pd.read_json(voting_records_json)
    except Exception as e:
        print("There is an issue with the voting_records.json. Quitting.")
        sys.exit()

    try: 
        df2 = pd.read_json(voting_records_senate_json)
    except Exception as e:
        print("There is an issue with the voting_records_senate.json. Quitting.")
        sys.exit()


    overall_df = merge_house_and_senate(df1, df2)
    overall_df = get_voting_record(overall_df)
    overall_df = check_missing_votes(overall_df)
    overall_df.drop('chamber', axis=1, inplace=True) #get rid of chamber now, don't need it for the merge

    vote_avg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_outputs", "vote_avg.json")
    print(f"Exporting {len(overall_df)} to vote_avg.json")
    overall_df.to_json(vote_avg_path, indent=2, orient='records')
    print(f"Created {vote_avg_path} from {voting_records_json} and {voting_records_senate_json}")

