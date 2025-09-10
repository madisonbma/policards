from PIL import Image, ImageDraw, ImageFont, ImageOps
import os
import requests
import json
from io import BytesIO
from datetime import date, datetime
import re
import sys
import logging

# --- Configuration ---
TEMPLATE_PATH = 'template.png'
LOGFILE_PATH = "card_gen.log"
OUTPUT_DIR = 'cards'
ARIMO_FONT_PATH = 'fonts/Arimo/Arimo-VariableFont_wght.ttf' # Path to a .ttf font file (e.g., download from Google Fonts or use one installed on your OS)
TITLE_FONT_PATH = 'fonts/Alfa_Slab_One/AlfaSlabOne-Regular.ttf' # Path to a .ttf font file (e.g., download from Google Fonts or use one installed on your OS)

BORDER = (45,45)
INTERNAL_SPACING = 15
# All coordinates are (x, y) from the top-left corner of the image.
CARD_DIMS = (1080, 1920)
PIC_MAX = (580, 670)
POSITIONS = {
    'pic_pos': (BORDER[0], 250),      # Top-left corner to paste player's face - 45
    'name_pos': (0, BORDER[1]),           # Position for player's name
    'header_pos' : (0, 170),
    'rightofface_text': (625, 250),
    'belowface_text': (BORDER[0], 920)
}

# Font sizes (adjust as needed)
FONT_SIZES = {
    'name': 100,
    'stats':30,
    'labels': 40
}

###Load in the fonts    
try:
    font_stats = ImageFont.truetype(ARIMO_FONT_PATH, FONT_SIZES['stats'])
    font_labels = ImageFont.truetype(ARIMO_FONT_PATH, FONT_SIZES['labels'])
except IOError:
    print(f"Warning: Could not load font from {ARIMO_FONT_PATH}. Using default Pillow font. "
        "Ensure the font file exists and is accessible.")
    font_stats = ImageFont.load_default()
    font_labels = ImageFont.load_default()

try:
    font_name = ImageFont.truetype(TITLE_FONT_PATH, FONT_SIZES['name'])
except IOError:
    print(f"Warning: Could not load font from {TITLE_FONT_PATH}. Using default Pillow font. "
        "Ensure the font file exists and is accessible.")
    font_name = ImageFont.load_default()



######################################################################################

def create_linear_gradient(size, start_color, end_color):
    """
    Creates a linear horizontal color gradient image.

    Args:
        size (tuple): A tuple (width, height) representing the image dimensions.
        start_color (tuple): An RGB tuple (R, G, B) for the starting color.
        end_color (tuple): An RGB tuple (R, G, B) for the ending color.

    Returns:
        PIL.Image.Image: The generated gradient image.
    """
    width, height = size
    image = Image.new("RGB", size)
    pixels = image.load()

    for x in range(width):
        # Calculate the progress of the gradient (0.0 to 1.0)
        progress = x / (width - 1)

        # Interpolate the R, G, and B values
        r = int(start_color[0] * (1 - progress) + end_color[0] * progress)
        g = int(start_color[1] * (1 - progress) + end_color[1] * progress)
        b = int(start_color[2] * (1 - progress) + end_color[2] * progress)

        # Apply the calculated color to all pixels in the current column
        for y in range(height):
            pixels[x, y] = (r, g, b)

    return image



def center_text(draw, text, font, text_color, offset=(0,0), center=(True,True)):

    _, _, w, h = draw.textbbox((0,0), text=text, font=font)
    #image_width, image_height = card.size
    if center[0]:
        x_text = ((CARD_DIMS[0] - offset[0] - w) / 2 ) + offset[0]
    else: 
        x_text = offset[0]
    if center[1]:
        y_text = ((CARD_DIMS[1] - offset[1] - h) / 2 ) + offset[1]

    else:
        y_text = offset[1]
    draw.text((x_text, y_text), text=text, font=font, fill=text_color)



