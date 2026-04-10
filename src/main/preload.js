const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  // Notes
  createNote: (content, tags) => ipcRenderer.invoke('note:create', content, tags),
  getAllNotes: () => ipcRenderer.invoke('note:getAll'),
  getNotesByTag: (tag) => ipcRenderer.invoke('note:getByTag', tag),
  deleteNote: (id) => ipcRenderer.invoke('note:delete', id),
  searchNotes: (query) => ipcRenderer.invoke('note:search', query),

  // Tags
  getAllTags: () => ipcRenderer.invoke('tag:getAll'),

  // Settings
  getSetting: (key) => ipcRenderer.invoke('setting:get', key),
  setSetting: (key, value) => ipcRenderer.invoke('setting:set', key, value),

  // Ask
  askQuestion: (question) => ipcRenderer.invoke('ask:question', question),

  // Events
  onNoteUpdated: (callback) => {
    ipcRenderer.on('note:updated', (_, data) => callback(data));
    return () => ipcRenderer.removeAllListeners('note:updated');
  },
});
