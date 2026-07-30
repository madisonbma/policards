import os
from datetime import date, datetime
import requests
import re
import json
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from requests.exceptions import RequestException, HTTPError
import argparse


def load_global_fonts(font_path):
    global NN_EXTRA_BOLD
    global NN_MEDIUM
    global NN_BOLD_ITALIC
    global FONT_CHECK_DICT

    NN_EXTRA_BOLD = os.path.join(font_path, "NeulisNeue", "NeulisNeue-ExtraBold.ttf")
    NN_MEDIUM = os.path.join(font_path, "NeulisNeue", "NeulisNeue-Medium.ttf")
    NN_BOLD_ITALIC = os.path.join(font_path, "NeulisNeue", "NeulisNeue-BoldItalic.ttf")

    FONT_CHECK_DICT = {
        "name": (100, NN_EXTRA_BOLD, 15.72),
        "state": (253, NN_BOLD_ITALIC, 10.24),
        "born_age": (100, NN_MEDIUM, 6.62),
        "education": (100, NN_MEDIUM, 6.62),
        "work": (100, NN_MEDIUM, 6.62)
    }


def resize_image(img, desired_width):
    # Open the image
    original_width, original_height = img.size
    
    # Calculate the new height to maintain aspect ratio
    aspect_ratio = original_height / original_width
    new_height = int(desired_width * aspect_ratio)

    if new_height > original_height:
        print(f"Having to expand picture, could be poor quality. Original photo: {img.size}")
    
    # Resize the image using the calculated dimensions
    resized_img = img.resize((desired_width, new_height))
    
    return resized_img



def pull_pic_from_web(rep, generated_outputs, dummy=False):
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
        else:
            face_path = rep.get('photo', None)

            # Get the face in rep['photo'] if it exists, check the size of image
            if face_path is None:
                #failed to get rep['photo'], try backup image
                face_path = rep['imageUrl']
                dims_1 = (0,0)
            elif "http" in face_path:
                #if image is big enough be done, otherwise try backup image
                try:
                    face_path_url = requests.get(face_path)
                    img_1 = Image.open(BytesIO(face_path_url.content))
                    dims_1 = img_1.size
                    if dims_1[0] < PIC_WIDTH or dims_1[1] < PIC_HEIGHT:
                        print(f"Image for {rep['name']} is too small at {dims_1} instead of {(PIC_WIDTH, PIC_HEIGHT)}. Trying backup image.")
                        face_path = rep['imageUrl']
                    else:
                        img = img_1
                    #my_logger.debug(f'Success image pull for {rep['name']}')
                except HTTPError as http_err:
                    print(f"HTTP error occurred: {http_err}")
                except RequestException as req_err:
                    print(f"Request exception occurred: {req_err}")
                except Exception as e:
                    print(f"An unexpected error occurred: {e}")


            if face_path is None:
                img = Image.new('RGB', (PIC_WIDTH,PIC_HEIGHT), color = 'lightgray')
                #my_logger.debug(f'No image found for {rep['name']}. Generating dummy image.')
            elif face_path == rep['photo']:
                #my_logger.debug(f'Primary image for {rep['name']} was sufficient.')
                dims_2 = (0,0)
                pass
                
            elif "http" in face_path:
                try:
                    face_path_url = requests.get(face_path)
                    img_2 = Image.open(BytesIO(face_path_url.content))
                    dims_2 = img_2.size
                    if dims_2[0] < PIC_WIDTH or dims_2[1] < PIC_HEIGHT:
                        print(f"Image for {rep['name']} is too small at {dims_2} instead of {(PIC_WIDTH, PIC_HEIGHT)}.")
                    else:
                        img = img_2
                        print(f"Using secondary image for {rep['name']}")
                    #my_logger.debug(f'Success image pull for {rep['name']}')
                except HTTPError as http_err:
                    print(f"HTTP error occurred: {http_err}")
                    img = Image.new('RGB', (PIC_WIDTH, PIC_HEIGHT), color = 'lightgray')
                except RequestException as req_err:
                    print(f"Request exception occurred: {req_err}")
                    img = Image.new('RGB', (PIC_WIDTH, PIC_HEIGHT), color = 'lightgray')
                except Exception as e:
                    print(f"An unexpected error occurred: {e}")
                    img = Image.new('RGB', (PIC_WIDTH, PIC_HEIGHT), color = 'lightgray')
            else:
                img = Image.new('RGB', (PIC_WIDTH,PIC_WIDTH), color = 'lightgray')
                #my_logger.debug(f'Face path invalid for {rep['name']}. Generating dummy image.')


            if img is None:
                #This means both images were too small. Pick the best one
                img = img_1 if dims_1[0]*dims_1[1] > dims_2[0]*dims_2[1] else img_2
                print(f'Both images too small for {rep['name']}. Using larger one at {img.size}.')

        #Resize the image
        img = resize_image(img, PIC_WIDTH)

        #Save the image to generated_outputs/temp.png
        pic_file = os.path.join(generated_outputs, "temp.png")
        img.save(pic_file)
        print(f"Saved photo for {rep['name']}")
        

    except ImportError:
        print(f"Pillow is installed, but couldn't create dummy images.")
        pass # Continue without dummy images if PIL issues persist
    except Exception as e:
        print(f"Unexpected error pulling image for {rep['name']}: {e}")
        raise e


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



