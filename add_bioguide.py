import requests
import os
import json
import time
import pandas as pd
import sys
import os
from datetime import date
import numpy as np
import re


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
    

def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            data = json.load(file)
            #print(f"Loaded file {filepath}")
        return data
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: The file '{filepath}' contains invalid JSON format.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred on {filepath}: {e}")
        return None


############################################

def add_bioguide_congress_data(list_of_dict):
    """
    Using the data loaded from bioguide.congress.gov, which has been downloaded to bioguide_data dir,
    update the current json with the relevant info

    """

    seen_rep = []
    #not case sensitive
    jobs = ("elementary", "medical doctor", "law", "business", "non", 
            "investment broker", "real estate", "united states merchant marine", "governor",
            "social worker", "program", "farmer", "entrepreneur", "sales", "investment banker",
            "optometrist", "rancher", "union", "civil engineer", "marketing", 
            "author", "instructor", "physician", "police", "sheriff", "realtor", "insurance")
    valid_roles = ("a delegate", "a representative", "a senator", "elected", "reelected")
    dead = ("died", "interment", "lay in", "death", "cremate", "entombment", "body", "buried")
    local_legislation = ("general assembly", "state senate", "state house of representatives", "mayor ", "mayor,", "city council", "state assembly")


    #case sensitive
    jobs_instring = ("owner", "CEO", "attorney", "faculty", "actor", "professor", "superintendent", "advocate", "manager", "dentist", "engineer",
                     "lecturer", "journalist", "attorney general", "Attorney General", "consultant", "farmer", "Peace Corps", "teacher", "newspaper",
                     "pastor", "principal", "dean", "minister", "pilot", "pharmacist", "stockbroker", "therapist", "staff", "Staff", "aide", "business")
    valid_degrees = ("S.J.D.", "B.E.E.", "D.C.S.", "LL.D.", "M. Div", "D. Div", "D.N.P.", "M.P.P.", "D.O.", "Ed.M.", "Ed.S.", "I.A.", "JD.",
                     "B.S.", "M.S.", "B.A.", "Ph.D.", "M.B.A", "A.B.", "J.D.", "LL.B.", "M.D.", "M.L.A", "M.B.T.", "D.D.S.", "B.L.S.", "B.P.A", 
                     "M.A.", "M.P.A", "B.B.A", "A.A.", "LL.M", "L.L.B", "B.D.", "M.Ed", "B. S.", "A.S.", "Ed.D.", "LLB", "D.P.A.",
                     "M. D.", "B.C.L.", "M.Div", "M.E.", "Ph..D.", "B.Litt.", "M.P.H.", "C.L.U", "Bachelor of Law", "Ph.B.", "A.M.", "M.H.R.M.")
    military_record = ("United States Army", "United States Nav", "United States Marine", "United States Coast Guard", 
                       "United States Air Force", "U.S. Army", "National Guard", "U.S. Marine", "Judge Advocate", "judge advocate", "Marine Corps")
    bad_behavior = ("censured", "reprimanded", "convicted", "sentence", "pardon", "indicted", "acquitted", "charges", "evidence", "denounced")
    term_end = ("resigned", )
    
    for rep in list_of_dict:
        education = []
        military_history = []
        illegal= []
        failed_runs = []
        work_history = []
        congressional_highlights = []
        accolades = []
        lawyer_stuff = []
        family = [] 
        hold = ""

        #Load the json for the current bioguideID
        #if rep['bioguideID'] not in seen_rep:
        seen_rep.append(rep.get('bioguideID'))
        newjson_path = f"bioguide_data/{rep.get('bioguideID')}.json"
        bioguide_data = load_json(newjson_path)
        
        #Parse the profileText section for more data
        #try:
        profiletext = bioguide_data.get('profileText')
        if profiletext is None:
            print(f"\tCould not find profileText data for {rep.get('bioguideID')}")
        else:
            data = profiletext.replace("&amp;", "&")
            data = data.replace("&aacute;", "a")
            data = data.replace("&rsquo;", "'")
            data = data.replace("&nbsp;", "")
            data = data.replace("&ndash;", "-")
            data = data.replace("&eacute;", "e")
            data = data.replace("<p>", "")
            data = data.replace("’", "'")

            data = data.split(";")
            for fact in data:
                fact = fact.lstrip()
                fact_lower = fact.lower()
            
                ### Format changes
                # if unmatched parenthesis, merge with the next line
                if hold:
                    fact = ",".join((hold, fact))
                    hold = ""

                if re.search(r".*\([^\)]*$", fact):
                    hold = fact
                    continue
                else:
                    hold = ""

                

                ###Skip these things
                if fact_lower.startswith(valid_roles): #already know elected/re-elected/current role
                    continue
                elif any(sub in fact_lower for sub in dead): #when they died, where they were buried, etc
                    continue
                elif any(sub in fact for sub in term_end): #when they ended their term. sometimes resign to run for something else, died, etc
                    continue
                elif fact.startswith(("not a candidate ", "was not a candidate ")): #often saying they ran for something else when they ran out of house terms
                    continue
                elif re.match(r"delegate.*(?:Democratic|Republican) National Convention.*", fact): #DNC or RNC, don't really care
                    continue
                elif re.match(r".*resumed.*", fact): #Resumed stuff, often practice of law, should already be accounted for in previous lines
                    continue
                elif re.match(r".*is a resident.*", fact): #Don't care if they're a resident
                    continue


                ###Random facts that we'll include
                elif any(sub in fact for sub in bad_behavior): #illegal behavior
                    illegal.append(fact)
                elif "unsuccessful" in fact_lower: #unsuccessful runs at legislation
                    failed_runs.append(fact)
                elif "to conduct the impeachment" in fact_lower: #if they conducted an impeachment thing
                    congressional_highlights.append(fact)
                elif re.match(r".*\(.*Congress.*\).*", fact): #some congress stat
                    congressional_highlights.append(fact)
                elif re.match(r"award", fact):
                    accolades.append(fact)
                elif re.match(r"\(.*\), a (?:Senator |Representative .*)", fact): #Relevant family members
                    family.append(fact)




                ###Get degrees
                elif any (sub in fact for sub in valid_degrees):
                    #Degree listed, add to education
                    education.append(fact)
                elif fact_lower.startswith("graduate"):
                    pattern = r"(?:graduated|graduate)(?! work)(.*)"
                    match = re.search(pattern, fact, re.I)
                    if not match:
                        #graduate work, goes into work category
                        work_history.append(fact)
                    else:
                        #else is education history
                        education.append(fact)
                ###Get military record
                elif any(sub in fact for sub in military_record):
                    military_history.append(fact)
                elif fact_lower.startswith("attended "):
                    #seems like we should count this as education history, but not a real degree will need to check
                    education.append(fact)
                elif re.search(r".* bar[s,]? ?.*", fact): #lawyer stuff related to the bar
                    lawyer_stuff.append(fact)


                ###Get work history
                elif fact_lower.startswith(jobs):
                    work_history.append(fact)
                elif any(sub in fact_lower for sub in local_legislation):
                    work_history.append(fact)
                elif any(sub in fact for sub in jobs_instring):
                    work_history.append(fact)


                ###Get birthplace
                #born Nancy D'Alesandro in Baltimore, Md., March 26, 1940
                #born near Decatur, Morgan County, Ala., January 15, 1840
                #born in Mission, Tex., February 11, 1921
                #born in Farmington, San Juan County, N. Mex., January 31, 1979
                elif fact_lower.startswith("born "):
                    #Birthplace
                    pattern = r"born (?:.* in )?([\w,\. -]+)"
                    #Remove the date
                    cleaned = re.sub(r"(?:(, |on |)?((January|February|March|April|May|June|July|August|September|October|November|December)( \d{1,2},)? \d{4})(, )?)", "", fact)
                    
                    match = re.search(pattern, cleaned, re.I)
                    if not match:
                        birthplace = None
                        print(f"Uncaptured birthplace: {fact}")
                    else: 
                        #Add to birthplace
                        birthplace = match.group(1)

                else:
                    #print(f"\tUncaptured string: {fact}")
                    continue
            #End looping through fact block
        
        #Update the JSON
        rep.update({'birthDate': bioguide_data.get('birthDate')})

        rep.update({'education': education})
        rep.update({'military': military_history})
        rep.update({'illegal': illegal })
        rep.update({'failed_runs': failed_runs})
        rep.update({'work_history': work_history})
        rep.update({'congress_highlights': congressional_highlights})
        rep.update({'accolades': accolades})
        #rep.update({'lawyer_stuff': lawyer_stuff})
        rep.update({'family': family})
        rep.update({'birthplace': birthplace})

    return list_of_dict


############################################




####################################################################################################


def add_bioguide(input_json):
    """
    Takes the json string object and will save a congressmen_mod.json 
    
    Args: 
        input_json [JSON str]: congressmen.json contents with voting data

    """

        #Load in the JSON
    #with open(input_json_f, 'r') as f:
    #    congress_list = json.load(f)

    list_of_congressmen = json.loads(input_json) #From json_string to JSON dict
    
    updated_list = add_bioguide_congress_data(list_of_congressmen) #list of dicts
    return updated_list
