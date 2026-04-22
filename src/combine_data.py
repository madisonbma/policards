import os
import sys
import modify_reps
import modify_votes
import argparse
import atexit

sys.stdout.reconfigure(line_buffering=True)

def cleanup_data(generated_outputs):
    #clean up all temp files generated in this process:
    congressmen_mod_json_tmp_path = os.path.join(generated_outputs, 'congressmen_mod.json.tmp')

    if os.path.exists(congressmen_mod_json_tmp_path):
        os.remove(congressmen_mod_json_tmp_path)
        print("CLEANUP: Removed congressmen_mod.json.tmp")



def combine_data(generated_outputs):
    """Checks the modify suite. Assumes you have the JSONs in place, will modify the voting record"""
    
    voting_records = os.path.join(generated_outputs, "voting_records.json")
    voting_records_senate = os.path.join(generated_outputs, "voting_records_senate.json")
    if not os.path.exists(voting_records):
        print(f"Error: File not found at '{voting_records}'")
        raise FileNotFoundError()
    elif not os.path.exists(voting_records_senate):
        print(f"Error: File not found at '{voting_records_senate}'")
        raise FileNotFoundError()
    else:
        modify_votes.modify_votes(voting_records, voting_records_senate)
        print("Combined senate and house votes successfully")
    
    congressmen = os.path.join(generated_outputs, "congressmen.json")
    vote_avg = os.path.join(generated_outputs, "vote_avg.json")
    if not os.path.exists(congressmen):
        print(f"Error: File not found at '{congressmen}'")
        raise FileNotFoundError()
    elif not os.path.exists(vote_avg):
        print(f"Error: File not found at '{vote_avg}'")
        raise FileNotFoundError()
    else:
        modify_reps.modify_reps(congressmen, vote_avg, generated_outputs)   
        print("Combined congressmen and voting records successfully")

if __name__ == "__main__":
    """Checks the modify suite. Assumes you have the JSONs in place, 
    will modify the voting record"""
    
    print("Running combine_data.py")

    # Get user inputs for API path and path to the repo
    parser = argparse.ArgumentParser(description="Merge all data")
    parser.add_argument('generated_outputs_path', help="path to generated_outputs dir")
    args = parser.parse_args()
    generated_outputs = args.generated_outputs_path

    atexit.register(cleanup_data, generated_outputs)

    combine_data(generated_outputs)