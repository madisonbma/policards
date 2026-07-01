import json
from datetime import datetime
import re
import os
from dateutil.relativedelta import relativedelta

VALID_DEGREES = ("S.J.D.", "B.E.E.", "D.C.S.", "LL.D.", "M. Div", "D. Div", "D.N.P.", 
                "M.P.P.", "M.P.M", "D.O.", "Ed.M.", "Ed.S.", "I.A.", "JD.",
                "B.S.", "M.S.", "B.A.", "Ph.D.", "M.B.A", "A.B.", "J.D.", "LL.B.",
                "M.D.", "M.L.A", "M.B.T.", "D.D.S.", "B.L.S.", "B.P.A", 
                "M.A.", "M.P.A", "B.B.A", "A.A.", "LL.M", "L.L.B", "B.D.", "M.Ed", 
                "B. S.", "A.S.", "Ed.D.", "LLB", "D.P.A.", "M.A.L.D.",
                "S.B.", "S.M.", "B.A", "D.Div", "B.J.", "M.Sc.", "M.A.C.T",
                "M. D.", "B.C.L.", "M.Div", "M.E.", "Ph..D.", "B.Litt.", "M.P.H.", 
                "C.L.U", "Bachelor of Law", "Ph.B.", "A.M.", "M.H.R.M.", 
                "B.S.F.S.", "M.I.L.R.", "M.P.P.A.", "B.S.B.A.", "M.P.H", "M.S.A.",
                "M.H.S", "B.S.N", "M.P.P.M", "M. St.", "B.S.N", "M.E.M", "D.M.D.",
                "A.L.B", "L.L.M.", "M.I.A.", "M.F.A.", "M. Phil.", "M.Phil.", "M.F.",
                "M.S.S", "M.A.R.", "LLM", "Pharm.D")

VALID_ROLES = ("a delegate", "a representative", "a senator", "elected", "reelected")

CABINET = ("Department of Agriculture", "Department of Commerce", "Department of Defense", "Department of Education", "Department of Energy", "Department of Health and Human Services",
        "Department of Homeland Security", "Department of Housing and Urban Development", "Department of Interior", "Department of Labor", "Department of Transportation",
        "Department of Treasury", "Department of Veterans Affairs") #State too but keeps getting other things
STATES = (
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", 
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", 
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", 
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", 
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", 
    "New Hampshire", "New Jersey", "New Mexico", "New York", 
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", 
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", 
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", 
    "West Virginia", "Wisconsin", "Wyoming"
)

JOBS = ("elementary", "medical doctor", "law", "business", "nonprofit", "non-profit" ,
            "investment broker", "real estate", "united states merchant marine", "governor",
            "lieutenant governor", "state auditor", "chemist", "welder", "automobile dealer",
            "community organizer", "auditor", "litigator", "administrator", "administrative",
            "firefighter", "physicist", "scientist", "opthalmologist", "driver",
            "urologist", "commentator", "restauranteur", "technician", "reporter",
            "prison guard", "courier", "examiner", "pediatrician",
            "social worker", "program", "farmer", "entrepreneur", "sales", "banker",
            "optometrist", "rancher", "union", "civil engineer", "marketing", 
            "author", "instructor", "physician", "police", "sheriff", "realtor", "insurance",
            "psychologist", "founder", "co-founder",
            "owner", "ceo", "attorney", "faculty", "actor", "professor", "superintendent", 
            "advocate", "manager", "dentist", "engineer",
            "lecturer", "journalist", "attorney general", "consultant", 
            "farmer", "peace corps", "teacher", "newspaper",
            "pastor", "principal", "dean", "minister", "pilot", "pharmacist", "stockbroker", 
            "therapist", "staff", "aide", "businessman", "businesswoman", "coach", 
            "riverboat captain", "ambassador", "geologist", "jewelry designer", "plumber", "bank officer",
            "mortician", 
            )




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
        return data
    except FileNotFoundError as e:
        print(f"ERROR: The file '{filepath}' was not found.")
        missing_file = os.path.basename(filepath)
        print(f"TO FIX:")
        print(f"1. Navigate to https://bioguide.congress.gov/search/bio/{missing_file}")
        print(f"2. Right Click > Save as > Save to politician_pages/bioguide_data")
        print(f"3. Close the app, reopen. Gen card > Update Records > No > Yes")
        raise e
    except json.JSONDecodeError as e:
        print(f"Error: The file '{filepath}' contains invalid JSON format.")
        raise e
    except Exception as e:
        print(f"An unexpected error occurred on {filepath}: {e}")
        raise e



############################################
    


def check_birthplace(birthplace):
    """
    Drop county of birthplace if 2 commas present
    
    :param birthplace: input string birthplace
    """

    if birthplace == None:
        return ""
    else:
        birthplace = birthplace.removesuffix(", ")
        birthplace = birthplace.replace("on the north side of", "")

        birthplace = to_state_code(birthplace, ", ", True) #first convert to state code
        birth_sections = birthplace.split(",")
        if len(birth_sections) == 3:
            return f"{birth_sections[0]},{birth_sections[2]}"
        else:
            return birthplace



def convert_parens_school_names(university):

    #if School of __ (of|at) (university)
    matched_1 = re.match(r"school of (\w+ )+(of|at) ?(?P<school>.*)", university, re.I)
    #matched_2 = re.match(r"(?P<school>.*) school of (\w+ )+(of|at) ?", university, re.I)
    matched_rename = re.match(r"(.*) \((now|later) ([a-z]+ )*(?P<new_school>[A-Z].*)\)", university)
    matched_rename_2 = re.match(r"(?P<new_school>.*) \(then (.*)\)", university)
    matched_rename_3 = re.match(r"(.*) \((?P<new_school>[A-Z].*)\)", university)
    if matched_1:
        return matched_1.group('school')
    elif matched_rename:
        return matched_rename.group('new_school')
    elif matched_rename_2:
        return matched_rename_2.group('new_school')
    elif matched_rename_3:
        return matched_rename_3.group('new_school')
    else:
        return university


def drop_school_or_college(university):
    """
    When the college/school is included, often gets too long.
    Trim to just keep the university name
    """
    school_with_u_match_1 = re.match(r"(?P<school>University of .*) (Graduate | Law )?School \w+", university)
    school_with_u_match_2 = re.match(r"(?P<school>.* University) (Graduate |Law )?School \w+", university)
    if school_with_u_match_1:
        #print(f"{university} -> {school_with_u_match_1.group('school')}")
        university = school_with_u_match_1.group('school')
    elif school_with_u_match_2:
        #print(f"{university} -> {school_with_u_match_2.group('school')}")
        university = school_with_u_match_2.group('school')
    return university

def map_school_names(university, city=None):
    """
    Docstring for map_school_names
    Will map an input university long name to a shorter one
    
    :param university: input string, university name
    :param city: input string (optional), the city if it's a school with multiple locations
    """

    university = convert_parens_school_names(university)
    university = drop_school_or_college(university)

    if (" at " in university):
        check_for_at = university.split(" at ")
        university = check_for_at[0]
        city = check_for_at[1]


    #check the name mappings:
    if university == "University of California":
        #change to UC City
        if city:
            return f" U.C.{city}"
        else:
            return university
    elif university == "California State University":
        #change to CSU City
        if city:
            return f" C.S.U.{city}"
        else:
            return university
    elif university == "California State":
        #change to CSU City
        if city:
            return f" C.S.U.{city}"
        else:
            return university
    elif university == "California Polytechnic State University":
        if city:
            return f"Cal Poly {city}"
        else:
            return "Cal Poly"
    elif university == "California State Polytechnic University":
        if city:
            return f"Cal Poly {city}"
        else:
            return "Cal Poly"
    elif university == "Massachusetts Institute of Technology":
        return "M.I.T."
    elif "University of California at Los Angeles" in university:
        return "U.C.L.A."
    elif "University of Virginia" in university:
        return "University of Virginia"
    elif "Johns Hopkins" in university:
        return "Johns Hopkins"
    elif "University of North Carolina" in university:
        return "U.N.C."
    elif "University of Maryland Baltimore County" in university:
        return "University of Maryland"
    elif university == "University of Oregon Law School Eugene":
        return "University of Oregon"
    elif university == "University Center (a division of the University of Alabama)":
        return "University of Alabama"
    elif university == "University of Minnesota School of Dentistry":
        return "University of Minnesota"
    elif "Samuel DeWitt Proctor School of Theology at Virginia Union University" in university:
        return "Virginia Union University"
    elif university == "Southeastern Baptist Theological Seminary":
        return "SE Baptist Theological Seminary"
    elif university == "Southwestern Baptist Theological Seminary":
        return "SW Baptist Theological Seminary"
    elif university == "Northeastern Oklahoma State University":
        return "NE Oklahoma State University"
    elif university == "Southwestern Oklahoma State University":
        return "SW Oklahoma State University"
    elif university == "Wharton School of the University of Pennsylvania":
        return "University of Pennsylvania"
    elif "University of California Hastings" in university:
        return "U.C. Law S.F."
    elif university == "Ohio State University Agricultural Technical Institute":
        return "Ohio State ATI"
    elif "Texas Agricultural and Mechanical" in university:
        return "Texas A&M"
    elif "Texas Agricultural & Mechanical" in university:
        return "Texas A&M"
    elif "Louisiana State University" in university:
        return "L.S.U."
    elif university == "the North Dakota State Agricultural College at Fargo":
        return "N.D.S.U."
    elif "Purdue University" in university:
        return "Purdue University"
    elif "Harvard" in university:
        return "Harvard University"
    elif university == "Adelbert College of Western Reserve University":
        return "Case Western Reserve University"
    elif "Army Command and General Staff College" in university:
        return "U.S.A.C.G.S.C"
    elif "University of Dayton" in university:
        return "University of Dayton"
    elif university == "George Washington University School of Medicine":
        return "George Washington University"
    elif "University of Kentucky" in university:
        return "University of Kentucky"
    elif "Missouri University" in university:
        return "Missouri University"
    elif "Syracuse University" in university:
        return "Syracuse University"
    elif "University of Newark" in university:
        return "University of Newark"
    elif "Southern Methodist University of Dallas" in university:
        return "Southern Methodist University"
    elif university == "Florence State University (University of North Alabama)":
        return "University of North Alabama"
    elif university == "Northwestern University Kellogg School of Management":
        return "Northwestern University"
    elif university == "Florida Agricultural and Mechanical University":
        return "Florida A&M University"
    elif university == "North Carolina Agricultural and Technical University":
        return "NC A&T State University"
    elif university == "North Carolina Agricultural and Technical State University":
        return "NC A&T State University"
    elif university == "Washington University School of Dental Medicine":
        return "WashU School of Dental Medicine"
    elif university == "California School of Professional Psychology":
        return "CA School of Professional Psych"
    elif university == "Oklahoma State University Institute of Technology":
        return "O.S.U.I.T."
    elif "Georgetown University" in university:
        return "Georgetown University"
    elif university == "Indiana University Kelley School of Business":
        return "Indiana University"
    elif university == "Federal Bureau of Investigation National Academy":
        return "FBI National Academy"
    elif university == "Duke":
        return "Duke University"
    elif "Yale" in university:
        return "Yale University"
    elif university == "New York University School of Commerce":
        return "N.Y.U."
    elif university == "Rosalind Franklin University of Medicine and Science":
        return "Rosalind Franklin University"
    elif university == "William M. Scholl College of Podiatric Medicine":
        return "Rosalind Franklin University"
    elif university == "Waterford Kamhlaba United World College of Southern Africa":
        return "WKUWCSA"
    elif university == "University of Illinois at Urbana-Champaign":
        return "U.I.U.C."
    elif university == "The Military College of South Carolina":
        return "The Citadel"
    elif university == "Philadelphia College of Osteopathic Medicine":
        return "P.C.O.M."
    elif "United States" in university:
        university = university.replace("United States", "U.S.")
        return university
    elif "Amos Tuck School of Business Administration" in university:
        return "Dartmouth College"
    elif university == "Tennessee Technical":
        return "Tennessee Tech"
    elif university == "Southern University and Agricultural & Mechanical College":
        return "Southern University A&M"
    else:
        return university



def exempt_from_hs(university):
    """
    These are schools that get flagged as high schools
    Return None if known high school
    Else Return the university name
    """
    known_hs = (
        "Pinecrest Academy in Florida", "Notre Dame Academy", "Sacred Heart Academy", 
        "Woodward Academy", "Osceola County School for the Arts", "LaSalle Academy",
        "Loomis School"
    )
    if university in known_hs:
        return None
    elif "high school" in university.lower():
        return None
    elif "grades 1 through 12" in university.lower():
        return None
    elif "nursing school" in university.lower():
        return university
    elif "Corpus Christi College-Academy" in university:
        return None
    elif "Preparatory School" in university:
        return None
    elif "University" in university:
        return university
    elif "The Citadel" in university:
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
    elif "West Point" in university:
        return university
    elif "School of Business" in university:
        return university
    elif  "School of Economics" in university:
        return university
    elif university == "Virginia Polytechnic Institute":
        return university
    elif university == "Marion Military Institute":
        return university
    elif university == "SUNY Geneseo":
        return university
    elif "School of Theology" in university:
        return university
    elif university == "Wentworth Institute":
        return university
    elif university == "California Institute for Integral Studies":
        return university
    elif "School of Medicine" in university:
        return university
    elif "Institute of Technology" in university:
        return university
    elif university == "Union Institute":
        return university
    elif university == "Virginia Military Institute":
        return university
    elif university == "Rensselaer Polytechnic Institute":
        return university
    elif university == "Touro Law Center":
        return university
    elif university == "Heidelberg U.":
        return university
    elif university == "Franklin Pierce Law Center":
        return university
    elif "ITT Educational Services" in university:
        return university
    elif "Southwest Missouri State" in university:
        return university
    elif "Worcester Polytechnic Institute" in university:
        return university
    elif "Claremont Graduate School" in university:
        return university
    elif university == "Louisiana Polytechnic Institute":
        return university
    else:
        return None
    



