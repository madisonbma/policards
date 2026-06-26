
const genCardsBtn = document.getElementById('genCardsBtn');
const updateDataBtn = document.getElementById('updateDataBtn');
const status_doc = document.getElementById('status');
const spinner = document.getElementById('spinner');

//popup elements
const popup = document.getElementById('popup');



// Modal elements
const modal = document.getElementById('manualInsertModal');
const step1 = document.getElementById('step1');
const step2 = document.getElementById('step2');
const step3 = document.getElementById('step3');
const step4 = document.getElementById('step4');
const step5 = document.getElementById('step5');
const step6 = document.getElementById('step6');
const step7 = document.getElementById('step7');
const step8 = document.getElementById('step8');
const step9 = document.getElementById('step9');
const step10 = document.getElementById('step10');
const step11 = document.getElementById('step11');
const step12 = document.getElementById('step12');
const step13 = document.getElementById('step13');

//Step 1 elements
const yesConBtn = document.getElementById('yesGenCongressmenBtn')
const noConBtn = document.getElementById('noGenCongressmenBtn')
const terminal1 = document.getElementById('terminalOutput1');


//Step 2 elements
const yesVoteBtn = document.getElementById('yesGenVotesBtn')
const noVoteBtn = document.getElementById('noGenVotesBtn')
const terminal2 = document.getElementById('terminalOutput2');

// Step 11 elements (top-donors fetch)
const terminal3 = document.getElementById('terminalOutput3');
const topDonorsHeading = document.getElementById('topDonorsHeading');

// Step 12 elements (top-donors review)
const topDonorsReviewList = document.getElementById('topDonorsReviewList');
const topDonorsReviewName = document.getElementById('topDonorsReviewName');
const topDonorsConfirmBtn = document.getElementById('topDonorsConfirmBtn');

// Step 13 elements (manual candidate entry, shown when bioguide can't be resolved)
const manualCandidateName = document.getElementById('manualCandidateName');
const manualCandidateInput = document.getElementById('manualCandidateInput');
const manualEntryError = document.getElementById('manualEntryError');
const manualCandidateSubmitBtn = document.getElementById('manualCandidateSubmitBtn');
const manualSpinner = document.getElementById('manualSpinner');
const terminal4 = document.getElementById('terminalOutput4');
let currentTopDonorsOverview = {};


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
const missingItemWarning = document.getElementById('missingItemWarning');

// Step 5 elements
const currentValue = document.getElementById('currentValue');
const valueInput = document.getElementById('valueInput');
const valueLabel = document.getElementById('valueLabel');
const saveBtn = document.getElementById('saveBtn');
const backToConfirmBtn = document.getElementById('backToConfirmBtn');

// Step 6 elements
const genCardBtn = document.getElementById('genCardBtn');
const addAnotherBtn = document.getElementById('addAnotherBtn');
const missingItemWarning2 = document.getElementById('missingItemWarning2');


//Step 7 elements
const genNewCardBtn = document.getElementById('genNewCardBtn');
const quitBtn = document.getElementById('quitBtn');

//Step 9 elements
const errorMessage = document.getElementById('errorMessage');

//Step 10 elements
const movedBioguideBtn = document.getElementById('movedBioguideBtn');

////////////////////////////////

// State
let fullRepInfo = [];
let supplement = [];
let selectedRep = null;
let selectedField = '';
let currentFieldValue = null;
let updated_data = false;
let need_update = [];
let recommend_update = [];

const LIST_FIELDS = ['committees', 'education', 'military', 'illegal', 'failed_runs', 'work_history', 'congress_highlights', 'accolades', 'family', 'top_donors', 'top_issues'];

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));



function showStatus(message, isSuccess, duration=3000) {
  console.log(message);
  status_doc.textContent = message;
  status_doc.className = 'status show ' + (isSuccess ? 'success' : 'error');
  setTimeout(() => {
    status_doc.className = 'status';
  }, duration);
}

