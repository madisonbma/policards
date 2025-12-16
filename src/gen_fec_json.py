import requests
import pandas as pd
import os
import time
import json
import re
from io import StringIO
import csv
from src.init_logger import my_logger

FEC_API_KEY = os.getenv("FEC_API_KEY")
if FEC_API_KEY is None:
    print("Error: FEC_API_KEY environment variable not set.")
    print("Please get an API key from https://api.open.fec.gov/developers/ and set it.")
    exit() # Exit if no API key is found

BASE_URL = "https://api.open.fec.gov/v1/"
HEADERS = {
    "Accept": "application/json"
}
RATE_LIMIT_DELAY_SECONDS = 1

STATE_NAME_TO_CODE = {
    # U.S. States
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
    
    # District and Territories
    "District of Columbia": "DC",
    "American Samoa": "AS",
    "Guam": "GU",
    "Northern Mariana Islands": "MP",
    "Puerto Rico": "PR",
    "Virgin Islands": "VI"
}


COMMON_NICKNAMES = {
    "mike": "michael",
    "tom": "thomas",
    "tommy": "thomas",
    "thom": "thomas",
    "eli": "elijah",
    "ed": "edward",
    "russ": "russell",
    "joe": "joseph",
    "lucy": "lucia",
    "randy": "randall",
    "pat": "patrick",
    "rick": "richard",
    "don": "donald",
    "vern": "vernon",
    "beth": "elizabeth",
    "lizzie": "elizabeth",
    "zach": "zachary",
    "johnny": "john",
    "jon": "jonathan",
    "gabe": "gabriel",
    "rob": "robert",
    "ben": "benjamin",
    "herb": "herbert",
    "lou": "luis",
    "angie": "angela",
    "dan": "daniel",
    "ami": "amerish",
    "sam": "samuel",
    "al": "alexander",
    "andy": "andrew",
    "jim": "james",
    "val": "valerie",
    "bill": "william",
    "jeffrey": "jeff",
    "jefferson": "jeff",
    "ro": "rohit",
    "nick": "nicholas",
    "steve": "stephen",
    "nellie": "nelida",
    "pete": "peter",
    "greg": "gregory",
    "tim": "timothy",
    "josh": "joshua",
    "ted": "theodore",
    "david": "dave",
    "ronald": "ron",
    "charles": "chuck",
    "deb": "debra",
    "jake": "john"

}

CUSTOM_MAPPINGS = {
    "kelly, george j jr": "kelly, mike",
    "nick, lalota": "lalota, nick",
    "bergman, john": "bergman, jack",
    "arenholz, ashley hinson": "hinson, ashley",
    "amata, aumua": "radewagen, aumua amata coleman",
    "reed, john f.": "reed, jack"
}

MISSING_COMM_IDS = {
    'WINRED': 'C00694323'
}

def get_independent_expenditures(fec_mapping, cycle=2024):
    result = []
    for person in fec_mapping:
        candidate_id = person.get('candidate_id')
        endpoint = "schedules/schedule_e/by_candidate"
        params = {
            'api_key': FEC_API_KEY,
            'candidate_id': candidate_id,
            'page': 1,
            'per_page': 50,
            'cycle': cycle,
            'election_full': "true",
            'sort': '-total'
        }
        try:

            response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            data = response.json()
            print(f"Getting data for {person.get('name')}")
            results_list = data.get('results')
            #print(results_list)
            for bought in results_list:
                keepme = {
                    'bioguide_id': person.get('bioguide_id'),
                    'supporter_comm_id': bought.get('committee_id'),
                    'supporter_name': bought.get('committee_name'),
                    'SO': bought.get('support_oppose_indicator'),
                    'paid': bought.get('total')
                }
                result.append(keepme)

            time.sleep(RATE_LIMIT_DELAY_SECONDS)

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
        except KeyboardInterrupt:
            print("Keyboard interrupt.")
            break



    return result

