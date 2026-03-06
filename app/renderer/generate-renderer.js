/**
 * STEP 1: would you like to update congressmen data? Should be done at least Jan 3 of every year
 *  yes/no
 * STEP 2: would you like to update voting records? The more often this is done the shorter it'll take
 *  yes/no
 * STEP 3: get name input of rep to generate
 *  nameInput, nameSuggestions, nameSubmitBtn, cancelBtn
 * STEP 4: this is the current info. update as needed.
 *  key, field for all keys
 *  add new field
 *  submit
 * STEP 5: close or add another
 */

const genCardsBtn = document.getElementById('genCardsBtn');
const updateDataBtn = document.getElementById('updateDataBtn');
const status_doc = document.getElementById('status');
const spinner = document.getElementById('spinner');




// Modal elements
const modal = document.getElementById('manualInsertModal');
const step1 = document.getElementById('step1');
const step2 = document.getElementById('step2');
const step3 = document.getElementById('step3');
const step4 = document.getElementById('step4');
const step5 = document.getElementById('step5');
const step6 = document.getElementById('step6');
const step7 = document.getElementById('step7');

//Step 1 elements
const yesConBtn = document.getElementById('yesGenCongressmenBtn')
const noConBtn = document.getElementById('noGenCongressmenBtn')

//Step 2 elements
const yesVoteBtn = document.getElementById('yesGenVotesBtn')
const noVoteBtn = document.getElementById('noGenVotesBtn')

// Step 3 elements
const nameInput = document.getElementById('nameInput');
const nameSuggestions = document.getElementById('nameSuggestions');
const nameSubmitBtn = document.getElementById('nameSubmitBtn');
const cancelBtn = document.getElementById('cancelBtn');

// Step 4 elements
const fieldSelect = document.getElementById('fieldSelect');
const fieldSubmitBtn = document.getElementById('fieldSubmitBtn');
const noUpdateBtn = document.getElementById('noUpdateBtn');
const backToNameBtn = document.getElementById('backToNameBtn');

// Step 5 elements
const currentValue = document.getElementById('currentValue');
const valueInput = document.getElementById('valueInput');
const valueLabel = document.getElementById('valueLabel');
const saveBtn = document.getElementById('saveBtn');
const backToConfirmBtn = document.getElementById('backToConfirmBtn');

// Step 6 elements
const genCardBtn = document.getElementById('genCardBtn');
const addAnotherBtn = document.getElementById('addAnotherBtn');

//Step 7 elements
const genNewCardBtn = document.getElementById('genNewCardBtn');
const quitBtn = document.getElementById('quitBtn');

// Output display elements
const outputContainer = document.getElementById('outputContainer');
const outputDisplay = document.getElementById('outputDisplay');
const clearOutputBtn = document.getElementById('clearOutputBtn');


////////////////////////////////

// State
let fullRepInfo = [];
let supplement = [];
let selectedRep = null;
let selectedField = '';
let currentFieldValue = null;

const LIST_FIELDS = ['committees', 'education', 'military', 'illegal', 'failed_runs', 'work_history', 'congress_highlights', 'accolades', 'family', 'top_donors', 'top_issues'];

function showOutput(text) {
  outputContainer.classList.add('show');
  const timestamp = new Date().toLocaleTimeString();
  outputDisplay.textContent += `[${timestamp}]\n${text}\n\n`;
  outputDisplay.scrollTop = outputDisplay.scrollHeight;
}

function clearOutput() {
  outputDisplay.textContent = '';
  outputContainer.classList.remove('show');
}

clearOutputBtn.addEventListener('click', clearOutput);

function showStatus(message, isSuccess) {
  status_doc.textContent = message;
  status_doc.className = 'status show ' + (isSuccess ? 'success' : 'error');
  setTimeout(() => {
    status_doc.className = 'status';
  }, 5000);
}

function setLoading(isLoading) {
  genCardsBtn.disabled = isLoading;
  updateDataBtn.disabled = isLoading;
  if (isLoading) {
    spinner.classList.add('show');
  } else {
    spinner.classList.remove('show');
  }
}

