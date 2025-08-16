#!/usr/bin/env python
import requests
import json

def test_admin_dashboard():
    """Simple test for admin dashboard access"""
    print("=== Simple Admin Dashboard Test ===")
    
    # Step 1: Login
    login_url = "http://127.0.0.1:8000/api/admin/login/"
    login_data = {
        "email": "Admin@gmail.com",
        "password": "admin123"
    }
    
    print("1. Testing admin login...")
    try:
        response = requests.post(login_url, json=login_data)
        print(f"   Login Status: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access')
            print(f"   Login SUCCESS! Got access token.")
            
            # Step 2: Test dashboard
            dashboard_url = "http://127.0.0.1:8000/api/admin/dashboard/"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            print("2. Testing dashboard access...")
            dashboard_response = requests.get(dashboard_url, headers=headers)
            print(f"   Dashboard Status: {dashboard_response.status_code}")
            
            if dashboard_response.status_code == 200:
                print("   Dashboard SUCCESS!")
                data = dashboard_response.json()
                if 'uploads' in data:
                    uploads = data['uploads']
                    print(f"   Found {len(uploads)} uploads in response")
                    for upload in uploads:
                        print(f"     - {upload.get('filename', 'Unknown')}")
                else:
                    print("   No 'uploads' key found in response")
                    print(f"   Response keys: {list(data.keys())}")
            else:
                print(f"   Dashboard FAILED: {dashboard_response.text}")
                
        else:
            print(f"   Login FAILED: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("   ERROR: Cannot connect to server. Make sure Django is running on http://127.0.0.1:8000")
    except Exception as e:
        print(f"   ERROR: {e}")

if __name__ == '__main__':
    test_admin_dashboard()
