import subprocess
import os
from datetime import date, datetime
import requests
import re
import json
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from requests.exceptions import RequestException, HTTPError
from init_logger import my_logger


# --- Configuration (UPDATE THESE PATHS) ---
current_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(current_dir, ".."))

NN_EXTRA_BOLD = os.path.join(project_root, "fonts", "NeulisNeue", "NeulisNeue-ExtraBold.ttf")
NN_MEDIUM = os.path.join(project_root, "fonts", "NeulisNeue", "NeulisNeue-Medium.ttf")
NN_BOLD_ITALIC = os.path.join(project_root, "fonts", "NeulisNeue", "NeulisNeue-BoldItalic.ttf")

#"C:\\Users\\Owner\\policards\\fonts\\NeulisNeue\\NeulisNeue-ExtraBold.ttf"
#NN_MEDIUM = "C:\\Users\\Owner\\policards\\fonts\\NeulisNeue\\NeulisNeue-Medium.ttf"
#NN_BOLD_ITALIC = "C:\\Users\\Owner\\policards\\fonts\\NeulisNeue\\NeulisNeue-BoldItalic.ttf"

FONT_CHECK_DICT = {
    "name": (100, NN_EXTRA_BOLD, 15.72),
    "state": (253, NN_BOLD_ITALIC, 10.24),
    "born_age": (100, NN_MEDIUM, 6.62),
    "education": (100, NN_MEDIUM, 6.62),
    "work": (100, NN_MEDIUM, 6.62)
}
    #name is Extra Bold, size 15.72
    #Title is Extra Bold, size 7.72
    #Born_age is medium/bold, size 6.62
    #Education is medium, size 6.62
    #State is bold italic, size 10.24



# --- End Configuration ---


def resize_image(img, desired_width):
    # Open the image
    original_width, original_height = img.size
    
    # Calculate the new height to maintain aspect ratio
    aspect_ratio = original_height / original_width
    new_height = int(desired_width * aspect_ratio)

    if new_height > original_height:
        my_logger.warning(f"Having to expand picture, could be poor quality. Original photo: {img.size}")
    
    # Resize the image using the calculated dimensions
    resized_img = img.resize((desired_width, new_height))
    
    return resized_img




