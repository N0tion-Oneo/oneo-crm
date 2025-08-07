#!/usr/bin/env python
"""Test field recovery API endpoints"""

import os
import sys
import django

# Set up Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from pipelines.models import Pipeline
from django.test import Client
import json

def test_field_recovery_api():
    User = get_user_model()
    
    # Get test user
    user = User.objects.filter(email='admin@demo.com').first()
    if not user:
        user = User.objects.filter(is_superuser=True).first()
    
    if not user:
        print("No test user found")
        return
    
    print(f'Testing with user: {user.email}')
    
    # Get test pipeline
    pipeline = Pipeline.objects.first()
    if not pipeline:
        print("No pipelines found")
        return
    
    print(f'Testing with pipeline: {pipeline.name} (ID: {pipeline.id})')
    
    # Create test client and force login
    client = Client()
    client.force_login(user)
    
    # Test the deleted fields endpoint
    response = client.get(f'/api/pipelines/{pipeline.id}/fields/deleted/')
    print(f'Status: {response.status_code}')
    
    if response.status_code != 200:
        print(f'Error: {response.content.decode()}')
    else:
        print('Success! Deleted fields endpoint working')
        try:
            data = json.loads(response.content.decode())
            print(f'Found {len(data)} deleted fields')
        except json.JSONDecodeError:
            print('Response is not valid JSON')
            print(f'Content: {response.content.decode()}')

if __name__ == '__main__':
    test_field_recovery_api()