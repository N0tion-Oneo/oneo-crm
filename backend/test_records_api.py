#!/usr/bin/env python3
"""
Test script to debug the 500 error with records API
"""
import requests
import json

def test_records_api():
    """Test the records API with proper authentication"""
    
    # First get a token
    login_data = {'email': 'josh@oneodigital.com', 'password': 'Admin123!'}
    response = requests.post('http://oneotalent.localhost:8000/auth/login/', json=login_data)
    print('Login response:', response.status_code)
    
    if response.status_code == 200:
        token = response.json()['access']
        print('Token obtained successfully')
        
        # Now try to get records
        headers = {'Authorization': f'Bearer {token}'}
        records_response = requests.get('http://oneotalent.localhost:8000/api/pipelines/1/records/?page=1&page_size=50&ordering=-updated_at', headers=headers)
        print('Records response status:', records_response.status_code)
        
        if records_response.status_code != 200:
            print('Records response text:', records_response.text)
            print('Records response headers:', dict(records_response.headers))
        else:
            print('Records API working correctly')
            data = records_response.json()
            print(f'Got {len(data.get("results", []))} records')
    else:
        print('Login failed:', response.text)

if __name__ == "__main__":
    test_records_api()