#!/usr/bin/env python
"""
Check channel connections across all tenants
"""
import os
import sys
import django

# Add the backend directory to Python path
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')

# Initialize Django
django.setup()

# Now we can import Django models and functions
from django.contrib.auth import get_user_model
from communications.models import UserChannelConnection
from tenants.models import Tenant
from django_tenants.utils import schema_context

User = get_user_model()

def check_all_connections():
    """Check connections across all tenants"""
    
    # Get all tenants except public
    tenants = Tenant.objects.exclude(schema_name='public')
    
    for tenant in tenants:
        print(f"\n🏢 Tenant: {tenant.name} ({tenant.schema_name})")
        
        with schema_context(tenant.schema_name):
            try:
                # Get users in this tenant
                users = User.objects.all()
                print(f"  👥 Users: {users.count()}")
                
                # Get all channel connections
                connections = UserChannelConnection.objects.all()
                print(f"  📡 Channel connections: {connections.count()}")
                
                for connection in connections:
                    print(f"    - {connection.user.email}: {connection.channel_type} ({connection.unipile_account_id}) - {connection.auth_status}")
                    
                # Find latest Gmail connection for testing
                gmail_connections = connections.filter(channel_type='gmail')
                if gmail_connections.exists():
                    latest_gmail = gmail_connections.first()
                    print(f"  📧 Latest Gmail connection: {latest_gmail.unipile_account_id} for {latest_gmail.user.email}")
                
            except Exception as e:
                print(f"  ❌ Error checking tenant {tenant.schema_name}: {e}")

if __name__ == "__main__":
    print("🔍 Checking channel connections across all tenants...")
    check_all_connections()