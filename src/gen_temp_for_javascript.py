import subprocess
import os
from datetime import date, datetime
import re
import json
from init_logger import my_logger


# --- Configuration (UPDATE THESE PATHS) ---
PHOTOSHOP_EXE_PATH = "C:\\Program Files\\Adobe\\Adobe Photoshop 2026\\Photoshop.exe" 
PSD_FILE_TO_OPEN = "C:\\Users\\Owner\\policards\\templates\\Republican-House_Senate_Gov-Social.psd"
JSX_SCRIPT_PATH = "C:\\Users\\Owner\\policards\\scripts\\move_layer.jsx"
# --- End Configuration ---



def create_temp(rep_info):
    """
    Create the temp file needed for javascript. Format is:
    NAME
    House Representative OR Senator OR Governor
    2025-Present | Up for re-election in 20XX
    BORN: City, State    AGE: XX
    EDUCATION: School 1, School 2"""
    text_block = ""
    name = rep_info.get('name')
    ########1 NAME
    text_block += rep_info.get('name', "NAME")
    text_block += "\n"
    ########2 House Representative OR Senator OR Governor
    chamber = rep_info.get('chamber')
    if chamber == "House of Representatives":
        text_block += "House Representative\n"
    elif chamber == "Senate":
        text_block += "Senator\n"
    elif chamber == "Governor":
        text_block += "Governor\n"
    else:
        text_block += "Unknown Position\n"
    
    ########3 2025-Present | Up for re-election in 20XX
    chamber = rep_info['chamber']
    tenure = f"{rep_info['tenure_rank_current_party']}/{rep_info['party_current_count']}"
    party = rep_info['partyName']

    if (rep_info['endYear'] - 1 > date.today().year):
        range = str(rep_info['startYear']) + " - Present"
        text_block += f"{range} | Up for re-election in {str(rep_info['endYear']-1)}\n"
    elif (rep_info['endYear'] - 1 < date.today().year):
        range = f"{rep_info['startYear']} - {rep_info['endYear']}"
        message += f"{range}"
    else:
        range = str(rep_info['startYear']) + " - Present"
        message += f"{range} | Up for re-election this year\n"
    
    ########4 BORN: City, State    AGE: XX
     
    birthplace = rep_info.get('birthplace', "Unknown")
    text_block += f"Born: {birthplace}"

    birthday = rep_info.get('birthDate', 0)
    today = date.today()

    if re.match(r"\d\d\d\d-\d\d-\d\d", birthday):
        date_format = "%Y-%m-%d"
        bday = datetime.strptime(birthday, date_format)
        age = today.year - bday.year - ((today.month, today.day) < (bday.month, bday.day))
    elif re.match(r"\d\d\d\d-\d\d", birthday):
        date_format = "%Y-%m"
        bday = datetime.strptime(birthday, date_format)
        age = today.year - bday.year - ((today.month) < (bday.month))
    else:
        age = 0

    text_block += f"    Age: {age}\n"

    ########5 EDUCATION: School 1, School 2
    ed_list = rep_info.get('education', [])
    if ed_list:
        if len(ed_list) > 1:
            ed_list.pop(0) #get rid of the high school info
        education = ", ".join(ed_list)
        text_block += f"Education: {education}\n"


    ####### Write to temp file
    root = os.path.dirname(os.path.abspath(__file__))
    temp_file = os.path.join(root, "generated_outputs", "temp.txt")
    with open(temp_file, 'w') as f:
        f.write(text_block)
        print(f"Successfully wrote {name} data to {temp_file}")



def gen_temp_for_javascript(congressmen_f, test_card=True):

    #Load in the JSON
    try: 
        with open(congressmen_f, 'r') as f:
            congressmen_json = json.load(f)
    except Exception as e:
        my_logger.error("There is an issue with the congressmen.json. Quitting.")
        return


    if test_card:
        my_logger.info("Running in debug mode. Just printing one card.")
        for rep in congressmen_json:
            #Pelosi P000197
            #Hamadeh H001098
            #Sanders S000033
            if rep.get('bioguideID')=='P000197': 
                create_temp(rep)
                #face_img = pull_pic_from_web(rep)
                #card = create_card_2(rep, face_img)
                #display_card(card)
                #save_card(card, rep['name'], option="1")
    else:
        for rep in congressmen_json:
            create_temp(rep)
            #face_img = pull_pic_from_web(rep, dummy=dummy_img)
            #card = create_card_2(rep, face_img)
            #save_card(card, rep['name'])
    my_logger.info("Card generation complete!")




def run_photoshop_script():
    # Construct the command to open the PSD and then execute the JSX script
    command = [
        PHOTOSHOP_EXE_PATH,
        PSD_FILE_TO_OPEN,
        "-r",  # Flag often used to indicate running a script
        JSX_SCRIPT_PATH
    ]

    try:
        # Run the command and wait for Photoshop to finish the script
        # Note: This will launch and close Photoshop, which takes time.
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print("Script execution successful!")
        print("Output:", result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"Error executing Photoshop script: {e}")
        print("Stdout:", e.stdout)
        print("Stderr:", e.stderr)
    except FileNotFoundError:
        print("ERROR: Could not find Photoshop executable. Check the path.")

if __name__ == "__main__":
    gen_temp_for_javascript("C:\\Users\\Owner\\policards\\src\\generated_outputs\\congressmen_mod.json", test_card=True)
    run_photoshop_script()