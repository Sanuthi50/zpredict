#!/usr/bin/env python
import requests
import json

def debug_reprocess_page():
    """Debug the reprocess page by simulating browser behavior"""
    print("=== Reprocess Page Debug ===")
    
    # Step 1: Login and store tokens like the admin dashboard does
    login_url = "http://127.0.0.1:8000/api/admin/login/"
    login_data = {
        "email": "Admin@gmail.com",
        "password": "admin123"
    }
    
    print("1. Logging in to get tokens...")
    response = requests.post(login_url, json=login_data)
    if response.status_code != 200:
        print(f"   Login failed: {response.status_code}")
        return
        
    token_data = response.json()
    access_token = token_data.get('access')
    refresh_token = token_data.get('refresh')
    
    print(f"   Access token: {access_token[:20]}...")
    print(f"   Refresh token: {refresh_token[:20]}...")
    
    # Step 2: Test the reprocess page with different token methods
    reprocess_page_url = "http://127.0.0.1:8000/admin-reprocess/"
    
    # Method 1: Cookie (like the AdminReprocessView expects)
    print("2. Testing reprocess page with cookie...")
    cookies = {'admin_token': access_token}
    response1 = requests.get(reprocess_page_url, cookies=cookies)
    print(f"   Cookie method status: {response1.status_code}")
    
    # Method 2: GET parameter
    print("3. Testing reprocess page with GET parameter...")
    params = {'token': access_token}
    response2 = requests.get(reprocess_page_url, params=params)
    print(f"   GET param method status: {response2.status_code}")
    
    # Method 3: Authorization header (like API calls)
    print("4. Testing reprocess page with Authorization header...")
    headers = {'Authorization': f'Bearer {access_token}'}
    response3 = requests.get(reprocess_page_url, headers=headers)
    print(f"   Auth header method status: {response3.status_code}")
    
    # Step 4: Check what the page actually returns
    if response1.status_code == 200:
        print("5. Page content analysis...")
        content = response1.text
        if 'reprocessBtn' in content:
            print("   ✓ Reprocess button found in HTML")
        else:
            print("   ✗ Reprocess button NOT found in HTML")
            
        if 'checkAuthStatus' in content:
            print("   ✓ JavaScript auth check found")
        else:
            print("   ✗ JavaScript auth check NOT found")
            
        if 'TOKEN_KEY' in content:
            print("   ✓ Token constants found")
        else:
            print("   ✗ Token constants NOT found")
    
    # Step 5: Test the specific API endpoints the page uses
    print("6. Testing API endpoints used by reprocess page...")
    
    # Test admin verify (used by checkAuthStatus)
    verify_url = "http://127.0.0.1:8000/api/admin/verify/"
    headers = {'Authorization': f'Bearer {access_token}'}
    verify_response = requests.get(verify_url, headers=headers)
    print(f"   Admin verify API: {verify_response.status_code} - {verify_response.text}")
    
    # Test reprocess PDF API
    reprocess_api_url = "http://127.0.0.1:8000/api/admin/reprocess-pdf/"
    reprocess_response = requests.post(reprocess_api_url, headers=headers)
    print(f"   Reprocess PDF API: {reprocess_response.status_code} - {reprocess_response.text}")

if __name__ == '__main__':
    debug_reprocess_page()
