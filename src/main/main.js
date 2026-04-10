const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const db = require('./database');
const claude = require('./claude');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 960,
    height: 700,
    minWidth: 760,
    minHeight: 500,
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#FFFFFF',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:3000');
  } else {
    mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
  }
}

app.whenReady().then(() => {
  db.initDatabase();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// --- IPC Handlers ---

// Notes
ipcMain.handle('note:create', async (_, content, tags) => {
  const noteId = db.createNote(content);

  // Add user-specified tags (from # syntax)
  if (tags && tags.length > 0) {
    db.setNoteTags(noteId, tags);
  }

  // Background: generate summary and AI tags
  claude.generateSummaryAndTags(content).then((result) => {
    if (result) {
      db.updateNoteSummary(noteId, result.summary || '');
      if (result.tags && result.tags.length > 0) {
        const existingTags = tags || [];
        const allTags = [...new Set([...existingTags, ...result.tags])];
        db.setNoteTags(noteId, allTags);
      }
      // Notify renderer that note was updated
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('note:updated', { noteId });
      }
    }
  }).catch((err) => {
    console.error('Failed to generate summary:', err.message);
  });

  return noteId;
});

ipcMain.handle('note:getAll', () => {
  return db.getAllNotes();
});

ipcMain.handle('note:getByTag', (_, tag) => {
  return db.getNotesByTag(tag);
});

ipcMain.handle('note:delete', (_, id) => {
  db.deleteNote(id);
  return true;
});

ipcMain.handle('note:search', (_, query) => {
  try {
    return db.searchNotes(query);
  } catch {
    return [];
  }
});

// Tags
ipcMain.handle('tag:getAll', () => {
  return db.getAllTags();
});

// Settings
ipcMain.handle('setting:get', (_, key) => {
  return db.getSetting(key);
});

ipcMain.handle('setting:set', (_, key, value) => {
  db.setSetting(key, value);
  return true;
});

// Ask
ipcMain.handle('ask:question', async (_, question) => {
  // Search local notes first
  let relevantNotes = [];
  try {
    relevantNotes = db.searchNotes(question);
  } catch {
    relevantNotes = db.getAllNotes().slice(0, 10);
  }
  return claude.askQuestion(question, relevantNotes);
});
