import os
import argparse

import win32com.client
import pythoncom

# Photoshop's version-independent COM ProgID. Works whether or not Photoshop is
# already running (COM attaches to the live instance or launches a new one).
PHOTOSHOP_PROG_ID = "Photoshop.Application"

# PsDialogModes: 1 = all dialogs, 2 = error dialogs only, 3 = no dialogs.
# We run headless, so suppress everything (alerts in the JSX would otherwise
# block or throw).
DIALOG_MODE_NO = 3


def run_photoshop_script(template, script, generated_outputs):
    """Open `template` in Photoshop and run the `script` JSX against it.

    Photoshop has no working command-line flag to execute a .jsx on Windows
    (`-r` is silently ignored and the .jsx gets treated as a file to open).
    The supported route is COM automation: DoJavaScriptFile runs the script IN
    the Photoshop process, passes real arguments to it (available as
    `arguments[0]` in the JSX), and re-raises any script error back here with
    its message -- far better than an opaque "exit status 1".
    """
    template_abs = os.path.abspath(template)
    script_abs = os.path.abspath(script)
    gen_abs = os.path.abspath(generated_outputs)

    if not os.path.exists(template_abs):
        print(f"ERROR: template not found: {template_abs}")
        return
    if not os.path.exists(script_abs):
        print(f"ERROR: script not found: {script_abs}")
        return

    try:
        app = win32com.client.Dispatch(PHOTOSHOP_PROG_ID)
    except pythoncom.com_error as e:
        print("ERROR: Could not connect to Photoshop via COM. Is Photoshop "
              f"installed and its COM automation registered?\n{e}")
        return

    # Open the template so the JSX can operate on app.activeDocument.
    doc = app.Open(template_abs)

    try:
        # arguments -> the JSX's `arguments` array; arguments[0] = outputs dir.
        app.DoJavaScriptFile(script_abs, [gen_abs], DIALOG_MODE_NO)
        print("Script execution successful!")
        # The script saved its own copy (saveAsNewFile); close the working doc
        # without saving so repeated runs don't pile up open documents.
        doc.Close(2)  # 2 = psDoNotSaveChanges
    except pythoncom.com_error as e:
        # DoJavaScriptFile surfaces the JSX's own error message here.
        print("Error executing Photoshop script (JSX threw or COM failed):")
        # e.excepinfo[2] usually holds the human-readable description.
        desc = None
        if getattr(e, "excepinfo", None):
            desc = e.excepinfo[2]
        print(desc or str(e))
        print("Leaving the document open in Photoshop for inspection.")


if __name__ == "__main__":
    print("Running Photoshop script...")
    parser = argparse.ArgumentParser(description="Pull info for Photoshop automation")
    parser.add_argument('template', help="Template path to modify")
    parser.add_argument('jsx', help="Name of javascript file")
    parser.add_argument('generated_outputs', help="gen_outputs for temp.txt path")
    args = parser.parse_args()

    template = args.template
    jsx = args.jsx
    generated_outputs = args.generated_outputs

    run_photoshop_script(template, jsx, generated_outputs)
