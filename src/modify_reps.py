import os
import json
import pandas as pd
import sys

sys.stdout.reconfigure(line_buffering=True)


current_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)

import src.add_bioguide as add_bioguide
import src.gen_committees as gen_committees
import sys
import os
from datetime import date
import numpy as np
from src.init_logger import my_logger



####################################################################################################



def update_endyear(df):
    """
    Converts endYear==NA to startYear+2 or +6 based on chamber
    This is because current members have no end year.
    """
    my_logger.debug(f"There are {len(df[df['endYear'].isna()])} NA endyears")

    df['current_member'] = np.where(df['endYear'].isna(), "yes", "no")
    my_logger.debug(f"Added yes to {len(df[df['current_member']=="yes"])} members")

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

    my_logger.info(f"After processing, there are {len(df[df['endYear'].isna()])} na endYears")
    return df

############################################

def add_tenure(df):
    """
    Calculate the tenure related fields:
        duration: endYear - startYear
        tenure_rank_all_time: Rank of tenure across all members, all time
        tenure_rank_all_time_party: Rank of tenure across all members, all time, within party
        tenure_rank_current: Rank of tenure across current members only, within chamber
        tenure_rank_current_party: Rank of tenure across current members only, within chamber and party
        party_all_time_count: Count of all time members within party
        party_current_count: Count of current members within party and chamber
        tenure_rank_current_party_percentile: Percentile rank of tenure across current members only, within
            chamber and party

    """
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
    df['chamber_current_count'] = df.groupby(['chamber', 'current_member'])['bioguideID'].transform('count')

    df['tenure_rank_current'] = df['tenure_rank_current'].astype(pd.Int64Dtype())

    df['tenure_rank_current_percentile'] = np.where(df['current_member']=="yes", df.groupby(['current_member','chamber'])['duration'].rank(ascending=True,method='max'), np.nan)
    df['tenure_rank_current_percentile'] = round(df['tenure_rank_current_percentile']/df['chamber_current_count']*100).astype(pd.Int64Dtype())


    return df

############################################

def only_current(df):
    """Filter to only current members"""
    df = df[df['current_member']=="yes"]
    return df

############################################

