import sys
import os
import json

current_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)



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
                    print("Person found.")
                    return rep_info
                else:
                    did_you_mean.append(rep_name)
    
        #if we didn't get a match, will hit this print statement
        if len(did_you_mean)!=0:
            print("Representative not found. Did you mean any of these names?")
            print("\n".join(did_you_mean))
        else:
            print("Representative not found.")

def get_field_input(rep_info):
    """
    Docstring for get_field_input
    Prompts the user for a field input and checks for field validity.
    
    :param rep_info: dictionary for the representative
    """


    while True:
        print(f"Valid fields: url, imageUrl, endYear, committees, photo, birthDate, education, military, illegal, failed_runs, work_history, congress_highlights, accolades, family, birthplace")
        user_input = input(f"What field would you like to edit?\n")

        if user_input == "quit" :
            sys.exit()
        
        else:
            try:
                val_to_change = rep_info.get(user_input)
                return user_input, val_to_change
            except KeyError:
                print("Key not found. Try again.")



def update_field(rep_info, supplement, key):
    input_is_list = False
    if key == "birthDate":
        user_input = input(f"What would you like the new value to be? Ideal format is YYYY-MM-DD\n")
    elif key == "committees":
        input_is_list = True
        user_input = input(f"What committee would you like to add?\n")
    elif key == "education":
        input_is_list = True
        user_input = input(f"What education would you like to add?\n")
    elif key == "military":
        input_is_list = True
        user_input = input(f"What committee would you like to add?\n")
    elif key == "illegal":
        input_is_list = True
        user_input = input(f"What illicit activity would you like to add?\n")
    elif key == "failed_runs":
        input_is_list = True
        user_input = input(f"What failed run would you like to add?\n")
    elif key == "work_history":
        input_is_list = True
        user_input = input(f"What work history would you like to add?\n")
    elif key == "congress_highlights":
        input_is_list = True
        user_input = input(f"What congressional highlight would you like to add?\n")
    elif key == "accolades":
        input_is_list = True
        user_input = input(f"What accolade would you like to add?\n")
    elif key == "family":
        input_is_list = True
        user_input = input(f"What family member would you like to add?\n")
    elif key == "birthplace":
        user_input = input(f"What congressional highlight would you like to add?\n")

    else:
        user_input = input(f"What would you like the new value to be?\n")

    if user_input == "quit":
        sys.exit()

    name = rep_info.get("name")
    for dictionary in supplement:
        if dictionary.get("name") == name:
            if input_is_list:
                dictionary.setdefault(key, []).append(user_input)
                return supplement
            else:
                dictionary[key] = user_input
                return supplement
        
    #if it gets past the for loop, it means we didn't have any data for them. add.
    if input_is_list:
        new_dict = {
            'name': name,
            key: [user_input]
        }
    else:
        new_dict = {
            'name': name,
            key: user_input
        }

    supplement.append(new_dict)
    return supplement



#def gen_supplement():
if __name__ == "__main__":
    """
    Docstring for gen_supplement
    If data is not present from the pulls, allow users to add to this block to add any missing data.

    """

    #Load in the congressmen_mod.json and the supplement_congressmen.json
    congressmen_mod_json = os.path.join(project_root, "src", "generated_outputs", "congressmen_mod.json")
    supplement_json = os.path.join(project_root, "src", "generated_outputs", "supplement_congressmen.json")
    try: 
        with open(congressmen_mod_json, 'r') as f:
            full_rep_info = json.load(f)
    except Exception as e:
        print("There is an issue loading in the congressmen_mod.json. Quitting.")
        sys.exit()

    try:
        if os.path.getsize(supplement_json) == 0:
            supplement = []
        else:
            with open(supplement_json, 'r') as s_f:
                supplement = json.load(s_f)

    except FileNotFoundError:
        supplement = []
    except Exception as e:
        print("There is an issue loading in the supplement.json. Quitting.")
        sys.exit()

    #Ask user for person and field to update
    rep = get_name_input(full_rep_info)
    change_key, val_current = get_field_input(rep)

    #Show user what the field is currently. Ask if they want to update

    if (get_yes_no_input(f"The current value for {change_key} is {val_current}. Are you sure you want to update?")):
        #Ask them what to update with
        supplement = update_field(rep, supplement, change_key)

        #Load that into a new json file, which will be opened with congressmen_mod.json for final card
        try:
            with open(supplement_json, 'w') as f:
                json.dump(supplement, f, indent=4)
        except Exception as e:
            print("Had a problem writing the final suppplement.json")
    else:
        print("Quitting...")
        sys.exit()