def pull_pic_from_web(rep, error_log, dummy=False):
    """
    Pull the photo from the web link. 
    If no link was given, fill with an empty photo.
    
    Args:
        rep (dict): Dictionary with rep info 
        error_log (list): List of errors to display at end
        dummy (bool): When True, will bypass pulling real images to save time. For debug mode.
    Returns:
        (img): Image of rep's face
    """
    try:
        if dummy:
            img = Image.new('RGB', PIC_MAX, color = 'lightgray')
            str_err = rep['name'] + "Face Image Format"
            error_log.append(str_err)
        else:
            face_path = rep['imageUrl']
            if face_path is None:
                #print (f"No image found. Creating dummy face image.")
                img = Image.new('RGB', PIC_MAX, color = 'lightgray')
                str_err = rep['name'] + "Face Image Not Found"
                error_log.append(str_err)

            elif "http" in face_path:
                #Pull from web source
                #print(f"Found face image at URL {face_path}. Saving.")
                face_path_url = requests.get(face_path)
                img = Image.open(BytesIO(face_path_url.content))
            else:
                #print (f"Not sure what format this photo is in: {face_path}. Creating dummy face image.")
                img = Image.new('RGB', PIC_MAX, color = 'lightgray')
                str_err = rep['name'] + "Face Image Format"
                error_log.append(str_err)


    except ImportError:
        print(f"Pillow is installed, but couldn't create dummy images.")
        pass # Continue without dummy images if PIL or font issues persist
    #except Exception as e:
    #    print("Likely couldn't find 'imageUrl', fix the dict")

    return img


def draw_wrapped_text(draw_context, text, font, xy, text_color=(0, 0, 0), extra_padding_for_newline=10, fill_color=None):
    """
    Draws text with automatic wrapping and handles existing newline characters,
    adding a little extra space for explicit newlines.

    Args:
        draw_context (ImageDraw.ImageDraw): The ImageDraw context to use for drawing.
        text (str): The string to draw, potentially containing "\n" characters.
        font (ImageFont.FreeTypeFont): The font to use.
        xy (tuple): A tuple of (x, y) coordinates for the top-left corner of the text box.
        text_color (tuple): The color of the text (e.g., (0, 0, 0) for black).
        extra_padding_for_newline (int): Additional vertical space to add for each "\n".
        fill_color (tuple): None==clear background. Else will fill a rounded box

    Returns:
        4-element tuple (int): box corners
    """
    x, y = xy
    all_lines = []
    newlines_count = 0
    max_width = CARD_DIMS[0] - BORDER[0] - x
    
    # Split the initial text by newlines to handle pre-existing breaks
    # We use a special marker to distinguish explicit newlines from wrapped lines
    paragraphs = text.replace('\n', '||NEWLINE||').split('||NEWLINE||')

    for para in paragraphs:
        lines = []
        line_words = []
        words = para.split(' ')

        for word in words:
            current_line = ' '.join(line_words + [word])
            # Use textbbox to get accurate width
            text_bbox = draw_context.textbbox((0, 0), current_line, font=font)
            line_width = text_bbox[2] - text_bbox[0]

            if line_width > max_width and line_words:
                lines.append(' '.join(line_words))
                line_words = [word]
            else:
                line_words.append(word)

        if line_words:
            lines.append(' '.join(line_words))
            
        all_lines.extend(lines)
        # Add a special marker to the list to indicate a manual newline
        all_lines.append("||MANUAL_NEWLINE||")
        newlines_count += 1

    # Remove the extra newline at the very end
    if all_lines and all_lines[-1] == "||MANUAL_NEWLINE||":
        all_lines.pop()
        newlines_count -= 1

    # Get the base line height
    _, _, _, line_height = draw_context.textbbox((0,0), "A", font=font)

    #Get dimensions of the box to create the box
    if fill_color:
        x_box = x + max_width+10
        y_box = y + (len(all_lines) - newlines_count)*line_height*1.2 + newlines_count*extra_padding_for_newline
        draw_context.rounded_rectangle((xy, (x_box, y_box)), 20, fill=fill_color)
    
    for line in all_lines:
        if line == "||MANUAL_NEWLINE||":
            # Add extra space for explicit newlines
            y += extra_padding_for_newline
        else:
            draw_context.text((x+10, y), line, font=font, fill=text_color)
            y += line_height * 1.2 # Standard spacing for wrapped lines

    return (x,y,x_box,y_box)



###############################################################################
# Section for text blocks.
###############################################################################

def create_title_block(draw, rep_info, text_color):
    """
    Block 1 is the title info.
    """
    name = rep_info['name']
    party = rep_info['partyName']
    state = rep_info['state']

    center_text(draw, text=name, font=font_name, offset=POSITIONS['name_pos'], text_color=text_color, center=(True,False))
    center_text(draw, text=f"{party} from {state}", font=font_labels, offset=POSITIONS['header_pos'], text_color=text_color, center=(True,False))
   