function showStep(stepNum) {
  [step1, step2, step3, step4, step5, step6, step7].forEach(s => s.classList.add('hidden'));
  
  if (stepNum === 1) step1.classList.remove('hidden');
  else if (stepNum === 2) step2.classList.remove('hidden');
  else if (stepNum === 3) step3.classList.remove('hidden');
  else if (stepNum === 4) step4.classList.remove('hidden');
  else if (stepNum === 5) step5.classList.remove('hidden');
  else if (stepNum === 6) step6.classList.remove('hidden');
  else if (stepNum === 7) step7.classList.remove('hidden');
}

function openModal() {
  modal.classList.add('show');
  nameInput.value = '';
  nameSuggestions.innerHTML = '';
  fieldSelect.value = '';
  valueInput.value = '';
  selectedRep = null;
  selectedField = '';
}

function closeModal() {
  modal.classList.remove('show');
}

function displayCurrentData() {
  const currentDataDisplay = document.getElementById('currentDataDisplay');
  currentDataDisplay.innerHTML = '';
  
  const fieldsToDisplay = [
    'url', 'imageUrl', 'endYear', 'committees', 'photo', 'birthDate',
    'education', 'military', 'illegal', 'failed_runs', 'work_history',
    'congress_highlights', 'accolades', 'family', 'birthplace', 'top_donors',
    'top_issues'
  ];
  
  const fieldLabels = {
    'url': 'URL',
    'imageUrl': 'Image URL',
    'endYear': 'End Year',
    'committees': 'Committees',
    'photo': 'Photo',
    'birthDate': 'Birth Date',
    'education': 'Education',
    'military': 'Military',
    'illegal': 'Illegal Activities',
    'failed_runs': 'Failed Runs',
    'work_history': 'Work History',
    'congress_highlights': 'Congress Highlights',
    'accolades': 'Accolades',
    'family': 'Personal',
    'top_donors': 'Top Donors',
    'top_issues': 'Top Issues',
    'birthplace': 'Birthplace',
  };
  
  fieldsToDisplay.forEach(field => {
    const value = selectedRep[field];
    const row = document.createElement('div');
    row.className = 'data-row';
    
    const keyDiv = document.createElement('div');
    keyDiv.className = 'data-key';
    keyDiv.textContent = fieldLabels[field] || field;
    
    const valueDiv = document.createElement('div');
    valueDiv.className = 'data-value';
    
    if (value === undefined || value === null || value === '') {
      valueDiv.textContent = '(empty)';
      valueDiv.style.fontStyle = 'italic';
      valueDiv.style.color = '#adb5bd';
    } else if (Array.isArray(value)) {
      if (value.length === 0) {
        valueDiv.textContent = '(empty)';
        valueDiv.style.fontStyle = 'italic';
        valueDiv.style.color = '#adb5bd';
      } else {
        const ul = document.createElement('ul');
        value.forEach(item => {
          const li = document.createElement('li');
          li.textContent = item;
          ul.appendChild(li);
        });
        valueDiv.appendChild(ul);
      }
    } else {
      valueDiv.textContent = value;
    }
    
    row.appendChild(keyDiv);
    row.appendChild(valueDiv);
    currentDataDisplay.appendChild(row);
  });
}

// Load data from files
async function loadData() {
  try {
    const data = await window.electronAPI.loadCongressmenData();
    fullRepInfo = data.congressmenMod;
    supplement = data.supplement;
    return true;
  } catch (error) {
    showStatus('Error loading data: ' + error.message, false);
    return false;
  }
}

//Step 1: Ask to update congressmen data
yesConBtn.addEventListener('click', async () => {
  console.log("Running API pull for congressmen.json");
  yesConBtn.disabled = true;
  noConBtn.disabled = true;
  setLoading(true);
  const result = await window.electronAPI.genRepsJSON();
  // Display Python output
  if (result.output) {
    showOutput(result.output);
  }
  if (result.success) {
    console.log("success");
    setLoading(false);
    yesConBtn.disabled = false;
    noConBtn.disabled = true;

    showStep(2);
  } else {
    showStatus('Error making congressmen.json: ' + result.message, false);
    yesConBtn.disabled = false;
    noConBtn.disabled = true;

  }

});
noConBtn.addEventListener('click', () => {
  console.log("Not updating congressmen.json");
  showStep(2);
});


