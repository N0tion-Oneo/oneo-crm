#!/usr/bin/env python
"""
Check if there are active WhatsApp connections
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from django.contrib.auth import get_user_model
from communications.models import UserChannelConnection

User = get_user_model()

def check_connections():
    """Check WhatsApp connections"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print("\n🔍 Checking WhatsApp Connections")
        print("=" * 60)
        
        # Get a user
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ No active user found")
            return
            
        print(f"✅ User: {user.username}")
        
        # Get all WhatsApp connections for the current user
        whatsapp_connections = UserChannelConnection.objects.filter(
            user=user,
            channel_type='whatsapp',
            is_active=True,
            unipile_account_id__isnull=False
        )
        
        print(f"\n📊 Found {whatsapp_connections.count()} active WhatsApp connections:")
        
        for conn in whatsapp_connections:
            print(f"\n   Connection ID: {conn.id}")
            print(f"   Account name: {conn.account_name}")
            print(f"   UniPile account ID: {conn.unipile_account_id}")
            print(f"   Auth status: {conn.auth_status}")
            print(f"   Is active: {conn.is_active}")
            print(f"   Config: {conn.connection_config}")
        
        if not whatsapp_connections.exists():
            print("\n⚠️ No active WhatsApp connections found for this user")
            
            # Check all connections
            all_connections = UserChannelConnection.objects.filter(
                channel_type='whatsapp'
            )
            
            print(f"\n📊 Total WhatsApp connections in system: {all_connections.count()}")
            for conn in all_connections[:3]:
                print(f"   - User: {conn.user.username}, Active: {conn.is_active}, Account: {conn.unipile_account_id}")

if __name__ == "__main__":
    check_connections()