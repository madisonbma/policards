from PIL import Image, ImageDraw, ImageFont, ImageOps
import os
import requests
import json
from io import BytesIO
from datetime import date, datetime
import re
from requests.exceptions import RequestException, HTTPError
from init_logger import my_logger

# --- Configuration ---
TEMPLATE_PATH = 'template.png'
OUTPUT_DIR = 'cards'
ARIMO_FONT_PATH = 'fonts/Arimo/Arimo-VariableFont_wght.ttf' # Path to a .ttf font file (e.g., download from Google Fonts or use one installed on your OS)
TITLE_FONT_PATH = 'fonts/Alfa_Slab_One/AlfaSlabOne-Regular.ttf' # Path to a .ttf font file (e.g., download from Google Fonts or use one installed on your OS)
ARIMO_ITALIC_FONT_PATH = 'fonts/Arimo/Arimo-Italic-VariableFont_wght.ttf'
ZAIN_FONT_PATH = 'fonts/Zain/Zain-Regular.ttf'
ZAIN_BOLD_PATH = 'fonts/Zain/Zain-Bold.ttf'

BORDER = (45,45)
INTERNAL_SPACING = 15
BOX_BOUND = 25
# All coordinates are (x, y) from the top-left corner of the image.
CARD_DIMS = (1080, 1920)
PIC_MAX = (580, 670)
PIC_WIDTH = 500
POSITIONS = {
    'pic_pos': (BORDER[0], 250),      # Top-left corner to paste player's face - 45
    'name_pos': (0, BORDER[1]),           # Position for player's name
    'header_pos' : (0, 170),
    'rightofface_text': (625, 250),
    'belowface_text': (BORDER[0], 920)
}
OFFBLUE = (206,218,235)
RED = (140, 23, 42)
BLUE = (18, 52, 153)
GRAY = (213, 220, 232)
#PINK = (161, 136, 166)
PINK = (216, 74, 98)
LILAC = (120, 139, 255)
TAN = (214, 203, 193)
BLACK = (0,0,0)

LINE_SPACING = 1.0
BAR_DIMS = (200, 30)

# Font sizes (adjust as needed)
FONT_SIZES = {
    'name': 100,
    'text':35,
    'headers': 40,
    'subtitle': 50
}

####GOOD COMBOS:
"""
Arimo: LINE_SPACING=1.2, FONT_SIZES['text'] = 30, FONT_SIZES['headers'] = 40
Zain: LINE_SPACING=1.0, FONT_SIZES['text'] = 35, FONT_SIZES['headers'] = 40, FONT_SIZES['subtitle'] = 50
"""

###Load in the fonts    
try:
    font_text = ImageFont.truetype(ZAIN_FONT_PATH, FONT_SIZES['text'])
except IOError:
    print(f"Warning: Could not load font from {ZAIN_FONT_PATH}. Using default Pillow font. "
        "Ensure the font file exists and is accessible.")
    font_text = ImageFont.load_default()

try:
    font_header = ImageFont.truetype(ZAIN_BOLD_PATH, FONT_SIZES['headers'])
except IOError:
    print(f"Warning: Could not load font from {ZAIN_BOLD_PATH}. Using default Pillow font. "
        "Ensure the font file exists and is accessible.")
    font_header = ImageFont.load_default()

try:
    font_name = ImageFont.truetype(TITLE_FONT_PATH, FONT_SIZES['name'])
except IOError:
    print(f"Warning: Could not load font from {TITLE_FONT_PATH}. Using default Pillow font. "
        "Ensure the font file exists and is accessible.")
    font_name = ImageFont.load_default()



######################################################################################