def get_user_input_hs(university, city=None):
    """
    Docstring for get_user_input_hs
    
    :param university: input line to be checked if university is in it
    :param city: 2nd input to check if it's like UC, Berkeley
    :return: will return university if it's a valid university.
            If not a valid university (could be HS), will return None
    :rtype: Any
    """
    university = university.strip()
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


def check_for_same_university(old_university, university, return_me):
    """
    In the DEG, UNI, YR scenario
    oftentimes the UNI is just saying "same as above.
    If that's the case, append anyways
    Get the university  from the previous append and use that
    """
    if len(return_me)==0:
        #print("No previous school to reference... skip")
        return None
    
    elif "same university" in university:
        old_uni = return_me[-1]
        if old_university is None:
            print(f"Previous university was a high school, can't pull.")
        elif old_university in old_uni:
            #print(f"Replacing same university with {old_university}")
            return old_university
        else:
            print(f"Previous university didn't match: {old_uni} vs {old_university}")

    else:
        return None
    



def trim_education_further(university):
    """
    If already trimmed education, remove "School of Law" and stuff
    """
    if university.endswith(" School of Law"):
        university = university.replace(" School of Law", "")
    elif university.endswith(" College of Law"):
        university = university.replace(" College of Law", "")
    elif university.endswith(" School of Medicine"):
        university = university.replace(" School of Medicine", "")
    elif university.endswith(" Medical School"):
        university = university.replace(" Medical School", "")
    elif university.endswith(" Law School"):
        university = university.replace(" Law School", "")
    elif university.endswith(" Law Center"):
        university = university.replace(" Law Center", "")
    elif university.endswith(" Health Science Center"):
        university = university.replace(" Health Science Center", "")
    elif university.endswith(" for Medical Sciences"):
        university = university.replace(" for Medical Sciences", "")

    university = too_long_check_for_and(university)
    return university


def too_long_check_for_and(university):
    """
    Sometimes the educations are too long because there's an and in there
    The and in there is some high school stuff and then some degree
    split by " and "
    check the split for a university
    if found one, return just the university
    """
    many_unis_uhoh = []
    if " and " in university:
        university_split = university.split(" and ")
        for possible_u in university_split:
            uni = get_user_input_hs(possible_u)
            if uni is not None:
                many_unis_uhoh.append(uni)

        if len(many_unis_uhoh)==0:
            #no luck
            return university
        elif len(many_unis_uhoh)==1:
            #print(f"Found university: {many_unis_uhoh[0]}")
            return many_unis_uhoh[0]
        else:
            print(f"Found many universities in {university}: {",".join(many_unis_uhoh)}")
            return university
    else:
        return university

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
    new_education = ""
    return_me = []
    old_university = None
    university = None

    #loop through all the educations in education_list
    for education in education_list:

        ########ADD TYPO FIXES FOR EDUCATION HERE ###################
        #before splitting by comma - if it ends in year and is missing the comma, add it
        pattern = r"(.*)([a-zA-Z\.]) (\d{4})$"
        replacement = r"\1\2,\3"
        education = re.sub(pattern, replacement, education)
        education = re.sub(r',(?![ ])', ', ', education)
        education = re.sub(r"^a(n) ", "", education)


        #########ADD POTENTIALLY MISSING COMMAS HERE ################
        #now that we've cleaned any typos at the end, look for dates in the middle of the string

        education_mega = []
        #check for YYYY(-YYYY)?
        date_matches = re.finditer(r"\d{4}(\-\d{4})?(, \d{4}-\d{4})?( and,\d{4})?", education)
        #if more than 1, split by it
        date_index_start = 0
        date_index_end = len(education)
        #will be empty if no match and nothing will run.
        for match in date_matches:
            date_index_end = match.end()

            #finalize the string
            hidden_education = education[date_index_start:date_index_end]

            #filter it for leading , | and | 
            hidden_education = re.sub(r'^,(\s)?', '', hidden_education)
            hidden_education = re.sub(r'^( )?and (from )?', '', hidden_education)
            hidden_education = re.sub(r' in,', ', ', hidden_education)
            hidden_education = re.sub(r' in ', ' ', hidden_education)
            hidden_education = re.sub(r'^received ', '', hidden_education)
            hidden_education = re.sub(r'^the ', '', hidden_education)
            hidden_education = hidden_education.replace("  ", " ")

        
            
            #now add it
            education_mega.append(hidden_education)

            date_index_start = date_index_end

        if len(education_mega) == 0:
            education_mega.append(education)

        
        #now have to loop through what we just made, most of the time this will just be once
        for ed in education_mega:
            #check if we missed a comma before year and add it so we split properly
            no_comma_before_year_pattern = r"([^,-])\s(\d{4})"
            replacement_pattern = r"\1, \2"
            ed = re.sub(no_comma_before_year_pattern, replacement_pattern, ed)

            #split by comma
            education_by_comma = [item.strip() for item in ed.split(',')]
            old_university = university #store previous university for check for "same school"
            new_education = ""

            #check if it starts with a valid degree
            if any ((deg:=sub) in education_by_comma[0] for sub in VALID_DEGREES):
                #####################################
                #TYPO CHECK: look for missing typo between degree and next item
                #####################################
                #split by space. if len>1, might be a typo. check.
                typo_check = education_by_comma[0].split(" ")

                if len(typo_check) > 1: #then the degree could be anywhere!
                    fix_typo = 1
                    if typo_check[0] == "a":
                        fix_typo = 0
                        education_by_comma[0] = typo_check[1]
                    elif typo_check[0] == "an":
                        fix_typo = 0
                        education_by_comma[0] = typo_check[1]
                    elif typo_check[0] == "Associate":
                        fix_typo = 0
                    elif typo_check[1] == "and":
                        #no problem, this is if they got 2 degrees, like "M.S. and B.S."
                        fix_typo = 0
                    elif typo_check[1] == "candidate":
                        #no problem, this is like "PhD candidate"
                        fix_typo = 0
                    elif typo_check[1] == "in":
                        # get rid of in, remaining words are the major
                        fix_typo = 1
                        typo_check.pop(1)
                    elif typo_check[0] == "Rhodes":
                        #this is for "Rhodes Scholar", merge it with [1]
                        education_by_comma[0] = education_by_comma[0] + education_by_comma.pop(1)
                        fix_typo = 0
                        


                    possible_append = " ".join(typo_check[1:])

                    if re.match(r"degree from", possible_append):
                        del typo_check[1:3]
                        possible_append = " ".join(typo_check[1:])
                        fix_typo = 1
                    elif re.match(r"degree$", possible_append):
                        education_by_comma[0] = typo_check[0]
                        fix_typo = 0
                    elif re.search(r"Bachelor of Law( |,)?$", education_by_comma[0]):
                        education_by_comma[0] = "L.L.B."
                        fix_typo = 0
                    elif re.match(r" ?\((now )?J\.D\.\)", possible_append):
                        fix_typo = 0
                        education_by_comma[0] = "LL.B. (J.D.)"

                    if fix_typo:
                        #print(f"editing typo: {education_by_comma[0]} -> {typo_check[0]}, {possible_append} ")
                        #then we need to add a comma between 0 and 1
                        education_by_comma[0] = typo_check[0]
                        #typo_check[1] = f" {typo_check[1]}"
                        education_by_comma.insert(1, possible_append)

                #now also check since starts with degree, see if next few are degrees:
                index_degree = 1
                degree = education_by_comma[0]
                while index_degree < len(education_by_comma):
                    if any(re.search(rf"(?<![a-zA-Z\.]){re.escape(word)}(?![\&a-zA-Z])", education_by_comma[index_degree]) for word in VALID_DEGREES):
                        degree += f", {education_by_comma.pop(index_degree)}"
                        #print(f"changed degree to {degree} in {ed}")
                        index_degree += 1
                    else:
                        break
                ############################################
                # end typo check
                ###########################################
                sections = len(education_by_comma)

                ############################################
                #starts with degree, ends with year
                ############################################
                if re.match(r"\s?\d{4}", education_by_comma[-1]):
                    #degree, year (no university)
                    if sections == 2:
                        return_me.append(ed)
                    
                    #if len==3, should just be degree, university, year. keep it.
                    elif sections == 3:
                        university = get_user_input_hs(education_by_comma[1])
                        if university is None:
                            university = check_for_same_university(old_university, education_by_comma[1], return_me)
                        if university is None:
                            print(f"No university found: {education_by_comma}")
                            for deg in VALID_DEGREES:
                                if deg in ed:
                                    degree = deg
                            new_education = ", ".join((degree, education_by_comma[-1]))

                        else:
                            new_education = ", ".join((degree, university, 
                                                    education_by_comma[2]))
                            
                            if (len(new_education) < 50):
                                return_me.append(new_education)
                                break
                            else:
                                #too long, try to trim the uni
                                university = trim_education_further(university)
                                new_education = ", ".join((degree, university, 
                                                education_by_comma[2]))

                            if (len(new_education) < 50):
                                return_me.append(new_education)
                            else:
                                #print(f"TOO LONG len3 deg,uni,yr: {new_education}")
                                return_me.append(new_education)
                        #print(f"{ed}->{new_education}")

                    #if len==4, should follow degree, major, university, year
                    elif sections == 4:
                        
                        if len(ed) < 50:
                            #if it fits, keep the major
                            new_education = ed
                            return_me.append(new_education)
                            break
                        else:
                            #drop major to make it fit
                            university = get_user_input_hs(education_by_comma[2])
                            if university is None:
                                #could be a weird edge case, like different countries. 
                                # try if other indeces are universities
                                university = get_user_input_hs(education_by_comma[1])
                            if university is None:
                                print(f"CAN'T FIND SCHOOL deg,maj,uni,yr: {ed}")
                                break
                            else:
                                new_education = ", ".join((degree, university, 
                                                        education_by_comma[3]))
                    
                        #if it's still too big, trim the name
                        if (len(new_education) < 50):
                            return_me.append(new_education)
                            break
                        else:
                            #too long, try to trim
                            university = trim_education_further(university)
                            new_education = ", ".join((degree, university, 
                                                        education_by_comma[3]))

                        #if it's still too big, drop the year
                        if len(new_education) < 50:
                            return_me.append(new_education)
                            break
                        else:
                            new_education = ", ".join((degree, university))

                        if len(new_education) < 50:
                            return_me.append(new_education)
                        else:
                            return_me.append(new_education)
                            print(f"TOO LONG len4 deg, maj, uni, yr: {new_education}")
                            break

                    #if len==5, should follow degree, university, city, state, year
                    elif sections == 5:   
                        
                        university = get_user_input_hs(education_by_comma[1], education_by_comma[2])
                        #drop city and state to make it fit     
                        if university is None:
                            university = get_user_input_hs(education_by_comma[2], education_by_comma[3])
                        if university is None:
                            university = get_user_input_hs(education_by_comma[3])
                        if university is None:
                            print(f"CAN'T FIND SCHOOL deg,uni,city,state,yr: {ed}")
                            break
                        else:
                            new_education = ", ".join((degree, university, 
                                                    education_by_comma[4]))

                        #if it's still too big, trim the name
                        if (len(new_education) < 50):
                            return_me.append(new_education)
                            break
                        else:
                            university = trim_education_further(university)
                            new_education = ", ".join((degree, university, 
                                                        education_by_comma[4]))

                        #if it's still too big, drop the year
                        if len(new_education) < 50:
                            return_me.append(new_education)
                            break
                        else:
                            new_education = ", ".join((degree, university))

                        if len(new_education) < 50:
                            return_me.append(new_education)
                        else:
                            print(f"TOO LONG deg, uni, city, state, yr: {new_education}")
                            return_me.append(new_education)


                    #if len==6, should follow either 
                    elif sections == 6:
                        #i want degree, university, year
                        #check for university, 
                        for i in range(0, 5):
                            university = get_user_input_hs(education_by_comma[i], education_by_comma[i+1])
                            if university is not None:
                                break
                        
                        if university is None:
                            print(f"CAN'T FIND SCHOOL, OMITTING: {ed}")
                        else:
                            new_education = ", ".join((degree, university, 
                                                    education_by_comma[-1]))
                            #if it's too big, trim the name
                            if (len(new_education) < 50):
                                return_me.append(new_education)
                                break
                            else:
                                university = trim_education_further(university)
                                new_education = ", ".join((degree, university, 
                                                            education_by_comma[-1]))
                            if (len(new_education) < 50):
                                return_me.append(new_education)
                                break
                            else:
                                #print(f"TOO LONG len6: {new_education}")
                                return_me.append(new_education)
                                break

                    else: #1,2,7+
                        ###Uncaptured length. Search for deg, university, and year
                        #don't use blind check because already know [0] is deg, [-1] is year
                        for j in range(0, len(education_by_comma)-1):
                            university = get_user_input_hs(education_by_comma[j], education_by_comma[j+1])
                            if university is not None:
                                break

                        if university is None:
                            print(f"Couldn't handle length, couldn't find university: {education_by_comma}")
                            break
                        else:
                            new_education = ", ".join((degree, university, education_by_comma[-1]))

                        if (len(new_education) < 50):
                            return_me.append(new_education)
                            break
                        else:
                            university = trim_education_further(university)
                            new_education = ", ".join((degree, university, 
                                                        education_by_comma[-1]))
                        if (len(new_education) < 50):
                            return_me.append(new_education)
                            break
                        else:
                            print(f"TOO LONG unknown length: {new_education}")     
                            return_me.append(new_education)
                            break 

                ######################
                # doesn't end in date
                ######################
                else:
                    if sections == 2:
                        #should just be degree, school. keep it
                        university = get_user_input_hs(education_by_comma[1])
                        if university is None:
                            print(f"CAN'T FIND SCHOOL deg, school: {ed}")
                            break
                        else:
                            new_education = ", ".join((degree, university))
                        #if too long, try to trim the school 
                        if (len(new_education) < 50):
                            return_me.append(new_education)
                            break
                        else:
                            university = trim_education_further(university)
                            new_education = ", ".join((degree, university))
                        #if still too long, report
                        if len(new_education) < 50:
                            return_me.append(new_education)
                        else:
                            print(f"TOO LONG deg, school: {new_education}")
                            return_me.append(new_education)


                    elif sections == 4:
                        #should be degree, school, city, state
                        university = get_user_input_hs(education_by_comma[1], education_by_comma[2])
                        if university is None:
                            print(f"CAN'T FIND SCHOOL deg,school,city,yr: {ed}")
                            break
                        else:
                            new_education = ", ".join((degree, university))
                        #if too long, try to trim the school
                        if (len(new_education) < 50):
                            return_me.append(new_education)
                            break
                        else:
                            university = trim_education_further(university)
                            new_education = ", ".join((degree, university))

                        if len(new_education) < 50:
                            return_me.append(new_education)
                            break
                        else:
                            print(f"TOO LONG deg, school, city, yr: {new_education}")
                            return_me.append(new_education)
                            break

                    #starts with degree, doesn't end in year, unmatched length
                    else:
                        new_education = blind_check_for_education(old_university, ed, return_me)
                        if new_education is not None:
                            return_me.append(new_education)


            ################
            # start section without degree
            ####################
            else: 
                sections = len(education_by_comma)

                #if it's just graduated, check [1]
                if education_by_comma[0] == "graduated":
                    university = get_user_input_hs(education_by_comma[1])
                    if university is not None:
                        new_education = ", ".join((university, education_by_comma[-1]))
                        if len(new_education) < 50:
                            return_me.append(new_education)
                            break
                        else:
                            #too long, try to trim the uni
                            university = trim_education_further(university)
                            new_education = ", ".join((university, education_by_comma[-1]))
                        if len(new_education) < 50:
                            return_me.append(new_education)
                            break
                        else:
                            print(f"TOO LONG graduated, : {new_education}")
                            return_me.append(new_education)
                            break
                    else:
                        #high school.
                        add_high_school(return_me)
                        break


                #first: "graduated ___" or "graduated from ___"
                #get rid of the beginning, see if next line has University or College
                #if not, change it to "high school diploma"
                elif re.match(r"graduate(d)?( from| of)?(?P<school>.*)", education_by_comma[0]):

                    matched = re.match(r"graduate(d)?( from| of)?(?P<school>.*)", education_by_comma[0])
                    university = matched.group('school')
                    #check if university is a high school or not:

                    if sections == 1:
                        university = get_user_input_hs(university)
                        if university is not None:
                            new_education = university
                            if len(new_education) < 50:
                                return_me.append(new_education)
                                break
                            else:
                                #print(f"TOO LONG len1 starts with graduate: {new_education}")
                                return_me.append(new_education)
                        else:
                            add_high_school(return_me)

                    elif sections == 2:
                        #should be school, year
                        #remove graduated 
                        university = get_user_input_hs(university)
                        if university is not None:
                            new_education = ", ".join((university, education_by_comma[-1]))
                            if (len(new_education) < 50):
                                return_me.append(new_education)
                                break
                            else:
                                #too long, try to trim the uni
                                university = trim_education_further(university)
                                new_education = ", ".join((university, education_by_comma[-1]))
                            if (len(new_education) < 50):
                                return_me.append(new_education)
                                break
                            else:
                                print(f"TOO LONG len2: {new_education}")
                        else:
                            add_high_school(return_me)
                            break



                    elif sections == 3:
                        #should be school, degree, year
                        #change to degree, school, year
                        university = get_user_input_hs(university)

                        if university is not None:
                            new_education = ", ".join((education_by_comma[1], university, 
                                                    education_by_comma[2]))
                            if len(new_education) < 50:
                                return_me.append(new_education)
                                break
                            else:
                                #too long, try to trim the uni
                                university = trim_education_further(university)
                                new_education = ", ".join((education_by_comma[1], university, 
                                                    education_by_comma[2]))
                            if (len(new_education) < 50):
                                return_me.append(new_education)
                                break
                            else:
                                print(f"TOO LONG len3 school, deg, yr: {new_education}")
                        else:
                            #high school.
                            add_high_school(return_me)
                            break

                        
                    elif sections == 4:
                        #school, city, state, year
                        #check if school is high school or not
                        university = get_user_input_hs(university)
                        if university is not None:
                            new_education = ", ".join((university, education_by_comma[-1]))
                            if len(new_education) < 50:
                                return_me.append(new_education)
                                break
                            else:
                                #too long, try to trim the uni
                                university = trim_education_further(university)
                                new_education = ", ".join((university, education_by_comma[-1]))
                            if (len(new_education) < 50):
                                return_me.append(new_education)
                                break
                            else:
                                print(f"TOO LONG len4 school, city, state, yr: {new_education}")
                        else:
                            #high school.
                            add_high_school(return_me)
                            break

                    elif sections == 5:
                        #should be school, city, state, degree, year
                        #change to degree, school, year
                        university = get_user_input_hs(university)
                        if university is not None:
                            new_education = ", ".join((education_by_comma[3], university, education_by_comma[4]))
                            if len(new_education) < 50:
                                return_me.append(new_education)
                                break
                            else:
                                #too long, try to trim the uni
                                university = trim_education_further(university)
                                new_education = ", ".join((education_by_comma[3], university, education_by_comma[4]))
                            if (len(new_education) < 50):
                                return_me.append(new_education)
                                break
                            else:
                                print(f"TOO LONG len5 school, city, state, deg, yr: {new_education}")
                        else:
                            #high school.
                            add_high_school(return_me)
                            break
                        

                    else:
                        yr = re.match(r"((\d{4} ?-? ?)?\d{4})", ed)
                        for k in range(0, len(education_by_comma)-1):
                            university = get_user_input_hs(education_by_comma[k], education_by_comma[k+1])
                            if university is not None:
                                break
                        if university is None:
                            university = get_user_input_hs(education_by_comma[-1])
                        if university is None: #probably high school
                            add_high_school(return_me)
                            break
                        if yr is None:
                            new_education = university
                        else:
                            new_education = ", ".join((university, yr))

                        if (len(new_education) < 50):
                            return_me.append(new_education)
                            break
                        else:
                            university = trim_education_further(university)
                            if yr is None:
                                new_education = university
                            else:
                                new_education = ", ".join((university, yr))
                        if (len(new_education) < 50):
                            return_me.append(new_education)
                            break
                        else:
                            print(f"Uncontrolled input education: {ed}")
                            

                elif re.match(r"attended (the )?(.*)", education_by_comma[0]):
                    matched = re.match(r"attended (the )?(?P<school>.*)", education_by_comma[0])
                    university = matched.group('school')
                    university = get_user_input_hs(university)

                    if university is None:
                        #check if next one is college
                        for index in range(len(education_by_comma)):
                            university = get_user_input_hs(education_by_comma[index])
                            if university is not None:
                                break
                    if university is None:
                        add_high_school(return_me)
                    else:                    
                        #if it ends in a date, join university, date
                        if re.match(r"\d{4}(\-\d{4})?", education_by_comma[-1]):
                            new_education = ", ".join((university, education_by_comma[-1]))
                        #else just return university
                        else:
                            new_education = university
                            return_me.append(new_education)
                            break
                        
                        if len(new_education) < 50:
                            return_me.append(new_education)
                            break
                        else:
                            #too long, try to trim the uni
                            university = trim_education_further(university)
                            new_education = ", ".join((university, education_by_comma[-1]))
                        if (len(new_education) < 50):
                            return_me.append(new_education)
                            break
                        else:
                            print(f"TOO LONG attended school: {new_education}")
                        
                    
                else: 
                    new_education = blind_check_for_education(old_university, ed, return_me)
                    if new_education is not None:
                        return_me.append(new_education)

    
    #print(education_list)
    #print(return_me)
    return return_me
    

