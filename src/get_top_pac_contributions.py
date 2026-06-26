import argparse
import csv
from io import StringIO
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler
import re
import os


import requests

BASE_URL = "https://api.open.fec.gov"

debug = False

# ---------------------------------------------------------------------------
# Name matching
#
# We compare donor names to decide "same person / same family" at an address.
# Plain edit distance (fuzz.ratio) has two structural blind spots for names:
#   1. nicknames  -> BOB/ROBERT, BILL/WILLIAM score ~0 but are the same person
#   2. it is over-lenient on short names at a low threshold
# So for *person* names we use Jaro-Winkler (built for name record-linkage:
# prefix-weighted, transposition-aware) plus a nickname lookup. Company/PAC
# strings keep using fuzz.ratio.
# ---------------------------------------------------------------------------

# Score (0-100) at/above which two person names are treated as the same name.
# Jaro-Winkler runs higher than the old fuzz.ratio, so this is stricter than the
# previous literal 50. Tune against real output if you see split/merged dupes.
NAME_SIM_THRESHOLD = 85


def _load_nickname_variants():
    """
    Load the nickname/diminutive lookup (resources/data/nicknames.csv, format
    `name1,relationship,name2`) into an UPPERCASE adjacency map: each name -> set
    of directly-linked variants, both directions.

    Adjacency is kept DIRECT (not transitive) on purpose: 'bill' links to both
    ROBERT and WILLIAM, but ROBERT and WILLIAM must NOT collapse into each other.
    Returns {} if the file is missing so matching degrades to Jaro-Winkler only.
    """
    path = Path(__file__).resolve().parent.parent / "resources" / "data" / "nicknames.csv"
    variants: dict[str, set[str]] = {}
    try:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for parts in reader:
                if len(parts) < 3:
                    continue
                a = parts[0].strip().upper()
                b = parts[2].strip().upper()
                if not a or not b or a == b:
                    continue
                variants.setdefault(a, set()).add(b)
                variants.setdefault(b, set()).add(a)
    except FileNotFoundError:
        print(f"WARNING: nickname lookup not found at {path}; "
              f"falling back to Jaro-Winkler only.")
    return variants


NICKNAME_VARIANTS = _load_nickname_variants()


def are_nickname_variants(a, b):
    """True if a and b are directly linked as formal-name/nickname (either order)."""
    return b.upper() in NICKNAME_VARIANTS.get(a.upper(), ())


def name_similarity(a, b, use_nicknames=True):
    """
    Similarity score (0-100) between two person names. Exact match or a known
    nickname pair scores 100; otherwise Jaro-Winkler. Pass use_nicknames=False
    for last names (where nickname expansion does not apply).
    """
    a = a.upper()
    b = b.upper()
    if a == b:
        return 100.0
    if use_nicknames and are_nickname_variants(a, b):
        return 100.0
    return JaroWinkler.normalized_similarity(a, b) * 100


# Vowels (incl. Y) used to tell a run-together initials token ("WJ") from a real
# short name ("ED", "AL", "JO"), which almost always contain a vowel.
_VOWELS = set("AEIOUY")


def _initials_form(name):
    """
    If `name` is written as initials, return its ordered initials; else None.
      'J.'    -> ['J']
      'W. J.' -> ['W', 'J']
      'WJ'    -> ['W', 'J']   (short, all-consonant single token)
      'JOHN'  -> None         (a real name, not initials)
    """
    tokens = [t for t in re.split(r"[\s.]+", name.upper()) if t]
    if not tokens:
        return None
    if all(len(t) == 1 for t in tokens):
        return tokens
    if len(tokens) == 1 and 2 <= len(tokens[0]) <= 3 and not (set(tokens[0]) & _VOWELS):
        return list(tokens[0])
    return None


def _leading_initials(name):
    """Ordered first letter of each token: 'JOHN T' -> ['J','T'], 'JOHN' -> ['J']."""
    return [t[0] for t in re.split(r"[\s.]+", name.upper()) if t]


def initials_compatible(a, b):
    """
    True if `a` and `b` could be the same person via initial abbreviation, with
    their ordered initials agreeing on the overlap (so 'J. T.' matches 'JOHN' but
    not 'JOHN R'). Only fires when at least one side is written as initials, so two
    real names ('JOHN' vs 'JAMES') never match here.
    """
    if a.upper() == b.upper():
        return False  # identical -> let exact-match logic handle it
    ia, ib = _initials_form(a), _initials_form(b)
    if ia is None and ib is None:
        return False  # both real names; not an abbreviation case
    seq_a = ia if ia is not None else _leading_initials(a)
    seq_b = ib if ib is not None else _leading_initials(b)
    n = min(len(seq_a), len(seq_b))
    if n == 0:
        return False
    return all(seq_a[k] == seq_b[k] for k in range(n))


def _name_tokens(name):
    """Split a name into uppercase word tokens: 'Robert P.' -> ['ROBERT', 'P']."""
    return [t for t in re.split(r"[\s.]+", name.upper()) if t]


def _token_match(x, y):
    """Two name tokens are compatible if equal, one is the other's initial
    ('P' ~ 'PAUL'), or they are nickname variants ('BOB' ~ 'ROBERT')."""
    if x == y:
        return True
    if len(x) == 1 and x == y[0]:
        return True
    if len(y) == 1 and y == x[0]:
        return True
    return are_nickname_variants(x, y)


def names_same_person(a, b):
    """
    True if two first-name strings plausibly denote the same person, allowing an
    optional / abbreviated MIDDLE name or initial but requiring the given name to
    match and any provided middle tokens to AGREE on the overlap:
      'ROBERT'   ~ 'ROBERT P'    -> True   (middle initial on one side only)
      'ROBERT P' ~ 'ROBERT PAUL' -> True   ('P' is the initial of 'PAUL')
      'BOB'      ~ 'ROBERT P'    -> True   (nickname given name + extra middle)
      'ROBERT P' ~ 'ROBERT K'    -> False  (middle initials conflict)
      'ROBERT'   ~ 'RICHARD'     -> False
    """
    ta, tb = _name_tokens(a), _name_tokens(b)
    if not ta or not tb:
        return False
    if not _token_match(ta[0], tb[0]):
        return False
    return all(_token_match(x, y) for x, y in zip(ta[1:], tb[1:]))

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
        'candidate_status': "C"
    }
    #        'is_active_candidate': "true",
    #        'incumbent_challenge': "I"

    return get_all_pages_numbered(session, f"/v1/candidates/search/", params, "house_candidates")



######################################################
# Step -1: get the bioguide name mapping
######################################################
def cross_reference(fec_data, bioguide_data, cycle):
    #'name', 'party', 'state'. if match, take "candidate_id" and "district_number"
    people_map = {}
    failed = []
    for bio_person in bioguide_data:
        bioname = convert_to_ascii(bio_person['name'])
        bioname_array = bioname.split(', ')
        bio_last_array = bioname_array[0].upper().replace("-", " ").replace("'", "").split(" ")
        bio_first_array = bioname_array[1].upper().replace("-", " ").replace("'", "").split(" ")
        
        appended_person = False
        
        for fec_person in fec_data:
            append_person = False
            state_match = False
            party_match = False
            name_match = False

            if STATE_NAME_TO_CODE.get(bio_person['state'], None) == fec_person['state']:
                state_match = True

            if fec_person.get('party') is None:
                party_match = True
            elif fec_person['party'].startswith("UN"):
                party_match = True
            elif bio_person['partyName'][0] == "D":
                if fec_person['party'][0]=="D": #D
                    party_match = True
            elif bio_person['partyName'][0] == "R":
                if fec_person['party'][0]=="R": #R
                    party_match = True
            else: #I
                if not fec_person['party'][0].startswith(("D", "R")):
                    party_match = True
            
            if fec_person.get('name') is None:
                continue

            name_array = fec_person['name'].split(', ')
            if len(name_array) == 1:
                #Typoed and didn't do the comma probably
                name_array = fec_person['name'].split(" ")

            fec_last_array = name_array[0].upper().replace("-", " ").replace("'", "").split(" ")
            fec_first_array = name_array[1].upper().replace("-", " ").replace("'", "").split(" ")

            first_match = set(bio_first_array) & set(fec_first_array)
            last_match = set(bio_last_array) & set(fec_last_array)
            if first_match and last_match:
                name_match = True
            elif last_match:
                if bio_last_array == fec_last_array:
                    if state_match and party_match:
                        name_match = True
                            
            if name_match:
                if state_match and party_match:
                    append_person = True
                else:
                    print(f"Names matched but party and state didn't: {bioname}")
                    print(f"  - {bio_person['state']} {fec_person['state']} | {bio_person['partyName']} {fec_person['party']}")
                
            if append_person:
                appended_person = True
                #print(f"Matched {bioname} to {fec_person['name']}")
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
        if not appended_person:
            print(f"Could not find a match for {bio_person['name']} in FEC data. This person is "
                    "likely not running again or died.")
            failed.append(bio_person['bioguideID'])
        else:
            continue
    
    return people_map, failed


######################################################
# Step 0: probe the endpoint /v1/candidate/{candidate_id}/totals for totals
######################################################

def fetch_totals_for_election_year(session: requests.Session, candidate_id: str, election_yr: int) -> list:

    print(f"\n=== Getting totals for candidate {candidate_id} (election {election_yr}) ===")

    params = {
        "candidate_id": candidate_id,
        "election_full": True,
        "sort": "-candidate_election_year"
    }

    totals = get_first_page_numbered(session, f"/v1/candidate/{candidate_id}/totals/", params, "totals")
    most_recent_election = totals[0].get('candidate_election_year')

    if most_recent_election == election_yr:
        report = totals[0]
        print(f"Candidate {candidate_id} is up for election in {election_yr}")
    
    elif most_recent_election > election_yr:
        report = totals[1]
        print(f"Candidate {candidate_id} is not up for election in {election_yr}. Taking most previous in {report['candidate_election_year']}.")

    else:
        sys.exit(f"Candidate {candidate_id} is not rerunning in {election_yr}. Most recent run was {most_recent_election}")
    
    tot = {"election_year": report['candidate_election_year'],
        "pac_total": report['other_political_committee_contributions'],
        "ind_total": report['individual_contributions'],
        "net_contributions": report["net_contributions"],
        "total_in": report['receipts']
    }
    return tot



