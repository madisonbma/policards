/**
 * STEP 1: get name inputs
 * STEP 2: choose field to update
 * STEP 3: show current data, prompt for new
 * STEP 4: update the field
 * STEP 5: close or add another
 */

const refetchBtn = document.getElementById('refetchBtn');
const manualInsertBtn = document.getElementById('manualInsertBtn');
const status_doc = document.getElementById('status');
const spinner = document.getElementById('spinner');




// Modal elements
const modal = document.getElementById('manualInsertModal');
const step1 = document.getElementById('step1');
const step2 = document.getElementById('step2');
const step3 = document.getElementById('step3');
const step4 = document.getElementById('step4');
const step5 = document.getElementById('step5');

// Step 1 elements
const nameInput = document.getElementById('nameInput');
const nameSuggestions = document.getElementById('nameSuggestions');
const nameSubmitBtn = document.getElementById('nameSubmitBtn');
const cancelBtn = document.getElementById('cancelBtn');

// Step 2 elements
const fieldSelect = document.getElementById('fieldSelect');
const fieldSubmitBtn = document.getElementById('fieldSubmitBtn');
const backToNameBtn = document.getElementById('backToNameBtn');

// Step 3 elements
const confirmUpdateBtn = document.getElementById('confirmUpdateBtn');
const backToFieldBtn = document.getElementById('backToFieldBtn');
const currentValue = document.getElementById('currentValue');

// Step 4 elements
const valueInput = document.getElementById('valueInput');
const valueLabel = document.getElementById('valueLabel');
const saveBtn = document.getElementById('saveBtn');
const backToConfirmBtn = document.getElementById('backToConfirmBtn');

// Step 5 elements
const closeModalBtn = document.getElementById('closeModalBtn');
const addAnotherBtn = document.getElementById('addAnotherBtn');

// State
let fullRepInfo = [];
let supplement = [];
let selectedRep = null;
let selectedField = '';
let currentFieldValue = null;

const LIST_FIELDS = ['committees', 'education', 'military', 'illegal', 'failed_runs', 'work_history', 'congress_highlights', 'accolades', 'family'];

function showStatus(message, isSuccess) {
  status_doc.textContent = message;
  status_doc.className = 'status show ' + (isSuccess ? 'success' : 'error');
  setTimeout(() => {
    status_doc.className = 'status';
  }, 5000);
}

function setLoading(isLoading) {
  refetchBtn.disabled = isLoading;
  manualInsertBtn.disabled = isLoading;
  if (isLoading) {
    spinner.classList.add('show');
  } else {
    spinner.classList.remove('show');
  }
}

function showStep(stepNum) {
  [step1, step2, step3, step4, step5].forEach(s => s.classList.add('hidden'));
  
  if (stepNum === 1) step1.classList.remove('hidden');
  else if (stepNum === 2) step2.classList.remove('hidden');
  else if (stepNum === 3) step3.classList.remove('hidden');
  else if (stepNum === 4) step4.classList.remove('hidden');
  else if (stepNum === 5) step5.classList.remove('hidden');
}

function openModal() {
  modal.classList.add('show');
  showStep(1);
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

//Step 1: Name and input suggestions
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
  showStep(2);
});

cancelBtn.addEventListener('click', closeModal);

// Step 2: Field selection
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
    currentValue.textContent = '(not set)';
  } else if (Array.isArray(currentFieldValue)) {
    currentValue.innerHTML = '<ul>' + currentFieldValue.map(v => '<li>' + v + '</li>').join('') + '</ul>';
  } else {
    currentValue.textContent = currentFieldValue;
  }
  
  showStep(3);
});

backToNameBtn.addEventListener('click', () => showStep(1));

// Step 3: Confirm update
confirmUpdateBtn.addEventListener('click', () => {
  document.getElementById('selectedName3').textContent = selectedRep.name;
  document.getElementById('selectedField2').textContent = selectedField;
  
  // Set appropriate label based on field type
  if (selectedField === 'birthDate') {
    valueLabel.textContent = 'Enter new birth date (YYYY-MM-DD):';
  } else if (LIST_FIELDS.includes(selectedField)) {
    const fieldLabels = {
      'committees': 'committee',
      'education': 'education entry',
      'military': 'military service',
      'illegal': 'illegal activity',
      'failed_runs': 'failed run',
      'work_history': 'work history entry',
      'congress_highlights': 'congressional highlight',
      'accolades': 'accolade',
      'family': 'family member'
    };
    valueLabel.textContent = `Enter ${fieldLabels[selectedField] || 'value'} to add:`;
  } else {
    valueLabel.textContent = 'Enter new value:';
  }
  
  showStep(4);
});

backToFieldBtn.addEventListener('click', () => showStep(2));

// Step 4: Enter new value
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
    showStep(5);
  } else {
    showStatus('Error saving data: ' + result.message, false);
  }
});

backToConfirmBtn.addEventListener('click', () => showStep(3));

// Step 5: Success
closeModalBtn.addEventListener('click', closeModal);

addAnotherBtn.addEventListener('click', () => {
  openModal();
});

// Main button handlers
refetchBtn.addEventListener('click', async () => {
  setLoading(true);
  status_doc.className = 'status';
  
  const result = await window.electronAPI.refetchData();
  
  setLoading(false);
  showStatus(result.message, result.success);
});

manualInsertBtn.addEventListener('click', async () => {
  setLoading(true);
  const loaded = await loadData();
  setLoading(false);
  
  if (loaded) {
    openModal();
  }
});