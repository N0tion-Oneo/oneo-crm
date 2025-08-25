#!/usr/bin/env python
"""
Test that sync configuration is strictly respected without overrides
"""
import os
import sys
import django
import logging
from datetime import datetime, timezone

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from communications.models import Channel, Message, Conversation
from communications.channels.whatsapp.sync.comprehensive import ComprehensiveSyncService
from communications.channels.whatsapp.sync.config import get_sync_options

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    print("\n" + "="*60)
    print("Testing Strict Config Enforcement")
    print("="*60)
    
    # Switch to oneotalent tenant
    with schema_context('oneotalent'):
        # Get the WhatsApp channel
        channel = Channel.objects.filter(
            channel_type='whatsapp',
            is_active=True
        ).first()
        
        if not channel:
            print("❌ No active WhatsApp channel found")
            return
            
        print(f"✅ Found channel: {channel.name}")
        
        # Test 1: Check that get_sync_options ignores overrides
        print("\n📋 Testing get_sync_options():")
        
        # Try with no overrides
        config_no_override = get_sync_options()
        print(f"   No overrides: {config_no_override}")
        
        # Try with frontend-style overrides (should be ignored)
        frontend_overrides = {
            'days_back': 30,
            'max_messages_per_chat': 500,  # This should be ignored
            'max_conversations': 999,  # This should be ignored
            'conversations_per_batch': 50,
            'messages_per_batch': 100
        }
        config_with_override = get_sync_options(frontend_overrides)
        print(f"   With overrides: {config_with_override}")
        
        # Verify they're the same (overrides ignored)
        if config_no_override == config_with_override:
            print("   ✅ Overrides correctly IGNORED - configs are identical")
        else:
            print("   ❌ ERROR: Overrides were applied!")
            print(f"      Expected: {config_no_override}")
            print(f"      Got: {config_with_override}")
            
        # Test 2: Run actual sync with frontend-style options
        print("\n🚀 Running actual sync with frontend overrides (should be ignored):")
        
        # Clear existing data first
        Message.objects.filter(conversation__channel=channel).delete()
        Conversation.objects.filter(channel=channel).delete()
        print("   ✅ Cleared existing data")
        
        # Initialize sync service
        sync = ComprehensiveSyncService(channel=channel)
        
        # Run the sync with frontend-style options (should be ignored)
        print("\n   Starting sync with frontend overrides...")
        print(f"   Passing options: {frontend_overrides}")
        
        # Get expected options (what should actually be used)
        expected_options = get_sync_options()
        print(f"   Expected to use: {expected_options}")
        
        try:
            result = sync.run_comprehensive_sync(options=frontend_overrides)
            
            # Check results
            print(f"\n   Sync completed:")
            print(f"   - Conversations synced: {result.get('conversations_synced', 0)}")
            print(f"   - Messages synced: {result.get('messages_synced', 0)}")
            
            # Verify it respected the config limits
            if result.get('conversations_synced', 0) <= expected_options['max_conversations']:
                print(f"   ✅ Respected max_conversations limit ({expected_options['max_conversations']})")
            else:
                print(f"   ❌ Exceeded max_conversations limit!")
                
        except Exception as e:
            print(f"   ❌ Sync failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("✅ Test Complete")
    print("="*60)

if __name__ == '__main__':
    main()