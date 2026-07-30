// Check if Photoshop is running
#target photoshop


// run_jsx.py drives Photoshop over COM and passes the outputs dir as the first
// script argument (app.DoJavaScriptFile(script, [dir], ...)), so it arrives as
// arguments[0]. $.getenv is only a fallback for other launch methods.
// The typeof guard is required, not cosmetic: macOS `do javascript` provides no
// `arguments` at all, and reading it bare is a ReferenceError that surfaces as an
// untraceable Photoshop error 8800. Precedence is unchanged -- arguments still win
// whenever they exist.
var generated_outputs = (typeof arguments !== "undefined" && arguments.length ? arguments[0] : null)
    || $.getenv("GEN_OUTPUT_DIR");
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
    // Don't alert() -- modal dialogs throw when Photoshop runs this headless.
    generated_outputs = null;
}



var CARD_WIDTH  = 788;
var BOTTOM = 104+932;
var MIDDLE = 78+235+10;
var LEFT = 57;
var RIGHT = 57+675;
var TOP = 78;
//var MAX_NAME_WIDTH = 520; //pixels
var MAX_ISSUE_WIDTH = 450; //pixels -- wrap width for top issues (JSX measures against this).
                           //Same px space as MAX_NAME_WIDTH(482)/donor box(450). TUNE to the
                           //real top-issues column width.

var NAME_SIZE = 15.72;


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

