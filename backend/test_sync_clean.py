#!/usr/bin/env python
"""
Clean test script to run comprehensive WhatsApp sync
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from communications.models import Channel, UserChannelConnection
from communications.channels.whatsapp.sync.comprehensive import ComprehensiveSyncService

def run_sync():
    """Run comprehensive sync with proper configuration"""
    
    # Use OneOTalent tenant
    tenant_schema = 'oneotalent'
    
    with schema_context(tenant_schema):
        # Get WhatsApp channel
        channel = Channel.objects.filter(channel_type='whatsapp').first()
        if not channel:
            print("❌ No WhatsApp channel found")
            return
        
        # Get connection
        connection = UserChannelConnection.objects.filter(channel_type='whatsapp').first()
        
        print(f"📱 Running sync for: {channel.name}")
        print(f"   Account ID: {connection.unipile_account_id if connection else 'N/A'}")
        
        # Run sync with default config (which uses environment variables)
        sync_service = ComprehensiveSyncService(
            channel=channel,
            connection=connection
        )
        
        # Run comprehensive sync
        stats = sync_service.run_comprehensive_sync()
        
        # Print results
        print(f"\n📊 Sync Results:")
        print(f"   - {stats['conversations_synced']} conversations synced")
        print(f"   - {stats['messages_synced']} messages across all conversations")
        print(f"   - {stats['attendees_synced']} attendees synced")
        
        if stats.get('incomplete_conversations'):
            print(f"\n⚠️ Incomplete conversations:")
            for conv_name, synced, target in stats['incomplete_conversations'][:5]:
                print(f"   - {conv_name}: {synced}/{target} messages")
        
        print("\n✅ Sync completed!")

if __name__ == '__main__':
    run_sync()