function showPopup(message) {

  //add yes/no buttons to popup
  popup.textContent = message;
  popup.className = 'popup show';

  const popupConfirmBtn = document.createElement('button');
  const popupCancelBtn = document.createElement('button');

  const butDiv = document.createElement('div');
  popupConfirmBtn.className = 'confirm';
  popupCancelBtn.className = 'cancel';
  popupConfirmBtn.textContent =  'Proceed';
  popupCancelBtn.textContent =  'Cancel';
  popupConfirmBtn.setAttribute('id', 'popupConfirmBtn');
  popupCancelBtn.setAttribute('id', 'popupCancelBtn');
  butDiv.appendChild(popupConfirmBtn);
  butDiv.appendChild(popupCancelBtn);
  popup.appendChild(butDiv);

  //disable field buttons in the meantime
  fieldSubmitBtn.disabled = true;
  noUpdateBtn.disabled = true;
  backToNameBtn.disabled = true;
  genCardBtn.disabled = true;
  addAnotherBtn.disabled = true;

  //on confirm, run the photoshop
  popupConfirmBtn.addEventListener('click', async () => {
    //re-enable the field buttons after confirmation
    fieldSubmitBtn.disabled = false;
    noUpdateBtn.disabled = false;
    backToNameBtn.disabled = false;
    genCardBtn.disabled = false;
    addAnotherBtn.disabled = false;
    popup.className = 'popup';

    showStep(7); //go to photoshop loading page
    setLoading(true);
    console.log("running gen card");
    console.log("Sending to main.js: ", selectedRep.name);

    const result = await window.electronAPI.genCard(selectedRep.name);

    if (result.success) {
      console.log("done with gen card");
      setLoading(false);
      showStep(8);
    }
    else {
      //showStatus('Error generating card: ' + result.message, false);
      errorMessage.textContent = result.message;
      showStep(9);
      setLoading(false);
    }
  });

  //on cancel, go back to field selection page
  popupCancelBtn.addEventListener('click', () => {
    //re-enable the field buttons after confirmation
    fieldSubmitBtn.disabled = false;
    noUpdateBtn.disabled = false;
    backToNameBtn.disabled = false;
    genCardBtn.disabled = false;
    addAnotherBtn.disabled = false;
    popup.className = 'popup';
    show4();
  });
}

function setLoading(isLoading) {
  if (isLoading) {
    spinner.classList.add('show');
  } else {
    spinner.classList.remove('show');
  }
}

function showStep(stepNum) {
  [step1, step2, step3, step4, step5, step6, step7, step8, step9, step10, step11, step12, step13].forEach(s => s.classList.add('hidden'));

  if (stepNum === 1) step1.classList.remove('hidden');
  else if (stepNum === 2) step2.classList.remove('hidden');
  else if (stepNum === 3) step3.classList.remove('hidden');
  else if (stepNum === 4) step4.classList.remove('hidden');
  else if (stepNum === 5) step5.classList.remove('hidden');
  else if (stepNum === 6) step6.classList.remove('hidden');
  else if (stepNum === 7) step7.classList.remove('hidden');
  else if (stepNum === 8) step8.classList.remove('hidden');
  else if (stepNum === 9) step9.classList.remove('hidden');
  else if (stepNum === 10) step10.classList.remove('hidden');
  else if (stepNum === 11) step11.classList.remove('hidden');
  else if (stepNum === 12) step12.classList.remove('hidden');
  else if (stepNum === 13) step13.classList.remove('hidden');
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
  need_update = []; //reset need_update for each rep
  recommend_update = [];
  const currentDataDisplay = document.getElementById('currentDataDisplay');
  missingItemWarning.textContent = '';
  noUpdateBtn.disabled = false; //disable gen card until compliant


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
    'photo': 'Image URL 2',
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

  //selectedRep == congressmen_mod.json rep info
  //supplement   
  let supplemental_data = supplement.find(s => s.name === selectedRep.name);


  let value;
  fieldsToDisplay.forEach(field => {
    // top_donors is stored as [overview, {company: amount}] (not a plain string list),
    // so render it as the list of donor company names with their amounts.
    if (field === 'top_donors') {
        const td = supplemental_data ? supplemental_data['top_donors'] : null;
        if (Array.isArray(td) && td.length >= 2 && td[1] && typeof td[1] === 'object') {
            value = Object.entries(td[1]).map(([company, amount]) =>
                `${company}: $${Number(amount).toLocaleString()}`);
        } else {
            value = [];
        }
    }
    // Check if we should append both lists together
    else if (typeof LIST_FIELDS !== 'undefined' && LIST_FIELDS.includes(field)) {
        const baseList = Array.isArray(selectedRep[field]) ? selectedRep[field] : [];
        const suppList = (supplemental_data && Array.isArray(supplemental_data[field])) 
                         ? supplemental_data[field] 
                         : [];
        
        // Merge both arrays and remove any duplicates (using Set)
        value = [...new Set([...baseList, ...suppList])];
    } else {
        // Fallback to your previous "Priority" logic for non-list fields
        value = (supplemental_data && supplemental_data[field] !== undefined) 
                ? supplemental_data[field] 
                : selectedRep[field];
    }

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

    const date_regex = /^\d{4}\-\d{2}\-\d{2}$/;
    if (field === "birthDate" && !date_regex.test(value)) {
      console.log("birthDate is not YYYY-MM-DD. Highlighting.");
      noUpdateBtn.disabled = true; //disable gen card until compliant
      need_update.push("birthDate");
      keyDiv.style.background = '#f1ff2f';
    } 
    else if (valueDiv.textContent === '(empty)') { //if empty, highlight.
      console.log(field, " is empty. Highlighting.");
      if (field === "top_donors") {
        if (missingItemWarning.textContent.length === 0) {
          recommend_update.push("top_donors");
        }
        keyDiv.style.background = '#f1ff2f';
      } 
      else if (field === "top_issues") {
        if (missingItemWarning.textContent.length === 0) {
          recommend_update.push("top_issues");
        }
        keyDiv.style.background = '#f1ff2f';
      }
      else if (field === 'education') {
        noUpdateBtn.disabled = true; //disable gen card until compliant
        need_update.push("education");
        keyDiv.style.background = '#f1ff2f';
      }
      else if (field === 'birthplace') {
        noUpdateBtn.disabled = true; //disable gen card until compliant
        need_update.push("birthplace");
        keyDiv.style.background = '#f1ff2f';
      }
      else {
        keyDiv.style.background = '#fccb94';
      }
    }

    
    row.appendChild(keyDiv);
    row.appendChild(valueDiv);
    currentDataDisplay.appendChild(row);
  });

  if (need_update.length > 0) {
    missingItemWarning.textContent = `Please update the following fields: ${need_update.join(', ')}`;
  }
  else if (recommend_update.length > 0) {
    missingItemWarning.textContent = `Consider updating the following fields for a more comprehensive card: ${recommend_update.join(', ')}`;
  }


}

