

# --- Phase 1: Web Scraping ---
import requests
import os
import json
import time
from datetime import date
import xml.etree.ElementTree as ET
import sys
import argparse

sys.stdout.reconfigure(line_buffering=True)
BASE_URL = "https://api.congress.gov/v3/"
HEADERS = {
    "Accept": "application/json"
}
RATE_LIMIT_DELAY_SECONDS = 0.2 



def get_permissions():
    """
    This is permissions from before the exe conversion.
    The idea was to get config from politician_pages_assets or from env vars.
    Now switching to config file as input to script, this isn't needed anymore
    """
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
        parent_dir = os.path.join(application_path, os.path.pardir, os.path.pardir, os.path.pardir)
        config_path = os.path.join(parent_dir, "politician_pages_assets")
        config_file = os.path.join(config_path, "config.json")
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                CONGRESS_API_KEY = config.get('CONGRESS_API_KEY')
                print("Loaded API key from config.json")
        except FileNotFoundError:
            print(f"ERROR: {config_file} not found")
            print(f"TO FIX: Make sure you have pulled the politician_pages_assets repo.")
            CONGRESS_API_KEY = None
            sys.exit()
    else:
        # 1. Try to load from the private config repo
        try:
            application_path = os.path.dirname(__file__)
            parent_dir = os.path.join(application_path, os.path.pardir, os.path.pardir)
            config_path = os.path.join(parent_dir, "politician_pages_assets")
            config_file = os.path.join(config_path, "config.json")
            
            with open(config_file, 'r') as f:
                config = json.load(f)
                CONGRESS_API_KEY = config.get('CONGRESS_API_KEY')
                print("Loaded API key from config.json")

        # 2. Fallback to environment variables if file/repo is missing
        except (ImportError, ModuleNotFoundError, FileNotFoundError):
            CONGRESS_API_KEY = os.getenv("CONGRESS_API_KEY")
            
            if not CONGRESS_API_KEY:
                print("Error: Neither config.json nor environment variables found.")
                print(f"TO FIX: Make sure you have pulled the politician_pages_assets repo.")

            else:
                print("Loaded CONGRESS_API_KEY from environment variables")

        # Finally, remove the path to keep the environment clean
        finally:
            if 'config_path' in locals() and config_path in sys.path:
                sys.path.remove(config_path)





def get_house_vote_members(vote_number, api_key, congress=119, session=1, limit=250, offset=0):
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
        "api_key": api_key,
        "format": "json",
        "limit": limit,
        "offset": current_offset
    }


    try:
        full_url = f"{BASE_URL}{endpoint}"
        #my_logger.info(f"  - Querying: {full_url} with offset={params['offset']}")
        response = requests.get(full_url, headers=HEADERS, params=params)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

        data = response.json()

        # Access the 'results' list nested under 'houseRollCallVoteMemberVotes'
        member_votes_container = data.get('houseRollCallVoteMemberVotes')
        member_votes_on_page = []

        if isinstance(member_votes_container, dict):
            member_votes_on_page = member_votes_container.get('results', [])

        if not member_votes_on_page:
            print("  - No more member votes found for this roll call or 'results' key missing/empty.")

        all_member_votes.extend(member_votes_on_page)
        #my_logger.info(f"  - Fetched {len(member_votes_on_page)} member votes. Total: {len(all_member_votes)}")

    except requests.exceptions.HTTPError as e:
        print(f"gen_voting_record_json.get_house_vote_members HTTP Error for vote members: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 404:
            print("Vote not found.")
        else:
            raise e
    except requests.exceptions.ConnectionError as e:
        print(f"gen_voting_record_json.get_house_vote_members Connection Error for vote members: {e}")
        raise e
    except requests.exceptions.Timeout as e:
        print(f"gen_voting_record_json.get_house_vote_members Timeout Error for vote members: {e}")
        raise e
    except requests.exceptions.RequestException as e:
        print(f"gen_voting_record_json.get_house_vote_members An unexpected error occurred for vote members: {e}")
        raise e
    except json.JSONDecodeError as e:
        print(f"gen_voting_record_json.get_house_vote_members Error decoding JSON response for vote members: {e}")
        raise e
    except Exception as e:
        print(f"gen_voting_record_json.get_house_vote_members An unhandled error occurred for vote members: {e}")
        raise e

    return data.get('houseRollCallVoteMemberVotes')


def get_voting_record(old_votes, api_key, congress, session, max_records=1000, start_vote=1):
    """
    This will query house voting records up to max_records. 

    Args: 
        old_votes (loaded JSON): votes already done
        max_records (int): Max number of measures to get voting records of, defaults to 1000 for now but will change once working

    """
    full_voting_record = old_votes
    i = start_vote
    max = max_records + start_vote
    print(f"Starting from vote {i} for house pull")
    while i < max:
        try: 
            vote_record_i = get_house_vote_members(i, api_key, congress=congress, session=session)
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
            
            print(f"Pulled House congress {congress} session {session} - Vote {i}")

            time.sleep(RATE_LIMIT_DELAY_SECONDS)
            i = i + 1
        except UnboundLocalError as e:
            print(f"Voting record not found for {i}, either timeout or doesn't exist.")
            return full_voting_record
        except Exception as e:
            print(f"An unhandled error occurred: {e}")
            raise e

    return full_voting_record


def get_root(url):
    try:
        response = requests.get(url)
        xml_content = response.content  # The XML content as bytes
        root = ET.fromstring(xml_content)
        return root
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
        raise e
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e}")
        raise e



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
    print(f"Starting from vote {i} for senate pull")
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
                print(f"No root found for {i}. Quitting.")
                raise ValueError(f"No root found for {i}")

            dict_i['congress'] = root.find('congress').text
            dict_i['session'] = root.find('session').text
            dict_i['identifier'] = root.find('vote_number').text
            dict_i['result'] = root.find('vote_result').text
            dict_i['voteQuestion'] = root.find('question').text
            #voteType = root.find('') #??

            members_list = root.find('members')

            if members_list is None:
                print("Error: The <members> element was not found.")
                raise ValueError("Missing <members> element in XML.")

            # Iterate through each <member> child of the <members> list
            for member_element in members_list.findall('member'):
                temp_dict = dict_i.copy()
                # 1. Get the ID
                temp_dict['lis_member_id'] = member_element.find('lis_member_id').text
                temp_dict['voteCast'] = member_element.find('vote_cast').text
                temp_dict['voteParty'] = member_element.find('party').text
                full_voting_record.append(temp_dict)
            print(f"Pulled Senate congress {congress} session {session} - Vote {i}")


        except ET.ParseError as e:
            print(f"XML {i} doesn't exist yet. Quitting.")
            return full_voting_record
        except ConnectionResetError as e:
            print(f"Voting record not found for {i}, likely timeout issue. Quitting.")
            raise e
        except requests.exceptions.HTTPError as e:
            print(f"Senate voting record {i} does not exist, quitting" )
            raise e
        except Exception as e:
            print(f"An unhandled error occurred: {e}")
            raise e
        
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
        return congress, session, id+1

    except FileNotFoundError:
        print(f"Error: The file {starting_file} was not found. Starting from vote 1.")
        return 119, 1, 1
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON from {starting_file}. Check if the JSON is well-formed.")
        raise e
    except Exception as e:
        print(f"An unexpected error occurred in gen_voting_record_json.py/get_starting_point: {e}")
        raise e

    
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

