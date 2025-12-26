import sys
import os
import time
import subprocess
import json
from tkinter import filedialog
import tkinter as tk


current_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)

from src.init_logger import my_logger

import src.run_jsx
import src.gen_temp_for_javascript
import src.gen_reps_json
import src.gen_voting_record_json
import src.modify_reps
import src.modify_votes
#import src.gen_xls
#import src.gen_cards

#PHOTOSHOP_EXE_PATH = "C:\\Program Files\\Adobe\\Adobe Photoshop 2026\\Photoshop.exe" 
CONFIG_NAME = "config.json"


def get_resource_path(relative_path):
    """ Handles paths for both dev and PyInstaller EXE """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)




def get_sub_directory(config, folder_key):
    # 1. Get the base location of your EXE/Script
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. Build the path: Base -> Root Folder -> Specific Subfolder
    root_folder = config["settings"]["output_root"]
    sub_folder = config["directories"][folder_key]
    
    full_path = os.path.abspath(os.path.join(base_dir, root_folder, sub_folder))

    # 3. Create it if it doesn't exist
    if not os.path.exists(full_path):
        os.makedirs(full_path, exist_ok=True)
    
    return full_path





def get_photoshop_path():
        #user_input = input(f"""Please pass in your photoshop executable.\n
        #                   On PC, it should look something like C:\\Program Files\\Adobe\\Adobe Photoshop 2026\\Photoshop.exe\n
        #                   on Mac it should be like /Applications/Adobe Photoshop [Version]/Adobe Photoshop [Version].app""")


        
        root = tk.Tk()
        root.withdraw() # Hide the main tiny window
        input_path = filedialog.askopenfilename(title="Select your Photoshop executable")
        return input_path


#####################

def get_base_path():
    """Finds the config file next to the EXE or the Script."""
    if getattr(sys, 'frozen', False):
        # Running as EXE
        base_path = os.path.dirname(sys.executable)
    else:
        # Running as Script
        base_path = os.path.dirname(os.path.abspath(__file__))
    return base_path

def get_config_path():
    base_path = get_base_path()
    return os.path.join(base_path, CONFIG_NAME)


def load_or_init_config():
    config_path = get_config_path()
    
    # 1. Load existing or create empty dict
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            try:
                config = json.load(f)
            except:
                config = {}
    else:
        config = {}

    # 2. Ensure 'settings' structure exists
    if "settings" not in config:
        config["settings"] = {}

    # 3. Check if photoshop_path is present and valid
    ps_path = config["settings"].get("photoshop_path")

    if not ps_path or not os.path.exists(ps_path):
        print("Photoshop path not found. Please select Photoshop.exe...")
        print(f"""On PC, it should look something like C:\\Program Files\\Adobe\\Adobe Photoshop 2026\\Photoshop.exe\n
                    on Mac it should be like /Applications/Adobe Photoshop [Version]/Adobe Photoshop [Version].app""")
        
        # Open File Dialog
        root = tk.Tk()
        root.withdraw() # Hide the main tkinter window
        root.attributes("-topmost", True) # Bring dialog to front
        
        selected_path = filedialog.askopenfilename(
            title="Select Photoshop.exe",
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")]
        )
        root.destroy()

        if selected_path:
            config["settings"]["photoshop_path"] = selected_path
            # 4. Save the updated config back to the file
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            print(f"Path saved to {CONFIG_NAME}")
        else:
            print("No file selected. Application cannot continue.")
            sys.exit(1)

    return config


######################


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

def get_name_input(full_rep_info):
    """
    Docstring for get_name_input
    Prompts the user for a name input and returns a valid name from rep_info.
    Handles case-sensitivity
    
    :param prompt: Description
    """


    while True:
        user_input = input(f"Please provide the name of the representative you\'re trying to generate: ").lower().strip()

        if user_input == "quit" :
            sys.exit()
        
        did_you_mean = []

        for rep_info in full_rep_info:
            rep_name = rep_info.get('name').lower()
            if rep_name.split(' ')[-1] == user_input.split(' ')[-1]: #check if last name matches
                #if full name matches, return that one
                if rep_name == user_input:
                    return rep_info
                else:
                    did_you_mean.append(rep_name)

        #if we didn't get a match, will hit this print statement
        if len(did_you_mean)!=0:
            print("Representative not found. Did you mean any of these names?")
            print("\n".join(did_you_mean))
        else:
            print("Representative not found.")




def run_photoshop_script(ps_exe, script):
    # Construct the command to open the PSD and then execute the JSX script
    command = [
        ps_exe,
        "-r",  # Flag often used to indicate running a script
        script
    ]


    try:
        # Run the command and wait for Photoshop to finish the script
        # Note: This will launch and close Photoshop, which takes time.
        result = subprocess.Popen(command)
        print("Launching Photoshop, should take a few seconds...")
        
    except subprocess.CalledProcessError as e:
        print(f"Error executing Photoshop script: {e}")
        print("Stdout:", e.stdout)
        print("Stderr:", e.stderr)
    except FileNotFoundError:
        print("ERROR: Could not find Photoshop executable. Check the path.")





if __name__ == "__main__":

    ####### 1. Get configuration settings
    # --- EXECUTION LOGIC ---
    config = load_or_init_config()
    ps_exe = config["settings"]["photoshop_path"]
    #print(f"Using Photoshop at: {ps_exe}")


    congressmen_json = os.path.join(project_root, "src", "generated_outputs", "congressmen.json")
    congressmen_mod_json = os.path.join(project_root, "src", "generated_outputs", "congressmen_mod.json")

    #Check if just going straight to cards or want to renegerate any subset of the data
    if os.path.isfile(congressmen_mod_json):
        modification_timestamp = os.path.getmtime(congressmen_json)
        readable_time = time.ctime(modification_timestamp)

        if get_yes_no_input(f"Data updated {readable_time}. Do you want to regenerate?"):
            print("Regenerating congressmen.json")
            regenerate = 1
        else:
            print("Skipping straight to photoshop.") 
            regenerate = 0

    if regenerate:
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
        voting_json = os.path.join(project_root, "src", "generated_outputs", "voting_records.json")
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
        voting_senate_json = os.path.join(project_root, "src", "generated_outputs", "voting_records_senate.json")
        vote_avg_json = os.path.join(project_root, "src", "generated_outputs", "vote_avg.json")
        src.modify_votes.modify_votes(voting_json, voting_senate_json)
        src.modify_reps.modify_reps(congressmen_json, vote_avg_json)


    #Now generate cards
    #if get_yes_no_input(f"Generate for all the congressmen? NOTE not fully functional"):
    #    print("Generating cards.")
    #    print("Running Photoshop script...")
    #    run_photoshop_script(ps_exe, os.path.join(project_root, "src", "fill_social_template.jsx"))

    
    #else:
    #Load in the congressmen data
    try: 
        with open(congressmen_mod_json, 'r') as f:
            full_rep_info = json.load(f)
    except Exception as e:
        my_logger.error("There is an issue loading in the congressmen_mod.json. Quitting.")

    rep_info = get_name_input(full_rep_info) #ask user for name to generate
    src.gen_temp_for_javascript.gen_temp_for_javascript(rep_info) #generate the temp file with info to pull from json
    run_photoshop_script(ps_exe, os.path.join(project_root, "src", "fill_social_template.jsx"))