def blind_check_for_education_general(old_university, ed, return_me):
    """
    For uncaptured use cases, when the formatting can't be expected
    Check for university, degree, and year
    Make a note if multiple are found
    """

    #remove "graduated," if present
    ed = re.sub(r"^graduated, ?", "", ed)

    education_by_comma = [item.strip() for item in ed.split(',')]
    university_list = []
    degree_list = []
    yr = re.search(r"\d{4}( ?- ?\d{4})?", ed)
    education_by_comma[0] = re.sub(r"graduate(d)?( from| of)?", "", education_by_comma[0])
    education_by_comma[0] = re.sub(r"attended (the )?", "", education_by_comma[0])

    #check for education or degree.
    for i in range(len(education_by_comma)-1):
        university = get_user_input_hs(education_by_comma[i], education_by_comma[i+1])
        if university is not None:
            university_list.append(university)
        else:
            university = check_for_same_university(old_university, education_by_comma[i], return_me)
            if university is not None:
                university_list.append(university)
                #print(f"In blind_check found same university: {ed}")
        if any (sub in education_by_comma[i] for sub in VALID_DEGREES):
            degree_list.append(education_by_comma[i])

    if any (sub in education_by_comma[-1] for sub in VALID_DEGREES):
        degree_list.append(education_by_comma[-1])

        
    #warn user if there were multiple degrees or universities listed
    combined_degree = None
    if len(degree_list) > 1:
        combined_degree = ", ".join(degree_list)
        #print(f"FOUND MANY DEGREES: {combined_degree}")
    elif len(degree_list) == 1:
        combined_degree = degree_list[0]
    else:
        #If no degree, probably a high school.
        return "High school graduate"
    
    if len(university_list) > 1:
        print(f"FOUND MANY UNIVERSITIES: {ed}")
        


    
    #now print
    if len(university_list)==0:
        print(f"only found degree: {ed}")
        return None
    else:
        if yr is None:
            new_education = f"{combined_degree}, {university_list[0]}"
        else:
            new_education = f"{combined_degree}, {university_list[0]}, {yr.group()}"

    if len(new_education) < 50:
        return new_education
    else:
        print(f"TOO LONG *: {new_education}")
        return new_education



def blind_check_for_education(old_university, ed, return_me):
    """
    For uncaptured use cases, when the formatting can't be expected
    Check for university, degree, and year
    Make a note if multiple are found
    """



    education_by_comma = [item.strip() for item in ed.split(',')]
    university_list = []
    degree_list = []
    yr = re.search(r"\d{4}( ?- ?\d{4})?", ed)

    #check for education or degree.
    for i in range(len(education_by_comma)-1):
        university = get_user_input_hs(education_by_comma[i], education_by_comma[i+1])
        if university is not None:
            university_list.append(university)
        else:
            university = check_for_same_university(old_university, education_by_comma[i], return_me)
            if university is not None:
                university_list.append(university)
                #print(f"In blind_check found same university: {ed}")
        if any (sub in education_by_comma[i] for sub in VALID_DEGREES):
            degree_list.append(education_by_comma[i])

    if any (sub in education_by_comma[-1] for sub in VALID_DEGREES):
        degree_list.append(education_by_comma[-1])

        
    #warn user if there were multiple degrees or universities listed
    combined_degree = None
    if len(degree_list) > 1:
        combined_degree = ", ".join(degree_list)
        #print(f"FOUND MANY DEGREES: {combined_degree}")
    elif len(degree_list) == 1:
        combined_degree = degree_list[0]
    else:
        #If no degree, probably a high school.
        return "High school graduate"
    
    if len(university_list) > 1:
        print(f"FOUND MANY UNIVERSITIES: {ed}")
        


    
    #now print
    if len(university_list)==0:
        print(f"only found degree: {ed}")
        return None
    else:
        if yr is None:
            new_education = f"{combined_degree}, {university_list[0]}"
        else:
            new_education = f"{combined_degree}, {university_list[0]}, {yr.group()}"

    if len(new_education) < 50:
        return new_education
    else:
        print(f"TOO LONG *: {new_education}")
        return new_education




