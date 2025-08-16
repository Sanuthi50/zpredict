reg_model_loaded = joblib.load(REG_MODEL_PATH)
clf_model_loaded = joblib.load(CLF_MODEL_PATH)
reg_ohe_loaded = joblib.load(REG_ENCODER_PATH)
clf_ohe_loaded = joblib.load(CLF_ENCODER_PATH)
valid_courses_map = build_valid_map(df_specific)
def predict_eligibility(stream: str, district: str, z_score: float):
    """
    Predicts university and course eligibility and selection probability for a student.

    Args:
        stream: The student's academic stream (e.g., "Biological Science", "Arts").
        district: The student's district (e.g., "COLOMBO", "KANDY").
        z_score: The student's current Z-score.

    Returns:
        A dictionary containing eligible universities, courses, predicted future year,
        selection probabilities, aptitude test requirements, and all-island merit status.
        (Detailed structure to be defined in subsequent steps).
    """
    pass
def predict_eligibility(stream: str, district: str, z_score: float):
    """
    Predicts university and course eligibility and selection probability for a student.

    Args:
        stream: The student's academic stream (e.g., "Biological Science", "Arts").
        district: The student's district (e.g., "COLOMBO", "KANDY").
        z_score: The student's current Z-score.

    Returns:
        A dictionary containing eligible universities, courses, predicted future year,
        selection probabilities, aptitude test requirements, and all-island merit status.
        (Detailed structure to be defined in subsequent steps).
    """
    if stream not in valid_courses_map:
        return {"error": f"Stream '{stream}' not found in valid courses map."}

    valid_courses = valid_courses_map[stream]
    prediction_results = []

    # Determine the current year from the data if possible, or set a default
    current_year = pd.to_numeric(df_specific["Year"], errors='coerce').max() if not df_specific.empty else 2024 # Default if no data

    # Placeholder values for Aptitude_Test and All_Island_Merit for prediction
    # These can be refined later based on specific course/university requirements
    # For now, we assume typical case where aptitude test is not always required
    # and All-Island Merit is not always the primary factor
    aptitude_test_placeholder = 0
    all_island_merit_placeholder = 0

    for course in valid_courses:
        # Find universities offering this course in the student's stream
        # and district from the original data to get valid university names
        relevant_universities = df_specific[
            (df_specific['Stream'] == stream) &
            (df_specific['Course Name'] == course) &
            (df_specific['District'] == district)
        ]['University'].unique().tolist()

        # If no past data for this course/district combination, skip it for now
        if not relevant_universities:
            continue

        for university in relevant_universities:
            for year_delta in range(1, 6): # Predict for next 5 years
                future_year = current_year + year_delta

                # Create input data for the regressor model
                input_data_reg = pd.DataFrame({
                    'Year': [future_year],
                    'Aptitude_Test': [aptitude_test_placeholder],
                    'All_Island_Merit': [all_island_merit_placeholder],
                    'University': [university],
                    'Course Name': [course],
                    'District': [district],
                    'Stream': [stream]
                })

                # Transform categorical features using the loaded encoder
                input_cat_encoded_reg = reg_ohe_loaded.transform(input_data_reg[reg_cat_cols]).toarray()
                input_num_reg = input_data_reg[reg_num_cols].values
                input_reg_processed = np.hstack([input_num_reg, input_cat_encoded_reg])

                # Predict the Z-score cutoff using the loaded regressor model
                predicted_cutoff = reg_model_loaded.predict(input_reg_processed)[0]

                prediction_results.append({
                    'University': university,
                    'Course Name': course,
                    'Predicted Year': future_year,
                    'Predicted Z_Score_Cutoff': predicted_cutoff,
                    'Aptitude_Test_Required': aptitude_test_placeholder, # Store placeholders for now
                    'All_Island_Merit': all_island_merit_placeholder     # Store placeholders for now
                })

    # The prediction results list now contains predicted cutoffs for each valid course/university
    # combination for the next 5 years within the student's stream and district.
    # The next steps will involve using the classifier and filtering based on the student's Z-score.

    return prediction_results # Return the intermediate results for now