def gen_voting_record_json(api_key, root, max_records=1000):
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
    print("Getting House Voting Records")

    voting_records_json = os.path.join(root, "src", "generated_outputs", "voting_records.json")
    try:
        with open(voting_records_json, 'r') as file:
            file_house_votes = json.load(file)
            print(f"Found file at {voting_records_json}. Will load that in first")
    except FileNotFoundError as e:
        print(f"File not found: {voting_records_json}. Make sure the config file is configured.")
        raise e
        #file_house_votes = []

    #Read pre-existing voting records to pick up where you left off.
    congress, session, house_start = get_starting_point(voting_records_json) #session 1/2
    max_congress, max_session = get_stop_point() #session 0/1

    while True:
        new_house_data = get_voting_record(file_house_votes, api_key, congress, session, max_records=max_records, start_vote=house_start)
        
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

    print("Now saving House records.")
    #Now save with full voting records
    with open(voting_records_json, 'w') as file:
        # Use indent for clean formatting
        json.dump(new_house_data, file, indent=2)


    print("House voting records all retrieved.")
    print("##############################################")
    print("Now getting Senate Voting Records")

    voting_records_senate_json = os.path.join(root, "src", "generated_outputs", "voting_records_senate.json")

    try:
        with open(voting_records_senate_json, 'r') as file:
            file_senate_votes = json.load(file)
    except FileNotFoundError as e:
        print(f"File not found: {voting_records_senate_json}. Make sure the config file is configured.")
        raise e

    #Read pre-existing voting records to pick up where you left off
    congress, session, senate_start = get_starting_point(voting_records_senate_json)

    while True:
        new_senate_data = get_voting_record_senate(file_senate_votes, congress, session, start_vote=senate_start)
        
        if congress == max_congress:
            if session == max_session+1:
                break
            else:
                session = 1 + (session % 2)
        else:
            congress += 1
            session = 1 + (session % 2)

        senate_start = 1

    print("Now saving Senate voting records.")
    #Now save with full voting records
    with open(voting_records_senate_json, 'w') as file:
        # Use indent for clean formatting
        json.dump(new_senate_data, file, indent=2)


    print("Senate voting records all retrieved.")

if __name__ == "__main__":
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

    parser = argparse.ArgumentParser(description="API Key")
    parser.add_argument('api', help="CONGRESS_API_KEY")
    parser.add_argument('pp_path', help="path to politician_pages repo")
    args = parser.parse_args()
    CONGRESS_API_KEY = args.api
    root = args.pp_path

    gen_voting_record_json(CONGRESS_API_KEY, root)