def add_high_school(list_in):
    hs_string = "High school graduate"
    if hs_string not in list_in:
        list_in.append(hs_string)

    return list_in


def check_for_death(line):

    if "interment" in line:
        return True
    elif "entombment" in line:
        return True
    elif "willed body to " in line:
        return True
    elif line.startswith("died "):
        return True
    elif "buried" in line:
        return True
    elif re.match(r"^lay in (state|repose|honor)", line):
        return True
    elif "cremated" in line:
        return True
    elif re.match(r"(resided|lived) in .* until (his|her) death.*", line):
        return True
    elif re.match(r".* resident .*until (his|her) death.*", line):
        return True
    else:
        return False
    



def dont_use_this_line(line):
    """
    Docstring for to_use_or_not_to_use
    Skip dates with no verb
    :param line: line in profileText

    Returns:
        (boolean): true if should skip line
    """
    # 1. CLEAN THE LINE
    clean_line = line.strip()

    # 2. THE DATE FILTER (Regex)
    # This catches "1969", "1969-1970", "Oct 12, 1960", etc.
    date_patterns = [
        r"^\d{4}$",                       # Just a year (1969)
        r"^\d{4}-\d{4}$",                 # Year range (1969-1970)
        r"^[A-Z][a-z]+ \d{1,2}, \d{4}$",  # Full date (October 17, 1971)
        r"^\d{1,2}/\d{1,2}/\d{2,4}$"      # Slashed date (10/17/1971)
    ]
    resident_pattern = r"(is|was) a resident"
    if any(re.match(p, clean_line) for p in date_patterns):
        #print(f"skipping this date: {line}")
        return True
    elif re.match(resident_pattern, line, re.I):
        return True
    elif check_for_death(line):
        return True
    elif re.match(r"[Dd]elegate.*(?:Democratic|Republican) [nN]ational [cC]onvention.*", line): #DNC or RNC, don't really care
        return True
    elif re.match(r"[Dd]elegate.*(?:Democratic|Republican) [nN]ational [cC]onvention.*", line): #DNC or RNC, don't really care
        return True
    elif re.search(r"Senatorial ([A-Z][a-z]+ )", line): #Senatorial Committee is not a committee.
        return True
    elif re.search(r"[aA] Delegate from [\w ]+", line):
        return True
    else:
        return False
    
def check_for_didnt_rerun(fact):
    match1 = re.match(r"(was )?not a candidate( for (renomination|(re)?election))? (in)?( )?(to)? the (United States |U.( )?S. )?(Senate|House of Representatives) (in )?(?P<end_date>\d{4})(\.)?$", fact)
    match2 = re.match(r"(was )?not a candidate( for (renomination|(re)?election))? (in)?( )?(to)? the ([A-Z][a-z]+.*) Congress( (in )?(?P<end_date>\d{4}))(\.)?$", fact)
    match3 = re.match(r"(was )?not a candidate( for (renomination|(re)?election))? in (?P<end_date>\d{4})( to the ([A-Z][a-z]+.*) Congress)?( |\.)?$", fact)
    match4 = re.match(r"(was )?not a candidate in (?P<end_date>\d{4})( for reelection)? to the (United States |U.( )?S. )?(Senate|House of Representatives)(\.| )?$", fact) 
    match5 = re.match(r"(was )?not a candidate( for (renomination|(re)?election))? in (?P<end_date>\d{4}) due to (\w+( )?)+", fact)
    match_nodate_1 = re.match(r"(was )?not a candidate( for (renomination|(re)?election))? to the ([A-Z][a-z]+.*) Congress(\.)?$", fact)
    match_end_1 = re.match(r"served until (his|her) death (on [A-Z][a-z]+ \d+, \d{4} )?\((?P<full_term>.*)\)", fact)
    match6 = re.match(r"did not seek (re)?election (in (?P<end_date>\d{4}))?", fact)

    if match1:
        #+1 because end_date is the election year, not the congressional cycle
        end_year = int(match1.group('end_date'))+1 
        return True
    elif match2:
        end_year = int(match2.group('end_date'))+1
        return True
    elif match3:
        end_year = int(match3.group('end_date'))+1
        return True
    elif match4:
        end_year = int(match4.group('end_date'))+1
        return True
    elif match5:
        end_year = int(match5.group('end_date'))+1
        return True  
    elif match6:
        if 'end_date' in match6.groupdict() and match6.group('end_date') is not None:
            end_year = int(match6.group('end_date'))+1
            return True
        else:
            end_year = get_years_from_congress(fact) #could be None
            if end_year is not None:
                end_year = end_year[0]
            return True

    elif match_nodate_1:
        end_year = get_years_from_congress(fact)[0]
        return True
    elif match_end_1: 
        full_term = match_end_1.group('full_term') 
        #format: Month \d+, \d{4}( )?-()?Month \d+, \d{4}
        return True
    else:
        return False


def check_failed_run(fact):
    match_fail_1 = re.match(r"(was an )?unsuccessful candidate for (election|nomination|reelection) (for|to) the ([A-Z][a-z]+.*) Congress in (?P<end_date>\d{4})$", fact)
    match_fail_2 = re.match(r"(was an )?unsuccessful candidate for (election|nomination) (to the|for) United States Senate( for the ([A-Z][a-z]+.*) Congress)? in (?P<end_date>\d{4})$", fact)
    match_fail_3 = re.match(r"unsuccessful candidate .* special election.* to the ([A-Z][a-z]+.*) Congress in (?P<end_date>\d{4})$", fact)
    if match_fail_1:
        end_year = int(match_fail_1.group('end_date'))+1
        return True
    elif match_fail_2:
        end_year = int(match_fail_2.group('end_date'))+1
        return True
    elif match_fail_3:
        end_year = int(match_fail_3.group('end_date'))+1
        return True
    else:
        return False
    

def get_chamber_history(fact):
    """
    Docstring for get_chamber_history
    There's a line that'll say "a Representative|Senator|both". Use this to determine if
        we need to look for multiple chamber services or if it's just the one
    :param fact: Description
    """
    match_rep = re.match(r"[aA] Representative from ([A-Z][a-z]+)+", fact)
    match_sen = re.match(r"[aA] Senator from ([A-Z][a-z]+)+", fact)
    match_both = re.match(r"[aA] (Representative|Senator) and a (Representative|Senator) from ([A-Z][a-z]+)+", fact)
    if match_rep:
        return "R"
    elif match_sen:
        return "S"
    elif match_both:
        return "B"
    else:
        return None

def calculate_house_or_senate(start_congress, subsequent, start_date):
    """
    Docstring for calculate_house_or_senate
    Given a fact, look for the starting Congress # and subsequent runs.
    If time / sum_runs ==2, house. if ==6, senate.
    Do this to predict end_date.
    :param fact: Description
    """
    start_congress = convert_stringnum_to_num(start_congress) #int
    





def check_for_term_info(fact, terms):
    """
    Docstring for check_for_term_info
    If they have some info about how they ended their term, pull it.
    
    :param fact: input fact
    :param term: input terms (dict) of (start_date, end_date): Senate|House
    """
    #find and replace any abbreviated months:
    month_dict = {"Jan ": "January ", "Feb ":"February ", "Mar ":"March ","Apr ": "April ",
                  "Aug ":"August ", "Sept ":"September", "Oct ":"October ", 
                  "Nov ":"November ", "Dec ":"December"}
    
    for key, value in month_dict.items():
        fact = fact.replace(key, value)
    #start time in congress
    #VALID_ROLES = ("a delegate", "a representative", "a senator", "elected", "reelected")
    #1: elected as a blah blah blah (date1-date2)
    #2: elected as a D to the US Senate for the term commencing MDY
    #3: elected as a D to the US Senate in YYYY
    #4: reelected (in \d{4}(,)?(( \d{4},)+)? and again )?in \d{4} for the term ending MDY
    #5: elected as a .* in \d{4} for the term ending MDY
    #6: elected as a Democrat to the One Hundred Second and to the seventeen succeeding Congresses (January 3, 1991-present)