def fetch_totals(session: requests.Session, candidate_id: str, cycle: int) -> list:
    """
    WARNING: This endpoint aggregates everything from the given cycle.
    This means that if someone ran for special election AND the next election, 
    both of these things would happen in one cycle. Then this reports both cases,
    which we don't really want - we want to distinguish.

    Here is where my numbers differ:
        total: 
            - mine did not have grassroots. in order to incorporate grassroots i would 
            need to include [33] from the F3N/A row, that will have the grassroots info
            - mine can be split for special. fec checks for anything reported (which can
            include old elections including specials) whereas I can break up by target 
            election. Note that the grassroots will be imperfect since it applies to the whole
            reporting period, regardless of how many races are included in the reporting period.

        pac total: 
            - fec determines pac total by summing anything in SA11C. I determine PAC total by
            summing anything in SA* that has "PAC" in the name. My way would include bundling PACs.
            This is still up for debate, but we decided PAC total should include only direct PAC
            contributions so that we don't make candidates look worse than they are. PAC bundling
            is currently contributing to the top donors, just not PAC totals. 
            - to replicate FEC, we could sum just over SA11C regardless of row[5].

    """
    
    print(f"\n=== Getting totals for candidate {candidate_id} (cycle {cycle}) ===")
    params = {
        "candidate_id": candidate_id,
        "cycle": cycle
    }
    totals = get_first_page_numbered(session, f"/v1/candidate/{candidate_id}/totals/", params, "totals")[0]
    tot = {"pac_total": totals['other_political_committee_contributions'],
        "ind_total": totals['individual_contributions'],
        "net_contributions": totals["net_contributions"],
        "total_in": totals['receipts']
    }
    return tot
    

######################################################
# Step 1: probe the endpoint /v1/committee/{committee_id}/filings
######################################################

def fetch_filings_by_cycle(session: requests.Session, committee_id: str, cycle: int) -> list:
    print(f"\n=== Retrieveing all filings for {committee_id} (cycle {cycle}) ===")
    params = {
        "committee_id": committee_id,
        "cycle": cycle,
        "sort": "-receipt_date",
        "per_page": 100,
        "form_type": "F3"
    }
    return get_all_pages_numbered(session, f"/v1/committee/{committee_id}/filings/", params, "filings")

def fetch_filings(session: requests.Session, committee_id: str) -> list:
    print(f"\n=== Retrieveing all filings for {committee_id}")
    params = {
        "committee_id": committee_id,
        "sort": "-coverage_end_date",
        "per_page": 100,
        "form_type": "F3"
    }
    filings = get_all_pages_numbered(session, f"/v1/committee/{committee_id}/filings/", params, "filings")

    # Process newest-PERIOD first so the first time we encounter a donor carries
    # their latest cycle-to-date aggregate (that's what the "see them once" logic
    # in factor_in_family_for_contribution_once relies on).
    #
    # coverage_end_date is the correct sort axis, NOT receipt_date: an amendment to
    # an early report is *filed* recently (recent receipt_date) but *covers* an early
    # period (early coverage_end_date). Sorting by receipt_date would process that
    # amendment first and lock the donor in at their early/smaller aggregate, causing
    # the later-period report with their true total to be skipped -> undercount.
    # receipt_date is the tiebreaker so the newest amendment of a given period still
    # comes before its superseded original (which the amendment_chain skip then drops).
    filings.sort(
        key=lambda f: (f.get("coverage_end_date") or "", f.get("receipt_date") or ""),
        reverse=True,
    )
    return filings


def candidate_period_cycles(candidate_id, election_year):
    """
    The two-year FEC periods to roll up for one election. A Senate seat (candidate_id
    starts with 'S') is a 6-year campaign spanning THREE two-year cycles; a House seat
    ('H') -- and anything else -- is a single cycle.

    This matters because the FEC contribution_aggregate (row[21]) resets every two-year
    period, so a donor's full election total is the SUM of their per-period aggregates.
    We process each period separately and add the results.
    """
    if str(candidate_id).upper().startswith("S"):
        return [election_year - 4, election_year - 2, election_year]
    return [election_year]


######################################################
# Step 2: now that we have the endpoint, go through each filing (skip if already saw amended),
# and get the csv
######################################################
def fetch_filing_csv(filings_report, cycle, generated_outputs):
    refund_data = {}
    pac_data = {}
    individual_data = {}
    skip_list = []

    # The period being processed (all filings in this batch share the same two-year
    # cycle); used to name the per-period debug dump so periods don't overwrite each
    # other. Falls back to the election year if the batch is empty.
    period_label = filings_report[0].get("cycle", cycle) if filings_report else cycle

    if debug:
        temp_aggregate = []
    for filing in filings_report:

        if filing['csv_url'] is None:
            continue

        #only get for years we care about
        if filing['cycle'] > cycle:
            continue

        # print form_type, document_description, and report_type
        if filing['file_number'] in skip_list:
            #print(f"Skipping filing {filing['file_number']} since we already looked at an amended version of it")
            continue
        #Skip the original if we already looked at the amended version of the same report
        if filing['amendment_indicator'] == "A":
            skip_list.extend(filing['amendment_chain'][:-1]) #add all previous versions of the report to skip list
            #print(f"Skip this one {len(filing['amendment_chain'])-1} times")

        print(f"==={filing['report_type_full']} {filing['report_year']}===")
        csv_data = get_csv_data(filing['csv_url'], filing['form_type'], cycle, refund_data, individual_data, pac_data)
        if csv_data is None:
            #This filing had no rows for the target election (or wasn't usable). Skip it
            #rather than break: with per-period processing we must scan every filing in
            #the period, and an early report with no target-designated rows isn't the end.
            continue

        if debug:
            #TODO DELETE THIS, TEMPORARY: dumping everythign into csv_data for now
            #temp_aggregate.append([filing['form_type'], filing['document_description'], filing['csv_url']])
            if csv_data is not None:
                temp_aggregate.extend(csv_data)

    if debug:
        #TEMPORARY SAVE AGGREGATE CSV DATA TO DEBUG FILE (one per period cycle)
        temp_aggregate_path = Path(generated_outputs) / f"temp_aggregate_{period_label}.csv"
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
    