def get_candidates_and_committees(office, page_start=1, election_cycle=2024):
    """
    Use the /candidates/search endpoint to get the term, successful or not. This will reduce API calls
    Then compare against the list of current representatives.
    Merge these data points - bioguideID to candidate_id, and candidate_id to committee_id.
    """
    endpoint = "candidates/search/"
    page = page_start
    result = []
    while True:
        try:
            params = {
                'api_key': FEC_API_KEY,
                'cycle': election_cycle,
                'per_page': 100,
                'page': page,
                'office': office
            }

            response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            data = response.json()
            
            results_list = data.get('results')
            result.extend(results_list)


            #Iterate through pages
            pagination = data.get('pagination')
            if page >= pagination.get('pages'):
                print(f"Fetched members from page {page}/{pagination.get('pages')} of {BASE_URL}{endpoint}")
                print(f"No pages left. Breaking. Should have {pagination.get('count')} records")
                break
            else:
                print(f"Fetched members from page {page}/{pagination.get('pages')} of {BASE_URL}{endpoint}")

                page += 1
                time.sleep(RATE_LIMIT_DELAY_SECONDS)


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

    return result


def cross_reference(fec_record, chamber, nonfec_record):
    results_list = []
    valid_names = {}
    
    if chamber == "H":
        cham_match = "House of Representatives"
    elif chamber == "S":
        cham_match = "Senate"

    # Go through the bioguide data to get a dictionary of the 
    for nonfec_person in nonfec_record:
        if not nonfec_person.get('endYear'): #only add them if they're current
            if nonfec_person.get("chamber")  == cham_match: # For now, since only doing house
                nonfec_name = nonfec_person.get('name').lower()
                nonfec_name = nonfec_name.replace("\"", "")
                nonfec_name = nonfec_name.replace("(", "")
                nonfec_name = nonfec_name.replace(")", "")
                nonfec_name = nonfec_name.replace("\'", "")
                nonfec_name = nonfec_name.replace("\u00e1", "a")
                nonfec_name = nonfec_name.replace("\u00e9", "e")
                nonfec_name = nonfec_name.replace("\u00fa", "u")
                nonfec_name = nonfec_name.replace("\u00ed", "i")
                nonfec_bioguide = nonfec_person.get('bioguideID')
                nonfec_state = STATE_NAME_TO_CODE.get(nonfec_person.get('state'))
                #Add all names to the bioguide dict
                key_tuple = (nonfec_name, nonfec_state)
                valid_names[key_tuple] = nonfec_bioguide

    #Get the data for each person, if they're a valid person add them to the list
    for person in fec_record:
        comm_list = []
        candidate_id = person.get('candidate_id')
        committees = person.get('principal_committees')
        for comm in committees:
            comm_list.append(comm.get('committee_id'))

        fec_state = person.get('state')
        fec_name = person.get('name').lower()

        # Get the custom mappings first for funky names:
        if fec_name in CUSTOM_MAPPINGS:
            bioguide_person = (CUSTOM_MAPPINGS.get(fec_name), fec_state)
            individual_dict = {
                'name': bioguide_person[0],
                'bioguide_id': valid_names.get(bioguide_person),
                'candidate_id': candidate_id,
                'committees': comm_list,
                'committees_len': len(comm_list)
            }
            del valid_names[bioguide_person]
            results_list.append(individual_dict)
        else:            

            fec_name = fec_name.replace("\"", "")
            fec_name = fec_name.replace("\'", "")
            fec_name_full = fec_name.split(", ")
            if len(fec_name_full) == 1: #name formatted without the comma, just split by space
                fec_name_full = fec_name.split(" ")
                fec_last_name = fec_name_full[-1]
                fec_first_name = fec_name_full[:-1]
            else:
                fec_last_name = fec_name_full[0].split(" ")
                fec_first_name = fec_name_full[1].split(" ")
            fec_first_name = [item for item in fec_first_name if "." not in item]

            #fec_name = re.search(name_pattern, person.get('name')).group(1)
            
            for bioguide_person in valid_names.keys():
                bioguide_name, bioguide_state = bioguide_person
                match_last = 0
                nonfec_name_full = bioguide_name.split(", ")
                nonfec_last_name = nonfec_name_full[0].split(" ")
                nonfec_first_name = nonfec_name_full[1].split(" ") 
                #throw out anything with "." so we don't match initials
                nonfec_first_name = [item for item in nonfec_first_name if "." not in item]

                # Step 1: if the states mismatch, this person ain't it, go on to next bioguide_person.  
                if fec_state == bioguide_state:
                
                    # Step 2: Now let's check if last names match
                    for last1 in nonfec_last_name: #check all words in each last name to see if any match
                        for last2 in fec_last_name:
                            if last1==last2:
                                match_last=1   
                    
                    # If any of the last names matched each other, look to see if first matches
                    # Map to classic nicknames just to double check
                    if match_last==1:
                        for first1 in nonfec_first_name:
                            for first2 in fec_first_name:
                                if first1==first2:
                                    # use this one  
                                    individual_dict = {
                                        'name': bioguide_name,
                                        'bioguide_id': valid_names.get(bioguide_person),
                                        'candidate_id': candidate_id,
                                        'committees': comm_list,
                                        'committees_len': len(comm_list)
                                    }
                                    match_last = 2
                                    remove = bioguide_person
                                    results_list.append(individual_dict)

                        #We've gone through the for loop and didn't match a first name. Check if it's maybe funky
                        if match_last != 2:
                            for first1 in nonfec_first_name:
                                for first2 in fec_first_name:
                                    if first1 in COMMON_NICKNAMES:
                                        first1 = COMMON_NICKNAMES.get(first1)
                                    elif first2 in COMMON_NICKNAMES:
                                        first2 = COMMON_NICKNAMES.get(first2)

                                    if first1==first2:
                                        # use this one, write in the log that we're doing a mapping
                                        individual_dict = {
                                            'name': bioguide_name,
                                            'bioguide_id': valid_names.get(bioguide_person),
                                            'candidate_id': candidate_id,
                                            'committees': comm_list,
                                            'committees_len': len(comm_list)
                                        }
                                        match_last = 2
                                        remove = bioguide_person
                                        results_list.append(individual_dict)
                                        print(f"Approximation made: {bioguide_name}, {fec_name}")
                        

                if match_last == 2: #This name worked, stop looking through bioguide_names
                    break

            if match_last == 2:
                del valid_names[remove]



    #For debug: print the missing names
    print(f"Succeeded for {len(results_list)}")
    print(f"Missing for bioguideid: {len(valid_names.keys())}")
    print(*valid_names.keys(), sep='\n')

    return results_list

   

