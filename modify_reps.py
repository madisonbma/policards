import requests
import os
import json
import time
import pandas as pd
import add_bioguide
import gen_committees
import sys
import os
from datetime import date
import numpy as np


####################################################################################################

def mod_json(list_of_dict):
    """Modifies the input JSON in the following ways:
        - Pads the "NA"s for endYear
    """
    for rep in list_of_dict:
        #Pad the NAs for endYear
        if 'endYear' not in rep:
            if rep['chamber'].lower()=="Senate".lower():
                rep.update({'endYear':rep['startYear']+6}) #6 year terms for senate
            elif rep['chamber'].lower()=="House of Representatives".lower():
                rep.update({'endYear':rep['startYear']+2}) #2 year terms for house
    


############################################

def update_endyear(df):
    #print(f"There are {len(df[df['endYear'].isna()])} NA endyears")

    df['current_member'] = np.where(df['endYear'].isna(), "yes", "no")
    #print(f"Added yes to {len(df[df['current_member']=="yes"])} members")

    year = int(date.today().year)

    #Replace endYear of HOR to startyear+2
    df['endYear'] = np.where(
        (df['endYear'].isna()) & (df['chamber'] == 'House of Representatives'),
        year + 2 - (year - df['startYear'])%2,
        df['endYear']
    )
    #Replace endYear of Senate to startyear+6
    df['endYear'] = np.where(
        (df['endYear'].isna()) & (df['chamber'] == 'Senate'),
        year + 6 - (year - df['startYear'])%6,
        df['endYear']
    )

    df['endYear'] = df['endYear'].astype(int)

    print(f"After processing, there are {len(df[df['endYear'].isna()])} na endYears")
    return df

############################################

def add_tenure(df):
    df['duration'] = df['endYear'] - df['startYear']

    #tenure_all_time is across everyone, and across all time
    df['tenure_rank_all_time']  = df['duration'].rank(ascending=False, method='min').astype(int)
    df['tenure_rank_all_time_party'] = df.groupby('partyName')['duration'].rank(ascending=False, method='min').astype(int)

    #tenure_current is just for current members, if they're not current members will be nan
    df['tenure_rank_current'] = np.where(df['current_member']=="yes", df.groupby(['current_member', 'chamber'])['duration'].rank(ascending=False,method='min'), np.nan)
    df['tenure_rank_current_party'] = np.where(df['current_member']=="yes", df.groupby(['current_member', 'chamber','partyName'])['duration'].rank(ascending=False,method='min'), np.nan)
    df['tenure_rank_current_party'] = df['tenure_rank_current_party'].astype(pd.Int64Dtype())

    df['party_all_time_count'] = df.groupby('partyName')['bioguideID'].transform('count')
    df['party_current_count'] = df.groupby(['partyName', 'chamber', 'current_member'])['bioguideID'].transform('count')

    df['tenure_rank_current'] = df['tenure_rank_current'].astype(pd.Int64Dtype())

    df['tenure_rank_current_party_percentile'] = np.where(df['current_member']=="yes", df.groupby(['current_member','chamber','partyName'])['duration'].rank(ascending=True,method='max'), np.nan)
    df['tenure_rank_current_party_percentile'] = round(df['tenure_rank_current_party_percentile']/df['party_current_count']*100).astype(pd.Int64Dtype())


    return df

############################################

def only_current(df):
    df = df[df['current_member']=="yes"]
    return df

############################################

def normalize_name(df):
    df['name'] = df['name'].str.split(', ').str[::-1].str.join(' ')
    return df

############################################

#Merge voting records into the reps df
def merge_in_voting_records(rep_df, vote_df):
    """
    Takes the current rep df and merges with the voting df. Merges on bioguideID
    """
    merged_df = pd.merge(
        rep_df,     # This is your left DataFrame (all rows kept)
        vote_df,     # This is your right DataFrame (info to be added)
        on='bioguideID',             # The common column to join on
        how='left'               # Type of merge: keep all rows from the rep_df
    )
    merged_df['Absent'] = merged_df['Absent'].astype(pd.Int64Dtype())
    merged_df['Abstained'] = merged_df['Abstained'].astype(pd.Int64Dtype())
    merged_df['Both'] = merged_df['Both'].astype(pd.Int64Dtype())
    merged_df['Neither'] = merged_df['Neither'].astype(pd.Int64Dtype())
    merged_df['with_D'] = merged_df['with_D'].astype(pd.Int64Dtype())
    merged_df['with_R'] = merged_df['with_R'].astype(pd.Int64Dtype())
    merged_df['vote_count'] = merged_df['vote_count'].astype(pd.Int64Dtype())


    return merged_df

