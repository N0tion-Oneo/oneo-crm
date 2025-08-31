#!/usr/bin/env python
"""
Script to remove duplicate UserChannelConnection
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

def remove_duplicate_connection(schema_name='oneotalent'):
    """Remove the admin@oneotalent.com connection for WhatsApp"""
    
    print(f"\nRemoving duplicate connection in schema: {schema_name}")
    
    with schema_context(schema_name):
        # Find the admin@oneotalent.com user
        admin_user = User.objects.filter(username='admin@oneotalent.com').first()
        
        if admin_user:
            # Find and delete the WhatsApp connection for this user
            connection = UserChannelConnection.objects.filter(
                user=admin_user,
                unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA',
                channel_type='whatsapp'
            ).first()
            
            if connection:
                print(f"Found duplicate connection:")
                print(f"  Account ID: {connection.unipile_account_id}")
                print(f"  Channel: {connection.channel_type}")
                print(f"  User: {connection.user.username}")
                print(f"  Deleting...")
                connection.delete()
                print("  ✓ Deleted successfully")
            else:
                print("No duplicate connection found for admin@oneotalent.com")
        else:
            print("admin@oneotalent.com user not found")
        
        # Verify remaining connections
        print("\n=== REMAINING WHATSAPP CONNECTIONS ===")
        for conn in UserChannelConnection.objects.filter(
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
        ).select_related('user'):
            user_display = conn.user.get_full_name() or conn.user.username if conn.user else "No user"
            print(f"Connection: {conn.unipile_account_id}")
            print(f"  Channel: {conn.channel_type}")
            print(f"  User: {user_display}")
            print(f"  Email: {conn.user.email if conn.user else 'None'}")

if __name__ == '__main__':
    remove_duplicate_connection()