def merge_families(individual_data):
    """
    Collapse the per-person records produced by match_or_add_person into family
    HOUSEHOLDS, reusing the family-merge heuristics from the original
    factor_in_family_for_contribution_once (same-person merging is already done upstream,
    so it is skipped here).

    For people sharing a last name (or a hyphenated component of it) at one address:
      * an unemployed member's contribution is folded into the household,
      * an employed member is folded into an otherwise-unemployed household (taking its
        employer) -- and unlike the original, their contribution IS added (bug fix),
      * a couple at the SAME employer is folded together (longer spelling kept),
      * a couple at DIFFERENT employers is kept as separate households.

    Each person's employer is their latest-date COMPANIES[0]; people with a job history
    (len(COMPANIES) > 1) are logged. Returns a NEW {address: [household, ...]} mapping of
    households shaped { LAST_NAME, NAMES, COMPANIES, CONTRIBUTIONS } for consolidation.
    """
    def related(last_name, h_last):
        if last_name == h_last:
            return True
        if "-" in last_name:
            return any(part and part in h_last for part in last_name.split("-"))
        return False

    merged = {}
    for address, persons in individual_data.items():
        households = []
        for person in persons:
            last_name = person["LAST_NAME"]
            companies = person["COMPANIES"]
            if len(companies) > 1:
                print(f"Person with multiple jobs at {address}: {person['NAMES']} "
                      f"{companies} -> using latest '{companies[0]}'.")
            job = companies[0] if companies else ""   # latest-date employer
            contribution = person["CONTRIBUTIONS"]
            names = list(person["NAMES"])

            placed = False
            for h in households:
                if not related(last_name, h["LAST_NAME"]):
                    continue
                if not job:
                    # incoming unemployed -> fold into the household
                    h["CONTRIBUTIONS"] += contribution
                    h["NAMES"].extend(names)
                    placed = True
                    break
                if not h["COMPANIES"]:
                    # household was unemployed -> take this earner's employer (and, unlike
                    # the original, add their contribution too).
                    h["COMPANIES"] = [job]
                    h["CONTRIBUTIONS"] += contribution
                    h["NAMES"].extend(names)
                    placed = True
                    break
                if same_company(job, h["COMPANIES"][0]):
                    # couple at the same employer -> fold; keep the longer spelling.
                    if len(job) > len(h["COMPANIES"][0]):
                        h["COMPANIES"][0] = job
                    h["CONTRIBUTIONS"] += contribution
                    h["NAMES"].extend(names)
                    placed = True
                    break
                # employed at a DIFFERENT employer -> keep separate; try next household.
            if not placed:
                households.append({
                    "LAST_NAME": last_name,
                    "NAMES": names,
                    "COMPANIES": [job] if job else [],
                    "CONTRIBUTIONS": contribution,
                })
        merged[address] = households
    return merged


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
    # ── Step 1: collapse each person's signed total (SA aggregate + any net refund) ──
    # match_or_add_person stored the most-recent-dated SA aggregate in CONTRIBUTION and any
    # leftover refund (for people we never saw an SA from) in SB_REFUND; fold them into the
    # single CONTRIBUTIONS field the family-merge + consolidation logic works with.
    for address, persons in individual_data.items():
        for person in persons:
            person["CONTRIBUTIONS"] = (person.get("CONTRIBUTION") or 0) + (person.get("SB_REFUND") or 0)
            if person["CONTRIBUTIONS"] < 0:
                print(f"NOTE: net-negative contribution for {person['NAMES']} "
                      f"{person['LAST_NAME']} at {address}: ${person['CONTRIBUTIONS']:,.2f} "
                      f"(aggregate {person.get('CONTRIBUTION')}, refund {person.get('SB_REFUND')}).")

    # ── Step 2: merge family members at each address into households ─────────────────
    individual_data = merge_families(individual_data)

    final_data = {}

    # ── Reconciliation bookkeeping ────────────────────────────────────────────
    # individual_input_total  = every dollar we stored across all households
    #                           (i.e. what the "count each donor once" logic decided
    #                            to keep). This is the money going INTO consolidation.
    # individual_output_total = the dollars we actually write into final_data below.
    # If these drift apart, money was dropped while bucketing households into companies.
    individual_input_total = sum(
        household["CONTRIBUTIONS"]
        for households in individual_data.values()
        for household in households
    )
    individual_output_total = 0.0

    #individual data, merge families
    print("++++++++++++++++ LOOKING AT INDIVIDUAL DATA FIRST +++++++++++++++++")
    for k,v in individual_data.items():
        #if len(v) > 1:
            #print(f"{len(v)} people found at {k}")
            #print(list(v))

        for household in v:
            # merge_families normalizes every household to <= 1 company (an unemployed
            # household -> [], otherwise the latest-date employer), so we only handle the
            # no-company and single-company cases here.
            if len(household["COMPANIES"]) == 0:
                #print("All members of household undisclosed.")
                final_data["Undisclosed"] = final_data.get("Undisclosed", 0) + household['CONTRIBUTIONS']
                individual_output_total += household["CONTRIBUTIONS"]
            else:
                #Individual person
                company = household["COMPANIES"][0]
                final_data[company] = final_data.get(company, 0) + household["CONTRIBUTIONS"]
                individual_output_total += household["CONTRIBUTIONS"]


    print("++++++++++++++++ DONE LOOKING AT INDIVIDUAL DATA  +++++++++++++++++")

    # Reconcile what we stored vs what made it into final_data.
    drift = individual_input_total - individual_output_total
    if abs(drift) > 0.01:
        print(f"!!! RECONCILIATION: ${drift:,.2f} of individual contributions were NOT "
              f"carried into final_data (stored ${individual_input_total:,.2f} vs "
              f"bucketed ${individual_output_total:,.2f}).")
    else:
        print(f"[OK] Reconciliation: all ${individual_input_total:,.2f} of individual "
              f"contributions accounted for.")

    # ── Collapse spelling variants by canonical name ──────────────────────────
    # 'Google', 'Google Inc', 'GOOGLE LLC' share one canonical key -> one bucket.
    # Exact and O(n), so the fuzzy pass below only has to handle typos and acronyms.
    # Display name = the spelling that brought in the most money for that company.
    canon_total, canon_display, canon_best = {}, {}, {}
    for original, amt in final_data.items():
        key = canonical_company(original)
        canon_total[key] = canon_total.get(key, 0) + amt
        if amt > canon_best.get(key, float("-inf")):
            canon_best[key] = amt
            canon_display[key] = original
    collapsed = len(final_data) - len(canon_total)
    if collapsed:
        print(f"Canonical merge collapsed {collapsed} spelling variant(s) "
              f"({len(final_data)} -> {len(canon_total)} company buckets).")
    final_data = {canon_display[key]: total for key, total in canon_total.items()}

    print("++++++++++++++++ NOW MERGING COMPANY DATA +++++++++++++++++")

    #go through companies and merge if score is high, merge on higher contribution amount.
    all_companies = list(final_data)

    # This loop is O(n^2) over every company (n can be thousands), so anything done
    # per-pair is multiplied tens of millions of times. Precompute the acronym data
    # ONCE per company here; the inner loop then only does cheap dict/set lookups
    # (no regex), which is what kept the merge fast before the acronym feature.
    _acro_token = {c: _is_acronym_token(c) for c in all_companies}     # c is a short token?
    _compact = {c: re.sub(r"[^A-Za-z0-9]+", "", c).upper() for c in all_companies}
    _ntokens = {c: sum(1 for w in re.split(r"[^A-Za-z0-9]+", c) if w) for c in all_companies}
    _acro_sets = {c: _company_acronyms(c) for c in all_companies}

    # Block by leading character. Two companies only merge here when their uppercased
    # strings are near-identical (>90 / ==100) or one is the other's acronym -- both
    # cases share a first letter -- so cross-block pairs never merge and are skipped.
    # This turns one ~33M-pair sweep into many small per-letter ones (~18x fewer pairs
    # for a large committee). 'companies' is rebound to each block so the merge body
    # below is byte-for-byte the same as the flat version.
    blocks = defaultdict(list)
    for c in all_companies:
        blocks[c[:1].upper()].append(c)

    for companies in blocks.values():
        for i in range(len(companies)):
            for j in range(i+1, len(companies)):
                if companies[i] in companies[j]:
                    #print(f"Found {companies[i]} in {companies[j]}")
                    pass
                elif companies[j] in companies[i]:
                    #print(f"Found {companies[j]} in {companies[i]}")
                    pass
                else:
                    ci, cj = companies[i], companies[j]
                    company1 = ci.upper()
                    company2 = cj.upper()
                    similarity_score = fuzz.ratio(company1, company2)
                    # Acronym/abbreviation pairs ('HPU' ~ 'High Point University') score
                    # ~0 on fuzz.ratio, so force a merge when one is the other's acronym.
                    # Only possible when one side is a short token and the other multi-word;
                    # the cheap _acro_token guard skips the set lookups for most pairs.
                    if (_acro_token[cj] and _ntokens[ci] >= 2 and _compact[cj] in _acro_sets[ci]) or \
                       (_acro_token[ci] and _ntokens[cj] >= 2 and _compact[ci] in _acro_sets[cj]):
                        similarity_score = 100
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
                            #print(f"{similarity_score:.2f}% similar: {companies[i]}, {companies[j]}. Going to merge them.")
                            if final_data[companies[i]] >= final_data[companies[j]]:
                                print(f"{companies[j]} => {companies[i]}")
                                final_data[companies[i]] += final_data[companies[j]]
                                final_data[companies[j]] = 0
                            else:
                                print(f"{companies[i]} => {companies[j]}")
                                final_data[companies[j]] += final_data[companies[i]]
                                final_data[companies[i]] = 0
                                break
                        else:
                            print(f"Close but skipped: {similarity_score:.2f}% similar: {companies[i]}, {companies[j]}")

    print("++++++++++++++++ DONE MERGING COMPANY DATA +++++++++++++++++")

    # The company-merge step only moves money between buckets (and zeroes the
    # emptied one), so the total must be unchanged. If it isn't, a merge branch
    # double-added or lost money.
    post_merge_total = sum(final_data.values())
    merge_drift = post_merge_total - individual_output_total
    if abs(merge_drift) > 0.01:
        print(f"!!! RECONCILIATION: company-merge changed the individual total by "
              f"${merge_drift:,.2f} (before ${individual_output_total:,.2f}, "
              f"after ${post_merge_total:,.2f}).")

    print("\n++++++++++++++++ NOW LOOKING AT PAC DATA +++++++++++++++++")


    #non-IND. PACs will be dict, everything else just blind add.
    for k,v in pac_data.items():
        if isinstance(v, dict): #PAC data.
            if (len(v) > 2):
                print("So many PACs under the same committee_id!", k, v)
            elif (len(v)==2):
                str1 = list(v)[0]
                str2 = list(v)[1]
                merge_pacs = pac_name_edit(str1, str2)
                if merge_pacs:
                    final_data[str1] = final_data.get(str1, 0) + v[str1] + v[str2]
                else:
                    for pac_name, contribution in v.items():
                        final_data[pac_name] = final_data.get(pac_name, 0) + contribution
            else:
                for pac_name, contribution in v.items():
                    final_data[pac_name] = final_data.get(pac_name, 0) + contribution

        else: #ORG data.
            #Accumulate (a refund stored as a negative v must subtract from any existing
            #total for this key, not overwrite it).
            final_data[k] = final_data.get(k, 0) + v
            continue

    print("\n++++++++++++++++ DONE LOOKING AT PAC DATA +++++++++++++++++")

    # Drop emptied buckets: the company-merge zeroes absorbed companies but leaves
    # the keys behind, which otherwise clutter the output as "Company": 0.
    final_data = {k: v for k, v in final_data.items() if v}

    return final_data


def pac_name_edit(pac1, pac2):
    """
    How to edit PAC names:
    If they both have (), convert to ()
    If one has (), convert to () and abbreviate the other
    Abbreviate both

    Increase score requirement when abbreviating
    """
    similarity_score = fuzz.ratio(pac1, pac2)
    if similarity_score > 80:
        print(f"{pac1} {pac2} merged.")
        return True
    

    if "(" in pac1:
        pac1_match = re.search(r"([^\()]+)\(([^\)]+)\)", pac1)
        pac1_noparen = pac1_match.group(1)
        pac1_abbr = pac1_match.group(2)
        if "(" in pac2:
            pac2_match = re.search(r"([^\()]+)\(([^\)]+)\)", pac2)
            pac2_noparen = pac2_match.group(1)
            pac2_abbr = pac2_match.group(2)
        else:
            pac2_noparen = pac2
            pac2 = pac2.replace("-", " ")
            pac2_abbr = "".join(word[0].upper() for word in pac2.split())

    elif "(" in pac2:
        pac2_match = re.search(r"([^\()]+)\(([^\)]+)\)", pac2)
        pac2_noparen = pac2_match.group(1)
        pac2_abbr = pac2_match.group(2)

        pac1_noparen = pac1
        pac1 = pac1.replace("-", " ")
        pac1_abbr = "".join(word[0].upper() for word in pac1.split())

    else:
        pac1_noparen = pac1
        pac1 = pac1.replace("-", " ")
        pac1_abbr = "".join(word[0].upper() for word in pac1.split())

        pac2_noparen = pac2
        pac2 = pac2.replace("-", " ")
        pac2_abbr = "".join(word[0].upper() for word in pac2.split())


    similarity_score = fuzz.ratio(pac1_noparen, pac2_noparen)
    if similarity_score > 75:
        print(f"{pac1_noparen} {pac2_noparen} merged.")
        return True
    else:
        print(f"{pac1_noparen}|{pac2_noparen} not merged: {similarity_score:.2f}%")
    
    similarity_score = fuzz.ratio(pac1_abbr, pac2_abbr)
    if similarity_score > 90:
        print(f"{pac1_abbr} {pac2_abbr} merged.")
        return True
    else:
        print(f"{pac1_abbr}|{pac2_abbr} too different: {similarity_score:.2f}%.")
        return False


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
            csv_for_cycle = keep_only_current_contributions(csv_list, cycle)
            if csv_for_cycle is None:
                print(f"No {cycle} donations found. Done.")
                return None
            
            print(f"=== Processing F3 {url} ===")

            process_form_no_refund(csv_for_cycle, individual_data, pac_data, cycle)

            return csv_for_cycle
        
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