def create_solid_background(size, color):
    """
    Creates a solid color background image.

    Args:
        size (tuple): A tuple (width, height) representing the image dimensions.
        start_color (tuple): An RGB tuple (R, G, B) for the color.

    Returns:
        PIL.Image.Image: The generated image.
    """
    image = Image.new("RGB", size, color)
    return image


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

    try:
        if dummy:
            img = Image.new('RGB', PIC_MAX, color = 'lightgray')
            my_logger.debug(f'Dummy Image for {rep['name']}')
        else:
            face_path = rep['photo']
            if face_path is None:
                my_logger.info(f"Trying backup image for {rep['name']}")
                face_path = rep['imageUrl']

            if face_path is None:
                img = Image.new('RGB', PIC_MAX, color = 'lightgray')
                my_logger.debug(f'No image found for {rep['name']}')

            elif "http" in face_path:
                try:
                    face_path_url = requests.get(face_path)
                    img = Image.open(BytesIO(face_path_url.content))
                    my_logger.debug(f'Success image pull for {rep['name']}')
                except HTTPError as http_err:
                    my_logger.error(f"HTTP error occurred: {http_err}")
                except RequestException as req_err:
                    my_logger.error(f"Request exception occurred: {req_err}")
                except Exception as e:
                    my_logger.error(f"An unexpected error occurred: {e}")

            else:
                img = Image.new('RGB', PIC_MAX, color = 'lightgray')
                my_logger.debug(f'Face path invalid for {rep['name']}')


    except ImportError:
        my_logger.error(f"Pillow is installed, but couldn't create dummy images.")
        pass # Continue without dummy images if PIL or font issues persist

    return img



def draw_wrapped_text(draw, text, xy, text_color=GRAY, extra_padding_for_newline=10, fill_color=None):
    """Gets the dimensions of what running a draw_wrapped_text would look like. Use this for the text blocks."""
    x, y = xy
    all_lines = []
    newlines_count = 0
    header_line_count = 0
    bar_count = 0
    max_width = CARD_DIMS[0] - x - BORDER[0] - 2*BOX_BOUND
    #full card width - border between anything and edge 

    # Split the initial text by newlines to handle pre-existing breaks
    # We use a special marker to distinguish explicit newlines from wrapped lines
    sections = text.split('\n')

    #The entire block will be considered, and sections will be each "line". 
    #If it's supposed to be the header, the para will start with "||HEADER||".
    #Otherwise it won't
    #Expect: ||HEADER||House of Representatives\nTenure Info\nSomething else that's too long
    #Output: ["||HEADER||House of", "||HEADER||Representatives", "||MANUAL_NEWLINE||", "Tenure Info",
    #  "||MANUAL_NEWLINE||", "Something else that's", "too long"]
    for para in sections:
        lines = []
        line_words = []
        if "||HEADER||" in para:
            header = 1
            para = para.replace("||HEADER||", "") #replace it and set a marker instead
        else:
            header = 0
        words = para.split(' ')

        for word in words:
            current_line = ' '.join(line_words + [word])

            # Use textbbox to get accurate width
            if header:
                text_bbox = draw.textbbox((0, 0), current_line, font=font_header) 
            else:
                text_bbox = draw.textbbox((0, 0), current_line, font=font_text) 

            #if STAT_BAR, append it outright 
            if "||STAT_BAR||" in word:
                bar_count += 1
                lines.append(word)
            else:
                line_width = text_bbox[2] - text_bbox[0]

                if line_width > max_width and line_words:
                    if header:
                        line_to_append = "||HEADER||"
                        line_to_append += ' '.join(line_words)
                        header_line_count += 1
                    else:
                        line_to_append = ' '.join(line_words)
                    lines.append(line_to_append)
                    line_words = [word]
                else:
                    line_words.append(word)
        #appends the last line leaving the loop
        if line_words:
            if header:
                line_to_append = "||HEADER||"
                header_line_count += 1
                line_to_append += ' '.join(line_words)
            else:
                line_to_append = ' '.join(line_words)
            lines.append(line_to_append)
        
            
        all_lines.extend(lines)
        # Add a special marker to the list to indicate a manual newline
        all_lines.append("||MANUAL_NEWLINE||")
        newlines_count += 1

    # Remove the extra newline at the very end
    if all_lines and all_lines[-1] == "||MANUAL_NEWLINE||":
        all_lines.pop()
        newlines_count -= 1

    # Get the base line height
    _, _, _, text_height = draw.textbbox((0,0), "A", font=font_text)
    _, _, _, header_height = draw.textbbox((0,0), "A", font=font_header)

    #Get dimensions of the box to create the box
    x_box = x + max_width + 2*BOX_BOUND
    text_count = len(all_lines) - newlines_count - header_line_count - bar_count
    
    #zeroing + wrapped_lines*height per wrapped_lines*1.2 spacing + added space for newlines*num of newlines
    y_box = y + text_count*text_height*LINE_SPACING + newlines_count*extra_padding_for_newline \
      + header_line_count*header_height*LINE_SPACING + 2*BOX_BOUND + bar_count*BAR_DIMS[1]

    #TODO: if y_box is beyond the y_max, do it all over again with the modifications:
    # 1. remove unnecessary lines
    # 2. reduce font size


    if fill_color:
        draw.rounded_rectangle((xy, (x_box, y_box)), 20, fill=fill_color)
    
    y += BOX_BOUND
    for line in all_lines:
        if line == "||MANUAL_NEWLINE||":
            # Add extra space for explicit newlines
            y += extra_padding_for_newline
        elif "||HEADER||" in line:
            #Remove the ||HEADER|| marker and use the header font
            message = line.replace("||HEADER||", "") #remove the marker
            draw.text((x+BOX_BOUND, y), message, font=font_header, fill=text_color)
            y += header_height*LINE_SPACING
        elif "||STAT_BAR||" in line:
            stat_val = int(line.replace("||STAT_BAR||", "")) #convert string to int
            stat_bar(draw, (x+BOX_BOUND,y), BAR_DIMS, stat_val, bg=(129, 66, 97), fg=(211,211,211), fg2=(15,15,15))
            y+= BAR_DIMS[1]*LINE_SPACING


        else:
            draw.text((x+BOX_BOUND, y), line, font=font_text, fill=text_color)
            y += text_height * LINE_SPACING # Standard spacing for wrapped lines

    return (x,y,x_box,y_box)    


