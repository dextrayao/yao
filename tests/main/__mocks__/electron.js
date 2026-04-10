// Mock electron for unit tests
module.exports = {
  app: {
    getPath: (name) => '/tmp/test-noted',
    whenReady: () => Promise.resolve(),
    on: () => {},
    quit: () => {},
  },
  BrowserWindow: class BrowserWindow {
    constructor() {}
    loadFile() {}
    loadURL() {}
    static getAllWindows() { return []; }
  },
  ipcMain: {
    handle: () => {},
    on: () => {},
  },
  ipcRenderer: {
    invoke: () => Promise.resolve(),
    on: () => {},
    removeAllListeners: () => {},
  },
  contextBridge: {
    exposeInMainWorld: () => {},
  },
};
