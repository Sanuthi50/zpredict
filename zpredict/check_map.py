import joblib
import os

try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'api', 'ml_model', 'valid_courses_map.pkl')
    print(f"Loading file from: {file_path}")
    print(f"File exists: {os.path.exists(file_path)}")
    print(f"File size: {os.path.getsize(file_path)} bytes")
    
    data = joblib.load(file_path)
    print('\nContent type:', type(data))
    if isinstance(data, dict):
        print('Number of items:', len(data))
        print('Sample items:', list(data.items())[:5])
    elif hasattr(data, '__len__'):
        print('Number of items:', len(data))
        print('Sample items:', data[:5])
    else:
        print('Content:', data)
except Exception as e:
    print(f"Error: {str(e)}")
