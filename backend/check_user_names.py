#!/usr/bin/env python
"""
Script to check user names in UserChannelConnection
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import UserChannelConnection
from django.contrib.auth import get_user_model

User = get_user_model()

def check_user_names(schema_name='oneotalent'):
    """Check user names and connections"""
    
    print(f"\nChecking users in schema: {schema_name}")
    
    with schema_context(schema_name):
        # Check all users
        print("\n=== ALL USERS ===")
        for user in User.objects.all():
            full_name = user.get_full_name()
            print(f"User ID: {user.id}")
            print(f"  Username: {user.username}")
            print(f"  Email: {user.email}")
            print(f"  First Name: {user.first_name}")
            print(f"  Last Name: {user.last_name}")
            print(f"  Full Name: {full_name}")
            print(f"  Display: {full_name or user.username}")
            print()
        
        # Check UserChannelConnections
        print("\n=== USER CHANNEL CONNECTIONS ===")
        for conn in UserChannelConnection.objects.select_related('user').all():
            if conn.user:
                user_display = conn.user.get_full_name() or conn.user.username
            else:
                user_display = "No user linked"
            
            print(f"Connection: {conn.unipile_account_id}")
            print(f"  Channel Type: {conn.channel_type}")
            print(f"  Account Name: {conn.account_name}")
            print(f"  Linked User: {conn.user.username if conn.user else 'None'}")
            print(f"  User Display Name: {user_display}")
            print(f"  User Email: {conn.user.email if conn.user else 'None'}")
            print()

if __name__ == '__main__':
    check_user_names()