function show4() {
  displayCurrentData();

  showStep(4);
  const currentDataSection = document.getElementById('currentDataSection');

  window.scrollTo(0,0);
  modal.scrollTop = 0;
  currentDataSection.scrollTop = 0;
  step4.scrollTop = 0;
}

// Popup asking whether to regenerate existing top_donors. Resolves true/false.
function askRegenerate(timestamp) {
  return new Promise((resolve) => {
    popup.innerHTML = '';
    let when = timestamp;
    try { when = new Date(timestamp).toLocaleString(); } catch (e) { /* keep raw */ }

    const msg = document.createElement('p');
    msg.textContent = `Top donors were last generated on ${when}. Regenerate?`;
    popup.appendChild(msg);

    const butDiv = document.createElement('div');
    const yesBtn = document.createElement('button');
    const noBtn = document.createElement('button');
    yesBtn.className = 'confirm';
    noBtn.className = 'cancel';
    yesBtn.textContent = 'Regenerate';
    noBtn.textContent = 'Use existing';
    butDiv.appendChild(yesBtn);
    butDiv.appendChild(noBtn);
    popup.appendChild(butDiv);
    popup.className = 'popup show';

    const close = (val) => {
      popup.className = 'popup';
      popup.innerHTML = '';
      resolve(val);
    };
    yesBtn.addEventListener('click', () => close(true));
    noBtn.addEventListener('click', () => close(false));
  });
}

// True only for the current top_donors shape: a 2-element array of [overview, donors],
// where overview is an object carrying generated_at and donors is a {company: amount}
// object. The legacy shape (an array of display strings, or []) returns false so we can
// force regeneration instead of prompting.
function isValidTopDonorsFormat(td) {
  return Array.isArray(td)
    && td.length === 2
    && td[0] && typeof td[0] === 'object' && !Array.isArray(td[0])
    && typeof td[0].generated_at === 'string'
    && td[1] && typeof td[1] === 'object' && !Array.isArray(td[1]);
}

// Store [overview, {top 20}] for selectedRep into the in-memory supplement + persist.
async function persistTopDonors(topDonors) {
  let entry = supplement.find(s => s.name === selectedRep.name);
  if (!entry) {
    entry = { name: selectedRep.name };
    supplement.push(entry);
  }
  entry.top_donors = topDonors;
  await window.electronAPI.saveSupplement(supplement);
}

// Run the FEC top-donors exe for selectedRep, stream output to terminal3, and on
// success store [overview, {top 20}] into the in-memory supplement + persist it.
// Returns { ok: boolean, needsManualEntry?: boolean, message?: string }. When the
// bioguide can't be resolved, needsManualEntry is set so the caller can prompt for a
// candidate code instead of treating it as a hard failure.
async function runTopDonors() {
  showStep(11);
  if (topDonorsHeading) topDonorsHeading.textContent = `Getting top donors for ${selectedRep.name}`;
  terminal3.innerHTML = '';

  const handler = (data) => {
    const p = document.createElement('p');
    p.textContent = data;
    terminal3.appendChild(p);
    terminal3.scrollTop = terminal3.scrollHeight;
  };
  window.electronAPI.onTerminalUpdate(handler);

  try {
    const result = await window.electronAPI.getTopDonors(selectedRep.bioguideID, selectedRep.name);
    window.electronAPI.removeTerminalListener(handler);

    if (!result || !result.success) {
      return {
        ok: false,
        needsManualEntry: !!(result && result.needsManualEntry),
        message: (result && result.message) ? result.message : 'Unknown error fetching top donors.'
      };
    }

    await persistTopDonors(result.top_donors);
    return { ok: true };
  } catch (e) {
    window.electronAPI.removeTerminalListener(handler);
    return { ok: false, message: String(e) };
  }
}

// Show the manual candidate-entry page (step 13). The submit handler (wired once
// below) runs the exe in candidate mode and, on success, continues to the review step.
function showManualCandidateEntry() {
  if (manualCandidateName) manualCandidateName.textContent = selectedRep ? selectedRep.name : '';
  if (manualEntryError) manualEntryError.textContent = '';
  if (manualCandidateInput) manualCandidateInput.value = '';
  if (terminal4) terminal4.innerHTML = '';
  if (manualSpinner) manualSpinner.classList.remove('show');
  showStep(13);
}

