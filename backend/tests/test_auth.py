#!/usr/bin/env python

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import authenticate, get_user_model
from django.db import connection
from django_tenants.utils import schema_context

User = get_user_model()

print("=== Testing Authentication ===")

# Test within testorg tenant context
with schema_context('testorg'):
    print(f"\nCurrent schema: {connection.schema_name}")
    
    # List all users
    users = User.objects.all()
    print(f"\nAll users in testorg schema:")
    for user in users:
        print(f"  - ID: {user.id}, Email: {user.email}, Username: {user.username}")
        print(f"    User Type: {user.user_type}")
        print(f"    Is Active: {user.is_active}")
        print(f"    Is Staff: {user.is_staff}")
    
    try:
        # Test authentication with email (since USERNAME_FIELD = 'email')
        print(f"\n=== Testing authenticate() with email ===")
        user1 = authenticate(username='test@testorg.co.za', password='Test123!')
        print(f"authenticate(username='test@testorg.co.za', password='Test123!'): {user1}")
        
        # Test authentication with username field
        print(f"\n=== Testing authenticate() with actual username ===")
        user2 = authenticate(username='test_testorg_user', password='Test123!')
        print(f"authenticate(username='test_testorg_user', password='Test123!'): {user2}")
        
        # Try to get user directly and check password
        print(f"\n=== Direct password verification ===")
        user = User.objects.get(email='test@testorg.co.za')
        password_valid = user.check_password('Test123!')
        print(f"User found: {user}")
        print(f"Password valid for 'Test123!': {password_valid}")
        
        # Test with different passwords
        password_valid2 = user.check_password('admin123')
        print(f"Password valid for 'admin123': {password_valid2}")
        
    except Exception as e:
        print(f"Error during authentication test: {e}")
        import traceback
        traceback.print_exc()

print("\n=== Test Complete ===")