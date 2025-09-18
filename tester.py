import gen_reps_json
import gen_voting_record_json
import modify_reps
import modify_votes
import gen_xls
import add_bioguide
import gen_cards
import sys
import os
import time

##############################################
def check_reps_standalone():
    gen_reps_json.gen_reps_json()
    print(gen_reps_json.get_member_committee_info(["O000172"]))

def check_voting_record_standalone():
    gen_voting_record_json.gen_voting_record_json()    

def modify_votes_standalone():
    modify_votes.modify_votes("voting_records.json")

def modify_reps_standalone():
    """This calls add_bioguide internally, and assumes modify_votes has already been run. """
    modify_reps.modify_reps("congressmen.json", "vote_avg.json")   

def add_bioguide_standalone():
    add_bioguide.add_bioguide("congressmen.json")

def gen_cards_standalone():    
    gen_cards.gen_cards('congressmen_mod.json', test_card=True, dummy_img=False)
################################################

def check_gen_json():
    """Checks the generate JSON section, which pulls info from both reps and voting records"""
    gen_reps_json.gen_reps_json()
    gen_voting_record_json.gen_voting_record_json()    


def check_full_modify_json():
    """Checks the modify suite. Assumes you have the JSONs in place, will modify the voting record"""
    modify_votes.modify_votes("voting_records.json")
    modify_reps.modify_reps("congressmen.json", "vote_avg.json")   

def check_modify_to_card_gen():
    """Regenerates the congressmen_mod.json, then generates a test card"""
    check_full_modify_json()
    gen_cards_standalone()

def check_converting_string_to_num():
    """Checks the string to num for when the 119th Congress is written as One Hundred Nineteenth"""
    print(gen_cards.convert_stringnum_to_num("chair, Committee on Indian Affairs (One Hundred Thirteenth Congress [January 3, 2013-February 12, 2014]),"))
    print(gen_cards.convert_stringnum_to_num("Committee on Commerce, Science, and Transportation (One Hundred Seventeenth and One Hundred Eighteenth Congresses)."))
    print(gen_cards.convert_stringnum_to_num("chair, Committee on Education and the Workforce (One Hundred Fifteenth and One Hundred Eighteenth Congresses)"))
    print(gen_cards.convert_stringnum_to_num("chair, Committee on Rules (One Hundred Nineteenth Congress)."))
    print(gen_cards.convert_stringnum_to_num("chair, Committee on Homeland Security (One Hundred Tenth, One Hundred Eleventh, One Hundred Sixteenth, and One Hundred Seventeenth Congresses)"))
    print(gen_cards.convert_stringnum_to_num("minority leader (One Hundred Eighth, One Hundred Ninth, and One Hundred Twelfth through One Hundred Fifteenth Congresses)"))
    print(gen_cards.convert_stringnum_to_num("chair, Committee on Energy and Natural Resources (One Hundred Thirteenth Congress [January 3, 2013-February 12, 2014]), Committee on Finance (One Hundred Thirteenth Congress [February 12, 2014-January 3, 2015], One Hundred Seventeenth and One Hundred Eighteenth Congresses)."))
    print(gen_cards.convert_stringnum_to_num("chair, Committee on Veterans' Affairs (One Hundred Sixteenth [January 3, 2020-January 3, 2021] and One Hundred Nineteenth Congresses).</p>"))
        


if __name__ == "__main__":
    #Put only functions listed above here:
    #check_modify_to_card_gen()
    gen_cards_standalone()