def create_birth_block(draw, rep_info, start_location):
    message = ""
    try: 
        birthplace = rep_info['birthplace'].replace("born in ", "Birthplace: ")
        message += f"Birthplace: {birthplace}\n"

    except Exception as e:
        print(f"Birthplace unknown for {rep_info['name']}.")

    try:
        birthday = rep_info['birthDate']
        today = date.today()

        if re.match(r"\d\d\d\d-\d\d-\d\d", birthday):
            date_format = "%Y-%m-%d"
            bday = datetime.strptime(birthday, date_format)
            age = today.year - bday.year - ((today.month, today.day) < (bday.month, bday.day))
        elif re.match(r"\d\d\d\d-\d\d", birthday):
            date_format = "%Y-%m"
            bday = datetime.strptime(birthday, date_format)
            age = today.year - bday.year - ((today.month) < (bday.month))

        message += f"Age: {age}"

    except Exception as e:
        print(f"Birthdate unknown for {rep_info['name']}")

    if message == "":
        print(f"No birth records for {rep_info['name']}. Skip this section.")
        return (start_location)
    else:
        _,_,_,y = draw_wrapped_text(draw, message, font_stats, start_location, fill_color=(206, 218, 235))
        return (start_location[0],y)



def create_bio_block(draw, rep_info, box_start):
    """Block 2 is the Rep info. Example:
    House of Representatives
    2025-Present
    240/275 most Tenured
    Up for re-election 2026

    Returns:
        (x,y) tuple: bottom right corner.
    """
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)
    chamber = rep_info['chamber']
    tenure = f"{rep_info['tenure_current_party']}/{rep_info['party_current_count']}"
    party = rep_info['partyName']

    #Line 1
    message = f"{chamber}\n"

    #Lines 2-4
    if (rep_info['endYear'] - 1 > date.today().year):
        range = str(rep_info['startYear']) + " - Present"
        message = f"{chamber}\n{range}\n{tenure} most tenured {party}\nUp for re-election in {str(rep_info['endYear']-1)}"
    elif (rep_info['endYear'] - 1 < date.today().year):
        range = f"{rep_info['startYear']} - {rep_info['endYear']}"
        message = f"{chamber}\n{range}\n{tenure} most tenured {party}\n"
    else:
        range = str(rep_info['startYear']) + " - Present"
        message = f"{chamber}\n{range}\n{tenure} most tenured {party}\nUp for re-election this year"
        
    _,_,_,y = draw_wrapped_text(draw, message, font_stats, box_with_spacing, fill_color=(206, 218, 235))
    return (box_with_spacing[0],y)


def create_vote_block(draw, rep_info, box_start):
    """
    This is the voting info block. Example:
        Voting Record
        Votes with Republicans 95% of the time
        Abstains 0% of the time 

    Returns:
        (x,y) tuple: bottom right corner.
    """
    party = rep_info['partyName']
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)

    try:
        with_party_percent = f"{int(rep_info['with_party']/rep_info['vote_count']*100)}"
        abstains_percent = f"{int(rep_info['abstain']/rep_info['vote_count']*100)}"
        absent_percent = f"{int(rep_info['absent']/rep_info['vote_count']*100)}"

        message = f"Voting Record\nVotes with {party}s {with_party_percent}% of the time\nAbstains {abstains_percent}% of the time"

        _,_,_,y = draw_wrapped_text(draw, message, font_stats, box_with_spacing,fill_color=(206, 218, 235))

    except Exception as e:
        print(f"No voting record for {rep_info['name']}. Skip this section.")
        _,y = box_start
        #str_err = rep_info['name'] + "Voting record not found"
        #error_log.append(str_err)

    return (box_start[0],y)


def create_ed_block(draw, rep_info, box_start):
    """
    This will list their education if present.
    """
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)


    ed_list = "\n".join(rep_info['education'])
    if not ed_list:
        print(f"No education for {rep_info['name']}. Skip this section.")
        _,y = box_start
    else:
        message = f"Education:\n{ed_list}"
        _,_,_,y = draw_wrapped_text(draw, message, font_stats, box_with_spacing, fill_color=(206, 218, 235))

    return (box_start[0],y)



