const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { exec } = require('child_process');
const fs = require('fs');
const fsPromises = fs.promises; 

const isDev = process.env.NODE_ENV !== 'production';
const debug = false;

let mainWindow;
let updateWindow;
let configWindow;
let genWindow;

let config;

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
  try {
    const configPath = path.join(__dirname, '../src/config.json');
    // Load config.json
    if (fs.existsSync(configPath)) {
      const configData = fs.readFileSync(configPath, 'utf8');
      config = JSON.parse(configData);
      if (Object.keys(config).length <= 0) {
        config = default_config(configPath);
      }
    } else {
      //create new config file with prepopulated fields
      config = default_config(configPath);
    }
    console.log("Loaded config data", config);
  } catch (error) {
    throw new Error(`Failed to load data: ${error.message}`);
  }

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


function createConfigWindow() {
  configWindow = new BrowserWindow({
    width: 800,
    height: 500,
    parent: mainWindow,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  configWindow.loadFile('renderer/config.html');

  configWindow.on('closed', () => {
    configWindow = null;
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

function default_config(configPath) {
  const default_config = {
    'CONGRESS_API_KEY': "",
    'FEC_API_KEY': "",
    'photoshop_year': "",
    'politician_pages_path': "",
    'politician_pages_assets_path': ""
  }
  const jsonString = JSON.stringify(default_config);
  fs.writeFile(configPath, jsonString, (err) => {
      if (err) {
          console.error('Error writing to file', err);
      } else {
          console.log(`Data written to ${configPath} as JSON.`);
      }
  });
  return default_config;
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

function getBinaryPath(file) {
  const isWin = process.platform === "win32";
  const folder = isWin ? 'win' : 'mac';
  const filename = isWin ? file + '.exe' : file + '-binary';
  if (isDev) {
    const filepath = path.join(config['politician_pages_path'], 'resources/bin', folder, filename);
    if (!fs.existsSync(filepath)) {
      console.log("FILE NOT FOUND: ", filepath)
    }
    else {
      console.log("Using file ", filepath);
    }

    return filepath;
  } else {
    const filepath = path.join(process.resourcesPath, 'bin', filename);
    if (!fs.existsSync(filepath)) {
      console.log("FILE NOT FOUND: ", filepath)
    }
    else {
      console.log("Using file ", filepath);
    }
    return filepath;
  }
}

function scriptname_to_py(name) {
  const filename = name + ".py";
  return path.join(__dirname, '../src', filename);
}

const { spawn } = require('child_process');

function runPythonScript(scriptName, args = []) {
  return new Promise((resolve, reject) => {
    let pyProcess;
    if (debug) {
      if (process.platform === "darwin") {
        pyProcess = spawn('python3.14', [scriptname_to_py(scriptName), ...args]);
      }
      else {
        pyProcess = spawn('python', [scriptname_to_py(scriptName), ...args]);
      }
    } else {
      pyProcess = spawn(getBinaryPath(scriptName), args, {
        stdio: 'pipe'
      });
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


function runPythonScriptAndStream(scriptName, args, sender) {
    let pythonProcess;
    return new Promise((resolve, reject) => {
      if (debug) {
        if (process.platform === "darwin") {
          pythonProcess = spawn('python3.14', [scriptname_to_py(scriptName), ...args]);
        }
        else {
          pythonProcess = spawn('python', [scriptname_to_py(scriptName), ...args]);
        }
      } else {
        console.log("Spawning: ", getBinaryPath(scriptName), args)
        pythonProcess = spawn(getBinaryPath(scriptName), args, {
          stdio: 'pipe'
        });
      }
      console.log("Spawning new process");


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
              console.log(scriptName, " finished successfully.");
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


function runPythonScriptAndStream_nopromise(scriptName, args, sender) {
  let pythonProcess;
  if (debug) {
    if (process.platform === "darwin") {
      pythonProcess = spawn('python3.14', [scriptname_to_py(scriptName), ...args]);
    }
    else {
      pythonProcess = spawn('python', [scriptname_to_py(scriptName), ...args]);
    }
  } else {
    pythonProcess = spawn(getBinaryPath(scriptName), args, {
      stdio: 'pipe'
    });
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


function change_permissions_for_mac() {
  if (process.platform !== 'win32') {
    fs.chmodSync(getBinaryPath('gen_reps_json'), '755');
    fs.chmodSync(getBinaryPath('gen_voting_record_json'), '755');
    fs.chmodSync(getBinaryPath('combine_data'), '755');
    fs.chmodSync(getBinaryPath('gen_temp_for_javascript'), '755');
  }
}


/////////////////////////////////////////////////////
// Start running the app
//////////////////////////////////////////////////////

change_permissions_for_mac();

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

// Handle Edit Config button - opens new window
ipcMain.handle('open-config-window', () => {
  if (configWindow) {
    configWindow.focus();
  } else {
    createConfigWindow();
  }
});

// Handle gen reps (step 1 of gen card): python call
ipcMain.handle('gen-reps-json', async (event) => {
  try {
    const pythonScript = 'gen_reps_json';
    await runPythonScriptAndStream(pythonScript, [config['CONGRESS_API_KEY'], config['politician_pages_path']], event.sender);

    return { success: true, message: 'Generated Reps' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});

// Handle gen votes (step 2 of gen card): python call
ipcMain.handle('gen-voting-record-json', async (event) => {
  try {
    const pythonScript = 'gen_voting_record_json';
    await runPythonScriptAndStream(pythonScript, [config['CONGRESS_API_KEY'], config['politician_pages_path']], event.sender);

    return { success: true, message: 'Generated Votes' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});

//combine data, aka make congressmen_mod.json
ipcMain.handle('combine-data', async (event) => {
  try {
    console.log("Now running combine data")
    const pythonScript = 'combine_data';
    await runPythonScriptAndStream(pythonScript, [config['politician_pages_path']], event.sender);

    return { success: true, message: 'Created congressmen_mod.json' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});

//gen card
ipcMain.handle('gen-card', async (_event, name) => {
  console.log("Received from renderer: ", name)
  try {
    const pythonScript = 'gen_temp_for_javascript';
    const jsxScript = path.join(config['politician_pages_path'], 'src/fill_social_template.jsx');
    const tempFile = path.join(config['politician_pages_path'], 'src/generated_outputs/temp.txt');
    const outputDir = path.join(config['politician_pages_path'], 'cards_ps');
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
    await runPythonScript(pythonScript, [name, config['politician_pages_path'], config['politician_pages_assets_path']]);
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
    console.log("Starting with ", config['politician_pages_path']);
    const congressmenModPath = path.join(config['politician_pages_path'], 'src/generated_outputs/congressmen_mod.json');
    const supplementPath = path.join(config['politician_pages_path'], 'src/generated_outputs/supplement_congressmen.json');
    console.log("Using paths", congressmenModPath, supplementPath);
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



// Load config data
ipcMain.handle('load-config-data', async () => {
  try {
    const configPath = path.join(__dirname, '../src/config.json');
    // Load config.json
    if (fs.existsSync(configPath)) {
      const configData = fs.readFileSync(configPath, 'utf8');
      config = JSON.parse(configData);
      if (Object.keys(config).length <= 0) {
        config = default_config(configPath);
      }
    } else {
      //create new config file with prepopulated fields
      config = default_config(configPath);
    }
    console.log("Loaded config data", config);
    return { config };
  } catch (error) {
    throw new Error(`Failed to load data: ${error.message}`);
  }
});

// Save config data
ipcMain.handle('save-config-data', async (event, configData) => {
  try {
    const configPath = path.join(__dirname, '../src/config.json');

    //load the data to use directly:
    config = configData;

    //now save to file for future use
    fs.writeFileSync(configPath, JSON.stringify(configData, null, 4), 'utf8');
    return { success: true, message: 'Data saved successfully!' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});

// Save supplement data
ipcMain.handle('save-supplement', async (event, supplementData) => {
  try {
    const supplementPath = path.join(config['politician_pages_path'], 'src/generated_outputs/supplement_congressmen.json');
    
    fs.writeFileSync(supplementPath, JSON.stringify(supplementData, null, 4), 'utf8');
    
    return { success: true, message: 'Data saved successfully!' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});