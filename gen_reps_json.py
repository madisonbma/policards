"""
This script pulls all congressmen data from the Congress.gov API.
The output is "congressmen.json", which is a json with info about each representative.
Use the output of this to generate the dataframe to merge with voting records.
Only needs to be run when there is a change in representatives
"""

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


########################################################


def get_bills_list(congress="119", bill_type="hr", limit=20, offset=0, sort="updateDateDesc"):
    """
    Fetches a list of bills from a specific Congress and bill type.

    Args:
        congress (str): The Congress number (e.g., "118").
        bill_type (str): The type of bill (e.g., "hr" for House Bill, "s" for Senate Bill).
        limit (int): Number of results to return per page (max 250).
        offset (int): Starting record number for pagination.
        sort (str): How to sort the results (e.g., "updateDateDesc", "updateDateAsc").

    Returns:
        dict: JSON response from the API, or None on error.
    """
    endpoint = f"bill"
    params = {
        "api_key": CONGRESS_API_KEY,
        "format": "json",
        "congress": congress,
        "type": bill_type,
        "limit": limit,
        "offset": offset,
        "sort": sort
    }

    try:
        print(f"Querying: {BASE_URL}{endpoint} with params: {params}")
        response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

        data = response.json()
        return data

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error: {e}")
    except requests.exceptions.Timeout as e:
        print(f"Timeout Error: {e}")
    except requests.exceptions.RequestException as e:
        print(f"An unexpected error occurred: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        print(f"Raw response: {response.text}")
    return None


def get_bill_details(congress, bill_type, bill_number):
    """
    Fetches detailed information for a specific bill.

    Args:
        congress (str): The Congress number (e.g., "118").
        bill_type (str): The type of bill (e.g., "hr", "s").
        bill_number (str): The bill number (e.g., "1").

    Returns:
        dict: JSON response from the API, or None on error.
    """
    endpoint = f"bill/{congress}/{bill_type}/{bill_number}"
    params = {
        "api_key": CONGRESS_API_KEY,
        "format": "json"
    }

    try:
        print(f"Querying: {BASE_URL}{endpoint}")
        response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params)
        response.raise_for_status()

        data = response.json()
        return data

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"An unexpected error occurred: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        print(f"Raw response: {response.text}")
    return None



def get_congress_members(congress=None, chamber=None, limit_per_page=250, max_members=None, sort="lastNameAsc"):
    """
    Fetches a list of members of Congress from the Congress.gov API, with pagination,
    and returns the collected data as a JSON formatted string.

    Args:
        congress (str, optional): The Congress number (e.g., "118"). If None,
                                  returns members from the current/latest Congress.
        chamber (str, optional): The chamber ("house" or "senate"). If None,
                                 returns members from both chambers for the specified congress.
        limit_per_page (int): Number of results to request per page (max 250 for this API).
        max_members (int, optional): The maximum number of members to fetch. If None,
                                     fetches all available members matching criteria.
        sort (str): How to sort the results. Common values:
                    "lastNameAsc", "lastNameDesc", "firstNameAsc", "firstNameDesc",
                    "birthDateAsc", "birthDateDesc".

    Returns:
        str: A JSON formatted string representing a list of member dictionaries.
             Returns an empty JSON array string "[]" if no data is found or an error occurs.
    """
    endpoint = "member"
    all_members_data = []
    current_offset = 0

    # Initial parameters
    params = {
        "api_key": CONGRESS_API_KEY,
        "format": "json",
        "limit": limit_per_page,
        "offset": current_offset,
        "sort": sort
    }

    if congress:
        params["congress"] = congress
    if chamber:
        params["chamber"] = chamber

    while True:
        try:
            print(f"Fetching members from offset: {current_offset} (Limit: {limit_per_page})")
            response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

            data = response.json()

            if 'members' in data and isinstance(data['members'], list):
                new_members = data['members']
                print(f"  - Got {len(new_members)} members from this page.")

                # Add new members to the list
                all_members_data.extend(new_members)

                # Check if we've hit the max_members limit
                if max_members is not None and len(all_members_data) >= max_members:
                    print(f"  - Reached max_members limit ({max_members}). Stopping.")
                    break

                # Check for pagination:
                pagination_info = data.get('pagination', {})
                if 'next' in pagination_info and pagination_info['next']:
                    current_offset += limit_per_page
                    params['offset'] = current_offset
                    time.sleep(RATE_LIMIT_DELAY_SECONDS)
                else:
                    print("  - No 'next' page indicated. All members fetched for this query.")
                    break # No more pages

            else:
                print("No 'members' key found in API response or invalid format. Ending pagination.")
                break

        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 429: # Too Many Requests
                print("Rate limit hit. Waiting and retrying (if logic supports, otherwise exiting).")
                time.sleep(RATE_LIMIT_DELAY_SECONDS * 5)
            break
        except requests.exceptions.ConnectionError as e:
            print(f"Connection Error: {e}")
            break
        except requests.exceptions.Timeout as e:
            print(f"Timeout Error: {e}")
            break
        except requests.exceptions.RequestException as e:
            print(f"An unexpected error occurred: {e}")
            break
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response: {e}")
            break
        except Exception as e:
            print(f"An unhandled error occurred: {e}")
            break

    # If max_members was specified, truncate the list
    if max_members is not None and len(all_members_data) > max_members:
        all_members_data = all_members_data[:max_members]

    print(f"\n--- Total members fetched: {len(all_members_data)} ---")

    # Convert the list of dictionaries to a JSON string
    return all_members_data # indent=2 for pretty printing


