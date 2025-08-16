import pandas as pd

# Load your original dataset
df = pd.read_csv('/content/drive/MyDrive/Predictor/universities.csv')

# Fix column names
df.rename(columns={
    "Z-Score Cutoff": "Z_Score_Cutoff",
    "Apitute test": "Aptitude_Test",
    "All  Island Merit": "All_Island_Merit"
}, inplace=True)

# Convert Z-score to numeric (removes "NQC" and invalid values)
df["Z_Score_Cutoff"] = pd.to_numeric(df["Z_Score_Cutoff"], errors="coerce")

# Drop rows with missing cutoff
df.dropna(subset=["Z_Score_Cutoff"], inplace=True)

df.reset_index(drop=True, inplace=True)

# Save the cleaned dataset
df.to_csv('/content/drive/MyDrive/Predictor/cleaned_universities.csv', index=False)
!pip install pandas matplotlib seaborn scikit-learn
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, accuracy_score, classification_report, roc_auc_score
import numpy as np
import joblib
import pickle
df = pd.read_csv('/content/drive/MyDrive/Predictor/cleaned_universities.csv')
df.head()
print(df.describe())
print(df["Stream"].value_counts())
print(df["University"].value_counts().head(10))
df_any_stream = df[df['Stream'] == 'Any'].copy()
display(df_any_stream.head())
unique_streams = df['Stream'].unique().tolist()
other_streams = [stream for stream in unique_streams if stream != 'Any']
print(other_streams)
expanded_rows = []
for index, row in df_any_stream.iterrows():
    for stream in other_streams:
        new_row = row.to_dict()
        new_row['Stream'] = stream
        expanded_rows.append(new_row)

df_expanded = pd.DataFrame(expanded_rows)
display(df_expanded.head())
df_filtered = df[df['Stream'] != 'Any']
df_combined = pd.concat([df_filtered, df_expanded], ignore_index=True)
df_combined.reset_index(drop=True, inplace=True)
display(df_combined.head())
df_combined_encoded = df_combined.copy()
new_encoders = {}
for col in ["University", "Course Name", "District", "Stream"]:
    le = LabelEncoder()
    df_combined_encoded[col] = le.fit_transform(df_combined_encoded[col])
    new_encoders[col] = le

display(df_combined_encoded.head())
features = ["Year", "University", "Course Name", "District", "Stream", "Aptitude_Test", "All  Island Merit "]
target = "Z_Score_Cutoff"

X = df_combined_encoded[features]
y = df_combined_encoded[target]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print("Shape of X_train:", X_train.shape)
print("Shape of X_test:", X_test.shape)
print("Shape of y_train:", y_train.shape)
print("Shape of y_test:", y_test.shape)
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)
print(model)
y_pred = model.predict(X_test)
print("R²:", r2_score(y_test, y_pred))
print("MAE:", mean_absolute_error(y_test, y_pred))
print("RMSE:", np.sqrt(mean_squared_error(y_test, y_pred)))
import joblib
from sklearn.preprocessing import LabelEncoder

stream_encoder = LabelEncoder()
district_encoder = LabelEncoder()
university_encoder = LabelEncoder()
degree_encoder = LabelEncoder()

# Fit encoders on the original string values from df_combined
stream_encoder.fit(df_combined['Stream'])
district_encoder.fit(df_combined['District'])
university_encoder.fit(df_combined['University'])
degree_encoder.fit(df_combined['Course Name'])

# Transform the encoded DataFrame using the fitted encoders
df_combined_encoded['Stream'] = stream_encoder.transform(df_combined['Stream'])
df_combined_encoded['District'] = district_encoder.transform(df_combined['District'])
df_combined_encoded['University'] = university_encoder.transform(df_combined['University'])
df_combined_encoded['Course Name'] = degree_encoder.transform(df_combined['Course Name'])


# Save the encoders
joblib.dump(stream_encoder, 'stream_encoder.pkl')
joblib.dump(district_encoder, 'district_encoder.pkl')
joblib.dump(university_encoder, 'university_encoder.pkl')
joblib.dump(degree_encoder, 'degree_encoder.pkl')

# Save the model
joblib.dump(model, 'regressor.pkl')
df.rename(columns={
    "Z-Score Cutoff": "Z_Score_Cutoff",
    "Apitute test": "Aptitude_Test",
    "All  Island Merit ": "All_Island_Merit"
}, inplace=True)