//Step 2: Ask to update voting data
//in both, need to re-merge data.
yesVoteBtn.addEventListener('click', async () => {
  console.log("Running API pull for voting_record.json");
  yesVoteBtn.disabled = true;
  noVoteBtn.disabled = true;
  setLoading(true);
  const result_vote = await window.electronAPI.genVotingRecordJSON();
  if (result_vote.output) {
    showOutput(result_vote.output);
  }
  if (result_vote.success) {
    console.log("success in genVotingRecordJSON");
    const result_combine = await window.electronAPI.combineData();
    if (result_combine.output) {
      showOutput(result_combine.output);
    }
    if (result_combine.success) {
      console.log('success in combineData')
      const loaded = await loadData();
      setLoading(false);
      yesVoteBtn.disabled = false;
      noVoteBtn.disabled = false;
      if (loaded){
        showStep(3);
      }
    }
    else {
      showStatus('Error combining data: ' + result_combine.message, false);
      yesVoteBtn.disabled = false;
      noVoteBtn.disabled = false;

    }

  } else {
    showStatus('Error making voting_record.json: ' + result_vote.message, false);
    yesVoteBtn.disabled = false;
    noVoteBtn.disabled = false;
  }

});
noVoteBtn.addEventListener('click', async () => {
  console.log("Not updating voting_record.json");
  setLoading(true);
  noVoteBtn.disabled = true;
  yesVoteBtn.disabled = true;
  const result_combine = await window.electronAPI.combineData();
  if (result_combine.output) {
    showOutput(result_combine.output);
  }
  if (result_combine.success) {
    console.log('success in combineData')
    const loaded = await loadData();
    setLoading(false);
    if (loaded){
      showStep(3);
    }
  }
  else {
    showStatus('Error loading/combining data: ' + result_combine.message, false);
    noVoteBtn.disabled = false;
    yesVoteBtn.disabled = false;
  }

});

//Step 3: Name and input suggestions
nameInput.addEventListener('input', () => {
  const input = nameInput.value.toLowerCase().trim();
  nameSuggestions.innerHTML = '';
  
  if (input.length === 0) return;
  
  // We use a Set to ensure we don't show the same person twice 
  // (e.g., if they match both 'starts with' and 'last name')
  const matches = [];
  const inputParts = input.split(' ');
  const lastInputPart = inputParts[inputParts.length - 1];
  
  for (const rep of fullRepInfo) {
    const repName = rep.name.toLowerCase();
    const repParts = repName.split(' ');
    const repLastName = repParts[repParts.length - 1];
    
    // Check 1: Does the full name START with the input? (e.g., "John D" matches "John Doe")
    const startsWithMatch = repName.startsWith(input);
    
    // Check 2: Does the last name match exactly?
    const lastNameMatch = repLastName === lastInputPart;

    if (startsWithMatch) {
      // Prioritize "starts with" matches at the top
      matches.push(rep);
    } else if (lastNameMatch) {
      // Add last name matches to the end
      matches.push(rep);
    }
  }

  // UI Rendering
  if (matches.length > 0) {
    // Limit to top 10 results so the UI doesn't explode
    matches.slice(0, 10).forEach(rep => {
      const div = document.createElement('div');
      div.className = 'suggestion-item';
      div.textContent = rep.name;
      div.onclick = () => {
        nameInput.value = rep.name;
        nameSuggestions.innerHTML = '';
        selectedRep = rep;
        // Trigger whatever function opens your editor here
        console.log("Selected:", selectedRep);
      };
      nameSuggestions.appendChild(div);
    });
  } else if (input.length > 2) {
    nameSuggestions.innerHTML = '<div class="suggestion-item">No matches found</div>';
  }
});

