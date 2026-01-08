const refetchBtn = document.getElementById('refetchBtn');
const manualInsertBtn = document.getElementById('manualInsertBtn');
const status = document.getElementById('status');
const spinner = document.getElementById('spinner');

function showStatus(message, isSuccess) {
  status.textContent = message;
  status.className = 'status show ' + (isSuccess ? 'success' : 'error');
  setTimeout(() => {
    status.className = 'status';
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

refetchBtn.addEventListener('click', async () => {
  setLoading(true);
  status.className = 'status';
  
  const result = await window.electronAPI.refetchData();
  
  setLoading(false);
  showStatus(result.message, result.success);
});

manualInsertBtn.addEventListener('click', async () => {
  setLoading(true);
  status.className = 'status';
  
  const result = await window.electronAPI.genSupplement();
  
  setLoading(false);
  showStatus(result.message, result.success);
});