import os
import sys
import django
import logging

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zpredict.settings')
django.setup()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import after Django setup
from api.ml_utils import ml_predictor_instance

def test_ml_loading():
    """Test if ML models and encoders are loaded correctly."""
    logger.info("Testing ML model loading...")
    
    # Check if models are loaded
    if not ml_predictor_instance.models_loaded:
        logger.error("ML models failed to load!")
        return False
    
    logger.info("✓ ML models loaded successfully")
    
    # Check if required components are loaded
    required_components = {
        'Regressor': ml_predictor_instance.regressor,
        'Classifier': ml_predictor_instance.classifier,
        'Scaler': ml_predictor_instance.scaler,
        'Classifier Encoder': ml_predictor_instance.classifier_encoder,
        'Feature Encoder': ml_predictor_instance.feature_encoder,
        'Valid Courses Map': ml_predictor_instance.valid_courses_map
    }
    
    all_loaded = True
    for name, component in required_components.items():
        if component is None:
            logger.warning(f"✗ {name} is not loaded")
            all_loaded = False
        else:
            logger.info(f"✓ {name} loaded successfully")
    
    # Log encoder information
    if ml_predictor_instance.classifier_encoder:
        logger.info("\nClassifier encoder information:")
        if hasattr(ml_predictor_instance.classifier_encoder, 'feature_names_in_'):
            logger.info(f"Feature names: {list(ml_predictor_instance.classifier_encoder.feature_names_in_)}")
        if hasattr(ml_predictor_instance.classifier_encoder, 'n_features_in_'):
            logger.info(f"Input features: {ml_predictor_instance.classifier_encoder.n_features_in_}")
    
    if ml_predictor_instance.feature_encoder:
        logger.info("\nFeature encoder information:")
        if hasattr(ml_predictor_instance.feature_encoder, 'feature_names_in_'):
            logger.info(f"Feature names: {list(ml_predictor_instance.feature_encoder.feature_names_in_)}")
        if hasattr(ml_predictor_instance.feature_encoder, 'n_features_in_'):
            logger.info(f"Input features: {ml_predictor_instance.feature_encoder.n_features_in_}")
    
    # Log courses map information
    if ml_predictor_instance.valid_courses_map:
        logger.info("\nValid courses map information:")
        logger.info(f"Available streams: {list(ml_predictor_instance.valid_courses_map.keys())}")
        for stream, courses in ml_predictor_instance.valid_courses_map.items():
            logger.info(f"{stream}: {len(courses)} courses")
    
    return all_loaded

def test_prediction():
    """Test prediction generation with sample data."""
    logger.info("\nTesting prediction generation...")
    
    if not ml_predictor_instance.models_loaded:
        logger.error("Cannot test prediction: Models not loaded")
        return False
    
    # Sample data for testing
    test_cases = [
        {
            'year': 2023,
            'z_score': 1.5,
            'stream': 'Physical',
            'district': 'COLOMBO',
            'university': 'University of Colombo',
            'course_name': 'Medicine',
            'aptitude_test': True,
            'all_island_merit': False
        },
        {
            'year': 2023,
            'z_score': 1.8,
            'stream': 'Biological',
            'district': 'KANDY',
            'university': 'University of Peradeniya',
            'course_name': 'Dental Surgery',
            'aptitude_test': True,
            'all_island_merit': False
        },
        {
            'year': 2023,
            'z_score': 1.2,
            'stream': 'Technology',
            'district': 'GAMPAHA',
            'university': 'University of Moratuwa',
            'course_name': 'Computer Science and Engineering',
            'aptitude_test': False,
            'all_island_merit': True
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\nTest Case {i}:")
        logger.info(f"Stream: {test_case['stream']}, Z-Score: {test_case['z_score']}")
        logger.info(f"Course: {test_case['course_name']} at {test_case['university']}")
        
        try:
            # Test cutoff prediction
            cutoff = ml_predictor_instance.predict_cutoff(
                year=test_case['year'],
                university=test_case['university'],
                course_name=test_case['course_name'],
                district=test_case['district'],
                stream=test_case['stream'],
                aptitude_test=test_case['aptitude_test'],
                all_island_merit=test_case['all_island_merit']
            )
            logger.info(f"✓ Cutoff prediction: {cutoff:.3f}")
            
            # Test probability prediction
            prob = ml_predictor_instance.predict_selection_probability(
                z_score=test_case['z_score'],
                stream=test_case['stream'],
                district=test_case['district'],
                course_name=test_case['course_name'],
                university=test_case['university'],
                aptitude_test=test_case['aptitude_test'],
                all_island_merit=test_case['all_island_merit']
            )
            logger.info(f"✓ Selection probability: {prob*100:.1f}%")
            
            # Get recommendation
            recommendation = ml_predictor_instance.get_recommendation_status(prob)
            logger.info(f"✓ Recommendation: {recommendation}")
            
        except Exception as e:
            logger.error(f"✗ Prediction failed: {str(e)}")
            return False
    
    return True

def test_course_filtering():
    """Test course filtering by stream."""
    logger.info("\nTesting course filtering by stream...")
    
    test_streams = ['Physical Science', 'Biological Science', 'Engineering Technology', 'Commerce', 'Arts']
    
    for stream in test_streams:
        logger.info(f"\nTesting stream: {stream}")
        try:
            courses = ml_predictor_instance.get_available_courses_for_stream(stream, limit=5)
            if not courses:
                logger.warning(f"No courses found for stream: {stream}")
                continue
                
            logger.info(f"Found {len(courses)} courses for {stream} stream:")
            for i, course in enumerate(courses[:5], 1):  # Show first 5 courses
                logger.info(f"  {i}. {course['course_name']} at {course['university_name']}")
                
        except Exception as e:
            logger.error(f"Error filtering courses for {stream}: {str(e)}")
            return False
    
    return True

if __name__ == "__main__":
    logger.info("Starting prediction system test...")
    
    # Test 1: Check model loading
    if not test_ml_loading():
        logger.error("ML model loading test failed!")
        sys.exit(1)
    
    # Test 2: Test predictions
    if not test_prediction():
        logger.error("Prediction test failed!")
        sys.exit(1)
    
    # Test 3: Test course filtering
    if not test_course_filtering():
        logger.error("Course filtering test failed!")
        sys.exit(1)
    
    logger.info("\n✅ All tests completed successfully!")