def gen_summary_stats(rep_info, rep_stats):
    """
    Docstring for gen_summary_stats
     * - Tenure: <rank/total>
     * - Absent: <N> times (<rank/total>)
     * - Population: TBD
     * - District Size: TBD
    :param rep_info: dictionary on representative info
    """
    summary_stat = ""
    chamber = rep_info.get("chamber")
    ### TENURE
    if chamber == "House of Representatives":
        summary_stat += f"Tenure: {rep_info.get("bg_duration")} years ({rep_info.get("bg_tenure_rank_current")}/535)||BREAK_DOT||"
    else:
        summary_stat += f"Tenure: {rep_info.get("bg_duration")} years ({rep_info.get("bg_tenure_rank_current")}/100)||BREAK_DOT||"

    ### ABSENT
    novote_count = rep_info.get('Absent', 0) + rep_info.get("Abstained", 0)
    novote_percent = novote_count / (rep_info.get('vote_count') - rep_info.get('Both', 0) - rep_info.get('Neither', 0)) * 100
    novote_percent = int(novote_percent)
    summary_stat += f"Not Voting: {novote_count} votes ({novote_percent}% of votes)||BREAK_DOT||"

    ### POPULATION
    summary_stat += f"Population: TBD||BREAK_DOT||"

    ### DISTRICT_SIZE 
    summary_stat += f"District Size: TBD"
    
    rep_stats['summary_stats'] = summary_stat



def gen_committee_list(rep_info, rep_stats):
    return_me = ""
    committees = rep_info.get("committees")
    if len(committees)==0:
        rep_stats['committee_list'] = ""
    else:
        parent_com = []
        sub_com = []
        comm_list = []
        for comm in committees:
            if not comm.startswith("Committee"):
                split = comm.split(":")
                addme = f" [{split[0]}]"
                comm = ":".join(split[1:])
            else:
                addme = ""
            #comm_list.append(comm + addme)
            if ":" not in comm:
                parent_com.append(comm + addme)
            else:
                sub_com.append(comm + addme)


        #return_me += "||BREAK_DOT||".join(comm_list)
        #rep_stats['committee_list'] = return_me

        #current template sets committee max length to 6
        return_me = ""
            #reorganize to include subcomms
        for pcom in parent_com:
            return_me += f"||BREAK_DOT||{pcom}"
            for subcom in sub_com:
                if pcom in subcom:
                    return_me += f"||BREAK_DOT||{subcom}"
        
        #else:
            #otherwise get rid of subcoms
        #    return_me += "||BREAK_DOT||".join(parent_com)


        rep_stats['committee_list'] = return_me