#elected as a Republican to the Ninety-seventh and to the twenty-two succeeding Congresses (January 3, 1981-present)

    date_format = "%B %d, %Y"

    match_start_1 = re.match(r"(elected as a.*|reelected to the [\w ]+ Congresses)\((?P<start_date>[A-Z][a-z]+ \d+, \d{4}) ?- ?(?P<end_date>[A-Z][a-z]+ \d+, \d{4})\)", fact)
    match_start_2 = re.match(r"elected as a.*Senate.*for the term commencing (?P<start_date>[A-Z][a-z]+ \d+, \d{4})", fact)
    match_start_3 = re.match(r"elected as a.*Senate.* in (?P<start_year>\d{4})$", fact)
    match_start_4 = re.match(r"reelected (in \d{4}(,)?(( \d{4},)+)? and again )?in \d{4} for the term ending (?P<end_date>[A-Z][a-z]+ \d+, \d{4})", fact)
    match_start_5 = re.match(r"elected as a.* in (?P<start_year>\d{4}) for the term ending (?P<end_date>[A-Z][a-z]+ \d+, \d{4})", fact)
    match_start_6 = re.match(r"elected [\w ]+ to the (?P<start_congress>([A-Z][a-z]+)( [A-Z][a-z]+|-[a-z]+)+).*, and served from (?P<start_date>[A-Z][a-z]+ \d+, \d{4}), to (?P<end_date>[A-Z][a-z]+ \d+, \d{4}).*resigned.*[sS]enat", fact)
    match_start_7 = re.match(r"elected in (?P<start_year>\d{4}) [\w ]+ to the (?P<start_congress>([A-Z][a-z]+)( [A-Z][a-z]+|-[a-z]+)+) Congress$", fact)

    match_start_present_1 = re.match(r"(appointed|elected)[\w ]+to the [\w ]+ Congress(es)?.*\((?P<start_date>[A-Z][a-z]+ \d+, \d{4}) ?- ?present\)(\.)?", fact)
    match_start_present_2 = re.match(r"elected [\w ]+ to the (?P<start_congress>([A-Z][a-z]+)( [A-Z][a-z]+|-[a-z]+)+) and (reelected )?to the (?P<subsequent>[\w-]+ )?succeeding (?P<subsequent2>\w+ )?Congress(es)? \([A-Z][a-z]+ (?P<start_year>\d{4}) ?- ?present\)(\.)?", fact)
    match_start_present_3 = re.match(r"elected [\w ]+ to the (?P<start_congress>([A-Z][a-z]+)( [A-Z][a-z]+|-[a-z]+)+) and (reelected )?to the (?P<subsequent>[\w-]+ )?succeeding (?P<subsequent2>\w+ )?Congress(es)? \((?P<start_date>[A-Z][a-z]+ \d+, \d{4}) ?- ?present\)(\.)?", fact)
    match_start_present_4 = re.match(r"elected [\w ]+ to the (?P<start_congress>([A-Z][a-z]+)( [A-Z][a-z]+|-[a-z]+)+) Congress$", fact)
    match_start_present_5 = re.match(r"(subsequently )?elected[\w ]+in (the )?(?P<start_date>[A-Z][a-z]+ \d+, \d{4}),? [\w ]+ term ending (?P<end_date>[A-Z][a-z]+ \d+, \d{4})(\.)?$", fact)
    match_start_present_PR = re.match(r"elected [\w ]+ to the (?P<start_congress>([A-Z][a-z]+)( [A-Z][a-z]+|-[a-z]+)+) Congress to a four-year term in \d{4} \((?P<start_date>[A-Z][a-z]+ \d+, \d{4}) ?- ?present\)(\.)?", fact)

    match_reelection_3 = re.match(r"reelected to the \w+ succeeding Congresses, and served from (?P<start_date>[A-Z][a-z]+ \d+, \d{4}), to (?P<end_date>[A-Z][a-z]+ \d+, \d{4}).*resigned to be .*[Ss]enator", fact)
    match_reelection_4 = re.match(r"unsuccessful candidate for renomination .*, but subsequently elected as a write-in candidate in the .*(?P<start_year>\d{4}),? general election, for the term ending (?P<end_date>[A-Z][a-z]+ \d+, \d{4})(\.)?$", fact)
    match_reelection_5 = re.match(r"reelected to the (?P<start_congress>([A-Z][a-z]+)( [A-Z][a-z]+|-[a-z]+| and)+) Congress(es)? \((?P<start_date>[A-Z][a-z]+ \d+, \d{4}) ?- ?(?P<end_date>[A-Z][a-z]+ \d+, \d{4})\)", fact)
    #end their time in congress
    match_end_2 = re.match(r"(was )?not a candidate.* unsuccessful.*", fact)
    match_end_3 = re.match(r"(was )?not a candidate for reelection( )?(in \d{4}\.)?$", fact)

    #change chambers
    match_takeover_1 =  re.match(r"appointed .* Senate to fill (the|a) vacancy caused by the resignation.*the term ending (?P<end_date>[A-Z][a-z]+ \d+, \d{4})", fact)
    match_takeover_2 =  re.match(r"(appointed|elected) .*Senate.* to fill (the|a) vacancy caused by the resignation.*took the oath of office on (?P<start_date>[A-Z][a-z]+ \d+, \d{4})", fact)
    match_takeover_3 =  re.match(r"appointed (?P<start_date>[A-Z][a-z]+ \d+, \d{4}), to fill (the|a) vacancy caused by the resignation", fact)
    match_takeover_3s =  re.match(r"appointed (.*Senate on )?(?P<start_date>[A-Z][a-z]+ \d+, \d{4}), to fill (the|a) vacancy caused by the resignation", fact)
    match_takeover_4 =  re.match(r"elected.*special election.* to fill (the|a) vacancy .*\((?P<start_date>[A-Z][a-z]+ \d+, \d{4})-present\)", fact)
    match_takeover_5 =  re.match(r"elected.*Senate.*term ending (?P<end_date>[A-Z][a-z]+ \d+, \d{4}), .*(resignation|death)?.*(began service|took the oath of office) on (?P<start_date>[A-Z][a-z]+ \d+, \d{4})", fact)
    match_takeover_6 =  re.match(r"elected in (?P<start_year>\d{4}).*special election.*term ending (?P<end_date>[A-Z][a-z]+ \d+, \d{4})", fact)
    match_takeover_7 =  re.match(r"(subsequently )?elected.*special election on (?P<start_date>[A-Z][a-z]+ \d+, \d{4})($|.* remainder of the term)", fact)
    match_takeover_8 =  re.match(r"(subsequently )?elected([\w ]+)? in (?P<start_year>\d{4}) in a special election$", fact)
    match_takeover_9 =  re.match(r"elected as a \w+ to the (?P<start_congress>([A-Z][a-z]+)( [A-Z][a-z]+|-[a-z]+)+) Congress (?!\d{4})+$", fact)
    match_takeover_10 = re.match(r"elected.*(?P<start_congress>([A-Z][a-z]+)( [A-Z][a-z]+|-[a-z]+)+) Congress.*special election(?!\d{4})+$", fact)

    match_change_1 = re.match(r"appointed on (?P<start_date>[A-Z][a-z]+ \d+, \d{4}),.*to the United States Senate", fact)
    match_change_2 = re.match(r"appointed on (?P<start_year>\d{4}),.*to the United States Senate", fact)
    match_change_3 = re.match(r"appointed .*to the United States Senate on (?P<start_date>[A-Z][a-z]+ \d+, \d{4})(?!\d{4})+$", fact)
    match_change_3p5 = re.match(r"appointed .*to the United States Senate on ([A-Z][a-z]+ \d+, \d{4}).*oath of office on (?P<start_date>[A-Z][a-z]+ \d+, \d{4})", fact)
    match_change_4 = re.match(r"(appointed|elected) .*to the (United States |U.( )?S. )Senate [oi]n (?P<start_year>\d{4})", fact)
    #match45 = was not a candidate in YYYY for reelection to CHAMBER but was elected to CHAMBER in DATE
    match_yrchamberchamberdate = re.match(r"(was )?not a candidate in (?P<end_year>\d{4}) for reelection to the (United States |U.( )?S. )?(House of Representatives|Senate).* but was elected.*(?P<chamber>House of Representatives|Senate)? ([io]n|commencing) ((?P<start_date>[A-Z][a-z]+ \d+, \d{4})).*", fact)
    match_chamberchamberdate_s = re.match(r"(was )?not a candidate for reelection to the (United States |U.( )?S. )?House of Representatives.* but was elected.*(Senate)? ([io]n|commencing) ((?P<start_date>([A-Z][a-z]+ \d+, )\d{4})).*", fact)
    match_chamberchamberdateend = re.match(r"(was )?not a candidate for reelection to the (United States |U.( )?S. )?House of Representatives but was elected.*(Senate)? ([io]n|commencing) (the )?((?P<start_date>([A-Z][a-z]+ \d+, )\d{4})).*term ending (?P<end_date>([A-Z][a-z]+ \d+, )\d{4})", fact)
    match_chamberchamberdate_h = re.match(r"(was )?not a candidate for reelection to the (United States |U.( )?S. )?Senate.* but was elected.*(House of Representatives)? ([io]n|commencing) ((?P<start_date>([A-Z][a-z]+ \d+, )\d{4})).*", fact)
    match_yrchamberchamber1 = re.match(r"(was )?not a candidate in (?P<end_year>\d{4}) for reelection to the (United States |U.( )?S. )?(House of Representatives|Senate).* but was (a successful|elected).*(?P<chamber>House of Representatives|Senate)( |\.)?$", fact)
    match_yrchamberchamber2 = re.match(r"(was )?not a candidate for reelection in (?P<end_year>\d{4}) to the (United States |U.( )?S. )?(House of Representatives|Senate).* but was elected.*(?P<chamber>House of Representatives|Senate)( |\.)?$", fact)
    match_chamberyrchamber = re.match(r"(was )?not a candidate for reelection to the (United States |U.( )?S. )?(House of Representatives|Senate) in (?P<end_year>\d{4}).* but was elected.*(?P<chamber>House of Representatives|Senate)( |\.)?$", fact)
    match_chamberyrchamberdate = re.match(r"(was )?not a candidate for reelection to the (United States |U.( )?S. )?(House of Representatives|Senate) in (?P<end_year>\d{4}).* but was elected.*(?P<chamber>House of Representatives|Senate) ([io]n|commencing) ((?P<start_date>[A-Z][a-z]+ \d+, \d{4}))$", fact)
    match_chamberyrchamberyr = re.match(r"(was )?not a candidate for re(election|nomination) to the (United States |U.( )?S. )?(House of Representatives|Senate) in (?P<start_year>\d{4}).* but was elected.*(House of Representatives|Senate) ([io]n|commencing) ((?P<end_year>\d{4}))$", fact)

    match_chamberyrchamberrange = re.match(r"(was )?not a candidate for reelection to the (United States |U.( )?S. )?(House of Representatives|Senate) in (?P<end_year>\d{4}).* but was elected.*(?P<chamber>House of Representatives|Senate) and served from (?P<start_term>[A-Z][a-z]+ \d+, \d{4}), to (?P<end_term>[A-Z][a-z]+ \d+, \d{4})", fact)
    match_yrchamberchamberrange = re.match(r"(was )?not a candidate for reelection in (?P<end_year>\d{4}) to the (United States |U.( )?S. )?(House of Representatives|Senate).* but was elected.*(?P<chamber>House of Representatives|Senate) and served from (?P<start_term>[A-Z][a-z]+ \d+, \d{4}), to (?P<end_term>[A-Z][a-z]+ \d+, \d{4})", fact)
    match_yrchamberdate = re.match(r"(was )?not a candidate for reelection, but was a candidate in \d{4} to the United States Senate .* commencing ((?P<start_date>[A-Z][a-z]+ \d+, \d{4}))$", fact)
    match_change_5 = re.match(r"(was )?not a candidate.* for reelection.* but was elected.*Senate (in |on .*)(?P<start_year>\d{4}).*", fact)
    match_change_6 = re.match(r"(was )?not a candidate.* for reelection.* but was elected.*(in |on .*)(?P<start_date>[A-Z][a-z]+ \d+, \d{4}).*term ending (?P<end_date>[A-Z][a-z]+ \d+, \d{4})(?!\d{4})+$", fact)
    match_change_7 = re.match(r"subsequently elected in the (?P<start_date>[A-Z][a-z]+ \d+, \d{4}) special election.*term ending (?P<end_date>[A-Z][a-z]+ \d+, \d{4})", fact)
    match_oath_of_office = re.search(r"took the oath of office on (?P<start_date>[A-Z][a-z]+ \d+, \d{4})", fact)

    if check_for_didnt_rerun(fact): 
        #print(f"***check_for_didnt_rerun: {fact}")
        return True, terms
    elif check_failed_run(fact):
        #print(f"***check_failed_run: {fact}")
        return True, terms
    elif match_start_1:
        #these all look like house
        start_date = datetime.strptime(match_start_1.group('start_date'), date_format)
        end_date = datetime.strptime(match_start_1.group('end_date'), date_format)
        terms.append([start_date, end_date, "h"])
        #print(f"match_start_1 {fact} = h = {start_date}-{end_date}")
        return True, terms
    elif match_start_2:
        start_date = datetime.strptime(match_start_2.group('start_date'), date_format)
        end_date = start_date + relativedelta(years=6)
        #print(f"match_start_2 {fact} = s = {start_date}-{end_date}")
        terms.append([start_date, end_date, "s"])    
        return True, terms
    elif match_start_3:
        start_year = int(match_start_3.group('start_year'))+1
        start_date = datetime.strptime(f"January 3, {start_year}", date_format)
        end_date = start_date + relativedelta(years=6)
        #print(f"match_start_3 {fact} = s = {start_date}, {end_date}")
        if len(terms)>0:
            if terms[-1][1] is None:
                terms[-1][1] = start_date
        terms.append([start_date, end_date, "s"])
        return True, terms
    elif match_start_4:
        #reelected in YR(, YR, and again in YR)? for the term ending in DATE. likely all senate
        end_date = datetime.strptime(match_start_4.group('end_date'), date_format)
        ch = None
        all_dates = re.findall(r"(\d{4})", fact)
        all_dates_int = [int(match) for match in all_dates]
        temp_list = []
        #date2 == first date
        date2 = datetime.strptime(f"January 3, {all_dates_int[0]+1}", date_format) 
        if len(terms)>0:
            #if terms exists, check if most recent one has nothing there. since reelected, can use this date as end date
            if terms[-1][1] is None:
                terms[-1][1] = date2


        for i in range(1, len(all_dates_int)-1):
            # The difference is current match - previous match
            diff = all_dates_int[i] - all_dates_int[i-1]
            if diff == 2: #house
                ch = "h"
                date1 = datetime.strptime(f"January 3, {all_dates_int[i-1]+1}", date_format)                
                date2 = datetime.strptime(f"January 3, {all_dates_int[i]+1}", date_format)
                temp_list.append([date1, date2, ch])
                continue
            elif diff == 6: #senate
                ch = "s"
                date1 = datetime.strptime(f"January 3, {all_dates_int[i-1]+1}", date_format)                
                date2 = datetime.strptime(f"January 3, {all_dates_int[i]+1}", date_format)
                temp_list.append([date1, date2, ch])
                continue
            else: #something went wrong
                print(f"Something went wrong here: {all_dates_int}")
        if ch is None:
            diff = end_date.year - date2.year
            if diff == 2:
                ch = "h"
            elif diff == 6:
                ch = "s"
            else:
                ch = "n"
        temp_list.append([date2, end_date, ch])
        #print(f"match_start_4 {fact} = {ch} = {temp_list}")
        terms.extend(temp_list)
        #print(terms)
        return True, terms
    elif match_start_5:
        start_year = int(match_start_5.group('start_year'))+1
        start_date = datetime.strptime(f"January 3, {start_year}", date_format)
        end_date = datetime.strptime(match_start_5.group('end_date'), date_format)
        #print(f"match_start_5 {fact} = s = {start_date}-{end_date}")
        terms.append([start_date, end_date, "s"])
        return True, terms
    elif match_start_6:
        start_date = datetime.strptime(match_start_6.group('start_date'), date_format)
        end_date = datetime.strptime(match_start_6.group('end_date'), date_format)
        #print(f"match_start_6 {fact} = h = {start_date}-{end_date}")
        terms.append([start_date, end_date, "h"])
        return True, terms
    elif match_start_7:
        start_year = match_start_7.group('start_year')
        start_date = datetime.strptime(f"January 3, {start_year}", date_format)
        #print(f"match_start_7 {fact} = idk = {start_date}")
        terms.append([start_date, None, "n"])
        return True, terms
    #the match_start_present are all for HOR: end_date if present is just the next odd year
    elif match_start_present_1:
        start_date = datetime.strptime(match_start_present_1.group('start_date'), date_format)
        current_year = datetime.today().year
        if current_year%2 == 1:
            end_date = datetime.strptime(f"January 3, {current_year+2}", date_format)
        else:
            end_date = datetime.strptime(f"January 3, {current_year+1}", date_format)

        #print(f"match_start_present_1 {fact} = h = {start_date}-{end_date}")
        terms.append([start_date, end_date, "h"])
        return True, terms    
    elif match_start_present_2:
        start_year = match_start_present_2.group('start_year')
        start_date = datetime.strptime(f"January 3, {start_year}", date_format)
        current_year = datetime.today().year
        if current_year%2 == 1:
            end_date = datetime.strptime(f"January 3, {current_year+2}", date_format)
        else:
            end_date = datetime.strptime(f"January 3, {current_year+1}", date_format)
        #print(f"match_start_present_2 {fact} = h = {start_date}-{end_date}")
        terms.append([start_date, end_date, "h"])
        return True, terms  
    elif match_start_present_3:
        start_date = datetime.strptime(match_start_present_3.group('start_date'), date_format)
        current_year = datetime.today().year
        if current_year%2 == 1:
            end_date = datetime.strptime(f"January 3, {current_year+2}", date_format)
        else:
            end_date = datetime.strptime(f"January 3, {current_year+1}", date_format)
        #print(f"match_start_present_3 {fact} = h = {start_date}-{end_date}")
        terms.append([start_date, end_date, "h"])
        return True, terms  
    elif match_start_present_4:
        #only get congress, convert to year
        start_year, end_year = get_years_from_congress(fact)
        start_date = datetime.strptime(f"January 3, {start_year}", date_format)
        end_date = datetime.strptime(f"January 3, {end_year}", date_format)
        #print(f"match_start_present_4 {fact} = h = {start_date}-{end_date}")
        terms.append([start_date, end_date, "h"])
        return True, terms
    elif match_start_present_5:
        start_date = datetime.strptime(match_start_present_5.group('start_date'), date_format)
        end_date = datetime.strptime(match_start_present_5.group('end_date'), date_format)
        if len(terms) > 0:
            if terms[-1][1] is None:
                terms[-1][1] = start_date #if had an oath, set the end to start_date
        #print(f"match_start_present_5 {fact} = h = {start_date}-{end_date}")
        terms.append([start_date, end_date, "h"])
        return True, terms
    elif match_start_present_PR:
        #for PR, the term is 4 years
        start_date = datetime.strptime(match_start_present_PR.group('start_date'), date_format)
        end_date = start_date + relativedelta(years=4)
        #print(f"match_start_present_PR {fact} = h = {start_date}-{end_date}")
        terms.append([start_date, end_date, "h"])
        return True, terms
    elif match_yrchamberchamberdate: 
        #NOT USED
        end_year = int(match_yrchamberchamberdate.group('end_year'))+1
        end_date = datetime.strptime(f"January 3, {end_year}", date_format)
        start_date = datetime.strptime(match_yrchamberchamberdate.group('start_date'), date_format)
        chamber = match_yrchamberchamberdate.group('chamber')
        if chamber == "House of Representatives":
            ch = 'h'
        elif chamber == "Senate":
            ch = 's'
        else:
            ch = 'n'
        terms.append([start_date, end_date, ch])
        print(f"yccd {fact} = {ch} = {start_date}, {end_date}")
        return True, terms
    elif match_yrchamberchamber1: 
        #NOT USED
        end_year = int(match_yrchamberchamber1.group('end_year'))+1
        end_date = datetime.strptime(f"January 3, {end_year}", date_format)
        chamber = match_yrchamberchamber1.group('chamber')
        if chamber == "House of Representatives":
            ch = 'h'
        elif chamber == "Senate":
            ch = 's'
        else:
            ch = 'n'
        terms.append([None, end_date, ch])
        print(f"!!!ycc1 {fact} = {ch} = {end_date}")
        return True, terms
    elif match_yrchamberchamber2: 
        #NOT USED
        end_year = int(match_yrchamberchamber2.group('end_year'))+1
        end_date = datetime.strptime( f"January 3, {end_year}", date_format)
        chamber = match_yrchamberchamber2.group('chamber')
        if chamber == "House of Representatives":
            ch = 'h'
        elif chamber == "Senate":
            ch = 's'
        else:
            ch = 'n'
        terms.append([None, end_date, ch])
        print(f"!!!ycc2 {fact} = {end_date}")     
        return True, terms
    elif match_chamberyrchamber: 
        #NOT USED
        start_year = int(match_chamberyrchamber.group('end_year'))+1
        start_date = datetime.strptime(f"January 3, {end_year}", date_format)
        chamber = match_yrchamberchamber2.group('chamber')
        if chamber == "House of Representatives":
            ch = 'h'
            end_date = start_date + relativedelta(years=2)
        elif chamber == "Senate":
            ch = 's'
            end_date = start_date + relativedelta(years=6)
        else:
            ch = 'n'
            end_date = None
        terms.append([start_date, end_date, ch])  
        print(f"cyc {fact} = {ch} = {end_date}")
        return True, terms
    elif match_chamberchamberdate_s:
        start_date = datetime.strptime(match_chamberchamberdate_s.group('start_date'), date_format)
        end_date = start_date + relativedelta(years=6)
        #print(f"ccds {fact} = s = {start_date}-{end_date}")
        terms.append([start_date, end_date, "s"])
        return True, terms
    elif match_chamberchamberdate_h:
        start_date = datetime.strptime(match_chamberchamberdate_h.group('start_date'), date_format)
        end_date = start_date + relativedelta(years=2)
        #print(f"ccdh {fact} = h = {start_date}-{end_date}")
        terms.append([start_date, end_date, "h"])
        return True, terms
    elif match_chamberchamberdateend:
        start_date = datetime.strptime(match_chamberchamberdateend.group('start_date'), date_format)
        end_date = datetime.strptime(match_chamberchamberdateend.group('end_date'), date_format)
        #print(f"ccde {fact} = s_se = {end_date - start_date}")
        terms.append([start_date, end_date, "s_se"])
        return True, terms
    elif match_chamberyrchamberdate:
        #NOT USED
        end_year = int(match_chamberyrchamberdate.group('end_year'))+1
        end_date = datetime.strptime(f"January 3, {end_year}", date_format)
        start_date = datetime.strptime(match_chamberyrchamberdate.group('start_date'), date_format)
        chamber = match_chamberyrchamberdate.group('chamber')
        if chamber == "House of Representatives":
            ch = 'h'
        elif chamber == "Senate":
            ch = 's'
        else:
            ch = 'n'
        terms.append([None, end_date, ch])  
        print(f"cycd {fact} = {ch} = {start_date}-{end_date}")
        return True, terms
    elif match_chamberyrchamberyr:
        start_year = int(match_chamberyrchamberyr.group('start_year'))+1
        start_date = datetime.strptime(f"January 3, {start_year}", date_format)
        end_date = start_date + relativedelta(years=6)
        #print(f"cycy {fact} = senate = {start_date}-{end_date}")
        terms.append([start_date, end_date, "s"])
        return True, terms
    elif match_chamberyrchamberrange:
        #NOT USED
        end_year = int(match_chamberyrchamberrange.group('end_year'))+1
        end_date = datetime.strptime(f"January 3, {end_year}", date_format)
        start_term = datetime.strptime(match_chamberyrchamberrange.group('start_term'), date_format)
        end_term = datetime.strptime(match_chamberyrchamberrange.group('end_term'), date_format)
        if terms[-1][1] is None:
            terms[-1][1] = end_date
        
        chamber = match_chamberyrchamberrange.group('chamber')
        if chamber == "House of Representatives":
            ch = 'h'
        elif chamber == "Senate":
            ch = 's'
        else:
            ch = 'n'
        terms.append([None, end_date, ch])  
        print(f"cycr{fact} = switched chambers {end_date}, in new chamber{ch} {start_term}-{end_term}")
        return True, terms
    elif match_yrchamberchamberrange:
        #NOT USED
        end_year = int(match_yrchamberchamberrange.group('end_year'))+1
        end_date = datetime.strptime(f"January 3, {end_year}", date_format)
        start_term = datetime.strptime( match_yrchamberchamberrange.group('start_term'), date_format)
        end_term = datetime.strptime(match_yrchamberchamberrange.group('end_term'), date_format)
        if terms[-1][1] is None:
            terms[-1][1] = end_date
        chamber = match_yrchamberchamberrange.group('chamber')
        if chamber == "House of Representatives":
            ch = 'h'
        elif chamber == "Senate":
            ch = 's'
        else:
            ch = 'n'
        print(f"yccr{fact} = switched chambers {end_date}, in new chamber {ch} {start_term}-{end_term}")
        terms.append([None, end_date, ch])  
        return True, terms
    elif match_yrchamberdate:
        #NOT USED
        start_date = datetime.strptime(match_yrchamberdate.group('start_date'), date_format)
        end_date = start_date + relativedelta(years=6)
        print(f"ycd {fact} = s = {start_date}")
        terms.append([start_date, end_date, "s"])
        return True, terms
    elif match_change_1:
        #NOT USED
        start_date = datetime.strptime(match_change_1.group('start_date'), date_format)
        end_date = start_date + relativedelta(years=6)
        print(f"match_change_1 {fact} = s = {start_date}")
        terms.append([start_date, end_date, "s"])
        return True, terms
    elif match_change_2:
        #NOT USED
        start_year = match_change_2.group('start_year')
        start_date = datetime.strptime(f"January 3, {start_year}", date_format)
        end_date = start_date + relativedelta(years=6)
        print(f"match_change_2 {fact} = s = {start_date}")
        terms.append([start_date, end_date, "s"])
        return True, terms
    elif match_change_3:
        #NOT CATCHING
        start_date = datetime.strptime( match_change_3.group('start_date'), date_format)
        end_date = start_date + relativedelta(years=6)
        print(f"match_change_3 {fact} = s = {start_date}")
        terms.append([start_date, end_date, "s"])
        return True, terms
    elif match_change_3p5:
        start_date = datetime.strptime( match_change_3p5.group('start_date'), date_format)
        #print(f"match_change_3p5 {fact} = s = {start_date}")
        terms.append([start_date, None, "s_se"])
        return True, terms
    elif match_change_4:
        start_year = match_change_4.group('start_year')
        start_date = datetime.strptime(f"January 3, {start_year}", date_format)
        end_date = start_date + relativedelta(years=6)
        #print(f"match_change_4 {fact} = s = {start_date}-{end_date}")
        terms.append([start_date, end_date, "s"])
        return True, terms
    elif match_change_5:
        start_year = int(match_change_5.group('start_year'))+1
        start_date = datetime.strptime(f"January 3, {start_year}", date_format)
        end_date = start_date + relativedelta(years=6)
        #print(f"match_change_5 {fact} = s = {start_date}-{end_date}")
        terms.append([start_date, end_date, "s"])
        return True, terms
    elif match_change_6:
        #NOT USED
        start_date = datetime.strptime(match_change_6.group('start_date'), date_format)
        end_date = datetime.strptime(match_change_6.group('end_date'), date_format)
        print(f"match_change_6 {fact} = s = {start_date}={end_date}")
        terms.append([start_date, end_date, "s"])
        return True, terms
    elif match_change_7:
        start_date = datetime.strptime(match_change_7.group('start_date'), date_format)
        end_date = datetime.strptime(match_change_7.group('end_date'), date_format)
        if len(terms) > 0:
            if terms[-1][1] is None:
                terms[-1][1] = start_date
        #print(f"match_change_7 {fact} = n_se = {end_date - start_date}")
        terms.append([start_date, end_date, "n_se"])
        return True, terms
    elif match_reelection_3:
        start_date = datetime.strptime(match_reelection_3.group('start_date'), date_format)
        end_date = datetime.strptime(match_reelection_3.group('end_date'), date_format)
        #print(f"match_reelection_3 {fact} = h = {start_date}-{end_date}")
        terms.append([start_date, end_date, "h"])
        return True, terms
    elif match_reelection_4:
        start_year = int(match_reelection_4.group('start_year')) + 1
        start_date = datetime.strptime(f"January 3, {start_year}", date_format)
        end_date = datetime.strptime(match_reelection_4.group('end_date'), date_format)
        terms.append([start_date, end_date, "s"])
        #print(f"match_reelection_4 {fact} = s = {end_date}, {start_date}")
        return True, terms
    elif match_reelection_5:
        #no terms, should be house. reelected, means merge with previous if has None
        start_date = datetime.strptime(match_reelection_5.group('start_date'), date_format)
        end_date = datetime.strptime(match_reelection_5.group('end_date'), date_format)
        if len(terms)>0 and terms[-1][1] is None:
            terms[-1][1] = end_date
        else:
            terms.append([start_date, end_date, "h"])
        #print(f"match_reelection_4 {fact} = h = {end_date}, {start_date}")
        return True, terms
    elif match_end_2 or match_end_3:
        #print(f"***match_end_2/3: {fact}")
        return True, terms
    elif match_takeover_1: 
        end_date = datetime.strptime(match_takeover_1.group('end_date'), date_format)
        #print(f"match_takeover_1 {fact} = s = {end_date}")
        terms.append([None, end_date, "s"])
        return True, terms
    elif match_takeover_2: 
        start_date = datetime.strptime(match_takeover_2.group('start_date'), date_format)
        #print(f"match_takeover_2 {fact} = s = {start_date}")
        if len(terms)>0 and terms[-1][0] is None:
            terms[-1][0] = start_date
        else:
            terms.append([start_date, None, "s"])
        return True, terms
    elif match_takeover_3: 
        #not explicitly senate
        start_date = datetime.strptime(match_takeover_3.group('start_date'), date_format)
        #print(f"match_takeover_3 {fact} = n_se = {start_date}")
        terms.append([start_date, None, "n_se"])
        return True, terms
    elif match_takeover_3s: 
        #senate explicitly
        #no end date, assume they are interim and will only take over until the next election cycle
        #next election cycle = the next year
        start_date = datetime.strptime(match_takeover_3s.group('start_date'), date_format)
        start_year = start_date.year
        end_date = datetime.strptime(f"January 3, {start_year+1}", date_format)
        #print(f"match_takeover_3 {fact} = s_se = {start_date}")
        terms.append([start_date, end_date, "s_se"])
        return True, terms
    elif match_takeover_4: 
        start_date = datetime.strptime(match_takeover_4.group('start_date'), date_format)
        current_year = datetime.today().year
        if current_year%2 == 1:
            end_date = datetime.strptime(f"January 3, {current_year+2}", date_format)
        else:
            end_date = datetime.strptime(f"January 3, {current_year+1}", date_format)
        #print(f"match_takeover_4 {fact} = n_se = {start_date}-{end_date}")
        terms.append([start_date, end_date, "n_se"])
        return True, terms
    elif match_takeover_5: 
        end_date = datetime.strptime(match_takeover_5.group('end_date'), date_format)
        start_date = datetime.strptime(match_takeover_5.group('start_date'), date_format)
        terms.append([start_date, end_date, "s_se"])
        #print(f"match_takeover_5 {fact} = s_se = {start_date}-{end_date}")
        return True, terms
    elif match_takeover_6: 
        #should be senate since "term ending"
        end_date = datetime.strptime(match_takeover_6.group('end_date'), date_format)
        start_year = match_takeover_6.group('start_year')
        start_date = datetime.strptime(f"January 3, {start_year}", date_format)
        #print(f"match_takeover_6 {fact} = s_se = {start_date}-{end_date}")
        if len(terms) > 0:
            if terms[-1][1] is None: #coming from oath, replace end_date with start_date
                terms[-1][1] = start_date
        terms.append([start_date, end_date, "s_se"])
        return True, terms
    elif match_takeover_7: 
        start_date = datetime.strptime(match_takeover_7.group('start_date'), date_format)
        #print(f"match_takeover_7 {fact} = n_se = {start_date}")
        if len(terms) > 0:
            if terms[-1][1] is None: #coming from oath, replace end_date with start_date
                terms[-1][1] = start_date
        terms.append([start_date, None, "n_se"])
        return True, terms
    elif match_takeover_8:
        start_year = match_takeover_8.group('start_year') 
        start_date = datetime.strptime(f"January 3, {start_year}", date_format)
        #print(f"match_takeover_8 {fact} = n_se = {start_date}")
        if len(terms) > 0:
            if terms[-1][1] is None: #coming from oath, replace end_date with start_date
                terms[-1][1] = start_date
        terms.append([start_date, None, "n_se"])
        return True, terms
    elif match_takeover_9:
        start_year, end_year = get_years_from_congress(fact)
        start_date = datetime.strptime(f"January 3, {start_year}", date_format)
        end_date = datetime.strptime(f"January 3, {end_year}", date_format)
        print(f"match_takeover_9 {fact} = n = {start_date}-{end_date}")
        terms.append([start_date, end_date, "n"])
        return True, terms
    elif match_takeover_10:
        start_year, end_year = get_years_from_congress(fact)
        start_date = datetime.strptime(f"January 3, {start_year}", date_format)
        end_date = datetime.strptime(f"January 3, {end_year}", date_format)
        print(f"match_takeover_10 {fact} = n_se = {start_date}-{end_date}")
        terms.append([start_date, end_date, "n_se"])
        return True, terms
    elif match_oath_of_office: 
        start_date = datetime.strptime(match_oath_of_office.group('start_date'), date_format)
        #print(f"oath_of_office: {fact} = idk = {start_date}")
        if len(terms)>0:
            if terms[-1][0] is None:
                terms[-1][0] = start_date
        else:
            terms.append([start_date, None, "oath"])
        return True, terms
    elif re.match(r"^(?!unsuccessful).*special election.*$", fact):
        #print(f"***unsuccessful special election: {fact}")
        return True, terms
    elif "inaugurated" in fact:
        #print(f"***inaugurated: {fact}")
        return True, terms
    elif "was reelected" in fact:
        #print(f"***was reelected: {fact}")
        return True, terms
    elif fact.startswith(("not a candidate ", "was not a candidate ")): 
        if re.search(r"\d{4}", fact): #if a date is here, check if we should save it
            match_yr_present = re.match(r"(was )?not a candidate for re(election|nomination) in (?P<end_date>\d{4})", fact)
            match_congress_present = re.match(r"(was )?not a candidate for reelection to the (([A-Z][a-z]+)( [A-Z][a-z]+|-[a-z]+)+) Congress", fact)

            if match_yr_present:
                end_date = int(match_yr_present.group('end_date'))+1
                return True, terms
            elif match_congress_present: #check for congress
                end_date = get_years_from_congress(fact)[0]
                return True, terms
            else: #date but not of congress or year of not running. return False
                return False, terms

        else: #no date present
            return False, terms
    else:
        return False, terms




