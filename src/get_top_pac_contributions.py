import argparse
import csv
from io import StringIO
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from rapidfuzz import fuzz
import re
import os


import requests

BASE_URL = "https://api.open.fec.gov"

debug = True

# ---------------------------------------------------------------------------
# Set dicts
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def save_json(data, filepath: Path, label: str):
    filepath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    print(f"\n  Saved {len(data)} records => {filepath}  [{label}]")


def get_all_pages_numbered(session: requests.Session, endpoint: str, params: dict, label: str) -> list:
    """
    Page through a FEC API endpoint using page= numbered pagination.
    Used by endpoints like schedule_b/by_recipient that do not return last_indexes.
    """
    results = []
    page_num = 0

    while True:
        page_num += 1
        call_params = dict(params)
        call_params["page"] = page_num

        print(f"  [{label}] fetching page {page_num} …", end="", flush=True)
        resp = session.get(f"{BASE_URL}{endpoint}", params=call_params)

        if resp.status_code != 200:
            print(f"\n  ERROR {resp.status_code}: {resp.text[:300]}")
            break

        data = resp.json()

        page_results = data.get("results", [])
        results.extend(page_results)
        print(f" got {len(page_results)} records (total so far: {len(results)})")

        pagination = data.get("pagination", {})
        total_pages = pagination.get("pages", 1)

        if page_num >= total_pages:
            break

        # Be polite to the API
        time.sleep(1)

    return results


def get_first_page_numbered(session: requests.Session, endpoint: str, params: dict, label: str) -> list:
    """
    Page through a FEC API endpoint using page= numbered pagination.
    Used by endpoints like schedule_b/by_recipient that do not return last_indexes.
    """

    call_params = dict(params)

    print(f"  [{label}] fetching first page …", end="", flush=True)
    resp = session.get(f"{BASE_URL}{endpoint}", params=call_params)

    if resp.status_code != 200:
        print(f"\n  ERROR {resp.status_code}: {resp.text[:300]}")
        return None

    data = resp.json()
    page_results = data.get("results", [])

    return page_results



def convert_to_ascii(name):

    name = name.replace("\u00e1", "a")
    name = name.replace("á", "a")
    name = name.replace("\u00e9", "e")
    name = name.replace("é", "e")
    name = name.replace("\u00fa", "u")
    name = name.replace("ú", "u")
    name = name.replace("\u00ed", "i")
    name = name.replace("í", "i")
    name = name.replace("\u00f3", "o")
    name = name.replace("ó", "o")
    return name



######################################################
# Step -2: Get the names and IDs of running candidates
######################################################
def get_candidates_and_committees(session: requests.Session, office: str, cycle: int) -> list:
        #session, office, page_start=1, election_cycle=2024):
    """
    Use the /candidates/search endpoint to get the term, successful or not.
    Then compare against the list of current representatives.
    Merge these data points - bioguideID to candidate_id, and candidate_id to committee_id.
    """

    params = {
        'cycle': cycle,
        'per_page': 100,
        'office': office,
        'is_active_candidate': "true",
        'incumbent_challenge': "I"
    }
    return get_all_pages_numbered(session, f"/v1/candidates/search/", params, "house_candidates")



######################################################
# Step -1: get the bioguide name mapping
######################################################
def cross_reference(fec_data, bioguide_data, cycle):
    #'name', 'party', 'state'. if match, take "candidate_id" and "district_number"
    people_map = {}
    for fec_person in fec_data:
        name_array = fec_person['name'].split(', ')
        if len(name_array) > 2:
            print(f"UHOH name {fec_person['name']} does not follow Last, First")
        else:
            fec_last = name_array[0].replace("-", " ").replace("'", "").split(" ")[-1].upper()
            fec_first = name_array[1].split(" ")[0].upper()
            appended_person = False
            for bio_person in bioguide_data:
                append_person = False
                bioname = convert_to_ascii(bio_person['name'])
                bioname_array = bioname.split(', ')
                bio_last = bioname_array[0].replace("-", " ").replace("'", "").split(" ")[-1].upper()
                bio_first = bioname_array[1].split(" ")[0].upper()

                if fec_last == bio_last:
                    if fec_first == bio_first:
                        append_person = True
                    elif STATE_NAME_TO_CODE.get(bio_person['state'], None) == fec_person['state']:
                        append_person = True
                    else:
                        append_person = False
                    
                    if append_person:
                        appended_person = True
                        if len(fec_person['principal_committees'])>1:
                            committee_list = []
                            for comm in fec_person['principal_committees']:
                                if cycle in comm['cycles']:
                                    committee_list.append(comm['committee_id'])
                                    #print(f" - Committee {comm['committee_id']} for {fec_person['name']} in cycle {cycle}")
                        else:
                            committee_list = [fec_person['principal_committees'][0]['committee_id']]
                        people_map[bio_person['bioguideID']] = {
                            "candidate_id": fec_person['candidate_id'],
                            "committee_id": committee_list,
                            "district_number": fec_person['district']
                        }
                        break
            if appended_person == False:
                print(f"Could not find a match for {fec_person['name']} in bioguide data.")
    
    return people_map


