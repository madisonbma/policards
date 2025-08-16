import gen_reps_json
import gen_voting_record_json
import gen_xls
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
    if os.path.isfile('congressmen.json'):
        modification_timestamp = os.path.getmtime('congressmen.json')
        readable_time = time.ctime(modification_timestamp)

        if get_yes_no_input(f"congressmen.json already exists, was created on {readable_time}. Do you want to force regeneration?"):
            print("Regenerating congressmen.json")
            gen_reps_json.gen_reps_json()
        else:
            print("Not regenerating, running with pre-existing congressmen.json.")    
    else:
        print("congressmen.json does not exist. Generating...")
        gen_reps_json.gen_reps_json()

    #Generate the voting record json if it doesn't exist or if forcing override.
    if os.path.isfile('voting_records.json'):
        modification_timestamp = os.path.getmtime('voting_records.json')
        readable_time = time.ctime(modification_timestamp)

        if get_yes_no_input(f"voting_records.json already exists, was created on {readable_time}. Do you want to force regeneration?"):
            print("Regenerating voting_records.json")
            gen_voting_record_json.gen_voting_record_json() 
        else:
            print("Not regenerating, running with pre-existing voting_records.json.")    
    else:
        print("voting_records.json does not exist. Generating...")
        gen_voting_record_json.gen_voting_record_json()    

    #Now that records have all been pulled, merge them and export into csv. 
    gen_xls.gen_xls("congressmen.json", "voting_records.json")
    print("Merging these JSONs, see result in raw_data.csv")
