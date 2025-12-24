// Check if Photoshop is running
#target photoshop


var rootdir = new File($.fileName);
rootdir = rootdir.parent;
var dataFilePath = rootdir + "/generated_outputs/temp.txt";
var picFilePath = rootdir + "/generated_outputs/temp.png";
var LogFilePath = rootdir + "generated_outputs/log_js.log";


var CARD_WIDTH  = 1080;
var BOTTOM = 1245.55+76.72;
var MIDDLE = 537.14+-51.06;
var LEFT = 33;
var MAX_NAME_WIDTH = 482; //pixels


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
        }
        else {
            alert("height of text box is bigger than the allotted space");
        }
        
    }
    else {
        var x = layer_to_be_centered.bounds[0].value;
        var w_of_layer = layer_to_be_centered.bounds[2].value - layer_to_be_centered.bounds[0].value;
        var w_of_space = bound2 - bound1;
        var target = ((w_of_space -  w_of_layer) / 2 ) + bound1;

        layer_to_be_centered.translate(target - x,0);

    }

}

function move_age(name_info_layer, rep_info) {
    /** Push the age blocks to be after the Birthplace block
     * Will need to get end dims of birthplace, and offset Age accordingly
     * Then get dims of Age block, use this fixed parameter to offset the actual
     * value of the age block
     */
    //The 3 layers we're working with
    var birthplace_layer = name_info_layer.layers[6];
    var age_layer = name_info_layer.layers[4];
    var age_var_layer = name_info_layer.layers[5];
    age_var_layer.textItem.contents = rep_info["age_line"];   


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
    /**
     * Take a list in and parse for delimiters.
     * ||BREAK_DOT||: standard delimiter. each BREAK_DOT gets a bullet and its own line
     *   -> ||BREAK||: if present in BREAK_DOT delimiting, line too long and ran over. 
     *                 start a new line, indent by 4 spaces
     *   -> ||BREAK_SUBDOT||: for committees specifically. 
     *                        add 4 spaces before, don't add the bullet bc already there
     */
    var addme = "";
    var bullet = String.fromCharCode(8226);
    layer.textItem.leading = 7;

    //start of bullet point
    if (text.indexOf("||BREAK_DOT||") !== -1) {
        log("||BREAK_DOT|| found in " + text);
        var snippets = text.split("||BREAK_DOT||");

        var bulletizedLines = [];
        // 2. Loop through the subcomponents.
        //check for BREAK to add indent, otherwise print normally with bullet
        for (var i = 0; i < snippets.length; i++) {
            var line = snippets[i]; 
            if (line.indexOf("||BREAK||") !== -1) {
                //if BREAK is present, split and indent
                //this is either a subdot or intermediate line break,
                //both of which are treated the same. add 4 space and return
                var subsnips = line.split("||BREAK||");
                for (var j = 0; j < subsnips.length; j++) {
                    var subline = subsnips[j];
                    
                    //to start, don't indent but include bullet
                    if (j == 0) {
                        bulletizedLines.push(bullet + subline);
                    }
                    else if (subline.length > 0) {
                        bulletizedLines.push("    " + subline);
                    }
                }
            }
            else {
                // 3. Skip empty lines that might result from splitting (e.g., "A,,B")
                if (line.length > 0) {
                    // 4. Add the bullet and a space to the front
                    bulletizedLines.push(bullet + line);
                }
            }
        }
    
        addme = bulletizedLines.join("\r"); 
        log("Adding: "+addme);
        layer.textItem.contents = addme;
    }
    else {
        log("No ||BREAK|| present in " + text);
        addme = bullet + text;
        layer.textItem.contents = addme;
    }
}