def pull_pic_from_web(rep, dummy=False):
    """
    Pull the photo from the web link. 
    If no link was given, fill with an empty photo.
    
    Args:
        rep (dict): Dictionary with rep info 
        dummy (bool): When True, will bypass pulling real images to save time. For debug mode.
    Returns:
        (img): Image of rep's face
    """
    PIC_WIDTH = 342
    PIC_HEIGHT = 428
    img = None
    try:
        if dummy:
            img = Image.new('RGB', (PIC_WIDTH, PIC_HEIGHT), color = 'lightgray')
            my_logger.debug(f'Dummy Image for {rep['name']}')
        else:
            face_path = rep.get('photo', None)

            # Get the face in rep['photo'] if it exists, check the size of image
            if face_path is None:
                #failed to get rep['photo'], try backup image
                my_logger.info(f"Trying backup image for {rep['name']}")
                face_path = rep['imageUrl']
            elif "http" in face_path:
                #if image is big enough be done, otherwise try backup image
                try:
                    face_path_url = requests.get(face_path)
                    img_1 = Image.open(BytesIO(face_path_url.content))
                    dims_1 = img_1.size
                    if dims_1[0] < PIC_WIDTH or dims_1[1] < PIC_HEIGHT:
                        my_logger.warning(f"Image for {rep['name']} is too small at {dims_1} instead of {(PIC_WIDTH, PIC_HEIGHT)}. Trying backup image.")
                        face_path = rep['imageUrl']
                    else:
                        img = img_1
                        my_logger.info(f"Using primary image for {rep['name']}")
                    #my_logger.debug(f'Success image pull for {rep['name']}')
                except HTTPError as http_err:
                    my_logger.error(f"HTTP error occurred: {http_err}")
                except RequestException as req_err:
                    my_logger.error(f"Request exception occurred: {req_err}")
                except Exception as e:
                    my_logger.error(f"An unexpected error occurred: {e}")


            if face_path is None:
                img = Image.new('RGB', (PIC_WIDTH,PIC_HEIGHT), color = 'lightgray')
                my_logger.debug(f'No image found for {rep['name']}. Generating dummy image.')
            elif face_path == rep['photo']:
                my_logger.debug(f'Primary image for {rep['name']} was sufficient.')
            elif "http" in face_path:
                try:
                    face_path_url = requests.get(face_path)
                    img_2 = Image.open(BytesIO(face_path_url.content))
                    dims_2 = img_2.size
                    if dims_2[0] < PIC_WIDTH or dims_2[1] < PIC_HEIGHT:
                        my_logger.warning(f"Image for {rep['name']} is too small at {dims_2} instead of {(PIC_WIDTH, PIC_HEIGHT)}.")
                    else:
                        img = img_2
                        my_logger.info(f"Using secondary image for {rep['name']}")
                    my_logger.debug(f'Success image pull for {rep['name']}')
                except HTTPError as http_err:
                    my_logger.error(f"HTTP error occurred: {http_err}")
                except RequestException as req_err:
                    my_logger.error(f"Request exception occurred: {req_err}")
                except Exception as e:
                    my_logger.error(f"An unexpected error occurred: {e}")
            else:
                img = Image.new('RGB', (PIC_WIDTH,PIC_WIDTH), color = 'lightgray')
                my_logger.debug(f'Face path invalid for {rep['name']}. Generating dummy image.')


            if img is None:
                #This means both images were too small. Pick the best one
                img = img_1 if dims_1[0]*dims_1[1] > dims_2[0]*dims_2[1] else img_2
                my_logger.info(f'Both images too small for {rep['name']}. Using larger one at {img.size}.')

        #Resize the image
        img = resize_image(img, PIC_WIDTH)

        #Save the image to generated_outputs/temp.png
        root = os.path.dirname(os.path.abspath(__file__))
        pic_file = os.path.join(root, "generated_outputs", "temp.png")
        img.save(pic_file)
        

    except ImportError:
        my_logger.error(f"Pillow is installed, but couldn't create dummy images.")
        pass # Continue without dummy images if PIL issues persist
    except Exception as e:
        my_logger.error(f"Unexpected error pulling image for {rep['name']}: {e}")

    #return img

def draw_wrapped_text(draw_context, text, font, max_width):


    lines = []
    line_words = []
    words = text.split(' ')
    return_me = ""


    for word in words:
        if word != '':
            current_line = ' '.join(line_words + [word])
            # Use textbbox to get accurate width
            text_bbox = draw_context.textbbox((0, 0), current_line, font=font)
            line_width = text_bbox[2] - text_bbox[0]
            if line_width > max_width and line_words: #out of bounds. append without new word
                lines.append(' '.join(line_words)) 
                line_words = [word] 
            else: #otherwise, keep growing current_line
                line_words.append(word) 

    #now append the last one
    lines.append(' '.join(line_words))
    #done parsing. 
    if lines: #if the whole line wasn't empty,
        if len(lines) > 1: #merge them with \\n 
            return_me = ('||BREAK||'.join(lines))
        else: #just return it
            return_me = lines[0]


    
    return return_me


def num_to_percentile(num):
    if num%10 == 1:
        if num%100==11:
            return f"{num}th percentile"
        else:
            return f"{num}st percentile"
    elif num%10 == 2:
        if num%100==12:
            return f"{num}th percentile"
        else:
            return f"{num}nd percentile"
    elif num%10 == 3:
        if num%100==13:
            return f"{num}th percentile"
        else:
            return f"{num}rd percentile"
    else:
        return f"{num}th percentile"



def gen_summary_stats(rep_info):
    """
    Docstring for gen_summary_stats
     * - Tenure: <rank/total>
     * - Absent: <N> times (<rank/total>)
     * - Population: TBD
     * - District Size: TBD
    :param rep_info: dictionary on representative info
    """

    return_me = ""
    chamber = rep_info.get("chamber")
    ### TENURE
    if chamber == "House of Representatives":
        return_me += f"Tenure: {rep_info.get("bg_duration")} years ({rep_info.get("bg_tenure_rank_current")}/535)||BREAK_DOT||"
    else:
        return_me += f"Tenure: {rep_info.get("bg_duration")} years ({rep_info.get("bg_tenure_rank_current")}/100)||BREAK_DOT||"

    ### ABSENT
    novote_count = rep_info.get('Absent', 0) + rep_info.get("Abstained", 0)
    novote_percent = novote_count / (rep_info.get('vote_count') - rep_info.get('Both', 0) - rep_info.get('Neither', 0)) * 100
    novote_percent = int(novote_percent)
    return_me += f"Not Voting: {novote_count} votes ({novote_percent}% of votes)||BREAK_DOT||"

    ### POPULATION
    return_me += f"Population: TBD||BREAK_DOT||"

    ### DISTRICT_SIZE 
    return_me += f"District Size: TBD"
    

    return_me += "\n"
    return return_me

