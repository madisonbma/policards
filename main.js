const { dialog, app, BrowserWindow, ipcMain } = require('electron');
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
let pythonProcess = null;

let config;
const generated_outputs = path.join(app.getPath('sessionData'), 'generated_outputs');
const bioguideDataDir = path.join(generated_outputs, 'bioguide_data');


const userDataPath = app.getPath('userData')
const configPath = path.join(userDataPath, 'config.json');

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 500,
    icon: path.join(__dirname, 'app/assets/icons/pp_logo.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  mainWindow.loadFile('app/renderer/index.html');

}

function createUpdateWindow() {
  updateWindow = new BrowserWindow({
    width: 800,
    height: 500,
    parent: mainWindow,
    icon: path.join(__dirname, 'app/assets/icons/pp_logo.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  updateWindow.loadFile('app/renderer/update.html');

  updateWindow.on('closed', () => {
    updateWindow = null;
  });
}


function createConfigWindow() {
  configWindow = new BrowserWindow({
    width: 800,
    height: 500,
    parent: mainWindow,
    icon: path.join(__dirname, 'app/assets/icons/pp_logo.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  configWindow.loadFile('app/renderer/config.html');

  configWindow.on('closed', () => {
    configWindow = null;
  });
}


function createGenWindow() {
  genWindow = new BrowserWindow({
    width: 800,
    height: 500,
    parent: mainWindow,
    icon: path.join(__dirname, 'app/assets/icons/pp_logo.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  genWindow.loadFile('app/renderer/gencard.html');

  genWindow.on('closed', () => {
    genWindow = null;
  });
}

async function load_config() {
  // Load config.json
  if (fs.existsSync(configPath)) {
    const configData = fs.readFileSync(configPath, 'utf8');
    config = JSON.parse(configData);
  }
  const config_fields = [
    'CONGRESS_API_KEY',
    'FEC_API_KEY',
    'photoshop_year',
    'politician_pages_path',
    'politician_pages_assets_path',
    'save_path'
  ]

  config_fields.forEach (field => {
    if (!config.hasOwnProperty(field)) {
      config[field] = "";
    }
  });
  console.log("Loaded config data", config);

}

async function bootstrap_data() {
  load_config();
  const seedDir = app.isPackaged 
      ? path.join(process.resourcesPath, 'app.asar.unpacked', 'src', 'generated_outputs')
      : path.join(__dirname, 'src', 'generated_outputs');
      //: path.join(config['politician_pages_path'], 'src', 'generated_outputs');

  console.log(generated_outputs);
  //make generated_outputs dir if doesn't exist
  if (!fs.existsSync(generated_outputs)) {
    fs.mkdirSync(generated_outputs, { recursive: true });
    console.log("Made dir ", generated_outputs);
  }

  const dataFiles = ['voting_records.json', 'voting_records_senate.json', 'congressmen.json',
    'supplement_congressmen.json', 'congressmen_mod.json'];

  dataFiles.forEach(file => {  
    const dest = path.join(generated_outputs, file);
    const src = path.join(seedDir, file);
    if (!fs.existsSync(dest)) {
      try {
        // Use copyFileSync for a blocking, reliable first-time copy
        fs.copyFileSync(src, dest);
          console.log(`Bootstrapped: ${file}`);
      } catch (err) {
        console.error(`Failed to bootstrap ${file}:`, err.message);
      }
    }
  });

}

function default_config(configPath) {
  const default_config = {
    'CONGRESS_API_KEY': "",
    'FEC_API_KEY': "",
    'photoshop_year': "",
    'politician_pages_path': "",
    'politician_pages_assets_path': "",
    'save_path': ""
  }
  const jsonString = JSON.stringify(default_config);
  fs.writeFile(configPath, jsonString, (err) => {
      if (err) {
          console.error('Error writing to file', err.message);
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
      console.error('Error deleting file:', err.message);
    }
  }
}

function getBinaryPath(file) {
  const isWin = process.platform === "win32";
  const folder = isWin ? 'win' : 'mac';
  const filename = isWin ? file + '.exe' : file ;
  if (isDev) {
    const filepath = path.join(config['politician_pages_path'], 'resources/bin', folder, filename);
    if (!fs.existsSync(filepath)) {
      console.log("FILE NOT FOUND: ", filepath)
      throw new Error(`File not found: ${filepath}`);
    }
    else {
      console.log("Using file ", filepath);
    }

    return filepath;
  } else {
    const filepath = path.join(process.resourcesPath, 'bin', filename);
    if (!fs.existsSync(filepath)) {
      console.log("FILE NOT FOUND: ", filepath)
      throw new Error(`File not found: ${filepath}`);
    }
    else {
      console.log("Using file ", filepath);
    }
    return filepath;
  }
}

function scriptname_to_py(name) {
  /* Used for non-packaged binaries anyways. Fine to use config path.*/
  const filename = name + ".py";
  
  return path.join(config['politician_pages_path'], 'src', filename);
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
    
    let error_data = "";
    pyProcess.stdout.on('data', (data) => console.log(`Python: ${data}`));
    pyProcess.stderr.on('data', (data) => error_data += data.toString());

    pyProcess.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`Python script exited with code ${code}: ${error_data}`));
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
          console.error(`Python Error Output:\n${errorData}`);
          reject(new Error(`${scriptName} failed (Code ${code}).\nDetails: ${errorData}`));
        }
      });

      pythonProcess.on('error', (err) => {
        console.log(err.message);
        reject(err);
      });
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

app.whenReady().then(() => {
  createMainWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
  bootstrap_data();
});

app.on('will-quit', () => {
    if (pythonProcess) {
        // 'SIGTERM' tells Python "Please stop," which is safer than 'SIGKILL'
        pythonProcess.kill('SIGTERM'); 
        pythonProcess = null;
    }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});


//////////////////////////////////
// GEN CARD 
/////////////////////////////////
ipcMain.handle('check-bioguide-exists', () => {
  return fs.existsSync(bioguideDataDir) && fs.readdirSync(bioguideDataDir).length > 0;
});

// Handle Gen Card button - opens new window
ipcMain.handle('open-gen-card', async () => {
  if (genWindow) {
    genWindow.focus();
  } else {
    createGenWindow();
  }

  //load config data when loading generate
  try {
    load_config();
  } catch (error) {
    throw new Error(`Failed to load data: ${error.message}`);
  }

  change_permissions_for_mac();

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
    await runPythonScriptAndStream(pythonScript, [config['CONGRESS_API_KEY'], generated_outputs], event.sender);

    return { success: true, message: 'Generated Reps' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});



const AdmZip = require('adm-zip'); // Import the zip library

ipcMain.handle('import-bioguide-data', async () => {
  const { canceled, filePaths } = await dialog.showOpenDialog({
    properties: ['openFile'],
    filters: [{ name: 'Bioguide Data', extensions: ['zip', 'json'] }]
  });

  if (canceled || filePaths.length === 0) return { success: false };

  const sourcePath = filePaths[0];

  // 1. Ensure the destination directory exists. Remove and reset if it does
  if (!fs.existsSync(bioguideDataDir)) {
    fs.mkdirSync(bioguideDataDir, { recursive: true });
  } else {
    fs.rmSync(bioguideDataDir, { recursive: true, force: true });
    fs.mkdirSync(bioguideDataDir, { recursive: true });
  }

  try {
    if (path.extname(sourcePath).toLowerCase() === '.zip') {
      // 2. Handle ZIP extraction
      const zip = new AdmZip(sourcePath);
          
      // Extract everything to the bioguide_data folder
      // overwrite: true ensures old data is replaced by the new export
      zip.extractAllTo(bioguideDataDir, true);
      console.log('ZIP extraction complete');
    } else {
      // 3. Handle single JSON file
      const destPath = path.join(bioguideDataDir, path.basename(sourcePath));
      fs.copyFileSync(sourcePath, destPath);
      console.log('JSON copy complete');
    }

    // 4. Trigger your Python processing script here
    // spawn(processExePath, [destDir]); 

    return { success: true, message: "Data imported and unpacked successfully!" };
  } catch (err) {
    console.error("Import failed:", err);
    return { success: false, error: err.message };
  }
});

// Handle gen votes (step 2 of gen card): python call
ipcMain.handle('gen-voting-record-json', async (event) => {
  try {
    const pythonScript = 'gen_voting_record_json';
    await runPythonScriptAndStream(pythonScript, [config['CONGRESS_API_KEY'], generated_outputs], event.sender);

    return { success: true, message: 'Generated Votes' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});

//combine data, aka make congressmen_mod.json
ipcMain.handle('combine-data', async (event) => {
  try {
    console.log("Now running combine data");
    const pythonScript = 'combine_data';
    await runPythonScriptAndStream(pythonScript, [generated_outputs], event.sender);

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

    const jsxScript = path.join(__dirname, 'app/assets/photoshop/fill_social_template.jsx');
    const tempFile = path.join(generated_outputs, 'temp.txt');
    const outputDir = config['save_path'];
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
    const fontDir = path.join(__dirname, 'app/assets/fonts')

    //1: gen temp for javascript
    await deleteFile(tempFile);
    await runPythonScript(pythonScript, [name, generated_outputs, config['politician_pages_assets_path'], outputDir, fontDir]);
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

    const env = { ...process.env, GEN_OUTPUT_DIR: generated_outputs };
    let command;
    if (isWindows) {
      // Windows: Use Photoshop's executable with the script
      command = `start "" "C:\\Program Files\\Adobe\\Adobe Photoshop ${config['photoshop_year']}\\Photoshop.exe" "${jsxScript}"`;
    } else if (isMac) {
      // Mac: Use osascript to tell Photoshop to run the script
      command = `osascript -e 'tell application "Adobe Photoshop ${config['photoshop_year']}" to do javascript file("${jsxScript}")' &`;
    } else {
      throw new Error('Unsupported operating system');
    }

    exec(command, { env }, (error) => {
        if (error) console.error(`Photoshop Launch Error: ${error}`);
        else console.log("Photoshop executed");
    });

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
    const congressmenModPath = path.join(generated_outputs, 'congressmen_mod.json');
    const supplementPath = path.join(generated_outputs, 'supplement_congressmen.json');
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



// Load config data when opening config page
ipcMain.handle('load-config-data', async () => {
    // Load config.json
  try {
    load_config();
    return { config };
  } catch (error) {
    throw new Error(`Failed to load data: ${error.message}`);
  }
});

// Save config data
ipcMain.handle('save-config-data', async (event, configData) => {
  try {
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
    const supplementPath = path.join(generated_outputs, 'supplement_congressmen.json');
    
    fs.writeFileSync(supplementPath, JSON.stringify(supplementData, null, 4), 'utf8');
    
    return { success: true, message: 'Data saved successfully!' };
  } catch (error) {
    return { success: false, message: error.toString() };
  }
});