def keep_only_current_contributions(csv_list, cycle):
    """
    Takes in a csv F3. If there is no mention of the current election, return False
    """

    clean_csv = []
    clean = False

    for row in csv_list:
        if row[0].upper() in ["HDR", "F6A", "F6N", "TEXT"]:
            clean_csv.append(row)
        elif row[0].upper() in ['F3N', 'F3A', 'F3S']:
            #need to get contributions, already factors in refunds
            #net_contributions = float(row[25])
            #grassroots_contributions = float(row[33])
            #pac_data['CAMPAIGN TOTAL'] = pac_data.get('CAMPAIGN TOTAL', 0) + net_contributions
            clean_csv.append(row)
            continue
        elif str(cycle) in row[17] or "Special" in row[18]:
            clean_csv.append(row)
            clean = True

        #elif str(cycle) in row[17] or "Special" in row[18]: #only for current cycle

    if clean:
        return clean_csv
    else:
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
        if str(cycle) in row[17] or "Special" in row[18]: #only for current cycle
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
                #print("Not bundled, just IND moving money around. Removing.")
                refund_data.pop(refund_code)
                return contribution
            else:
                return contribution

    else:
        
        #check if it was bundled, regardless of [5]
        refund_code = row[3] if row[3] else row[2]
        refund_code = f"temp_{refund_code}"
        if refund_code in refund_data:
            #print(f"Found bundle. {row[6]}")
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

def apply_signed(store, key, delta):
    """
    Fold a SIGNED amount into store[key] under the contribution/refund netting rules.
    `delta` is +aggregate for a contribution (SA11) and -refund for a refund (SB20).

      key absent      -> store[key] = delta     (first time we encounter the entity)
      store[key] < 0  -> store[key] += delta    (a loaded refund: net the new amount in --
                                                 a later contribution, or another refund)
      store[key] >= 0 -> unchanged              (already counted; row[21] is the running
                                                 cumulative total, so we don't re-add/sum)
    """
    cur = store.get(key)
    if cur is None:
        store[key] = delta
        #print(f"Added: {key}: {delta}")
    elif isinstance(cur, dict):
        # Structural collision: this key holds a committee bucket, not a scalar total, so
        # the scalar netting below would crash ('dict < int'). The root cause is keying a
        # name and a committee bucket to the same slot; warn rather than abort the run.
        print(f"WARNING: apply_signed skipped {key!r} (delta {delta}): key holds a "
              f"committee bucket, not a scalar total.")
    elif cur < 0:
        store[key] = cur + delta
        #print(f"Updated {key}: {cur} -> {cur + delta}")

    # cur >= 0: already counted -> do nothing


def refund_for_pac(row, pac_data, refund_amount):
    """
    SB20 refund for a PAC / ORG / COM. Net the refund into wherever the entity already
    lives -- or, if we have not seen them yet, load it as a pending negative -- using
    the same signed-netting rule as contributions (apply_signed with a negative delta).
    """
    if row[26] != "":
        #this might not ever be true for SB20C, looks like it might be in [6] but keeping jic
        name = row[26].upper().replace("POLITICAL ACTION COMMITTEE", "PAC")
    elif row[6] != "":
        name = row[6].upper().replace("POLITICAL ACTION COMMITTEE", "PAC")
    else:
        print(f"Missing name for SB20 refund, skipping.")
        return

    if row[24].startswith("C"):
        committee_id = row[24]  # SB20 committee_id column (SA11 uses 25)
    elif row[25].startswith("C"):
        committee_id = row[25]
    else:
        # No real committee code -> treat as an ORG entry keyed by NAME at the top level,
        # exactly like the ORG contribution path (apply_signed(pac_data, name, ...)).
        # Using row[6] as the committee_id here previously created a DICT under a name key,
        # which never netted against the scalar name-keyed contribution AND crashed
        # apply_signed later with 'dict < int' when that name was hit as a top-level value.
        if row[5].upper() in ["COM", "ORG"]:
            #COM/ORG doesn't have committee id
            committee_id = None
        else:
            print(f"Could not find committee_id for {name} ({row[5]}); keying refund by name at top level.")
            committee_id = None
    delta = -refund_amount

    # Net into the existing entry wherever it lives: committee-keyed under its own id,
    # then name-keyed (a float org total), then any committee bucket holding the name.
    if committee_id and isinstance(pac_data.get(committee_id), dict) and name in pac_data[committee_id]:
        apply_signed(pac_data[committee_id], name, delta)
        return
    if isinstance(pac_data.get(name), (int, float)):
        apply_signed(pac_data, name, delta)
        return
    for entry in pac_data.values():
        if isinstance(entry, dict) and name in entry:
            apply_signed(entry, name, delta)
            return

    # Not seen anywhere -> load a pending refund (negative), to be netted when (if) we
    # reach their contribution in an older filing of the same period.
    print(f"No previous data found for {name}. Loading pending refund {delta}")
    if committee_id:
        apply_signed(pac_data.setdefault(committee_id, {}), name, delta)
    else:
        apply_signed(pac_data, name, delta)


def check_row_format(row):
    """
    Validate that an SA11*/SA12/SB20* row has the columns we rely on, in the shape we
    expect, before process_form_no_refund consumes it.

    Returns True if the row is well-formed and should be processed; False if it should be
    skipped -- either a known no-op (an SA11/SA12 with an empty aggregate row[21], which
    is just money moving around) or a malformed row (a warning is printed so the bad row
    is visible rather than silently miscounted or crashing a later float() call).

    Column expectations (per row type):
      17  cycle, [PGS]####            18  empty or any string (vacuous, not checked)
      19  8 digits (date)             20  contribution/refund, float-convertible
      21  aggregate, float (SA11/12)  25/24  C######## or empty (committee id)
      26  name string (fallback 6)
    """
    form = row[0].upper() if row else ""

    def col(i):
        return row[i] if i < len(row) else ""

    def is_cycle(s):
        return bool(re.fullmatch(r"[PGSO]\d{4}", s))

    def is_8_digits(s):
        return bool(re.fullmatch(r"\d{8}", s))

    def is_float(s):
        try:
            float(s)
            return True
        except (TypeError, ValueError):
            return False

    def is_committee_or_empty(s):
        return s == "" or bool(re.fullmatch(r"C\d{8}", s))

    problems = []

    if form == "SA11D":
        return True #skip SA11D, but do other SA11s
    
    if "SA11" in form or "SA12" in form:
        # Shared by IND and non-IND (cols 17, 19, 20).
        if not is_cycle(col(17)):
            problems.append(f"col17 (cycle) not [PGSO]####: {col(17)!r}")
        if not is_8_digits(col(19)):
            problems.append(f"col19 (date) not 8 digits: {col(19)!r}")
        if not is_float(col(20)):
            problems.append(f"col20 (contribution) not float-convertible: {col(20)!r}")

        # Aggregate (col 21): empty -> money moving around, skip (not an error).
        if col(21) == "":
            print("WARNING: No aggregate found.")
            return False
        if not is_float(col(21)):
            problems.append(f"col21 (aggregate) not float-convertible: {col(21)!r}")

        # Non-IND adds committee id + name fields (cols 25, 26 / fallback 6).
        if col(5) != "IND":
            if not is_committee_or_empty(col(25)):
                problems.append(f"col25 (committee_id) not C######## or empty: {col(25)!r}")
            if not col(26) and not col(6):
                problems.append("name missing: neither col26 nor col6 is set")

    elif "SB20" in form:
        # Shared by IND and non-IND (cols 17, 19, 20). No aggregate (col 21) for refunds.
        if not is_cycle(col(17)):
            problems.append(f"col17 (cycle) not [PGS]####: {col(17)!r}")
        if not is_8_digits(col(19)):
            problems.append(f"col19 (date) not 8 digits: {col(19)!r}")
        if not is_float(col(20)):
            problems.append(f"col20 (refund) not float-convertible: {col(20)!r}")

        # Non-IND refund carries the committee id in col 24.
        if col(5) != "IND":
            if not is_committee_or_empty(col(24)):
                problems.append(f"col24 (committee_id) not C######## or empty: {col(24)!r}")

    if problems:
        print(f"WARNING: malformed {form} row [{col(5)}]: {'; '.join(problems)}")
        print(row)
        return False

    return True




