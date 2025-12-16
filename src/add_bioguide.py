import json
import pandas as pd
from datetime import date
import numpy as np
import re
import os


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
    



def map_school_names(university, city=None):
    """
    Docstring for map_school_names
    Will map an input university long name to a shorter one
    
    :param university: input string, university name
    :param city: input string (optional), the city if it's a school with multiple locations
    """

    #check the name mappings:
    if university == " University of California":
        #change to UC City
        if city:
            return f" U.C.{city}"
        else:
            return university
    elif university == " California State University":
        #change to CSU City
        if city:
            return f" C.S.U.{city}"
        else:
            return university
    elif university == " Massachusetts Institute of Technology":
        return " M.I.T."
    elif university == " University of North Carolina at Chapel Hill":
        return " University of North Carolina"
    elif university == " Florida Agricultural and Mechanical University":
        return " Florida A&M University"
    elif university == " Harvard University Kennedy School of Government":
        return " Harvard Kennedy School" #could also just be Harvard University?
    elif university == " D'Youville College (now D'Youville University)":
        return " D'Youville University"
    elif university == " North Carolina Agricultural and Technical University":
        return " NC A&T State University"
    elif university == " North Carolina Agricultural and Technical State University":
        return " NC A&T State University"
    elif university == " Washington University School of Dental Medicine":
        return " WashU School of Dental Medicine"
    elif university == " Mount Vernon College (now the George Washington University)":
        return " George Washington University"
    elif university == " California School of Professional Psychology":
        return " CA School of Professional Psych"
    elif university == " Oklahoma State University Institute of Technology":
        return " O.S.U.I.T."
    elif university == " Columbus College (now Columbus State University)":
        return " Columbus State University"
    elif university == " University of Bombay (now University of Mumbai)":
        return " University of Mumbai"
    elif university == " Gulf Coast Community College (now Gulf Coast State College)":
        return " Gulf Coast State College"
    elif university == " Georgetown University School of Foreign Service":
        return " Georgetown University"
    elif university == " Georgetown University School of Medicine":
        return " Georgetown University"
    elif university == " Indiana University Kelley School of Business":
        return " Indiana University"
    elif university == " Federal Bureau of Investigation National Academy":
        return " FBI National Academy"
    elif university == " New York Maritime University (now SUNY Maritime College)":
        return "SUNY Maritime College"
    else:
        return university



def exempt_from_hs(university):
    """
    These are schools that get flagged as high schools
    Return None if known high school
    Else Return the university name
    """
    known_hs = (
        " Pinecrest Academy in Florida", " Notre Dame Academy", " Sacred Heart Academy", 
        " Woodward Academy", " Osceola County School for the Arts", " LaSalle Academy"
    )
    
    if "high school" in university.lower():
        return None
    elif university in known_hs:
        return None
    elif "Preparatory School" in university:
        return None
    elif "University" in university:
        return university
    elif "College" in university:
        return university
    elif "Law School" in university:
        return university
    elif "School of Law" in university:
        return university
    elif "Postgraduate" in university:
        return university
    elif "Seminary" in university:
        return university
    elif "United States" in university:
        return university
    elif "West Point" in university:
        return university
    elif "School of Business" in university:
        return university
    elif university == " Yale Divinity School":
        return university
    elif  "School of Economics" in university:
        return university
    elif university == " Virginia Polytechnic Institute":
        return university
    elif university == " Marion Military Institute":
        return university
    elif university == " SUNY Geneseo":
        return university
    elif "School of Theology" in university:
        return university
    elif university == " Wentworth Institute":
        return university
    elif "School of Medicine" in university:
        return university
    elif "Institute of Technology" in university:
        return university
    elif university == " Union Institute":
        return university
    else:
        return None
    



def get_user_input_hs(university, city=None):
    university_filtered = map_school_names(university, city=city)
    if university != university_filtered:
        #then a definite university, skip high school check
        return university_filtered
    else:
        parsed_for_hs = exempt_from_hs(university_filtered)

    if parsed_for_hs is None:
        #TODO: ask for user input to approve
        return None
    else:
        return university_filtered
    