def check_for_personal(fact):
    """
    Docstring for check_for_personal
    Checks for relevant family members.
    Format: (relation to person), a Role from Home 
    :param fact: Description
    """
    if re.match(r"\(.*\), a (?:Senator |Representative .*)", fact): #Relevant family members
        return True
    elif "immigrated" in fact:
        return True
    elif re.match(r"an enrolled member of the .* Nation", fact):
        return True
    else:
        return False


def check_gov_highlights(fact):
    fact_lower = fact.lower()
    if "to conduct the impeachment" in fact_lower: #if they conducted an impeachment thing
        #print(f"to conduct theimpeachment: {fact}")
        return True
    elif re.match(r".*\(.*Congress.*\).*", fact): #some committee work
        #print(f"(Congress): {fact}")
        return True
    elif "in the Cabinet" in fact:
        #print(f"in the Cabinet: {fact}")
        return True
    elif any(re.search(rf"\b{re.escape(cabinet)}\b", fact ) for cabinet in CABINET):
        #print(f"Cabinet: {fact}")
        return True
    elif re.search(r"(Republican|Democratic) Conference", fact): #this is in congress, put it in highlights
        #print(f"Conference: {fact}")
        return True
    else:
        return False
        

def check_accolades(fact):
    if "award" in fact:
        return True
    elif "Purple Heart" in fact:
        return True


