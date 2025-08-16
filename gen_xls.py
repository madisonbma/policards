"""
Script to take in a JSON of representatives and 
Output is master spreadsheet of raw data, can be loaded in for data analytics
"""

import pandas as pd
import io
import os


####################################################################################################

def json_to_df(file_name):
    """
    Loads input JSON to use as dataframe.
    Args: 
        file_name: Input file, should point to a JSON formatted file.
    Returns: 
        df: a pandas dataframe
    """
    return pd.read_json(file_name)


############################################




####################################################################################################

def gen_xls(file1, file2):
    df1 = json_to_df(file1)
    df2 = json_to_df(file2)

    #Merge the 2 congressmen and voting_records on bioguideID
    merged_df = pd.merge(
        df1,     # This is your left DataFrame (all rows kept)
        df2,     # This is your right DataFrame (info to be added)
        on='bioguideID',             # The common column to join on
        how='left'               # Type of merge: keep all rows from the left DataFrame
    )
    merged_df.to_csv('raw_data.csv', index=False)  