def get_work_history(rep_info, draw, font, max_width, rep_stats):
    new_ed = []
    work_history = rep_info.get('work_history')
    if len(work_history)==0:
        rep_stats['work_history'] = ""
    else:
        for work in work_history:
            new_ed.append(work)
            #new_ed.append(draw_wrapped_text(draw, work, font, max_width))
        new_ed[0] = f"||BREAK_DOT||{new_ed[0]}"
        rep_stats['work_history'] = "||BREAK_DOT||".join(new_ed)



def create_vote_block(rep_info, absolute_stats, rep_stats):
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
        with_d = rep_info.get('with_D_percent')
        with_r = rep_info.get('with_R_percent')
        novote_count = rep_info.get('Absent', 0) + rep_info.get("Abstained", 0)
        novote_percent = novote_count / (rep_info.get('vote_count') - rep_info.get('Both', 0) - rep_info.get('Neither', 0)) * 100
        novote_percent = int(novote_percent)
        rep_stats['absent_percent'] = f"{novote_percent}"
        if with_d > with_r:
            rep_stats['vote_with_party_text'] = f"Votes {with_d}% Democrat, {with_r}% Republican,||BREAK||Not Voting {novote_percent}%"
            #rep_stats['vote_with_party_text'] = f"Votes {with_d}% Democrat, {with_r}% Republican, Not Voting {novote_percent}%"
        else:
            rep_stats['vote_with_party_text'] = f"Votes {with_r}% Republican, {with_d}% Democrat,||BREAK||Not Voting {novote_percent}%"
            #rep_stats['vote_with_party_text'] = f"Votes {with_r}% Republican, {with_d}% Democrat, Not Voting {novote_percent}%"


        #if they are D or R, show how often they vote with party:
        if party=="Republican":
            if chamber == "House of Representatives":
                rep_stats['avg_vote_text'] = f"The average House Republican votes {absolute_stats.get('with_R_avg_vote_H_R'):.{3}g}% Republican||BREAK||and is not voting {absolute_stats.get('absent_percent_avg_vote_H_R'):.{3}g}% of the time"
                #rep_stats['avg_vote_text'] = f"The average House Republican votes {absolute_stats.get('with_R_avg_vote_H_R'):.{3}g}% Republican and is not voting {absolute_stats.get('absent_percent_avg_vote_H_R'):.{3}g}% of the time"
            else:
                #rep_stats['avg_vote_text'] = f"The average Senate Republican votes {absolute_stats.get('with_R_avg_vote_S_R'):.{3}g}% Republican and is not voting {absolute_stats.get('absent_percent_avg_vote_S_R'):.{3}g}% of the time"
                rep_stats['avg_vote_text'] = f"The average Senate Republican votes {absolute_stats.get('with_R_avg_vote_S_R'):.{3}g}% Republican||BREAK||and is not voting {absolute_stats.get('absent_percent_avg_vote_S_R'):.{3}g}% of the time"
    
        elif party=="Democrat":
            if chamber == "House of Representatives":
                rep_stats['avg_vote_text'] = f"The average House Democrat votes {absolute_stats.get('with_D_avg_vote_H_D'):.{3}g}% Democrat||BREAK||and is not voting {absolute_stats.get('absent_percent_avg_vote_H_D'):.{3}g}% of the time"
                #rep_stats['avg_vote_text'] = f"The average House Democrat votes {absolute_stats.get('with_D_avg_vote_H_D'):.{3}g}% Democrat and is not voting {absolute_stats.get('absent_percent_avg_vote_H_D'):.{3}g}% of the time"
            else:
                rep_stats['avg_vote_text'] = f"The average Senate Democrat votes {absolute_stats.get('with_D_avg_vote_S_D'):.{3}g}% Democrat||BREAK||and is not voting {absolute_stats.get('absent_percent_avg_vote_S_D'):.{3}g}% of the time"
                #rep_stats['avg_vote_text'] = f"The average Senate Democrat votes {absolute_stats.get('with_D_avg_vote_S_D'):.{3}g}% Democrat and is not voting {absolute_stats.get('absent_percent_avg_vote_S_D'):.{3}g}% of the time"

        else: #if they're not D or R, show which party they vote with more often:
            if rep_info['with_D'] > rep_info['with_R']:
                #Vote more often with democrats
                if chamber == "House of Representatives":
                    rep_stats['avg_vote_text'] = f"Votes more often with House Democrats, who on average vote {absolute_stats.get('with_D_avg_vote_H_D'):.{3}g}% Democrat||BREAK||and is not voting {absolute_stats.get('absent_percent_avg_vote_H_D'):.{3}g}% of the time"
                    #rep_stats['avg_vote_text'] = f"Votes more often with House Democrats, who on average vote {absolute_stats.get('with_D_avg_vote_H_D'):.{3}g}% Democrat and is not voting {absolute_stats.get('absent_percent_avg_vote_H_D'):.{3}g}% of the time"
                else:
                    rep_stats['avg_vote_text'] = f"Votes more often with Senate Democrats, who on average vote {absolute_stats.get('with_D_avg_vote_S_D'):.{3}g}% Democrat||BREAK||and is not voting {absolute_stats.get('absent_percent_avg_vote_S_D'):.{3}g}% of the time"
                    #rep_stats['avg_vote_text'] = f"Votes more often with Senate Democrats, who on average vote {absolute_stats.get('with_D_avg_vote_S_D'):.{3}g}% Democrat and is not voting {absolute_stats.get('absent_percent_avg_vote_S_D'):.{3}g}% of the time"
            elif rep_info['with_D'] == rep_info['with_R']:
                rep_stats['avg_vote_text'] = "Votes with Democrats and Republicans 50% of the time"
            else:
                #Vote more often with republicans
                if chamber == "House of Representatives":
                    rep_stats['avg_vote_text'] = f"Votes more often with House Republicans, who on average vote {absolute_stats.get('with_R_avg_vote_H_R'):.{3}g}% Democrat||BREAK||and is not voting {absolute_stats.get('absent_percent_avg_vote_H_R'):.{3}g}% of the time"
                    #rep_stats['avg_vote_text'] = f"Votes more often with House Republicans, who on average vote {absolute_stats.get('with_R_avg_vote_H_R'):.{3}g}% Republican and is not voting {absolute_stats.get('absent_percent_avg_vote_H_R'):.{3}g}% of the time"
                else:
                    rep_stats['avg_vote_text'] = f"Votes more often with Senate Republicans, who on average vote {absolute_stats.get('with_R_avg_vote_S_R'):.{3}g}% Democrat||BREAK||and is not voting {absolute_stats.get('absent_percent_avg_vote_S_R'):.{3}g}% of the time"
                    #rep_stats['avg_vote_text'] = f"Votes more often with Senate Republicans, who on average vote {absolute_stats.get('with_R_avg_vote_S_R'):.{3}g}% Republican and is not voting {absolute_stats.get('absent_percent_avg_vote_S_R'):.{3}g}% of the time"

    except Exception as e:
        print(f"No voting record for {rep_info['name']}. Skip this section.")


