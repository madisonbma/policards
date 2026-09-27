const genCardBtn = document.getElementById('genCardBtn');
const customFECBtn = document.getElementById('customFECBtn');
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
  customFECBtn.disabled = isLoading;
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
    customFECBtn.disabled = false;
    console.log("Enabled genCardBtn");
  } else {
    genCardBtn.disabled = true;
    customFECBtn.disabled = true;
    console.log("Disabled genCardBtn and customFECBtn");
  }
}

check_config();

//EVENT LISTENERS
genCardBtn.addEventListener('click', async () => {
  await window.electronAPI.openGenCard();
});

customFECBtn.addEventListener('click', async () => {
  await window.electronAPI.openCustomFEC();
})


editConfigBtn.addEventListener('click', async () => {
  console.log("Clicked edit config btn");
  await window.electronAPI.openConfigWindow();
});

window.electronAPI.onConfigClosed(() => {
  check_config();
});