def draw_wrapped_text_OLD(draw_context, text, font, xy, text_color=(0, 0, 0), extra_padding_for_newline=10, fill_color=None):
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
        y_box = y + (len(all_lines) - newlines_count)*line_height*LINE_SPACING + newlines_count*extra_padding_for_newline
        draw_context.rounded_rectangle((xy, (x_box, y_box)), 20, fill=fill_color)
    
    for line in all_lines:
        if line == "||MANUAL_NEWLINE||":
            # Add extra space for explicit newlines
            y += extra_padding_for_newline
        else:
            draw_context.text((x+10, y), line, font=font, fill=text_color)
            y += line_height * LINE_SPACING # Standard spacing for wrapped lines

    return (x,y,x_box,y_box)


def check_text_fit(draw, font_type, start_size, text, dims=CARD_DIMS):
    """
    Try the input text, if it doesn't fit, drop the text and return the new bottom dimensions

    Args:
        draw: input draw context
        font_type: input font
        start_size: input font ideal size
        text: input text
        dims (optional): a tuple of the necessary width and height. Defaults to size of card.
    Returns: 
        tuple of bottom right position
    """

    #try to use the default font. If it doesn't fit, drop the size until it does.
    #Font size is the vertical height. 
    #font_name = ImageFont.truetype(font, start_size)
    font_size = start_size
    while True:
        try:
            font = ImageFont.truetype(font_type, font_size)
        except IOError:
            font = ImageFont.load_default()
        # Use textbbox to get accurate width
        text_bbox = draw.textbbox((0, 0), text, font=font)
        line_width = text_bbox[2] - text_bbox[0]
        over_width = line_width - dims[0]


        if over_width > 0:
            #Need to reduce the font size until it fits, drop by 10% every time, rounding down.
            font_size = int(font_size*0.9)


        else:
            #return the font
            return font


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

    name_font = check_text_fit(draw, TITLE_FONT_PATH, FONT_SIZES["name"], name)
    center_text(draw, text=name, font=name_font, offset=POSITIONS['name_pos'], text_color=text_color, center=(True,False))
    subtitle_text = f"{party} from {state}"
    subtitle_font = check_text_fit(draw, ZAIN_FONT_PATH, FONT_SIZES["subtitle"], subtitle_text)
    center_text(draw, text=subtitle_text, font=subtitle_font, offset=POSITIONS['header_pos'], text_color=text_color, center=(True,False))
   

