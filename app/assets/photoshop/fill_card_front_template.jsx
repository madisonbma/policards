// Check if Photoshop is running
#target photoshop


// The outputs dir is passed in from run_jsx.py via an env var. Photoshop's CLI
// can't forward args to a .jsx, so arguments[0] is only a fallback.
var generated_outputs = $.getenv("GEN_OUTPUT_DIR") || arguments[0];
const enable_log = false;

if (generated_outputs) {
    // Photoshop paths often need to be converted to File objects
    var dataFolder = new Folder(generated_outputs);
    
    // Now you can use dataFolder to find your JSONs
    var dataFilePath = dataFolder + "/temp.txt";
    var picFilePath = dataFolder + "/temp.png";
    if (enable_log) {
        var LogFilePath = dataFolder + "/log_js.log";
    }
} else {
    alert("Error: GEN_OUTPUT_DIR environment variable not found.");
}



var CARD_WIDTH  = 1080;
var BOTTOM = 1245.55+76.72;
var MIDDLE = 537.14+-51.06;
var LEFT = 33;
var RIGHT = 1080-33;
var TOP = 91.87;
var MAX_NAME_WIDTH = 482; //pixels
var MAX_STATE_WIDTH = 342-49; //pixels
var MAX_ISSUE_WIDTH = 450; //pixels -- wrap width for top issues (JSX measures against this).
                           //Same px space as MAX_NAME_WIDTH(482)/donor box(450). TUNE to the
                           //real top-issues column width.

var NAME_SIZE = 15.72;
var STATE_SIZE = 10.24;


/**
 * Appends a message to the temporary log file.
 * @param {string} message - The message to write.
 */
function log(message) {
    if (enable_log) {
        var logFile = new File(LogFilePath);
        try {
            // Open the file for appending ('a')
            logFile.open('a'); 
            logFile.seek(0, 2); // Move to the end of the file
            logFile.writeln((new Date().toLocaleTimeString()) + ": " + message);
            logFile.close();
        } catch (e) {
            // If file writing fails, at least use the default alert
            alert("LOGGING ERROR: Could not write to log file. " + e.message);
        }
    }
}


///////////// FORMATTING SECTION ///////////////////////



function add_photo(photo_layer, photo_path){

    if (photo_layer.kind != LayerKind.SMARTOBJECT) {
            throw new Error("ERROR: Layer '" + photo_layer + "' is not a Smart Object.");
        }

    var imageFilePath = new File(photo_path); 
    doc.activeLayer = photo_layer;

    //
    var photo_dims = photo_layer.bounds;
        
    // If file exists, replace it.
    if (imageFilePath.exists) {
        var desc3 = new ActionDescriptor();
        desc3.putPath(charIDToTypeID("null"), imageFilePath);
        desc3.putInteger(charIDToTypeID("PgNm"), 1);
        executeAction(stringIDToTypeID("placedLayerReplaceContents"), desc3, DialogModes.NO);
        //reset the name to "photo" for iterating
        photo_layer.name = "photo";

        //alert("Image placed successfully!");
    } else {
        alert("Error: Image file not found at " + imageFilePath.fsName);
    }

    //Now put it back to original dimensions
    scale_photo_down(photo_dims, photo_layer);
        
}

function scale_photo_down(good_bounds, layer) {

    var bad_bounds = layer.bounds;

    var good_w = good_bounds[2].value - good_bounds[0].value;

    var bad_w = bad_bounds[2].value - bad_bounds[0].value;

    //scale image down to original dimensions
    var scale_factor = (good_w / bad_w ) * 100;
    var idTrnf = charIDToTypeID( "Trnf" ); 
    var desc = new ActionDescriptor();
    
    var idnull = charIDToTypeID( "null" );
    var ref = new ActionReference();
    var idLyr = charIDToTypeID( "Lyr " );
    // set current target to current layer
    ref.putEnumerated( idLyr, charIDToTypeID( "Ordn" ), charIDToTypeID( "Trgt" ) );
    desc.putReference( idnull, ref ); //standard to put reference object under null reference


    desc.putUnitDouble( charIDToTypeID( "Wdth" ), charIDToTypeID( "#Prc" ), scale_factor ); 
    desc.putUnitDouble( charIDToTypeID( "Hght" ), charIDToTypeID( "#Prc" ), scale_factor ); 
    
    executeAction( idTrnf, desc, DialogModes.NO );


}

