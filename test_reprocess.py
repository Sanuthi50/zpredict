#!/usr/bin/env python
import requests
import json

def test_reprocess_functionality():
    """Test the reprocess page and API endpoint"""
    print("=== Reprocess Functionality Test ===")
    
    # Step 1: Login to get token
    login_url = "http://127.0.0.1:8000/api/admin/login/"
    login_data = {
        "email": "Admin@gmail.com",
        "password": "admin123"
    }
    
    print("1. Getting admin token...")
    try:
        response = requests.post(login_url, json=login_data)
        if response.status_code != 200:
            print(f"   Login failed: {response.status_code}")
            return
            
        token_data = response.json()
        access_token = token_data.get('access')
        print("   Login successful!")
        
        # Step 2: Test reprocess page access (GET)
        reprocess_page_url = "http://127.0.0.1:8000/admin-reprocess/"
        print("2. Testing reprocess page access...")
        
        # Test with token in cookie (simulating browser)
        cookies = {'admin_token': access_token}
        page_response = requests.get(reprocess_page_url, cookies=cookies)
        print(f"   Reprocess page status: {page_response.status_code}")
        
        if page_response.status_code == 200:
            print("   Reprocess page accessible!")
        else:
            print(f"   Reprocess page failed: {page_response.text[:200]}")
        
        # Step 3: Test admin verify API
        verify_url = "http://127.0.0.1:8000/api/admin/verify/"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        print("3. Testing admin verify API...")
        verify_response = requests.get(verify_url, headers=headers)
        print(f"   Admin verify status: {verify_response.status_code}")
        print(f"   Admin verify response: {verify_response.text}")
        
        # Step 4: Test reprocess PDF API
        reprocess_api_url = "http://127.0.0.1:8000/api/admin/reprocess-pdf/"
        print("4. Testing reprocess PDF API...")
        
        reprocess_response = requests.post(reprocess_api_url, headers=headers)
        print(f"   Reprocess API status: {reprocess_response.status_code}")
        print(f"   Reprocess API response: {reprocess_response.text}")
        
    except requests.exceptions.ConnectionError:
        print("   ERROR: Cannot connect to server.")
    except Exception as e:
        print(f"   ERROR: {e}")

if __name__ == '__main__':
    test_reprocess_functionality()