def create_birth_block(draw, message_in, rep_info, start_location):
    message = ""
    try: 
        birthplace = rep_info['birthplace']
        message += f"Born: {birthplace}\n"

    except Exception as e:
        my_logger.warning(f"Birthplace unknown for {rep_info['name']}.")

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

        message += f"Age: {age}\n"

    except Exception as e:
        my_logger.warning(f"Birthdate unknown for {rep_info['name']}")

    if message == "":
        my_logger.warning(f"No birth records for {rep_info['name']}. Skip this section.")
        #return (start_location)
        return message_in
    else:
        #_,_,_,y = draw_wrapped_text(draw, message, start_location, fill_color=(206, 218, 235))
        #return (start_location[0],y)
        return message_in + message



def create_bio_block(draw, message_in, rep_info, box_start):
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
    message = f"||HEADER||{chamber}\n"

    #Lines 2-4
    if (rep_info['endYear'] - 1 > date.today().year):
        range = str(rep_info['startYear']) + " - Present"
        message += f"{range}\n{tenure} most tenured {party}\nUp for re-election in {str(rep_info['endYear']-1)}\n"
    elif (rep_info['endYear'] - 1 < date.today().year):
        range = f"{rep_info['startYear']} - {rep_info['endYear']}"
        message += f"{range}\n{tenure} most tenured {party}\n"
    else:
        range = str(rep_info['startYear']) + " - Present"
        message += f"{range}\n{tenure} most tenured {party}\nUp for re-election this year\n"
        
    #_,_,_,y = draw_wrapped_text(draw, message, box_with_spacing, fill_color=(206, 218, 235))
    #return (box_with_spacing[0],y)
    return message_in + message


def create_bio_block_bar(draw, message_in, rep_info, box_start):
    """Block 2 is the Rep info. Example:
    House of Representatives
    2025-Present
    Tenure Score: PROGRESS BAR
    Up for re-election 2026

    Returns:
        (x,y) tuple: bottom right corner.
    """
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)
    chamber = rep_info['chamber']

    #Line 1
    message = f"||HEADER||{chamber}\n"

    #Lines 2-4
    if (rep_info['endYear'] - 1 > date.today().year):
        range = str(rep_info['startYear']) + " - Present"
        message += f"{range}\nUp for re-election in {str(rep_info['endYear']-1)}\n"
    elif (rep_info['endYear'] - 1 < date.today().year):
        range = f"{rep_info['startYear']} - {rep_info['endYear']}"
        message += f"{range}\n"
    else:
        range = str(rep_info['startYear']) + " - Present"
        message += f"{range}\nUp for re-election this year\n"
  
    #_,_,_,y = draw_wrapped_text(draw, message, box_with_spacing, fill_color=(206, 218, 235))
    #return (box_with_spacing[0],y)
    return message_in + message


def create_vote_block(draw, message_in, rep_info, box_start):
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
        message = f"||HEADER||Voting Record\n"

        #if they are D or R, show how often they vote with party:
        if party=="Republican" or party=="Democrat":
            with_party_percent = rep_info['with_party_percent']
            if with_party_percent >= 95:
                message += f"Votes with {party}s {with_party_percent}% of the time\n"
            else:
                message += f"Votes with {party}s {with_party_percent}% of the time ({rep_info['with_party_rank']} percentile)\n"


        else: #if they're not D or R, show which party they vote with more often:
            if rep_info['with_D'] > rep_info['with_R']:
                with_party_percent = int((rep_info['with_D'] + rep_info['Both'])/rep_info['vote_count']*100)
                message += f"Votes with Democrats {with_party_percent}% of the time\n"
            elif rep_info['with_D'] == rep_info['with_R']:
                message += "Votes with Democrats and Republicans 50% of the time\n"
            else:
                with_party_percent = int((rep_info['with_R'] + rep_info['Both'])/rep_info['vote_count']*100)
                message += f"Votes with Republicans {with_party_percent}% of the time\n"

        #if they abstain 0% of the time, skip:
        if rep_info['Abstained'] == 1:
            message += f"Has abstained once\n"
        elif rep_info['Abstained'] != 0:
            message += f"Has abstained {rep_info['Abstained']} times\n"

        if rep_info['Neither'] == 1:
            message += f"Voted against bipartisan consensus 1 time\n"
        elif rep_info['Neither'] != 0:
            message += f"Voted against bipartisan consensus {rep_info['Neither']} times\n"

        #_,_,_,y = draw_wrapped_text(draw, message, box_with_spacing,fill_color=(206, 218, 235))

    except Exception as e:
        my_logger.warning(f"No voting record for {rep_info['name']}. Skip this section.")
        message = ""
        #_,y = box_start


    #return (box_start[0],y)
    return message_in + message