// Step 13: fetch top donors from a user-supplied candidate code, then continue
// into the normal review step exactly as the bioguide path does.
manualCandidateSubmitBtn.addEventListener('click', async () => {
  const candidateId = manualCandidateInput.value.trim().toUpperCase();

  manualEntryError.textContent = '';
  if (!/^[HS][0-9A-Z]{8}$/.test(candidateId)) {
    manualEntryError.textContent = 'Candidate ID must be 9 characters: H or S followed by 8 letters/digits (e.g. H8NY01234).';
    return;
  }


  terminal4.innerHTML = '';
  manualSpinner.classList.add('show');
  manualCandidateSubmitBtn.disabled = true;

  const handler = (data) => {
    const p = document.createElement('p');
    p.textContent = data;
    terminal4.appendChild(p);
    terminal4.scrollTop = terminal4.scrollHeight;
  };
  window.electronAPI.onTerminalUpdate(handler);

  try {
    const result = await window.electronAPI.getTopDonorsManual(candidateId);
    window.electronAPI.removeTerminalListener(handler);
    manualSpinner.classList.remove('show');
    manualCandidateSubmitBtn.disabled = false;

    if (!result || !result.success) {
      manualEntryError.textContent = (result && result.message) ? result.message : 'Unknown error fetching top donors.';
      return;
    }

    await persistTopDonors(result.top_donors);
    showTopDonorsReview();
  } catch (e) {
    window.electronAPI.removeTerminalListener(handler);
    manualSpinner.classList.remove('show');
    manualCandidateSubmitBtn.disabled = false;
    manualEntryError.textContent = String(e);
  }
});

// Required review/edit page for top_donors. Renders the top-20 as editable
// company-name rows (amounts read-only) with delete buttons, mirroring step 5.
function showTopDonorsReview() {
  const entry = supplement.find(s => s.name === selectedRep.name);
  const td = entry ? entry.top_donors : null;
  currentTopDonorsOverview = (Array.isArray(td) && td[0] && typeof td[0] === 'object') ? td[0] : {};
  const donors = (Array.isArray(td) && td[1] && typeof td[1] === 'object') ? td[1] : {};

  topDonorsReviewName.textContent = selectedRep.name;
  topDonorsReviewList.innerHTML = '';

  Object.entries(donors).forEach(([company, amount], index) => {
    const row = document.createElement('div');
    row.className = 'data-row';

    const rowBtnAndInput = document.createElement('div');
    rowBtnAndInput.className = 'input-l-button';

    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.textContent = '-';
    deleteBtn.setAttribute('id', 'top_donors_del_' + index);
    deleteBtn.addEventListener('click', () => row.remove());

    const nameInputEl = document.createElement('input');
    nameInputEl.type = 'text';
    nameInputEl.setAttribute('id', 'top_donors_' + index);
    nameInputEl.value = company;
    nameInputEl.setAttribute('data-amount', amount);

    const amountSpan = document.createElement('span');
    amountSpan.className = 'donor-amount';
    amountSpan.textContent = ' $' + Number(amount).toLocaleString();

    rowBtnAndInput.appendChild(deleteBtn);
    rowBtnAndInput.appendChild(nameInputEl);
    rowBtnAndInput.appendChild(amountSpan);
    row.appendChild(rowBtnAndInput);
    topDonorsReviewList.appendChild(row);
  });

  showStep(12);
}

// Confirm the reviewed top donors: rebuild [overview, {company: amount}] from the
// (possibly edited) rows, persist, and only then proceed to the full data display.
topDonorsConfirmBtn.addEventListener('click', async () => {
  const newDonors = {};
  Array.from(topDonorsReviewList.children).forEach(row => {
    const input = row.children[0].children[1]; // input-l-button -> [delBtn, input, amountSpan]
    const company = input.value.trim();
    const amount = parseFloat(input.getAttribute('data-amount'));
    if (company && !isNaN(amount)) {
      newDonors[company] = (newDonors[company] || 0) + amount; // merge any renamed-into-each-other dupes
    }
  });

  let entry = supplement.find(s => s.name === selectedRep.name);
  if (!entry) {
    entry = { name: selectedRep.name };
    supplement.push(entry);
  }
  entry.top_donors = [currentTopDonorsOverview, newDonors];
  await window.electronAPI.saveSupplement(supplement);

  show4();
});