def remove_duplicates(dict_list, unify_key):
    """
    Unify a dictionary on a given field - if duplicates exist for that field, merge.
    """
    seen = {}
    final_list = []
    for dictionary in dict_list:
        if dictionary.get(unify_key) in seen:
            continue
        else:
            final_list.append(dictionary)
            seen[dictionary.get(unify_key)] = 1
    print(f"Reduced input list from {len(dict_list)} to {len(final_list)}")
    return final_list



def get_top_donors(current_member_fec_mapping, election_cycle=2024, max=10):
    """
    Get the top 100 donations for the election_cycle.
    """
    endpoint = "schedules/schedule_a/"
    result = []
    i = 1

    for person in current_member_fec_mapping:
        if i == max:
            break
        i += 1
        comm_list = person.get('committees')
        for committee_id in comm_list:
        #committee_id = "C00313247"
            try:
                params = {
                    'api_key': FEC_API_KEY,
                    'committee_id': committee_id,
                    'two_year_transaction_period': election_cycle,
                    'per_page': 100,
                    'sort': '-contribution_receipt_amount', 
                    'contributor_aggregate_ytd': True,
                }
                
                print(f"Fetching members from page of {BASE_URL}{endpoint}")
                response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params)
                response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
                data = response.json()

                results_list = data.get('results')
                for contribution in results_list:
                    info_i_care_about = {
                        "bioguide_id": person.get('bioguide_id'),
                        "candidate_id": person.get('candidate_id'),
                        "committee_id": committee_id,
                        "two_year_transaction_period": contribution.get("two_year_transaction_period"),
                        "contribution_receipt_amount": contribution.get("contribution_receipt_amount"),
                        "contribution_receipt_date": contribution.get("contribution_receipt_date"),
                        "contributor_aggregate_ytd": contribution.get("contributor_aggregate_ytd"),
                        "contributor_id": contribution.get("contributor_id"),
                        "contributor_name": contribution.get("contributor_name"),
                        "contributor_employer": contribution.get("contributor_employer"),
                        "donor_committee_name": contribution.get("donor_committee_name"),
                        "entity_type": contribution.get("entity_type"),
                        "line_number_label": contribution.get("line_number_label")
                    }
                    result.append(info_i_care_about)
                time.sleep(RATE_LIMIT_DELAY_SECONDS)


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
            #except Exception as e:
            #    print(f"An unhandled error occurred: {e}")
            #    break
    return result