def create_ed_block(draw, message_in, rep_info, box_start):
    """
    This will list their education if present.
    """
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)

    ed_list = rep_info['education']
    if not ed_list:
        my_logger.warning(f"No education for {rep_info['name']}. Skip this section.")
        message = ""
        #_,y = box_start
    else:
        if len(ed_list) > 1:
            ed_list.pop(0) #get rid of the high school info
            ed_list = "\n".join(rep_info['education'])
        message = f"||HEADER||Education:\n{ed_list}"
        #_,_,_,y = draw_wrapped_text(draw, message, box_with_spacing, fill_color=(206, 218, 235))

    #return (box_start[0],y)
    return message_in + message



def create_military_block(draw, message_in, rep_info, box_start):
    message = ""
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)
    mil_list = "\n".join(rep_info['military'])
    if not mil_list:
        my_logger.warning(f"No military record for {rep_info['name']}. Skip.")
        #_,y = box_start
    else:
        message = f"||HEADER||Military Record:\n{mil_list}\n"
        #_,_,_,y = draw_wrapped_text(draw, message, box_with_spacing, fill_color=(206, 218, 235))

    return message_in + message
    #return (box_start[0],y)

def create_work_history(draw, message_in, rep_info, box_start):
    message = ""
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)

    work_hist = "\n".join(rep_info['work_history'])
    if not work_hist:
        my_logger.warning(f"No work history found for {rep_info['name']}. Skip.")
        _,y = box_start
    else:
        message = f"||HEADER||Previous Jobs:\n{work_hist}\n"
        #_,_,_,y = draw_wrapped_text(draw, message, box_with_spacing, fill_color=(206, 218, 235))

    #return (box_start[0],y)
    return message_in + message


def create_congressional_block(draw, message_in, rep_info, box_start):
    message = ""
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)

    congress_highlights = ""
    for string in rep_info['congress_highlights']:
        congress_highlights += f"{convert_stringnum_to_num(string)}\n"
    
    congress_highlights = congress_highlights[:-1] #remove the last \n
    if not congress_highlights:
        my_logger.warning(f"No congressional stats found for {rep_info['name']}. Skip.")
        _,y = box_start
    else:
        message = f"||HEADER||Congressional Leadership:\n{congress_highlights}\n"
        #_,_,_,y = draw_wrapped_text(draw, message, box_with_spacing, fill_color=(206, 218, 235))

    #return (box_start[0],y)
    return message_in + message

def create_awards_box(draw, message_in, rep_info, box_start):
    message = ""
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)

    awards = "\n".join(rep_info['accolades'])
    if not awards:
        my_logger.warning(f"No awards found for {rep_info['name']}. Skip.")
        _,y = box_start
    else:
        message = f"||HEADER||Awards:\n{awards}\n"
        #_,_,_,y = draw_wrapped_text(draw, message, box_with_spacing, fill_color=(206, 218, 235))

    #return (box_start[0],y)
    return message_in + message

def create_net_worth_box(draw, message_in, rep_info, box_start):
    message = ""
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)

    net_worth = "IN PROGRESS"
    #net_worth = rep_info['net_worth']

    if not net_worth:
        my_logger.warning(f"No net worth found for {rep_info['name']}. Skip.")
        _,y = box_start
    else:
        message = f"||HEADER||Net Worth: {net_worth}\n"
        #_,_,_,y = draw_wrapped_text(draw, message, box_with_spacing, fill_color=(206, 218, 235))

    #return (box_start[0],y)
    return message_in + message

