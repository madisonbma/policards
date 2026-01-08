const genCardBtn = document.getElementById('genCardBtn');
const updateDataBtn = document.getElementById('updateDataBtn');
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
  genCardBtn.disabled = isLoading;
  updateDataBtn.disabled = isLoading;
  if (isLoading) {
    spinner.classList.add('show');
  } else {
    spinner.classList.remove('show');
  }
}

genCardBtn.addEventListener('click', async () => {
  setLoading(true);
  status.className = 'status';
  
  const result = await window.electronAPI.genCard();
  
  setLoading(false);
  showStatus(result.message, result.success);
});

updateDataBtn.addEventListener('click', async () => {
  await window.electronAPI.openUpdateWindow();
});