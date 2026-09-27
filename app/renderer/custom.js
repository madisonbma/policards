
const terminal4 = document.getElementById('terminalOutput4');
const manualResult = document.getElementById('manualResult')


manualCandidateSubmitBtn.addEventListener('click', async () => {
  const candidateId = manualCandidateInput.value.trim().toUpperCase();
  manualResult.textContent = "";

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
    else {
        //result = [totals_dict, contribution_data]
        var final_text = "";
        final_text += JSON.stringify(result.top_donors[0], null, 2);
        final_text += JSON.stringify(result.top_donors[1], null, 2);
        manualResult.textContent = final_text;
        /*const final_text_1 = Object.entries(result.top_donors[0])
            .map(([key, value]) => `${key}: ${value}`)
            .join('\n'); // Separates each pair with a newline

        const final_text_2 = Object.entries(result.top_donors[1])
            .map(([key, value]) => `${key}: ${value}`)
            .join('\n'); // Separates each pair with a newline

        manualResult.textContent = final_text_1 + "\n" + final_text_2;
        */

    }

  } catch (e) {
    window.electronAPI.removeTerminalListener(handler);
    manualSpinner.classList.remove('show');
    manualCandidateSubmitBtn.disabled = false;
    manualEntryError.textContent = String(e);
  }
});

