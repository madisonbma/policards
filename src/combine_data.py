import os
import sys
import modify_reps
import modify_votes

sys.stdout.reconfigure(line_buffering=True)


def check_full_modify_json():
    """Checks the modify suite. Assumes you have the JSONs in place, will modify the voting record"""
    root_dir = os.path.dirname(__file__)
    
    voting_records = os.path.join(root_dir, "generated_outputs", "voting_records.json")
    voting_records_senate = os.path.join(root_dir, "generated_outputs", "voting_records_senate.json")
    if not os.path.exists(voting_records):
        print(f"Error: File not found at '{voting_records}'")
        return None
    elif not os.path.exists(voting_records_senate):
        print(f"Error: File not found at '{voting_records_senate}'")
        return None
    else:
        modify_votes.modify_votes(voting_records, voting_records_senate)
    
    congressmen = os.path.join(root_dir, "generated_outputs", "congressmen.json")
    vote_avg = os.path.join(root_dir, "generated_outputs", "vote_avg.json")
    if not os.path.exists(congressmen):
        print(f"Error: File not found at '{congressmen}'")
        return None
    elif not os.path.exists(vote_avg):
        print(f"Error: File not found at '{vote_avg}'")
        return None
    else:
        modify_reps.modify_reps(congressmen, vote_avg)   

if __name__ == "__main__":
    """Checks the modify suite. Assumes you have the JSONs in place, will modify the voting record"""
    print("Running combine_data.py")
    root_dir = os.path.dirname(__file__)
    
    voting_records = os.path.join(root_dir, "generated_outputs", "voting_records.json")
    voting_records_senate = os.path.join(root_dir, "generated_outputs", "voting_records_senate.json")
    if not os.path.exists(voting_records):
        print(f"Error: File not found at '{voting_records}'")
        sys.exit()
    elif not os.path.exists(voting_records_senate):
        print(f"Error: File not found at '{voting_records_senate}'")
        sys.exit()
    else:
        modify_votes.modify_votes(voting_records, voting_records_senate)
    
    congressmen = os.path.join(root_dir, "generated_outputs", "congressmen.json")
    vote_avg = os.path.join(root_dir, "generated_outputs", "vote_avg.json")
    if not os.path.exists(congressmen):
        print(f"ERROR: File not found at '{congressmen}'")
        sys.exit()
    elif not os.path.exists(vote_avg):
        print(f"ERROR: File not found at '{vote_avg}'")
        sys.exit()
    else:
        modify_reps.modify_reps(congressmen, vote_avg)   