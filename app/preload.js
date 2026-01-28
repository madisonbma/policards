const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  genCard: () => ipcRenderer.invoke('gen-card'),
  openUpdateWindow: () => ipcRenderer.invoke('open-update-window'),
  refetchData: () => ipcRenderer.invoke('refetch-data'),
  genSupplement: () => ipcRenderer.invoke('gen-supplement'),
  loadCongressmenData: () => ipcRenderer.invoke('load-congressmen-data'),
  saveSupplement: (data) => ipcRenderer.invoke('save-supplement', data)
});