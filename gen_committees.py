import xml.etree.ElementTree as ET
import requests
from init_logger import my_logger

# Define the XML content as a string for this example
# In your case, you would load this from a file or a web request

def get_root(url):
    """Gets an XML from a given URL"""
    try:
        response = requests.get(url)
        xml_content = response.content  # The XML content as bytes
        root = ET.fromstring(xml_content)
        return root
    except requests.exceptions.ConnectionError as e:
        my_logger.error(f"Connection error: {e}")
    except requests.exceptions.HTTPError as e:
        my_logger.error(f"HTTP error: {e}")


def get_committee_codes_senate(root):
    """
    Parses a string of XML content to extract member information
    and their committee assignments into a dictionary.
    """
    member_assignments = {}
    try:

        # Iterate through each <member> child of the <senator> list
        for member_element in root.findall('senator'):
            # 1. Get the bioguideID
            bioguide_element = member_element.find('bioguideId')
            if bioguide_element is not None:
                bioguide_id = bioguide_element.text
            else:
                continue  # Skip this member if the ID isn't found

            # 2. Get the committee-assignments list
            assignments_list = []
            committee_assignments_element = member_element.find('committees')
            
            if committee_assignments_element is not None:
                # Iterate over all children of <committee-assignments> and add them to the list
                for assignment in committee_assignments_element:
                    seat = assignment.get('position')
                    if seat is not None:
                        comm_name = seat + ": " + assignment.text
                    else:
                        comm_name = assignment.text
                    assignments_list.append(comm_name)

            
            # 3. Store the information in the dictionary
            member_assignments[bioguide_id] = assignments_list
        my_logger.info("Success getting list of comcodes per bioguideID for senate")
        return member_assignments
    
    except ET.ParseError as e:
        my_logger.error(f"Error parsing XML: {e}")
        return None
    


def get_committee_codes_house(root):
    """
    Parses a string of XML content to extract member information
    and their committee assignments into a dictionary.

    Returns:
        A dictionary where the key is the bioguideID and the value is a
        list of all committee and subcommittee assignments.
    """
    # Create the dictionary to store the results
    member_assignments = {}

    try:
        # Parse the XML from the string
        #root = tree.getroot()
        
        # Navigate to the correct parent element, which is the <members> tag.
        # This corresponds to root[1] in the XML structure you described.
        members_list = root.find('members')

        if members_list is None:
            my_logger.error("Error: The <members> element was not found.")
            return None

        # Iterate through each <member> child of the <members> list
        for member_element in members_list.findall('member'):
            # 1. Get the bioguideID
            bioguide_element = member_element.find('member-info/bioguideID')
            if bioguide_element is not None:
                bioguide_id = bioguide_element.text
            else:
                continue  # Skip this member if the ID isn't found

            # 2. Get the committee-assignments list
            assignments_list = []
            committee_assignments_element = member_element.find('committee-assignments')
            
            if committee_assignments_element is not None:
                # Iterate over all children of <committee-assignments> and add them to the list
                for assignment in committee_assignments_element:
                    assignments_list.append(assignment.attrib)

            
            # 3. Store the information in the dictionary
            member_assignments[bioguide_id] = assignments_list
        my_logger.info("Success getting list of comcodes per bioguideID for House")
        return member_assignments

    except ET.ParseError as e:
        my_logger.error(f"Error parsing XML: {e}")
        return None



def get_comm_codes_to_names_house(root):
    """
    Will pull from this same XML to get the committee name
    """
    comm_dict = {}

    #root = tree.getroot()
    committees_list = root.find('committees')
    if committees_list is None:
        my_logger.error("Error: The <committees> element was not found.")
        return None
    
    for comm in committees_list:
        comcode = comm.attrib.get('comcode')
        comname = comm.find('committee-fullname').text
        comm_dict[comcode] = comname
        subcoms = comm.findall('subcommittee')
        if subcoms is None:
            my_logger.warning(f"No subcommittees found for {comname}")
        else:
            for subcom in subcoms:
                subcomcode = subcom.attrib.get('subcomcode')
                subcomname = subcom.find('subcommittee-fullname').text
                subcomname = f"{comname}: {subcomname}"
                comm_dict[subcomcode] = subcomname

    my_logger.info(f"Success getting list of (sub)committee names for comcode")
    return comm_dict

def convert_comm_codes_house(code_bioguide_dict, code_name_dict):
    """
    Will remove the committee codes and swap with the names. Returns the stuff we actually want.

    bioguideID: [[Committee1_Name, Rank, Leadership], [Committee2, Rank], [Committee3, Rank]]
    Bioguide ID: T000165
    Assignments: [{'comcode': 'II00', 'rank': '10'}, 
    {'comcode': 'JU00', 'rank': '5'}, 
    {'subcomcode': 'II06', 'rank': '6'}, 
    {'subcomcode': 'II10', 'rank': '1', 'leadership': 'Chair'}, 
    {'subcomcode': 'JU01', 'rank': '3'}, 
    {'subcomcode': 'JU08', 'rank': '2'}]

    """
    final_dict = {}
    for bioguide_id in code_bioguide_dict:
        returned_comm_list = []
        person_comm_list = code_bioguide_dict[bioguide_id]
        for comm in person_comm_list:
            comcode = comm.get('comcode')
            if comcode is None:
                comcode = comm.get('subcomcode')
            if comcode is None:
                my_logger.warning(f"Comcode not found for {bioguide_id}, Nonetype returned.")
            else:
                if comcode in code_name_dict:
                    title = comm.get('leadership')
                    if title is not None:
                        returned_comm_list.append(f"{title}: {code_name_dict[comcode]}")
                    else:
                        returned_comm_list.append(code_name_dict[comcode])
                    #comm['name'] = code_name_dict[comcode]
                else:
                    my_logger.warning(f"No mapping available for comcode {comcode}")
        final_dict[bioguide_id] = returned_comm_list

    return final_dict




def gen_house():
    xml_house = "https://clerk.house.gov/xml/lists/memberdata.xml"
    house_root = get_root(xml_house)
    bioguide_w_codes_dict = get_committee_codes_house(house_root)
    codes_w_names_dict = get_comm_codes_to_names_house(house_root)
    final_dict = convert_comm_codes_house(bioguide_w_codes_dict, codes_w_names_dict)
    return final_dict

def gen_senate():
    xml_senate = "https://www.senate.gov/legislative/LIS_MEMBER/cvc_member_data.xml"
    senate_root = get_root(xml_senate)
    final_dict = get_committee_codes_senate(senate_root)
    return final_dict



def gen_committees():
    final_dict_house = gen_house()
    final_dict_senate = gen_senate()
    final_dict = final_dict_house | final_dict_senate
    return final_dict
    