function distribute_layers(layer_list, bound1, bound2, axis) {
/**
 * Given input layers, shift them down and evenly distribute them
 * bound1 is the topmost/leftmost bound
 * bound2 is the bottommost/rightmost bound
 * axis=0 means vertical, axis=1 is horizontal
 */

    var bounds_list = [];
    var current_measurement = 0;
    //go through the layers and get the bounds
    for (var i = 0; i < layer_list.length; i++) {
        bounds_list.push(layer_list[i].bounds);
        if (axis == 0) {
            current_measurement += (layer_list[i].bounds[3].value - layer_list[i].bounds[1].value);
        }
        else {
            current_measurement += (layer_list[i].bounds[2].value - layer_list[i].bounds[0].value);
        }
    }

    var fit_within_this = bound2 - bound1;
    var spacing = (fit_within_this - current_measurement) / (layer_list.length+1);

    log("Spacing: " + spacing + "from " + fit_within_this + "and" + current_measurement);


    // now reformat using the spacing - throw an error if spacing is negative. then we have 
    // too much content, it's impossible to fit
    //bound1 + spacing
    //bound1 + spacing + layer1 + spacing

    var layer_start = bound1;
    for (var j = 0; j < layer_list.length; j++) {
        if (axis == 0) {
            layer_start += spacing;
            layer_list[j].translate(0, layer_start - layer_list[j].bounds[1].value);
            log ("Placing " + layer_list[j] + "at " + layer_start);

            layer_start += (layer_list[j].bounds[3].value - layer_list[j].bounds[1].value);
        }
        else {
            layer_start += spacing;
            layer_list[j].translate(layer_start - layer_list[j].bounds[0].value , 0);
            layer_start += (layer_list[j].bounds[2].value - layer_list[j].bounds[0].value);
        }
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

function format_stat_bars(statbar_layer, line2, rep_info) {
    ////////////////////////////////////////////////////////////
    // New layer for stat bars 
    ////////////////////////////////////////////////////////////

    // Voting Stat Bar
    var voting_block = statbar_layer.layers.getByName("Voting Record");
    move_stat_tracker(voting_block, rep_info["vote_with_party_percentile"]);
    write(voting_block.layers[4], rep_info["vote_with_party_text"]);

    //Tenure Stat Bar
    var tenure_block = statbar_layer.layers.getByName("Tenure");
    move_stat_tracker(tenure_block, rep_info["tenure_percentile"]);

    write(tenure_block.layers.getByName("Text").layers[3], rep_info["tenure_percentile_formatted"]);
    write(tenure_block.layers.getByName("Text").layers[1], rep_info["max_tenure"]);

    //Text below stat bars
    write(statbar_layer.layers[2], rep_info["avg_vote_text"]);


    distribute_layers([statbar_layer.layers[2]], voting_block.layers[4].bounds[3].value, line2.bounds[1].value, 0);
}

function state_and_photo(photocard_layer, rep_info) {
    ///////////////////////////////////////////////////////////
    // STATE AND PHOTO CARD LAYER
    //////////////////////////////////////////////////////////
    var state_layer = photocard_layer.layers[0];
    var photo_layer = photocard_layer.layers.getByName("Photo").layers.getByName("photo");
    write(state_layer, rep_info["state"]);

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


function resize_name(name_layer) {
    /**
     * Check if name is gonna run into the logo
     * If it is, reduce the font size until it won't anymore
     * Also set the line spacing to 12 since might get reset
     * 
     */

    name_layer.textItem.leading = 12;

    var name_w = name_layer.bounds[2] - name_layer.bounds[0];
    if (name_w > MAX_NAME_WIDTH) {
        // need to resize!
        //defaults to 15.72pt. scale
        //name_w / 15.72 = MAX_NAME_WIDTH / ans
        var new_font_size = MAX_NAME_WIDTH * 15.72 / name_w;
        var newUnit = "px"; // Can be "pt", "px", "in", "cm", "pica"
        name_layer.textItem.size = new UnitValue(new_font_size, newUnit);
        log("Resized name from 15.72pt to " + new_font_size);

    }
    //else do nothing
}

function name_and_title(name_and_info_layer, rep_info) {
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

    write(name_and_info_layer.layers[0], rep_info["name_line"]);
    resize_name(name_and_info_layer.layers[0]);

    write(name_and_info_layer.layers[1], rep_info["title_line"]);
    write(name_and_info_layer.layers[2], rep_info["chamber_line"]);
    write(name_and_info_layer.layers[3], rep_info["reelection_line"]);

    write(name_and_info_layer.layers[6], rep_info["birthplace_line"]);


    move_age(name_and_info_layer, rep_info);

    education_size = write_bulleted_list(name_and_info_layer.layers[9], rep_info["education_line"]);
    return education_size;
}


/////////////////////////////
// Load in the temp input  //
/////////////////////////////

function load_temp_dict() {
    try {

        var datafile = new File(dataFilePath);
        datafile.open('r');

        var dict = {};
        dict["state"] = datafile.readln();
        dict["name_line"] = datafile.readln();
        dict["title_line"] = datafile.readln();
        dict["chamber_line"] = datafile.readln();
        dict["reelection_line"] = datafile.readln();
        dict["birthplace_line"] = datafile.readln();
        dict["age_line"] = datafile.readln();
        dict["education_line"] = datafile.readln();
        dict["vote_with_party_percentile"] = parseFloat(datafile.readln());
        dict["vote_with_party_text"] = datafile.readln();
        dict["avg_vote_text"] = datafile.readln();
        dict["tenure_percentile"] = parseFloat(datafile.readln());
        dict["tenure_percentile_formatted"] = datafile.readln();
        dict["max_tenure"] = datafile.readln();
        dict["summary_stats"] = datafile.readln();
        dict["committee_list"] = datafile.readln();
        dict["work_history"] = datafile.readln();
        dict["bonus_header"] = datafile.readln();
        dict["bonus_text"] = datafile.readln();
        dict["file_save_path"] = datafile.readln();
        dict["template_path"] = datafile.readln();

        datafile.close();
        return dict;


    } catch (e) {
        alert("Error reading data file: " + e.toString());
    }
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
//Load in the variables I want
var rep_info = load_temp_dict();

//open the template designated in temp.txt
var template_file = new File(rep_info['template_path']);

//

if (template_file.exists) {
    // 1. OPEN the file as a Photoshop Document
    var doc = app.open(template_file); 
    
    // 2. MAKE it the active document (just to be safe)
    app.activeDocument = doc;
    app.preferences.rulerUnits = Units.PIXELS;

    var toplayer = doc.layers[0]; //Republican-House_Senate_Gov-Social
    var toplayer = toplayer.layers[0]; //MASTER FOLDER
    var layerNames = [];

    var lines_layer = toplayer.layers.getByName("Divider Lines");
    var social_media_layer = toplayer.layers.getByName("Social");

    var photocard_layer = toplayer.layers.getByName("PHOTO CARD");
    state_and_photo(photocard_layer, rep_info);

    var name_and_info_layer = toplayer.layers.getByName("NAME+INFO ");
    name_and_title(name_and_info_layer, rep_info);
    if (education_size > 1) {
        raise_bio_section(toplayer);
    }



    var statbar_layer = toplayer.layers.getByName("Stat Bars");
    format_stat_bars(statbar_layer, lines_layer.layers.getByName("Line 2"), rep_info);




    var top_issues_layer = toplayer.layers.getByName("Top Issues");

    var layer_list = [
        statbar_layer, lines_layer.layers.getByName("Line 2"),
        top_issues_layer, lines_layer.layers.getByName("Line 3"),
        social_media_layer
    ];

    distribute_layers(layer_list, MIDDLE, BOTTOM, 0);
    //move top donors to align with the new placement of top issues
    var top_donors_layer = toplayer.layers.getByName("Top Donors");
    var new_y = top_issues_layer.bounds[1].value;
    var move = new_y - top_donors_layer.bounds[1].value;
    top_donors_layer.translate(0, move);
    lines_layer.layers.getByName("Line 4").translate(0, move);


    SaveOptions.DONOTSAVECHANGES;
    saveAsNewFile(rep_info["file_save_path"]);

    //save_file_as_png_export(file_save_path, doc);
    //doc.save();
    alert("SUCCESS");



} else {
    alert("File does not exist at path: " + template_file);
}

