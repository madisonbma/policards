import subprocess


PHOTOSHOP_EXE_PATH = "C:\\Program Files\\Adobe\\Adobe Photoshop 2026\\Photoshop.exe" 

def run_photoshop_script(template, script):
    # Construct the command to open the PSD and then execute the JSX script
    command = [
        PHOTOSHOP_EXE_PATH,
        template,
        "-r",  # Flag often used to indicate running a script
        script
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
    print("Running Photoshop script...")
    run_photoshop_script("C:\\Users\\Owner\\policards\\templates\\Republican-House_Senate_Gov-Social.psd", 
                         "C:\\Users\\Owner\\policards\\src\\fill_social_template.jsx")
    
    #run_photoshop_script("C:\\Users\\Owner\\policards\\templates\\Republican House_Senate-Newsletter.psd", 
    #                     "C:\\Users\\Owner\\policards\\src\\fill_newsletter_template.jsx")