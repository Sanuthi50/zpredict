#!/usr/bin/env python
import os
import sys
import django
import requests
import json

# Add the project directory to the Python path
sys.path.append(r'c:\Sanuthi BSC\Sem 3\Zpredict\zpredict')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zpredict.settings')
django.setup()

from api.models import User

def create_and_test_student():
    """Create test student and test chat"""
    print("=== Student Chat Test ===")
    
    # Create test student if doesn't exist
    test_email = "teststudent@test.com"
    existing_student = User.objects.filter(email=test_email).first()
    
    if not existing_student:
        print("Creating test student...")
        try:
            student = User.objects.create_user(
                email=test_email,
                password="test123",
                first_name="Test",
                last_name="Student",
                user_type="student",
                is_active=True
            )
            print(f"Student created: {test_email}")
        except Exception as e:
            print(f"Failed to create student: {e}")
            return
    else:
        print(f"Using existing student: {test_email}")
    
    # Test student login
    login_url = "http://127.0.0.1:8000/api/login/"
    login_data = {
        "email": test_email,
        "password": "test123"
    }
    
    print("Testing student login...")
    try:
        response = requests.post(login_url, json=login_data)
        print(f"Login status: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access')
            print("Student login successful!")
            
            # Test chat
            chat_url = "http://127.0.0.1:8000/api/chat/"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            print("Testing chat endpoint...")
            chat_response = requests.post(chat_url, headers=headers, json={
                'question': 'Hello, can you help me?'
            }, timeout=30)
            
            print(f"Chat status: {chat_response.status_code}")
            print(f"Chat response: {chat_response.text[:200]}...")
            
        else:
            print(f"Login failed: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    create_and_test_student()
