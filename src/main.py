import src.gen_reps_json
import src.gen_voting_record_json
import src.modify_reps
import src.modify_votes
import src.gen_xls
import src.gen_cards
import sys
import os
import time

def get_yes_no_input(prompt):
    """
    Prompts the user for a 'y' or 'n' input and returns True for 'y' and False for 'n'.
    Handles case-insensitivity and invalid inputs by re-prompting.
    """
    while True:
        user_input = input(f"{prompt} (y/n): ").lower().strip()
        if user_input == 'y':
            return True
        elif user_input == 'n':
            return False
        else:
            print("Invalid input. Please enter 'y' or 'n'.")


if __name__ == "__main__":
    #Generate the representative json if it doesn't exist or if forcing override.
    root = os.path.dirname(os.path.abspath(__file__))
    root = os.path.join(root, os.path.pardir)

    congressmen_json = os.path.join(root, "src", "generated_outputs", "congressmen.json")
    if os.path.isfile(congressmen_json):
        modification_timestamp = os.path.getmtime(congressmen_json)
        readable_time = time.ctime(modification_timestamp)

        if get_yes_no_input(f"congressmen.json already exists, was created on {readable_time}. Do you want to force regeneration?"):
            print("Regenerating congressmen.json")
            src.gen_reps_json.gen_reps_json()
        else:
            print("Not regenerating, running with pre-existing congressmen.json.")    
    else:
        print("src/generated_outputs/congressmen.json does not exist. Generating...")
        src.gen_reps_json.gen_reps_json()

    #Generate the voting record json if it doesn't exist or if forcing override.
    voting_json = os.path.join(root, "src", "generated_outputs", "voting_records.json")
    if os.path.isfile(voting_json):
        modification_timestamp = os.path.getmtime(voting_json)
        readable_time = time.ctime(modification_timestamp)

        if get_yes_no_input(f"voting_records.json already exists, was created on {readable_time}. Do you want to pull the votes since then?"):
            print("Pulling new voting_records.json")
            src.gen_voting_record_json.gen_voting_record_json() 
        else:
            print("Not regenerating, running with pre-existing voting_records.json.")    
    else:
        print("voting_records.json does not exist. Generating...")
        src.gen_voting_record_json.gen_voting_record_json()    


    #Now perform data analytics on pulled raw data.
    voting_senate_json = os.path.join(root, "src", "generated_outputs", "voting_records_senate.json")
    vote_avg_json = os.path.join(root, "src", "generated_outputs", "vote_avg.json")
    congressmen_mod_json = os.path.join(root, "src", "generated_outputs", "congressmen_mod.json")
    src.modify_votes.modify_votes(voting_json, voting_senate_json)
    src.modify_reps.modify_reps(congressmen_json, vote_avg_json)


    #Now generate cards
    if get_yes_no_input(f"Proceed with card creation on congressmen size above?"):
        print("Generating cards")
        src.gen_cards.gen_cards(congressmen_mod_json, test_card=False, dummy_img=False)
    else:
        if get_yes_no_input(f"Single card debug?"):
            src.gen_cards.gen_cards(congressmen_mod_json, test_card=True, dummy_img=False)
        else:
            print("Batch debug, disabling photo pull")
            src.gen_cards.gen_cards(congressmen_mod_json, test_card=False, dummy_img=True)

        
