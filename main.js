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

// The Python pac-contribution step caches house_runners_<cycle>.json /
// senate_runners_<cycle>.json and reuses them if present. Clear them on each app launch
// so the runner list is regenerated fresh -- a stale cache skewed the results. Matches any
// cycle (2026, 2028, ...) rather than a hard-coded year.
function deleteStaleRunnerFiles() {
  try {
    if (!fs.existsSync(generated_outputs)) return;
    for (const file of fs.readdirSync(generated_outputs)) {
      if (/^(house|senate)_runners_.*\.json$/.test(file)) {
        try {
          fs.unlinkSync(path.join(generated_outputs, file));
          console.log('Cleared stale runner cache:', file);
        } catch (err) {
          console.error('Failed to delete stale runner file', file, err.message);
        }
      }
    }
  } catch (err) {
    console.error('Error clearing stale runner files:', err.message);
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
  // Remove stale runner caches so they regenerate fresh this session.
  deleteStaleRunnerFiles();
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

// Sanitize a rep name into the card filename stem (e.g. "Lisa Murkowski" -> "lisa_murkowski").
function sanitizeCardName(name) {
  const replacements = { ',': '', '"': '', '.': '', ' ': '_' };
  const regex = new RegExp(Object.keys(replacements).map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|'), 'g');
  return name.replace(regex, (match) => replacements[match] || '').toLowerCase();
}

// Run the Python step that writes temp.txt (rep_info) for the JSX. Shared by the
// social ("Gen Card") and card-back ("Gen Manual Card") flows -- both consume the
// same rep_info. Returns the temp.txt path once it's confirmed written.
async function prepareTempForRep(name) {
  const tempFile = path.join(generated_outputs, 'temp.txt');
  const fontDir = app.isPackaged
    ? path.join(process.resourcesPath, 'fonts')
    : path.join(__dirname, 'app', 'assets', 'fonts');
  await deleteFile(tempFile);
  await runPythonScript('gen_temp_for_javascript',
    [name, generated_outputs, config['politician_pages_assets_path'], config['save_path'], fontDir]);
  if (!fs.existsSync(tempFile)) {
    throw new Error('temp.txt was not generated');
  }
  return tempFile;
}


// Absolute path to a .jsx we ship (packaged -> resources/photoshop, dev -> app/assets).
function photoshopScriptPath(jsxRelName) {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'photoshop', jsxRelName)
    : path.join(__dirname, 'app', 'assets', 'photoshop', jsxRelName);
}

// PowerShell serializes its error stream as CLIXML whenever stderr is redirected,
// so a COM failure arrives as a wall of XML. Pull the human-readable parts back out
// and flatten to one line -- this is what the user sees on the failure page.
function cleanHostError(text) {
  let s = String(text || '');
  if (s.indexOf('#< CLIXML') !== -1) {
    const parts = [...s.matchAll(/<S S="Error">([\s\S]*?)<\/S>/g)].map(m => m[1]);
    if (parts.length) s = parts.join('');
  }
  return s
    .replace(/_x000D_/gi, '')
    .replace(/_x000A_/gi, ' ')
    .replace(/&gt;/g, '>').replace(/&lt;/g, '<').replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'").replace(/&amp;/g, '&')
    .replace(/\s+/g, ' ')
    .trim();
}

// Open `templatePath` in Photoshop and run `jsxScript` against it, passing the
// outputs dir to the script as arguments[0]. Photoshop has no working CLI
// script flag, so we drive it over COM on Windows / AppleScript on mac. The
// template is opened HERE (not inside the JSX) so main.js controls which template
// each flow uses.
//
// Both hosts are synchronous, so this resolves only once Photoshop is done and
// rejects with whatever the host reported -- that's how a Photoshop-side failure
// reaches the UI as real text instead of an unexplained timeout.
// `genOutputsDir` deliberately does NOT reuse the module-level `generated_outputs`
// name: shadowing it hid a bug where an array was passed here and String()'d into
// a comma-joined path four layers down inside Photoshop.
function runPhotoshop(templatePath, jsxScript, genOutputsDir) {
  const env = { ...process.env, GEN_OUTPUT_DIR: genOutputsDir };
  const isWindows = process.platform === 'win32';
  const isMac = process.platform === 'darwin';

  let command;
  if (isWindows) {
    // COM (New-Object -ComObject) launches Photoshop if it isn't already open.
    // While it's still starting the call throws RPC_E_SERVERCALL_RETRYLATER
    // (0x8001010A); retry ONLY on that busy error so a genuine Open/JSX error
    // still propagates (no double-run). Open the template first, then run the JSX.
    const psEsc = (s) => String(s).replace(/'/g, "''");
    //const argsPs = '@(' + genOutputsDir  + ')';
    const psScript =
      "$ErrorActionPreference='Stop'; " +
      "$ps = New-Object -ComObject 'Photoshop.Application'; " +
      "$deadline = (Get-Date).AddSeconds(90); " +
      "function Invoke-PsRetry([ScriptBlock]$action){ " +
      "  while($true){ " +
      "    try{ & $action; break } " +
      "    catch{ " +
      "      if( ($_.Exception.Message -match 'RETRYLATER|8001010A|busy') -and ((Get-Date) -lt $deadline) ){ Start-Sleep -Milliseconds 750 } " +
      "      else { throw } " +
      "    } " +
      "  } " +
      "} " +
      "Invoke-PsRetry { [void]$ps.Open('" + psEsc(templatePath) + "') }; " +
      "Invoke-PsRetry { $ps.DoJavaScriptFile('" + psEsc(jsxScript) + "', @('" + psEsc(genOutputsDir) + "')) }; ";
      //"Invoke-PsRetry { $ps.DoJavaScriptFile('" + psEsc(jsxScript) + "', " + argsPs + ") }";

      const encoded = Buffer.from(psScript, 'utf16le').toString('base64');
    command = `powershell -NoProfile -EncodedCommand ${encoded}`;
  } else if (isMac) {
    // Straight transplant of the sequence verified in Script Editor. Three things
    // matter and each cost a debugging round:
    //  1. `POSIX file "..."` must be coerced OUTSIDE the tell block -- inside one
    //     it collides with Photoshop's own `file` term and fails to compile (-1728).
    //  2. It must be coerced `as alias`. A bare file specifier is a reference that
    //     Photoshop tries to resolve in its own scope and rejects (-43).
    //  3. The template is opened via ExtendScript (`do javascript` with a source
    //     STRING), not AppleScript's `open`, which rejects the alias with -43.
    // The `with timeout` block is the one addition: AppleEvents default to a 120s
    // send timeout, which a full card render can exceed.
    const year = config['photoshop_year'];
    const appName = `Adobe Photoshop ${year}`;
    // Three nested syntaxes: ExtendScript source, inside an AppleScript string
    // literal, inside a single-quoted shell word. Escape innermost first.
    const jsStr = (s) => String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
    const asStr = (s) => String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
    const shSq = (s) => String(s).replace(/'/g, `'\\''`);
    const e = (applescript) => `-e '${shSq(applescript)}'`;

    const openJs = `app.open(new File("${jsStr(templatePath)}"))`;
    const macArgs = `"${asStr(genOutputsDir)}"`;

    command = [
      'osascript',
      e(`set jsxFile to POSIX file "${asStr(jsxScript)}" as alias`),
      e('with timeout of 300 seconds'),
      e(`tell application "${appName}" to do javascript "${asStr(openJs)}"`),
      e(`tell application "${appName}" to do javascript jsxFile with arguments {${macArgs}}`),
      e('end timeout'),
    ].join(' ');
  } else {
    throw new Error('Unsupported operating system');
  }

  return new Promise((resolve, reject) => {
    exec(command, { env, maxBuffer: 1024 * 1024 }, (error, stdout, stderr) => {
      if (error) {
        // stderr carries the useful text: the AppleScript error (including
        // Photoshop's own message) or the PowerShell/COM exception.
        const detail = [stderr, stdout].map(cleanHostError).filter(Boolean).join(' | ');
        const message = `Photoshop error: ${detail || error.message}`;
        console.error(message);
        return reject(new Error(message));
      }
      console.log("Photoshop executed");
      resolve();
    });
  });
}

// Resolve once the JSX writes `outputPath`. Photoshop is driven synchronously now,
// so by the time we get here saveAs has already returned -- this is a short backstop
// for filesystem lag, not the primary success signal.
function waitForCardOutput(outputDir, outputFileName, outputPath, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      watcher.close();
      reject(new Error(
        `Photoshop finished without reporting an error, but no card appeared at ${outputPath}. ` +
        `Check that the JSX saved to the expected filename.`));
    }, timeoutMs);

    const watcher = fs.watch(outputDir, (eventType, filename) => {
      if (filename === outputFileName && fs.existsSync(outputPath)) {
        clearTimeout(timer);
        watcher.close();
        console.log("File generated successfully!");
        resolve({ success: true, path: outputPath });
      }
    });

    // Quick check in case it finished instantly before the watcher started
    if (fs.existsSync(outputPath)) {
      clearTimeout(timer);
      watcher.close();
      console.log("File generated successfully!");
      resolve({ success: true, path: outputPath });
    }
  });
}

//gen card (social / digital template, party-specific)
ipcMain.handle('gen-card', async (_event, name, party) => {
  console.log("Received from renderer: ", name, party)
  try {
    const stem = sanitizeCardName(name);
    const suffix = partyTemplateSuffix(party);

    // 1: gen temp.txt for the JSX
    await prepareTempForRep(name);
    console.log("Success! temp.txt has been created.");

    // 2: pick the party-specific digital template here (no longer from temp.txt),
    //    render it, and wait for the output file.
    return await generateCardSide(
      'fill_social_template.jsx', 'digital_cards', `digital_card_${suffix}.psd`, `${stem}_card.psd`);
  } catch (error) {
    // .message (not .toString()) so the failure page shows the JSX's own text
    // without an "Error:" prefix in front of it.
    return { success: false, message: error.message || String(error) };
  }
});

// Render one card side/variant: open its template (under templates/<subdir>/),
// run its JSX with an explicit save path (arguments[1]) so the output name is
// exactly what we watch for, and wait for the file to appear.
// Resolves { success, path }.
async function generateCardSide(jsxRelName, templateSubdir, templateName, outputFileName) {
  const outputDir = config['save_path'];
  const jsxScript = photoshopScriptPath(jsxRelName);
  // Templates live in the user's assets folder under the given subdir.
  const templatePath = path.join(config['politician_pages_assets_path'], 'templates', templateSubdir, templateName);
  const outputPath = path.join(outputDir, outputFileName);

  if (!fs.existsSync(templatePath)) {
    throw new Error(`Template not found: ${templatePath}`);
  }
  if (!fs.existsSync(jsxScript)) {
    throw new Error(`Photoshop script not found: ${jsxScript}`);
  }
  // Photoshop's saveAs fails with a bare "file not found" (-43) if the destination
  // directory doesn't exist -- it won't create one.
  fs.mkdirSync(outputDir, { recursive: true });

  await deleteFile(outputPath);

  // Rejects with the host's error text if Photoshop or the JSX fails.
  // Only the outputs dir crosses to the JSX now -- it derives the filename itself
  // by appending _card.psd / _card_back.psd / _card_front.psd to file_save_path.
  await runPhotoshop(templatePath, jsxScript, generated_outputs);
  return await waitForCardOutput(outputDir, outputFileName, outputPath);
}

// Map a party name to the physical-template suffix (R/D/I). Anything that isn't
// Republican/Democrat (e.g. Independent) falls back to 'I'.
function partyTemplateSuffix(party) {
  switch (String(party || '').toLowerCase()) {
    case 'republican': return 'R';
    case 'democrat':   return 'D';
    default:           return 'I';
  }
}

//gen manual card (physical card: back + front, party-specific templates)
ipcMain.handle('gen-manual-card', async (_event, name, party) => {
  console.log("Received from renderer (manual): ", name, party)
  try {
    const stem = sanitizeCardName(name);
    const suffix = partyTemplateSuffix(party);

    // 1: same data pipeline as Gen Card (one temp.txt feeds both sides)
    await prepareTempForRep(name);
    console.log("Success! temp.txt has been created.");

    // 2: render both sides sequentially, using the party-specific templates.
    //    Photoshop is single-instance, so we wait for each side's file before
    //    launching the next (avoids the two COM runs colliding in one process).
    const backResult = await generateCardSide(
      'fill_card_back_nosocial_template.jsx', 'physical_cards', `card_back_no_socials_${suffix}.psd`, `${stem}_card_back.psd`);
    const frontResult = await generateCardSide(
      'fill_card_front_template.jsx', 'physical_cards', `card_front_${suffix}.psd`, `${stem}_card_front.psd`);

    return { success: true, paths: [backResult.path, frontResult.path] };
  } catch (error) {
    return { success: false, message: error.message || String(error) };
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