def process_form_no_refund(csv_data, individual_data, pac_data, cycle):
    """
    ok so my current methodology sums everyone over their name.
    the problem is, someone could have donated 200 in grassroots, then gotten a refund for that 200 
    (which i won't have record of) and then donate more after that. then the -200 will have seemingly
    come out of nowhere. 

    also my actblue numbers aren't matching.

    so i think we should take row[21], keyed by our key_id that we have for SA11AI entries. 
    then we don't have to worry about sb* and it should have already accounted for grassroots and refunds.
    we'll need to keep the same factor_in_families methodology, but instead it should be 
    "if we've seen this person already, do not add their contribution" because we already hve their totals.

    also, i'm only catching these people because they requested refunds. but there are probably
    so many more people who didn't request refunds that have +$200 or something to their totals
    that i'm missing because they weren't itemized yet!
    """

    form_version = csv_data[0][2]
    if form_version not in ["8.5", "8.4", "8.3"]:
        print(f"Unsupported form version: form_version")
        return
    

    for row in csv_data: 
        if row[0].upper() in ["HDR", "F6A", "F6N", "TEXT", "F3S"]:
            continue
        elif row[0].upper() in ['F3N', 'F3A']:
            #need to get contributions, already factors in refunds
            net_contributions = float(row[25])
            grassroots_contributions = float(row[33])
            #pac_contributions = float(row[73])
            pac_contributions = float(row[36])
            print(f"Net contributions: {net_contributions}")
            print(f"PAC contributions: {pac_contributions}")
            #pac_data['CAMPAIGN TOTAL'] = pac_data.get('CAMPAIGN TOTAL', 0) + net_contributions
            continue

        row_ok = check_row_format(row)
        if not row_ok:
            continue

        if str(cycle) not in row[17] and "Special" not in row[18]: #only for current cycle
            continue
        
        if row[0].upper() == "SA11AI" or row[0].upper() == "SA11C" or row[0].upper() == "SA12": #itemized individual contributions
            contribution = float(row[21]) #aggregate.

            if row[5] == "IND":
                #SA aggregate row[21] as of contribution_date row[19]; matcher keeps the
                #most-recent-dated aggregate per person.
                match_or_add_person(row, individual_data, contribution, row[19])
            else:
                if row[26] != "":
                    #name = re.sub(re.escape("political action committee"), "PAC", row[26], flags=re.IGNORECASE)
                    name = row[26].upper().replace("POLITICAL ACTION COMMITTEE", "PAC")
                elif row[6] != "":
                    name = row[6].upper().replace("POLITICAL ACTION COMMITTEE", "PAC")    
                else:
                    print(f"Missing name for SA11 contribution {row}, skipping.")
                
                #row[21] is the cumulative cycle-to-date aggregate (for a conduit
                #like ActBlue/WinRed it is the running CONDUIT TOTAL repeated on every
                #earmark row), so we keep one value (apply_signed: set once, never sum;
                #but net in any pending refund loaded earlier).
                if row[25] == "": #no committee ID -> merge on name (ORG/COM)
                    apply_signed(pac_data, name, contribution)
                else: #committee id present -> merge on committee_id + name
                    apply_signed(pac_data.setdefault(row[25], {}), name, contribution)
        elif row[0].upper() == "SA11B":
            if row[21] == '':
                print(f"Row formatted weird: {row}")
                contribution = float(row[20])
            else:
                contribution = float(row[21]) #aggregate
            name = row[26].upper() if row[26] else row[6].upper()
            committee_id = row[25]
            if committee_id == "":
                    print("Missing committee_id in SA11B party donation", name)
            else:
                apply_signed(pac_data.setdefault(committee_id, {}), name, contribution)
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
        elif row[0].upper() == "SB20A":
            #if the last thing they do is get refunded, this will be their most recent data. Add it only if 
            # we haven't seen their name
            if row[20] == '':
                print(f"Row formatted weird: {row}")
            else:
                contribution = float(row[20])

            if row[5] == "IND":
                #refund: pass the positive refund amount; the matcher accumulates it into
                #the person's SB_REFUND (only while they have no SA aggregate yet).
                match_or_add_person(row, individual_data, contribution, row[19])
            elif row[5] == "ORG":
                refund_for_pac(row, pac_data, contribution)
            elif row[5] == "COM":
                refund_for_pac(row, pac_data, contribution)
            else:
                print(f"Dont know what to do with non-IND SB20A: {row}")
                continue
            
        elif row[0].upper() == "SB20C": #refund data
            #if the last thing they do is get refunded, this will be their most recent data. Add it only if 
            # we haven't seen their name
            if row[20] == '':
                print(f"Row formatted weird: {row}")
            contribution = float(row[20])
            #print(f"SB20C using 20: {contribution}")


            if row[5] == "PAC":
                refund_for_pac(row, pac_data, contribution)
            elif row[5] == "ORG":
                refund_for_pac(row, pac_data, contribution)
            elif row[5] == "CCM":
                refund_for_pac(row, pac_data, contribution)
            elif row[5] == "COM":
                refund_for_pac(row, pac_data, contribution)
            else:
                print(f"Dont know what to do with non-PAC SB20C: {row}")
                continue
            
        elif row[0].upper() == "SB21": #other disbursements, money given to other committees. not contribution skip
            pass
        elif row[0].upper() == "SD10": #debts. skip
            pass
        else:
            print("Unknown row type in version 8.5:", row[0])



