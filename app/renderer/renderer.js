const genCardBtn = document.getElementById('genCardBtn');
const updateDataBtn = document.getElementById('updateDataBtn');
const status_doc = document.getElementById('status');
const spinner = document.getElementById('spinner');

//STATUS
function showStatus(message, isSuccess) {
  status_doc.textContent = message;
  status_doc.className = 'status show ' + (isSuccess ? 'success' : 'error');
  setTimeout(() => {
    status_doc.className = 'status';
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


//EVENT LISTENERS
genCardBtn.addEventListener('click', async () => {
  await window.electronAPI.openGenCard();
});

updateDataBtn.addEventListener('click', async () => {
  await window.electronAPI.openUpdateWindow();
});