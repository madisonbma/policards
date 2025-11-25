// Check if Photoshop is running
#target photoshop
var dataFilePath = "C:\\Users\\Owner\\policards\\src\\generated_outputs\\temp.txt";

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

    var name_line = datafile.readln();
    var chamber_line = datafile.readln();
    var reelection_line = datafile.readln();
    var born_age_line = datafile.readln();
    var education_line = datafile.readln();

    datafile.close();
} catch (e) {
    alert("Error reading data file: " + e.toString());
}



if (app.documents.length > 0) {
    // Get the active document (the PSD file you want to edit)
    var doc = app.activeDocument;
    var toplayer = doc.layers[0]; //Republican-House_Senate_Gov-Social
    var toplayer = toplayer.layers[0]; //MASTER FOLDER
    var layerNames = [];

    var name_and_info_layer = toplayer.layers.getByName("NAME+INFO");
    //[0] is name
    var nameLayer = name_and_info_layer.layers[0];
    nameLayer.textItem.contents = name_line;

    //[1] is house/senate title/governor
    var titleLayer = name_and_info_layer.layers[1];
    titleLayer.textItem.contents = chamber_line;
    //[2] is Born: Chicago, IL        AGE: 34
    var demographics_layer = name_and_info_layer.layers[2];
    demographics_layer.textItem.contents = born_age_line;

    //[3] is house of representatives:  2025-Present | Up for re-election in
    var reelection_layer = name_and_info_layer.layers[3];
    reelection_layer.textItem.contents = reelection_line;
    //[4] is education: • Bachelors, ASU         • Degree, School
    var education_layer = name_and_info_layer.layers[4];
    education_layer.textItem.contents = education_line;
    SaveOptions.DONOTSAVECHANGES;
    //doc.save();
    alert("SUCCESS");
} else {
    alert("ERROR: No document is open.");
}


// Ensure we have a document open

    // Iterate through all layers in the document
    /*
    for (var i = 0; i < name_and_info_layer.layers.length; i++) {
        var textLayer = name_and_info_layer.layers[i];
        if (textLayer.kind == LayerKind.TEXT) {
            var textItem = textLayer.textItem;

            // Get the contents of the text box
            var textContents = textItem.contents;
            alert("Text Contents: " + textContents);

            // Get the position (top-left coordinates) of the text box
            var position = textItem.position; // Returns an array [x, y]
            alert("Text Box Position (x, y): " + position[0] + ", " + position[1]);

            // Get the width and height of the text box
            //var width = textItem.width;
            //var height = textItem.height;
            //alert("Text Box Dimensions (width, height): " + width + ", " + height);

            // You can also modify these properties:
             textItem.contents = "New Name";
            // textItem.position = [100, 50]; // Move the text box
            // textItem.font = "Arial";
            // textItem.size = 24;
        }
        //var currentLayer = name_and_info_layer.layers[i];
        layerNames.push(textLayer.name);
    }*/

    // Display the layer names in an alert
    //alert("Layer Names:\n" + layerNames.join("\n"));
    
    //var textLayer = doc.artLayers.getByName("NAME+INFO"); // Replace "YourTextLayerName" with the actual name of your text layer
    //layer.textItem.contents = "NAME HERE";


    // Move the layer: [Horizontal, Vertical]
    //layer.translate(x_offset, y_offset); 

    // Save the document (overwriting the original)
    // Note: Use SaveOptions.DONOTSAVECHANGES if you want to avoid saving
    //SaveOptions.DONOTSAVECHANGES;
    //doc.save();

    // The script must return a simple value (like true) for your Python/C++ code to read