############################################

def replace_democratic(df):
    """Change Democratic party to Democrat"""
    df['partyName'] = df['partyName'].replace('Democratic', 'Democrat')
    return df

############################################

def get_voter_rank_0(merged_df):
    """
    On the merged df between reps and votes, sorted by party allegiance 
    get their rank of times voting with their party.
    #If they're independent, simply put if they voted with D or R more.
    Also get rank of absentia, abstention (non-party specific)

    with_party_count is the raw count of number of times they've voted with their party
    with_party_percent is the percent of their votes that they've voted with the party, excluding absentia
    with_party_rank is for the percent bar. It's scaled out of 100 what their voting percentage rank is among 
        their peers, repeated for ties
    """
    ###Only do this for House members, care about how they vote within a chamber.
    #reps_mask = np.logical_and(merged_df['partyName']=="Republican", merged_df['chamber']=="House of Representatives")
    #dems_mask = np.logical_and(merged_df['partyName']=="Democrat", merged_df['chamber']=="House of Representatives")
    reps_mask = merged_df['partyName']=="Republican"
    dems_mask = merged_df['partyName']=="Democrat"
    #ind_mask = merged_df['partyName']!='Democrat' & merged_df['partyName']!='Republican'

    #with_party_count == Raw count of times they voted with their party
    merged_df['with_party_count'] = np.where(reps_mask, merged_df['Both'] + merged_df['with_R'], np.nan)
    merged_df['with_party_count'] = np.where(dems_mask, merged_df['Both'] + merged_df['with_D'], merged_df['with_party_count'])
    merged_df['with_party_count'] = merged_df['with_party_count'].astype(pd.Int64Dtype())


    #Then want to rank them based on their with_party_count / vote_count
    merged_df['with_party_percent'] = merged_df['with_party_count'] / (merged_df['vote_count'] - merged_df['Absent'])
    #Rank them based on the percentage of the time they vote with their party
    #This one is for ranking by party, changed to ranking within the chamber
    #merged_df['with_party_rank'] = merged_df.groupby('partyName')['with_party_percent'].rank(ascending=True, method='max')
    merged_df['with_party_rank'] = merged_df.groupby('chamber')['with_party_percent'].rank(ascending=True, method='max')

    #convert rank to percentile
    senate_count = len(merged_df[merged_df['chamber']=="Senate"])
    house_count = len(merged_df[merged_df['chamber']=="House of Representatives"])


    #Same as above, changing to ranking within the chamber
    #merged_df['with_party_rank'] = round(merged_df['with_party_rank']/merged_df['party_current_count']*100).astype(pd.Int64Dtype())
    merged_df['with_party_rank'] = np.where(merged_df['chamber']=="Senate", 
                                            round(merged_df['with_party_rank']/senate_count*100), 
                                            round(merged_df['with_party_rank']/house_count*100)) 
    merged_df['with_party_rank'] = merged_df['with_party_rank'].astype(pd.Int64Dtype())
    merged_df['with_party_percent'] = round(merged_df['with_party_percent']*100).astype(pd.Int64Dtype())

    return merged_df



