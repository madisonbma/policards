const { dialog, app, BrowserWindow, ipcMain, nativeImage } = require('electron');
const path = require('path');
const os = require('os');
const { exec } = require('child_process');
const fs = require('fs');
const fsPromises = fs.promises;


const isDev = process.env.NODE_ENV !== 'production';
const debug = false;

// Exit code the top-donors script returns when the bioguide_id can't be resolved.
// Keep in sync with BIOGUIDE_NOT_FOUND_EXIT in src/get_top_pac_contributions.py.
// On this code we offer manual candidate-code entry instead of a generic failure.
const BIOGUIDE_NOT_FOUND_EXIT = 42;

// The top-donors script writes its [overview, {company: amount}] result here so we can
// read it back and store it ONLY in the supplement (no duplicate copy in appData). It's
// a throwaway handoff file in the OS temp dir, deleted after every run -- so the name is
// fixed (runs are sequential; one python process at a time) rather than uniquified.
const contributionTmpPath = path.join(os.tmpdir(), 'pp_contribution_data.json');

let mainWindow;
let updateWindow;
let configWindow;
let genWindow;
let pythonProcess = null;

let config;
const generated_outputs = path.join(app.getPath('sessionData'), 'generated_outputs');
const bioguideDataDir = path.join(generated_outputs, 'bioguide_data');


const userDataPath = app.getPath('userData');
const configPath = path.join(userDataPath, 'config.json');



function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 500,
    icon: path.join(__dirname, 'app/assets/icons/pp_logo_1024.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });
  if(process.platform === "darwin") {
    const icon = nativeImage.createFromPath('app/assets/icons/pp_logo_1024.png');
    app.dock.setIcon(icon);
  }
  mainWindow.loadFile('app/renderer/index.html');

}

