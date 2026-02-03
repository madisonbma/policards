const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  openGenCard: () => ipcRenderer.invoke('open-gen-card'),
  genRepsJSON: () => ipcRenderer.invoke('gen-reps-json'),
  genVotingRecordJSON: () => ipcRenderer.invoke('gen-voting-record-json'),
  genCard: () => ipcRenderer.invoke('gen-card'),
  openUpdateWindow: () => ipcRenderer.invoke('open-update-window'),
  loadCongressmenData: () => ipcRenderer.invoke('load-congressmen-data'),
  combineData: () => ipcRenderer.invoke('combine-data'),
  saveSupplement: (data) => ipcRenderer.invoke('save-supplement', data)
});