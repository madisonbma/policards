const saveBtn = document.getElementById('saveBtn');
const status_doc = document.getElementById('status');
const currentDataDisplay = document.getElementById('currentDataDisplay');

let config = [];

function showStatus(message, isSuccess) {
  console.log(message);
  status_doc.textContent = message;
  status_doc.className = 'status show ' + (isSuccess ? 'success' : 'error');
  setTimeout(() => {
    status_doc.className = 'status';
  }, 5000);
}

// Load data from files
async function loadAndDisplayData() {
  try {
    const data = await window.electronAPI.loadConfigData();
    config = data.config;
    console.log("Loaded data:", config);
    displayConfigData();

    return true;
  } catch (error) {
    showStatus('Error loading data: ' + error.message, false);
    return false;
  }
}


function displayConfigData() {
  currentDataDisplay.innerHTML = '';

  Object.keys(config).forEach(key => {
    const value = config[key];

    const row = document.createElement('div');
    row.className = 'data-row';

    const keyDiv = document.createElement('div');
    keyDiv.className = 'data-key';
    keyDiv.textContent = key;
    
    const valueDiv = document.createElement('input');
    valueDiv.setAttribute('type', 'text');
    valueDiv.setAttribute('id', 'cfg_' + key);
    //valueDiv.setAttribute('placeholder', value);
    valueDiv.value = value;

    
    if (value === undefined || value === null || value === '') {
      valueDiv.setAttribute('placeholder', '(empty)');
      valueDiv.style.fontStyle = 'italic';
      valueDiv.style.color = '#adb5bd';
    } else {
      valueDiv.value = value;
      valueDiv.setAttribute('placeholder', value);

    }

    
    row.appendChild(keyDiv);
    row.appendChild(valueDiv);
    currentDataDisplay.appendChild(row);
  });
}

//////////////////////////
// Process 
/////////////////////////
window.onload = loadAndDisplayData;


saveBtn.addEventListener('click', async () => {
    //go row by row and save the value if it exists, otherwise throw an error
    //check if any configs are empty, error if so
    const rows = currentDataDisplay.children;
    for (const row of Array.from(rows)) {
        const keyDiv = row.children[0];
        const key = keyDiv.textContent;
        const valueInput = row.children[1]; //0 is key, 1 is value

        const newValue = valueInput.value.trim();
        //if updated val, save that one
        if (newValue) {
          //now check if it's safe to save:
          if (key === "politician_pages_assets_path") {
            const assets_ok = await window.electronAPI.checkPathExists(newValue);
            if (!assets_ok) {
              showStatus("Won't save, politician_pages_assets_path invalid");
              return;
            }
          }
            config[key] = newValue;
            console.log("saving ", key, ": ", newValue);
            valueInput.setAttribute('placeholder', newValue);
            valueInput.value = newValue;
        }

    }
    //now save the configs to file
    console.log("Sending: ", config);
    const result = await window.electronAPI.saveConfigData(config);
  
    if (result.success) {
        showStatus("Saved. Close this page.", true)
    } else {
        showStatus('Error saving data: ' + result.message, false);
    }
});
