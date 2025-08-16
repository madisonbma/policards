# --- Phase 1: Web Scraping ---
import requests
import os
import json
import time

# --- Configuration ---
CONGRESS_API_KEY = os.getenv("CONGRESS_API_KEY")
if CONGRESS_API_KEY is None:
    print("Error: CONGRESS_API_KEY environment variable not set.")
    print("Please get an API key from https://api.data.gov/signup/ and set it.")
    exit() # Exit if no API key is found

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

    print(f"Requesting members for vote: Congress {congress}, Session {session}, Vote #{vote_number}")

    try:
        full_url = f"{BASE_URL}{endpoint}"
        print(f"  - Querying: {full_url} with offset={params['offset']}")
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
        print(f"  - Fetched {len(member_votes_on_page)} member votes. Total: {len(all_member_votes)}")

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error for vote members: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 404:
            print("  - Vote not found or invalid congress/session/voteNumber combination.")
    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error for vote members: {e}")
    except requests.exceptions.Timeout as e:
        print(f"Timeout Error for vote members: {e}")
    except requests.exceptions.RequestException as e:
        print(f"An unexpected error occurred for vote members: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response for vote members: {e}")
    except Exception as e:
        print(f"An unhandled error occurred for vote members: {e}")

    return data.get('houseRollCallVoteMemberVotes')


def get_voting_record(max_records=100):
    """
    This will query house voting records up to max_records. 

    Args: 
        max_records (int): Max number of measures to get voting records of, defaults to 100 for now but will change once working

    """
    full_voting_record = []
    i = 1
    #Modify this, can set this whole thing to True when running for all voting records

    while i < max_records:
        try: 
            vote_record_i = get_house_vote_members(i)
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
                'voteType': vote_record_i.get('voteType')
            }
            results_list = vote_record_i.get('results', [])

            # Iterate through each term and create a new, flattened dictionary
            for vote in results_list:
                # Create a new dictionary for this row
                flattened_row = parent_fields.copy()  # Start with the parent data
                flattened_row.update(vote)           # Add the nested term data
                full_voting_record.append(flattened_row)

            time.sleep(RATE_LIMIT_DELAY_SECONDS)
            i = i + 1
        except requests.exceptions.HTTPError as e:
            print(f"Voting record {i} does not exist, quitting" )
            break
        except Exception as e:
            print(f"An unhandled error occurred: {e}")
            break

    return full_voting_record





#if __name__ == "__main__":
def gen_voting_record_json():
    voting_json = get_voting_record()

    with open('voting_records.json', 'w') as f:
        json.dump(voting_json, f, indent=2)

    print("Wrote to file name voting_records.json")