######################################################
# Step 0: probe the endpoint /v1/candidate/{candidate_id}/totals for totals
######################################################

def fetch_totals(session: requests.Session, candidate_id: str, cycle: int) -> list:
    """
    WARNING: This endpoint aggregates everything from the given cycle.
    This means that if someone ran for special election AND the next election, 
    both of these things would happen in one cycle. Then this reports both cases,
    which we don't really want - we want to distinguish.
    """
    
    print(f"\n=== Getting totals for candidate {candidate_id} (cycle {cycle}) ===")
    params = {
        "candidate_id": candidate_id,
        "cycle": cycle
    }
    totals = get_first_page_numbered(session, f"/v1/candidate/{candidate_id}/totals/", params, "totals")[0]
    #tot = {"pac_total": totals['other_political_committee_contributions'],
    #    "ind_total": totals['individual_contributions'],
    #    "total_in": totals['receipts']
    #}
    return totals
    

######################################################
# Step 1: probe the endpoint /v1/committee/{committee_id}/filings
######################################################

def fetch_filings(session: requests.Session, committee_id: str, cycle: int) -> list:
    print(f"\n=== Retrieveing all filings for {committee_id} (cycle {cycle}) ===")
    params = {
        "committee_id": committee_id,
        "cycle": cycle,
        "sort": "-receipt_date",
        "per_page": 100,
    }
    return get_all_pages_numbered(session, f"/v1/committee/{committee_id}/filings/", params, "filings")


######################################################
# Step 2: now that we have the endpoint, go through each filing (skip if already saw amended),
# and get the csv
######################################################
def fetch_filing_csv(filings_report, cycle):
    refund_data = {}
    pac_data = {}
    individual_data = {}
    skip_list = []

    if debug:
        temp_aggregate = []
    for filing in filings_report:

        if filing['csv_url'] is None:
            continue

        # print form_type, document_description, and report_type
        if filing['file_number'] in skip_list:
            #print(f"Skipping filing {filing['file_number']} since we already looked at an amended version of it")
            continue
        #Skip the original if we already looked at the amended version of the same report
        if filing['amendment_indicator'] == "A":
            skip_list.extend(filing['amendment_chain'][:-1]) #add all previous versions of the report to skip list
            #print(f"Skip this one {len(filing['amendment_chain'])-1} times")

        csv_data = get_csv_data(filing['csv_url'], filing['form_type'], cycle, refund_data, individual_data, pac_data)

        if debug:
            #TODO DELETE THIS, TEMPORARY: dumping everythign into csv_data for now
            #temp_aggregate.append([filing['form_type'], filing['document_description'], filing['csv_url']])
            if csv_data is not None:
                temp_aggregate.extend(csv_data)

    if debug:
        #TEMPORARY SAVE AGGREGATE CSV DATA TO DEBUG FILE
        temp_aggregate_path = Path("temp_aggregate.csv")
        with temp_aggregate_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(temp_aggregate)

    print("\n=====================================")
    print("Done retrieving data. Now consolidating contribution data.\n")
    final_data = consolidate_contribution_data(individual_data, pac_data)

    if len(refund_data) > 0:
        print("\n*************************\nRefunds leftover: ", refund_data)
    
    print("Saving contribution data")
    return final_data
    