def create_military_block(draw, rep_info, box_start):

    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)
    mil_list = "\n".join(rep_info['military'])
    if not mil_list:
        print(f"No military record for {rep_info['name']}. Skip.")
        _,y = box_start
    else:
        message = f"Military Record:\n{mil_list}"
        _,_,_,y = draw_wrapped_text(draw, message, font_stats, box_with_spacing, fill_color=(206, 218, 235))


    return (box_start[0],y)

def create_work_history(draw, rep_info, box_start):
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)

    work_hist = "\n".join(rep_info['work_history'])
    if not work_hist:
        print(f"No work history found for {rep_info['name']}. Skip.")
        _,y = box_start
    else:
        message = f"Previous Jobs:\n{work_hist}"
        _,_,_,y = draw_wrapped_text(draw, message, font_stats, box_with_spacing, fill_color=(206, 218, 235))

    return (box_start[0],y)


def create_congressional_block(draw, rep_info, box_start):
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)

    congress_highlights = ""
    for string in rep_info['congress_highlights']:
        congress_highlights += f"{convert_stringnum_to_num(string)}\n"
    
    congress_highlights = congress_highlights[:-1] #remove the last \n
    if not congress_highlights:
        print(f"No congressional stats found for {rep_info['name']}. Skip.")
        _,y = box_start
    else:
        message = f"Congressional Leadership:\n{congress_highlights}"
        _,_,_,y = draw_wrapped_text(draw, message, font_stats, box_with_spacing, fill_color=(206, 218, 235))

    return (box_start[0],y)

def create_awards_box(draw, rep_info, box_start):
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)

    awards = "\n".join(rep_info['accolades'])
    if not awards:
        print(f"No awards found for {rep_info['name']}. Skip.")
        _,y = box_start
    else:
        message = f"Awards:\n{awards}"
        _,_,_,y = draw_wrapped_text(draw, message, font_stats, box_with_spacing, fill_color=(206, 218, 235))

    return (box_start[0],y)

def create_net_worth_box(draw, rep_info, box_start):
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)

    net_worth = "IN PROGRESS"
    #net_worth = rep_info['net_worth']

    if not net_worth:
        print(f"No net worth found for {rep_info['name']}. Skip.")
        _,y = box_start
    else:
        message = f"Net Worth: {net_worth}"
        _,_,_,y = draw_wrapped_text(draw, message, font_stats, box_with_spacing, fill_color=(206, 218, 235))

    return (box_start[0],y)

def create_committee_membership_box(draw, rep_info, box_start):
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)

    committees = ["Placeholder 1", "Placeholder 2", "Placeholder 3"]
    #committees = rep_info['committees']

    committee_list = "\n   ".join(committees)

    if not committee_list:
        print(f"No committees found for {rep_info['name']}. Skip.")
        _,y = box_start
    else:
        message = f"Committee List (WIP):\n   {committee_list}"
        _,_,_,y = draw_wrapped_text(draw, message, font_stats, box_with_spacing, fill_color=(206, 218, 235))

    return (box_start[0],y)

def create_top_donors_box(draw, rep_info, box_start):
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)

    top_donors = ["Placeholder 1", "Placeholder 2", "Placeholder 3"]
    #top_donors = rep_info['top_donors']

    donor_list = "\n   ".join(top_donors)

    if not donor_list:
        print(f"No donor info found for {rep_info['name']}. Skip.")
        _,y = box_start
    else:
        message = f"Top Donors (WIP):\n   {donor_list}"
        _,_,_,y = draw_wrapped_text(draw, message, font_stats, box_with_spacing, fill_color=(206, 218, 235))

    return (box_start[0],y)

def create_top_issues_box(draw, rep_info, box_start):
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)

    top_issues = ["Placeholder 1", "Placeholder 2", "Placeholder 3"]
    #top_issues = rep_info['top_issues']

    issues_list = "\n   ".join(top_issues)

    if not issues_list:
        print(f"No top issues found for {rep_info['committees']}. Skip.")
        _,y = box_start
    else:
        message = f"Top Issues (WIP):\n   {issues_list}"
        _,_,_,y = draw_wrapped_text(draw, message, font_stats, box_with_spacing, fill_color=(206, 218, 235))

    return (box_start[0],y)




