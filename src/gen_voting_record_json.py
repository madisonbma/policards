

# --- Phase 1: Web Scraping ---
import requests
import os
import json
import time
from datetime import date
import xml.etree.ElementTree as ET
import sys

current_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)

from src.init_logger import my_logger

# --- Configuration ---
# 1. Try to load from the private config repo
try:
    # Get path to parent directory, then into the private repo folder
    # Assumes structure: 
    # ./public_repo/script.py
    # ./private_config_repo/config.py
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    config_path = os.path.join(parent_dir, "politician_pages_assets")
    print(f"adding {config_path} to path")
    
    sys.path.insert(0, config_path)
    from permissions import CONGRESS_API_KEY
    print("Loaded CONGRESS_API_KEY from config.py")

# 2. Fallback to environment variables if file/repo is missing
except (ImportError, ModuleNotFoundError):
    CONGRESS_API_KEY = os.getenv("FEC_API_KEY")
    
    if not CONGRESS_API_KEY:
        print("Error: Neither config.py nor environment variables found.")
    else:
        print("Loaded CONGRESS_API_KEY from environment variables")

# Finally, remove the path to keep the environment clean
finally:
    if 'config_path' in locals() and config_path in sys.path:
        sys.path.remove(config_path)

BASE_URL = "https://api.congress.gov/v3/"
HEADERS = {
    "Accept": "application/json"
}
RATE_LIMIT_DELAY_SECONDS = 0.2 



