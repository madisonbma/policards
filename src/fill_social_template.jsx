// Check if Photoshop is running
#target photoshop
var dataFilePath = "C:\\Users\\Owner\\policards\\src\\generated_outputs\\temp.txt";
var picFilePath = "C:\\Users\\Owner\\policards\\src\\generated_outputs\\temp.png";
var LogFilePath = "C:\\Users\\Owner\\policards\\src\\generated_outputs\\log_js.log";
var CARD_WIDTH  = 1080;



/**
 * Appends a message to the temporary log file.
 * @param {string} message - The message to write.
 */
function log(message) {
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

function move_age(name_info_layer) {
    /** Push the age blocks to be after the Birthplace block
     * Will need to get end dims of birthplace, and offset Age accordingly
     * Then get dims of Age block, use this fixed parameter to offset the actual
     * value of the age block
     */
    //The 3 layers we're working with
    var birthplace_layer = name_info_layer.layers[6];
    var age_layer = name_info_layer.layers[4];
    var age_var_layer = name_info_layer.layers[5];
    age_var_layer.textItem.contents = age_line;   


    //get end bounds so we can translate from here
    var end_of_birthplace = birthplace_layer.bounds[2].value;
    var age_x0 = age_layer.bounds[0].value;

    //get width of age block so we can center it
    var age_width = age_var_layer.bounds[2].value - age_x0;
    var width_to_center = CARD_WIDTH - end_of_birthplace;

    var offset_to_center = (width_to_center - age_width ) / 2;

    //age_x1 = end_of_birthplace + 10
    //shift_by = age_x1 - age_x0
    //shift_by =  end_of_birthplace - age_x0 + 10
    //
    var offset = end_of_birthplace + offset_to_center - age_x0;
    age_layer.translate(offset, 0);
    age_var_layer.translate(offset, 0);



}

//MAX WIDTHS:
/**
 *  state = 253 * RESIZE
 *  name_line = 466 * WRAPAROUND
 *  chamber_line = no need?
 *  reelection_line = no need?
 *  born_age_line = 600 * no need?
 *  education_line = 600 *WRAPAROUND by entry
 *  vote_with_party_percentile = no need
 *  vote_with_party_text = no need
 *  tenure_percentile = no need
 *  tenure_percentile_formatted = no need
 */


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

function write_bulleted_list(layer, text){
    //1. if \r present in text, split by \r and turn into a list. 
    // then combine the list elements by \r again.
    //2. otherwise, just add the text to the layer
    var addme = "";
    var bullet = String.fromCharCode(8226);
    layer.textItem.leading = 8;


    if (text.indexOf("||BREAK||") !== -1) {
        log("||BREAK|| found in " + text);
        var snippets = text.split("||BREAK||");

        var bulletizedLines = [];
        // 2. Loop through the subcomponents
        for (var i = 0; i < snippets.length; i++) {
            var line = snippets[i]; 
            
            // 3. Skip empty lines that might result from splitting (e.g., "A,,B")
            if (line.length > 0) {
                // 4. Add the bullet and a space to the front
                bulletizedLines.push(bullet + line);
            }
        }
    
        addme = bulletizedLines.join("\r"); 
        log("Adding: "+addme);
        layer.textItem.contents = addme;
        return snippets.length;
    }
    else {
        log("No ||BREAK|| present in " + text);
        addme = bullet + text;
        layer.textItem.contents = addme;
        return 1;
    }
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

function move_stat_tracker(fLayer, percentage) {
    var tracker = fLayer.layers.getByName("Tracker");
    var bar_left = fLayer.layers.getByName("Stat Bar").bounds[0];
    var bar_right = fLayer.layers.getByName("Stat Bar").bounds[2];
    var bar_width = bar_right - bar_left;
    var x1 = tracker.bounds[0]; //left
    var x2 = tracker.bounds[2]; //right
    var tracker_width = x2 - x1; //full width of tracker

    var tracker_center_location = bar_left + (bar_width * (parseFloat(percentage) / 100));

    var tracker_left_new = tracker_center_location - (tracker_width / 2); //where we want the left to go
    //convert to relative to current position
    tracker.translate(tracker_left_new - x1, 0); //move to new location


}



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



function resetSmartObjectTransform() {
    // Action code for Edit > Transform > Scale
    var idTrnf = charIDToTypeID( "Trnf" ); // Transform ID
    var desc = new ActionDescriptor();
    
    var idnull = charIDToTypeID( "null" );
    var ref = new ActionReference();
    var idLyr = charIDToTypeID( "Lyr " );
    
    // set current target to current layer
    ref.putEnumerated( idLyr, charIDToTypeID( "Ordn" ), charIDToTypeID( "Trgt" ) );

    desc.putReference( idnull, ref ); //standard to put reference object under null reference
    
    //now add things to do within the description
    var idFTcs = charIDToTypeID( "FTcs" ); // Type of transform: Free Transform
    var idQCkF = charIDToTypeID( "QCkF" );
    desc.putEnumerated( idFTcs, idQCkF, charIDToTypeID( "LkSg" ) );
    
    // Crucial Step: Set scale to 100% horizontally and vertically
    var idWdth = charIDToTypeID( "Wdth" ); // Width
    var idPrc = charIDToTypeID( "#Prc" ); // Percent unit
    desc.putUnitDouble( idWdth, idPrc, 100.000000 );
    
    var idHght = charIDToTypeID( "Hght" ); // Height
    desc.putUnitDouble( idHght, idPrc, 100.000000 );

    // Execute the transform action
    executeAction( idTrnf, desc, DialogModes.NO ); 
}

function format_stat_bars(statbar_layer) {
    ////////////////////////////////////////////////////////////
    // New layer for stat bars 
    ////////////////////////////////////////////////////////////

    // Voting Stat Bar
    var voting_block = statbar_layer.layers.getByName("Voting Record");
    move_stat_tracker(voting_block, vote_with_party_percentile);
    write(voting_block.layers[4], vote_with_party_text);

    //Tenure Stat Bar
    var tenure_block = statbar_layer.layers.getByName("Tenure");
    move_stat_tracker(tenure_block, tenure_percentile);

    write(tenure_block.layers.getByName("Text").layers[3], tenure_percentile_formatted);
    write(tenure_block.layers.getByName("Text").layers[1], max_tenure);

    //Text below stat bars
    write(statbar_layer.layers[2], avg_vote_text);
}

function state_and_photo(photocard_layer) {
    ///////////////////////////////////////////////////////////
    // STATE AND PHOTO CARD LAYER
    //////////////////////////////////////////////////////////
    var state_layer = photocard_layer.layers[0];
    var photo_layer = photocard_layer.layers.getByName("Photo").layers.getByName("photo");
    write(state_layer, state);

    log("Photo layer name and size before replacing photo: " + photo_layer.name + ", " + photo_layer.bounds);

    add_photo(photo_layer, picFilePath);
    log("Photo layer name and size after replacing photo: " + photo_layer.name + ", " + photo_layer.bounds);
}

function raise_bio_section(toplayer) {
    /**
     * When the education section is 2+, raise everything from the red bar to education up by 8.
     */
    //layers to raise: Line 1, text sections 2:9
    var layer = toplayer.layers.getByName("Divider Lines").layers.getByName("Line 1");
    layer.translate(0,-8)
    for (var i = 2; i <= 9; i++) {
        layer = toplayer.layers.getByName("NAME+INFO ").layers[i];
        layer.translate(0,-8);

    }

}



function name_and_title(name_and_info_layer) {
    /**
     * Adds the name and title information. 
     * Layer order for newsletter template:
     * <Name>
     * <CONGRESS | GOVERNOR>
     * <chamber>
     * <XXXX-XXXX | Up for re-election XXXX>
     * AGE:
     * <age>
     * <birthplace>
     * BORN: 
     * EDUCATION:
     * <education_list>
     */

    //for name, need to change the default line spacing

    write(name_and_info_layer.layers[0], name_line);
    name_and_info_layer.layers[0].textItem.leading = 12;

    write(name_and_info_layer.layers[1], title_line);
    write(name_and_info_layer.layers[2], chamber_line);
    write(name_and_info_layer.layers[3], reelection_line);

    write(name_and_info_layer.layers[6], birthplace_line);


    move_age(name_and_info_layer);

    education_size = write_bulleted_list(name_and_info_layer.layers[9], education_line);
    return education_size;
}

try {
    /*
    temp contents:
    NAME
    House Representative OR Senator OR Governor
    2025-Present | Up for re-election in 20XX
    BORN: City, State    AGE: XX
    EDUCATION: School 1, School 2*/
    var datafile = new File(dataFilePath);
    datafile.open('r');

    var state = datafile.readln();
    var name_line = datafile.readln();
    var title_line = datafile.readln();
    var chamber_line = datafile.readln();
    var reelection_line = datafile.readln();
    var birthplace_line = datafile.readln();
    var age_line = datafile.readln();
    var education_line = datafile.readln();
    var vote_with_party_percentile = parseFloat(datafile.readln());
    var vote_with_party_text = datafile.readln();
    var avg_vote_text = datafile.readln();
    var tenure_percentile = parseFloat(datafile.readln());
    var tenure_percentile_formatted = datafile.readln();
    var max_tenure = datafile.readln();
    var file_save_path = datafile.readln();

    datafile.close();
} catch (e) {
    alert("Error reading data file: " + e.toString());
}


//////////////////////////////////////////////////////////////


if (app.documents.length > 0) {
    // Get the active document (the PSD file you want to edit)
    var doc = app.activeDocument;
    var toplayer = doc.layers[0]; //Republican-House_Senate_Gov-Social
    var toplayer = toplayer.layers[0]; //MASTER FOLDER
    var layerNames = [];


    var photocard_layer = toplayer.layers.getByName("PHOTO CARD");
    state_and_photo(photocard_layer);

    var name_and_info_layer = toplayer.layers.getByName("NAME+INFO ");
    name_and_title(name_and_info_layer);
    if (education_size > 1) {
        raise_bio_section(toplayer);
    }


    var statbar_layer = toplayer.layers.getByName("Stat Bars");
    format_stat_bars(statbar_layer);


    SaveOptions.DONOTSAVECHANGES;
    //save_file_as_png_export(file_save_path, doc);
    //doc.save();
    alert("SUCCESS");
} else {
    alert("ERROR: No document is open.");
}