def convert_stringnum_to_num(string):
    # Task:
    # if [] after the Congress, remove the number of congress
    # if standalone, replace with the date
    # if with other congress "and", combine the years

    nums = {"first":1, "second":2, "third":3, "fourth":4, "fifth":5, "sixth":6, "seventh":7, "eighth":8, "ninth":9, "tenth":10,
            "eleventh":11, "twelfth":12, "thirteenth":13, "fourteenth":14, "fifteenth":15, "sixteenth":16, "seventeenth":17, "eighteenth":18, 
            "nineteenth":19, "twentieth":20, "twenty":20, "thirtieth":30, "thirty":30, "fortieth":40, "forty":40, "fiftieth":50, "fifty":50, 
            "sixtieth":60, "sixty":60, "seventieth":70, "seventy":70, "eightieth":80, "eighty":80, "ninetieth":90, "ninety":90, 
            "hundred":100, "hundredth":100}
    
    all_matches = re.findall(r"([^\(]+\([^\)]+\))", string) #finds anything ^( + ( + ^) + )
    final_string = ""

    for substring in all_matches:
        #pull the stuff in the parenthesis
        match = re.match(r"([^\(]*)\(([^\)]+)\)", substring) #get the groups now
        dont_touch = match.group(1)
        congresses = match.group(2).lower()

        #split by ",", "and" - each one will be a different congress or some funky case we'll catch for below
        con_list = re.split(r",|and", congresses)
        service_list = []
        bracket = ""
        bracket_marker = 0

        for number_wspace in con_list:
            #then split by spaces
            number = number_wspace.lower().split(" ")
            num = 0
            #One Hundred Thirteenth Congress [January 3, 2013-February 12, 2014]
            #go through each number
            for digit in number:
                if digit == "":
                    continue
                elif digit == "through": #add a 0 marker to replace with -
                    service_list.append(num) #append the number we just finished
                    service_list.append(-1) #add a -1 marker to replace with -
                    num = 0 #reset for new number
                elif "[" in digit: #get rid of the previous entry in service_list, keep going until "]"
                    if num == 0:
                        service_list.pop() #remove the previous number, will replace with the dates in the bracket
                    bracket_marker = 1 
                    bracket += f"{digit} "
                elif "]" in digit: #end the bracket section, add the whole thing to the list and reset
                    bracket_marker = 0
                    bracket += digit
                    service_list.append(bracket)
                    num = 0
                    bracket = ""
                elif bracket_marker: #blindly add anything in the bracket
                    bracket += f"{digit} "
                elif digit == "one": #this is for one hundred, just move on
                    continue
                elif "congress" in digit: #for congress or congresses, append the previous number
                    service_list.append(num)
                    num = 0
                else:
                    try:
                        num += nums.get(digit)
                    except Exception as e:
                        print(f"\"{digit}\" not a registered number, adding whatever number we've found up until now.")
                        service_list.append(num)

            if not bracket_marker:
                service_list.append(num)
        service_list = list(filter(lambda x: x != 0, service_list)) #remove the 0s

        output = ""
        i = 0
        while i < len(service_list):
            if isinstance(service_list[i], str): #add it to the output str blindly
                output += f"{service_list[i]}, "
            else:
                start_year = 1789 + (service_list[i]-1)*2
                end_year = start_year + 1

                if i < len(service_list)-1: #check the next one to see if we need to use the -
                    if isinstance(service_list[i+1], str): #if the next one is a string, use normal end year
                        output += f"{start_year}-{end_year}, "
                    elif service_list[i] +1 == service_list[i+1]: #if it's monotonic increase, use the -
                        output += f"{start_year}-{end_year+2}, "
                        i += 1
                    elif service_list[i+1]==-1: #if a -1, it's a "through". There will be a spot 2 ahead with the end date.
                        output += f"{start_year}-{1789+(service_list[i+2]-1)*2+1}, "
                        i += 2
                    else: #use normal end year
                        output += f"{start_year}-{end_year}, "
                else:
                    output += f"{start_year}-{end_year}, "
            i += 1
        final_string += dont_touch + "(" + output[:-2] + ")"

    return final_string




###############################################################################

