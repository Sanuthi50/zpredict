import os
import joblib
import pandas as pd
import numpy as np
from django.conf import settings
from django.core.cache import cache
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class MLPredictor:
    def __init__(self):
        self.regressor = None
        self.classifier = None
        self.classifier_encoder = None
        self.feature_encoder = None
        self.valid_courses_map = None
        self.model_path = os.path.join(settings.BASE_DIR, 'api', 'ml_model')
        self.models_loaded = False
        self.load_models()
    
    def load_models(self) -> None:
        """Load trained models and encoders with improved error handling"""
        try:
            # Check if models are cached
            cached_models = cache.get('ml_models')
            if cached_models:
                self.regressor = cached_models.get('regressor')
                self.classifier = cached_models.get('classifier')
                self.classifier_encoder = cached_models.get('classifier_encoder')
                self.feature_encoder = cached_models.get('feature_encoder')
                self.valid_courses_map = cached_models.get('valid_courses_map')
                self.models_loaded = True
                logger.info("Models loaded from cache")
                return
            
            # Create model directory if it doesn't exist
            if not os.path.exists(self.model_path):
                logger.error(f"Model directory does not exist: {self.model_path}")
                return
            
            # Load all models
            self._load_regressor()
            self._load_classifier()
            self._load_classifier_encoder()
            self._load_feature_encoder()
            self._load_valid_courses_map()
            
            # Cache models for 1 hour if at least one model was loaded
            if self.regressor or self.classifier:
                cache.set('ml_models', {
                    'regressor': self.regressor,
                    'classifier': self.classifier,
                    'classifier_encoder': self.classifier_encoder,
                    'feature_encoder': self.feature_encoder,
                    'valid_courses_map': self.valid_courses_map
                }, 3600)
                self.models_loaded = True
                logger.info("Models loaded and cached successfully")
            else:
                logger.warning("No models were loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
            self.models_loaded = False
    
    def _load_regressor(self) -> None:
        """Load regressor model"""
        regressor_path = os.path.join(self.model_path, 'regressor.pkl')
        if os.path.exists(regressor_path):
            try:
                self.regressor = joblib.load(regressor_path)
                logger.info("Regressor model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading regressor: {str(e)}")
                self.regressor = None
    
    def _load_classifier(self) -> None:
        """Load classifier model"""
        classifier_path = os.path.join(self.model_path, 'classifier.pkl')
        if os.path.exists(classifier_path):
            try:
                self.classifier = joblib.load(classifier_path)
                logger.info("Classifier model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading classifier: {str(e)}")
                self.classifier = None
    
    def _load_classifier_encoder(self) -> None:
        """Load classifier encoder"""
        encoder_path = os.path.join(self.model_path, 'classifier_encoder.pkl')
        if os.path.exists(encoder_path):
            try:
                self.classifier_encoder = joblib.load(encoder_path)
                logger.info("Classifier encoder loaded successfully")
            except Exception as e:
                logger.error(f"Error loading classifier encoder: {str(e)}")
                self.classifier_encoder = None
    
    def _load_feature_encoder(self) -> None:
        """Load feature encoder"""
        encoder_path = os.path.join(self.model_path, 'feature_encoder.pkl')
        if os.path.exists(encoder_path):
            try:
                self.feature_encoder = joblib.load(encoder_path)
                logger.info("Feature encoder loaded successfully")
            except Exception as e:
                logger.error(f"Error loading feature encoder: {str(e)}")
                self.feature_encoder = None
    
    
    def _load_valid_courses_map(self) -> None:
        """Load valid courses map"""
        courses_map_path = os.path.join(self.model_path, 'valid_courses_map.pkl')
        if os.path.exists(courses_map_path):
            try:
                self.valid_courses_map = joblib.load(courses_map_path)
                logger.info("Valid courses map loaded successfully")
            except Exception as e:
                logger.error(f"Error loading valid courses map: {str(e)}")
                self.valid_courses_map = None
    
    def _validate_models_loaded(self) -> bool:
        """Check if models are properly loaded"""
        if not self.models_loaded:
            logger.error("Models not properly loaded. Please check model files.")
            return False
        return True
    
    def _encode_features_for_regressor(self, data_dict: Dict[str, Any]) -> np.ndarray:
        """Encode features for regressor using the feature encoder"""
        if not self.feature_encoder:
            raise ValueError("Feature encoder not loaded")
        
        # Prepare features in the order expected by the encoder (from ml_model.py)
        # reg_cat_cols = ["University", "Course Name", "District", "Stream"]
        features = [
            data_dict.get('university', ''),
            data_dict.get('course_name', ''),
            data_dict.get('district', ''),
            data_dict.get('stream', '')
        ]
        
        # Encode categorical features and convert to dense format
        encoded_features = self.feature_encoder.transform([features]).toarray()
        
        # Prepare numerical features in the order expected by the regressor
        # reg_num_cols = ["Year", "Aptitude_Test", "All_Island_Merit"]
        numerical_features = np.array([
            data_dict.get('year', 2024),
            data_dict.get('aptitude_test', False),
            data_dict.get('all_island_merit', True)
        ]).reshape(1, -1)
        
        # Combine numerical and encoded categorical features exactly like in ml_model.py
        # np.hstack([numerical_features, encoded_categorical_features])
        combined_features = np.hstack([numerical_features, encoded_features])
        
        return combined_features
    
    def _encode_features_for_classifier(self, data_dict: Dict[str, Any]) -> np.ndarray:
        """Encode features for classifier using the classifier encoder"""
        if not self.classifier_encoder:
            raise ValueError("Classifier encoder not loaded")
        
        # Prepare features in the order expected by the encoder (from ml_model.py)
        # clf_cat_cols = ["Stream", "District", "Course Name", "University"]
        features = [
            data_dict.get('stream', ''),
            data_dict.get('district', ''),
            data_dict.get('course_name', ''),
            data_dict.get('university', '')
        ]
        
        # Encode categorical features and convert to dense format
        encoded_features = self.classifier_encoder.transform([features]).toarray()
        
        # Prepare numerical features in the order expected by the classifier
        # clf_num_cols = ["Z_Score", "Aptitude_Test", "All_Island_Merit"]
        numerical_features = np.array([
            data_dict.get('z_score', 0.0),
            data_dict.get('aptitude_test', False),
            data_dict.get('all_island_merit', True)
        ]).reshape(1, -1)
        
        # Combine numerical and encoded categorical features exactly like in ml_model.py
        # np.hstack([numerical_features, encoded_categorical_features])
        combined_features = np.hstack([numerical_features, encoded_features])
        
        return combined_features
    
    def predict_cutoff(self, year: int, university: str, course_name: str, district: str, 
                      stream: str, aptitude_test: bool, all_island_merit: bool) -> float:
        """Predict Z-score cutoff using regressor"""
        if not self._validate_models_loaded():
            raise ValueError("Models not properly loaded")
        
        if not self.regressor:
            raise ValueError("Regressor model not loaded")
        
        # Validate inputs
        if not all([year, university, course_name, district, stream]):
            raise ValueError("All input parameters must be provided and non-empty")
        
        # Prepare features
        features_dict = {
            'university': str(university),
            'course_name': str(course_name),
            'district': str(district).upper(),
            'stream': str(stream),
            'year': year,
            'aptitude_test': aptitude_test,
            'all_island_merit': all_island_merit
        }
        
        try:
            # Encode features
            encoded_features = self._encode_features_for_regressor(features_dict)
            
            # Use encoded features directly (scaler not compatible with current model)
            # The regressor was trained on these encoded features without scaling
            
            # Predict
            prediction = self.regressor.predict(encoded_features)
            result = float(prediction[0])
            
            # Validate result
            if np.isnan(result) or np.isinf(result):
                logger.warning("Invalid prediction result, returning default value")
                return 0.0
            
            return result
            
        except Exception as e:
            logger.error(f"Error during prediction: {str(e)}")
            raise ValueError(f"Prediction failed: {str(e)}")
    
    def predict_selection_probability(self, z_score: float, stream: str, district: str, 
                                    course_name: str, university: str, aptitude_test: bool, 
                                    all_island_merit: bool) -> float:
        """Predict selection probability using classifier"""
        if not self._validate_models_loaded():
            raise ValueError("Models not properly loaded")
        
        if not self.classifier:
            raise ValueError("Classifier model not loaded")
        
        # Validate inputs
        if z_score is None or not all([stream, district, course_name, university]):
            raise ValueError("All input parameters must be provided and non-empty")
        
        # Prepare features
        features_dict = {
            'stream': str(stream),
            'district': str(district).upper(),
            'course_name': str(course_name),
            'university': str(university),
            'z_score': z_score,
            'aptitude_test': aptitude_test,
            'all_island_merit': all_island_merit
        }
        
        try:
            # Encode features
            encoded_features = self._encode_features_for_classifier(features_dict)
            
            # Predict probability
            probability = self.classifier.predict_proba(encoded_features)
            result = float(probability[0][1])  # Return probability of being selected (class 1)
            
            # Validate result
            if np.isnan(result) or np.isinf(result):
                logger.warning("Invalid probability result, returning default value")
                return 0.0
            
            return max(0.0, min(1.0, result))  # Ensure probability is between 0 and 1
            
        except Exception as e:
            logger.error(f"Error during probability prediction: {str(e)}")
            raise ValueError(f"Probability prediction failed: {str(e)}")
    
    def get_recommendation_status(self, probability: float) -> str:
        """Convert probability to recommendation status with validation"""
        if not isinstance(probability, (int, float)) or probability < 0 or probability > 1:
            logger.warning(f"Invalid probability value: {probability}")
            return 'Unknown'
        
        if probability >= 0.7:
            return 'Highly Recommended'
        elif probability >= 0.4:
            return 'Recommended'
        else:
            return 'Not Recommended'
    
    def get_available_courses_for_stream(self, stream: str, limit: int = 50) -> List[Dict[str, str]]:
        """Get available courses for a given stream using the valid_courses_map"""
        if not self._validate_models_loaded():
            logger.warning("Models not loaded, returning empty course list")
            return []
        
        if not self.valid_courses_map:
            logger.warning("Valid courses map not loaded")
            return []
        
        if not self.feature_encoder:
            logger.warning("Feature encoder not loaded, cannot extract university data")
            return []
        
        # Map common stream names to the keys in valid_courses_map
        stream_mapping = {
            'physical': 'Physical Science',
            'biological': 'Biological Science',
            'biosystems': 'Biosystems Technology',
            'commerce': 'Commerce',
            'engineering': 'Engineering Technology',
            'arts': 'Arts',
            'other': 'Other'
        }
        
        # Find the matching stream key
        stream_key = None
        stream_lower = stream.lower().strip()
        
        # First try exact match
        if stream in self.valid_courses_map:
            stream_key = stream
        else:
            # Try mapping
            for key, value in stream_mapping.items():
                if key in stream_lower:
                    stream_key = value
                    break
        
        if not stream_key:
            logger.warning(f"Stream '{stream}' not found in valid courses map. Available streams: {list(self.valid_courses_map.keys())}")
            return []
        
        # Get courses for the stream
        courses = self.valid_courses_map.get(stream_key, [])
        
        if not courses:
            logger.warning(f"No courses found for stream: {stream_key}")
            return []
        
        # Extract universities from feature encoder (index 0 contains universities)
        try:
            available_universities = list(self.feature_encoder.categories_[0])
            # Clean up university names (remove extra spaces and duplicates)
            cleaned_universities = []
            seen = set()
            for uni in available_universities:
                cleaned_uni = uni.strip()
                if cleaned_uni and cleaned_uni not in seen:
                    cleaned_universities.append(cleaned_uni)
                    seen.add(cleaned_uni)
            
            if not cleaned_universities:
                logger.warning("No universities found in feature encoder")
                return []
            
        except Exception as e:
            logger.error(f"Error extracting universities from feature encoder: {str(e)}")
            return []
        
        # Generate course-university pairs
        course_university_pairs = []
        max_courses_per_stream = max(1, limit // len(cleaned_universities))
        
        for course in courses[:max_courses_per_stream]:
            for university in cleaned_universities:
                course_university_pairs.append({
                    'course_name': course,
                    'university_name': university
                })
                if len(course_university_pairs) >= limit:
                    break
            if len(course_university_pairs) >= limit:
                break
        
        logger.info(f"Generated {len(course_university_pairs)} course-university pairs for stream '{stream}' using {len(cleaned_universities)} universities from pkl data")
        return course_university_pairs
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models for debugging"""
        return {
            'models_loaded': self.models_loaded,
            'regressor_available': self.regressor is not None,
            'classifier_available': self.classifier is not None,
            'classifier_encoder_available': self.classifier_encoder is not None,
            'feature_encoder_available': self.feature_encoder is not None,
            'valid_courses_map_available': self.valid_courses_map is not None,
            'model_path': self.model_path,
            'regressor_features': getattr(self.regressor, 'n_features_in_', None) if self.regressor else None,
            'classifier_features': getattr(self.classifier, 'n_features_in_', None) if self.classifier else None,
            'available_streams': list(self.valid_courses_map.keys()) if self.valid_courses_map else []
        }

# Create a single, globally-loaded instance of the predictor
# This ensures models are loaded only once when the server starts.
try:
    ml_predictor_instance = MLPredictor()
    logger.info("ML Predictor instance created successfully")
except Exception as e:
    logger.error(f"Failed to create ML Predictor instance: {str(e)}")
    ml_predictor_instance = None  