def create_committee_membership_box(draw, message_in, rep_info, box_start):
    message = ""
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)

    committees = ["Placeholder 1", "Placeholder 2", "Placeholder 3"]
    #committees = rep_info['committees']

    committee_list = "\n   ".join(committees)

    if not committee_list:
        my_logger.warning(f"No committees found for {rep_info['name']}. Skip.")
        _,y = box_start
    else:
        message = f"||HEADER||Committee List (WIP):\n   {committee_list}\n"
        #_,_,_,y = draw_wrapped_text(draw, message, box_with_spacing, fill_color=(206, 218, 235))

    #return (box_start[0],y)
    return message_in + message

def create_top_donors_box(draw, message_in, rep_info, box_start):
    message = ""
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)

    top_donors = ["Placeholder 1", "Placeholder 2", "Placeholder 3"]
    #top_donors = rep_info['top_donors']

    donor_list = "\n   ".join(top_donors)

    if not donor_list:
        my_logger.warning(f"No donor info found for {rep_info['name']}. Skip.")
        _,y = box_start
    else:
        message = f"||HEADER||Top Donors (WIP):\n   {donor_list}\n"
        #_,_,_,y = draw_wrapped_text(draw, message, box_with_spacing, fill_color=(206, 218, 235))

    #return (box_start[0],y)
    return message_in + message

def create_top_issues_box(draw, message_in, rep_info, box_start):
    message = ""
    box_with_spacing = (box_start[0], box_start[1] + INTERNAL_SPACING)

    top_issues = ["Placeholder 1", "Placeholder 2", "Placeholder 3"]
    #top_issues = rep_info['top_issues']

    issues_list = "\n   ".join(top_issues)

    if not issues_list:
        my_logger.warning(f"No top issues found for {rep_info['committees']}. Skip.")
        _,y = box_start
    else:
        message = f"||HEADER||Top Issues (WIP):\n   {issues_list}\n"
        #_,_,_,y = draw_wrapped_text(draw, message, box_with_spacing, fill_color=(206, 218, 235))

    #return (box_start[0],y)
    return message_in + message

def create_block_0_bar(draw, rep_info, box_start, fill_color, text_color):
    """Create the bar section only. Bar data should include:
    tenure
    vote with party
    vote against bipartisan"""
    (x,y) = (0,0)

    msg = ""
    msg += f"||HEADER||Tenure:\n||STAT_BAR||{rep_info['tenure_current_party_percentile']}"

    w_party_rank = rep_info['with_party_rank']
    if w_party_rank:
        msg += f"\n||HEADER||Vote with Party:\n||STAT_BAR||{w_party_rank}"
    else:
        my_logger.warning(f"{rep_info['name']} doesn't have voting info. Skipping bar generation.")

    _,_,x,y = draw_wrapped_text(draw, msg, box_start, fill_color=fill_color, text_color=text_color)

    return x,y


def create_block_1_bar(draw, rep_info, box_start, fill_color, text_color):
    (x,y) = (0,0)
    msg = create_birth_block(draw, "", rep_info, box_start )
    msg = create_bio_block_bar(draw, msg, rep_info, box_start)
    msg = create_ed_block(draw, msg, rep_info, (x,y))

    _,_,x,y = draw_wrapped_text(draw, msg, box_start, fill_color=fill_color, text_color=text_color)

    return x,y

def create_block_1(draw, rep_info, box_start, fill_color, text_color):
    msg = create_birth_block(draw, "", rep_info, box_start )
    (x,y) = (0,0)

    msg = create_bio_block(draw, msg, rep_info, (x,y))

    msg = create_vote_block(draw, msg, rep_info, (x,y))

    msg = create_ed_block(draw, msg, rep_info, (x,y))

    _,_,x,y = draw_wrapped_text(draw, msg, box_start, fill_color=fill_color, text_color=text_color)
    return x,y

