#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('c:\\Sanuthi BSC\\Sem 3\\Zpredict\\zpredict')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zpredict.settings')
django.setup()

from api.serializers import SavedCareerPredictionCreateSerializer
from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model
from api.models import CareerSession

User = get_user_model()

# Get a test user and session
user = User.objects.filter(user_type='student').first()
session = CareerSession.objects.first()

print(f"Testing with user: {user.email if user else 'None'}")
print(f"Testing with session: {session.id if session else 'None'}")

if user and session:
    # Create a mock request
    factory = APIRequestFactory()
    request = factory.post('/')
    request.user = user
    
    # Test data
    data = {
        'career_code': 'TEST123',
        'career_title': 'Test Career',
        'match_score': 0.8,
        'session_id': session.id,
        'notes': 'test'
    }
    
    print(f"Test data: {data}")
    
    # Test serializer
    serializer = SavedCareerPredictionCreateSerializer(data=data, context={'request': request})
    print(f"Is valid: {serializer.is_valid()}")
    
    if not serializer.is_valid():
        print(f"Errors: {serializer.errors}")
    else:
        print("Serializer validation passed!")
        
        # Try to save
        try:
            instance = serializer.save(student=user)
            print(f"Successfully created: {instance}")
        except Exception as e:
            print(f"Error saving: {e}")
else:
    print("No test user or session found")
