const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { exec } = require('child_process');
const fs = require('fs');
const fsPromises = fs.promises; 

let mainWindow;
let updateWindow;
let genWindow;

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 500,
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
    width: 800,
    height: 500,
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

function createGenWindow() {
  genWindow = new BrowserWindow({
    width: 800,
    height: 500,
    parent: mainWindow,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  genWindow.loadFile('renderer/gencard.html');

  genWindow.on('closed', () => {
    genWindow = null;
  });
}


async function deleteFile(filePath) {
  try {
    await fsPromises.unlink(filePath);
    console.log(`File ${filePath} deleted successfully`);
  } catch (err) {
    if (err.code === 'ENOENT') {
      console.log('File does not exist');
    } else {
      console.error('Error deleting file:', err);
    }
  }
}


const { spawn } = require('child_process');

function runPythonScript(scriptPath, args = []) {
  return new Promise((resolve, reject) => {
    // Note: Use 'python' or 'python3' depending on your system
    const pyProcess = spawn('python', [scriptPath, ...args]);

    pyProcess.stdout.on('data', (data) => console.log(`Python: ${data}`));
    pyProcess.stderr.on('data', (data) => console.error(`Python Error: ${data}`));

    pyProcess.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`Python script exited with code ${code}`));
      }
    });
  });
}


/////////////////////////////////////////////////////
// Start running the app
//////////////////////////////////////////////////////

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


//////////////////////////////////
// GEN CARD 
/////////////////////////////////

// Handle Gen Card button - opens new window
ipcMain.handle('open-gen-card', async () => {
  if (genWindow) {
    genWindow.focus();
  } else {
    createGenWindow();
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

// Handle gen reps (step 1 of gen card): python call
ipcMain.handle('gen-reps-json', async () => {
  try {
    const pythonScript = path.join(__dirname, '../src/gen_reps_json.py');

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

    return { success: true, message: 'Generated Reps' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});

// Handle gen votes (step 2 of gen card): python call
ipcMain.handle('gen-voting-record-json', async () => {
  try {
    const pythonScript = path.join(__dirname, '../src/gen_voting_record_json.py');

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

    return { success: true, message: 'Generated Votes' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});

//combine data, aka make congressmen_mod.json
ipcMain.handle('combine-data', async () => {
  try {
    const pythonScript = path.join(__dirname, '../src/combine_data.py');

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

    return { success: true, message: 'Created congressmen_mod.json' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});

//gen card
ipcMain.handle('gen-card', async () => {
  try {
    const pythonScript = path.join(__dirname, '../src/gen_temp_for_javascript.py');
    const jsxScript = path.join(__dirname, '../src/fill_social_template.jsx');
    const tempFile = path.join(__dirname, '../src/generated_outputs/temp.txt');

    await deleteFile(tempFile);
    //1: gen temp for javascript

    await runPythonScript(pythonScript, name);
    console.log("Success! temp.txt has been created.");
    // 2: Check if temp.txt was created
    if (!fs.existsSync(tempFile)) {
      throw new Error('temp.txt was not generated');
    }

    // 3: Run Photoshop script using ExtendScript
    await new Promise((resolve, reject) => {
      const isWindows = process.platform === 'win32';
      const isMac = process.platform === 'darwin';

      let command;
      if (isWindows) {
        // Windows: Use Photoshop's executable with the script
        command = `"C:\\Program Files\\Adobe\\Adobe Photoshop 2026\\Photoshop.exe" "${jsxScript}"`;
      } else if (isMac) {
        // Mac: Use osascript to tell Photoshop to run the script
        command = `osascript -e 'tell application "Adobe Photoshop 2026" to do javascript file("${jsxScript}")'`;
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

// Load congressmen data for manual entry
ipcMain.handle('load-congressmen-data', async () => {
  try {
    const congressmenModPath = path.join(__dirname, '../src/generated_outputs/congressmen_mod.json');
    const supplementPath = path.join(__dirname, '../src/generated_outputs/supplement_congressmen.json');

    let congressmenMod = [];
    let supplement = [];

    // Load congressmen_mod.json
    if (fs.existsSync(congressmenModPath)) {
      const congressmenData = fs.readFileSync(congressmenModPath, 'utf8');
      congressmenMod = JSON.parse(congressmenData);
    } else {
      throw new Error(`congressmen_mod.json not found. Looking at ${congressmenModPath}`);
    }

    // Load supplement_congressmen.json
    if (fs.existsSync(supplementPath)) {
      const supplementData = fs.readFileSync(supplementPath, 'utf8');
      if (supplementData.trim().length > 0) {
        supplement = JSON.parse(supplementData);
      }
    }

    return { congressmenMod, supplement };
  } catch (error) {
    throw new Error(`Failed to load data: ${error.message}`);
  }
});

// Save supplement data
ipcMain.handle('save-supplement', async (event, supplementData) => {
  try {
    const supplementPath = path.join(__dirname, '../src/generated_outputs/supplement_congressmen.json');
    
    fs.writeFileSync(supplementPath, JSON.stringify(supplementData, null, 4), 'utf8');
    
    return { success: true, message: 'Data saved successfully!' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});