function center(layer_to_be_centered, bound1, bound2, axis) {
    /**
     * given two layers, center between the 2
     * layer1 should be the leftmost/topmost layer depending on axis
     * axis = 0: vertical alignment
     * axis = 1: horizontal alignment
     */
    if (axis == 0) {
        var y = layer_to_be_centered.bounds[1].value;
        var h_of_layer = layer_to_be_centered.bounds[3].value - layer_to_be_centered.bounds[1].value;
        var h_of_space = bound2 - bound1;
        var target = ((h_of_space -  h_of_layer) / 2 ) + bound1;

        //translate from current position to splitting the top and bottom bound
        //shift current_top - 
        if (h_of_space > h_of_layer) {
            layer_to_be_centered.translate(0, target - y);
            log("Moved "+ layer_to_be_centered.name + " vertically  " + (target - y))

        }
        else {
            log ("Failed to move layer "+ layer_to_be_centered.name)
            //alert("height of text box is bigger than the allotted space");
        }
        
    }
    else {
        var x = layer_to_be_centered.bounds[0].value;
        var w_of_layer = layer_to_be_centered.bounds[2].value - layer_to_be_centered.bounds[0].value;
        var w_of_space = bound2 - bound1;
        var target = ((w_of_space -  w_of_layer) / 2 ) + bound1;

        layer_to_be_centered.translate(target - x,0);
        log("Moved "+ layer_to_be_centered.name + " horizontally " + (target - x))

    }

}


//////////////// CARD SPECIFIC FORMATTING //////////////////////////



function resize_text(text_layer, start_font_size, max_width) {
    /**
     * Resize a font if too big.
     * Currently used for name and state.
     */
    text_layer.textItem.leading = 12;
    var layer_w = text_layer.bounds[2] - text_layer.bounds[0];
    log("checking resize: " + layer_w + " to " + max_width);
    if (layer_w > max_width) {

        var new_font_size = max_width * start_font_size / layer_w;
        var newUnit = "px"; // Can be "pt", "px", "in", "cm", "pica"
        text_layer.textItem.size = new UnitValue(new_font_size, newUnit);
        log("Resized " + text_layer + " from " + start_font_size + " to " + new_font_size);
        return true;

    }
    else {
        return false;
    }

}




///////////// WRITING SECTION ///////////////////////


function write(layer, text){
    //1. if \r present in text, split by \r and turn into a list. 
    // then combine the list elements by \r again.
    //2. otherwise, just add the text to the layer
    var addme = "";
    layer.textItem.leading = 7;

    if (text.indexOf("||BREAK||") !== -1) {
        log("||BREAK|| found in " + text);
        var snippets = text.split("||BREAK||");
        addme = snippets.join("\r");
        log("Adding: "+addme);
        layer.textItem.contents = addme;
    }
    else {
        log("No ||BREAK|| present in " + text);
        layer.textItem.contents = text;
    }
}





function getTextLayerScale(layer) {
    /**
     * Read a type layer's baked-in transform scale (xx / yy of its matrix).
     *
     * textItem.width / firstLineIndent / size are all in the layer's PRE-transform
     * space. If the template scaled the type layer (ours carries ~4.167x, == doc
     * resolution / 72), the on-canvas size is value * scale. Read the real scale so
     * callers can pass true canvas-pixel values and divide them back out.
     *
     * Returns {x, y}; defaults to {1, 1} if the layer has no transform.
     */
    try {
        var ref = new ActionReference();
        ref.putProperty(charIDToTypeID("Prpr"), stringIDToTypeID("textKey"));
        ref.putIdentifier(charIDToTypeID("Lyr "), layer.id);
        var tk = executeActionGet(ref).getObjectValue(stringIDToTypeID("textKey"));
        if (tk.hasKey(stringIDToTypeID("transform"))) {
            var t = tk.getObjectValue(stringIDToTypeID("transform"));
            return { x: t.getDouble(stringIDToTypeID("xx")),
                     y: t.getDouble(stringIDToTypeID("yy")) };
        }
    } catch (e) {
        log("getTextLayerScale failed, defaulting to 1: " + e.message);
    }
    return { x: 1, y: 1 };
}



