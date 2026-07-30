// Generic runner. main.js never invokes a card JSX directly -- it invokes this,
// which opens the template, runs the target, and (crucially) catches any
// ExtendScript error so the message survives the trip back to the app.
//
// Without this wrapper a thrown JSX error is opaque: AppleScript's `do javascript`
// reports it as "General Photoshop error occurred ... number 8800" with no text,
// and COM is only marginally better. main.js then just never sees an output file
// and reports a generic timeout, which is indistinguishable from a real hang.
//
// arguments[0] = generated_outputs dir      (the target reads this)
// arguments[1] = explicit save path         (the target reads this)
// arguments[2] = absolute path to the target .jsx
// arguments[3] = absolute path to the template .psd to open
//
// REPORT PROTOCOL -- <generated_outputs>/jsx_error.txt always ends up holding one of:
//   "OK"               ran to completion
//   "JSX ERROR: ..."   the target threw; message and line included
//   "STARTED ..."      died between the breadcrumb and the catch (i.e. in this file)
//   <no file at all>   this script never ran: bad path, or a syntax error in HERE
// main.js reads it and treats anything that isn't "OK" as the failure message.
// Keep this file ES3-only -- ExtendScript has no const/let/arrow functions, and
// `arguments` cannot be used as an assignment target (doing so is a compile error
// that silently kills the whole script before the try block is ever reached).

var PP_GEN_OUTPUTS = arguments[0];
var PP_SAVE_PATH   = arguments[1];
var PP_TARGET_JSX  = arguments[2];
var PP_TEMPLATE    = arguments[3];

var PP_ERROR_FILE = new File(PP_GEN_OUTPUTS + "/jsx_error.txt");

function pp_report(msg) {
    try {
        PP_ERROR_FILE.encoding = "UTF-8";
        if (PP_ERROR_FILE.open('w')) {
            PP_ERROR_FILE.write(msg);
            PP_ERROR_FILE.close();
        }
    } catch (ignored) {}
}

// Breadcrumb: overwritten with OK or the real error below. If it survives as-is,
// something in this wrapper failed outside the try.
pp_report("STARTED but did not finish: target=" + PP_TARGET_JSX + " template=" + PP_TEMPLATE);

try {
    // Suppress Photoshop's own dialogs. A modal on macOS is unrecoverable -- it
    // blocks the AppleEvent indefinitely and the only symptom is a timeout.
    // NOTE: this does not suppress ExtendScript alert(); those still block.
    app.displayDialogs = DialogModes.NO;

    // fill_social / fill_card_front check this env var before arguments[0].
    // The targets also read `arguments` directly, and $.evalFile evaluates in the
    // global scope, so they see the array Photoshop injected for this script --
    // same indices (0 = outputs dir, 1 = save path), which is why the arg order
    // above matters.
    $.setenv("GEN_OUTPUT_DIR", PP_GEN_OUTPUTS);

    // Open the template HERE rather than from the host. On macOS, AppleScript's
    // `open` rejects a file alias sent over the AppleEvent boundary with -43, and
    // `POSIX file` inside a `tell` block collides with Photoshop's own `file`
    // term (-1728). Opening from ExtendScript sidesteps both and keeps mac and
    // Windows on a single path.
    app.open(new File(PP_TEMPLATE));

    $.evalFile(new File(PP_TARGET_JSX));

    pp_report("OK");
    "OK";
} catch (e) {
    var pp_msg = "JSX ERROR: " + (e.message || e)
        + (e.line ? " (line " + e.line + ")" : "")
        + (e.fileName ? " in " + e.fileName : "");
    pp_report(pp_msg);
    pp_msg;
}