def create_block_2(draw, rep_info, box_start, fill_color, text_color):
    #box_start = (POSITIONS['pic_pos'][0], POSITIONS['pic_pos'][1]+PIC_MAX[1])
    x,y = (0,0)
    msg = create_military_block(draw, "", rep_info, box_start)

    msg = create_work_history(draw, msg, rep_info, (x,y))

    msg = create_congressional_block(draw, msg, rep_info, (x,y))

    msg = create_awards_box(draw, msg, rep_info, (x,y))

    msg = create_committee_membership_box(draw, msg, rep_info, (x,y))

    msg = create_net_worth_box(draw, msg, rep_info, (x,y))

    msg = create_top_donors_box(draw, msg, rep_info, (x,y))

    msg = create_top_issues_box(draw, msg, rep_info, (x,y))

    _,_,x,y = draw_wrapped_text(draw, msg, box_start, fill_color=fill_color, text_color=text_color)


    return x,y




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
    if all_matches == []: #if it's empty, doesn't match. just return the string.
        final_string = string
    
    else:
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
                            my_logger.warning(f"\"{digit}\" not a registered number, adding whatever number we've found up until now.")
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


def resize_image(img, desired_width):
    # Open the image
    original_width, original_height = img.size
    
    # Calculate the new height to maintain aspect ratio
    aspect_ratio = original_height / original_width
    new_height = int(desired_width * aspect_ratio)
    
    # Resize the image using the calculated dimensions
    resized_img = img.resize((desired_width, new_height))
    
    return resized_img


# --- Function to create a single player card ---
def create_card_1(rep_info, face_img):
    """
    Card 1 is the original formatting. Picture on the left, Some info on the right, bonus info 
    on the bottom
    """

    # Instead of loading a template image, create a color gradient
    party = rep_info['partyName']

    if party == "Democrat": #Make a blue card
        card = create_linear_gradient(size=CARD_DIMS, start_color=BLUE, end_color=(49, 75, 153))
        fill_color = LILAC
        text_color = GRAY
        #card = create_solid_background(size=CARD_DIMS, color=BLUE)
    elif party == "Republican": #Make a red card
        #card = create_linear_gradient(size=CARD_DIMS, start_color=RED, end_color=(176, 93, 93))
        card = create_solid_background(size=CARD_DIMS, color=RED)
        fill_color = PINK
        text_color = GRAY

    else: #Make a gray card
        card = create_linear_gradient(size=CARD_DIMS, start_color=(100,100,100), end_color=(200,200,200))
        fill_color = GRAY
        text_color = BLACK
    #card = Image.open(TEMPLATE_PATH).convert("RGBA") # Convert to RGBA for transparency handling


    # 2. Add face in

    face_img = resize_image(face_img, PIC_WIDTH)
    #face_img.thumbnail(PIC_MAX) # Resize to desired dimensions
    #face_img = face_img.resize(PIC_MAX) # Resize to desired dimensions
    card.paste(face_img, box=POSITIONS['pic_pos'])

    pic_dims = face_img.size
    print(pic_dims)


    # 3. Prepare to draw text
    draw = ImageDraw.Draw(card)


    # 4. Text blocks
    create_title_block(draw, rep_info, text_color)

    box_start = (POSITIONS['pic_pos'][0] + pic_dims[0] + INTERNAL_SPACING, POSITIONS['pic_pos'][1])

    x,y = create_block_1(draw, rep_info, box_start, fill_color, text_color)
    y = max(y+INTERNAL_SPACING, POSITIONS['pic_pos'][1]+pic_dims[1] + INTERNAL_SPACING)
    create_block_2(draw, rep_info, (BORDER[0],y), fill_color, text_color)

    return card