function createUpdateWindow() {
  updateWindow = new BrowserWindow({
    width: 800,
    height: 500,
    parent: mainWindow,
    icon: path.join(__dirname, 'app/assets/icons/pp_logo_1024.png'),
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
    icon: path.join(__dirname, 'app/assets/icons/pp_logo_1024.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  configWindow.loadFile('app/renderer/config.html');

  configWindow.on('closed', () => {
    configWindow = null;
    if (mainWindow) {
      mainWindow.webContents.send('config-closed');
    }
  });
}


function createGenWindow() {
  genWindow = new BrowserWindow({
    width: 800,
    height: 500,
    parent: mainWindow,
    icon: path.join(__dirname, 'app/assets/icons/pp_logo_1024.png'),
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
  } else {
    config = {};
  }
  const config_fields = [
    'CONGRESS_API_KEY',
    'FEC_API_KEY',
    'photoshop_year',
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
  const seedDir = path.join(config['politician_pages_assets_path'], 'json');
  /*const seedDir = app.isPackaged 
      ? path.join(process.resourcesPath, 'app.asar.unpacked', 'src', 'generated_outputs')
      : path.join(__dirname, 'src', 'generated_outputs');*/
  if (!fs.existsSync(seedDir)) {
    console.error("ERROR: ", seedDir, " does not exist.");
  } else {
    console.log("Copying ", seedDir, "to ", generated_outputs);
  }

  //make generated_outputs dir if doesn't exist
  if (!fs.existsSync(generated_outputs)) {
    fs.mkdirSync(generated_outputs, { recursive: true });
    console.log("Made dir ", generated_outputs);
  }

  const dataFiles = ['voting_records.json', 'voting_records_senate.json', 'supplement_congressmen.json'];

  dataFiles.forEach(file => {  
    const dest = path.join(generated_outputs, file);
    const src = path.join(seedDir, file);
    if (!fs.existsSync(dest)) { //only if file doesn't exist yet
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

  if (!app.isPackaged) {
    // DEVELOPMENT: Root/resources/bin/mac/file
    filepath = path.join(__dirname, 'resources', 'bin', folder, filename);
  } else {
    // PRODUCTION: Contents/Resources/bin/mac/file
    filepath = path.join(process.resourcesPath, 'bin', folder, filename);
  }

  if (!fs.existsSync(filepath)) {
    console.error("FILE NOT FOUND:", filepath);
    throw new Error(`File not found: ${filepath}`);
  }

  return filepath;
}

function scriptname_to_py(name) {
  /* Used for non-packaged binaries anyways. Fine to use config path.*/
  const filename = name + ".py";
  
  return path.join(__dirname, 'src', filename);
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


function runPythonScriptAndStream(scriptName, args, sender) {
    return new Promise((resolve, reject) => {
      let errorData = "";
      if (debug) {
        if (process.platform === "darwin") {
          console.log("Running python3.14 ", scriptname_to_py(scriptName));
          pythonProcess = spawn('python3.14', [scriptname_to_py(scriptName), ...args]);
        }
        else {
          console.log("Running python ", scriptname_to_py(scriptName));
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

      // Capture stderr so a non-zero exit reports the real error (and show it in the
      // terminal view too, not just a generic failure).
      pythonProcess.stderr.on('data', (data) => {
        const text = data.toString('utf8');
        errorData += text;
        console.error(text);
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
          const err = new Error(`${scriptName} failed (Code ${code}).\nDetails: ${errorData}`);
          err.code = code; // surface the exit code so callers can branch on it
          reject(err);
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
ipcMain.handle('check-congressmen-exists', () => {
  return fs.existsSync(path.join(generated_outputs, 'congressmen.json'));
});
ipcMain.handle('check-vote-exists', () => {
  return fs.existsSync(path.join(generated_outputs, 'voting_records.json')) && fs.existsSync(path.join(generated_outputs, 'voting_records_senate.json'));
});
ipcMain.handle('check-path-exists', (_event, path) => {
  return fs.existsSync(path);
});


ipcMain.handle('config-is-clean', () => {
  load_config();
  if (config) {
    if (config['CONGRESS_API_KEY'] === "") {
      console.log("CONGRESS_API_KEY is not valid. Gating genCard option.");
      return false;
    } else if (config['photoshop_year'] === "") {
      console.log("photoshop_year is not valid. Gating genCard option.");
      return false
    } else if (config['politician_pages_assets_path'] === "") {
      console.log("politician_pages_assets_path is not valid. Gating genCard option.");
      return false;
    } else if (config['save_path'] === "") {
      console.log("save_path is not valid. Gating genCard option.");
      return false;
    } else if (!fs.existsSync(config['politician_pages_assets_path'])) {
      console.log("politician_pages_assets_path is not valid. Gating genCard option.");
      return false;
    } else {
      return true;
    }
  } else {
    console.log("Config does not exist");
    return false;
  }
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
    bootstrap_data();
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

    const jsxScript = app.isPackaged
      ? path.join(process.resourcesPath, 'photoshop', 'fill_social_template.jsx')
      : path.join(__dirname, 'app', 'assets', 'photoshop', 'fill_social_template.jsx'); 
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
    const fontDir = app.isPackaged
      ? path.join(process.resourcesPath, 'fonts')
      : path.join(__dirname, 'app', 'assets', 'fonts');
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
      // Windows: drive Photoshop via COM (DoJavaScriptFile) so generated_outputs is
      // passed as the JSX argument (arguments[0]) -- the same as the mac osascript
      // "with arguments {...}". (Photoshop.exe on the CLI can't pass JSX arguments,
      // and COM activation launches Photoshop if it isn't already open.)
      //
      // While Photoshop is still launching/busy, the COM call throws
      // RPC_E_SERVERCALL_RETRYLATER (0x8001010A); retry until it's ready. Only retry
      // on that busy error so a genuine JSX error still propagates (no double-run).
      const psEsc = (s) => String(s).replace(/'/g, "''");
      const psScript =
        "$ErrorActionPreference='Stop'; " +
        "$ps = New-Object -ComObject 'Photoshop.Application'; " +
        "$deadline = (Get-Date).AddSeconds(90); " +
        "while($true){ " +
        "  try{ $ps.DoJavaScriptFile('" + psEsc(jsxScript) + "', @('" + psEsc(generated_outputs) + "')); break } " +
        "  catch{ " +
        "    if( ($_.Exception.Message -match 'RETRYLATER|8001010A|busy') -and ((Get-Date) -lt $deadline) ){ Start-Sleep -Milliseconds 750 } " +
        "    else { throw } " +
        "  } " +
        "}";
      const encoded = Buffer.from(psScript, 'utf16le').toString('base64');
      command = `powershell -NoProfile -EncodedCommand ${encoded}`;
    } else if (isMac) {
      // Mac: Use osascript to tell Photoshop to run the script
      command = `osascript -e 'tell application "Adobe Photoshop ${config['photoshop_year']}" to do javascript file "${jsxScript}" with arguments {"${generated_outputs}"}' &`;
    } else {
      throw new Error('Unsupported operating system');
    }

    exec(command, { env }, (error) => {
        if (error) console.error(`Photoshop Launch Error: ${error}`);
        else console.log("Photoshop executed");
    });

    //4: Wait for file completion
    return await new Promise((resolve, reject) => {
        const timeoutMs = 120000; // 2 minute limit
        
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

// Read the throwaway contribution_data file the top-donors script wrote at `outPath`
// and shape it into the { success, top_donors:[overview, top20] } payload the renderer
// expects. The caller owns the temp file's lifecycle (deletes it after).
function readTopDonorsOutput(outPath) {
  if (!fs.existsSync(outPath)) {
    throw new Error(`Top-donor output not found at ${outPath}`);
  }
  const parsed = JSON.parse(fs.readFileSync(outPath, 'utf8'));
  const overview = parsed[0] || {};
  const donors = parsed[1] || {};

  // Top 20 by amount (script already sorts descending; sort again defensively)
  const top20 = Object.fromEntries(
    Object.entries(donors).sort((a, b) => b[1] - a[1]).slice(0, 20)
  );
  overview.generated_at = new Date().toISOString();

  return { success: true, top_donors: [overview, top20] };
}

// Run the FEC top-donors exe for one representative, stream output to the terminal,
// and return [overview, {top 20 company: amount}] (with a generated_at timestamp).
// The result is read from a temp file and stored only in the supplement (the renderer
// does that) -- no duplicate copy in appData. If the bioguide can't be resolved (exit
// code 42), return needsManualEntry so the renderer can prompt for a candidate code.
ipcMain.handle('get-top-donors', async (event, bioguideId, name) => {
  try {
    const fecKey = config['FEC_API_KEY'];
    if (!fecKey || String(fecKey).trim() === "") {
      return { success: false, message: "FEC_API_KEY is not set. Add it in the config window before fetching top donors." };
    }

    const cycle = String(new Date().getFullYear()); // default cycle = current year
    const args = [
      '--api-key', fecKey,
      '--bioguide-id', bioguideId,
      '--cycle', cycle,
      '--generated-outputs', generated_outputs,
      '--output-path', contributionTmpPath,
    ];

    await runPythonScriptAndStream('get_top_pac_contributions', args, event.sender);

    return readTopDonorsOutput(contributionTmpPath);
  } catch (error) {
    if (error && error.code === BIOGUIDE_NOT_FOUND_EXIT) {
      return { success: false, needsManualEntry: true, message: error.toString() };
    }
    return { success: false, message: error.toString() };
  } finally {
    await deleteFile(contributionTmpPath); // throwaway handoff file; clean up every run
  }
});

// Manual fallback: the user supplies a candidate id directly (used when the bioguide
// lookup failed). Runs the same exe in --candidate-id mode, which writes the same
// throwaway output file we then read back.
ipcMain.handle('get-top-donors-manual', async (event, candidateId) => {
  try {
    const fecKey = config['FEC_API_KEY'];
    if (!fecKey || String(fecKey).trim() === "") {
      return { success: false, message: "FEC_API_KEY is not set. Add it in the config window before fetching top donors." };
    }

    const candidate = String(candidateId || '').trim().toUpperCase();
    if (!candidate) {
      return { success: false, message: "Candidate code is required." };
    }
    const cycle = String(new Date().getFullYear()); // default cycle = current year

    const args = [
      '--api-key', fecKey,
      '--candidate-id', candidate,
      '--cycle', cycle,
      '--generated-outputs', generated_outputs,
      '--output-path', contributionTmpPath,
    ];

    await runPythonScriptAndStream('get_top_pac_contributions', args, event.sender);

    return readTopDonorsOutput(contributionTmpPath);
  } catch (error) {
    return { success: false, message: error.toString() };
  } finally {
    await deleteFile(contributionTmpPath); // throwaway handoff file; clean up every run
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