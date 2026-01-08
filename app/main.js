const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { exec } = require('child_process');
const fs = require('fs');

let mainWindow;
let updateWindow;

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 600,
    height: 400,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  mainWindow.loadFile('renderer/index.html');
}

function createUpdateWindow() {
  updateWindow = new BrowserWindow({
    width: 500,
    height: 300,
    parent: mainWindow,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  updateWindow.loadFile('renderer/update.html');

  updateWindow.on('closed', () => {
    updateWindow = null;
  });
}

app.whenReady().then(() => {
  createMainWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Handle Gen Card button
ipcMain.handle('gen-card', async () => {
  try {
    const pythonScript = path.join(__dirname, '../src/gen_temp_for_javascript.py');
    const jsxScript = path.join(__dirname, '../src/fill_social_template.jsx');
    const tempFile = path.join(__dirname, '../src/generated_outputs/temp.txt');

    // Step 1: Run Python script
    await new Promise((resolve, reject) => {
      exec(`python "${pythonScript}"`, (error, stdout, stderr) => {
        if (error) {
          reject(`Python Error: ${error.message}`);
          return;
        }
        if (stderr) {
          console.log('Python stderr:', stderr);
        }
        console.log('Python stdout:', stdout);
        resolve();
      });
    });

    // Step 2: Check if temp.txt was created
    if (!fs.existsSync(tempFile)) {
      throw new Error('temp.txt was not generated');
    }

    // Step 3: Run Photoshop script using ExtendScript
    await new Promise((resolve, reject) => {
      const isWindows = process.platform === 'win32';
      const isMac = process.platform === 'darwin';

      let command;
      if (isWindows) {
        // Windows: Use Photoshop's executable with the script
        command = `"C:\\Program Files\\Adobe\\Adobe Photoshop 2024\\Photoshop.exe" "${jsxScript}"`;
      } else if (isMac) {
        // Mac: Use osascript to tell Photoshop to run the script
        command = `osascript -e 'tell application "Adobe Photoshop 2024" to do javascript file("${jsxScript}")'`;
      } else {
        reject('Unsupported operating system');
        return;
      }

      exec(command, (error, stdout, stderr) => {
        if (error) {
          reject(`Photoshop Error: ${error.message}`);
          return;
        }
        if (stderr) {
          console.log('Photoshop stderr:', stderr);
        }
        console.log('Photoshop stdout:', stdout);
        resolve();
      });
    });

    return { success: true, message: 'Card generated successfully!' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});

// Handle Update Data button - opens new window
ipcMain.handle('open-update-window', () => {
  if (updateWindow) {
    updateWindow.focus();
  } else {
    createUpdateWindow();
  }
});

// Handle Refetch Data button
ipcMain.handle('refetch-data', async () => {
  try {
    const pythonScript = path.join(__dirname, '../src/refetch_data.py');

    await new Promise((resolve, reject) => {
      exec(`python "${pythonScript}"`, (error, stdout, stderr) => {
        if (error) {
          reject(`Error: ${error.message}`);
          return;
        }
        if (stderr) {
          console.log('stderr:', stderr);
        }
        console.log('stdout:', stdout);
        resolve();
      });
    });

    return { success: true, message: 'Data refetched successfully!' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});

// Handle Manually Insert New Data button
ipcMain.handle('gen-supplement', async () => {
  try {
    const pythonScript = path.join(__dirname, '../src/gen_supplement.py');

    await new Promise((resolve, reject) => {
      exec(`python "${pythonScript}"`, (error, stdout, stderr) => {
        if (error) {
          reject(`Error: ${error.message}`);
          return;
        }
        if (stderr) {
          console.log('stderr:', stderr);
        }
        console.log('stdout:', stdout);
        resolve();
      });
    });

    return { success: true, message: 'Data inserted successfully!' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});