def gen_top_issues_prototype(rep_info, draw, font, max_width, rep_stats):
    # PROTOTYPE: wrapping now happens in Photoshop (write_bulleted_list_wrapped),
    # so we no longer pre-compute line breaks with draw_wrapped_text here -- just
    # join the raw issues with the bullet delimiter. (draw/font/max_width unused.)
    top_issues_list = rep_info.get('top_issues', [])
    if top_issues_list:
        top_issues = "||BREAK_DOT||".join(top_issues_list)
        rep_stats['top_issues'] = f"||BREAK_DOT||{top_issues}"
    else:
        rep_stats['top_issues'] = "||BREAK_DOT||Issue 1||BREAK_DOT||Issue 2||BREAK_DOT||Issue 3"


def gen_top_issues(rep_info, draw, font, max_width, rep_stats):
    top_issues_list = rep_info.get('top_issues', [])

    if top_issues_list:
        formatted_list = []
        for issue in top_issues_list:
            formatted_list.append(issue)
            #formatted_list.append(draw_wrapped_text(draw, issue, font, max_width))
        rep_stats['top_issues'] = "||BREAK_DOT||".join(formatted_list)
    else:
        rep_stats['top_issues'] = "||BREAK_DOT||Issue 1||BREAK_DOT||Issue 2||BREAK_DOT||Issue 3"