def predict_eligibility(stream: str, district: str, z_score: float):
    """
    Predicts university and course eligibility and selection probability for a student.

    Args:
        stream: The student's academic stream (e.g., "Biological Science", "Arts").
        district: The student's district (e.g., "COLOMBO", "KANDY").
        z_score: The student's current Z-score.

    Returns:
        A dictionary containing eligible universities, courses, predicted future year,
        selection probabilities, aptitude test requirements, and all-island merit status.
        (Detailed structure to be defined in subsequent steps).
    """
    if stream not in valid_courses_map:
        return {"error": f"Stream '{stream}' not found in valid courses map."}

    valid_courses = valid_courses_map[stream]
    classifier_inputs = []

    # Determine the current year from the data if possible, or set a default
    current_year = pd.to_numeric(df_specific["Year"], errors='coerce').max() if not df_specific.empty else 2024 # Default if no data

    # Placeholder values for Aptitude_Test and All_Island_Merit for prediction
    # These can be refined later based on specific course/university requirements
    # For now, we assume typical case where aptitude test is not always required
    # and All-Island Merit is not always the primary factor
    aptitude_test_placeholder = 0
    all_island_merit_placeholder = 0

    for course in valid_courses:
        # Find universities offering this course in the student's stream
        # and district from the original data to get valid university names
        relevant_universities = df_specific[
            (df_specific['Stream'] == stream) &
            (df_specific['Course Name'] == course) &
            (df_specific['District'] == district)
        ]['University'].unique().tolist()

        # If no past data for this course/district combination, skip it for now
        if not relevant_universities:
            continue

        for university in relevant_universities:
            for year_delta in range(1, 6): # Predict for next 5 years
                future_year = current_year + year_delta

                # Prepare input data for the classifier model
                input_data_clf = pd.DataFrame({
                    'Z_Score': [z_score],
                    'Stream': [stream],
                    'District': [district],
                    'Course Name': [course],
                    'University': [university],
                    'Aptitude_Test': [aptitude_test_placeholder],
                    'All_Island_Merit': [all_island_merit_placeholder]
                })

                # Define classifier categorical and numerical columns (must match train_and_save)
                clf_cat_cols = ["Stream", "District", "Course Name", "University"]
                clf_num_cols = ["Z_Score", "Aptitude_Test", "All_Island_Merit"]

                # Transform categorical features using the loaded classifier encoder
                input_cat_encoded_clf = clf_ohe_loaded.transform(input_data_clf[clf_cat_cols]).toarray()
                input_num_clf = input_data_clf[clf_num_cols].values

                # Combine numerical and encoded categorical features
                input_clf_processed = np.hstack([input_num_clf, input_cat_encoded_clf])

                classifier_inputs.append({
                    'University': university,
                    'Course Name': course,
                    'Predicted Year': future_year,
                    'Classifier_Input': input_clf_processed,
                    'Aptitude_Test_Required': aptitude_test_placeholder,
                    'All_Island_Merit': all_island_merit_placeholder
                })

    # The classifier_inputs list now contains the prepared input data for the classifier
    # for each valid university, course, and future year combination.

    return classifier_inputs # Return the intermediate results for now