def replace_company_name(employer):
    partial_replacement = {
        "U of ": "University of ",
        "Univ.": "University",
        "Univ ": "University ",
        "Univeristy": "University",
        "Universityof ": "University of ",
        "Unversity": "University",
        "Pulbic ": "Public ",
        " Of ": " of ",
        "Nyu": "NYU",
        " And ": " & ",
        " and ": " & ",
        "U.S. ": "US ",
        "Calif ": "California",
        "Svc": "Service",
        "Sch ": "School ",
        ",": "",
        ".": "",
        "USA ": "US "
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


# Legal-entity suffixes stripped when forming a company's canonical key, so
# 'Google', 'Google Inc' and 'Google LLC' collapse together. Conservative list:
# only true entity types, nothing distinguishing (no GROUP/HOLDINGS/etc.).
_COMPANY_SUFFIXES = {"INC", "INCORPORATED", "LLC", "LLP", "LP", "LTD",
                     "CORP", "CORPORATION", "CO", "COMPANY", "PC", "PLLC"}


def canonical_company(name):
    """
    Canonical KEY for an employer/company name, used to merge spelling variants into
    one bucket: 'Google', 'Google Inc', 'GOOGLE LLC' and 'The Google Company' all map
    to 'GOOGLE'.

    Single source of truth for company-name normalization: it folds in
    replace_company_name (the alias map) and then uppercases, drops punctuation,
    normalizes 'AND' -> '&', and strips trailing legal-entity suffixes and a leading
    'The'. The returned key is for grouping only; a human-readable display name is
    chosen separately from the original spellings.
    """
    name = replace_company_name(name)                      # alias map + existing fixups
    s = re.sub(r"[^\w\s&]", " ", name.upper())             # punctuation -> space (keep &)
    tokens = ["&" if t == "AND" else t for t in s.split()]
    while len(tokens) > 1 and tokens[-1] in _COMPANY_SUFFIXES:
        tokens.pop()
    if len(tokens) > 1 and tokens[0] == "THE":
        tokens = tokens[1:]
    return " ".join(tokens)


# Words dropped when deriving a company acronym, so
# "University of North Carolina" -> "UNC", not "UONC".
_ACRONYM_STOPWORDS = {"OF", "THE", "AND", "FOR", "AT", "IN", "A", "AN", "&"}


def _company_acronyms(name):
    """
    Candidate acronyms for a company name, both keeping and dropping connector
    words, since real-world abbreviations do both:
      'University of North Carolina' -> {'UONC', 'UNC'}
      'Bank of America'              -> {'BOA',  'BA'}
      'High Point University'        -> {'HPU'}
    """
    words = [w for w in re.split(r"[^A-Za-z0-9]+", name.upper()) if w]
    if not words:
        return set()
    all_words = "".join(w[0] for w in words)
    significant = [w for w in words if w not in _ACRONYM_STOPWORDS]
    sig = "".join(w[0] for w in significant) if len(significant) >= 2 else all_words
    return {all_words, sig}


def _is_acronym_token(name):
    """A single 2-6 letter token that could be an acronym (HPU, UNC, NYU, IBM, GM)."""
    token = re.sub(r"[^A-Za-z0-9]", "", name)
    return token.isalpha() and 2 <= len(token) <= 6


def is_company_acronym_match(a, b):
    """
    True if one employer string is the acronym of the other, e.g.
    'Hpu' ~ 'High Point University', 'BOA' ~ 'Bank of America'.
    Order-independent. Pure acronym test (no fuzzy fallback).
    """
    a_tokens = [w for w in re.split(r"[^A-Za-z0-9]+", a) if w]
    b_tokens = [w for w in re.split(r"[^A-Za-z0-9]+", b) if w]
    a_compact = "".join(a_tokens).upper()
    b_compact = "".join(b_tokens).upper()
    if len(a_tokens) >= 2 and _is_acronym_token(b) and b_compact in _company_acronyms(a):
        return True
    if len(b_tokens) >= 2 and _is_acronym_token(a) and a_compact in _company_acronyms(b):
        return True
    return False


def same_company(a, b, threshold=88):
    """
    True if two employer strings denote the same organization: exact match,
    an acronym/abbreviation pair, or a near-typo (fuzz.ratio >= threshold).
    """
    a = (a or "").strip()
    b = (b or "").strip()
    if not a or not b:
        return False
    if a.upper() == b.upper():
        return True
    if is_company_acronym_match(a, b):
        return True
    return fuzz.ratio(a.upper(), b.upper()) >= threshold


def resolve_initial_abbreviation(persons, first_name, last_name, job, undisclosed):
    """
    Decide whether `first_name` is an initial-abbreviation of an existing household
    member (e.g. 'J.' for 'JOHN', 'WJ' for 'W. J.') and return that person-dict.

    Policy (from the user's choices):
      * consider only existing people with the SAME last name whose names are
        initials-compatible (ordered initials agree on the overlap);
      * collapse only when the match is UNAMBIGUOUS -- exactly one such person;
      * if several qualify, pick the one whose employer matches `job` (when exactly
        one does); otherwise return None so the caller keeps them separate.
    Returns the matching person-dict, or None.
    """
    candidates = []
    for p in persons:
        if p["LAST_NAME"] != last_name:
            continue
        if first_name in p["NAMES"]:
            return None  # exact name already present -> normal logic handles it
        if any(initials_compatible(first_name, nm) for nm in p["NAMES"]):
            candidates.append(p)

    if len(candidates) == 1:
        return candidates[0]

    if len(candidates) > 1 and job.upper() not in undisclosed:
        job_matches = [p for p in candidates
                       if any(same_company(job, c) for c in p["COMPANIES"])]
        if len(job_matches) == 1:
            return job_matches[0]

    return None  # ambiguous (or no abbreviation match) -> keep separate


def _factor_in_family_for_contribution(row, individual_data):
    """
    DEPRECATED
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
    if row[0].upper() == "SB20" or row[0].upper() == "SB20C":
        job = ''
    else:
        job = replace_company_name(row[23])
    contribution = float(row[20])
    name = (row[8]+row[7]).upper() #last name + first name, all uppercase to avoid case issues
    last_name = row[7].upper()
    new_person = True

    if job == "":
        print(f"No job found: {row}")

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





def factor_in_family_for_contribution_once(row, individual_data, contribution, debug=False):
    """
    Some contributions are made by family members, if they aren't working then
    we'll consider their contribution their spouse's contribution.
    Infer: same last name, same primary household.

    In this version, we want to only include the contributions once - do not overwrite.
    If the person is already in there, skip them.

    """

    undisclosed = ["NOT EMPLOYED", "SELF EMPLOYED", "SELF-EMPLOYED", "ME", "HOME", "SELF",
                   "N/A", "SELF- EMPLOYED", "UNEMPLOYED", "HOMEMAKER", "NOT-EMPLOYED",
                   "RETIRED", "NONE", "RETRIED"]
    # ADDRESS: [
    #   {LAST_NAME: GREEN
    #   NAMES: [person1, person2]
    #   COMPANIES: [role1, role2]
    #   CONTRIBUTIONS: contribution
    #   }
    # ]
    address = row[12]+row[14]+row[15]
    if row[0].upper().startswith("SB20"):
        job = ''
    else:
        job = replace_company_name(row[23])
    name = (row[8]+row[7]).upper() #last name + first name, all uppercase to avoid case issues
    first_name = row[8].upper() #last name + first name, all uppercase to avoid case issues
    middle_name = row[9].upper()
    last_name = row[7].upper()
    last_name = last_name.replace(" ", "").replace("'", "")
    new_person = True

    # Misfiled name fields: some donors put their middle initial in the first-name
    # slot [8] and their actual first name in the middle slot [9] (e.g. 'fellows,w.,jay'
    # = first 'W.', middle 'JAY'). Only when [8] is just an initial AND [9] is a real
    # name, treat [9] as the first name (prefer the fuller name) and keep [8] as an
    # alias so the donor is recognized as the same person.
    name_aliases = []
    if middle_name and _initials_form(first_name) is not None and _initials_form(middle_name) is None:
        #print(f"Swapped name fields: [8]='{first_name}' is an initial, [9]='{middle_name}' "
        #      f"is a name -> using '{middle_name}' as first name (alias '{first_name}')")
        name_aliases.append(first_name)
        first_name = middle_name

    #if no one lives here, add them
    #if this is SB20, then they refunded without a contribution in the same form.
    #then add -contribution
    if individual_data.get(address) is None:
        if row[0] == "SB20A":
            individual_data[address] = [{"LAST_NAME": last_name,
                                "NAMES": [first_name] + name_aliases,
                                "COMPANIES": [job] if job.upper() not in undisclosed else [],
                                "CONTRIBUTIONS": -contribution
                                }]
        else:
            individual_data[address] = [{"LAST_NAME": last_name,
                                "NAMES": [first_name] + name_aliases,
                                "COMPANIES": [job] if job.upper() not in undisclosed else [],
                                "CONTRIBUTIONS": contribution
                                }]


    #if someone already lives here, check if their last names match to combine
    else:

        # Logged only if this row is ultimately added as a genuinely new household
        # member, so re-processing the same donor (multiple filings / SB20 rows)
        # doesn't re-print it on every scan.
        two_jobs_note = None
        typo_note = None

        # Abbreviation pre-pass: an initialed first name ('J.' for 'JOHN', 'WJ' for
        # 'W. J.') is the SAME person, not a new family member. Resolve it first so it
        # isn't merged in as a separate contributor (which would double-count). Only
        # collapses when unambiguous (or disambiguated by employer) per policy.
        abbrev_match = resolve_initial_abbreviation(
            individual_data[address], first_name, last_name, job, undisclosed)
        if abbrev_match is not None:
            if debug:
                print(f"Initial abbreviation: {first_name} = {abbrev_match['NAMES']} "
                    f"{last_name} (same person, not double-counted)")
            abbrev_match["NAMES"].append(first_name)
            new_person = False

        for person in individual_data[address]:
            if not new_person:
                # resolved already (abbreviation pre-pass) -> stop scanning
                break

            #if last name is direct match - using this dict! not new person!
            #(exact equality; substring matching over-merged short names like "AN" in "MORGAN".
            # near-miss/typo last names are handled by the fuzzy branch in the else below.)
            if last_name == person["LAST_NAME"]:
                #print(f"Last name {last_name} match: check if {first_name} in {person["NAMES"]}")

                #last and first match - already have them.
                if first_name in person["NAMES"]:
                    new_person = False
                    #If this household is currently NEGATIVE it is a loaded refund (an
                    #SB20 we saw in a newer filing); net this contribution -- or another
                    #refund -- into it. If it is already >= 0 it is counted, so skip.
                    if person['CONTRIBUTIONS'] < 0:
                        person['CONTRIBUTIONS'] += contribution
                    if person['COMPANIES']==['']:
                        #were added as SB20A, add their job
                        person['COMPANIES'] = [job] if job.upper() not in undisclosed else []
                    break

                #last name match, not first.
                #but might still be same person!
                for name in person["NAMES"]:

                    # if similar name and first_name, check if they work at same place
                    # if they have the same job and their names are close, same person
                    # Jaro-Winkler + nickname lookup (e.g. BOB == ROBERT scores 100).
                    similarity_score = name_similarity(first_name, name)

                    if similarity_score == 100:
                        #nickname. add it, already seen them.
                        if debug:
                            print(f"Nickname, already found them: {first_name}/{name} {last_name}")
                        person["NAMES"].append(first_name)
                        person['COMPANIES'] = [] if person['COMPANIES']==[''] else person['COMPANIES']
                        person['COMPANIES'] = [job] if job.upper() not in undisclosed else person['COMPANIES']
                        #same person: if this household is a pending (negative) refund, net this in
                        if person['CONTRIBUTIONS'] < 0:
                            person['CONTRIBUTIONS'] += contribution
                        new_person = False
                        break
                    if similarity_score >= NAME_SIM_THRESHOLD:
                        #check if they're the same person
                        companies_upper = [word.upper() for word in person['COMPANIES']]
                        #if companies_upper == []:
                            #if it's empty, check if first_name is unemployed too
                        if job.upper() in undisclosed and companies_upper == []:
                            if debug:
                                print(f"Same unemployed {last_name} detected {similarity_score:.2f}%:", first_name, name)
                            person["NAMES"].append(first_name)
                            if person['CONTRIBUTIONS'] < 0:
                                person['CONTRIBUTIONS'] += contribution
                            new_person = False
                            break

                        elif job.upper() in companies_upper:
                            if debug:
                                print(f"Same {last_name} detected {similarity_score:.2f}%:", first_name, name)
                            person["NAMES"].append(first_name)
                            if person['CONTRIBUTIONS'] < 0:
                                person['CONTRIBUTIONS'] += contribution
                            new_person = False
                            break
                        else:

                            if person['COMPANIES'] == ['']:
                                #then the first entry was SB20
                                #add the job but don't change anything. add the name.
                                if debug:
                                    print(f"{first_name} {last_name} was SB20 first: {person['NAMES']} {last_name}")
                                person['COMPANIES'] = [job] if job.upper() not in undisclosed else []
                                person['NAMES'].append(first_name)
                                if person['CONTRIBUTIONS'] < 0:
                                    person['CONTRIBUTIONS'] += contribution
                                new_person = False
                                break

                            #https://github.com/madisonbma/policards/issues/12
                            if contribution <= person['CONTRIBUTIONS']:
                                if debug:
                                    print('Total contribution went down so assuming this is the same person that lost/changed job:', first_name, job, name, person['COMPANIES'])
                                person['NAMES'].append(first_name)
                                new_person = False
                                break
                            else:
                                #this means they are different people. add the new person to the name.
                                if debug:
                                    print(f"Names close but different work and wrong contribution {last_name}:", first_name, job, name, person['COMPANIES'])
                                person['CONTRIBUTIONS'] += contribution
                                person["NAMES"].append(first_name)
                                new_person = False
                                break

                else:
                    # The for-loop above ran to completion WITHOUT break, meaning none
                    # of the existing names was judged to be the same person. So this is
                    # a genuinely different household member who shares the last name.

                    # merge into household if unemployed
                    if job.upper() in undisclosed:
                        if debug:
                            print(f"Add to household: {first_name} to {person['NAMES']} {last_name}, {person['COMPANIES']}")
                        person['CONTRIBUTIONS'] += contribution
                        person["NAMES"].append(first_name)
                        new_person = False

                    # family but decidedly different people.
                    # merge into household and add work
                    else:
                        if person['COMPANIES'] == []:
                            if debug:
                                print(f"Add job {job} for {first_name} to household {person['NAMES']} {last_name}.")
                            person['NAMES'].append(first_name)
                            person['COMPANIES'].append(job)
                            new_person = False
                        elif same_company(job, person['COMPANIES'][0]):
                            # Same employer written differently (e.g. 'Hpu' ~ 'High
                            # Point University') -> one workplace, merge the couple.\
                            if debug:
                                print(f"Same employer for couple {last_name}: "
                                    f"{job} ~ {person['COMPANIES'][0]}. Merging.")
                            # keep the more descriptive (longer) spelling for display
                            if len(job) > len(person['COMPANIES'][0]):
                                person['COMPANIES'][0] = job
                            person['NAMES'].append(first_name)
                            person['CONTRIBUTIONS'] += contribution
                            new_person = False
                        else:
                            two_jobs_note = (f"Two jobs for this couple: {first_name}:{job}, "
                                             f"{person['NAMES']}:{person['COMPANIES']}.")

                # If we resolved this person (merged, or recognized as already present),
                # stop scanning. But in the genuine "two jobs" case new_person is still
                # True: keep scanning, because another entry at this SAME address may BE
                # this person (their name was added in an earlier filing / SB20 row). We
                # must reach that entry to recognize them and avoid re-adding -> double
                # counting their contribution.
                if not new_person:
                    break

            #otherwise if they have a dash, check both last names
            elif "-" in last_name:
                last_name_parts = last_name.split("-")
                for possible_last in last_name_parts:
                    if possible_last in person["LAST_NAME"]:
                        #print(f"Hyphenated name match found for {name} at {address} with possible last name {possible_last}")
                        if first_name in person['NAMES']:
                            new_person = False
                            break
                        else:
                            if job.upper() in undisclosed:
                                person['NAMES'].append(first_name)
                                person['CONTRIBUTIONS'] += contribution
                                if debug:
                                    print(f"Unemployed person added to the family: {first_name} {last_name}")
                                new_person = False
                                break
                            elif person['COMPANIES'] == []:
                                person['NAMES'].append(first_name)
                                person['CONTRIBUTIONS'] += contribution
                                if debug:
                                    print(f"{first_name} {last_name} is employed, but spouse is not. Merging.")
                                new_person = False
                                break
                            else:
                                if debug:
                                    print(f"Couple with hyphenated name with 2 different jobs, keeping separate people")


            else:
                #Check for last name typos (Jaro-Winkler; no nickname expansion for surnames)
                similarity_score = name_similarity(last_name, person['LAST_NAME'], use_nicknames=False)
                if similarity_score >= NAME_SIM_THRESHOLD:
                    #print(f"***Possible last name typo at {address}: {last_name}, {person['LAST_NAME']}")

                    # match a bare given name to one stored with a middle name/initial
                    # ('ROBERT' ~ 'ROBERT P'), without merging conflicting middles.
                    if any(names_same_person(first_name, nm) for nm in person["NAMES"]):
                        if debug:
                            print(f"Matched person with typoed last name: {first_name} {last_name} ~ {person['NAMES']} {person['LAST_NAME']}")
                        if first_name not in person["NAMES"]:
                            person["NAMES"].append(first_name)
                        new_person = False
                        break
                    else:
                        #defer: only meaningful if this row is ultimately added as new,
                        #so we don't re-print it on every scan past this household member.
                        typo_note = (f"!!! Last name typo but no one found here: "
                                     f"{first_name} {last_name} no match in {person}")



            #if they don't match, add as a new person at the address
        if new_person:
            if two_jobs_note and debug:
                print(two_jobs_note)
            if typo_note and debug:
                print(typo_note)
            #print(f"No hyphenated name match found for {name} at {address}")
            #`contribution` is the signed delta already (+aggregate for SA11, -refund for
            #SB20 -- the caller negates row[20]), so store it directly. Do NOT re-negate
            #for SB20A or refunds become positive and pile into the empty-employer "" key.
            new_dict = {"LAST_NAME": last_name,
                        "NAMES": [first_name] + name_aliases,
                        "COMPANIES": [job] if job.upper() not in undisclosed else [],
                        "CONTRIBUTIONS": contribution
                        }
            individual_data[address].append(new_dict)


def match_or_add_person(row, individual_data, contribution, date=None, debug=False):
    """
    Bucket an itemized IND row to the SAME PERSON at an address. We merge only genuine
    same-person variants (nicknames, initials, last-name typos) -- NOT family members.
    (Families are merged later, downstream, to stay compatible with consolidation.)

    Per person we keep the cycle-to-date aggregate from the MOST RECENT contribution
    date, because row[21] is the aggregate AS OF the row's date (row[19]) and is not
    consistent/monotonic across the form.

    Per-person record:
      { LAST_NAME, NAMES:[variants], COMPANIES:[employers, latest-date first],
        CONTRIBUTION, CONTRIBUTION_DATE, SB_REFUND }

    `contribution` is the RAW positive amount; the row type decides how it is used:
      SA11/SA12 -> aggregate row[21]; replace CONTRIBUTION/CONTRIBUTION_DATE iff `date`
                   is newer (or the person has no SA aggregate yet).
      SB20      -> refund row[20]; accumulate -contribution into SB_REFUND ONLY while
                   CONTRIBUTION is still None (no SA seen). Once an SA has set
                   CONTRIBUTION we ignore further refunds (the aggregate nets them).
    """

    undisclosed = ["NOT EMPLOYED", "SELF EMPLOYED", "SELF-EMPLOYED", "ME", "HOME", "SELF",
                   "N/A", "SELF- EMPLOYED", "UNEMPLOYED", "HOMEMAKER", "NOT-EMPLOYED",
                   "RETIRED", "NONE", "RETRIED"]

    is_refund = row[0].upper().startswith("SB20")

    address = row[12] + row[14] + row[15]
    job = '' if is_refund else replace_company_name(row[23])
    first_name = row[8].upper()
    middle_name = row[9].upper()
    last_name = row[7].upper().replace(" ", "").replace("'", "")

    # Misfiled name fields: some donors put their middle initial in the first-name slot
    # [8] and their actual first name in the middle slot [9] (e.g. 'fellows,w.,jay' =
    # first 'W.', middle 'JAY'). Only when [8] is just an initial AND [9] is a real name,
    # treat [9] as the first name and keep [8] as an alias so the donor is still matched.
    name_aliases = []
    if middle_name and _initials_form(first_name) is not None and _initials_form(middle_name) is None:
        name_aliases.append(first_name)
        first_name = middle_name

    job_disclosed = bool(job) and job.upper() not in undisclosed

    def norm_date(d):
        # YYYYMMDD is chronologically sortable as a string; anything else -> "" (oldest).
        d = (d or "").strip()
        return d if re.fullmatch(r"\d{8}", d) else ""

    def record_names(person):
        for nm in [first_name] + name_aliases:
            if nm and nm not in person["NAMES"]:
                person["NAMES"].append(nm)

    def add_employer(person, make_latest):
        # COMPANIES holds the disclosed employers this person has had, latest-date first.
        if not job_disclosed:
            return
        if make_latest:
            others = [c for c in person["COMPANIES"] if not same_company(c, job)]
            person["COMPANIES"] = [job] + others
        elif not any(same_company(c, job) for c in person["COMPANIES"]):
            person["COMPANIES"].append(job)  # an older/other job we hadn't recorded

    def apply_to_person(person):
        record_names(person)
        if is_refund:
            # Net the refund only while we still have no SA aggregate; once CONTRIBUTION
            # is set, the aggregate already accounts for refunds, so ignore.
            if person["CONTRIBUTION"] is None:
                person["SB_REFUND"] = (person["SB_REFUND"] or 0) - contribution
            return
        new_d, old_d = norm_date(date), norm_date(person["CONTRIBUTION_DATE"])
        if person["CONTRIBUTION"] is None or new_d > old_d:
            person["CONTRIBUTION"] = contribution
            person["CONTRIBUTION_DATE"] = date
            add_employer(person, make_latest=True)
        elif new_d == old_d and contribution > person["CONTRIBUTION"]:
            # same date but a larger aggregate -> take the max
            #print(f"NOTE: same-date ({date}) duplicate aggregate for {person['NAMES']} "
            #      f"{last_name}: had {person['CONTRIBUTION']}, saw {contribution}; taking max.")
            person["CONTRIBUTION"] = contribution
            add_employer(person, make_latest=True)
        else:
            add_employer(person, make_latest=False)

    def new_record():
        return {
            "LAST_NAME": last_name,
            "NAMES": [first_name] + name_aliases,
            "COMPANIES": [job] if job_disclosed else [],
            "CONTRIBUTION": None if is_refund else contribution,
            "CONTRIBUTION_DATE": None if is_refund else date,
            "SB_REFUND": -contribution if is_refund else None,
        }

    def is_same_person(person):
        p_last, names = person["LAST_NAME"], person["NAMES"]
        # Exact last name: same first name, a nickname (BOB==ROBERT), or a similar first
        # name AT THE SAME EMPLOYER. Similar name + different/unknown employer is treated
        # as a DIFFERENT person now (the old "contribution went down" heuristic is dropped
        # -- recency by date supersedes it).
        if last_name == p_last:
            if first_name in names:
                return True
            for nm in names:
                sim = name_similarity(first_name, nm)
                if sim == 100:
                    return True
                if sim >= NAME_SIM_THRESHOLD and job_disclosed and \
                        any(same_company(job, c) for c in person["COMPANIES"]):
                    return True
            return False
        # Hyphenated last name: a component matches and the given name is the same.
        if "-" in last_name:
            for part in last_name.split("-"):
                if part and part in p_last and first_name in names:
                    return True
            return False
        # Last-name typo (no nickname expansion for surnames) + same given name.
        if name_similarity(last_name, p_last, use_nicknames=False) >= NAME_SIM_THRESHOLD:
            if any(names_same_person(first_name, nm) for nm in names):
                return True
        return False

    persons = individual_data.get(address)
    if persons is None:
        individual_data[address] = [new_record()]
        return

    # Same-person via initial abbreviation ('J.' for 'JOHN', 'WJ' for 'W. J.'),
    # unambiguous only (disambiguated by employer when several qualify).
    abbrev_match = resolve_initial_abbreviation(persons, first_name, last_name, job, undisclosed)
    if abbrev_match is not None:
        if debug:
            print(f"Initial abbreviation: {first_name} = {abbrev_match['NAMES']} {last_name}")
        apply_to_person(abbrev_match)
        return

    for person in persons:
        if is_same_person(person):
            apply_to_person(person)
            return

    # No same-person match -> a distinct person at this address (family or otherwise).
    persons.append(new_record())




# Exit code used when the requested bioguide_id is not in the resolved map. The app
# branches on this specific code to offer manual committee-code entry; keep in sync
# with the matching constant in main.js.
BIOGUIDE_NOT_FOUND_EXIT = 42


def get_committee_id_for_candidate(session: requests.Session, candidate_id: str):
    """
    Derive the committee id(s) tied to a candidate via the FEC endpoint
    /v1/candidate/{id}/committees (sorted by most recent cycle). Used by manual
    --candidate-id mode, where there is no bioguide cross-reference to supply the
    committee. Returns the committees active in the candidate's most recent cycle, or
    None if the candidate has none.
    """
    params = {
        'sort': "-cycles"
    }
    results = get_first_page_numbered(session, f"/v1/candidate/{candidate_id}/committees", params, "committee_detail")
    if not results:
        return None
    
    comm_ids = []
    recent_cycle = max(results[0]['cycles'])
    for result in results:
        if recent_cycle in result['cycles']:
            comm_ids.append(result.get('committee_id'))

    return comm_ids if comm_ids else None


def _run_for_candidate(session, generated_outputs, candidate_id, committee_id, cycle, output_path):
    """
    Shared pipeline once candidate_id + committee_id are known (resolved from either the
    bioguide cross-reference or manual --candidate-id mode): pull totals, fetch and roll
    up filings across the relevant period cycle(s), and return [totals_dict, contribution_data].

    The result is also written ONCE to `output_path` (a throwaway handoff file the app
    supplies in the OS temp dir, then reads and deletes) so it isn't duplicated in appData.
    The filings cache in generated_outputs is still written -- it's a legitimate, reusable
    cross-run cache, separate from the per-candidate result.
    """
    # ── Step 0: get PAC and ind totals ─────────────────────────
    #totals_dict = fetch_totals(session, candidate_id, cycle)
    totals_dict = fetch_totals_for_election_year(session, candidate_id, cycle)
    print(totals_dict)
    election = totals_dict['election_year']

    # ── Step 1: fetch filings (cached per committee+election in generated_outputs) ──
    filings_path = generated_outputs / f"filings_{committee_id}_{election}.json"

    if os.path.exists(filings_path):
        load_path = Path(filings_path)
        print(f"\n=== Loading Filings from {load_path} ===")
        filings = json.loads(load_path.read_text(encoding="utf-8"))
        print(f"  Loaded {len(filings)} records.")
    else:
        filings = fetch_filings(session, committee_id)
        if debug:
            save_json(filings, filings_path, "filings")

    # ── Step 2: fetch CSV data from filings ────────────────────────────
    # The aggregate resets each two-year period, so for a Senate seat (3 cycles) we
    # process each period separately and SUM; House is a single period. candidate_id's
    # first letter (S/H) tells us which.
    period_cycles = candidate_period_cycles(candidate_id, election)
    totals_dict["year_range"] = f"{period_cycles[0]-1}-{period_cycles[-1]}"

    print(f"\nRolling up election {election} over period cycle(s): {period_cycles}")
    contribution_data = {}
    for period in period_cycles:
        period_filings = [f for f in filings if f.get("cycle") == period]
        if not period_filings:
            print(f"  (no filings for period cycle {period}, skipping)")
            continue
        print(f"\n=== Period cycle {period}: {len(period_filings)} filing(s) ===")
        period_data = fetch_filing_csv(period_filings, election, generated_outputs)
        for k, v in period_data.items():
            contribution_data[k] = contribution_data.get(k, 0) + v

    contribution_data = dict(sorted(contribution_data.items(), key=lambda item: item[1], reverse=True)) #sort contribution data by amount, descending

    # ── Ballpark check: sum of our contribution_data vs FEC total receipts ──────
    # Expected to run HIGH: conduits (ActBlue/WinRed) are counted as their own bucket
    # AND as the individual donations they bundle, so there is built-in double counting.
    total_in = totals_dict.get("total_in")
    print("\n=== BALLPARK vs FEC total_in ===")
    print(f"  FEC total_in (receipts) : ${total_in:,.2f}")
    print(f"  sum(contribution_data)  : ${sum(contribution_data.values()):,.2f}  "
          f"(diff ${sum(contribution_data.values()) - total_in:,.2f})")

    # ── Step 3: write the result to the handoff path + return it ──────────────────
    result = [totals_dict, contribution_data]
    save_json(result, output_path, "contribution data from filings")
    print(f"  results          : {output_path}")

    print("Top 10:")
    for name, amount in list(contribution_data.items())[:10]:
        print(f"  {name}: ${amount:,.2f}")

    return result


def check_running(bioguide_map, congressmen_bioguide):
    """
    We cross_reference by going through the FEC candidates and finding the associated bioguide.
    But what if they aren't running again? Then they won't show up as FEC candidate and we 
    won't map. Search through the bioguide
    """

    for person in congressmen_bioguide:
        if person.get('bioguideID') not in bioguide_map:
            print(f"{person.get('name')} not mapped.")



def main2():
    parser = argparse.ArgumentParser(
        description="Get filing endpoints to parse the CSVs for full receipt data."
    )
    parser.add_argument("--api-key", required=True, help="FEC API key")
    parser.add_argument("--bioguide-id", help="bioguideID of candidate")
    parser.add_argument(
        "--candidate-id",
        help="FEC candidate id (e.g. H4AS00036). Manual mode: when given, the bioguide "
             "cross-reference is skipped and this candidate is used directly.",
    )
    parser.add_argument(
        "--cycle",
        required=True,
        type=int,
        help="Two-year transaction period / cycle (e.g. 2024)",
    )

    parser.add_argument(
        "--generated-outputs",
        default=".",
        help="Directory to generated_outputs",
    )

    parser.add_argument(
        "--output-path",
        help="Path to write the [totals, contribution_data] result. The app passes a "
             "throwaway temp file it reads then deletes. Defaults to "
             "generated_outputs/contribution_data.json.",
    )

    parser.add_argument(
        "--debug",
        help="Enable debug mode, save files",
        action='store_true'
    )


    args = parser.parse_args()

    if not args.bioguide_id and not args.candidate_id:
        parser.error("one of --bioguide-id or --candidate-id is required")

    global debug
    if args.debug:
        debug = True

    generated_outputs = Path(args.generated_outputs)
    generated_outputs.mkdir(parents=True, exist_ok=True)

    # Where the final result is written. The app supplies a throwaway temp path it reads
    # then deletes (so the result lives only in the supplement, not duplicated in appData);
    # standalone runs fall back to a fixed file in generated_outputs.
    output_path = Path(args.output_path) if args.output_path else generated_outputs / "contribution_data.json"

    # Shared session with API key
    session = requests.Session()
    session.params = {"api_key": args.api_key}  # type: ignore[assignment]

    # ── Resolve candidate_id + committee_id ──────────────────────────────────────
    # Manual mode (--committee-id given): skip the runner/cross-reference resolution
    # entirely and derive the candidate_id straight from the committee. Otherwise the
    # normal path resolves both from the bioguide cross-reference below.
    if args.candidate_id:
        candidate_id = args.candidate_id
        committee_id = get_committee_id_for_candidate(session, candidate_id)
        if committee_id is None:
            sys.exit(f"Error: no committees found for candidate {candidate_id}. "
                     "Please check the candidate code and cycle.")
        print(f"Manual mode: candidate {candidate_id} -> committee {committee_id}")
        if len(committee_id) > 1:
            print(f"Candidate has multiple committees, using first committee: {committee_id[0]}")
        committee_id = committee_id[0]
        return _run_for_candidate(
            session, generated_outputs, candidate_id, committee_id, args.cycle, output_path
        )

    # ── Step N: get all running candidates names and comms ──────────────────────
    house_runners_path = generated_outputs / f"house_runners_{args.cycle}.json"
    senate_runners_path = generated_outputs / f"senate_runners_{args.cycle}.json"
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
    bioguide_path = generated_outputs / "congressmen.json"
    bioguide_data = json.loads(bioguide_path.read_text(encoding="utf-8"))
    bioguide_map, failed_map = cross_reference(house_runners + senate_runners, bioguide_data, args.cycle)
    save_json(bioguide_map, generated_outputs / f"bioguide_fec_map_{args.cycle}.json", "bioguide map")


    # ── Resolve candidate + committee from the cross-reference ───────────────────
    # bioguide not found -> exit with a DISTINCT code so the app can tell this case
    # apart from a generic failure and offer manual committee-code entry instead.
    if bioguide_map.get(args.bioguide_id) is None:
        print(f"Error: bioguide_id {args.bioguide_id} not found in bioguide map. "
              "Please check the bioguide_id and cycle, and ensure the candidate is "
              "running in that cycle.", file=sys.stderr)
        sys.exit(BIOGUIDE_NOT_FOUND_EXIT)

    candidate_id = bioguide_map[args.bioguide_id]["candidate_id"]

    committee_id = bioguide_map[args.bioguide_id]["committee_id"]
    if len(committee_id) > 1:
        print(f"Candidate has multiple committees, using first committee: {committee_id[0]}")
    committee_id = committee_id[0]

    return _run_for_candidate(
        session, generated_outputs, candidate_id, committee_id, args.cycle, output_path
    )


if __name__ == "__main__":
    main2()