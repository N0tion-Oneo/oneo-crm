#!/usr/bin/env python
"""
Setup email connection for testing
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection
from authentication.models import User

def setup_email_connection():
    """Setup email connection for testing"""
    
    # Use oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print(f"🏢 Setting up in tenant: {tenant.name} ({tenant.schema_name})")
        
        # Check existing connections
        connections = UserChannelConnection.objects.all()
        print(f"\n📧 Existing connections: {connections.count()}")
        for conn in connections:
            print(f"   - {conn.channel_type}: {conn.account_name} (Active: {conn.is_active})")
        
        # Get or create email connection
        admin_user = User.objects.filter(is_admin=True).first()
        if not admin_user:
            print("❌ No admin user found")
            return
            
        # Check if we have an email connection
        email_conn = UserChannelConnection.objects.filter(
            channel_type='email'
        ).first()
        
        if email_conn:
            # Activate it
            email_conn.is_active = True
            email_conn.save()
            print(f"\n✅ Activated existing email connection: {email_conn.account_name}")
        else:
            # Create a test email connection
            email_conn = UserChannelConnection.objects.create(
                user=admin_user,
                channel_type='email',
                account_name='josh@oneotalent.com',
                account_email='josh@oneotalent.com',
                unipile_account_id='test_account_id',  # This would normally come from UniPile
                is_active=True,
                auth_status='authenticated',
                account_status='active'
            )
            print(f"\n✅ Created new email connection: {email_conn.account_name}")
        
        # Show final state
        active_count = UserChannelConnection.objects.filter(is_active=True).count()
        print(f"\n📊 Total active connections: {active_count}")

if __name__ == '__main__':
    setup_email_connection()