def predict_eligibility(stream: str, district: str, z_score: float):
    """
    Predicts university and course eligibility and selection probability for a student.

    Args:
        stream: The student's academic stream (e.g., "Biological Science", "Arts").
        district: The student's district (e.g., "COLOMBO", "KANDY").
        z_score: The student's current Z-score.

    Returns:
        A dictionary containing eligible universities, courses, predicted future year,
        selection probabilities, aptitude test requirements, and all-island merit status.
        (Detailed structure to be defined in subsequent steps).
    """
    if stream not in valid_courses_map:
        return {"error": f"Stream '{stream}' not found in valid courses map."}

    valid_courses = valid_courses_map[stream]
    classifier_inputs = []

    # Determine the current year from the data if possible, or set a default
    current_year = pd.to_numeric(df_specific["Year"], errors='coerce').max() if not df_specific.empty else 2024 # Default if no data

    # Placeholder values for Aptitude_Test and All_Island_Merit for prediction
    # These can be refined later based on specific course/university requirements
    # For now, we assume typical case where aptitude test is not always required
    # and All-Island Merit is not always the primary factor
    aptitude_test_placeholder = 0
    all_island_merit_placeholder = 0

    for course in valid_courses:
        # Find universities offering this course in the student's stream
        # and district from the original data to get valid university names
        relevant_universities = df_specific[
            (df_specific['Stream'] == stream) &
            (df_specific['Course Name'] == course) &
            (df_specific['District'] == district)
        ]['University'].unique().tolist()

        # If no past data for this course/district combination, skip it for now
        if not relevant_universities:
            continue

        for university in relevant_universities:
            for year_delta in range(1, 6): # Predict for next 5 years
                future_year = current_year + year_delta

                # Prepare input data for the classifier model
                input_data_clf = pd.DataFrame({
                    'Z_Score': [z_score],
                    'Stream': [stream],
                    'District': [district],
                    'Course Name': [course],
                    'University': [university],
                    'Aptitude_Test': [aptitude_test_placeholder],
                    'All_Island_Merit': [all_island_merit_placeholder]
                })

                # Define classifier categorical and numerical columns (must match train_and_save)
                clf_cat_cols = ["Stream", "District", "Course Name", "University"]
                clf_num_cols = ["Z_Score", "Aptitude_Test", "All_Island_Merit"]

                # Transform categorical features using the loaded classifier encoder
                input_cat_encoded_clf = clf_ohe_loaded.transform(input_data_clf[clf_cat_cols]).toarray()
                input_num_clf = input_data_clf[clf_num_cols].values

                # Combine numerical and encoded categorical features
                input_clf_processed = np.hstack([input_num_clf, input_cat_encoded_clf])

                # Predict selection probability using the loaded classifier model
                selection_probability = clf_model_loaded.predict_proba(input_clf_processed)[:, 1][0]


                classifier_inputs.append({
                    'University': university,
                    'Course Name': course,
                    'Predicted Year': future_year,
                    'Selection Probability': selection_probability,
                    'Aptitude_Test_Required': aptitude_test_placeholder,
                    'All_Island_Merit': all_island_merit_placeholder
                })

    # The classifier_inputs list now contains the predicted selection probabilities
    # for each valid university, course, and future year combination.

    return classifier_inputs # Return the intermediate results for now
def predict_eligibility(stream: str, district: str, z_score: float):
    """
    Predicts university and course eligibility and selection probability for a student.

    Args:
        stream: The student's academic stream (e.g., "Biological Science", "Arts").
        district: The student's district (e.g., "COLOMBO", "KANDY").
        z_score: The student's current Z-score.

    Returns:
        A dictionary containing eligible universities, courses, predicted future year,
        selection probabilities, aptitude test requirements, and all-island merit status.
        (Detailed structure to be defined in subsequent steps).
    """
    if stream not in valid_courses_map:
        return {"error": f"Stream '{stream}' not found in valid courses map."}

    valid_courses = valid_courses_map[stream]
    prediction_results = []

    # Determine the current year from the data if possible, or set a default
    current_year = pd.to_numeric(df_specific["Year"], errors='coerce').max() if not df_specific.empty else 2024 # Default if no data

    # Create a lookup for Aptitude_Test and All_Island_Merit
    # Group by University and Course Name and take the maximum to get 1 if required anytime
    lookup_df = df_specific.groupby(['University', 'Course Name'])[['Aptitude_Test', 'All_Island_Merit']].max().reset_index()

    for course in valid_courses:
        # Find universities offering this course in the student's stream
        # and district from the original data to get valid university names
        relevant_universities = df_specific[
            (df_specific['Stream'] == stream) &
            (df_specific['Course Name'] == course) &
            (df_specific['District'] == district)
        ]['University'].unique().tolist()

        # If no past data for this course/district combination, skip it for now
        if not relevant_universities:
            continue

        for university in relevant_universities:
            # Retrieve Aptitude_Test and All_Island_Merit from the lookup
            lookup_match = lookup_df[
                (lookup_df['University'] == university) &
                (lookup_df['Course Name'] == course)
            ]
            aptitude_test_required = lookup_match['Aptitude_Test'].iloc[0] if not lookup_match.empty else 0
            all_island_merit = lookup_match['All_Island_Merit'].iloc[0] if not lookup_match.empty else 0


            for year_delta in range(1, 6): # Predict for next 5 years
                future_year = current_year + year_delta

                # Prepare input data for the classifier model
                input_data_clf = pd.DataFrame({
                    'Z_Score': [z_score],
                    'Stream': [stream],
                    'District': [district],
                    'Course Name': [course],
                    'University': [university],
                    'Aptitude_Test': [aptitude_test_required],
                    'All_Island_Merit': [all_island_merit]
                })

                # Define classifier categorical and numerical columns (must match train_and_save)
                clf_cat_cols = ["Stream", "District", "Course Name", "University"]
                clf_num_cols = ["Z_Score", "Aptitude_Test", "All_Island_Merit"]

                # Transform categorical features using the loaded classifier encoder
                input_cat_encoded_clf = clf_ohe_loaded.transform(input_data_clf[clf_cat_cols]).toarray()
                input_num_clf = input_data_clf[clf_num_cols].values

                # Combine numerical and encoded categorical features
                input_clf_processed = np.hstack([input_num_clf, input_cat_encoded_clf])

                # Predict selection probability using the loaded classifier model
                selection_probability = clf_model_loaded.predict_proba(input_clf_processed)[:, 1][0]


                prediction_results.append({
                    'University': university,
                    'Course Name': course,
                    'Predicted Year': future_year,
                    'Selection Probability': selection_probability,
                    'Aptitude_Test_Required': aptitude_test_required,
                    'All_Island_Merit': all_island_merit
                })

    # The prediction_results list now contains the predicted selection probabilities
    # and the required information for each valid university, course, and future year combination.

    return prediction_results # Return the intermediate results for now

