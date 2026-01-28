import joblib
import json
import os
import re


def load_model():
    # 1. Path to your saved model file
    model_path = 'bioguide_model.pkl'

    # 2. Check if the file exists before loading
    if os.path.exists(model_path):
        # This one line reloads the entire "Pipeline" (Vectorizer + Brain)
        model = joblib.load(model_path)
        print("Model loaded successfully!")
    else:
        print(f"Error: {model_path} not found. Did you run the trainer yet?")

    return model



def classify_with_safety(model, phrase, threshold=0.7):
    # predict_proba returns a list of probabilities for each category
    probs = model.predict_proba([phrase])[0]
    
    # Get the highest probability and the index of that category
    max_prob = max(probs)
    category_index = probs.argmax()
    category = model.classes_[category_index]

    # If the model is 'guessing' (below threshold), move it to Unused
    if max_prob < threshold:
        return "unused"
    
    return str(category)




def test_model(model):
    input_file = "generated_outputs/debug_bioguide.log"
    with open(input_file, 'r') as file:
        list_of_congressmen = json.load(file)

    test_data = {}
    for rep_info in list_of_congressmen:
        uncaptured = rep_info.get("uncaptured")
        if len(uncaptured) != 0:
            for item in uncaptured:
                prediction = model.predict([item])
                key = prediction[0]
                test_data.setdefault(key, []).append(item)
                #print(f"Phrase: {item}")
                #print(f"Predicted Category: {prediction[0]}")
    
    return test_data
                    


if __name__ == "__main__":

    model = load_model()
    results_dict = test_model(model)
    for key in results_dict:
        print(key)
        print("\n   ".join(results_dict.get(key)))