df.reset_index(drop=True, inplace=True)
with open('/content/drive/MyDrive/Predictor/regressor.pkl', 'rb') as f:
    reg_model = joblib.load(f)

reg_le_cols = ["stream", "district", "degree", "university"]
reg_encoders = {}

for col in reg_le_cols:
    with open(f'/content/drive/MyDrive/Predictor/{col.lower().replace(" ", "_")}_encoder.pkl', 'rb') as f:
        reg_encoders[col] = joblib.load(f)
df_filtered_for_prediction = df[df['Stream'] != 'Any'].copy()

df_encoded = df_filtered_for_prediction.copy()
# Correct the keys to match the DataFrame column names
reg_encoders_corrected = {
    "Stream": reg_encoders["stream"],
    "District": reg_encoders["district"],
    "Course Name": reg_encoders["degree"], # Corrected key
    "University": reg_encoders["university"]
}

for col, encoder in reg_encoders_corrected.items():
    df_encoded[col] = encoder.transform(df_encoded[col])

# Rename the column to match the feature name used during model training
df_encoded.rename(columns={"All_Island_Merit": "All  Island Merit "}, inplace=True)


# Features regressor expects
reg_features = ["Year", "University", "Course Name", "District", "Stream", "Aptitude_Test", "All  Island Merit "]

# Predict cutoff using regressor
df_filtered_for_prediction["Predicted_Cutoff"] = reg_model.predict(df_encoded[reg_features])

# You can now merge this back to the original df if needed, or work with df_filtered_for_prediction
display(df_filtered_for_prediction.head())
student_data = []
for _, row in df_filtered_for_prediction.iterrows():
    cutoff = row["Predicted_Cutoff"]

    # Simulate 5 students below and 5 above the cutoff
    for delta in np.linspace(-0.2, 0.2, 11):
        z_score = cutoff + delta
        label = 1 if delta >= 0 else 0

        student_data.append({
            "Z_Score": round(z_score, 4),
            "Stream": row["Stream"],
            "District": row["District"],
            "Course Name": row["Course Name"],
            "University": row["University"],
            "Aptitude_Test": row["Aptitude_Test"],
            "All_Island_Merit": row["All_Island_Merit"],
            "Selected": label
        })

student_df = pd.DataFrame(student_data)
display(student_df.head())
clf_encoders = reg_encoders_corrected
# Save classifier encoders
for col, encoder in clf_encoders.items():
    filename = f'clf_{col.lower().replace(" ", "_")}_encoder.pkl'
    with open(filename, 'wb') as f:
        pickle.dump(encoder, f)
    print(f"Encoder for {col} saved to {filename}")

# Save the classifier model
joblib.dump(clf, 'classifier.pkl')
print("Classifier model saved to classifier.pkl")
# Define features (X) and target (y) for the classifier
features_clf = ["Z_Score", "Stream", "District", "Course Name", "University", "Aptitude_Test", "All_Island_Merit"]
target_clf = "Selected"

X_clf = student_df[features_clf]
y_clf = student_df[target_clf]
X_clf_encoded = X_clf.copy()
for col_name, encoder in reg_encoders_corrected.items():
    if col_name in X_clf_encoded.columns:
        X_clf_encoded[col_name] = encoder.transform(X_clf_encoded[col_name])

display(X_clf_encoded.head())
# Split the data into training and testing sets for the classifier
X_train_clf, X_test_clf, y_train_clf, y_test_clf = train_test_split(X_clf_encoded, y_clf, test_size=0.2, random_state=42)

print("Shape of X_train_clf:", X_train_clf.shape)
print("Shape of X_test_clf:", X_test_clf.shape)
print("Shape of y_train_clf:", y_train_clf.shape)
print("Shape of y_test_clf:", y_test_clf.shape)
from sklearn.ensemble import RandomForestClassifier

# Initialize and train the Random Forest Classifier
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train_clf, y_train_clf)
y_pred = clf.predict(X_test_clf)
y_prob = clf.predict_proba(X_test_clf)[:, 1]

print("Accuracy:", accuracy_score(y_test_clf, y_pred))
print("ROC AUC:", roc_auc_score(y_test_clf, y_prob))
print(classification_report(y_test_clf, y_pred))