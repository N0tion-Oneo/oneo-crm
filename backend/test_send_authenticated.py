#!/usr/bin/env python3
import requests
import json

# Test JWT token (valid for 1 hour)
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU1NzA0ODgzLCJpYXQiOjE3NTU3MDEyODMsImp0aSI6IjIxZmJlM2NjOThkNzRiNzk4NWRlMTljNWFhZTllNGIxIiwidXNlcl9pZCI6MX0.lBJkEtXzdBuQsIj1DCc4uQEXvRXdH7dQzR9bh3FnBOs"

# API call
url = "http://demo.localhost:8000/api/v1/communications/whatsapp/chats/test123/send/"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}
data = {
    "text": "Hello World from API test!"
}

print(f"🚀 Testing Message Sending API")
print(f"URL: {url}")
print(f"Data: {json.dumps(data, indent=2)}")
print()

try:
    response = requests.post(url, headers=headers, json=data, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print()
    
    if response.headers.get('content-type', '').startswith('application/json'):
        try:
            result = response.json()
            print("Response JSON:")
            print(json.dumps(result, indent=2))
        except:
            print(f"Raw Response: {response.text}")
    else:
        print(f"Raw Response: {response.text}")
        
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")