def gen_committee_list(rep_info):
    return_me = ""
    committees = rep_info.get("committees")
    if len(committees)==0:
        return "\n"
    else:
        parent_com = []
        sub_com = []
        for comm in committees:
            comm = comm.replace("Committee on ", "")
            if ":" not in comm:
                parent_com.append(comm)
            else:
                sub_com.append(comm)


        #current template sets committee max length to 6
        if len(committees) <= 7:
            return_me = ""
            #reorganize to include subcomms
            for pcom in parent_com:
                return_me += f"||BREAK_DOT||{pcom}"
                for subcom in sub_com:
                    if pcom in subcom:
                        return_me += f"||BREAK||-- {subcom.split(": ")[1]}"
        
        else:
            #otherwise get rid of subcoms
            return_me += "||BREAK_DOT||".join(parent_com)


        return_me += "\n"
        return return_me


def get_work_history(rep_info, draw, font, max_width):
    return_me = ""
    new_ed = []
    work_history = rep_info.get('work_history')
    if len(work_history)==0:
        return "\n"
    else:
        for work in work_history:
            new_ed.append(draw_wrapped_text(draw, work, font, max_width))
        new_ed[0] = f"||BREAK_DOT||{new_ed[0]}"
        return_me = "||BREAK_DOT||".join(new_ed)
        return_me += "\n"
        return return_me



def create_vote_block(rep_info, absolute_stats):
    """
    This is the voting info block. Example:
        Votes with Republicans 95% of the time
        Abstains 0% of the time 

    Returns:
        (x,y) tuple: bottom right corner.
    """
    party = rep_info['partyName']
    chamber = rep_info.get('chamber')

    try:
        message = ""
        with_d = rep_info.get('with_D_percent')
        with_r = rep_info.get('with_R_percent')
        novote_count = rep_info.get('Absent', 0) + rep_info.get("Abstained", 0)
        novote_percent = novote_count / (rep_info.get('vote_count') - rep_info.get('Both', 0) - rep_info.get('Neither', 0)) * 100
        novote_percent = int(novote_percent)
        message += f"{novote_percent}\n"
        if with_d > with_r:
            message += f"Votes {with_d}% Democrat, {with_r}% Republican,||BREAK||Not Voting {novote_percent}%\n"
        else:
            message += f"Votes {with_r}% Republican, {with_d}% Democrat,||BREAK||Not Voting {novote_percent}%\n"


        #if they are D or R, show how often they vote with party:
        if party=="Republican":
            if chamber == "House of Representatives":
                message += f"The average House Republican votes {absolute_stats.get('with_R_avg_vote_H_R'):.{3}g}% Republican||BREAK||and is not voting {absolute_stats.get('absent_percent_avg_vote_H_R'):.{3}g}% of the time\n"
            else:
                message += f"The average Senate Republican votes {absolute_stats.get('with_R_avg_vote_S_R'):.{3}g}% Republican||BREAK||and is not voting {absolute_stats.get('absent_percent_avg_vote_S_R'):.{3}g}% of the time\n"
    
        elif party=="Democrat":
            if chamber == "House of Representatives":
                message += f"The average House Democrat votes {absolute_stats.get('with_D_avg_vote_H_D'):.{3}g}% Democrat||BREAK||and is not voting {absolute_stats.get('absent_percent_avg_vote_H_D'):.{3}g}% of the time\n"
            else:
                message += f"The average Senate Democrat votes {absolute_stats.get('with_D_avg_vote_S_D'):.{3}g}% Democrat||BREAK||and is not voting {absolute_stats.get('absent_percent_avg_vote_S_D'):.{3}g}% of the time\n"

        else: #if they're not D or R, show which party they vote with more often:
            if rep_info['with_D'] > rep_info['with_R']:
                #Vote more often with democrats
                if chamber == "House of Representatives":
                    message += f"Votes more often with House Democrats, who on average vote {absolute_stats.get('with_D_avg_vote_H_D'):.{3}g}% Democrat||BREAK||and is not voting {absolute_stats.get('absent_percent_avg_vote_H_D'):.{3}g}% of the time\n"
                else:
                    message += f"Votes more often with Senate Democrats, who on average vote {absolute_stats.get('with_D_avg_vote_S_D'):.{3}g}% Democrat||BREAK||and is not voting {absolute_stats.get('absent_percent_avg_vote_S_D'):.{3}g}% of the time\n"
            elif rep_info['with_D'] == rep_info['with_R']:
                message += "Votes with Democrats and Republicans 50% of the time\n"
            else:
                #Vote more often with republicans
                if chamber == "House of Representatives":
                    message += f"Votes more often with House Republicans, who on average vote {absolute_stats.get('with_R_avg_vote_H_R'):.{3}g}% Democrat||BREAK||and is not voting {absolute_stats.get('absent_percent_avg_vote_H_R'):.{3}g}% of the time\n"
                else:
                    message += f"Votes more often with Senate Republicans, who on average vote {absolute_stats.get('with_R_avg_vote_S_R'):.{3}g}% Democrat||BREAK||and is not voting {absolute_stats.get('absent_percent_avg_vote_S_R'):.{3}g}% of the time\n"

 


    except Exception as e:
        my_logger.warning(f"No voting record for {rep_info['name']}. Skip this section.")
        message = ""

    return message
    




