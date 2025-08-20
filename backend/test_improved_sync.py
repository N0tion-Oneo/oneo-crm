#!/usr/bin/env python3
"""
Test the improved comprehensive sync
"""
import os
import sys
import asyncio
import django
from pathlib import Path

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import tenant_context
from tenants.models import Tenant
from communications.models import Channel
from communications.services.comprehensive_sync import comprehensive_sync_service
from asgiref.sync import sync_to_async

async def test_improved_sync():
    """Test the improved comprehensive sync with missing attendee handling"""
    
    # Get tenant context
    tenant = await sync_to_async(Tenant.objects.get)(schema_name='oneotalent')
    
    with tenant_context(tenant):
        # Get WhatsApp channel
        channel = await sync_to_async(Channel.objects.filter(channel_type='whatsapp').first)()
        
        if not channel:
            print("❌ No WhatsApp channel found")
            return
            
        print(f"🔄 Testing improved comprehensive sync for {channel.name}")
        
        try:
            # Run comprehensive sync
            stats = await comprehensive_sync_service.sync_account_comprehensive(
                channel=channel,
                days_back=30,
                max_messages_per_chat=10
            )
            
            print(f"✅ Comprehensive sync completed:")
            print(f"  - Attendees synced: {stats['attendees_synced']}")
            print(f"  - Conversations created: {stats['conversations_created']}")  
            print(f"  - Conversations updated: {stats['conversations_updated']}")
            print(f"  - Messages synced: {stats['messages_synced']}")
            
            if 'missing_attendees' in stats:
                print(f"  - Missing attendees found: {stats['missing_attendees']}")
                
        except Exception as e:
            print(f"❌ Sync failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_improved_sync())