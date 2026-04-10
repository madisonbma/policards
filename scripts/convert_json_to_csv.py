import os 
import json
import csv

if __name__ == "__main__":

    root_path = os.path.dirname(os.path.abspath(__file__))
    root_path = os.path.join(root_path, '..', 'src', 'generated_outputs')
    # Load the JSON data

    json_files = [f for f in os.listdir(root_path) if f.endswith('.json')]

    for file_name in json_files:
        file_name_clean = file_name.replace('.json', '')
        full_path = os.path.join(root_path, file_name)
        #print(full_path)
        #open the JSON file and load the data
        with open(os.path.join(root_path, file_name), 'r') as json_file:
            data = json.load(json_file)

        # Open a CSV file for writing
        with open(f'{file_name_clean}.csv', 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)

            # Write the header row (keys of the first dictionary)
            header = data[0].keys()
            writer.writerow(header)

            # Write the data rows
            for entry in data:
                writer.writerow(entry.values())

        print("Done converting JSON to CSV for file:", file_name)