function displayFieldData(selectedField, displayValue) {
  //displayValue is the array or item to show
  const currentFieldDisplay = document.getElementById('currentFieldDisplay');
  const inputSection = document.getElementById('inputRButton');
  currentFieldDisplay.innerHTML = '';
  const isListField = LIST_FIELDS.includes(selectedField);
  //show the info depending on the selectedField
  if (selectedField == "birthDate") {
    valueLabel.textContent = 'Enter new birth date (YYYY-MM-DD):';
  }
  else if (isListField) {
    valueLabel.textContent = "Please enter a single bullet point at a time.";
  }
  else {
    valueLabel.textContent = 'Enter new value:';
  }
  
  // Display the current data in upper section for step 5
  if (displayValue === undefined || displayValue === null || displayValue === '') {
    //nothing to edit, just show the Add button
      //currentValue.textContent = '(empty)';
  //if it's an array to display, show with delete/edit capability
  } else if (Array.isArray(displayValue)) {
    if (displayValue.length !== 0) { 
      displayValue.forEach((item, index) => {
        const row = document.createElement('div');
        row.className = 'data-row';
        
        const rowBtnAndInput = document.createElement('div');
        rowBtnAndInput.className = 'input-l-button';

        const valueDiv = document.createElement('input');
        valueDiv.setAttribute('type', 'text');
        valueDiv.setAttribute('id', selectedField + '_' + index);
        valueDiv.setAttribute('placeholder', item);
        valueDiv.value = item || "";

        const deleteBtn = document.createElement('button');
        deleteBtn.type = 'button';
        deleteBtn.textContent =  '-';
        deleteBtn.setAttribute('id', selectedField + '_del_' + index);
        
        deleteBtn.addEventListener('click', function() {
        // This removes the specific row from the UI
        row.remove();

        console.log("Deleted data: ", item);
        const newKey = selectedField + "_mods";
        
        });

        rowBtnAndInput.appendChild(deleteBtn);
        rowBtnAndInput.appendChild(valueDiv);
        row.appendChild(rowBtnAndInput);
        currentFieldDisplay.appendChild(row);
      });
    }
  //otherwise just show the item. do not make input box.
  } else {
    const row = document.createElement('div');
    row.className = 'data-row';
    const item = displayValue;
    //do not make input, make paragraph
    const valueDiv = document.createElement('p');
    valueDiv.setAttribute('id', selectedField);
    valueDiv.textContent = item || "";


    row.appendChild(valueDiv);
    currentFieldDisplay.appendChild(row);
  }


  //now if the field is a list field, let them edit by appending multiple.
  //otherwise just let them append, no + button
  if (isListField) {
    const existingAddBtn = document.getElementById('addFieldBtn');
    if (existingAddBtn) {  //remove the current + button to avoid duplicates
      existingAddBtn.remove();
    }
    console.log("Adding + button for input");
    const addFieldBtn = document.createElement('button');
    addFieldBtn.type = 'button';
    addFieldBtn.textContent =  '+';
    addFieldBtn.setAttribute('id', 'addFieldBtn');

    inputSection.appendChild(addFieldBtn);

    //if it's a list, then we have the add field button. set the event listener:
    addFieldBtn.addEventListener('click', async () => {
      let existingEntry = supplement.find(s => s.name === selectedRep.name);

      let newValue = valueInput.value.trim();

      if (!newValue) {
        showStatus('Please enter a value', false);
        return;
      }

      //add, update the visual
      if (existingEntry) {
        if (isListField) {
          if (!existingEntry[selectedField]) {
            existingEntry[selectedField] = [];
          }
          existingEntry[selectedField].push(newValue);
        } else {
          existingEntry[selectedField] = newValue;
        }
        newValue = "";
        valueInput.value = "";
      } else {
        const newEntry = { name: selectedRep.name };
        if (isListField) {
          newEntry[selectedField] = [newValue];
        } else {
          newEntry[selectedField] = newValue;
        }
        supplement.push(newEntry);
        console.log("Added to supplement: ", newEntry);
        newValue = "";
        valueInput.value = "";

      }

      displayValue = updateDisplayValue();
      displayFieldData(selectedField, displayValue);

    });
    
  } else {
    //also remove the + button if it exists
    const existingAddBtn = document.getElementById('addFieldBtn');
    if (existingAddBtn) {
      existingAddBtn.remove();
    }
    valueInput.setAttribute('placeholder', "New value");
  }
}