nameSubmitBtn.addEventListener('click', () => {
  const input = nameInput.value.trim();
  if (!input) {
    showStatus('Please enter a name', false);
    return;
  }
  // Find exact match
  const match = fullRepInfo.find(rep => rep.name.toLowerCase() === input.toLowerCase());
  if (!match) {
    showStatus('Representative not found', false);
    return;
  }
  selectedRep = match;
  document.getElementById('selectedName').textContent = selectedRep.name;
  displayCurrentData();
  showStep(4);
});

cancelBtn.addEventListener('click', closeModal);
//////////////////////////////////////////////////////////////


// Step 4: Field selection
fieldSubmitBtn.addEventListener('click', () => {
  selectedField = fieldSelect.value;
  
  if (!selectedField) {
    showStatus('Please select a field', false);
    return;
  }
  
  currentFieldValue = selectedRep[selectedField];
  
  document.getElementById('selectedName2').textContent = selectedRep.name;
  document.getElementById('selectedField').textContent = selectedField;
  
  // Display current value
  if (currentFieldValue === undefined || currentFieldValue === null) {
    currentValue.textContent = '(empty)';
  } else if (Array.isArray(currentFieldValue)) {
    currentValue.innerHTML = '<ul>' + currentFieldValue.map(v => '<li>' + v + '</li>').join('') + '</ul>';
  } else {
    currentValue.textContent = currentFieldValue;
  }
  
  showStep(5);
});

noUpdateBtn.addEventListener('click', () => {
  showStep(6);
});

backToNameBtn.addEventListener('click', () => showStep(3));


// Step 5: Update fields as needed
saveBtn.addEventListener('click', async () => {
  const newValue = valueInput.value.trim();
  
  if (!newValue) {
    showStatus('Please enter a value', false);
    return;
  }
  
  // Update supplement
  const isListField = LIST_FIELDS.includes(selectedField);
  let existingEntry = supplement.find(s => s.name === selectedRep.name);
  
  if (existingEntry) {
    if (isListField) {
      if (!existingEntry[selectedField]) {
        existingEntry[selectedField] = [];
      }
      existingEntry[selectedField].push(newValue);
    } else {
      existingEntry[selectedField] = newValue;
    }
  } else {
    const newEntry = { name: selectedRep.name };
    if (isListField) {
      newEntry[selectedField] = [newValue];
    } else {
      newEntry[selectedField] = newValue;
    }
    supplement.push(newEntry);
  }
  
  // Save to file
  const result = await window.electronAPI.saveSupplement(supplement);
  
  if (result.success) {
    showStep(6);
  } else {
    showStatus('Error saving data: ' + result.message, false);
  }
});

backToConfirmBtn.addEventListener('click', () => showStep(3));

// Step 6: Success updating congressman, gen card or update another field
genCardBtn.addEventListener('click', async () => {
  setLoading(true);
  console.log("running gen card");

  const result = await window.electronAPI.genCard();

  if (result.output) {
    showOutput(result.output);
  }
  if (result.success) {
    console.log("done with gen card");
    setLoading(false);
    showStep(7);
  }
  else {
    showStatus('Error generating card: ' + result.message, false);
  }
});

addAnotherBtn.addEventListener('click', () => {
  openModal();
  showStep(4);
});

//Step 7: Gen another card or quit?
genNewCardBtn.addEventListener('click', () => {
  showStep(3);
});
quitBtn.addEventListener('click', closeModal);



//updateData (step 0): do not load data, will need to run steps 1 and 2 and combine data
updateDataBtn.addEventListener('click', async () => {
  setLoading(true);
  const loaded = await loadData();
  setLoading(false);
  
  if (loaded) {
    openModal();
    showStep(1);
  }
});

//genCards (step 0): load data and go to look for name
genCardsBtn.addEventListener('click', async () => {
  setLoading(true);
  const loaded = await loadData();

  setLoading(false);
  
  if (loaded) {
    openModal();
    showStep(3);
  }
});