def predict_eligibility(stream: str, district: str, z_score: float):
    """
    Predicts university and course eligibility and selection probability for a student.

    Args:
        stream: The student's academic stream (e.g., "Biological Science", "Arts").
        district: The student's district (e.g., "COLOMBO", "KANDY").
        z_score: The student's current Z-score.

    Returns:
        A dictionary containing eligible universities, courses, predicted future year,
        selection probabilities, aptitude test requirements, and all-island merit status.
        (Detailed structure to be defined in subsequent steps).
    """
    if stream not in valid_courses_map:
        return {"error": f"Stream '{stream}' not found in valid courses map."}

    valid_courses = valid_courses_map[stream]
    prediction_results = []

    # Determine the current year from the data if possible, or set a default
    current_year = pd.to_numeric(df_specific["Year"], errors='coerce').max() if not df_specific.empty else 2024 # Default if no data

    # Create a lookup for Aptitude_Test and All_Island_Merit
    # Group by University and Course Name and take the maximum to get 1 if required anytime
    lookup_df = df_specific.groupby(['University', 'Course Name'])[['Aptitude_Test', 'All_Island_Merit']].max().reset_index()

    for course in valid_courses:
        # Find universities offering this course in the student's stream
        # and district from the original data to get valid university names
        relevant_universities = df_specific[
            (df_specific['Stream'] == stream) &
            (df_specific['Course Name'] == course) &
            (df_specific['District'] == district)
        ]['University'].unique().tolist()

        # If no past data for this course/district combination, skip it for now
        if not relevant_universities:
            continue

        for university in relevant_universities:
            # Retrieve Aptitude_Test and All_Island_Merit from the lookup
            lookup_match = lookup_df[
                (lookup_df['University'] == university) &
                (lookup_df['Course Name'] == course)
            ]
            aptitude_test_required = lookup_match['Aptitude_Test'].iloc[0] if not lookup_match.empty else 0
            all_island_merit = lookup_match['All_Island_Merit'].iloc[0] if not lookup_match.empty else 0


            for year_delta in range(1, 6): # Predict for next 5 years
                future_year = current_year + year_delta

                # Prepare input data for the classifier model
                input_data_clf = pd.DataFrame({
                    'Z_Score': [z_score],
                    'Stream': [stream],
                    'District': [district],
                    'Course Name': [course],
                    'University': [university],
                    'Aptitude_Test': [aptitude_test_required],
                    'All_Island_Merit': [all_island_merit]
                })

                # Define classifier categorical and numerical columns (must match train_and_save)
                clf_cat_cols = ["Stream", "District", "Course Name", "University"]
                clf_num_cols = ["Z_Score", "Aptitude_Test", "All_Island_Merit"]

                # Transform categorical features using the loaded classifier encoder
                input_cat_encoded_clf = clf_ohe_loaded.transform(input_data_clf[clf_cat_cols]).toarray()
                input_num_clf = input_data_clf[clf_num_cols].values

                # Combine numerical and encoded categorical features
                input_clf_processed = np.hstack([input_num_clf, input_cat_encoded_clf])

                # Predict selection probability using the loaded classifier model
                selection_probability = clf_model_loaded.predict_proba(input_clf_processed)[:, 1][0]


                prediction_results.append({
                    'University': university,
                    'Course Name': course,
                    'Predicted Year': future_year,
                    'Selection Probability': selection_probability,
                    'Aptitude_Test_Required': aptitude_test_required,
                    'All_Island_Merit': all_island_merit
                })

    # Filter results based on a probability threshold
    probability_threshold = 0.5  # Define the threshold
    eligible_courses = []

    for result in prediction_results:
        if result['Selection Probability'] >= probability_threshold:
            eligible_courses.append(result)

    return eligible_courses # Return the filtered results

