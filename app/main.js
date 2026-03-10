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
    if (!(err.code === 'ENOENT')) {
      console.error('Error deleting file:', err);
    }
  }
}


const { spawn } = require('child_process');

function runPythonScript(scriptPath, args = []) {
  return new Promise((resolve, reject) => {
    // Note: Use 'python' or 'python3' depending on your system
    let pyProcess;
    if (process.platform === "darwin") {
      pyProcess = spawn('python3.14', [scriptPath, ...args]);
    }
    else {
      pyProcess = spawn('python', [scriptPath, ...args]);
    }
    

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

function sendSafe(sender, channel, data) {
    // 1. Check if sender exists
    // 2. Check if the window hasn't been destroyed (user closed the modal)
    if (sender && !sender.isDestroyed()) {
        sender.send(channel, data);
    } else {
        console.warn("Attempted to send to a destroyed window. Ignoring.");
    }
}


function runPythonScriptAndStream(scriptPath, args, sender) {
    console.log("Launching python script");
    let pythonProcess;
    return new Promise((resolve, reject) => {
        if (process.platform === "darwin") {
          pythonProcess = spawn('python3.14', [scriptPath, ...args]);
        }
        else {
          pythonProcess = spawn('python', [scriptPath, ...args]);
        }
        console.log("Spawned new process");
        pythonProcess.stdout.on('data', (data) => {
          const text = data.toString('utf8');
          console.log(text);
          if (sender && !sender.isDestroyed()) {
              sender.send('terminal-update', text);
            }
        });

        // Resolve the promise when the process exits successfully
        pythonProcess.on('close', (code) => {
            if (code === 0) {
                console.log("Python script ", scriptPath, " finished successfully.");
                resolve(); 
            } else {
                reject(new Error(`Python process exited with code ${code}`));
            }
        });

        pythonProcess.on('error', (err) => {
            console.log(err);
            reject(err);
        });
    });
}


function runPythonScriptAndStream_nopromise(scriptPath, args, sender) {
  let pythonProcess;
    if (process.platform === "darwin") {
      pythonProcess = spawn('python3.14', [scriptPath, ...args]);
    }
    else {
      pythonProcess = spawn('python', [scriptPath, ...args]);
    }
    pythonProcess.stdout.on('data', (data) => {
        // Send each chunk of data to the UI
        sendSafe(sender, 'terminal-update', data.toString());    
        console.log(`Python: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
      sendSafe(sender, 'terminal-update', `ERROR: ${data.toString()}`);
      console.log(`ERROR: ${data.toString()}`);
    });

    sender.on('destroyed', () => {
        pythonProcess.kill();
        console.log('Killed process')
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
ipcMain.handle('gen-reps-json', async (event) => {
  try {
    const pythonScript = path.join(__dirname, '../src/gen_reps_json.py');
    await runPythonScriptAndStream(pythonScript, [], event.sender);

    return { success: true, message: 'Generated Reps' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});

// Handle gen votes (step 2 of gen card): python call
ipcMain.handle('gen-voting-record-json', async (event) => {
  try {
    const pythonScript = path.join(__dirname, '../src/gen_voting_record_json.py');
    await runPythonScriptAndStream(pythonScript, [], event.sender);

    return { success: true, message: 'Generated Votes' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});

//combine data, aka make congressmen_mod.json
ipcMain.handle('combine-data', async (event) => {
  try {
    console.log("Now running combine data")
    const pythonScript = path.join(__dirname, '../src/combine_data.py');
    await runPythonScriptAndStream(pythonScript, [], event.sender);

    return { success: true, message: 'Created congressmen_mod.json' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});

//gen card
ipcMain.handle('gen-card', async (_event, name) => {
  console.log("Received from renderer: ", name)
  try {
    const pythonScript = path.join(__dirname, '../src/gen_temp_for_javascript.py');
    const jsxScript = path.join(__dirname, '../src/fill_social_template.jsx');
    const tempFile = path.join(__dirname, '../src/generated_outputs/temp.txt');
    const outputDir = path.join(__dirname, '../cards_ps');
    const replacements = {
      ',': '',
      '"': '',
      '.': '',
      ' ': '_'
    };
    const regex = new RegExp(Object.keys(replacements).map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|'), 'g');
    const sanitizedName = name.replace(regex, (match) => replacements[match] || '')
                          .toLowerCase();
    const outputFileName = `${sanitizedName}_card.psd`;
    const outputPath = path.join(outputDir, outputFileName);


    //1: gen temp for javascript
    await deleteFile(tempFile);
    await runPythonScript(pythonScript, [name]);
    console.log("Success! temp.txt has been created.");


    // 2: Check if temp.txt was created, remove previous psd file if exists
    if (!fs.existsSync(tempFile)) {
      throw new Error('temp.txt was not generated');
    }
    await deleteFile(outputPath);


    // 3: Launch Photoshop
    //await new Promise((resolve, reject) => {
    const isWindows = process.platform === 'win32';
    const isMac = process.platform === 'darwin';

    let command;
    if (isWindows) {
      // Windows: Use Photoshop's executable with the script
      command = `start "" "C:\\Program Files\\Adobe\\Adobe Photoshop 2026\\Photoshop.exe" "${jsxScript}"`;
    } else if (isMac) {
      // Mac: Use osascript to tell Photoshop to run the script
      command = `osascript -e 'tell application "Adobe Photoshop 2026" to do javascript file("${jsxScript}")' &`;
    } else {
      reject('Unsupported operating system');
      return;
    }

    exec(command);
    console.log("Photoshop executed");

    //4: Wait for file completion
    return await new Promise((resolve, reject) => {
        const timeoutMs = 90000; // 90 second limit
        
        // Setup the Timeout
        const timer = setTimeout(() => {
            watcher.close();
            reject(new Error("Timeout: Photoshop took too long to generate the card."));
        }, timeoutMs);

        // Setup the File Watcher
        const watcher = fs.watch(outputDir, (eventType, filename) => {
            if (filename === outputFileName && fs.existsSync(outputPath)) {
                clearTimeout(timer);
                watcher.close();
                console.log("File generated successfully!")
                resolve({ success: true, path: outputPath });
            }
        });

        // Quick check in case it finished instantly before the watcher started
        if (fs.existsSync(outputPath)) {
            clearTimeout(timer);
            watcher.close();
            console.log("File generated successfully!")
            resolve({ success: true, path: outputPath });
        }
    });

    //return { success: true, message: 'Card generated successfully!' };
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