def normalize_name(df):
    """Normalize the name format from 'Last, First' to 'First Last'"""
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

    DEPRECATED FUNCTION
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
    Also get rank of absentia, abstention (non-party specific)

    with_party_count is the raw count of number of times they've voted with their party
    with_party_percent is the percent of their votes that they've voted with the party, excluding absentia
    with_party_percentile is for the percent bar. It's scaled out of 100 what their voting percentage rank is among 
        their peers, repeated for ties
    """

    #Then want to rank them based on their with_party_count / vote_count
    #vote_count = BOTH + NEITHER + WITH_D + WITH_R + ABSENT + ABSTAIN
    #removing BOTH and NEITHER (bipartisan consensus) from the denominator
    merged_df['with_D_percent'] = (merged_df['with_D'] / (merged_df['vote_count'] - merged_df['Both'] - merged_df['Neither']))*100
    merged_df['with_R_percent'] = (merged_df['with_R'] / (merged_df['vote_count'] - merged_df['Both'] - merged_df['Neither']))*100
    merged_df['absent_percent'] = (merged_df['Absent'] / (merged_df['vote_count'] - merged_df['Both'] - merged_df['Neither']))*100
    merged_df['for_bar'] = (merged_df['with_R'] / (merged_df['with_R'] + merged_df['with_D']))*100
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


def get_absolute_stats(df, input_json_f):
    """
    Docstring for get_absolute_stats
    Get the absolute values for congress that doesn't need to be duplicated. i.e.:
    - number of members in each chamber
    - max tenure per chamber
    - max tenure per chamber per party
    - party all time count
    - party current count

    :param df: input df of reps that's about to be spit out into congressmen_mod.json

    Will spit out its own json file
    """

    #1: get pivot table for max tenure by house and party
    max_tenure_by_house = df.groupby(['chamber'])['bg_duration'].max()
    max_tenure_by_house = max_tenure_by_house.reset_index()
    max_tenure_by_house['dummy'] = 1

    df_pivot = max_tenure_by_house.pivot_table(
        index='dummy', # Use a dummy index since we want all data in one row
        columns=['chamber'],
        values='bg_duration'
    )

    df_pivot = df_pivot.reset_index(drop=True)
    #df_pivot.columns = ['_'.join(map(str, col)).replace(' ', '_') for col in df_pivot.columns]

    df_pivot.rename(columns=lambda x: x.replace('House of Representatives', 'max_tenure_H')
                                    .replace('Senate', 'max_tenure_S')
                                    .replace('_Democrat', '_D')
                                    .replace('_Republican', '_R')
                                    .replace('_Independent', '_I')
                                    .replace('0_', '', 1) # Remove the dummy index column name part
                                    , inplace=True)

    df_pivot = df_pivot.reset_index(drop=True)
    df_pivot = df_pivot.astype(int)


    #2: get table for counts of individuals by party
    current_count = df.groupby('partyName')['bioguideID'].nunique()

    current_count = current_count.reset_index()
    df_count_pivot = current_count.set_index('partyName').T # T transposes (swaps rows and columns)
    df_count_pivot.columns = [f"count_{col[0]}" for col in df_count_pivot.columns] # count_D, count_I, count_R
    df_count_pivot = df_count_pivot.reset_index(drop=True)


    #3: get table for average vote by party and chamber
    avg_vote = df.groupby(['chamber', 'partyName'])[['with_D_percent', 'with_R_percent', 'absent_percent']].mean()
    avg_vote = avg_vote.reset_index()
    avg_vote['dummy'] = 1

    avg_vote_pivot = avg_vote.pivot_table(
        index='dummy', # Use a dummy index since we want all data in one row
        columns=['chamber', 'partyName'],
        values=['with_D_percent', 'with_R_percent', 'absent_percent']
    )

    avg_vote_pivot = avg_vote_pivot.reset_index(drop=True)
    avg_vote_pivot.columns = ['_'.join(map(str, col)).replace(' ', '_') for col in avg_vote_pivot.columns]

    avg_vote_pivot.rename(columns=lambda x: x.replace('House_of_Representatives', 'avg_vote_H')
                                    .replace('Senate', 'avg_vote_S')
                                    .replace('_Democrat', '_D')
                                    .replace('_Republican', '_R')
                                    .replace('_Independent', '_I')
                                    .replace('with_D_percent', 'with_D')
                                    .replace('with_R_percent', 'with_R')
                                    .replace('0_', '', 1) # Remove the dummy index column name part
                                    , inplace=True)

    avg_vote_pivot = avg_vote_pivot.reset_index(drop=True)
  
    # 4. Merge the two single-row tables (using index)
    final_result = pd.concat([df_pivot, df_count_pivot, avg_vote_pivot], axis=1)

    #Final replacements
    final_result['H_members'] = len(df[df['chamber']=="House of Representatives"])
    final_result['S_members'] = len(df[df['chamber']=="Senate"])

    #final_result = final_result.T

    #now write to json file
    absolute_stats_path = os.path.join(os.path.dirname(input_json_f), 'absolute_stats.json')

    final_result.to_json(path_or_buf=absolute_stats_path, orient='records', indent=4)

    print(f"Wrote some absolute stats to {absolute_stats_path}")


def add_bioguide_tenure_ranks(modified_congressmen_json):
    df = pd.DataFrame(modified_congressmen_json)
    df['terms_start_date'] = df['terms'].str[0]
    df['terms_start_date'] = df['terms_start_date'].fillna(df['startYear'].astype(str)+"-01-03")
    df['terms_start_date'] = pd.to_datetime(df['terms_start_date'])
    df['terms_end_date'] = df['terms'].str[1]
    df['terms_end_date'] = df['terms_end_date'].fillna(df['endYear'].astype(str)+"-01-03")
    df['terms_end_date'] = pd.to_datetime(df['terms_end_date'])

    today = pd.Timestamp.now()
    effective_end_date = np.where(df['terms_end_date'] > today, today, df['terms_end_date'])
    df['bg_duration'] = (pd.to_datetime(effective_end_date) - df['terms_start_date']).dt.days

    df['bg_duration'] = df['bg_duration'].astype(int)
    df['bg_duration'] = df['bg_duration'] / 365
    df['bg_duration'] = df['bg_duration'].astype(int)


    #tenure_all_time is across everyone, and across all time
    df['bg_tenure_rank_all_time']  = df['bg_duration'].rank(ascending=False, method='min').astype(int)
    df['bg_tenure_rank_all_time_party'] = df.groupby('partyName')['bg_duration'].rank(ascending=False, method='min').astype(int)

    #tenure_current is just for current members, if they're not current members will be nan
    df['bg_tenure_rank_current'] = np.where(df['current_member']=="yes", df.groupby(['current_member', 'chamber'])['bg_duration'].rank(ascending=False,method='min'), np.nan)
    df['bg_tenure_rank_current_party'] = np.where(df['current_member']=="yes", df.groupby(['current_member', 'chamber','partyName'])['bg_duration'].rank(ascending=False,method='min'), np.nan)
    df['bg_tenure_rank_current_party'] = df['bg_tenure_rank_current_party'].astype(pd.Int64Dtype())

    df['bg_tenure_rank_current'] = df['bg_tenure_rank_current'].astype(pd.Int64Dtype())

    df['bg_tenure_rank_current_percentile'] = np.where(df['current_member']=="yes", df.groupby(['current_member','chamber'])['bg_duration'].rank(ascending=True,method='max'), np.nan)
    df['bg_tenure_rank_current_percentile'] = round(df['bg_tenure_rank_current_percentile']/df['chamber_current_count']*100).astype(pd.Int64Dtype())

    df['bg_endYear'] = df['terms_end_date'].dt.year.astype(int)
    df['bg_startYear'] = df['terms_start_date'].dt.year.astype(int)
    df.drop(columns=['terms_start_date', 'terms_end_date'], inplace=True)

    return df



####################################################################################################


def modify_reps(input_json_f, vote_f):
    """
    Takes the congressmen.json file path and will save a congressmen_mod.json 
    1. Updates endYear for current members
    2. Adds tenure related fields
    3. Normalizes name format for easy printing of card
    4. Filters to only current members
    5. Merges voting records and congressmen stats

    Then on the merged df:
    1. Replaces Democratic party name to Democrat *doesn't need to be done on merged df*
    2. Gets voter rank related fields
    3a. Pulls in committee assignments for senate and house
    3b. Merges in committee assignments to merged df


    Args: 
        input_json_f [str]: File path to congressmen.json

    """
    #Load in the JSON
    try: 
        df = pd.read_json(input_json_f)
    except Exception as e:
        print("There is an issue converting congressmen.json to df. Quitting.")
        sys.exit()

    try: 
        vote_df = pd.read_json(vote_f)
    except Exception as e:
        print("There is an issue converting voting_records.json to df. Quitting.")
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
    modified_congressmen_json_pre = add_bioguide.add_bioguide(con_json) #list of dicts python Obj


    tenure_df = add_bioguide_tenure_ranks(modified_congressmen_json_pre)
    get_absolute_stats(tenure_df, input_json_f)

    modified_congressmen_json = tenure_df.replace({np.nan: None}).to_dict(orient='records')
    ####Write to file
    congressmen_mod_json_path = os.path.join(os.path.dirname(input_json_f), 'congressmen_mod.json')
    with open(congressmen_mod_json_path, 'w') as json_file:
        json.dump(modified_congressmen_json, json_file, indent=4) # indent for pretty printing

    print(f"Modified congressmen.json with voting and committee info, wrote mods to {congressmen_mod_json_path}")

