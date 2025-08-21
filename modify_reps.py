import requests
import os
import json
import time
import pandas as pd
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
    df['tenure_all_time']  = df['duration'].rank(ascending=False, method='min').astype(int)
    df['tenure_all_time_party'] = df.groupby('partyName')['duration'].rank(ascending=False, method='min').astype(int)

    #tenure_current is just for current members, if they're not current members will be nan
    df['tenure_current'] = np.where(df['current_member']=="yes", df.groupby('current_member')['duration'].rank(ascending=False,method='min'), np.nan)
    df['tenure_current_party'] = np.where(df['current_member']=="yes", df.groupby(['current_member','partyName'])['duration'].rank(ascending=False,method='min'), np.nan)

    df['tenure_current'] = df['tenure_current'].astype(pd.Int64Dtype())
    df['tenure_current_party'] = df['tenure_current_party'].astype(pd.Int64Dtype())

    df['party_all_time_count'] = df.groupby('partyName')['bioguideID'].transform('count')
    df['party_current_count'] = df.groupby(['partyName','current_member'])['bioguideID'].transform('count')




    return df

def only_current(df):
    df = df[df['current_member']=="yes"]
    return df

def normalize_name(df):
    df['name'] = df['name'].str.split(', ').str[::-1].str.join(' ')
    return df

####################################################################################################


def modify_reps(input_json_f):
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
        
    df = update_endyear(df)
    df = add_tenure(df)
    df = normalize_name(df)
    df = only_current(df)

    print(f"Exporting {len(df)} congressmen")

    df.to_json('congressmen_mod.json', indent=2, orient='records')

    print("Modified congressmen.json, wrote mods to congressmen_mod.json")

