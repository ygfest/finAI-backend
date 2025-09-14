#!/usr/bin/env python3
"""
Quick test script to verify login error handling
"""
import requests
import json

# Test invalid credentials
def test_invalid_credentials():
    url = "http://localhost:8000/auth/login"
    data = {
        "email": "test@example.com",
        "password": "wrongpassword"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 401:
            print("✅ Invalid credentials properly handled with 401 status")
        else:
            print("❌ Expected 401 status for invalid credentials")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_invalid_credentials()
