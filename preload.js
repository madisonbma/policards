const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  openGenCard: () => ipcRenderer.invoke('open-gen-card'),
  genRepsJSON: () => ipcRenderer.invoke('gen-reps-json'),
  genVotingRecordJSON: () => ipcRenderer.invoke('gen-voting-record-json'),
  onTerminalUpdate: (callback) => ipcRenderer.on('terminal-update', (event, data) => callback(data)),
  removeTerminalListener: (callback) => ipcRenderer.removeAllListeners('terminal-update', callback),
  genCard: (name, party) => ipcRenderer.invoke('gen-card', name, party),
  genManualCard: (name, party) => ipcRenderer.invoke('gen-manual-card', name, party),
  getTopDonors: (bioguideId, name) => ipcRenderer.invoke('get-top-donors', bioguideId, name),
  getTopDonorsManual: (candidateId) => ipcRenderer.invoke('get-top-donors-manual', candidateId),
  openUpdateWindow: () => ipcRenderer.invoke('open-update-window'),
  loadCongressmenData: () => ipcRenderer.invoke('load-congressmen-data'),
  loadConfigData: () => ipcRenderer.invoke('load-config-data'),
  combineData: () => ipcRenderer.invoke('combine-data'),
  saveSupplement: (data) => ipcRenderer.invoke('save-supplement', data),
  saveConfigData: (data) => ipcRenderer.invoke('save-config-data', data),
  openConfigWindow: () => ipcRenderer.invoke('open-config-window'),
  importBioguideData: () => ipcRenderer.invoke('import-bioguide-data'),
  checkBioguideExists: () => ipcRenderer.invoke('check-bioguide-exists'),
  checkCongressmenExists: () => ipcRenderer.invoke('check-congressmen-exists'),
  checkVoteExists: () => ipcRenderer.invoke('check-vote-exists'),
  configIsClean: () => ipcRenderer.invoke('config-is-clean'),
  checkPathExists: (path) => ipcRenderer.invoke('check-path-exists', path),
  onConfigClosed: (callback) => ipcRenderer.on('config-closed', callback)

});