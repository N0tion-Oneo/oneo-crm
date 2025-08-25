#!/usr/bin/env python
"""
Test manual sync trigger
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from communications.models import Channel, UserChannelConnection
from communications.channels.whatsapp.sync.tasks import sync_account_comprehensive_background

User = get_user_model()

def test_manual_sync():
    """Test triggering sync manually"""
    
    # Use oneotalent tenant
    with schema_context('oneotalent'):
        print("\n🧪 Testing Manual Sync Trigger")
        print("=" * 50)
        
        # Get user
        user = User.objects.filter(email='josh@oneodigital.com').first()
        if not user:
            print("❌ User not found")
            return
        
        print(f"✅ Found user: {user.email}")
        
        # Get channel
        channel = Channel.objects.filter(
            channel_type='whatsapp',
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
        ).first()
        
        if not channel:
            print("❌ Channel not found")
            return
            
        print(f"✅ Found channel: {channel.name} ({channel.id})")
        
        # Get connection
        connection = UserChannelConnection.objects.filter(
            user=user,
            channel_type='whatsapp',
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
        ).first()
        
        if connection:
            print(f"✅ Found connection: {connection.account_name}")
        else:
            print("⚠️ No connection found, but continuing")
        
        # Trigger sync
        print("\n🚀 Triggering background sync...")
        
        # Call the task synchronously for testing
        result = sync_account_comprehensive_background(
            channel_id=str(channel.id),
            user_id=str(user.id),
            sync_options={
                'max_conversations': 5,
                'max_messages_per_chat': 20,
                'days_back': 7
            },
            tenant_schema='oneotalent'
        )
        
        print(f"\n📊 Sync result: {result}")
        
        if result.get('success'):
            print("✅ Sync completed successfully!")
            if result.get('stats'):
                stats = result['stats']
                print(f"  - Conversations synced: {stats.get('conversations_synced', 0)}")
                print(f"  - Messages synced: {stats.get('messages_synced', 0)}")
                print(f"  - Attendees synced: {stats.get('attendees_synced', 0)}")
        else:
            print(f"❌ Sync failed: {result.get('error')}")

if __name__ == '__main__':
    test_manual_sync()