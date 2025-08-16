#!/usr/bin/env python
import requests
import json
import time

def test_chat_performance():
    """Test chat endpoint performance with multiple requests"""
    print("=== Chat Performance Test ===")
    
    # Step 1: Login to get student token (you'll need a student account)
    # For now, let's test with admin token to see if the optimization works
    login_url = "http://127.0.0.1:8000/api/admin/login/"
    login_data = {
        "email": "Admin@gmail.com",
        "password": "admin123"
    }
    
    print("1. Getting authentication token...")
    response = requests.post(login_url, json=login_data)
    if response.status_code != 200:
        print(f"   Login failed: {response.status_code}")
        return
        
    token_data = response.json()
    access_token = token_data.get('access')
    print("   Token obtained!")
    
    # Step 2: Test chat endpoint multiple times to measure performance
    chat_url = "http://127.0.0.1:8000/api/chat/"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    test_questions = [
        "What is the university admission process?",
        "How do I apply for scholarships?", 
        "What are the course requirements?"
    ]
    
    print("2. Testing chat endpoint performance...")
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n   Request {i}: '{question[:30]}...'")
        
        start_time = time.time()
        
        try:
            chat_response = requests.post(chat_url, headers=headers, json={
                'question': question
            }, timeout=60)  # 60 second timeout
            
            end_time = time.time()
            response_time = end_time - start_time
            
            print(f"   Status: {chat_response.status_code}")
            print(f"   Response time: {response_time:.2f} seconds")
            
            if chat_response.status_code == 200:
                data = chat_response.json()
                answer = data.get('answer', 'No answer')
                print(f"   Answer preview: {answer[:50]}...")
                
                # Performance analysis
                if response_time < 5:
                    print("   ✅ FAST response!")
                elif response_time < 15:
                    print("   ⚠️ Moderate response time")
                else:
                    print("   ❌ SLOW response")
            else:
                print(f"   Error: {chat_response.text}")
                
        except requests.exceptions.Timeout:
            print("   ❌ TIMEOUT (>60 seconds)")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    print("\n3. Performance Summary:")
    print("   - First request: May be slow (model loading)")
    print("   - Subsequent requests: Should be much faster (cached models)")
    print("   - Target: <5 seconds for cached requests")

if __name__ == '__main__':
    test_chat_performance()