function updateDisplayValue() {
  let supplemental_data = supplement.find(s => s.name === selectedRep.name);
  let displayValue;
  if (typeof LIST_FIELDS !== 'undefined' && LIST_FIELDS.includes(selectedField)) {
      const baseList = Array.isArray(selectedRep[selectedField]) ? selectedRep[selectedField] : [];
      const suppList = (supplemental_data && Array.isArray(supplemental_data[selectedField])) 
                        ? supplemental_data[selectedField] 
                        : [];
      
      // Merge both arrays and remove any duplicates (using Set)
      displayValue = [...new Set([...baseList, ...suppList])];
  } else {
      // Fallback to your previous "Priority" logic for non-list fields
      displayValue = (supplemental_data && supplemental_data[selectedField] !== undefined) 
              ? supplemental_data[selectedField] 
              : selectedRep[selectedField];
  }
  return displayValue;
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

async function checkBioguideExists() {
  /**
   * If sessionData/bioguide_data doesn't exist, disable genCardsBtn
   */
    // 'electronAPI' matches what we defined in the preload script
    const bioguide_exists = await window.electronAPI.checkBioguideExists();
    if (bioguide_exists) {
      genCardsBtn.disabled = false;
      noConBtn.disabled = false;
    } else {
      genCardsBtn.disabled = true;
      noConBtn.disabled = true;
    }
    //console.log("The session data path is:", path);
    return path;
}

async function disableButtons() {
  const bioguide_exists = await window.electronAPI.checkBioguideExists();
  const congressmen_exists = await window.electronAPI.checkCongressmenExists();
  const vote_exists = await window.electronAPI.checkVoteExists();

  if (bioguide_exists && congressmen_exists) {
    genCardsBtn.disabled = false;
    if (vote_exists) {
      noConBtn.disabled = false;
    } else {
      noConBtn.disabled = true;
    }
  } else {
    genCardsBtn.disabled = true;
    noConBtn.disabled = true;
  }

  if (vote_exists) {
    noVoteBtn.disabled = false;
  } else {
    noVoteBtn.disabled = true;
  }
}

/////////////////////////////////////////////
//checkBioguideExists();
disableButtons();

movedBioguideBtn.addEventListener('click', async () => {
  setLoading(true);
  updated_data = true;
  movedBioguideBtn.disabled = true;
  const result = await window.electronAPI.importBioguideData();
  if (result.success) {
    setLoading(false);
    console.log("bioguide refreshed.");
    genCardsBtn.disabled = false;
    noConBtn.disabled = false;
    movedBioguideBtn.disabled = false;

    showStep(2);
  } else {
    showStatus("Failed to move bioguide.", false);
    genCardsBtn.disabled = false;
    noConBtn.disabled = false;
    movedBioguideBtn.disabled = false;
    setLoading(false);
  }
  
});



//Step 1: Ask to update congressmen data
yesConBtn.addEventListener('click', async () => {
  updated_data = true;
  yesConBtn.disabled = true;
  noConBtn.disabled = true;
  setLoading(true);

  terminal1.innerHTML = "Running API pull for congressmen.json";
  //init the handler and terminal interaction
  const handler1 = (data) => {
        console.log("Data received:", data); 
        console.log("Data type:", typeof data);
        const message = (typeof data === 'string') ? data : JSON.stringify(data);
        const p = document.createElement('p');
        p.textContent = message;
        terminal1.appendChild(p);
        terminal1.scrollTop = terminal1.scrollHeight;
  };

  window.electronAPI.onTerminalUpdate(handler1);
  console.log("Listener is active, now triggering Python...");
  const result = await window.electronAPI.genRepsJSON();
  window.electronAPI.removeTerminalListener(handler1);
  // Display Python output

  if (result.success) {
    console.log("success");
    setLoading(false);
    yesConBtn.disabled = false;
    noConBtn.disabled = false;
    showStep(10); //go to bioguide requirement
  } else {
    const e = result.message;
    const p2 = document.createElement('p');
    p2.style.whiteSpace = "pre-line";
    p2.textContent = "Error making congressmen.json: " + e + "\n\nPlease copy this error message, send to Madison, and close the window.";
    terminal1.appendChild(p2);
    showStatus('Error making congressmen.json: ' + e , false);
    yesConBtn.disabled = true;
    noConBtn.disabled = true;
    setLoading(false);

  }

});
noConBtn.addEventListener('click', () => {
  console.log("Not updating congressmen.json");
  showStep(2);
});


//Step 2: Ask to update voting data
//in both, need to re-merge data.
yesVoteBtn.addEventListener('click', async () => {
  yesVoteBtn.disabled = true;
  noVoteBtn.disabled = true;
  setLoading(true);
  terminal2.innerHTML = "Running API pull for voting_record.json";

  //init the handler and terminal interaction
  const handler2 = (data) => {
        console.log("Data received:", data); 
        console.log("Data type:", typeof data);
        const message = (typeof data === 'string') ? data : JSON.stringify(data);
        const p = document.createElement('p');
        p.textContent = message;
        terminal2.appendChild(p);
        terminal2.scrollTop = terminal2.scrollHeight;
  };

  window.electronAPI.onTerminalUpdate(handler2);
  const result_vote = await window.electronAPI.genVotingRecordJSON();

  //success generating vote record
  if (result_vote.success) {
    console.log("Success in genVotingRecordJSON");
    const result_combine = await window.electronAPI.combineData();

    //success combining data too
    if (result_combine.success) {
      //showStatus('Success in combineData. Loading data...', true);
      const loaded = await loadData();
      setLoading(false);
      yesVoteBtn.disabled = false;
      noVoteBtn.disabled = false;
      if (loaded){
        showStep(3);
      }
    }
    //yes vote record, fail combine data
    else {
      const e = result_combine.message;
      const p2 = document.createElement('p');
      p2.style.whiteSpace = "pre-line";
      p2.textContent = "Error combining data: " + e + "\n\nPlease copy this error message, send to Madison, and close the window.";
      terminal2.appendChild(p2);
      showStatus('Error combining data: ' + e , false);
      setLoading(false);

    }
  //fail vote record
  } else {
    const e = result_vote.message;
    const p2 = document.createElement('p');
    p2.style.whiteSpace = "pre-line";
    p2.textContent = "Error generating voting_record.json: " + e + "\n\nPlease copy this error message, send to Madison, and close the window.";
    terminal2.appendChild(p2);
    showStatus('Error generating voting_record.json: ' + e , false);
    setLoading(false);
  }

  window.electronAPI.removeTerminalListener(handler2);

});

noVoteBtn.addEventListener('click', async () => {
  console.log("Not updating voting_record.json");

  if (updated_data) {
    terminal2.innerHTML = "Running merge on data sets since congressmen data was updated";
    updated_data = false;
    setLoading(true);
    noVoteBtn.disabled = true;
    yesVoteBtn.disabled = true;

    //init the handler and terminal interaction
    const handler3 = (data) => {
          console.log("Data received:", data); 
          console.log("Data type:", typeof data);
          const message = (typeof data === 'string') ? data : JSON.stringify(data);
          const p = document.createElement('p');
          p.textContent = message;
          terminal2.appendChild(p);
          terminal2.scrollTop = terminal2.scrollHeight;
    };
    window.electronAPI.onTerminalUpdate(handler3);

    const result_combine = await window.electronAPI.combineData();
    window.electronAPI.removeTerminalListener(handler3);

    if (result_combine.success) {
      console.log('Success in combineData.')
      const loaded = await loadData();
      yesVoteBtn.disabled = false;
      noVoteBtn.disabled = false;
      setLoading(false);
      if (loaded){
        showStep(3);
      }
    }
    else {
      const e = result_vote.message;
      const p2 = document.createElement('p');
      p2.style.whiteSpace = "pre-line";
      p2.textContent = "Error loading/combining data: " + e + "\n\nPlease copy this error message, send to Madison, and close the window.";
      terminal2.appendChild(p2);
      showStatus('Error loading/combining data: ' + e , false);
      setLoading(false);
    }
  }
  else {
    console.log('Success in combineData.')
    const loaded = await loadData();
    setLoading(false);
    if (loaded){
      showStep(3);
    }
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

nameSubmitBtn.addEventListener('click', async () => {
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

  // Top donors: auto-generate if missing OR stored in the old/legacy format; only when
  // a correctly-formatted entry already exists do we show its date and ask the operator
  // whether to regenerate.
  const supEntry = supplement.find(s => s.name === selectedRep.name);
  const existing = supEntry ? supEntry.top_donors : null;

  let doRun;
  if (isValidTopDonorsFormat(existing)) {
    doRun = await askRegenerate(existing[0].generated_at);
  } else {
    // Missing, empty, or legacy (array-of-strings) format -> force regeneration.
    doRun = true;
  }

  if (doRun) {
    const res = await runTopDonors();
    if (!res.ok) {
      if (res.needsManualEntry) {
        // Bioguide couldn't be resolved: let the operator supply a candidate code.
        // The manual submit handler continues into showTopDonorsReview() on success.
        showManualCandidateEntry();
        return;
      }
      // No top donors to review; surface the error and go straight to the data.
      showStatus('Could not fetch top donors: ' + res.message, false);
      show4();
      return;
    }
  }

  // Force the operator to review the top donors before seeing the full data.
  showTopDonorsReview();
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
    
  document.getElementById('selectedName2').textContent = selectedRep.name;
  document.getElementById('selectedField').textContent = selectedField;
  

  // Calculate the combined value specifically for this display block
  displayValue = updateDisplayValue();

  console.log("Using data ", displayValue);

  //this is where we used to prep the data to show for step 5
  displayFieldData(selectedField, displayValue);
  
  showStep(5);
});

//step 4->5, generate card
noUpdateBtn.addEventListener('click', async () => {
  let supplemental_data = supplement.find(s => s.name === selectedRep.name);
  if (!supplemental_data || supplemental_data['top_issues'] === undefined || supplemental_data['top_issues'].length === 0) {
    showPopup("The 'Top Issues' field is empty. Are you sure you want to proceed without updating it?");
    return;
  } else if(!supplemental_data || supplemental_data['top_donors'] === undefined || supplemental_data['top_donors'].length === 0) {
    showPopup("The 'Top Donors' field is empty. Are you sure you want to proceed without updating it?");
    return;
  }
  else {
    showStep(7); //go to photoshop loading page
    setLoading(true);
    console.log("running gen card");
    console.log("Sending to main.js: ", selectedRep.name);
    //showStatus('Generating card. May take 1-2 minutes if Photoshop not open yet.', true);

    const result = await window.electronAPI.genCard(selectedRep.name);

    if (result.success) {
      console.log("done with gen card");
      setLoading(false);
      showStep(8);
    }
    else {
      //showStatus('Error generating card: ' + result.message, false);
      errorMessage.textContent = result.message;
      showStep(9);
      setLoading(false);
    }
    
  }
});

backToNameBtn.addEventListener('click', () => showStep(3));



// Step 5: Save the updated field
saveBtn.addEventListener('click', async () => {

  const isListField = LIST_FIELDS.includes(selectedField);
  let existingEntry = supplement.find(s => s.name === selectedRep.name);
  if (isListField) {
    let field_data = [];
    const rows = currentFieldDisplay.children;

    if (rows.length === 0) {
      if (existingEntry) {
        existingEntry[selectedField] = [];
      }
    }
    else {
      Array.from(rows).forEach(row => {
        const newValue = row.children[0].children[1].value; //[0] is input-l-button, then [0] is button, [1] is input
        if (newValue) {
          field_data.push(newValue);
        }


        if (existingEntry) {
          existingEntry[selectedField] = field_data;
        }
        else {
          const newEntry = { name: selectedRep.name };
          newEntry[selectedField] = field_data;
          console.log("Saving to supplement: ", newEntry);
          supplement.push(newEntry);
        }
      });
    }

    //then if they left anything in the value input, add that as well
    const inputValue = valueInput.value.trim();
    if (inputValue) {
      if (existingEntry) {
        if (!existingEntry[selectedField]) {
          existingEntry[selectedField] = [];
        }
        existingEntry[selectedField].push(inputValue);
      }
      else {
        const newEntry = { name: selectedRep.name };
        newEntry[selectedField] = [inputValue];
        console.log("Saving to supplement: ", newEntry);
        supplement.push(newEntry);
      }
    }

  } else {
    //if not listfield, then only one row. append to supplemental
    if (selectedField === "birthDate") {
      const date_regex = /^\d{4}\-\d{2}\-\d{2}$/;
      const newValue = valueInput.value.trim();
      if (!date_regex.test(newValue)) {
        showStatus('Birth date must be in YYYY-MM-DD format', false);
        return;
      }
    }
    if (existingEntry) {
      const newValue = valueInput.value.trim();
      existingEntry[selectedField] = newValue;
    } else { //if single entry, value is just what's in valueInput
      const newValue = valueInput.value.trim();
      const newEntry = { name: selectedRep.name };
      newEntry[selectedField] = newValue;
      console.log("Saving to supplement: ", newEntry);
      supplement.push(newEntry);
    }

  }

  
  // Save to file
  const result = await window.electronAPI.saveSupplement(supplement);
  
  if (result.success) {
    valueInput.value = '';
    showStep(6);

    //remove from warning if updated
    console.log("Should remove ", selectedField, " from need_update and recommend_update if present");
    if (need_update.includes(selectedField)) {
      need_update = need_update.filter(f => f !== selectedField);
      console.log("Need update is now: ", need_update);
    }
    else if (recommend_update.includes(selectedField)) {
      recommend_update = recommend_update.filter(f => f !== selectedField);
      console.log("Recommend update is now: ", recommend_update);
    }

    if (need_update.length > 0) {
      missingItemWarning2.textContent = `***MUST UPDATE: ${need_update.join(', ')}`;
      genCardBtn.disabled = true; //disable gen card until compliant
    }
    else if (recommend_update.length > 0) {
      console.log("There are still recommend updates: ", recommend_update);
      missingItemWarning2.textContent = `WARNING: Recommended updates: ${recommend_update.join(', ')}`;
      genCardBtn.disabled = false;
    }
    else {
      genCardBtn.disabled = false;
      missingItemWarning2.textContent = "";

    }
  } else {
    showStatus('Error saving data: ' + result.message + '. Please screenshot, send to Madison, and close.', false, 20000);
  }

});

backToConfirmBtn.addEventListener('click', () => showStep(3));

// Step 6: Success updating congressman, gen card or update another field
genCardBtn.addEventListener('click', async () => {
  //check if top_issues or top_donors is empty, if so, show popup warning before gen card
  if(recommend_update.length === 1) {
    showPopup(`Field ${recommend_update[0]} is empty. Are you sure you want to proceed without updating it?`);
  } else if(recommend_update.length > 1) {
    showPopup(`Fields ${recommend_update.join(', ')} are empty. Are you sure you want to proceed without updating them?`);
  } else {
    setLoading(true);
    console.log("running gen card");
    console.log("Sending to main.js: ", selectedRep.name);
    showStatus('Generating card. May take 1-2 minutes if Photoshop not open yet.', true);

    const result = await window.electronAPI.genCard(selectedRep.name);

    if (result.success) {
      console.log("done with gen card");
      setLoading(false);
      showStep(8);
    }
    else {
      //showStatus('Error generating card: ' + result.message, false);
      errorMessage.textContent = result.message;
      showStep(9);
      setLoading(false);
    }
  }

});

addAnotherBtn.addEventListener('click', () => {
  //openModal();
  loadData();
  show4();
});

//Step 7: Gen another card or quit?
genNewCardBtn.addEventListener('click', () => {
  showStep(3);
});
quitBtn.addEventListener('click', closeModal);



//updateData (step 0): do not load data, will need to run steps 1 and 2 and combine data
updateDataBtn.addEventListener('click', async () => {
  /*setLoading(true);
  const loaded = await loadData(); //madison
  setLoading(false);
  
  if (loaded) {
    openModal();
    showStep(1);
  }*/
  openModal();
  showStep(1);
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