def flatten_user_terms(users_list):
    """
    The input is a list, with each entry a dictionary (with a dictionary inside). 
    We want to flatten that dictionary inside.
    Flattens a list of user dictionaries, each with a nested 'terms' field,
    into a single list of dictionaries where each row represents one term.

    FIELDS:
        'bioguideId'
        'depiction' *dictionary*
            {'attribution': 'Collection of the U.S. House of Representatives', 
            'imageUrl': 'https://www.congress.gov/img/member/c000243_200.jpg'}, 
        'name'
        'partyName'
        'state'
        'terms': 
            {'item': [{'chamber': 'House of Representatives',
            'endYear': 2011, 
            'startYear': 1993}]}, 
        'updateDate': '2025-08-15T12:19:20Z',
        'url': 'https://api.congress.gov/v3/member/C000243?format=json'}, 

    """
    all_flattened_terms = []

    for user_dict in users_list:
        # Safely get the terms list, handling cases where it's missing or not a dict
        terms_container = user_dict.get('terms', {})
        terms_list = terms_container.get('item', [])
        depiction_container = user_dict.get('depiction', {})


        # Get the parent fields you want to keep in each row
        parent_fields = {
            'bioguideID': user_dict.get('bioguideId'),
            'name': user_dict.get('name'),
            'partyName': user_dict.get('partyName'),
            'state': user_dict.get('state'),
            #'updateDate_rep': user_dict.get('updateDate'),
            'url': user_dict.get('url')
        }
        #add the depiction dictionary data
        parent_fields.update(depiction_container)
        
        # Iterate through each term and create a new, flattened dictionary
        for term in terms_list:
            # Create a new dictionary for this row
            flattened_row = parent_fields.copy()  # Start with the parent data
            flattened_row.update(term)           # Add the nested term data
            all_flattened_terms.append(flattened_row)
    
    return all_flattened_terms




###############################################
#main loop. generate the xls
###############################################
#Run to get the starting JSON. Don't need to do this every time, can just load in a pre-existing.
#Do this only once in a while. So first line is to save, second line is to load the file in
#if __name__ == "__main__":
def gen_reps_json():
    members_dict = get_congress_members()

    members_json = flatten_user_terms(members_dict)

    with open('congressmen.json', 'w') as f:
        json.dump(members_json, f, indent=2)

    print("Wrote to file name congressmen.json")