def consolidate_contribution_data(individual_data, pac_data):
    """
    Contribution_data should look like this: 

    1234 5th St: [
        {SURNAME: greene,
        NAMES: [john greene, mary greene]
        COMPANIES: [company.co]
        CONTRIBUTION: total
        },
        {SURNAME: brown,
        NAMES: [leroy brown],
        COMPANIES: [disney],
        CONTRIBUTIONS: total
        }
    ],
    5678 9th St: [
        {SURNAME: white,
        NAMES: [john white]
        COMPANIES: [lawyer llc]
        CONTRIBUTIONS: total
        },
        {SURNAME: white,
        NAMES: [sarah white],
        COMPANIES: [disney],
        CONTRIBUTIONS: total
        }
    ],
    C00001234:
        NAME OF PAC: float(contribution),
        NAME OF PAC2: float(contribution)
    ORG_NAME: float(contribution)

    Want to convert to 
    COMPANY: contribution,
    C00001234+NAME OF COMMITTEE: contribution,
    ORG_NAME: contribution

    ***If COMPANIES len==0, then they're excluded (unemployed or self-employed).
    """
    final_data = {}
    #individual data, merge families
    for k,v in individual_data.items():
        for household in v:
            #if len(household['NAMES'])>1:
                #print(f"Household combined: {household["NAMES"]}")
            if len(household['COMPANIES'])>1:
                print("MORE THAN ONE COMPANY FOR THIS COUPLE:",
                        household['NAMES'],"-", household["COMPANIES"])
                str1 = household["COMPANIES"][0]
                str2 = household["COMPANIES"][1]
                similarity_score = fuzz.ratio(str1.upper(), str2.upper())
                if similarity_score > 60:
                    if similarity_score != 100:
                        print(f"Similarity {str1} to {str2}: {similarity_score:.2f}% > 60%. Merging.")
                    final_data[str1] = final_data.get(str1, 0) + household["CONTRIBUTIONS"]
                else:
                    print(f"Similarity {str1} to {str2}: {similarity_score:.2f}% <= 60%.")

            elif len(household["COMPANIES"]) == 0:
                #print("All members of household undisclosed.")
                final_data["Undisclosed"] = final_data.get("Undisclosed", 0) + household['CONTRIBUTIONS']
            else:
                company = household["COMPANIES"][0]
                final_data[company] = final_data.get(company, 0) + household["CONTRIBUTIONS"]
        
    #go through companies and merge if score is high, merge on higher contribution amount.
    companies = list(final_data)
    for i in range(len(companies)):
        for j in range(i+1, len(companies)):
            if companies[i] in companies[j]:
                #print(f"Found {companies[i]} in {companies[j]}")
                pass
            elif companies[j] in companies[i]:
                #print(f"Found {companies[j]} in {companies[i]}")
                pass
            else:
                company1 = companies[i].upper()
                company2 = companies[j].upper()
                similarity_score = fuzz.ratio(company1, company2)
                if similarity_score == 100:
                    #merge if they're the same, just caps difference.
                    if final_data[companies[i]] >= final_data[companies[j]]:
                        #print(f"{companies[i]} => {final_data[companies[i]]+final_data[companies[j]]}")
                        final_data[companies[i]] += final_data[companies[j]]
                        final_data[companies[j]] = 0
                    else:
                        #print(f"{companies[j]} => {final_data[companies[i]]+final_data[companies[j]]}")
                        final_data[companies[j]] += final_data[companies[i]]
                        final_data[companies[i]] = 0
                        break
                elif similarity_score > 90:
                    company1_split = re.split(r"[ \-]", company1)
                    company2_split = re.split(r"[ \-]", company2)
                    if len(company1_split) > 1 and len(company1_split) == len(company2_split):
                        similarity_score = 0
                        count = 0
                        for index in range(len(company1_split)):
                            score = fuzz.ratio(company1_split[index], company2_split[index])
                            if score != 100:
                                similarity_score += score
                                count += 1
                        if similarity_score != 0:
                            similarity_score = similarity_score / count
                        else:
                            similarity_score = 100


                    if similarity_score > 90:
                        print(f"{similarity_score:.2f}% similar: {companies[i]}, {companies[j]}. Going to merge them.")
                        if final_data[companies[i]] >= final_data[companies[j]]:
                            #print(f"{companies[i]} => {final_data[companies[i]]+final_data[companies[j]]}")
                            final_data[companies[i]] += final_data[companies[j]]
                            final_data[companies[j]] = 0
                        else:
                            #print(f"{companies[j]} => {final_data[companies[i]]+final_data[companies[j]]}")
                            final_data[companies[j]] += final_data[companies[i]]
                            final_data[companies[i]] = 0
                            break
                    else:
                        print(f"Whittled: {similarity_score:.2f}% similar: {companies[i]}, {companies[j]}")




    #PACs and ORGs 
    for k,v in pac_data.items():
        if isinstance(v, dict): #PAC data.
            if (len(v) > 1):
                print("Multiple PACs under the same committee_id:", k, v)
                str1 = list(v)[0]
                str2 = list(v)[1]
                similarity_score = fuzz.ratio(str1, str2)
                if similarity_score > 60:
                    print(f"Similarity {str1} to {str2}: {similarity_score:.2f}% > 60%. Merging.")
                    final_data[str1] = final_data.get(str1, 0) + household["CONTRIBUTIONS"]
                else:
                    print(f"Similarity {str1} to {str2}: {similarity_score:.2f}% <= 60%.")
            for pac_name, contribution in v.items():
                final_data[pac_name] = final_data.get(pac_name, 0) + contribution
        else: #ORG data.
            final_data[k] = v
            continue

    return final_data