def get_house_vote_members(vote_number, congress=119, session=1, limit=250, offset=0):
    """
    Fetches the voting details for all members on a specific House roll call vote. No pagination required

    Args:
        congress (int or str): The Congress number (e.g., 119).
        session (int or str): The session number (e.g., 1, 2).
        vote_number (int or str): The unique roll call vote number for that session.
        limit (int): Number of results to return per page (max 250).
        offset (int): Starting record number for pagination.

    Returns:
        list: A list of dictionaries, where each dictionary represents a member's
              vote on this specific roll call, or an empty list if an error occurs.
              This list will contain the individual member vote objects.
    """
    endpoint = f"house-vote/{congress}/{session}/{vote_number}/members"
    all_member_votes = []
    current_offset = offset

    params = {
        "api_key": CONGRESS_API_KEY,
        "format": "json",
        "limit": limit,
        "offset": current_offset
    }

    my_logger.info(f"Requesting members for vote: Congress {congress}, Session {session}, Vote #{vote_number}")

    try:
        full_url = f"{BASE_URL}{endpoint}"
        my_logger.info(f"  - Querying: {full_url} with offset={params['offset']}")
        response = requests.get(full_url, headers=HEADERS, params=params)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

        data = response.json()

        # Access the 'results' list nested under 'houseRollCallVoteMemberVotes'
        member_votes_container = data.get('houseRollCallVoteMemberVotes')
        member_votes_on_page = []

        if isinstance(member_votes_container, dict):
            member_votes_on_page = member_votes_container.get('results', [])

        if not member_votes_on_page:
            my_logger.info("  - No more member votes found for this roll call or 'results' key missing/empty.")

        all_member_votes.extend(member_votes_on_page)
        my_logger.info(f"  - Fetched {len(member_votes_on_page)} member votes. Total: {len(all_member_votes)}")

    except requests.exceptions.HTTPError as e:
        my_logger.error(f"HTTP Error for vote members: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 404:
            my_logger.error("  - Vote not found or invalid congress/session/voteNumber combination.")
    except requests.exceptions.ConnectionError as e:
        my_logger.error(f"Connection Error for vote members: {e}")
    except requests.exceptions.Timeout as e:
        my_logger.error(f"Timeout Error for vote members: {e}")
    except requests.exceptions.RequestException as e:
        my_logger.error(f"An unexpected error occurred for vote members: {e}")
    except json.JSONDecodeError as e:
        my_logger.error(f"Error decoding JSON response for vote members: {e}")
    except Exception as e:
        my_logger.error(f"An unhandled error occurred for vote members: {e}")

    return data.get('houseRollCallVoteMemberVotes')


def get_voting_record(old_votes, congress, session, max_records=1000, start_vote=1):
    """
    This will query house voting records up to max_records. 

    Args: 
        old_votes (loaded JSON): votes already done
        max_records (int): Max number of measures to get voting records of, defaults to 1000 for now but will change once working

    """
    full_voting_record = old_votes
    i = start_vote
    max = max_records + start_vote
    my_logger.info(f"Starting from vote {i} for house pull")
    while i < max:
        try: 
            vote_record_i = get_house_vote_members(i, congress=congress, session=session)
            ###Postprocesses the vote_record_test JSON to flatten the "results" column
            parent_fields = {
                'congress': vote_record_i.get('congress'),
                'identifier': vote_record_i.get('identifier'),
                'result': vote_record_i.get('result'),
                #'rollCallNumber': vote_record_i.get('rollCallNumber'),
                #'sessionNumber': vote_record_i.get('sessionNumber'),
                #'sourceDataURL': vote_record_i.get('sourceDataURL'),
                #'startDate': vote_record_i.get('startDate'),
                #'updateDate_vote': vote_record_i.get('updateDate'),
                'voteQuestion': vote_record_i.get('voteQuestion'),
                #'voteType': vote_record_i.get('voteType')
            }
            results_list = vote_record_i.get('results', [])

            # Iterate through each term and create a new, flattened dictionary
            for vote in results_list:
                """vote contains this info:
                    "bioguideID": "A000148",
                    "firstName": "Jake",
                    "lastName": "Auchincloss",
                    "voteCast": "Present",
                    "voteParty": "D",
                    "voteState": "MA"
                    we only need bioguideID, voteCast, and voteParty
                """
                keep_terms = ['bioguideID', 'voteCast', 'voteParty']
                vote_keep = {key: vote[key] for key in keep_terms if key in vote}

                flattened_row = parent_fields.copy()  # Start with the parent data
                flattened_row.update(vote_keep)           # Add the nested term data
                full_voting_record.append(flattened_row)

            time.sleep(RATE_LIMIT_DELAY_SECONDS)
            i = i + 1
        except UnboundLocalError as e:
            my_logger.error(f"Voting record not found for {i}, either timeout or doesn't exist.")
            break
        except Exception as e:
            my_logger.error(f"An unhandled error occurred: {e}")
            break

    return full_voting_record


def get_root(url):
    try:
        response = requests.get(url)
        xml_content = response.content  # The XML content as bytes
        root = ET.fromstring(xml_content)
        return root
    except requests.exceptions.ConnectionError as e:
        my_logger.error(f"Connection error: {e}")
    except requests.exceptions.HTTPError as e:
        my_logger.error(f"HTTP error: {e}")



def get_voting_record_senate(old_votes, congress, session, max_records=1000, start_vote=1):
    # url example: https://www.senate.gov/legislative/LIS/roll_call_votes/vote1191/vote_119_1_00001.xml 
    # 1. Iterate over all the vote paths.
    # 2. Add same content as for house: congress, identifier, result, voteQuestion, voteType, bioguideID, voteCast, voteParty
    # 3. Add to a JSON
    # 
    #  
    url_base = f"https://www.senate.gov/legislative/LIS/roll_call_votes/vote{congress}{session}/vote_{congress}_{session}_"
    full_voting_record = old_votes
    i = start_vote
    max = start_vote+max_records
    my_logger.info(f"Starting from vote {i} for senate pull")
    while i < max:
        dict_i = {}

        # Pull the XML page for the ith vote
        num_to_string = str(i)
        if len(num_to_string) < 5:
            num_to_string = "0"*(5 - len(num_to_string)) + num_to_string + ".xml"

        try:
            url = url_base + num_to_string
            root = get_root(url)

            if root is None:
                my_logger.error(f"No root found for {i}. Quitting.")
                break

            dict_i['congress'] = root.find('congress').text
            dict_i['session'] = root.find('session').text
            dict_i['identifier'] = root.find('vote_number').text
            dict_i['result'] = root.find('vote_result').text
            dict_i['voteQuestion'] = root.find('question').text
            #voteType = root.find('') #??

            members_list = root.find('members')

            if members_list is None:
                my_logger.error("Error: The <members> element was not found.")
                break

            # Iterate through each <member> child of the <members> list
            for member_element in members_list.findall('member'):
                temp_dict = dict_i.copy()
                # 1. Get the ID
                temp_dict['lis_member_id'] = member_element.find('lis_member_id').text
                temp_dict['voteCast'] = member_element.find('vote_cast').text
                temp_dict['voteParty'] = member_element.find('party').text
                full_voting_record.append(temp_dict)
            my_logger.info(f"Success getting votes for vote {num_to_string} for Senate")

        except ET.ParseError as e:
            my_logger.error(f"XML {i} doesn't exist yet. Quitting.")
            break
        except ConnectionResetError as e:
            my_logger.error(f"Voting record not found for {i}, likely timeout issue. Quitting.")
            break
        except requests.exceptions.HTTPError as e:
            my_logger.error(f"Senate voting record {i} does not exist, quitting" )
            break
        except Exception as e:
            my_logger.error(f"An unhandled error occurred: {e}")
            break
        
        time.sleep(RATE_LIMIT_DELAY_SECONDS)
        i += 1
    return full_voting_record




def get_starting_point(starting_file):
    """
    Open the pre-existing file if it exists. If not, starting value is vote 1.
    Then check for the most recent voting record, return n+1 which will be the starting point.
    """
    #open input json file and load it in. 
    try:
        with open(starting_file, 'r') as f:
            data = json.load(f)

        n = str(data[-1].get('identifier'))
        if len(n) > 8: #house formatting (e.g. 11912025111), get rid of first 8
            id = int(n[8:])
            congress = int(n[0:3])
            session = int(n[3])

        else:
            id = int(n)
            congress = int(data[-1].get('congress'))
            session = int(data[-1].get('session'))
        print(congress, session, id+1)
        return congress, session, id+1

    except FileNotFoundError:
        print(f"Error: The file {starting_file} was not found. Starting from vote 1.")
        return 119, 1, 1
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON from the file. Check if the JSON is well-formed.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in get_starting_point: {e}")
        return None

    
def get_stop_point():
    """
    Docstring for get_stop_point
    Get how far we need to go in records.
    Increments congress# and session# for us.
    """
    current_year = date.today().year
    if current_year % 2 == 0:
        session = 1
    else:
        session = 0
    
    congress = (current_year - 1787 - session )/2
    return (congress, session)

def gen_voting_record_json(max_records=1000):
    """
    This script pulls all voting record data from the Congress.gov API.
    The output is "voting_records.json", which compiles all the data for each vote.
    Use the output of this to generate the dataframe to merge with congressmen info.
    Needs to be run semi-frequently. Added new functionality to pick up where 
    you left off 10/15.
    NOTE: Senate data is pulled from a different source, so both are handled here.
    Format for senate data is XML.

    Args:
        max_records (int): for debug, can set to limit number of voting records pulled.
    
    Outputs:
        voting_records_senate.json: File with senate votes.
        voting_records.json: File with house votes.
    """
    print("##############################################")
    print("Calling gen_voting_record_json.py for House Data")

    root =os.path.join(os.path.dirname(os.path.abspath(__file__)),  os.path.pardir)
    voting_records_json = os.path.join(root, "src", "generated_outputs", "voting_records.json")
    try:
        with open(voting_records_json, 'r') as file:
            file_house_votes = json.load(file)
    except FileNotFoundError:
        file_house_votes = []

    #Read pre-existing voting records to pick up where you left off.
    congress, session, house_start = get_starting_point(voting_records_json) #session 1/2
    max_congress, max_session = get_stop_point() #session 0/1

    while True:
        new_house_data = get_voting_record(file_house_votes, congress, session, max_records=max_records, start_vote=house_start)
        
        if congress == max_congress:
            if session == max_session+1:
                break
            else:
                session = 1 + (session % 2)
        else:
            congress += 1
            session = 1 + (session % 2)
        print(f"Now proceeding for congress {congress} session {session}")
        house_start = 1


    #Now save with full voting records
    with open(voting_records_json, 'w') as file:
        # Use indent for clean formatting
        json.dump(new_house_data, file, indent=2)

    my_logger.info(f"Done generating {voting_records_json}")


    print("##############################################")
    print("Calling gen_voting_record_json.py for Senate Data")

    voting_records_senate_json = os.path.join(root, "src", "generated_outputs", "voting_records_senate.json")

    try:
        with open(voting_records_senate_json, 'r') as file:
            file_senate_votes = json.load(file)
    except FileNotFoundError:
        file_senate_votes = []

    #Read pre-existing voting records to pick up where you left off
    congress, session, senate_start = get_starting_point(voting_records_senate_json)

    while True:
        new_senate_data = get_voting_record_senate(file_senate_votes, congress, session, max_records=max_records, start_vote=senate_start)
        
        if congress == max_congress:
            if session == max_session+1:
                break
            else:
                session = 1 + (session % 2)
        else:
            congress += 1
            session = 1 + (session % 2)

        senate_start = 1

    #Now save with full voting records
    with open(voting_records_senate_json, 'w') as file:
        # Use indent for clean formatting
        json.dump(new_senate_data, file, indent=2)


    my_logger.info(f"Done generating {voting_records_senate_json}")