# --- Function to create a single player card ---
def create_card(rep_info, face_img, error_log):


    # Instead of loading a template image, create a color gradient
    party = rep_info['partyName']

    if party == "Democrat": #Make a blue card
        card = create_linear_gradient(size=CARD_DIMS, start_color=(30,80,150), end_color=(111,114,189))
    elif party == "Republican": #Make a red card
        card = create_linear_gradient(size=CARD_DIMS, start_color=(171, 26, 26), end_color=(176, 93, 93))
    else: #Make a gray card
        card = create_linear_gradient(size=CARD_DIMS, start_color=(100,100,100), end_color=(200,200,200))

    #card = Image.open(TEMPLATE_PATH).convert("RGBA") # Convert to RGBA for transparency handling


    # 2. Add face in
    face_img = face_img.resize(PIC_MAX) # Resize to desired dimensions
    card.paste(face_img, box=POSITIONS['pic_pos'])


    # 3. Prepare to draw text
    draw = ImageDraw.Draw(card)
    text_color = (0, 0, 0, 255) # Black color with full opacity


    # 4. Text blocks
    create_title_block(draw, rep_info, text_color)

    x,y = create_birth_block(draw, rep_info, (POSITIONS['pic_pos'][0] + PIC_MAX[0] + INTERNAL_SPACING, POSITIONS['pic_pos'][1]))

    x,y = create_bio_block(draw, rep_info, (x,y))

    x,y = create_vote_block(draw, rep_info, (x,y))

    x,y = create_ed_block(draw, rep_info, (x,y))

    x,y = create_military_block(draw, rep_info, (POSITIONS['pic_pos'][0], POSITIONS['pic_pos'][1]+PIC_MAX[1]))

    x,y = create_work_history(draw, rep_info, (x,y))

    x,y = create_congressional_block(draw, rep_info, (x,y))

    x,y = create_awards_box(draw, rep_info, (x,y))

    x,y = create_committee_membership_box(draw, rep_info, (x,y))

    x,y = create_net_worth_box(draw, rep_info, (x,y))

    x,y = create_top_donors_box(draw, rep_info, (x,y))

    x,y = create_top_issues_box(draw, rep_info, (x,y))

    return card


def save_card(card, name):

    replacements = str.maketrans({",": "", "\"": "", ".":"", " ":"_"})
    output_filename = os.path.join(OUTPUT_DIR, \
         f"{name.translate(replacements).lower()}_card.png")
    card.save(output_filename)
    print(f"Created card: {output_filename}")



def display_card(card):
    card.show()


def stat_bar(draw, xy, wh, percentile, bg=(129, 66, 97), fg=(211,211,211), fg2=(15,15,15)):
    x, y = xy
    w, h = wh
    # Draw the background
    draw.rectangle((x+(h/2), y, x+w+(h/2), y+h), fill=fg2, width=10)
    draw.ellipse((x+w, y, x+h+w, y+h), fill=fg2)
    draw.ellipse((x, y, x+h, y+h), fill=fg2)
    w = int(w*percentile)
    # Draw the part of the progress bar that is actually filled
    draw.rectangle((x+(h/2), y, x+w+(h/2), y+h), fill=fg, width=10)
    draw.ellipse((x+w, y, x+h+w, y+h), fill=fg)
    draw.ellipse((x, y, x+h, y+h), fill=fg)

def gen_cards(congressmen_f, test_card=False, dummy_img=False):
    error_log = []

    #logging.basicConfig(
    #    filename=LOGFILE_PATH,
    #    level=logging.INFO,
    #    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    #)

    #Load in the JSON
    try: 
        with open(congressmen_f, 'r') as f:
            congressmen_json = json.load(f)
    except Exception as e:
        print("There is an issue with the congressmen.json. Quitting.")
        return


    #if not os.path.exists(TEMPLATE_PATH):
    #    print("\nExiting. Please set up your template and data, then run again.")
    #    sys.exit()
    #else:
        # --- Create output directory if it doesn't exist ---

    os.makedirs(OUTPUT_DIR, exist_ok=True) #Make the cards directory
    #print(f"Using template: {TEMPLATE_PATH}")
    if test_card:
        print("Running in debug mode. Just printing one card.")
        for rep in congressmen_json:
            if rep.get('bioguideID')=='M000934': #Test on Pelosi P000197 
                face_img = pull_pic_from_web(rep, error_log)
                card = create_card(rep, face_img, error_log)
                display_card(card)
    else:
        for rep in congressmen_json:
            face_img = pull_pic_from_web(rep, error_log, dummy=dummy_img)
            card = create_card(rep, face_img, error_log)
            save_card(card, rep['name'])
    print("\nCard generation complete!")

    with open(LOGFILE_PATH, 'w') as log_fh:
        for entry in error_log:
            log_fh.write(f"{entry}\n")
    print(f"Issue detected in the following congressmen, take a look at {LOGFILE_PATH}")