def get_csv_data(url, form_type, cycle, refund_data, individual_data, pac_data):
    """
    Imports a CSV file from a given URL and returns its data as a list of dictionaries.
    """
    try:
        if url is None:
            print("No CSV URL provided for this filing, skipping.")
            return None
        
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        # Use StringIO to treat the string content as a file-like object
        csv_file = StringIO(response.text)

        # Use csv.reader to read the CSV into dictionaries
        csv_reader = csv.reader(csv_file)
        csv_list = list(csv_reader)

        if form_type== "F3":
            print(f"=== Processing F3 {url} ===")
            get_refund_data(csv_list, refund_data, cycle)
            #print(refund_data)
            process_form(csv_list, individual_data, pac_data, refund_data, cycle)
            refund_data = clean_refund_data(refund_data)
            return csv_list
        elif form_type in ["F6", "F1", "F99"]:
            #F6==48hour notice of funds
            #F1==Statement of Organization
            #F99==Misc text disclaimers
            #print("Skipping F6 since double counted in F3s for not-current cycles.")
            return None
            #pass
        else:
            print("=== Skipping unknown form type: ", form_type, url, "===")
            return None
            
        #return csv_list

    except requests.exceptions.RequestException as e:
        print(f"Error fetching CSV from URL: {e}")
        return None

    

def clean_refund_data(refund_data):
    for key in [k for k in refund_data if k.startswith('temp_')]:
        del refund_data[key]
    return refund_data


def get_refund_data(csv_data, refund_data, cycle):
    """
    REFUND_DATA:
    IND: row[7]+row[8]+row[12]+row[15]+row[16]
    COM: row[6]
    PAC: row[24]
    CCM: row[24]
    ORG: row[7]+row[8]+row[12]+row[15]+row[16]
    else: skipped
    """

    for row in csv_data:

        #set key to add to refund_data
        if row[0].upper() == "SB20A": #refunds of contributions - add as negative
            if row[5] == "IND":
                contribution = float(row[20])
                key = row[7] + row[8] + row[12] + row[15] + row[16]
                key = key.upper()
            elif row[5] == "ORG":
                contribution = float(row[20])
                key = row[7] + row[8] + row[12] + row[15] + row[16]
                key = key.upper()
            else:
                print(f"Found a non-IND/ORG in SB20A...: {row[5]}")

        elif row[0].upper() == "SB20C":
            if row[5]=="COM":
                key = row[6].upper()
            elif row[5] == "PAC":
                key = row[24]
                if not re.match(r"C\d{8}", key):
                    print(f"Invalid committee code for {row[6]}: {key}")
            elif row[5] == "CCM":
                key = row[24]
                if not re.match(r"C\d{8}", key):
                    print(f"Invalid committee code for {row[6]}: {key}")
            else:
                print(f"Don't know what to do with this for SB20C: {row[5]}")
                key = row[24]
                if not re.match(r"C\d{8}", key):
                    print(f"Invalid committee code for {row[6]}: {key}")

        else:
            continue

        #only add to refund_data if it's the election we care about
        if str(cycle) in row[17]: # or "Special" in row[18]: #only for current cycle
            contribution = float(row[20])
            refund_data[key] = refund_data.get(key, 0) - contribution