def fmt_money_abbrev(n):
    """Abbreviated dollars: 11700064 -> '$11.7M', 48269 -> '$48K', 250 -> '$250'."""
    try:
        n = float(n or 0)
    except (TypeError, ValueError):
        return "$0"
    a = abs(n)
    if a >= 1_000_000:
        return f"${n / 1_000_000:.1f}M"
    if a >= 1_000:
        return f"${n / 1_000:.0f}K"
    return f"${n:,.0f}"


def fmt_name(pac_key):
    """
    PACs and ORGs come in caps lock. Convert to .capitalize(),
    but keep PAC or one-word caps-locked
    """
    #print(pac_key)
    if pac_key.isupper():
        if ' ' not in pac_key: #if one word
            if pac_key.endswith("PAC"):#if ends in pac, keep it capitalized. else title
                name = pac_key
            else:
                name = pac_key.title()
        elif '(' in pac_key:
            match = re.match(r"([^\(]+)\(([^\)]+)\)", pac_key)
            if match:
                name1 = match.group(1)
                name2 = match.group(2)
                name = name2 if len(name1)>len(name2) else name1
                if ' ' not in name:
                    pass
                else:
                    name = name.title()
                    name = re.sub(r"\bPac\b", "PAC", name)
            else:
                name = pac_key.title()
                name = re.sub(r"\bPac\b", "PAC", name)
        else:
            name = pac_key.title()
            name = re.sub(r"\bPac\b", "PAC", name)
    else:
        name = pac_key


    name = re.sub(r"\bPac\b", "PAC", name)
    name = re.sub(r"\bLlc\b", "LLC", name)

    #print("->", name)
    return name

def gen_top_donors_prototype(rep_info, draw, font, max_width, rep_stats):
    # top_donors is now [overview_dict, {company: amount}] (overview has year_range,
    # net_contributions, pac_total, ...). Title -> donor_title_layer; the rest is the
    # donor_text_layer: plain totals header (||BREAK|| = line break) then the top 3
    # donors as bullets (||BREAK_DOT||).
    top_donors = rep_info.get('top_donors')
    if (isinstance(top_donors, list) and len(top_donors) >= 2
            and isinstance(top_donors[1], dict)):
        overview = top_donors[0] if isinstance(top_donors[0], dict) else {}
        donors = top_donors[1]

        year_range = overview.get('year_range') or str(overview.get('election_year', ''))
        rep_stats['donor_title'] = f"DONORS ({year_range})"

        net = fmt_money_abbrev(overview.get('net_contributions', 0))
        pac = fmt_money_abbrev(overview.get('pac_total', 0))
        header = (f"Total Donations: {net}||BREAK||"
                  f"Total from PACs: {pac}")


        top3 = sorted(donors.items(), key=lambda kv: kv[1], reverse=True)[:3]
        donor_lines = "||BREAK_DOT||"+"||BREAK_DOT||".join(
            f"{fmt_name(key)} ({fmt_money_abbrev(value)})" for key, value in top3
        )

        rep_stats['top_donors_hdr'] = header
        rep_stats['top_donors'] = donor_lines
    else:
        rep_stats['donor_title'] = "DONORS"
        rep_stats['top_donors_hdr'] = "Total Donations: $0||BREAK||Total from PACs: $0"
        rep_stats['top_donors'] = "||BREAK_DOT||Donor 1||BREAK_DOT||Donor 2||BREAK_DOT||Donor 3"