def get_nonregistered_bundles(current_member_fec_mapping, election_cycle=2024, max=10):
    """
    TODO
    Get the top 50 donations from non-individuals over $6600. 
    *Do we need to do over $6600?
    """
    endpoint = "schedules/schedule_a/"
    result = []
    i = 1

    for person in current_member_fec_mapping:
        if i == max:
            break
        i += 1
        comm_list = person.get('committees')
        for committee_id in comm_list:
        #committee_id = "C00313247"
            try:
                params = {
                    'api_key': FEC_API_KEY,
                    'committee_id': committee_id,
                    'two_year_transaction_period': election_cycle,
                    'per_page': 50,
                    'page': 1,
                    'sort': '-contribution_receipt_amount', 
                    'is_individual': "false"
                }
                
                print(f"Fetching for {committee_id} from page of {BASE_URL}{endpoint}")
                response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params)
                response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
                data = response.json()
                print(f"Found {data.get('pagination').get('count')} donations over $6600 for {committee_id} in {election_cycle} cycle")

                results_list = data.get('results')
                result_per_person = {}
                result_per_person['committee_id'] = committee_id

                for contribution in results_list:
                    info_i_care_about = {
                        "bioguide_id": person.get('bioguide_id'),
                        "candidate_id": person.get('candidate_id'),
                        "committee_id": committee_id,
                        "two_year_transaction_period": contribution.get("two_year_transaction_period"),
                        "contribution_receipt_amount": contribution.get("contribution_receipt_amount"),
                        "contribution_receipt_date": contribution.get("contribution_receipt_date"),
                        "contributor_aggregate_ytd": contribution.get("contributor_aggregate_ytd"),
                        "contributor_id": contribution.get("contributor_id"),
                        "contributor_name": contribution.get("contributor_name"),
                        "contributor_employer": contribution.get("contributor_employer"),
                        "donor_committee_name": contribution.get("donor_committee_name"),
                        "entity_type": contribution.get("entity_type"),
                        "line_number_label": contribution.get("line_number_label")
                    }
                    #result.append(info_i_care_about)
                    result_per_person['name'] = contribution.get('committee').get('name')

                    key = contribution.get('contributor_id')
                    if not key:
                        print(f"Null contributor ID, adding name")
                        key = contribution.get('contributor_name')
                    if not key:
                        print(f"No key found: {info_i_care_about}")
                    else:
                        result_per_person[key] = result_per_person.get(key, 0) + 1
                result.append(result_per_person)
                print(f"Found {len(result_per_person)} unique contributors in this category.")
                time.sleep(RATE_LIMIT_DELAY_SECONDS)


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
            #except Exception as e:
            #    print(f"An unhandled error occurred: {e}")
            #    break
    return result