def check_refund(refund_data, row):
    """
    REFUND_DATA:
    IND: row[7]+row[8]+row[12]+row[15]+row[16]
    temp_<RECEIPT>
    COM: row[6].upper()
    PAC: row[24]
    CCM: row[24]
    ORG: row[7]+row[8]+row[12]+row[15]+row[16]

    else: skipped
    """
    contribution = float(row[20])
    if refund_data is None:
        return contribution
    

    update_contribution_amount = False
    add_associated_receipt = False


    #check if the person/pac was refunded directly
    if row[5] == "IND":
        #direct contribution check
        refund_code = row[7] + row[8] + row[12] + row[15] + row[16]
        refund_code = refund_code.upper()
        if refund_code in refund_data: #check individual immmediately.
            update_contribution_amount = True
            add_associated_receipt = True

        #mistaken bundle-flag check
        else:
            refund_code = row[3] if row[3] else row[2]
            refund_code = f"temp_{refund_code}"
            if refund_code in refund_data:
                print("Not bundled, just IND moving money around. Removing.")
                refund_data.pop(refund_code)
                return contribution
            else:
                return contribution

    else:
        
        #check if it was bundled, regardless of [5]
        refund_code = row[3] if row[3] else row[2]
        refund_code = f"temp_{refund_code}"
        if refund_code in refund_data:
            print(f"Found bundle. {row[6]}")
            update_contribution_amount = True

        #it wasn't bundled. then check for direct contributions
        else:
            if row[5] == "PAC":
                refund_code = row[25] #committee_code instead
                if not re.match(r"C\d{8}", refund_code):
                    print(f"No committee code found for PAC SA11C: {row[6]}")

                if refund_code in refund_data:
                    update_contribution_amount = True
                else:
                    return contribution
            elif row[5] == "CCM":
                refund_code = row[25]
                if not re.match(r"C\d{8}", refund_code):
                    print(f"No committee code found for CCM SA11C: {row[6]}")

                if refund_code in refund_data:
                    update_contribution_amount = True
                else:
                    return contribution
            elif row[5] == "COM":
                refund_code = row[6].upper()
                if refund_code in refund_data:
                    update_contribution_amount = True
                else:
                    return contribution
            elif row[5] == "ORG":
                refund_code = row[7] + row[8] + row[12] + row[15] + row[16]
                refund_code = refund_code.upper()
                if refund_code in refund_data: #check individual immmediately.
                    update_contribution_amount = True
                else:
                    return contribution
            else:
                print(f"Uncaught: don't know how to check refund for {row[5]}")
        ######################################################

    if (update_contribution_amount):
        refund = refund_data[refund_code]
        real_contribution = contribution + refund
        if real_contribution == 0:
            #print(f"Cancel each other out, remove: {refund_code}")
            contribution = 0
            refund_data.pop(refund_code) #remove from refund data since we've matched it to a contribution
        elif real_contribution < 0:
            #print(f"Still some refund left: {refund_code} has {real_contribution}")
            contribution = 0
            refund_data[refund_code] = real_contribution
        else:
            #print(f"Refunded with some funds left over: {refund_code}=> {real_contribution}")
            contribution = real_contribution
            refund_data.pop(refund_code)

    if (add_associated_receipt):
        if row[5] == "IND":
            connected_receipt = row[3] if row[3] else row[2]
            connected_receipt = f"temp_{connected_receipt}"
            #then check for receipt, add if doesn't exist
            refund_data[connected_receipt] = refund_data.get(connected_receipt, 0) + refund

            #print(f"Adding/updating {connected_receipt}: {refund_data[connected_receipt]}")
        else:
            print(f"Can't add associated receipt for non-IND: {row[5]}")
            pass


    return contribution