def gen_top_donors(rep_info, draw, font, max_width, rep_stats):
    # top_donors is now [overview_dict, {company: amount}] (overview has year_range,
    # net_contributions, pac_total, ...). Title -> donor_title_layer; the rest is the
    # donor_text_layer: plain totals header (||BREAK|| = line break) then the top 3
    # donors as bullets (||BREAK_DOT||).
    top_donors = rep_info.get('top_donors')
    if (isinstance(top_donors, list) and len(top_donors) >= 2
            and isinstance(top_donors[1], dict)):
        overview = top_donors[0] if isinstance(top_donors[0], dict) else {}
        donors = top_donors[1]

        year_range = overview.get('year_range') or str(overview.get('election_year', ''))
        rep_stats['donor_title'] = f"DONORS ({year_range})"

        net = fmt_money_abbrev(overview.get('net_contributions', 0))
        pac = fmt_money_abbrev(overview.get('pac_total', 0))
        header = (f"Total Donations: {net}||BREAK||"
                  f"Total from PACs: {pac}||BREAK||||BREAK||"
                  f"||BREAK||")


        top3 = sorted(donors.items(), key=lambda kv: kv[1], reverse=True)[:3]
        formatted_list = []
        for company, amount in top3:
            formatted_list.append(f"{company} ({fmt_money_abbrev(amount)})")
            #formatted_list.append(draw_wrapped_text(draw, f"{company} ({fmt_money_abbrev(amount)})", font, max_width))
        donor_lines = "||BREAK_DOT||".join(formatted_list)

        rep_stats['top_donors_hdr'] = header
        rep_stats['top_donors'] = donor_lines
    else:
        rep_stats['donor_title'] = "DONORS"
        rep_stats['top_donors_hdr'] = "Total Donations: $0||BREAK||Total from PACs: $0||BREAK||||BREAK||"
        rep_stats['top_donors'] = "||BREAK_DOT||Donor 1||BREAK_DOT||Donor 2||BREAK_DOT||Donor 3"


def gen_bonus_section(rep_info, draw, font, max_width, rep_stats):
    bonus_list = []
    if rep_info.get('military'):
        bonus_list = rep_info.get('military')
        rep_stats['bonus_header'] = "MILITARY SERVICE"
    elif rep_info.get('accolades'):
        bonus_list = rep_info.get('accolades')
        rep_stats['bonus_header'] = "AWARDS"
    elif rep_info.get('illegal'):
        bonus_list = rep_info.get("illegal")
        rep_stats['bonus_header'] = "REPRIMANDS"
    elif rep_info.get('family'):
        bonus_list = rep_info.get("family")  
        rep_stats['bonus_header'] = "NOTABLE FAMILY" 
    elif rep_info.get('congress_highlights'):
        bonus_list = rep_info.get("congress_highlights")
        rep_stats['bonus_header'] = "CONGRESS HIGHLIGHTS"
    else:
        return
    
    formatted_list = []
    for item in bonus_list:
        formatted_list.append(item)
        #formatted_list.append(draw_wrapped_text(draw, item, font, max_width))
    formatted_list[0] = f"||BREAK_DOT||{formatted_list[0]}"
    rep_stats['bonus_text'] = "||BREAK_DOT||".join(formatted_list)



