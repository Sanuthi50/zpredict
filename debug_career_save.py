#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('c:\\Sanuthi BSC\\Sem 3\\Zpredict\\zpredict')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zpredict.settings')
django.setup()

from api.models import CareerSession, SavedCareerPrediction, User
from api.serializers import SavedCareerPredictionCreateSerializer
from rest_framework.test import APIRequestFactory
import json

# Get test data
user = User.objects.filter(user_type='student').first()
session = CareerSession.objects.filter(student=user).first() if user else None

print(f"User: {user.email if user else 'None'}")
print(f"Session: {session.id if session else 'None'}")

if user and session:
    # Simulate the exact request from frontend
    factory = APIRequestFactory()
    request_data = {
        'career_code': 'TEST456',
        'career_title': 'Software Engineer',
        'match_score': 0.85,
        'session_id': session.id,
        'recommended_level': 'Recommended',
        'notes': 'Saved from career prediction system'
    }
    
    print(f"Testing with data: {request_data}")
    
    # Create request
    request = factory.post('/api/career-predictions/', 
                          data=json.dumps(request_data),
                          content_type='application/json')
    request.user = user
    
    # Test serializer
    serializer = SavedCareerPredictionCreateSerializer(
        data=request_data, 
        context={'request': request}
    )
    
    print(f"Serializer valid: {serializer.is_valid()}")
    
    if not serializer.is_valid():
        print(f"Validation errors: {serializer.errors}")
    else:
        try:
            instance = serializer.save(student=user)
            print(f"SUCCESS: Created {instance}")
            print(f"Saved to DB with ID: {instance.id}")
        except Exception as e:
            print(f"ERROR saving: {e}")
            import traceback
            traceback.print_exc()

# Check current count
print(f"\nCurrent SavedCareerPrediction count: {SavedCareerPrediction.objects.count()}")