def process_form(csv_data, individual_data, pac_data, refund_data, cycle):
    """Replacement process_form, just swapping with dict-style
    family_data method since most of the data is there anyways.
    
    1234 5th St: [
        {SURNAME: greene,
        NAMES: [john greene, mary greene]
        COMPANIES: [company.co, unemployed]
        CONTRIBUTION: total
        },
        {SURNAME: brown,
        NAMES: [leroy brown],
        COMPANIES: [disney],
        CONTRIBUTION: total
        }
    ],
    C00001234+NAME OF COMMITTEE: float(contribution),
    ORG_NAME: float(contribution)
    
    """

    form_version = csv_data[0][2]
    for row in csv_data: 
        if row[0].upper() in ["HDR", "F3N", "F3A", "F3S", "F6A", "F6N", "TEXT"]:
            continue

        if str(cycle) not in row[17]: #and "Special" not in row[18]: #only for current cycle
            continue
        """
        if form_version == "8.4":
            if row[0].upper() == "SA11AI" or row[0].upper() == "SA12": #itemized individual contributions
                contribution = check_refund(refund_data, row)
                if row[5] == "PAC": #If PAC, sum contributions by committee_id.
                    pac_data['PAC TOTAL'] = pac_data.get("PAC TOTAL", 0) + contribution
                    name = row[26].upper().replace("POLITICAL ACTION COMMITTEE", "PAC")
                    committee_id = row[25]
                    if committee_id == "":
                        print("Missing committee_id for PAC contribution from", name)
                        pac_data[name] = pac_data.get(name, 0) + contribution
                    else: 
                        if committee_id in pac_data:
                            if name in pac_data[committee_id]:
                                pac_data[committee_id][name] += contribution
                            else:
                                pac_data[committee_id][name] = contribution
                        else:
                            pac_data[committee_id] = {name: contribution}
                elif row[5] == "IND": #if IND, sum contributions by employer
                    #pac_data["INDIVIDUAL TOTAL"] = pac_data.get("INDIVIDUAL TOTAL", 0) + contribution
                    factor_in_family_for_contribution(row, individual_data)

                elif row[5] == "ORG":
                    #org doesn't have committee ID, treat as individual
                    #pac_data["INDIVIDUAL TOTAL"] = pac_data.get("INDIVIDUAL TOTAL", 0) + contribution
                    name = row[6].upper()
                    if name == "":
                        print("Missing name for ORG contribution from", row[6])
                    else:
                        pac_data[name] = pac_data.get(name, 0) + contribution
                else:
                    print("Unknown contribution type in v8.4:", row[5])
            elif row[0].upper() == "SA11B":
                contribution = float(row[20])
                name = row[26].upper() if row[26] else row[6].upper()
                committee_id = row[25]
                if committee_id == "":
                        print("Missing committee_id in SA11B party donation", name)
                else: 
                    if committee_id in pac_data:
                        if name in pac_data[committee_id]:
                            pac_data[committee_id][name] += contribution
                        else:
                            pac_data[committee_id][name] = contribution
                    else:
                        pac_data[committee_id] = {name: contribution}
            elif row[0].upper() == "SA11C": #committee contributions
                contribution = float(row[20])
                if row[5] == "PAC":
                    pac_data["PAC TOTAL"] = pac_data.get("PAC TOTAL", 0) + contribution

                if row[5]== "PAC" or row[5] == "CCM" or row[5] == "COM":
                    name = row[26].upper().replace("POLITICAL ACTION COMMITTEE", "PAC")
                    committee_id = row[25]
                    if committee_id == "":
                        print("Missing committee_id for PAC contribution from", name)
                        pac_data[name] = pac_data.get(name, 0) + contribution
                    else: 
                        if committee_id in pac_data:
                            if name in pac_data[committee_id]:
                                pac_data[committee_id][name] += contribution
                            else:
                                pac_data[committee_id][name] = contribution
                        else:
                            pac_data[committee_id] = {name: contribution}
                
                else:
                    print("Unknown non-PAC SA11C contribution in v8.4:", row[5])
            elif row[0].upper() == "SA11D": #self-funded:
                pass
            elif row[0].upper() == "SA14": #offsets to operating expenditures - not direct contribution so skip
                pass
            elif row[0].upper() == "SA15": #misc indirect (interest, rebate, dividend) - not direct contribution so skip
                pass
            elif row[0].upper() == "SB17": #operating expenditures - spending, not contribution so skip
                pass  
            elif row[0].upper() == "SB18": #operating expenditures - spending, not contribution so skip
                pass   
            elif row[0].upper() == "SB20A" or row[0].upper() == "SB20C": #already did refund data
                pass
            elif row[0].upper() == "SB21": #other disbursements, money given to other committees. not contribution skip
                pass
            elif row[0].upper() == "SD10": #debts. skip
                pass
            else:
                print("Unknown row type in version 8.4:", row[0])
        """
        if form_version == "8.5" or form_version == "8.4":
            if row[0].upper() == "SA11AI" or row[0].upper() == "SA11C" or row[0].upper() == "SA12": #itemized individual contributions
                contribution = check_refund(refund_data, row)

                if row[5] == "PAC":
                    pac_data["PAC TOTAL"] = pac_data.get("PAC TOTAL", 0) + contribution
                
                if row[5] == "IND":
                    factor_in_family_for_contribution(row, individual_data)
                else:
                    if row[26] != "":
                        name = row[26].upper().replace("POLITICAL ACTION COMMITTEE", "PAC")
                    elif row[6] != "":
                        name = row[6].upper().replace("POLITICAL ACTION COMMITTEE", "PAC")    
                    else:
                        print(f"Missing name for SA11 contribution {row}, skipping.")
                    
                    if row[25] == "": #no committee ID. Merge on name.
                        pac_data[name] = pac_data.get(name, 0) + contribution
                    #if there's a committee, merge on committee_id and name.
                    else:
                        committee_id = row[25]
                        if committee_id in pac_data:
                            if name in pac_data[committee_id]:
                                pac_data[committee_id][name] += contribution
                            else:
                                pac_data[committee_id][name] = contribution
                        else:
                            pac_data[committee_id] = {name: contribution}
            elif row[0].upper() == "SA11B":
                contribution = float(row[20])
                name = row[26].upper() if row[26] else row[6].upper()
                committee_id = row[25]
                if committee_id == "":
                        print("Missing committee_id in SA11B party donation", name)
                else: 
                    if committee_id in pac_data:
                        if name in pac_data[committee_id]:
                            pac_data[committee_id][name] += contribution
                        else:
                            pac_data[committee_id][name] = contribution
                    else:
                        pac_data[committee_id] = {name: contribution} 
            elif row[0].upper() == "SA11D": #self-funded:
                pass
            elif row[0].upper() == "SA14": #offsets to operating expenditures - not direct contribution so skip
                pass
            elif row[0].upper() == "SA15": #misc indirect (interest, rebate, dividend) - not direct contribution so skip
                pass
            elif row[0].upper() == "SB17": #operating expenditures - spending, not contribution so skip
                pass  
            elif row[0].upper() == "SB18": #operating expenditures - spending, not contribution so skip
                pass   
            elif row[0].upper() == "SB20A" or row[0].upper() == "SB20C": #already did refund data
                pass
            elif row[0].upper() == "SB21": #other disbursements, money given to other committees. not contribution skip
                pass
            elif row[0].upper() == "SD10": #debts. skip
                pass
            else:
                print("Unknown row type in version 8.5:", row[0])
    
        else:
            print(f"Unsupported form version: {form_version}")