def check_education(education_list):
    """
    Education should come in the following formats:
        "graduated from The Master's Academy, Oviedo, Fla., 1995",
        "attended Troy State University, Troy, Ala.",
        "Rhodes Scholar, Ph.D., Oxford University, Oxford, England, 2010"
        "J.D., University of Oregon Law School in Eugene 1974"
        "M.Div., M.Phil., and Ph.D., Union Theological Seminary, New York, N.Y."
        "J.D., University of Mississippi, University, Miss. 1975"
        "M.F.S. and J.D., Georgetown University, 1993"

    education is too long if it's 50 or longer.
    """
    target_length = len(education_list)
    #print(f"S {target_length}: {education_list}")
    new_education = ""
    return_me = []

    #loop through all the educations in education_list
    for education in education_list:

        #before splitting by comma - if it ends in year and is missing the comma, add it
        pattern = r"(.*)([a-zA-Z\.])\s(\d{4})$"
        replacement = r"\1\2,\3"
        education = re.sub(pattern, replacement, education)

        #now that we've cleaned any typos at the end, look for dates in the middle of the string
        education_mega = []
        date_matches = re.finditer(r"\d{4}(\-\d{4})?", education)
        #if more than 1, split by it
        date_index_start = 0
        date_index_end = len(education)
        for match in date_matches:
            date_index_end = match.end()
            education_mega.append(education[date_index_start:date_index_end])
            date_index_start = match.end() + 2


        if len(education_mega) == 0:
            education_mega.append(education)
            #print("No match found, appending outright")
        elif len(education_mega) > 1:
            print(f"|||Splitting {education} in {len(education_mega)}")
        


        #now have to loop through what we just made, most of the time this will just be once
        for ed in education_mega:
            #split by comma
            education_by_comma = ed.split(",")

            #check if it starts with a valid degree
            if re.match(r"^[A-Z].*", education_by_comma[0]):
                #####################################
                #TYPO CHECK: look for missing typo between degree and next item
                #####################################
                #split by space. if len>1, might be a typo. check.
                typo_check = education_by_comma[0].split(" ")
                if len(typo_check) > 1:
                    typo_found = 1
                    if typo_check[1] == "and":
                        #no problem, this is if they got 2 degrees, like "M.S. and B.S."
                        typo_found = 0
                    elif typo_check[1] == "candidate":
                        #no problem, this is like "PhD candidate"
                        typo_found = 0
                    elif typo_check[1] == "in":
                        # get rid of in, remaining words are the major
                        typo_found = 1
                        typo_check.pop(1)
                    elif typo_check[0] == "Rhodes":
                        #this is for "Rhodes Scholar", merge it with [1]
                        education_by_comma[0] = education_by_comma[0] + education_by_comma.pop(1)
                        typo_found = 0

                    if typo_found:
                        #then we need to add a comma between 0 and 1
                        education_by_comma[0] = typo_check[0]
                        typo_check[1] = f" {typo_check[1]}"
                        education_by_comma.insert(1, " ".join(typo_check[1:]))
                ############################################
                # end typo check
                ###########################################
                sections = len(education_by_comma)

                ############################################
                #starts with degree, ends with year
                ############################################
                if re.match(r"\s?\d{4}", education_by_comma[-1]):

                    #if len==3, should just be degree, university, year. keep it.
                    if sections == 3:
                        university = get_user_input_hs(education_by_comma[1])
                        new_education = ",".join((education_by_comma[0], university, 
                                                education_by_comma[2]))
                        return_me.append(new_education)

                    #if len==4, should follow degree, major, university, year
                    elif sections == 4:
                        
                        if len(ed) < 50:
                            #if it fits, keep the major
                            return_me.append(ed)
                            break
                        else:
                            #drop major to make it fit
                            university = get_user_input_hs(education_by_comma[2])
                            if university is None:
                                #could be a weird edge case, like different countries. 
                                # try if other indeces are universities
                                university = get_user_input_hs(education_by_comma[1])
                                if university is None:
                                    print(f"Can't find a school: {ed}")

                            
                            new_education = ",".join((education_by_comma[0], university, 
                                                    education_by_comma[3]))
                    
                        #if it's still too big, drop the year
                        if len(new_education) < 50:
                            return_me.append(new_education)
                            break
                        else:
                            new_education = ",".join((education_by_comma[0], university))

                        if len(new_education) > 50:
                            return_me.append(new_education)
                            print(f"TOO LONG: {ed}")
                            break
                        else:
                            return_me.append(new_education)

                    #if len==5, should follow degree, university, city, state., year
                    elif sections == 5:   
                        university = get_user_input_hs(education_by_comma[1], education_by_comma[2])
                        #drop city and state to make it fit     
                        if university is None:
                            university = get_user_input_hs(education_by_comma[2])
                        if university is None:
                            university = get_user_input_hs(education_by_comma[3])
                        if university is None:
                            print(f"Can't find a school: {ed}")
                        new_education = ",".join((education_by_comma[0], university, 
                                                education_by_comma[4]))

                        #if it's still too big, drop the year
                        if len(new_education) < 50:
                            return_me.append(new_education)
                            break
                        else:
                            new_education = ",".join((education_by_comma[0], university))

                        if len(new_education) > 50:
                            print(f"TOO LONG: {ed}")
                            return_me.append(new_education)
                        else:
                            return_me.append(new_education)

                    #if len==6, should follow either 
                    elif sections == 6:
                        #i want degree, university, year
                        #check for university, 
                        for stat in education_by_comma:
                            if "University" in stat:
                                university = stat
                            elif "College" in stat:
                                university = stat
                            elif "Massachusetts Institute of Technology" in stat:
                                university = stat
                        
                        university = get_user_input_hs(university)
                        new_education = ",".join((education_by_comma[0], university, 
                                                education_by_comma[-1]))
                        return_me.append(new_education)

                    else:
                        print(f"PROBLEM: {education_by_comma}")
                ######################
                # doesn't end in date
                ######################
                else:
                    if sections == 2:
                        #should just be degree, school. keep it
                        university = get_user_input_hs(education_by_comma[1])
                        new_education = ",".join((education_by_comma[0], university))
                        if len(new_education) > 50:
                            print(f"TOO LONG: {ed}")
                            return_me.append(new_education)
                        else:
                            return_me.append(new_education)

                    elif sections == 4:
                        #should be degree, school, city, state
                        university = get_user_input_hs(education_by_comma[1])
                        new_education = ",".join((education_by_comma[0], university))
                        if len(new_education) > 50:
                            print(f"TOO LONG: {ed}")
                            return_me.append(new_education)
                        else:
                            return_me.append(new_education)

                    else:
                        print(f"No date end: {ed}")

            ################
            # start section without degree
            ####################
            else: 
                sections = len(education_by_comma)


                #if it's just graduated, check [1]
                if education_by_comma[0] == "graduated":
                    university = get_user_input_hs(education_by_comma[1])
                    if university is not None:
                        new_education = ",".join((university, education_by_comma[-1]))
                        return_me.append(new_education)
                        break
                    else:
                        #high school.
                        return_me.append(high_school())
                        break


                #first: "graduated ___" or "graduated from ___"
                #get rid of the beginning, see if next line has University or College
                #if not, change it to "high school diploma"
                elif re.match(r"graduated( from)?(?P<school>.*)", education_by_comma[0]):

                    matched = re.match(r"graduated( from)?(?P<school>.*)", education_by_comma[0])
                    university = matched.group('school')
                    #check if university is a high school or not:

                    if sections == 1:
                        university = get_user_input_hs(university)
                        if university is not None:
                            new_education = university
                            if len(new_education) > 50:
                                print(f"TOO LONG: {new_education}")
                                return_me.append(new_education)
                            else:
                                return_me.append(new_education)
                        else:
                            return_me.append(high_school())

                    elif sections == 2:
                        #should be school, year
                        #remove graduated 
                        university = get_user_input_hs(university)
                        if university is not None:
                            new_education = ",".join((university, education_by_comma[-1]))
                            return_me.append(new_education)
                            break
                        else:
                            #high school.
                            return_me.append(high_school())
                            break



                    elif sections == 3:
                        #should be school, degree, year
                        #change to degree, school, year
                        university = get_user_input_hs(university)

                        if university is not None:
                            new_education = ",".join((education_by_comma[1], university, 
                                                    education_by_comma[2]))
                            if len(new_education) < 50:
                                return_me.append(new_education)
                                break
                            else:
                                print(f"TOO LONG: {ed}")
                        else:
                            #high school.
                            return_me.append(high_school())
                            break

                        
                    elif sections == 4:
                        #school, city, state, year
                        #check if school is high school or not
                        university = get_user_input_hs(university)
                        if university is not None:
                            new_education = ",".join((university, education_by_comma[-1]))
                            if len(new_education) < 50:
                                return_me.append(new_education)
                                break
                            else:
                                print(f"TOO LONG: {ed}")
                        else:
                            #high school.
                            return_me.append(high_school())
                            break

                    elif sections == 5:
                        #should be school, city, state, degree, year
                        #change to degree, school, year
                        university = get_user_input_hs(university)
                        if university is not None:
                            new_education = ",".join((education_by_comma[3], university, education_by_comma[4]))
                            if len(new_education) < 50:
                                return_me.append(new_education)
                                break
                            else:
                                print(f"TOO LONG: {ed}")
                        else:
                            #high school.
                            return_me.append(high_school())
                            break
                        

                    else:
                        print(f"Unmatched length: {ed}")

                elif re.match(r"attended (.*)", education_by_comma[0]):
                    matched = re.match(r"attended(?P<school>.*)", education_by_comma[0])
                    university = matched.group('school')
                    university = get_user_input_hs(university)

                    if university is None:
                        return_me.append(high_school())
                    else:                    
                        #if it ends in a date, join university, date
                        if re.match(r"\s\d{4}(\-\d{4})?", education_by_comma[-1]):
                            new_education = ",".join((university, education_by_comma[-1]))
                        #else just return university
                        else:
                            new_education = university
                        
                        if len(new_education) > 50:
                            print(f"TOO LONG: {ed}")
                        else:
                            return_me.append(new_education)

                        

                #if starts with attended, trim it down and add it
                else: 
                    
                    print(f"unknown start: {ed}")

    if target_length != len(return_me):
        print(f"Mismatched lengths!!!")
    #print(f"E {len(return_me)}: {return_me}")

    return return_me
    