def get_bundle_amounts(nr_bundles, election_cycle=2024, max=10):
    """
    Given the committee_ids of donors, get how much they donated to a campaign. 
    """
    endpoint = "schedules/schedule_b/by_recipient_id"
    result = []
    failed = []
    i = 1

    for person in nr_bundles:
        if i == max:
            break
        i += 1
        recipient = person.pop('name')
        recipient_comm = person.pop('committee_id')

        result_per_person = {}
        result_per_person['committee_id'] = recipient_comm
        print(f"Fetching {len(person)} results for {recipient}")

        for committee_id in person:
            #If the committee is known to be missing an ID, map to the known ID
            if committee_id in MISSING_COMM_IDS:
                print(f"Mapped {committee_id} to {MISSING_COMM_IDS[committee_id]}")
                committee_id = MISSING_COMM_IDS[committee_id]

            try:
                params = {
                    'api_key': FEC_API_KEY,
                    'committee_id': committee_id,
                    'cycle': election_cycle,
                    'recipient_id': recipient_comm,
                    'per_page': 1,
                    'page': 1
                }                
                #print(f"Fetching for {committee_id} from page of {BASE_URL}{endpoint}")
                response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params)
                response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
                data = response.json()
                responses = data.get('pagination').get('count')
                if responses == 0:
                    failed.append((committee_id, recipient_comm))
                    result_per_person[committee_id] = None
                elif responses == 1:
                    results = data.get('results')[0]
                    result_per_person[results.get('committee_name')] = results.get('total')
                    print(f"{results.get('committee_name')} : {results.get('total')}")
                else:
                    print(f"SKIPPING")


                time.sleep(RATE_LIMIT_DELAY_SECONDS)

            except requests.exceptions.HTTPError as e:
                print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 429: # Too Many Requests
                    print("Rate limit hit. Waiting and retrying (if logic supports, otherwise exiting).")
                    time.sleep(RATE_LIMIT_DELAY_SECONDS * 5)
                    break
                elif e.response.status_code == 422:
                    print(f"This committee_id {committee_id} doesn't exist. Manual lookup needed.")

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
            #except Exception as e:
            #    print(f"An unhandled error occurred: {e}")
            #    break
        result.append(result_per_person)
        print(f"Appending results for {recipient}")
    
    print(f"Failed the following from, to: ")
    print(*failed, sep='\n')

    return result


def get_lobbyist_receipts(cycle=2024, max_pages=5):
    """
    Get the Form 3L receipts for a given cycle. This will give all reports of lobbyists.
    Use the CSV to lookup the actual contributions from the lobbyists.
    """
    #Filings endpoint: committee/{committee_id}/filings
    endpoint = "filings"
    result = []
    page = 1

    while page <= max_pages:
            
        try:
            params = {
                'api_key': FEC_API_KEY,
                'page': page,
                'cycle': cycle,
                'per_page': 100,
                'form_type': "F3L"

            }
            
            print(f"Getting lobbying record for {cycle} cycle, page {page}")
            response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            data = response.json()
            print(f"There are {data.get('pagination').get('count')} records found.")

            results_list = data.get('results')
            for f3l in results_list:
                if f3l.get('pages') != 1:
                    keep = {
                        "amendment_version": f3l.get('amendment_version'),
                        'candidate_id': f3l.get('candidate_id'),
                        'committee_id': f3l.get('committee_id'),
                        'committee_name': f3l.get('committee_name'),
                        'committee_type': f3l.get('committee_type'),
                        'csv_url': f3l.get('csv_url')
                    }
                    keep = get_lobbyist_amounts(keep)
                    result.append(keep)

            time.sleep(RATE_LIMIT_DELAY_SECONDS)
            page += 1


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
            print(f"An unknown error occurred: {e}")
            break

    return result