def replace_company_name(employer):
    partial_replacement = {
        "U of ": "University of ",
        "Univ.": "University",
        "Univ ": "University ",
        " Of ": " of ",
        "Nyu": "NYU",
        " And ": " & ",
        " and ": " & ",
        "U.S. ": "US ",
        "Calif ": "California",
        "Svc": "Service",
        ",": "",
        ".": "",
    }

    end_replacement = {
        " Corp": "",
        " Corporation": ""
    }

    full_name_replacement = {
        "Amazoncom": "Amazon",
        "Amazon Com": "Amazon",
        "Amazon Web Services": "Amazon",
        "Facebook": "Meta",
        "Facebook Inc": "Meta",
        "Qualcomm Technologies, Inc.": "Qualcomm",
        "NYU": "New York University",
        "CUNY": "City University of New York"
    }

    for key, value in partial_replacement.items():
        employer = employer.replace(key, value)


    for k, v in end_replacement.items():
        if employer.endswith(k):
            # Slice off the ending part, and replace it with the new value
            employer = employer[:-len(k)] + v

    return full_name_replacement.get(employer, employer)


def factor_in_family_for_contribution(row, individual_data):
    """
    Some contributions are made by family members, if they aren't working then
    we'll consider their contribution their spouse's contribution.
    Infer: same last name, same primary household."""

    undisclosed = ["NOT EMPLOYED", "SELF EMPLOYED", "SELF-EMPLOYED", "ME", "HOME", "SELF",
                   "N/A", "SELF- EMPLOYED"]
    # ADDRESS: [
    #   {LAST_NAME: GREEN
    #   NAMES: [person1, person2]
    #   COMPANIES: [role1, role2]
    #   CONTRIBUTIONS: contribution
    #   }
    # ]
    address = row[12]+row[14]+row[15]
    job = replace_company_name(row[23])
    contribution = float(row[20])
    name = (row[8]+row[7]).upper() #last name + first name, all uppercase to avoid case issues
    last_name = row[7].upper()
    new_person = True

    #if no one lives here, add them
    if individual_data.get(address) is None:
        individual_data[address] = [{"LAST_NAME": last_name, 
                                "NAMES": [name], 
                                "COMPANIES": [job] if job.upper() not in undisclosed else [],
                                "CONTRIBUTIONS": contribution
                                }]
        
    #if someone already lives here, check if their last names match to combine      
    else: 
    
        for person in individual_data[address]:
            #if last name is direct match
            if last_name in person["LAST_NAME"]:
                #print(f"Match found for {name} at {address} with last name {last_name}")
                if name in person["NAMES"]:
                    person["CONTRIBUTIONS"] += contribution
                    new_person = False
                    break
                else:
                    #if names don't match, new person. if undisclosed, add name and sum contribution
                    #if not undisclosed, new_person = True
                    if job.upper() in undisclosed:
                        person['CONTRIBUTIONS'] += contribution
                        person["NAMES"].append(name)
                        new_person = False
                        break
                    else:
                        continue
            #otherwise if they have a dash, check both last names
            elif "-" in last_name:
                last_name_parts = last_name.split("-")
                for possible_last in last_name_parts:
                    if possible_last in person["LAST_NAME"]:
                        #print(f"Hyphenated name match found for {name} at {address} with possible last name {possible_last}")
                        if name not in person["NAMES"]:
                            person["NAMES"].append(name)
                        if job not in person["COMPANIES"]:
                            person["COMPANIES"].append(job)
                            person["COMPANIES"] = [x for x in person["COMPANIES"] if x.upper() not in undisclosed]
                        person["CONTRIBUTIONS"] += contribution
                        new_person = False
                        break
            #if they don't match, add as a new person at the address
        if new_person:
            #print(f"No hyphenated name match found for {name} at {address}")
            new_dict = {"LAST_NAME": last_name, 
                        "NAMES": [name], 
                        "COMPANIES": [job] if job.upper() not in undisclosed else [],
                        "CONTRIBUTIONS": contribution
                        }
            individual_data[address].append(new_dict)







