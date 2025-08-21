from PIL import Image, ImageDraw, ImageFont, ImageOps
import os
import requests
import json
from io import BytesIO
from datetime import date

# --- Configuration ---
TEMPLATE_PATH = 'template.png'
OUTPUT_DIR = 'cards'
FONT_PATH = 'fonts/Arimo-VariableFont_wght.ttf' # Path to a .ttf font file (e.g., download from Google Fonts or use one installed on your OS)

# All coordinates are (x, y) from the top-left corner of the image.
CARD_DIMS = (1080, 1920)
PIC_MAX = (580, 670)
POSITIONS = {
    'pic_pos': (75, 250),      # Top-left corner to paste player's face
    'name_pos': (0, 80),           # Position for player's name
    'header_pos' : (0, 170),
    'partyName_pos': (700, 300),    
    'state_pos': (700, 400),        
    'chamber_pos': (700, 500),    
    'endYear_pos': (700, 600),    

}

# Font sizes (adjust as needed)
FONT_SIZES = {
    'name': 70,
    'stats':30,
    'labels': 40
}

try:
    font_name = ImageFont.truetype(FONT_PATH, FONT_SIZES['name'])
    font_stats = ImageFont.truetype(FONT_PATH, FONT_SIZES['stats'])
    font_labels = ImageFont.truetype(FONT_PATH, FONT_SIZES['labels'])
except IOError:
    print(f"Warning: Could not load font from {FONT_PATH}. Using default Pillow font. "
        "Ensure the font file exists and is accessible.")
    font_name = ImageFont.load_default()
    font_stats = ImageFont.load_default()
    font_labels = ImageFont.load_default()

######################################################################################

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

def pull_pic_from_web(rep, error_log):
    """
    Pull the photo from the web link. 
    If no link was given, fill with an empty photo.
    
    Args:
        rep (dict): Dictionary with rep info 
    Returns:
        (img): Image of rep's face
    """

    try:
        face_path = rep['imageUrl']
        if face_path is None:
            print (f"No image found. Creating dummy face image.")
            img = Image.new('RGB', PIC_MAX, color = 'lightgray')
            str_err = rep['name'] + "Face Image Not Found"
            error_log.append(str_err)

        elif "http" in face_path:
            #Pull from web source
            print(f"Found face image at URL {face_path}. Saving.")
            face_path_url = requests.get(face_path)
            img = Image.open(BytesIO(face_path_url.content))
        else:
            print (f"Not sure what format this photo is in: {face_path}. Creating dummy face image.")
            img = Image.new('RGB', PIC_MAX, color = 'lightgray')
            str_err = rep['name'] + "Face Image Format"
            error_log.append(str_err)


    except ImportError:
        print(f"Pillow is installed, but couldn't create dummy images. Please ensure {FONT_PATH} or a similar font is available, or manually create face images.")
        pass # Continue without dummy images if PIL or font issues persist
    #except Exception as e:
    #    print("Likely couldn't find 'imageUrl', fix the dict")

    return img


def draw_wrapped_text(draw_context, text, font, xy, max_width, fill_color=(0, 0, 0), extra_padding_for_newline=10):
    """
    Draws text with automatic wrapping and handles existing newline characters,
    adding a little extra space for explicit newlines.

    Args:
        draw_context (ImageDraw.ImageDraw): The ImageDraw context to use for drawing.
        text (str): The string to draw, potentially containing "\n" characters.
        font (ImageFont.FreeTypeFont): The font to use.
        xy (tuple): A tuple of (x, y) coordinates for the top-left corner of the text box.
        max_width (int): The maximum width of the text box in pixels.
        fill_color (tuple): The color of the text (e.g., (0, 0, 0) for black).
        extra_padding_for_newline (int): Additional vertical space to add for each "\n".
    """
    x, y = xy
    all_lines = []
    
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

    # Remove the extra newline at the very end
    if all_lines and all_lines[-1] == "||MANUAL_NEWLINE||":
        all_lines.pop()

    # Get the base line height
    _, _, _, line_height = draw_context.textbbox((0,0), "A", font=font)
    
    for line in all_lines:
        if line == "||MANUAL_NEWLINE||":
            # Add extra space for explicit newlines
            y += extra_padding_for_newline
        else:
            draw_context.text((x, y), line, font=font, fill=fill_color)
            y += line_height * 1.2 # Standard spacing for wrapped lines