def get_lobbyist_amounts(f3l):
    """
    Imports a CSV file from a given URL and returns its data as a list of dictionaries.
    """
    try:
        url = f3l.get('csv_url')
        print(f"Getting CSV records from {url}")
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        # Use StringIO to treat the string content as a file-like object
        csv_file = StringIO(response.text)

        # Use csv.reader to read the CSV into dictionaries
        csv_reader = csv.reader(csv_file)
        csv_list = list(csv_reader)
        lobby_row = csv_list[2]
        lobby_row = [item for item in lobby_row if item != ""]
        f3l['lobbyists'] = lobby_row
        print(f"Complete for url")
        return f3l

    except requests.exceptions.RequestException as e:
        print(f"Error fetching CSV from URL: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def get_lobbyists():
    temp = get_lobbyist_receipts()
    with open('lobbyist_data.json', 'w') as f:
        json.dump(temp, f, indent=2)


def get_bioguide_map(regenerate=0, save=0, append=0):
    ### Regenerate / reload data block
    if regenerate:
        print("Getting all house members from 2024")
        house_records = get_candidates_and_committees("H", page_start=1)
        if append: 
            try:
                with open('house_names.json', 'r') as file:
                    house_records_og = json.load(file)
            except FileNotFoundError:
                house_records_og = []
            house_records.extend(house_records_og)
        if save:
            with open('house_names.json', 'w') as f:
                json.dump(house_records, f, indent=2)
            print("Saved this master file to house_names.json")

        print("Getting all senate members from 2024")
        senate_records = get_candidates_and_committees("S", page_start=1)
        if append: 
            try:
                with open('senate_names.json', 'r') as file:
                    senate_records_og = json.load(file)
            except FileNotFoundError:
                senate_records_og = []
            senate_records.extend(senate_records_og)
        if save:
            with open('senate_names.json', 'w') as f:
                json.dump(senate_records, f, indent=2)
            print("Saved this master file to senate_names.json")

    else:
        try:
            with open('house_names.json', 'r') as file:
                house_records = json.load(file)
        except FileNotFoundError:
            house_records = []
        try:
            with open('senate_names.json', 'r') as file:
                senate_records = json.load(file)
        except FileNotFoundError:
            senate_records = []
        
    ### Create dict of current congressmen with mapping table for IDs and comms to look up for step 3
    try:
        with open('congressmen.json', 'r') as file:
            nonfec_record = json.load(file)
    except FileNotFoundError:
        print("WARNING: congressmen.json not loaded")
        nonfec_record = []

    if not house_records:
        print("WARNING: house_records is empty")
    if not senate_records:
        print("WARNING: senate_records is empty")
    current_member_fec_mapping_h = cross_reference(fec_record=house_records, chamber="H", nonfec_record=nonfec_record)
    current_member_fec_mapping_s = cross_reference(fec_record=senate_records, chamber="S", nonfec_record=nonfec_record)
    current_member_fec_mapping = current_member_fec_mapping_h + current_member_fec_mapping_s
    current_member_fec_mapping = remove_duplicates(current_member_fec_mapping, 'name')
    if save:
        with open('fec_mapping.json', 'w') as f:
            json.dump(current_member_fec_mapping, f, indent=2)
        print("Saved new dict from bioguide to fec in fec_mapping.json")


if __name__ == "__main__":
    if os.path.exists('fec_mapping.json'):
        print("Already have bioguide mapping. Skipping regeneration.")
    else:
        print("Could not find fec_mapping.json - regenerating bioguide mapping.")
        get_bioguide_map()

    if os.path.exists('lobbyist_data.json'):
        print("Lobbyist data already exists. Skipping regeneration.")
    else:
        print("Could not find lobbyist_data.json - regenerating lobbyist data")
        get_lobbyists()

    # get PAC independent expenditures
    if os.path.exists('independent_expenditures.json'):
        print("Already have independent expenditures. Skipping regeneration.")
    else:
        print("Generating independent_expenditures.json")
        with open ('fec_mapping.json', 'r') as f:
            fec = json.load(f)
        fec = remove_duplicates(fec, 'name')
        ie = get_independent_expenditures(fec)

        with open ('independent_expenditures.json', 'w') as f:
            json.dump(ie, f, indent=2)

    # TODO: get bundles of non-registered groups - not everyone will have, just should cap at 3300
    with open ('fec_mapping.json', 'r') as f:
        fec = json.load(f)
    fec = remove_duplicates(fec, 'name')

    if os.path.exists('nr_bundles.json'):
        print("Loading pre-existing nr_bundles.json")
        with open ('nr_bundles.json', 'r') as f:
            nr_bundles = json.load(f)
    else:
        nr_bundles = get_nonregistered_bundles(fec)        
        with open ('nr_bundles.json', 'w') as f:
            json.dump(nr_bundles, f, indent=2)

    bundles = get_bundle_amounts(nr_bundles)

    with open ('bundles.json', 'w') as f:
        json.dump(bundles, f, indent=2)