def main2():
    parser = argparse.ArgumentParser(
        description="Get filing endpoints to parse the CSVs for full receipt data."
    )
    parser.add_argument("--api-key", required=True, help="FEC API key")
    parser.add_argument("--bioguide-id", required=True, help="bioguideID of candidate")
    parser.add_argument(
        "--cycle",
        required=True,
        type=int,
        help="Two-year transaction period / cycle (e.g. 2024)",
    )

    parser.add_argument(
        "--out-dir",
        default=".",
        help="Directory to write output files (default: current directory)",
    )

    parser.add_argument(
        "--filings-raw",
        default=None,
        help="Path to an existing filings.json file. When provided, "
             "skips fetching filings from the API and loads data from this file instead.",
    )

    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Shared session with API key
    session = requests.Session()
    session.params = {"api_key": args.api_key}  # type: ignore[assignment]

    # ── Step N: get all running candidates names and comms ──────────────────────
    house_runners_path = out_dir / f"house_runners_{args.cycle}.json"
    senate_runners_path = out_dir / f"senate_runners_{args.cycle}.json"
    if house_runners_path.exists() and senate_runners_path.exists():
        house_runners = json.loads(house_runners_path.read_text(encoding="utf-8"))
        senate_runners = json.loads(senate_runners_path.read_text(encoding="utf-8"))
        print(f"  House already generated - loaded {len(house_runners)} records.")
        print(f"  Senate already generated - loaded {len(senate_runners)} records.")
    else:
        house_runners = get_candidates_and_committees(session, "H", args.cycle)
        print(f"  House generated {len(house_runners)} records.")
        save_json(house_runners, house_runners_path, "house runners")

        senate_runners = get_candidates_and_committees(session, "S", args.cycle)
        print(f"  Senate generated {len(senate_runners)} records.")
        save_json(senate_runners, senate_runners_path, "senate runners")


    # ── Step N: open congressmen.json to get names and bioguide_ids ──────────────────────
    bioguide_path = Path("generated_outputs") / "congressmen.json"
    bioguide_data = json.loads(bioguide_path.read_text(encoding="utf-8"))
    print("Run for House")
    house_map = cross_reference(house_runners, bioguide_data, args.cycle)
    print("Run for Senate")
    senate_map = cross_reference(senate_runners, bioguide_data, args.cycle)
    bioguide_map = house_map | senate_map
    save_json(bioguide_map, out_dir / f"bioguide_fec_map_{args.cycle}.json", "house bioguide map")

    # ── Step 0: get PAC and ind totals ─────────────────────────
    if bioguide_map.get(args.bioguide_id) is None:
        print(f"Error: bioguide_id {args.bioguide_id} not found in bioguide map. Please check the bioguide_id and cycle, and ensure the candidate is running in that cycle.")
        return
    
    candidate_id = bioguide_map[args.bioguide_id]["candidate_id"]
    #totals_dict = fetch_totals(session, candidate_id, args.cycle)


    # ── Step 1: fetch filings with debug save option ─────────────────────────
    committee_id = bioguide_map[args.bioguide_id]["committee_id"]
    if len(committee_id) > 1:
        print(f"Candidate has multiple committees for cycle {args.cycle}, using first committee: {committee_id[0]}")
        committee_id = committee_id[0]
    else:
        committee_id = committee_id[0]
    filings_path = out_dir / f"filings_{committee_id}_{args.cycle}.json"

    if args.filings_raw:
        load_path = Path(args.filings_raw)
        print(f"\n=== Loading Filings from {load_path} ===")
        filings = json.loads(load_path.read_text(encoding="utf-8"))
        print(f"  Loaded {len(filings)} records.")
    else:
        filings = fetch_filings(session, committee_id, args.cycle)
        save_json(filings, filings_path, "filings")


    # ── Step 2: fetch CSV data from filings ────────────────────────────
    contribution_data = fetch_filing_csv(filings, args.cycle)
    contribution_data = dict(sorted(contribution_data.items(), key=lambda item: item[1], reverse=True)) #sort contribution data by amount, descending

    # ── Step 3: save contribution data────────────────────────────────
    contribution_data_path = out_dir / f"{committee_id}_contribution_data.json"
    #save_json([totals_dict, contribution_data], contribution_data_path, "contribution data from filings")
    save_json(contribution_data, contribution_data_path, "contribution data from filings")

    print("\n=== Done ===")
    print(f"  results          : {contribution_data_path}")


if __name__ == "__main__":
    main2()