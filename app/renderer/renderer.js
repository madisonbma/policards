const genCardBtn = document.getElementById('genCardBtn');
const editConfigBtn = document.getElementById('editConfigBtn');
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
async function check_config() {
  const config_clean = await window.electronAPI.configIsClean();
  if (config_clean) {
    genCardBtn.disabled = false;
    console.log("Enabled genCardBtn");
  } else {
    genCardBtn.disabled = true;
    console.log("Disabled genCardBtn");
  }
}

check_config();

//EVENT LISTENERS
genCardBtn.addEventListener('click', async () => {
  await window.electronAPI.openGenCard();
});


editConfigBtn.addEventListener('click', async () => {
  console.log("Clicked edit config btn");
  await window.electronAPI.openConfigWindow();
});

window.electronAPI.onConfigClosed(() => {
  check_config();
});