function realign_horizontally(align_to_this_layer, move_layer) {
    //move top donors to align with the new placement of top issues
    var new_y = align_to_this_layer.bounds[1].value;
    var move = new_y - move_layer.bounds[1].value;
    move_layer.translate(0, move);

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


function normalize_text_box_size(text_layer) {
    if (text_layer.kind !== LayerKind.TEXT) {
        alert("Please select a Text Layer first.");
        return;
    }

    var textItem = text_layer.textItem;

    // We can only shrink a bounding box if it's currently Paragraph (Area) Text
    if (textItem.kind === TextType.PARAGRAPHTEXT) {
        
        // Step 1: Temporarily convert to Point Text to collapse the bounding box
        textItem.kind = TextType.POINTTEXT;

        // Step 2: Grab the exact visual boundaries of the rendered text.
        // bounds are in canvas/document px (POST-transform).
        var bounds = text_layer.bounds;
        var exactWidth = bounds[2] - bounds[0];
        var exactHeight = bounds[3] - bounds[1];
        var scale = getTextLayerScale(text_layer);

        // Step 3: Convert it back to Paragraph Text
        textItem.kind = TextType.PARAGRAPHTEXT;

        // Step 4: Re-apply the exact dimensions to the text container.
        // textItem.width/height live in the layer's PRE-transform space, so divide the
        // canvas-px bounds back out by the layer's baked-in scale (~4.167x). Without this
        // the box renders scale-times bigger than the text.
        textItem.width = new UnitValue(exactWidth / scale.x, "px");
        textItem.height = new UnitValue(exactHeight / scale.y, "px");
        
    } else {
        alert("The selected layer is already Point Text and has no bounding box to shrink.");
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

function reformat_top_section(name_and_info_layer, lines_layer) {
    /**
     * Check how long the name is, and how long the education is.
     * Name is 1:
     *  enable autospace function that's prebuilt?
     * Name is 2:
     *  education is 1: do nothing
     *  education is 2: enable autospace function?
     *  education is 3: ?
     * 
     * move age, age_value, and birthplace to even with BORN
     */

    var spacing_list = [
        name_and_info_layer.layers[0], name_and_info_layer.layers[1],
        lines_layer.layers.getByName("Line 1"), name_and_info_layer.layers[2],
        name_and_info_layer.layers[7],
        name_and_info_layer.layers[8], name_and_info_layer.layers[9]
    ];


    distribute_layers(spacing_list, TOP, MIDDLE, 0);
    realign_horizontally(name_and_info_layer.layers[2], name_and_info_layer.layers[3]);

    realign_horizontally(name_and_info_layer.layers[7], name_and_info_layer.layers[4]);
    realign_horizontally(name_and_info_layer.layers[7], name_and_info_layer.layers[5]);
    realign_horizontally(name_and_info_layer.layers[7], name_and_info_layer.layers[6]);

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


///////////// WRITING SECTION ///////////////////////


function write(layer, text){
    //1. if \r present in text, split by \r and turn into a list. 
    // then combine the list elements by \r again.
    //2. otherwise, just add the text to the layer
    var addme = "";
    layer.textItem.leading = 5.5;
    var temp_text = text.split("||BREAK||").join(" ");
    layer.textItem.contents = temp_text;
    /*if (text.indexOf("||BREAK||") !== -1) {
        var snippets = text.split("||BREAK||");
        addme = snippets.join("\r");
        log("Adding: "+addme);
        layer.textItem.contents = addme;
    }
    else {
        layer.textItem.contents = text;
    }*/
}

function write_temp(text) {
    var addme = "";

    if (text.indexOf("||BREAK||") !== -1) {
        log("||BREAK|| found in " + text);
        var snippets = text.split("||BREAK||");
        addme = snippets.join("\r");
        log("Adding: "+addme);
        return addme;
    }
    else {
        log("No ||BREAK|| present in " + text);
        return text;
    }
}



function write_bulleted_list(layer, text_in, resize) {
    /**
     * Take a list in and parse for delimiters.
     * ||BREAK_DOT||: standard delimiter. each BREAK_DOT gets a bullet and its own line
     *   -> ||BREAK||: if present in BREAK_DOT delimiting, line too long and ran over. 
     *                 start a new line, indent by 4 spaces
     *   -> ||BREAK_SUBDOT||: for committees specifically. 
     *                        add 4 spaces before, don't add the bullet bc already there
     */

    var text = text_in.split("||BREAK||").join(" ");

    if (resize) {
        layer.textItem.kind = TextType.POINTTEXT; 
        var bounds = layer.bounds;
        var exactWidth = bounds[2] - bounds[0];
        var exactHeight = bounds[3] - bounds[1];
        var scale = getTextLayerScale(layer);
        log("Starting bounds: " + exactWidth+ "x"+exactHeight);
    }

    layer.textItem.leading = 5.5;
    layer.textItem.kind = TextType.PARAGRAPHTEXT;

    //start of bullet point
    if (text.indexOf("||BREAK_DOT||") !== -1) {
        var snippets = text.split("||BREAK_DOT||");

        var bulletizedLines = [];
        // 2. Loop through the subcomponents.
        //check for BREAK to add indent, otherwise print normally with bullet
        for (var i = 0; i < snippets.length; i++) {
            var line = snippets[i];
            // 3. Skip empty lines that might result from splitting (e.g., "A,,B")
            if (line.length === 0) {
                continue;
            }
            // ||BREAK_SUBDOT|| -> start a new line and indent it with a tab, the
            // same as pressing Tab in the type tool (committees: the bullet is
            // already in the text, so don't add one).
            if (line.indexOf("||BREAK_SUBDOT||") !== -1) {
                var subparts = line.split("||BREAK_SUBDOT||");
                for (var k = 0; k < subparts.length; k++) {
                    if (subparts[k].length === 0) {
                        continue;
                    }
                    // first subpart continues its line; each later one is a new tab-indented line
                    bulletizedLines.push(k === 0 ? subparts[k] : "--" + subparts[k]);
                }
            }
            else {
                bulletizedLines.push(line);
            }
        }
    

        layer.textItem.contents = bulletizedLines.join("\r");
    }
    else {
        log("No ||BREAK|| present in " + text);
        layer.textItem.contents = text;
    }

    if (resize) {
        // Step 3: Convert it back to Paragraph Text
       // layer.textItem.kind = TextType.PARAGRAPHTEXT;

        // Step 4: Re-apply the exact dimensions to the text container.
        // textItem.width/height live in the layer's PRE-transform space, so divide the
        // canvas-px bounds back out by the layer's baked-in scale (~4.167x). Without this
        // the box renders scale-times bigger than the text.
        log("Scale by "+ scale.x + "/"+ scale.y)
        log("Final bounds: "+ (exactWidth / scale.x) + "x" +( exactWidth / scale.y));

        layer.textItem.width = new UnitValue(exactWidth / scale.x, "px");
        layer.textItem.height = new UnitValue(exactHeight / scale.y, "px");
       
    }
}

function write_bulleted_list_bckup(layer, text_in, resize) {
    /**
     * Take a list in and parse for delimiters.
     * ||BREAK_DOT||: standard delimiter. each BREAK_DOT gets a bullet and its own line
     *   -> ||BREAK||: if present in BREAK_DOT delimiting, line too long and ran over. 
     *                 start a new line, indent by 4 spaces
     *   -> ||BREAK_SUBDOT||: for committees specifically. 
     *                        add 4 spaces before, don't add the bullet bc already there
     */

    var text = text_in.split("||BREAK||").join(" ");

    if (resize) {
        layer.textItem.kind = TextType.POINTTEXT; 
        var bounds = layer.bounds;
        var exactWidth = bounds[2] - bounds[0];
        var exactHeight = bounds[3] - bounds[1];
        var scale = getTextLayerScale(layer);
        log("Starting bounds: " + exactWidth+ "x"+exactHeight);
    }

    var addme = "";
    //var bullet = String.fromCharCode(8226);
    var bullet = "";
    layer.textItem.leading = 5.5;
    layer.textItem.kind = TextType.PARAGRAPHTEXT;

    //start of bullet point
    if (text.indexOf("||BREAK_DOT||") !== -1) {
        var snippets = text.split("||BREAK_DOT||");

        var bulletizedLines = [];
        // 2. Loop through the subcomponents.
        //check for BREAK to add indent, otherwise print normally with bullet
        for (var i = 0; i < snippets.length; i++) {
            var line = snippets[i];
            // the first snippet is the header/title -> no bullet, every later line gets one
            var prefix = (i == 0) ? "" : bullet;
            if (line.indexOf("||BREAK||") !== -1) {
                //if BREAK is present, split and indent
                //this is either a subdot or intermediate line break,
                //both of which are treated the same. add 4 space and return
                var subsnips = line.split("||BREAK||");
                for (var j = 0; j < subsnips.length; j++) {
                    var subline = subsnips[j];

                    //to start, don't indent but include bullet (unless this is the header)
                    if (j == 0) {
                        bulletizedLines.push(prefix + subline);
                    }
                    else if (subline.length > 0) {
                        bulletizedLines.push("    " + subline);
                    }
                }
            }
            else {
                // 3. Skip empty lines that might result from splitting (e.g., "A,,B")
                if (line.length > 0) {
                    // 4. Add the bullet (header gets none) and a space to the front
                    bulletizedLines.push(prefix + line);
                }
            }
        }
    

        layer.textItem.contents = bulletizedLines.join("\r");
    }
    else {
        log("No ||BREAK|| present in " + text);
        layer.textItem.contents = text;
    }

    if (resize) {
        // Step 3: Convert it back to Paragraph Text
       // layer.textItem.kind = TextType.PARAGRAPHTEXT;

        // Step 4: Re-apply the exact dimensions to the text container.
        // textItem.width/height live in the layer's PRE-transform space, so divide the
        // canvas-px bounds back out by the layer's baked-in scale (~4.167x). Without this
        // the box renders scale-times bigger than the text.
        log("Scale by "+ scale.x + "/"+ scale.y)
        log("Final bounds: "+ (exactWidth / scale.x) + "x" +( exactWidth / scale.y));

        layer.textItem.width = new UnitValue(exactWidth / scale.x, "px");
        layer.textItem.height = new UnitValue(exactHeight / scale.y, "px");
       
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




function shrink_voting_bar(voting_block) {
    var bar_to_shrink = voting_block.layers.getByName('Stat Bar')
    var og_bounds = bar_to_shrink.bounds;
    var shrink = (rep_info['absent_percent']*(og_bounds[2].value-og_bounds[0].value))/2;
    //INCOMPLETE: need to get new dimensions still
    scale_photo_down(rep_info['absent_percent'], bar_to_shrink)


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


    //distribute_layers([statbar_layer.layers[2]], voting_block.layers[4].bounds[3].value, line2.bounds[1].value, 0);
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
    //resize_text(name_and_info_layer.layers[0], NAME_SIZE, MAX_NAME_WIDTH);

    write(name_and_info_layer.layers[1], rep_info["chamber_line"]);
    //write(name_and_info_layer.layers[2], rep_info["chamber_line"]);
    write(name_and_info_layer.layers[3], rep_info["reelection_line"]);

    write(name_and_info_layer.layers[6], rep_info["birthplace_line"]);


    move_age(name_and_info_layer, rep_info);

    write_bulleted_list(name_and_info_layer.layers[9], rep_info["education_line"], false);
    const ed_length = rep_info['education_line'].split("||BREAK_DOT||").length - 1;

    name_and_info_layer.layers[9].textItem.height = new UnitValue(ed_length*20, "px")
}

function fill_committees(committee_layer, rep_info) {
    log("COMMITTEES")
    write_bulleted_list(committee_layer.layers[0], rep_info['committee_list'], false);


}

function fill_jobs(job_layer, rep_info) {
    log("JOBS")
    write_bulleted_list(job_layer.layers[0], rep_info['work_history'], false);
    center(job_layer.layers[1], top_issues_layer.bounds[0].value, top_issues_layer.bounds[2].value, 1)


}

function fill_top_issues(top_issues_layer, rep_info) {
    log("TOP ISSUES")
    top_issues = top_issues_layer.layers[0]
    write_bulleted_list(top_issues_layer.layers[0], rep_info['top_issues'], false);

}



function fill_top_donors(top_donors_layer, rep_info) {
    log("TOP DONORS")
    var donor_title_layer = top_donors_layer.layers[0];
    var donor_overview_layer = top_donors_layer.layers[1];
    var donor_text_layer = top_donors_layer.layers[2];

    // Title line, e.g. "DONORS (2025-2026)"
    write(donor_title_layer, rep_info['donor_title']);

    write(donor_overview_layer, rep_info['top_donors_hdr'])
    //addme = write_temp(rep_info['top_donors_hdr'])

    //set width to 300.

    write_bulleted_list(donor_text_layer, rep_info['top_donors'], false);


    /*donor_text_layer.textItem.kind = TextType.POINTTEXT;
    donor_text_layer.textItem.leading = 7;
    donor_text_layer.textItem.contents = lines.join("\r");*/

    // 1. Change kind to PARAGRAPHTEXT to allow automatic wrapping
    //donor_text_layer.textItem.kind = TextType.PARAGRAPHTEXT;
    
    // 2. Set your strict bounding box boundaries (use UnitValue for safety)
    // Adjust these pixel values to perfectly fit your trading card layout dimensions
    //donor_text_layer.textItem.width = new UnitValue(300, "px"); 
    //donor_text_layer.textItem.height = new UnitValue(300, "px");
    //normalize_text_box_size(donor_text_layer);

    // 3. Keep your tight baseline formatting
    //donor_text_layer.textItem.leading = 7;
    //donor_text_layer.textItem.contents = lines.join("\r");
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
    // asCopy = false so the OPEN document becomes the saved card (no leftover
    // modified template with a '*'), matching fill_social_template.jsx.
    doc.saveAs(outputFile, psdOptions, false, Extension.LOWERCASE);
    
    // alert("File saved to: " + outputFile.fsName);
}


//////////////////////////////////////////////////////////////

// Wrap the whole run so any exception lands in log_js.log (with a line number)
// instead of vanishing behind a bare "exit status 1". NOTE: alert() is not used
// here on purpose -- when Photoshop runs a script headless via `-r`, modal
// dialogs throw, so all diagnostics go to the log file.
try {

//this should load in dataFilePath which creates a var rep_info
$.evalFile(dataFilePath);
log("evalFile OK -- rep_info loaded, documents open: " + app.documents.length);

// The template is passed on the command line to run_jsx.py, which hands it to
// Photoshop as a positional arg. Photoshop opens it BEFORE running this script,
// so it's already the active document. (Photoshop's CLI can't forward the path
// into the script as an argument, so we read it off the open document instead
// of rep_info['template_path'].)
if (app.documents.length > 0) {
    var doc = app.activeDocument;
    app.preferences.rulerUnits = Units.PIXELS;

    var toplayer = doc.layers[0]; //Republican-House_Senate_Gov-Social
    //var toplayer = toplayer.layers[0]; //MASTER FOLDER
    var layerNames = [];
    log("Top layer: " + toplayer.name);

    var lines_layer = toplayer.layers.getByName("Divider Lines");


    var name_and_info_layer = toplayer.layers.getByName("NAME+INFO");
    name_and_title(name_and_info_layer, rep_info);


    var statbar_layer = toplayer.layers.getByName("Stat Bars");
    format_stat_bars(statbar_layer, lines_layer.layers.getByName("Line 2"), rep_info);

    var top_issues_layer = toplayer.layers.getByName("Top Issues");
    var top_donors_layer = toplayer.layers.getByName("Top Donors");

    var job_layer = toplayer.layers.getByName("Recent Jobs");
    var committees_layer = toplayer.layers.getByName("Committees");

    fill_top_issues(top_issues_layer, rep_info);
    fill_top_donors(top_donors_layer, rep_info);
    fill_committees(committees_layer, rep_info);
    fill_jobs(job_layer, rep_info);


    /////// REDO SPACING ////////

    reformat_top_section(name_and_info_layer, lines_layer);



    
    //if top_issues is taller, use that. otherwise use top_donors. then realign to the one you used

    top_issues_h = (top_issues_layer.bounds[3].value - top_issues_layer.bounds[1].value);
    top_donors_h = (top_donors_layer.bounds[3].value - top_donors_layer.bounds[1].value);
    jobs_h = (job_layer.bounds[3].value - job_layer.bounds[1].value);
    committee_h = (committees_layer.bounds[3].value - committees_layer.bounds[1].value);
    
    if (top_donors_h > top_issues_h) {
        var layer2a = top_donors_layer;
        var layer2b = top_issues_layer;
    }
    else {
        var layer2a = top_issues_layer;
        var layer2b = top_donors_layer;
    }
    if (jobs_h > committee_h) {
        var layer1a = job_layer;
        var layer1b = committees_layer;
    } else {
        var layer1a = committees_layer;
        var layer1b = job_layer;
    }

    var layer_list = [
        layer1a, 
        lines_layer.layers.getByName("Line 5"),
        statbar_layer, lines_layer.layers.getByName("Line 2"),
        layer2a
    ];
    distribute_layers(layer_list, MIDDLE, BOTTOM, 0);
    realign_horizontally(layer1a, layer1b);
    realign_horizontally(layer2a, layer2b);
    distribute_layers([top_issues_layer, lines_layer.layers.getByName("Line 4"), top_donors_layer], LEFT, RIGHT, 1)
    distribute_layers([job_layer, lines_layer.layers.getByName("Line 6"), committees_layer], LEFT, RIGHT, 1)
    center(lines_layer.layers.getByName("Line 4"), top_issues_layer.bounds[2].value, top_donors_layer.bounds[0].value, 1)
    center(lines_layer.layers.getByName("Line 6"), job_layer.bounds[2].value, committees_layer.bounds[0].value, 1)
    center(lines_layer.layers.getByName("Line 4"), lines_layer.layers.getByName("Line 2").bounds[2].value, BOTTOM, 0)
    center(lines_layer.layers.getByName("Line 6"), MIDDLE,  lines_layer.layers.getByName("Line 5").bounds[0].value, 0)
    

    SaveOptions.DONOTSAVECHANGES;
    // Optional save-path override via arguments[1] -- the "Gen Manual Card" flow
    // passes <name>_card_back.psd so it doesn't collide with the social
    // <name>_card.psd. Falls back to temp.txt's file_save_path otherwise.
    var save_path = rep_info["file_save_path"]+"_card_back.psd";
    saveAsNewFile(save_path);

    //save_file_as_png_export(file_save_path, doc);
    //doc.save();
    //alert("SUCCESS");



} else {
    log("ERROR: No document is open. Pass the template path to run_jsx.py so Photoshop opens it before running this script.");
}

} catch (e) {
    // Record exactly what failed and where, then re-throw so the process still
    // exits non-zero and run_jsx.py flags it.
    // Re-throw a NEW error carrying the origin: the host (COM / AppleScript) only
    // ever reports the RETHROW site -- i.e. this line -- so re-throwing `e` bare
    // loses the line number that actually matters.
    var where = " (line " + e.line + ", file " + e.fileName + ")";
    log("FATAL: " + e.message + where);
    throw new Error(e.message + where);
}