def high_school():
    return "High school graduate"


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
                       "United States Air Force", "U.S. Army", "National Guard", "U.S. Marine", "Judge Advocate", "judge advocate", "Marine Corps",
                       "discharged", "enlisted")
    bad_behavior = ("expelled", "censured", "reprimanded", "convicted", "sentence", "pardon", "indicted", "acquitted", "charges", "evidence", "denounced")
    term_end = ("resigned", )

    root = os.path.dirname(os.path.abspath(__file__))

    
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
        newjson_path = os.path.join(root, os.path.pardir, "bioguide_data", f"{rep.get('bioguideID')}.json")
        bioguide_data = load_json(newjson_path)
        photo_url = ""
        
        #Get the URL for the photo
        photo_path_list = bioguide_data.get('image')
        if not photo_path_list:
            photo_path_list = bioguide_data.get('asset')
        if not photo_path_list:
            #print(f"No photo available for {rep.get('bioguideID')}")
            rep.update({"photo": None})
        else:
            jpg_path = photo_path_list[0].get('contentUrl')
            if jpg_path:
                base_url = "https://bioguide.congress.gov/photo/"
                photo_url = base_url + jpg_path.split("/")[-1]
                rep.update({"photo": photo_url})
            else:
                rep.update({"photo": None})



        #Parse the profileText section for more data
        profiletext = bioguide_data.get('profileText')
        if profiletext is None:
            print(f"\tCould not find profileText data for {rep.get('bioguideID')}")
            print(f"{rep.keys()}")
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
                    fact = fact.replace("B. S.", "B.S.")
                    fact = fact.replace("M. Div", "M.Div")
                    fact = fact.replace("D. Div", "D.Div")
                    fact = fact.replace("M. D.", "M.D.")
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
                        if birthplace.startswith("in "):
                            birthplace = birthplace[2:]
                            
                else:
                    #print(f"\tUncaptured string: {fact}")
                    continue
            #End looping through fact block
        

        #update the education before appending
        education = check_education(education)


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

    #with open(input_file, 'r', encoding='utf-8') as file:
    #    list_of_congressmen = json.load(file)
        

    list_of_congressmen = json.loads(input_json) #From json_string to JSON dict
    
    updated_list = add_bioguide_congress_data(list_of_congressmen) #list of dicts
    return updated_list
