#!/usr/bin/env python3
"""
Network Connectivity Test Script
Tests various network connections to diagnose Error 10054 issues
"""

import socket
import requests
import time
import sys
import os

def test_basic_connectivity():
    """Test basic internet connectivity"""
    print("Testing basic internet connectivity...")
    
    # Test DNS resolution
    try:
        socket.gethostbyname("www.google.com")
        print("✓ DNS resolution working")
    except socket.gaierror as e:
        print(f"✗ DNS resolution failed: {e}")
        return False
    
    # Test HTTP connectivity
    try:
        response = requests.get("http://httpbin.org/get", timeout=10)
        if response.status_code == 200:
            print("✓ HTTP connectivity working")
        else:
            print(f"✗ HTTP request failed with status: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ HTTP connectivity failed: {e}")
        return False
    
    return True

def test_gemini_api_connectivity():
    """Test Gemini API connectivity"""
    print("\nTesting Gemini API connectivity...")
    
    try:
        import google.generativeai as genai
        
        # Test with a dummy API key to see if we can reach the servers
        test_key = "test_key_for_connectivity_check"
        genai.configure(api_key=test_key)
        
        # This will fail with authentication error, but we can see if it's a network issue
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            # This should fail with auth error, not network error
            response = model.generate_content("test")
        except Exception as e:
            error_msg = str(e).lower()
            if "10054" in error_msg or "forcibly closed" in error_msg:
                print("✗ Gemini API network connectivity failed (Error 10054)")
                return False
            elif "api_key" in error_msg or "authentication" in error_msg:
                print("✓ Gemini API network connectivity working (auth error expected)")
                return True
            else:
                print(f"✓ Gemini API network connectivity working (other error: {e})")
                return True
                
    except ImportError:
        print("✗ google-generativeai package not installed")
        return False
    except Exception as e:
        print(f"✗ Gemini API test failed: {e}")
        return False

def test_local_models():
    """Test local model loading"""
    print("\nTesting local model loading...")
    
    try:
        # Test if we can access the model directory
        model_path = os.path.join(os.getcwd(), "zpredict", "api", "ml_model")
        if os.path.exists(model_path):
            print(f"✓ Model directory exists: {model_path}")
            
            # Check for model files
            model_files = ["regressor.pkl", "classifier.pkl", "classifier_encoder.pkl", 
                          "feature_encoder.pkl", "valid_courses_map.pkl"]
            
            for file in model_files:
                file_path = os.path.join(model_path, file)
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
                    print(f"✓ {file}: {size:.1f} MB")
                else:
                    print(f"✗ {file}: Missing")
        else:
            print(f"✗ Model directory not found: {model_path}")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ Local model test failed: {e}")
        return False

def test_redis_connectivity():
    """Test Redis connectivity"""
    print("\nTesting Redis connectivity...")
    
    try:
        import redis
        r = redis.Redis(host='127.0.0.1', port=6379, db=0, socket_timeout=5)
        r.ping()
        print("✓ Redis connectivity working")
        return True
    except ImportError:
        print("✗ Redis package not installed")
        return False
    except Exception as e:
        print(f"✗ Redis connectivity failed: {e}")
        return False

def main():
    """Run all network tests"""
    print("Network Connectivity Diagnostic Tool")
    print("=" * 40)
    
    tests = [
        test_basic_connectivity,
        test_gemini_api_connectivity,
        test_local_models,
        test_redis_connectivity
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 40)
    print("SUMMARY")
    print("=" * 40)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! Your network should be working fine.")
    else:
        print("✗ Some tests failed. Check the issues above.")
        
        if not results[0]:  # Basic connectivity failed
            print("\nRECOMMENDATIONS:")
            print("1. Check your internet connection")
            print("2. Run the fix_network.bat file as administrator")
            print("3. Restart your computer")
            print("4. Check Windows Defender firewall settings")
        
        if not results[1]:  # Gemini API failed
            print("\nGEMINI API ISSUES:")
            print("1. Check your GEMINI_API_KEY in .env file")
            print("2. Verify the API key is valid")
            print("3. Check if you're behind a corporate firewall/proxy")
            print("4. Try using a different network (mobile hotspot)")

if __name__ == "__main__":
    main()