def clean_profiletext_data(data):
    data = data.replace("&amp;", "&")
    data = data.replace("&aacute;", "a")
    data = data.replace("&uacute;", "u")
    data = data.replace("&rsquo;", "'")
    data = data.replace("&nbsp;", "")
    data = data.replace("&ndash;", "-")
    data = data.replace("&eacute;", "e")
    data = data.replace("<p>", "")
    data = data.replace("’", "'")
    return data



def get_profile_photo(bioguide_data, rep):
    """
    Docstring for get_profile_photo
    Updates the rep to add the bioguide photo path as well
    
    :param bioguide_data: Input bioguide_data of rep
    :param rep: Starting rep info from congressmen.json
    """
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



def add_bioguide_congress_data(list_of_dict, generated_outputs):
    """
    Using the data loaded from bioguide.congress.gov, which has been downloaded to bioguide_data dir,
    update the current json with the relevant info

    """

    seen_rep = {}
    uncaptured_length = 0
    #not case sensitive
    

    local_legislation = ("general assembly", "state senate", "state house of representatives", 
                         "mayor ", "mayor,", "city council", "state assembly")


    #case sensitive

    military_record = ("United States Army", "United States Nav", "United States Marine", 
                       "United States Coast Guard", 
                       "United States Air Force", "U.S. Army", "National Guard", 
                       "U.S. Marine", "Judge Advocate", "judge advocate", "Marine Corps",
                       "discharged", "enlisted", "prisoner of war", "commanded the ", "Normandy",
                       "War in Afghanistan")
    bad_behavior = ("expelled", "censured", "reprimanded", "convicted", 
                    "sentence", "pardon", "indicted", "acquitted", "charges", 
                    "evidence", "denounced")


    
    for rep in list_of_dict:
        #print(f"starting for {rep.get('name')}")
        education = []
        military_history = []
        illegal= []
        work_history = []
        gov_highlights = []
        accolades = []
        lawyer_stuff = []
        personal = [] 
        uncaptured = []
        term_info = []
        valid_roles = []
        terms = []
        hold = ""
        birthplace = ""

        #Load the json for the current bioguideID
        #A problem because there are multiple instances of bioguideID in the original congressmen.json.
        #Need to clean those up before can do this, might not be worth it.
        #if rep.get('bioguideID') in seen_rep:
        #    continue
        #else:
        #    seen_rep[rep.get('bioguideID')] = 1
            
        #newjson_path = os.path.join(generated_outputs, "..", "..", "bioguide_data", f"{rep.get('bioguideID')}.json")

        newjson_path = os.path.join(generated_outputs, "bioguide_data", f"{rep.get('bioguideID')}.json")
        bioguide_data = load_json(newjson_path)
        if bioguide_data is None:
            break
            #print(f"{rep.get('bioguideID')} has no info")
        if len(bioguide_data.keys())==1 and "data" in bioguide_data:
            bioguide_data = bioguide_data['data']

        get_profile_photo(bioguide_data, rep)


        #Parse the profileText section for more data
        profiletext = bioguide_data.get('profileText')

        if profiletext is not None:
            #DEBUG uncomment if trying to figure out the text for a particular person
            #if rep.get('name') == "Alan Armstrong":
            #    print(f"original profiletext: {profiletext}")
            data = clean_profiletext_data(profiletext)
            data = data.split(";")
            chamber = None
            ########## FACT TIDBITS ARE HERE ##########
            for fact in data:
                fact_used = False
                fact = fact.lstrip()
                fact = to_state_code(fact, None, False) #convert any state abbreviations to postal code
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

                
                if dont_use_this_line(fact):
                    continue
                elif get_chamber_history(fact) is not None: #True if found a "a Senator|Representative"
                    chamber = get_chamber_history(fact)
                    continue
                elif check_for_term_info(fact, terms)[0]:
                    #_,terms = check_for_term_info(fact, terms)
                    term_info.append(fact)
                    fact_used = True
                    continue
                elif re.match(r".*resumed.*", fact): #Resumed stuff, often practice of law
                    #print(fact) #TODO this is actually work history possibly
                    continue

                ###Random facts that we'll include
                elif any(sub in fact for sub in bad_behavior): #illegal behavior
                    fact_used = True
                    illegal.append(fact)
                elif check_gov_highlights(fact):
                    fact_used = True
                    gov_highlights.append(fact)
                elif "secretary of " in fact_lower:
                    fact_used = True
                    work_history.append(fact)
                elif check_accolades(fact):
                    fact_used = True
                    accolades.append(fact)
                elif check_for_personal(fact):
                    fact_used = True
                    personal.append(fact)


                ############DEGREE FILTERS###############

                elif any(re.search(rf"(?<![a-zA-Z\.]){re.escape(sub)}(?![a-zA-Z])", fact) for sub in VALID_DEGREES):
                    #Degree listed, add to education
                    fact = fact.replace("B. S.", "B.S.")
                    fact = fact.replace("M. Div", "M.Div")
                    fact = fact.replace("D. Div", "D.Div")
                    fact = fact.replace("M. D.", "M.D.")
                    fact_used = True
                    if ("J.D. Vance" in fact):
                        term_info.append(fact) #TODO see if this is where this fact should go
                    else:
                        education.append(fact)

                elif fact_lower.startswith("graduate"):
                    pattern = r"(?:graduated|graduate)(?! work| assistant)(.*)"
                    match = re.search(pattern, fact, re.I)
                    if not match:
                        #graduate work, goes into work category
                        fact_used = True
                        work_history.append(fact)
                    else:
                        #else is education history
                        fact_used = True
                        education.append(fact)

                ############ MILITARY RECORD ################
                ###Get military record
                elif any(sub in fact for sub in military_record):
                    fact_used = True
                    military_history.append(fact)
                elif fact_lower.startswith("attended "): #check after military record for people who attended military schools
                    fact_used = True
                    education.append(fact)
                elif re.search(r".* [Bb]ar[s,]? ?.*", fact): #lawyer stuff related to the bar
                    fact_used = True
                    lawyer_stuff.append(fact)
                elif "commenced practice" in fact:
                    fact_used = True
                    lawyer_stuff.append(fact)

                ###Get work history

                elif any(sub in fact_lower for sub in local_legislation):
                    fact_used = True
                    work_history.append(fact)
                elif any(sub in fact_lower for sub in JOBS):
                    fact_used = True
                    work_history.append(fact)


                ############ BIRTHPLACE ############
                elif fact_lower.startswith("born "):
                    #check for birthdate, add as backup, remove it:
                    pattern_date = r"((January|February|March|April|May|June|July|August|September|October|November|December)( \d{1,2},)? \d{4})"
                    match = re.search(pattern_date, fact)
                    if match:
                        pattern_date_clean = r"((January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4})"
                        check_me = match.group()
                        match_date = re.search(pattern_date_clean, check_me)
                        if not match_date:
                            birthday = None
                        else:
                            fact_used = True
                            datetime_object = datetime.strptime(match_date.group(), '%B %d, %Y')
                            birthday = datetime_object.strftime('%Y-%m-%d')
                        cleaned = re.sub(pattern_date, '', fact)

                    #Birthplace
                    pattern_birthplace = r"born (?:.* in )?([\w,\. -]+)"
                    match = re.search(pattern_birthplace, cleaned, re.I)
                    if not match:
                        birthplace = ""
                    elif cleaned == "born on ":
                        birthplace = ""
                    else: 
                        #Add to birthplace
                        birthplace = match.group(1)
                        if birthplace.startswith("in "):
                            birthplace = birthplace[2:]
                        fact_used = True
                        birthplace = check_birthplace(birthplace)

                else:
                    uncaptured.append(fact)
                    #print(f"uncaptured: {fact}")
                    continue

                if not fact_used:
                    print(f"Not used: {fact}")
            #End looping through fact block
        

        #final updates to clean things up
        education = check_education(education)
        

        #Update the JSON
        birthdate = bioguide_data.get('birthDate', None)
        if birthdate is None:
            birthdate = birthday

        rep.update({'birthplace': birthplace})

        rep.update({'birthDate': birthdate})
        rep.update({'term_info': term_info})
        
        #if (rep.get('name') == "Darrell Issa"):
        #    print(f"CHECKING: {terms}")
        new_terms = convert_terms_to_useful(terms)
        #if (rep.get('name') == "Darrell Issa"):
        #    print(f"CHECKING: {new_terms}")
        
        if new_terms is not None:
            rep.update({"terms": new_terms[-1]})
            #print(f"{rep.get('name')}: {new_terms}")
        else:
            print(f"new_terms not found for {rep.get('name')}")
        rep.update({"valid_roles": valid_roles})
        rep.update({'education': education})
        rep.update({'military': military_history})
        rep.update({'illegal': illegal })
        rep.update({'work_history': work_history})
        rep.update({'gov_highlights': gov_highlights})
        rep.update({'accolades': accolades})
        #rep.update({'lawyer_stuff': lawyer_stuff})
        rep.update({'personal': personal})

        rep.update({'uncaptured': uncaptured})
        uncaptured_length += len(uncaptured)
        #print("\n".join(uncaptured))

    print(f"Uncaptured items remaining: {uncaptured_length}")
    return list_of_dict