def get_voter_rank(merged_df):
    """
    On the merged df between reps and votes, sorted by party allegiance 
    get their rank of times voting with their party.
    #If they're independent, simply put if they voted with D or R more.
    Also get rank of absentia, abstention (non-party specific)

    with_party_count is the raw count of number of times they've voted with their party
    with_party_percent is the percent of their votes that they've voted with the party, excluding absentia
    with_party_percentile is for the percent bar. It's scaled out of 100 what their voting percentage rank is among 
        their peers, repeated for ties
    """

    #Then want to rank them based on their with_party_count / vote_count
    #removing BOTH and NEITHER (bipartisan consensus) from the denominator
    #removing ABSENT and ABSTAIN from the denominator since showing elsewhere
    merged_df['with_D_percent'] = (merged_df['with_D'] / (merged_df['with_D'] + merged_df['with_R']))*100
    merged_df['with_R_percent'] = (merged_df['with_R'] / (merged_df['with_D'] + merged_df['with_R']))*100
    merged_df['absent_percent'] = (merged_df['Absent'] / (merged_df['vote_count']))*100
    merged_df['neither_percent'] = (merged_df['Neither'] / (merged_df['vote_count'] - merged_df['Absent']))*100

    #with_party_count == Raw count of times they voted with their party
    merged_df['with_party_percent'] = np.where(merged_df['partyName']=="Republican", merged_df['with_R_percent'], np.nan)
    merged_df['with_party_percent'] = np.where(merged_df['partyName']=="Democrat", merged_df['with_D_percent'], merged_df['with_party_percent'])

    #Rank them
    merged_df['neither_rank'] = merged_df.groupby('chamber')['neither_percent'].rank(ascending=True, method='max')
    merged_df['absent_rank'] = merged_df.groupby('chamber')['absent_percent'].rank(ascending=True, method='max')
    merged_df['with_party_rank'] = merged_df.groupby('chamber')['with_party_percent'].rank(ascending=True, method='max')

    #convert rank to percentile
    senate_count = len(merged_df[merged_df['chamber']=="Senate"])
    house_count = len(merged_df[merged_df['chamber']=="House of Representatives"])


    #Same as above, changing to ranking within the chamber
    merged_df['with_party_percentile'] = np.where(merged_df['chamber']=="Senate", 
                                            round(merged_df['with_party_rank']/senate_count*100), 
                                            round(merged_df['with_party_rank']/house_count*100)) 
    merged_df['neither_percentile'] = np.where(merged_df['chamber']=="Senate", 
                                            round(merged_df['neither_rank']/senate_count*100), 
                                            round(merged_df['neither_rank']/house_count*100)) 
    merged_df['absent_percentile'] = np.where(merged_df['chamber']=="Senate", 
                                            round(merged_df['absent_rank']/senate_count*100), 
                                            round(merged_df['absent_rank']/house_count*100)) 
    
    #Convert all to Int64Dtype
    merged_df['with_D_percent'] = round(merged_df['with_D_percent']).astype(pd.Int64Dtype())
    merged_df['with_R_percent'] = round(merged_df['with_R_percent']).astype(pd.Int64Dtype())
    merged_df['absent_percent'] = round(merged_df['absent_percent']).astype(pd.Int64Dtype())
    merged_df['neither_percent'] = round(merged_df['neither_percent']).astype(pd.Int64Dtype())
    merged_df['with_party_percent'] = round(merged_df['with_party_percent']).astype(pd.Int64Dtype())
    merged_df['neither_rank'] = merged_df['neither_rank'].astype(pd.Int64Dtype())
    merged_df['absent_rank'] = merged_df['absent_rank'].astype(pd.Int64Dtype())
    merged_df['with_party_rank'] = merged_df['with_party_rank'].astype(pd.Int64Dtype())
    merged_df['with_party_percentile'] = merged_df['with_party_percentile'].astype(pd.Int64Dtype())
    merged_df['neither_percentile'] = merged_df['neither_percentile'].astype(pd.Int64Dtype())
    merged_df['absent_percentile'] = merged_df['absent_percentile'].astype(pd.Int64Dtype())


    return merged_df


def merge_in_comms(df, comms_dict):
    """Given the final dataframe and the comms_dict, add the committees in per bioguideID.
    If no committee found, add "None" instead.
    """
    df['committees'] = df['bioguideID'].map(comms_dict)

    return df
####################################################################################################


def modify_reps(input_json_f, vote_f):
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

    try: 
        vote_df = pd.read_json(vote_f)
    except Exception as e:
        print("There is an issue with the voting_records.json. Quitting.")
        sys.exit()
        
    df = update_endyear(df)
    df = add_tenure(df)
    df = normalize_name(df)
    df = only_current(df)
    df = merge_in_voting_records(df, vote_df)
    df = replace_democratic(df)

    #Functions you need to do on merged vote and reps:
    df = get_voter_rank(df)

    comm_dict = gen_committees.gen_committees()
    df = merge_in_comms(df, comm_dict)


    print(f"Exporting {len(df)} congressmen")

    con_json = df.to_json(indent=2, orient='records')
    print("Starting the add_bioguide")
    #Last, modify the JSON with add_bioguide.py
    modified_congressmen_json = add_bioguide.add_bioguide(con_json) #list of dicts python Obj
    with open('congressmen_mod.json', 'w') as json_file:
        json.dump(modified_congressmen_json, json_file, indent=4) # indent for pretty printing

    print("Modified congressmen.json, wrote mods to congressmen_mod.json")