def create_temp(rep_info, absolute_stats, generated_outputs, assets_dir, save_path):
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
    rep_stats = {}


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
    rep_stats['state'] = f"{state}"


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
    rep_stats['name_line'] = f"{name_data}"
    #rep_stats['name_line'] = f"{name}"

    ##################################################
    #      EITHER CONGRESS OR GOVERNOR               #
    ##################################################
    chamber = rep_info.get('chamber')
    if chamber == "House of Representatives":
        rep_stats['title_line'] = "Congress"
    elif chamber == "Senate":
        rep_stats['title_line'] = "Congress"
    elif chamber == "Governor":
        rep_stats['title_line'] = "Governor"
    else:
        rep_stats['title_line'] = "Unknown Position"
    
    rep_stats['chamber_line'] = f"{chamber}"
    ##################################################
    #    XXXX-Present | Up for re-election in 20XX   #
    ##################################################
    #tenure = f"{rep_info['tenure_rank_current_party']}/{rep_info['party_current_count']}"
    #party = rep_info['partyName']

    if (rep_info['bg_endYear'] - 1 > date.today().year):
        range = str(rep_info['bg_startYear']) + " - Present"
        rep_stats['reelection_line'] = f"{range} | Up for re-election in {str(rep_info['bg_endYear']-1)}"
    elif (rep_info['bg_endYear'] - 1 < date.today().year):
        range = f"{rep_info['bg_startYear']} - {rep_info['bg_endYear']}"
        rep_stats['reelection_line'] = f"Served from {range}"
    else:
        range = str(rep_info['bg_startYear']) + " - Present"
        rep_stats['reelection_line'] =  f"{range} | Up for re-election this year"
    

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
        rep_stats['birthplace_line'] = f"Unknown"
    else:
        birthplace = draw_wrapped_text(draw, birthplace, font, max_width)
        rep_stats['birthplace_line'] = f"{birthplace}"

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

    rep_stats['age_line'] = f"{age}"


    ##################################################
    #        EDUCATION: School 1, School 2           #
    ##################################################
    ed_list = rep_info.get('education', [])
    if ed_list:
        if len(ed_list) > 1:
            if ed_list[0] == "High school graduate":
                ed_list.pop(0) #get rid of the high school info
        education = "||BREAK_DOT||".join(ed_list)
        rep_stats['education_line'] = f"||BREAK_DOT||{education}"
    else:
        rep_stats['education_line'] = ""

    #############SECTION 2 #########################
    #Voting Record: %f percentage
    #Tenure: %f percentage
    #Historically has voted with party %n, Democratic %n, Republican %n
    #voting_pct = rep_info.get('with_R_percent', None)
    voting_pct = rep_info.get('for_bar', None)

    if voting_pct is not None:
        rep_stats['vote_with_party_percentile'] = f"{voting_pct}"

    create_vote_block(rep_info, absolute_stats, rep_stats)

    key = f"max_tenure_{chamber[0].upper()}"
    max_tenure = absolute_stats.get(key)

    duration = rep_info.get('bg_duration', None)
    tenure_marker = int((duration/max_tenure)*100)
    rep_stats['tenure_percentile'] = tenure_marker
    tenure_pct = rep_info.get("bg_tenure_rank_current_percentile", None)
    if tenure_pct is not None:
        if duration is None:
            rep_stats['tenure_percentile_formatted'] = f"{num_to_percentile(tenure_pct)}"
        elif duration < 1:
            duration = duration*12
            if duration < 1: #if less than 1 month
                rep_stats['tenure_percentile_formatted'] = f"{num_to_percentile(tenure_pct)} (<1 month)"

            else:
                rep_stats['tenure_percentile_formatted'] = f"{num_to_percentile(tenure_pct)} ({duration:.{2}g} months)"
        elif duration == 1:
            rep_stats['tenure_percentile_formatted'] = f"{num_to_percentile(tenure_pct)} ({duration} year)"
        else:
            rep_stats['tenure_percentile_formatted'] = f"{num_to_percentile(tenure_pct)} ({duration} years)"


    rep_stats['max_tenure'] = f"{max_tenure}"

    gen_summary_stats(rep_info, rep_stats)
    gen_committee_list(rep_info, rep_stats)


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
    get_work_history(rep_info, draw, font, max_width, rep_stats)


    gen_bonus_section(rep_info, draw, font, max_width, rep_stats)
    gen_top_issues_prototype(rep_info, draw, font, max_width, rep_stats)
    gen_top_donors_prototype(rep_info, draw, font, max_width, rep_stats)


    #################################################
    ####### Add in paths for save, template
    ################################################

    temp_file = os.path.join(generated_outputs, "temp.txt")

    cards_dir = save_path
    os.makedirs(cards_dir, exist_ok=True)

    replacements = str.maketrans({",": "", "\"": "", ".":"", " ":"_"})
    
    output_filename = os.path.join(cards_dir, \
        f"{name.translate(replacements).lower()}_card.psd")
    rep_stats['file_save_path'] = output_filename

    party = rep_info.get('partyName')
    if party=="Republican":
        rep_stats['template_path'] = os.path.join(assets_dir, "templates", "Republican-House_Senate_Gov-Social.psd")
    elif party=="Democrat":
        rep_stats['template_path'] = os.path.join(assets_dir, "templates", "Democrat-House_Senate_Gov-Social.psd")
    else:
        rep_stats['template_path'] = os.path.join(assets_dir, "templates", "Independent-House_Senate_Gov-Social.psd")


    #################################################
    ####### Write to temp file
    ################################################
    with open(temp_file, 'w') as f:
        f.write("var rep_info = ")
        json.dump(rep_stats, f, indent=4)
        f.write(";")
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




