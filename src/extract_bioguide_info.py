import json

input_file = "generated_outputs/debug_bioguide.log"
with open(input_file, 'r') as file:
    list_of_congressmen = json.load(file)


training_data = []
for rep_info in list_of_congressmen:
    valid_keys = (
        "military", "illegal", "gov_runs", "work_history", "gov_highlights", "accolades",
        "family", "education", "weird_term"
    )
    for key in valid_keys:
        work_with_this_list = rep_info.get(key)
        if work_with_this_list is None:
            print(f"idk why this is None: {key, rep_info.get('bioguideID')}")
            continue
        if len(work_with_this_list) != 0:
            for item in work_with_this_list:
                training_data.append((item, key))
                
    
#now add some manual ones:



training_data.append(("and served until October 30, 2013, a successor having been chosen in a special election", "weird_term"))
training_data.append(("served from January 2, 1971, until his resignation January 1, 1977", "weird_term"))
training_data.append(("and served until her resignation on December 8, 2024", "weird_term"))
training_data.append(("and served until October 30, 2013, a successor having been chosen in a special election", "weird_term"))

training_data.append(("lived with foster families until reunited with his family in Orlando, FL, in 1966", "family"))





from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
import joblib

# 1. Split data into phrases (X) and categories (y)
X, y = zip(*training_data)

# 2. Create a "Pipeline" 
# This first turns text into numbers (Tfidf), then applies a Math model (NB)
model = make_pipeline(
    TfidfVectorizer(
        # This regex allows 1-character tokens and includes numbers specifically
        token_pattern=r"(?u)\b\w+\b", 
        # Using character n-grams can help identify "date-like" patterns
        analyzer='char_wb', 
        ngram_range=(2, 4) 
    ),
    MultinomialNB()
)
# 3. TRAIN the model
model.fit(X, y)

# 4. SAVE the model to a file
joblib.dump(model, 'bioguide_model.pkl')

print("Model trained and saved!")

