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

def test_jwt_authentication():
    """Test JWT authentication flow"""
    print("=== JWT Authentication Test ===\n")
    
    # Find an admin user
    admin_user = User.objects.filter(user_type='admin').first()
    if not admin_user:
        print("❌ No admin user found!")
        return
    
    print(f"Testing with admin user: {admin_user.email}")
    print(f"User permissions: is_staff={admin_user.is_staff}, is_superuser={admin_user.is_superuser}")
    
    # Test login endpoint
    login_url = "http://127.0.0.1:8000/api/admin/login/"
    login_data = {
        "email": admin_user.email,
        "password": "admin123"  # You may need to adjust this
    }
    
    print(f"\n1. Testing login at: {login_url}")
    try:
        response = requests.post(login_url, json=login_data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access')
            print(f"   ✅ Login successful! Token: {access_token[:20]}...")
            
            # Test dashboard endpoint with token
            dashboard_url = "http://127.0.0.1:8000/api/admin/dashboard/"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            print(f"\n2. Testing dashboard at: {dashboard_url}")
            dashboard_response = requests.get(dashboard_url, headers=headers)
            print(f"   Status: {dashboard_response.status_code}")
            print(f"   Response: {dashboard_response.text[:200]}...")
            
            if dashboard_response.status_code == 200:
                print("   ✅ Dashboard access successful!")
            else:
                print("   ❌ Dashboard access failed!")
                
        else:
            print("   ❌ Login failed!")
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection failed! Make sure Django server is running on http://127.0.0.1:8000")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == '__main__':
    test_jwt_authentication()