def get_rep_info(full_rep_info, name):
    """
    Name has already been vetted by the electron app.
    Don't need to check for it having a match in rep_info.
    Return rep_info for that rep.
    """


    for rep_info in full_rep_info:
        rep_name = rep_info.get('name')
        if rep_name == name:
            return rep_info
        
    print(f"Representative {name} not found")
    return None


#used for main.py
def gen_temp_for_javascript(name, generated_outputs, assets_dir, save_path, font_path):

    abs_stat_f = os.path.join(generated_outputs, "absolute_stats.json")
    supplement_f = os.path.join(generated_outputs, "supplement_congressmen.json")
    congressmen_f = os.path.join(generated_outputs, "congressmen_mod.json")

    #Load in rep_info
    try: 
        with open(congressmen_f, 'r') as f:
            full_rep_info = json.load(f)
    except Exception as e:
        print("There is an issue loading in the congressmen_mod.json. Quitting.")

    rep_info = get_rep_info(full_rep_info, name)

    #Load in the absolute_stats JSON
    try: 
        with open(abs_stat_f, 'r') as abs_f:
            absolute_stats = json.load(abs_f)[0]
    except Exception as e:
        print("There is an issue with the absolute_stats.json. Quitting.")
        return
    
    #Load in the supplement JSON
    try: 
        with open(supplement_f, 'r') as supp_f:
            supplement_data = json.load(supp_f)
    except Exception as e:
        print("There is an issue with the supplement_congressmen.json. Quitting.")
        return

    load_global_fonts(font_path)

    rep_info = merge_in_supplement(rep_info, supplement_data)
    create_temp(rep_info, absolute_stats, generated_outputs, assets_dir, save_path)
    pull_pic_from_web(rep_info, generated_outputs, dummy=False)


#used for electron
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pull info for Photoshop automation")
    parser.add_argument('name', help="Name of congressman to run")
    parser.add_argument('generated_outputs', help="Path to generated_outputs")
    parser.add_argument('pp_assets', help="Path for psd assets")
    parser.add_argument('save_path', help="Path for outputs")
    parser.add_argument('font_path', help="Path for fonts")
    args = parser.parse_args()
    name = args.name
    generated_outputs = args.generated_outputs
    assets_dir = args.pp_assets
    save_path = args.save_path
    font_path = args.font_path

    gen_temp_for_javascript(name, generated_outputs, assets_dir, save_path, font_path)