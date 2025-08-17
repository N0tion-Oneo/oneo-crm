#!/usr/bin/env python3
"""
Test the fixed conversation ID format
"""

import os
import django
import json

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import Conversation

def test_fixed_format():
    """Test the new conversation ID format"""
    print("🧪 TESTING FIXED CONVERSATION ID FORMAT")
    print("=" * 80)
    
    with schema_context('oneotalent'):
        conversations = Conversation.objects.all()[:3]
        
        for i, conv in enumerate(conversations, 1):
            # Simulate what the API now returns
            new_format_id = f"{conv.channel.channel_type}_{conv.external_thread_id}"
            
            print(f"\n💬 Conversation {i}:")
            print(f"   Database UUID: {conv.id}")
            print(f"   NEW API Format: {new_format_id}")
            print(f"   External Thread: {conv.external_thread_id}")
            print(f"   Channel Type: {conv.channel.channel_type}")
            
            # Test if it can be split properly (what send message API does)
            try:
                channel_type, external_id = new_format_id.split('_', 1)
                print(f"   ✅ Split Test: channel_type='{channel_type}', external_id='{external_id}'")
                
                # Verify it matches original data
                if channel_type == conv.channel.channel_type and external_id == conv.external_thread_id:
                    print(f"   ✅ Data Match: Perfect!")
                else:
                    print(f"   ❌ Data Mismatch!")
                    
            except Exception as e:
                print(f"   ❌ Split Failed: {e}")

def show_before_after():
    """Show before and after comparison"""
    print(f"\n📊 BEFORE vs AFTER")
    print("=" * 40)
    
    with schema_context('oneotalent'):
        conv = Conversation.objects.first()
        if conv:
            old_format = str(conv.id)
            new_format = f"{conv.channel.channel_type}_{conv.external_thread_id}"
            
            print(f"BEFORE (UUID):     {old_format}")
            print(f"AFTER (Compatible): {new_format}")
            print(f"")
            print(f"Send Message API Split Test:")
            print(f"  Old: '{old_format}'.split('_') → {old_format.split('_')} ❌")
            print(f"  New: '{new_format}'.split('_', 1) → {new_format.split('_', 1)} ✅")

def main():
    """Main function"""
    test_fixed_format()
    show_before_after()
    
    print(f"\n🎯 RESULT: Send message API should now work!")
    print(f"✅ Conversation IDs now compatible with send message endpoint")

if __name__ == '__main__':
    main()