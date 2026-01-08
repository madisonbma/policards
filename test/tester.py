
import json
import sys
import os
import time

current_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)


import src.gen_reps_json
#from src import gen_reps_json
import src.gen_voting_record_json
import src.modify_reps
import src.modify_votes
#import src.gen_xls
import src.add_bioguide
import src.gen_cards
import src.gen_committees



##############################################
def check_reps_standalone():
    src.gen_reps_json.gen_reps_json()
    print(src.gen_reps_json.get_member_committee_info(["O000172"]))

def gen_voting_record_standalone():
    src.gen_voting_record_json.gen_voting_record_json()    

def modify_votes_standalone():
    voting_records = os.path.join("..", "src", "generated_outputs", "voting_records.json")
    voting_records_senate = os.path.join("..", "src", "generated_outputs", "voting_records_senate.json")
    if not os.path.exists(voting_records):
        print(f"Error: File not found at '{voting_records}'")
        return None
    elif not os.path.exists(voting_records_senate):
        print(f"Error: File not found at '{voting_records_senate}'")
        return None
    else:
        src.modify_votes.modify_votes(voting_records, voting_records_senate)

def modify_reps_standalone():
    """This calls add_bioguide internally, and assumes modify_votes has already been run. """
    congressmen = os.path.join("..", "src", "generated_outputs", "congressmen.json")
    vote_avg = os.path.join("..", "src", "generated_outputs", "vote_avg.json")
    if not os.path.exists(congressmen):
        print(f"Error: File not found at '{congressmen}'")
        return None
    elif not os.path.exists(vote_avg):
        print(f"Error: File not found at '{vote_avg}'")
        return None
    else:
        src.modify_reps.modify_reps(congressmen, vote_avg)   

def add_bioguide_standalone():
    """
    This actually might not work anymore... don't use this
    """
    congressmen = os.path.join("..", "src", "generated_outputs", "congressmen.json")
    if not os.path.exists(congressmen):
        print(f"Error: File not found at '{congressmen}'")
        return None
    else:
        src.add_bioguide.add_bioguide(congressmen)

def gen_committees_standalone():
    print(src.gen_committees.gen_committees())

def gen_cards_standalone():    
    congressmen_mod = os.path.join("..", "src", "generated_outputs", "congressmen_mod.json")
    if not os.path.exists(congressmen_mod):
        print(f"Error: File not found at '{congressmen_mod}'")
        return None
    else:
        src.gen_cards.gen_cards(congressmen_mod, test_card=True, dummy_img=False)
################################################

def check_gen_json():
    """Checks the generate JSON section, which pulls info from both reps and voting records"""
    src.gen_reps_json.gen_reps_json()
    src.gen_voting_record_json.gen_voting_record_json()    


def check_full_modify_json():
    """Checks the modify suite. Assumes you have the JSONs in place, will modify the voting record"""
    voting_records = os.path.join("..", "src", "generated_outputs", "voting_records.json")
    voting_records_senate = os.path.join("..", "src", "generated_outputs", "voting_records_senate.json")
    if not os.path.exists(voting_records):
        print(f"Error: File not found at '{voting_records}'")
        return None
    elif not os.path.exists(voting_records_senate):
        print(f"Error: File not found at '{voting_records_senate}'")
        return None
    else:
        src.modify_votes.modify_votes(voting_records, voting_records_senate)
    
    congressmen = os.path.join("..", "src", "generated_outputs", "congressmen.json")
    vote_avg = os.path.join("..", "src", "generated_outputs", "vote_avg.json")
    if not os.path.exists(congressmen):
        print(f"Error: File not found at '{congressmen}'")
        return None
    elif not os.path.exists(vote_avg):
        print(f"Error: File not found at '{vote_avg}'")
        return None
    else:
        src.modify_reps.modify_reps(congressmen, vote_avg)   

def check_modify_to_card_gen():
    """Regenerates the congressmen_mod.json, then generates a test card"""
    check_full_modify_json()
    gen_cards_standalone()

def check_converting_string_to_num():
    """Checks the string to num for when the 119th Congress is written as One Hundred Nineteenth"""
    print(src.gen_cards.convert_stringnum_to_num("chair, Committee on Indian Affairs (One Hundred Thirteenth Congress [January 3, 2013-February 12, 2014]),"))
    print(src.gen_cards.convert_stringnum_to_num("Committee on Commerce, Science, and Transportation (One Hundred Seventeenth and One Hundred Eighteenth Congresses)."))
    print(src.gen_cards.convert_stringnum_to_num("chair, Committee on Education and the Workforce (One Hundred Fifteenth and One Hundred Eighteenth Congresses)"))
    print(src.gen_cards.convert_stringnum_to_num("chair, Committee on Rules (One Hundred Nineteenth Congress)."))
    print(src.gen_cards.convert_stringnum_to_num("chair, Committee on Homeland Security (One Hundred Tenth, One Hundred Eleventh, One Hundred Sixteenth, and One Hundred Seventeenth Congresses)"))
    print(src.gen_cards.convert_stringnum_to_num("minority leader (One Hundred Eighth, One Hundred Ninth, and One Hundred Twelfth through One Hundred Fifteenth Congresses)"))
    print(src.gen_cards.convert_stringnum_to_num("chair, Committee on Energy and Natural Resources (One Hundred Thirteenth Congress [January 3, 2013-February 12, 2014]), Committee on Finance (One Hundred Thirteenth Congress [February 12, 2014-January 3, 2015], One Hundred Seventeenth and One Hundred Eighteenth Congresses)."))
    print(src.gen_cards.convert_stringnum_to_num("chair, Committee on Veterans' Affairs (One Hundred Sixteenth [January 3, 2020-January 3, 2021] and One Hundred Nineteenth Congresses).</p>"))
        

def check_check_education_bioguide():
    file_path = os.path.join("..", "src", "generated_outputs", "congressmen_mod.json")
    # 1. Check if the file exists first for cleaner error handling
    if not os.path.exists(file_path):
        print(f"Error: File not found at '{file_path}'")
        return None
    try:
        # 2. Use 'with open' to safely open and automatically close the file
        #    'r' means read mode, 'utf-8' is best practice for text data
        with open(file_path, 'r', encoding='utf-8') as file:
            # 3. Use json.load() to parse the file content into a dict
            list_of_congressmen = json.load(file)
            #return data_dictionary
            
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON file: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

    #list_of_congressmen = json.loads(file_path) #From json_string to JSON dict
    for person in list_of_congressmen:
        education = person.get('education')
        src.add_bioguide.check_education(education)




if __name__ == "__main__":
    #Put only functions listed above here:
    #gen_voting_record_standalone()
    #gen_committees_standalone()
    #check_modify_to_card_gen()
    check_full_modify_json()
    #gen_cards_standalone()
    #check_check_education_bioguide()


