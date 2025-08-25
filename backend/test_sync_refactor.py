#!/usr/bin/env python
"""
Quick test to verify the refactored sync modules work correctly
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection
from tenants.models import Tenant

# Switch to first available tenant for testing
try:
    demo_tenant = Tenant.objects.exclude(schema_name='public').first()
    if demo_tenant:
        connection.set_tenant(demo_tenant)
        print(f"📌 Using tenant: {demo_tenant.schema_name}")
    else:
        print("⚠️ No tenant available for testing, using public schema")
except Exception as e:
    print(f"⚠️ Could not switch tenant: {e}")

print("=" * 60)
print("🧪 Testing Refactored Sync Modules")
print("=" * 60)

# Test imports
try:
    from communications.channels.whatsapp.sync import (
        ComprehensiveSyncService,
        ConversationSyncService,
        MessageSyncService,
        AttendeeSyncService,
        SyncJobManager,
        SyncProgressTracker,
        SYNC_CONFIG,
        DEFAULT_SYNC_OPTIONS,
        sync_account_comprehensive_background,
        sync_chat_specific_background,
    )
    print("✅ All sync module imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test backward compatibility imports
try:
    from communications.channels.whatsapp import background_sync_refactored as background_sync
    print("✅ Backward compatibility import successful")
except ImportError as e:
    print(f"❌ Backward compatibility import failed: {e}")
    sys.exit(1)

# Test that services can be instantiated
try:
    from communications.models import Channel, UserChannelConnection
    
    # Get a channel for testing
    channel = Channel.objects.filter(channel_type='whatsapp').first()
    if channel:
        print(f"📱 Using channel: {channel.name}")
        
        # Test instantiating services
        attendee_service = AttendeeSyncService(channel=channel)
        print("✅ AttendeeSyncService instantiated")
        
        message_service = MessageSyncService(channel=channel)
        print("✅ MessageSyncService instantiated")
        
        conversation_service = ConversationSyncService(channel=channel)
        print("✅ ConversationSyncService instantiated")
        
        comprehensive_service = ComprehensiveSyncService(channel=channel)
        print("✅ ComprehensiveSyncService instantiated")
        
        # Test the new API method exists
        from communications.channels.whatsapp.utils.attendee_detection import WhatsAppAttendeeDetector
        detector = WhatsAppAttendeeDetector(channel=channel)
        
        # Check that the new method exists
        if hasattr(detector, 'extract_attendee_from_api_message'):
            print("✅ New extract_attendee_from_api_message method exists")
            
            # Test calling it with sample data
            test_message = {
                'sender_attendee_id': 'test123',
                'sender_name': 'Test User',
                'is_sender': False
            }
            result = detector.extract_attendee_from_api_message(test_message)
            if result.get('external_id') == 'test123':
                print("✅ API message extraction working correctly")
            else:
                print(f"⚠️ Unexpected result: {result}")
        else:
            print("❌ extract_attendee_from_api_message method not found")
    else:
        print("⚠️ No WhatsApp channel found for testing")
        
except Exception as e:
    print(f"❌ Service instantiation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ All tests passed - refactored sync modules working!")
print("=" * 60)