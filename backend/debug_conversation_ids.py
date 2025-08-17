#!/usr/bin/env python3
"""
Debug conversation ID formats to fix send message issue
"""

import os
import django
import json

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import Message, Conversation, Channel

def debug_conversation_ids():
    """Check conversation ID formats"""
    print("🔍 DEBUGGING CONVERSATION ID FORMATS")
    print("=" * 80)
    
    with schema_context('oneotalent'):
        conversations = Conversation.objects.all()[:5]
        
        print(f"📊 Found {conversations.count()} conversations")
        
        for i, conv in enumerate(conversations, 1):
            print(f"\n💬 Conversation {i}:")
            print(f"   Database ID (UUID): {conv.id}")
            print(f"   External Thread ID: {conv.external_thread_id}")
            print(f"   Channel Type: {conv.channel.channel_type}")
            print(f"   Channel ID: {conv.channel.id}")
            
            # What the frontend receives from local API
            frontend_id = str(conv.id)
            print(f"   Frontend Receives: {frontend_id}")
            
            # What the send message API expects
            expected_format = f"{conv.channel.channel_type}_{conv.external_thread_id}"
            print(f"   Send API Expects: {expected_format}")
            
            # Check if UUID has underscore
            has_underscore = '_' in frontend_id
            print(f"   Has Underscore: {has_underscore}")
            
            if not has_underscore:
                print(f"   ❌ PROBLEM: Send API will fail - UUID has no underscore to split!")
            else:
                print(f"   ✅ OK: Contains underscore")

def show_api_mismatch():
    """Show the API format mismatch"""
    print(f"\n🚨 API FORMAT MISMATCH IDENTIFIED")
    print("=" * 60)
    
    print("📤 LOCAL INBOX API RETURNS:")
    print("   conversation_id: 'c2f16684-b072-4f1e-ae40-fbb3859ec6e6' (UUID)")
    
    print("\n📨 SEND MESSAGE API EXPECTS:")
    print("   conversation_id: 'whatsapp_pTPcq3IFXyi0p9Awd93STw' (type_external_id)")
    
    print("\n🔧 SOLUTION NEEDED:")
    print("   1. Modify local inbox API to return correct format")
    print("   2. OR: Modify send message API to handle UUIDs")
    print("   3. OR: Convert UUID to correct format in frontend")

def main():
    """Main function"""
    debug_conversation_ids()
    show_api_mismatch()

if __name__ == '__main__':
    main()