def gen_bonus_section(rep_info, draw, font, max_width):
    return_me = ""
    bonus_list = []
    if rep_info.get('military'):
        bonus_list = rep_info.get('military')
        return_me += "MILITARY SERVICE\n"
    elif rep_info.get('accolades'):
        bonus_list = rep_info.get('accolades')
        return_me += "AWARDS\n"
    elif rep_info.get('illegal'):
        bonus_list = rep_info.get("illegal")
        return_me += "REPRIMANDS\n"
    elif rep_info.get('family'):
        bonus_list = rep_info.get("family")  
        return_me += "NOTABLE FAMILY\n" 
    elif rep_info.get('congress_highlights'):
        bonus_list = rep_info.get("congress_highlights")
        return_me += "CONGRESS HIGHLIGHTS\n"
    else:

        return "\n\n"

    formatted_list = []
    for item in bonus_list:
        formatted_list.append(draw_wrapped_text(draw, item, font, max_width))
    formatted_list[0] = f"||BREAK_DOT||{formatted_list[0]}"
    return_me += "||BREAK_DOT||".join(formatted_list)
    return_me += "\n"
    return return_me



def create_temp(rep_info, absolute_stats):
    """
    Create the temp file needed for javascript. Format is:
    NAME
    House Representative OR Senator OR Governor
    2025-Present | Up for re-election in 20XX
    BORN: City, State    AGE: XX
    EDUCATION: School 1, School 2"""

    #First create a dummy draw to get dimensions of fonts
    card = Image.new("RGB", (1080, 1920), (140, 23, 42))
    draw = ImageDraw.Draw(card)
    text_block = ""


    ##################################################
    #                      STATE                     #
    ##################################################
    font_tuple = FONT_CHECK_DICT.get('state')
    max_width = font_tuple[0]
    try:
        font = ImageFont.truetype(font_tuple[1], font_tuple[2])
    except IOError:
        print(f"Warning: Could not load font from {font_tuple[1]}."
            "Ensure the font file exists and is accessible.")

    state = draw_wrapped_text(draw, rep_info.get('state', "STATE"), font, max_width)
    text_block += f"{state}\n"


    ##################################################
    #                      NAME                      #
    ##################################################
    font_tuple = FONT_CHECK_DICT.get('name')
    max_width = font_tuple[0]
    name = rep_info.get('name', "NAME")
    try:
        font = ImageFont.truetype(font_tuple[1], font_tuple[2])
    except IOError:
        print(f"Warning: Could not load font from {font_tuple[1]}."
            "Ensure the font file exists and is accessible.")

    name_data = draw_wrapped_text(draw, name, font, max_width)
    text_block += f"{name_data}\n"

    ##################################################
    #      EITHER CONGRESS OR GOVERNOR               #
    ##################################################
    chamber = rep_info.get('chamber')
    if chamber == "House of Representatives":
        text_block += "Congress\n"
    elif chamber == "Senate":
        text_block += "Congress\n"
    elif chamber == "Governor":
        text_block += "Governor\n"
    else:
        text_block += "Unknown Position\n"
    
    text_block += f"{chamber}:\n"
    ##################################################
    #    XXXX-Present | Up for re-election in 20XX   #
    ##################################################
    #tenure = f"{rep_info['tenure_rank_current_party']}/{rep_info['party_current_count']}"
    #party = rep_info['partyName']

    if (rep_info['bg_endYear'] - 1 > date.today().year):
        range = str(rep_info['startYear']) + " - Present"
        text_block += f"{range} | Up for re-election in {str(rep_info['bg_endYear']-1)}\n"
    elif (rep_info['bg_endYear'] - 1 < date.today().year):
        range = f"{rep_info['startYear']} - {rep_info['bg_endYear']}"
        text_block += f"Served from {range}\n"
    else:
        range = str(rep_info['startYear']) + " - Present"
        text_block += f"{range} | Up for re-election this year\n"
    

    ##################################################
    #         BORN: City, State    AGE: XX           #
    ##################################################
    font_tuple = FONT_CHECK_DICT.get('born_age') 
    max_width = font_tuple[0]
    try:
        font = ImageFont.truetype(font_tuple[1], font_tuple[2])
    except IOError:
        print(f"Warning: Could not load font from {font_tuple[1]}."
            "Ensure the font file exists and is accessible.")

    birthplace = rep_info.get('birthplace')
    if birthplace == "":
        text_block += f"Unknown\n"
    else:
        birthplace = draw_wrapped_text(draw, birthplace, font, max_width)
        text_block += f"{birthplace}\n"

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

    text_block += f"{age}\n"


    ##################################################
    #        EDUCATION: School 1, School 2           #
    ##################################################
    ed_list = rep_info.get('education', [])
    if ed_list:
        if len(ed_list) > 1:
            if ed_list[0] == "High school graduate":
                ed_list.pop(0) #get rid of the high school info
        education = "||BREAK_DOT||".join(ed_list)
        text_block += f"||BREAK_DOT||{education}\n"
    else:
        text_block += "\n"

    #############SECTION 2 #########################
    #Voting Record: %f percentage
    #Tenure: %f percentage
    #Historically has voted with party %n, Democratic %n, Republican %n
    #voting_pct = rep_info.get('with_R_percent', None)
    voting_pct = rep_info.get('for_bar', None)

    if voting_pct is not None:
        text_block += f"{voting_pct}\n"

    text_block += create_vote_block(rep_info, absolute_stats)

    key = f"max_tenure_{chamber[0].upper()}"
    max_tenure = absolute_stats.get(key)

    duration = rep_info.get('bg_duration', None)
    tenure_marker = int((duration/max_tenure)*100)
    tenure_pct = rep_info.get("bg_tenure_rank_current_percentile", None)
    if tenure_pct is not None:
        if duration is None:
            text_block += f"{tenure_marker}\n{num_to_percentile(tenure_pct)}\n"
        elif duration < 1:
            duration = duration*12
            if duration < 1: #if less than 1 month
                text_block += f"{tenure_marker}\n{num_to_percentile(tenure_pct)} (<1 month)\n"

            else:

                text_block += f"{tenure_marker}\n{num_to_percentile(tenure_pct)} ({duration:.{2}g} months)\n"

        else:
            text_block += f"{tenure_marker}\n{num_to_percentile(tenure_pct)} ({duration} years)\n"


    text_block += f"{max_tenure}\n"

    text_block += gen_summary_stats(rep_info)
    text_block += gen_committee_list(rep_info)


    ##################################################
    #               WORK HISTORY                     # 
    ##################################################
    font_tuple = FONT_CHECK_DICT.get('work')
    max_width = font_tuple[0]
    try:
        font = ImageFont.truetype(font_tuple[1], font_tuple[2])
    except IOError:
        print(f"Warning: Could not load font from {font_tuple[1]}."
            "Ensure the font file exists and is accessible.")
    text_block += get_work_history(rep_info, draw, font, max_width)


    text_block += gen_bonus_section(rep_info, draw, font, max_width)



    #################################################
    ####### Add in paths for save, template
    ################################################

    root = os.path.dirname(os.path.abspath(__file__))
    temp_file = os.path.join(root, "generated_outputs", "temp.txt")


    replacements = str.maketrans({",": "", "\"": "", ".":"", " ":"_"})

    output_filename = os.path.join(root, "..", "cards_ps", \
        f"{name.translate(replacements).lower()}_card.psd")
    text_block += output_filename
    text_block += "\n"

    party = rep_info.get('partyName')
    if party=="Republican":
        text_block += os.path.join(root, os.path.pardir, os.path.pardir, "politician_pages_assets", "templates", "Republican-House_Senate_Gov-Social.psd")
    elif party=="Democrat":
        text_block += os.path.join(root, os.path.pardir, os.path.pardir, "politician_pages_assets", "templates", "Democrat-House_Senate_Gov-Social.psd")
    else:
        text_block += os.path.join(root, os.path.pardir, os.path.pardir, "politician_pages_assets", "templates", "Independent-House_Senate_Gov-Social.psd")



    #################################################
    ####### Write to temp file
    ################################################
    with open(temp_file, 'w') as f:
        f.write(text_block)
        print(f"Successfully wrote {name} data to {temp_file}")






