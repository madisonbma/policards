from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import requests # We will still use requests to make a quick check
import json
import os

# List of Bioguide IDs to download
bioguide_ids = [
    'A000370'
]

# The directory where the JSON files will be saved
output_dir = 'congress_data'
os.makedirs(output_dir, exist_ok=True)

# Set up the Selenium WebDriver
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # Run in the background without a UI
options.add_argument('--disable-gpu') # Needed for some systems

try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
except Exception as e:
    print(f"Error setting up WebDriver: {e}")
    print("Please make sure you have Chrome installed and WebDriver is correctly configured.")
    exit()

for bio_id in bioguide_ids:
    url = f"https://bioguide.congress.gov/search/bio/{bio_id}.json"
    file_path = os.path.join(output_dir, f"{bio_id}.json")

    try:
        # Selenium can't directly handle the .json endpoint.
        # Instead, we will visit the regular HTML page to get the necessary cookies.
        page_url = f"https://bioguide.congress.gov/search/{bio_id}"
        print(f"Opening browser to {page_url}...")
        driver.get(page_url)
        
        # Give the page a moment to load and for any security scripts to run
        time.sleep(5)
        
        # Now, get the cookies from the live session and pass them to requests
        cookies = driver.get_cookies()
        
        # Create a session to use the cookies with the requests library
        with requests.Session() as session:
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])
            
            # Now, try to make the request to the JSON endpoint with the session
            print(f"Downloading JSON data from {url}...")
            response = session.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
                'Referer': page_url
            })
            response.raise_for_status()
            
            json_data = response.json()
            with open(file_path, 'w') as f:
                json.dump(json_data, f, indent=4)
            print(f"Successfully saved {file_path}")

    except Exception as e:
        print(f"An error occurred for ID {bio_id}: {e}")
        continue
    
driver.quit()
print("\nAll download attempts complete.")