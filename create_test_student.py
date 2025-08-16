#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(r'c:\Sanuthi BSC\Sem 3\Zpredict\zpredict')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zpredict.settings')
django.setup()

from api.models import User

def create_test_student():
    """Create a test student account for chat testing"""
    print("=== Creating Test Student Account ===")
    
    # Check if test student already exists
    test_email = "teststudent@test.com"
    existing_student = User.objects.filter(email=test_email).first()
    
    if existing_student:
        print(f"Test student already exists: {test_email}")
        print(f"Password: test123")
        return
    
    # Create test student
    try:
        student = User.objects.create_user(
            email=test_email,
            password="test123",
            first_name="Test",
            last_name="Student",
            user_type="student",
            is_active=True
        )
        
        print(f"✅ Test student created successfully!")
        print(f"Email: {test_email}")
        print(f"Password: test123")
        print(f"User type: {student.user_type}")
        print(f"Active: {student.is_active}")
        
    except Exception as e:
        print(f"❌ Failed to create test student: {e}")

if __name__ == '__main__':
    create_test_student()