############################################
def convert_terms_to_useful(terms):
    """
    terms (list of lists): list of [start_year, end_year, chamber]
    1. get difference between years. if <=2 years, house. if <=6 years, senate. else print out to debug
    3. 

    return the past terms (should only be len 1-2, maybe 3):
        [
        [YYYY-MM-DD, YYYY-MM-DD],
        [YYYY-MM-DD, YYYY-MM-DD]
        ]
    """
    if len(terms)==0:
        return None
    
    final_list = []
    date_format = "%Y-%m-%d"

    #replace the None if present
    #if terms[0][1] is None:
    #    terms[0][1] = terms[0][0] + relativedelta(years=2)

    if len(terms) == 1:
        return [[terms[0][0].strftime(date_format), terms[0][1].strftime(date_format)]]


    start_date, end_date, _ = terms[0]
    for i in range(1, len(terms)):
        prev_start, prev_end, prev_ch = terms[i-1]
        curr_start, curr_end, curr_ch = terms[i]

        #if the end_date and start_date match, then might want to combine. Check if they're the same term width
        if prev_end == curr_start:
            #if dates match and chambers match, join.
            if prev_ch == curr_ch:
                end_date = curr_end
            elif prev_ch == "s" or prev_ch == "s_se":
                #senate to house = upload
                if curr_ch == "h" or curr_ch == "h_se":
                    final_list.append([start_date.strftime(date_format), end_date.strftime(date_format)])
                    start_date = curr_start
                    end_date = curr_end  
                elif curr_ch == "s" or curr_ch == "s_se":
                    #extend run of senate time
                    end_date = curr_end
                #senate to unknown special election should be senate to senate. means were appointed and then elected
                elif curr_ch == "n_se":
                    end_date = curr_end
                else:
                    print(f"Uncaught: {terms[i-1]}-{terms[i]}")
                    final_list.append([start_date.strftime(date_format), end_date.strftime(date_format)])
                    start_date = curr_start
                    end_date = curr_end    
            elif prev_ch == "h" or prev_ch == "h_se":
                #house to senate = upload
                if curr_ch == "s" or curr_ch == "s_se":
                    final_list.append([start_date.strftime(date_format), end_date.strftime(date_format)])
                    start_date = curr_start
                    end_date = curr_end  
                elif curr_ch == "h" or curr_ch == "h_se":
                    #extend run of house time
                    end_date = curr_end 
                #house to unknown should be house to senate
                elif curr_ch == "n_se":
                    final_list.append([start_date.strftime(date_format), end_date.strftime(date_format)])
                    start_date = curr_start
                    end_date = curr_end  
                else:
                    print(f"Uncaught: {terms[i-1]}-{terms[i]}")
                    final_list.append([start_date.strftime(date_format), end_date.strftime(date_format)])
                    start_date = curr_start
                    end_date = curr_end   
            else:
                #days match but chamber changed. append what we've got and reset.
                final_list.append([start_date.strftime(date_format), end_date.strftime(date_format)])
                start_date = curr_start
                end_date = curr_end
                
        #if previous is special election, combine it with this one
        elif "se" in prev_ch:
            if "n" in curr_ch:
                print(f"Inconclusive what chamber these are, SE to N: {terms[i-1]} - {terms[i]}")
            else:
                end_date = curr_end
        
        #if current is "oath", it indicates a switch. upload what we have.
        elif curr_ch == "oath":
            final_list.append([start_date.strftime(date_format), end_date.strftime(date_format)])
            start_date = curr_start
            end_date = curr_end

        elif prev_ch == "s" or prev_ch == "s_se":
            #senate to house = upload
            if curr_ch == "h" or curr_ch == "h_se":
                final_list.append([start_date.strftime(date_format), end_date.strftime(date_format)])
                start_date = curr_start
                end_date = curr_end  
            #senate to unknown special election should be senate to senate. means were appointed and then elected
            elif curr_ch == "n_se":
                end_date = curr_end
            #senate to senate but dates don't match - noncontiguous runs, split
            elif curr_ch == "s":
                final_list.append([start_date.strftime(date_format), end_date.strftime(date_format)])
                start_date = curr_start
                end_date = curr_end  
            else:
                print(f"Uncaught: {terms[i-1]}-{terms[i]}")
                final_list.append([start_date.strftime(date_format), end_date.strftime(date_format)])
                start_date = curr_start
                end_date = curr_end  
        elif prev_ch == "h" or prev_ch == "h_se":
            #house to senate = upload
            if curr_ch == "s" or curr_ch == "s_se":
                final_list.append([start_date.strftime(date_format), end_date.strftime(date_format)])
                start_date = curr_start
                end_date = curr_end  
            #house to unknown should be house to senate
            elif curr_ch == "n_se":
                final_list.append([start_date.strftime(date_format), end_date.strftime(date_format)])
                start_date = curr_start
                end_date = curr_end  
            #house to house but dates don't match - noncontiguous runs, split
            elif curr_ch == "h":
                final_list.append([start_date.strftime(date_format), end_date.strftime(date_format)])
                start_date = curr_start
                end_date = curr_end  
            else:
                print(f"Uncaught: {terms[i-1]}-{terms[i]}")
                final_list.append([start_date.strftime(date_format), end_date.strftime(date_format)])
                start_date = curr_start
                end_date = curr_end  
        else:
            print(f"Uncaught: {terms[i-1]}-{terms[i]}")
            final_list.append([start_date.strftime(date_format), end_date.strftime(date_format)])
            start_date = curr_start
            end_date = curr_end  
        
        

    final_list.append([start_date.strftime(date_format), end_date.strftime(date_format)])
    return final_list




def convert_stringnum_to_num_congress(string):
    #One Hundred Fourth
    #One Hundred Nineteenth
    #Ninety-eighth
    pattern = r"(([A-Z][a-z]+)( [A-Z][a-z]+|-[a-z]+)+) Congress"
    match = re.search(pattern, string)
    return convert_stringnum_to_num(match.group(1))


def convert_stringnum_to_num(string):
    # Task:
    # if [] after the Congress, remove the number of congress
    # if standalone, replace with the date
    # if with other congress "and", combine the years

    nums = {"first":1, "second":2, "third":3, "fourth":4, "fifth":5, "sixth":6, "seventh":7, "eighth":8, "ninth":9, "tenth":10,
            "eleventh":11, "twelfth":12, "thirteenth":13, "fourteenth":14, "fifteenth":15, "sixteenth":16, "seventeenth":17, "eighteenth":18, 
            "nineteenth":19, "twentieth":20, "twenty":20, "thirtieth":30, "thirty":30, "fortieth":40, "forty":40, "fiftieth":50, "fifty":50, 
            "sixtieth":60, "sixty":60, "seventieth":70, "seventy":70, "eightieth":80, "eighty":80, "ninetieth":90, "ninety":90, 
            "hundred":100, "hundredth":100}
    

    pattern = r"([A-Z][a-z]+.*)"
    #-lower
    # Upper
    match = re.search(pattern, string)
    if match:
        congress = match.group(1)
        number_split = re.split(r"-|,|and| ", congress)
        num = 0
        for number in number_split:
            number = number.lower()
            if number == "":
                continue
            elif number == "one":
                continue
            elif number in nums:
                num += nums.get(number)
            else:
                print(f"No number found: {number} in {congress}")

        return num
    else:
        return 0


def get_years_from_congress(fact):
    """
    Docstring for get_years_from_congress
    Takes full fact, looks for a Congress, and converts to a start year
    
    :param fact: Whole string input
    Returns tuple (startyear, endyear) of a given congress found in the input fact
        if no input fact found, returns None
    """
    congress_no = convert_stringnum_to_num_congress(fact)
    if congress_no == 0:
        return None
    else:
        return congress_to_years(congress_no) 

def congress_to_years(congress_int):
    """
    Docstring for congress_to_years
    Convert congress # to a tuple (startyear, endyear)
    
    :param congress_int: int input of Congress #

    Return (startyear, endyear)
    """

    startyear = 1787 + congress_int*2
    endyear = startyear + 2

    return (startyear, endyear)


def to_state_code (str_in, delimiter, swap_full_state):
    """
    Convert to normal state codes. 
    States abbrs can be found in birthplace, work history

    Inputs:
        str_in: input string to be parsed
        delimiter: input string to split words by
        swap_full_state: boolean to indicate if you want to swap 
            full names to state codes

    Return:
        <str> parsed string

    """
    full_state_to_code = {
        "Alaska": "AK",
        "Arkansas": "AR",
        "Hawaii": "HI",
        "Florida": "FL",
        "Maine": "ME",
        "Idaho": "ID",
        "New Hampshire": "NH",
        "Ohio": "OH",
        "Texas": "TX",
        "Utah": "UT",
        "Iowa": "IA",

    }
    state_to_code = {
        "Ala.": "AL",
        "Ariz.": "AZ",
        "Ark.": "AR",
        "Calif.": "CA",
        "Colo.": "CO",
        "Conn.": "CT",
        "Del.": "DE",
        "Fla.": "FL",
        "Ga.": "GA",
        "Territory of Hawai": "HI",
        "Ill.": "IL",
        "Ind.": "IN",
        "Kans.": "KS",
        "Ky.": "KY",
        "La.": "LA",
        "Md.": "MD",
        "Mass.": "MA",
        "Mich.": "MI",
        "Minn.": "MN",
        "Miss.": "MS",
        "Mo.": "MO",
        "Mont.": "MT",
        "Nebr.": "NE",
        "Neb.": "NE",
        "Nev.": "NV", 
        "N.H.": "NH",
        "N.J.": "NJ",
        "N.Mex.": "NM",
        "N. Mex.": "NM",
        "N.Y.": "NY",
        "King": "NY",
        "N.C.": "NC",
        "N. Dak.": "ND",
        "N.D.": "ND",
        "Okla.": "OK",
        "Oreg.": "OR",
        "Ore.": "OR",
        "Pa.": "PA",
        "Penn.": "PA",
        "R.I.": "RI",
        "S.C.": "SC",
        "S.Dak.": "SD",
        "S. Dak.": "SD",
        "Tenn.": "TN",
        "Tex.": "TX",
        "Vt.": "VT",
        "Va.": "VA",
        "Wash.": "WA",
        "W. Va.": "WV",
        "W.Va.": "WV",
        "Wis.": "WI",
        "Wyo.": "WY"
    }

    #For cases where blindly search string, like work history
    if  delimiter is None:
        for key,val in state_to_code.items():
            str_in = str_in.replace(key, val)
        if swap_full_state:
            for key,val in full_state_to_code.items():
                str_in = str_in.replace(key, val)
        return str_in
    
    #Else split by delimiter
    else:
        words = str_in.split(delimiter)
        new_words = [state_to_code.get(word, word) for word in words]

        if swap_full_state:
            new_words = [full_state_to_code.get(word, word) for word in new_words]

        new_sentence = delimiter.join(new_words)
        return new_sentence


####################################################################################################


def add_bioguide(input_json, generated_outputs):
    """
    Takes the json string object and will save a congressmen_mod.json 
    
    Args: 
        input_json [JSON str]: congressmen.json contents with voting data

    """

    #with open(input_file, 'r', encoding='utf-8') as file:
    #    list_of_congressmen = json.load(file)

    if isinstance(input_json, str):
        list_of_congressmen = json.loads(input_json)
    elif isinstance(input_json, list):
        list_of_congressmen = input_json
    else:
        print("Invalid input type for add_bioguide. Expected string or list.")
        raise TypeError(f"Expected string or list, got {type(input_json)}")
    
    updated_list = add_bioguide_congress_data(list_of_congressmen, generated_outputs) #list of dicts
    return updated_list