def merge_in_supplement(rep_info, supplement):
    """
    Supplemental data to merge into rep_info by name.
    """
    for supplement_data in supplement:
        if rep_info.get('name') == supplement_data.get('name'):
            for key in supplement_data:
                rep_info[key] = supplement_data[key]
                print(f"Using supplement data for {key}: {supplement_data[key]}")

    return rep_info




def gen_temp_for_javascript_old(test_card=True):

    current_dir = os.path.dirname(__file__)
    congressmen_f = os.path.join(current_dir, "generated_outputs", "congressmen_mod.json")
    abs_stat_f = os.path.join(current_dir, "generated_outputs", "absolute_stats.json")
    #Load in the JSON
    try: 
        with open(congressmen_f, 'r') as f:
            congressmen_json = json.load(f)
    except Exception as e:
        my_logger.error("There is an issue with the congressmen.json. Quitting.")
        return

    #Load in the JSON
    try: 
        with open(abs_stat_f, 'r') as abs_f:
            absolute_stats = json.load(abs_f)[0]
    except Exception as e:
        my_logger.error("There is an issue with the absolute_stats.json. Quitting.")
        return



    if test_card:
        #max committee length
        comm_dict = {}
        my_logger.info("Running in debug mode. Just printing one card.")
        for rep in congressmen_json:
            comm = rep.get('committees', "a")
            if comm is not None:
                comm_len = len(comm)
                comm_dict[comm_len] = comm_dict.get(comm_len, 0) + 1

            else:
                comm_dict[0] = comm_dict.get(0, 0) + 1
            #Pelosi P000197
            #Hamadeh H001098
            #Sanders S000033
            if rep.get('bioguideID')=='O000172': 
                create_temp(rep, absolute_stats)
                pull_pic_from_web(rep, dummy=False)
        #print(comm_dict)
    else:
        for rep in congressmen_json:
            create_temp(rep, absolute_stats)



def gen_temp_for_javascript(rep_info):

    current_dir = os.path.dirname(__file__)
    abs_stat_f = os.path.join(current_dir, "generated_outputs", "absolute_stats.json")
    supplement_f = os.path.join(current_dir, "generated_outputs", "supplement_congressmen.json")

    #Load in the absolute_stats JSON
    try: 
        with open(abs_stat_f, 'r') as abs_f:
            absolute_stats = json.load(abs_f)[0]
    except Exception as e:
        my_logger.error("There is an issue with the absolute_stats.json. Quitting.")
        return
    
    #Load in the supplement JSON
    try: 
        with open(supplement_f, 'r') as supp_f:
            supplement_data = json.load(supp_f)
    except Exception as e:
        my_logger.error("There is an issue with the supplement_congressmen.json. Quitting.")
        return


    rep_info = merge_in_supplement(rep_info, supplement_data)
    create_temp(rep_info, absolute_stats)
    pull_pic_from_web(rep_info, dummy=False)