# --- Function to create a single player card ---
def create_card(rep_info, face_img):
    
    # 1. Open the template image
    card = Image.open(TEMPLATE_PATH).convert("RGBA") # Convert to RGBA for transparency handling

    # 2. Open and process the player's face image
    #face_img = ImageOps.fit(face_img, PIC_MAX, method=0, bleed=0.0, centering=(0.5, 0.5))
    face_img = face_img.resize(PIC_MAX) # Resize to desired dimensions

    print("Successfully resized face image")

    # Paste the face image onto the card
    card.paste(face_img, box=POSITIONS['pic_pos'])

    # 3. Prepare to draw text
    draw = ImageDraw.Draw(card)
    text_color = (0, 0, 0, 255) # Black color with full opacity

    chamber = rep_info['chamber']
    tenure = f"{rep_info['tenure_current_party']}/{rep_info['party_current_count']}"
    party = rep_info['partyName']
    state = rep_info['state']
    ###If using bonus data, load it here

    # 4. Draw player name, centered
    center_text(draw, text=rep_info['name'], font=font_name, offset=POSITIONS['name_pos'], text_color=text_color, center=(True,False))
    
    center_text(draw, text=f"{party} from {state}", font=font_labels, offset=POSITIONS['header_pos'], text_color=text_color, center=(True,False))
    # 5. Draw stats and labels

    """FORMAT:
        House of
        Representatives
        2019-Present
        1/226 most tenured Democrat
        Up for re-election in 2027

    """

    if (rep_info['endYear'] - 1 > date.today().year):
        range = str(rep_info['startYear']) + " - Present"
        message1 = f"{chamber}\n{range}\n{tenure} most tenured {party}\nUp for re-election in {str(rep_info['endYear']-1)}"

    elif (rep_info['endYear'] - 1 < date.today().year):
        range = f"{rep_info['startYear']} - {rep_info['endYear']}"
        message1 = f"{chamber}\n{range}\n{tenure} most tenured {party}\n"

    else:
        range = str(rep_info['startYear']) + " - Present"
        message1 = f"{chamber}\n{range}\n{tenure} most tenured {party}\nUp for re-election this year"
        
    draw_wrapped_text(draw, message1, font_labels, (690, 250), 300)


    # 6. Save the final card
    replacements = str.maketrans({",": "", "\"": "", ".":"", " ":"_"})
    output_filename = os.path.join(OUTPUT_DIR, \
         f"{rep_info['name'].translate(replacements).lower()}_card.png")
    card.save(output_filename)
    print(f"Created card: {output_filename}")


def gen_cards(congressmen_f, test_card=False):
    error_log = []
    #Load in the JSON
    try: 
        with open(congressmen_f, 'r') as f:
            congressmen_json = json.load(f)
    except Exception as e:
        print("There is an issue with the congressmen.json. Quitting.")
        return


    if not os.path.exists(TEMPLATE_PATH):
        print("\nExiting. Please set up your template and data, then run again.")
    else:
        # --- Create output directory if it doesn't exist ---
        os.makedirs(OUTPUT_DIR, exist_ok=True) #Make the cards directory
        print(f"Using template: {TEMPLATE_PATH}")
        if test_card:
            print("Running in debug mode. Just printing one card.")
            rep = congressmen_json[0]
            face_img = pull_pic_from_web(rep, error_log)
            create_card(rep, face_img)
        else:
            for rep in congressmen_json:
                face_img = pull_pic_from_web(rep, error_log)
                create_card(rep, face_img)
        print("\nPlayer card generation complete!")
        print(f"Issue detected in the following congressmen, take a look: {error_log}")