function save_file_as_png_export(save_file_path, doc) {
    var savePath = new File(save_file_path);

    // 1. Create the Export options object
    var exportOptions = new ExportOptionsSaveForWeb();
    
    // 2. Set the necessary parameters
    exportOptions.format = SaveDocumentType.PNG; // Explicitly set format to PNG
    exportOptions.PNG8 = false; // False = PNG-24 (better quality, transparency)
    exportOptions.transparency = true; // Preserve transparency
    exportOptions.interlaced = false;
    exportOptions.quality = 100; // Ignored for PNG, but good practice

    // 3. Execute the export command
    // ExportType.SAVEFORWEB means it will automatically flatten the image
    doc.exportDocument(savePath, ExportType.SAVEFORWEB, exportOptions);

    alert("Document exported as PNG-24: " + savePath.fsName);


}

/////////////////////// TEXT EDITING /////////////////////////////

function state_and_photo(photocard_layer, rep_info) {
    ///////////////////////////////////////////////////////////
    // STATE AND PHOTO CARD LAYER
    //////////////////////////////////////////////////////////
    var state_layer = photocard_layer.layers[0];
    var name_layer = photocard_layer.layers[1];
    var photo_layer = photocard_layer.layers.getByName("Photo").layers.getByName("photo");
    //resize_text(name_and_info_layer.layers[0], NAME_SIZE, MAX_NAME_WIDTH);

    var chamber = rep_info["chamber_line"].split(" ")[0];
    var name = rep_info['name_line'].split("||BREAK||").join(" ");
    write(state_layer, chamber + " - " +rep_info["state"]);
    write(name_layer, name);
    //var resized = resize_text(state_layer, STATE_SIZE, MAX_STATE_WIDTH);
    //if (resized) {
        //also recenter the state if resized
    //    center(state_layer, photo_layer.bounds[0].value, photo_layer.bounds[2].value, 1)
    //}
    //log("Photo layer name and size before replacing photo: " + photo_layer.name + ", " + photo_layer.bounds);
    center(name_layer, photo_layer.bounds[0].value, photo_layer.bounds[2].value, 1);
    add_photo(photo_layer, picFilePath);
    //log("Photo layer name and size after replacing photo: " + photo_layer.name + ", " + photo_layer.bounds);
}



/**
 * Saves the active document with a new name in the same directory as the original.
 * @param {string} newName - The desired name (e.g., "Student_John_Doe.psd")
 */
function saveAsNewFile(newPath) {

    var outputFile = new File(newPath);

    // 2. Define Photoshop Save Options
    var psdOptions = new PhotoshopSaveOptions();
    psdOptions.layers = true; // Keep your layers intact
    psdOptions.embedColorProfile = true;
    psdOptions.annotations = true;
    psdOptions.alphaChannels = true;

    // 3. Execute the Save As command
    // Set 'asCopy' to true if you want to keep the original open
    doc.saveAs(outputFile, psdOptions, false, Extension.LOWERCASE);
    
    // alert("File saved to: " + outputFile.fsName);
}


//////////////////////////////////////////////////////////////

//this should load in dataFilePath which creates a var rep_info
$.evalFile(dataFilePath);

// The template is opened by the caller (main.js reads rep_info.template_path
// from temp.txt and opens it; run_jsx.py opens the CLI template) BEFORE this
// script runs, so it's already the active document -- same as
// fill_card_back_nosocial_template.jsx. We no longer open it here.
if (app.documents.length > 0) {
    var doc = app.activeDocument;
    app.preferences.rulerUnits = Units.PIXELS;

    var toplayer = doc.layers[0]; //Republican-House_Senate_Gov-Social
    //var toplayer = toplayer.layers[0]; //MASTER FOLDER

    var photocard_layer = toplayer.layers.getByName("PHOTO CARD");
    state_and_photo(photocard_layer, rep_info);




    SaveOptions.DONOTSAVECHANGES;
    // Optional save-path override via arguments[1] -- the "Gen Manual Card" flow
    // passes <name>_card_front.psd so it doesn't collide with the social
    // <name>_card.psd. Falls back to temp.txt's file_save_path otherwise.
    var save_path = (arguments.length > 1 && arguments[1]) ? arguments[1] : rep_info["file_save_path"];
    saveAsNewFile(save_path);

    //save_file_as_png_export(file_save_path, doc);
    //doc.save();
    //alert("SUCCESS");



} else {
    // Headless: don't alert() (modal dialogs throw). No open document means the
    // caller didn't open the template PSD before running this script.
    throw new Error("No document open: caller must open the template PSD before running this script.");
}