def create_card_2(rep_info, face_img):
    """
    Card 2 changes some boxes. The top right box is now a status bar box, below is non-bar info,
    bottom is the same
    """


    # Instead of loading a template image, create a color gradient
    party = rep_info['partyName']

    if party == "Democrat": #Make a blue card
        card = create_linear_gradient(size=CARD_DIMS, start_color=BLUE, end_color=(49, 75, 153))
        fill_color = LILAC
        text_color = GRAY
        #card = create_solid_background(size=CARD_DIMS, color=BLUE)
    elif party == "Republican": #Make a red card
        #card = create_linear_gradient(size=CARD_DIMS, start_color=RED, end_color=(176, 93, 93))
        card = create_solid_background(size=CARD_DIMS, color=RED)
        fill_color = PINK
        text_color = GRAY

    else: #Make a gray card
        card = create_linear_gradient(size=CARD_DIMS, start_color=(100,100,100), end_color=(200,200,200))
        fill_color = GRAY
        text_color = BLACK

    #card = Image.open(TEMPLATE_PATH).convert("RGBA") # Convert to RGBA for transparency handling


    # 2. Add face in
    face_img = resize_image(face_img, PIC_WIDTH)
    #face_img.thumbnail(PIC_MAX) # Resize to desired dimensions
    #face_img = face_img.resize(PIC_MAX) # Resize to desired dimensions
    card.paste(face_img, box=POSITIONS['pic_pos'])

    pic_dims = face_img.size


    # 3. Prepare to draw text
    draw = ImageDraw.Draw(card)


    # 4. Text blocks
    create_title_block(draw, rep_info, text_color)

    box_start = (POSITIONS['pic_pos'][0] + pic_dims[0] + INTERNAL_SPACING, POSITIONS['pic_pos'][1])

    x,y = create_block_1_bar(draw, rep_info, box_start, fill_color, text_color)
    x,y = create_block_0_bar(draw, rep_info, (box_start[0],y+INTERNAL_SPACING), fill_color, text_color)
    y = max(y+INTERNAL_SPACING, POSITIONS['pic_pos'][1]+pic_dims[1] + INTERNAL_SPACING)
    create_block_2(draw, rep_info, (BORDER[0],y),fill_color, text_color)

    return card


def save_card(card, name, option=None):

    replacements = str.maketrans({",": "", "\"": "", ".":"", " ":"_"})
    if option:
        output_filename = os.path.join(OUTPUT_DIR, \
            f"{name.translate(replacements).lower()}_card_{option}.png")
    else:
        output_filename = os.path.join(OUTPUT_DIR, \
            f"{name.translate(replacements).lower()}_card.png")
    card.save(output_filename)
    my_logger.info(f"Created card: {output_filename}")



def display_card(card):
    card.show()


def stat_bar(draw, xy, wh, percentile, bg=(129, 66, 97), fg=(211,211,211), fg2=(15,15,15)):
    x, y = xy
    w, h = wh
    # Draw the background
    draw.rectangle((x+(h/2), y, x+w+(h/2), y+h), fill=fg2, width=10)
    draw.ellipse((x+w, y, x+h+w, y+h), fill=fg2)
    draw.ellipse((x, y, x+h, y+h), fill=fg2)
    w = int(w*percentile/100)
    # Draw the part of the progress bar that is actually filled
    draw.rectangle((x+(h/2), y, x+w+(h/2), y+h), fill=fg, width=10)
    draw.ellipse((x+w, y, x+h+w, y+h), fill=fg)
    draw.ellipse((x, y, x+h, y+h), fill=fg)




def gen_cards(congressmen_f, test_card=False, dummy_img=False):

    #Load in the JSON
    try: 
        with open(congressmen_f, 'r') as f:
            congressmen_json = json.load(f)
    except Exception as e:
        my_logger.error("There is an issue with the congressmen.json. Quitting.")
        return

    #if not os.path.exists(TEMPLATE_PATH):
    #    print("\nExiting. Please set up your template and data, then run again.")
    #    sys.exit()
    #else:
        # --- Create output directory if it doesn't exist ---

    os.makedirs(OUTPUT_DIR, exist_ok=True) #Make the cards directory
    #print(f"Using template: {TEMPLATE_PATH}")
    if test_card:
        my_logger.info("Running in debug mode. Just printing one card.")
        for rep in congressmen_json:
            #Pelosi P000197
            #Hamadeh H001098
            #Sanders S000033
            if rep.get('bioguideID')=='H001098': 
                face_img = pull_pic_from_web(rep)
                card = create_card_1(rep, face_img)
                display_card(card)
                #save_card(card, rep['name'], option="1")
    else:
        for rep in congressmen_json:
            face_img = pull_pic_from_web(rep, dummy=dummy_img)
            card = create_card_1(rep, face_img)
            save_card(card, rep['name'])
    my_logger.info("Card generation complete!")