def predict_eligibility(stream: str, district: str, z_score: float):
    """
    Predicts university and course eligibility and selection probability for a student.

    Args:
        stream: The student's academic stream (e.g., "Biological Science", "Arts").
        district: The student's district (e.g., "COLOMBO", "KANDY").
        z_score: The student's current Z-score.

    Returns:
        A dictionary containing eligible universities, courses, predicted future year,
        selection probabilities, aptitude test requirements, and all-island merit status.
        (Detailed structure to be defined in subsequent steps).
    """
    if stream not in valid_courses_map:
        return {"error": f"Stream '{stream}' not found in valid courses map."}

    valid_courses = valid_courses_map[stream]
    prediction_results = []

    # Determine the current year from the data if possible, or set a default
    current_year = pd.to_numeric(df_specific["Year"], errors='coerce').max() if not df_specific.empty else 2024 # Default if no data

    # Create a lookup for Aptitude_Test and All_Island_Merit
    # Group by University and Course Name and take the maximum to get 1 if required anytime
    lookup_df = df_specific.groupby(['University', 'Course Name'])[['Aptitude_Test', 'All_Island_Merit']].max().reset_index()

    for course in valid_courses:
        # Find universities offering this course in the student's stream
        # and district from the original data to get valid university names
        relevant_universities = df_specific[
            (df_specific['Stream'] == stream) &
            (df_specific['Course Name'] == course) &
            (df_specific['District'] == district)
        ]['University'].unique().tolist()

        # If no past data for this course/district combination, skip it for now
        if not relevant_universities:
            continue

        for university in relevant_universities:
            # Retrieve Aptitude_Test and All_Island_Merit from the lookup
            lookup_match = lookup_df[
                (lookup_df['University'] == university) &
                (lookup_df['Course Name'] == course)
            ]
            aptitude_test_required = lookup_match['Aptitude_Test'].iloc[0] if not lookup_match.empty else 0
            all_island_merit = lookup_match['All_Island_Merit'].iloc[0] if not lookup_match.empty else 0


            for year_delta in range(1, 6): # Predict for next 5 years
                future_year = current_year + year_delta

                # Prepare input data for the classifier model
                input_data_clf = pd.DataFrame({
                    'Z_Score': [z_score],
                    'Stream': [stream],
                    'District': [district],
                    'Course Name': [course],
                    'University': [university],
                    'Aptitude_Test': [aptitude_test_required],
                    'All_Island_Merit': [all_island_merit]
                })

                # Define classifier categorical and numerical columns (must match train_and_save)
                clf_cat_cols = ["Stream", "District", "Course Name", "University"]
                clf_num_cols = ["Z_Score", "Aptitude_Test", "All_Island_Merit"]

                # Transform categorical features using the loaded classifier encoder
                input_cat_encoded_clf = clf_ohe_loaded.transform(input_data_clf[clf_cat_cols]).toarray()
                input_num_clf = input_data_clf[clf_num_cols].values

                # Combine numerical and encoded categorical features
                input_clf_processed = np.hstack([input_num_clf, input_cat_encoded_clf])

                # Predict selection probability using the loaded classifier model
                selection_probability = clf_model_loaded.predict_proba(input_clf_processed)[:, 1][0]


                prediction_results.append({
                    'University': university,
                    'Course Name': course,
                    'Predicted Year': future_year,
                    'Selection Probability': selection_probability,
                    'Aptitude_Test_Required': aptitude_test_required,
                    'All_Island_Merit': all_island_merit
                })

    # Filter results based on a probability threshold
    probability_threshold = 0.5  # Define the threshold
    eligible_courses = [result for result in prediction_results if result['Selection Probability'] >= probability_threshold]

    # Format and group results by Predicted Year
    formatted_results = {}
    for result in eligible_courses:
        year = result['Predicted Year']
        if year not in formatted_results:
            formatted_results[year] = []
        formatted_results[year].append({
            'University': result['University'],
            'Course Name': result['Course Name'],
            'Selection Probability': f"{result['Selection Probability']:.2%}", # Format as percentage
            'Aptitude Test Required': "Yes" if result['Aptitude_Test_Required'] else "No",
            'All-Island Merit': "Yes" if result['All_Island_Merit'] else "No"
        })

    return formatted_results
