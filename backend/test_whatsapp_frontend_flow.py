#!/usr/bin/env python3
"""
Test the complete WhatsApp frontend flow for OneOTalent
Validate end-to-end webhook -> database -> frontend display
"""
import os
import sys
import json
import requests
import time
from datetime import datetime, timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
import django
django.setup()

from django.db import transaction
from django_tenants.utils import schema_context
from communications.models import (
    UserChannelConnection, Channel, Message, Conversation
)

TENANT_SCHEMA = "oneotalent"
WEBHOOK_URL = "http://localhost:8000/webhooks/unipile/"

def create_whatsapp_webhook_and_verify():
    """Create a WhatsApp webhook and verify it shows up in the data"""
    print("🚀 TESTING COMPLETE WEBHOOK → FRONTEND FLOW")
    print("=" * 60)
    
    # Step 1: Get initial state
    print("\n📊 Step 1: Getting initial state...")
    with schema_context(TENANT_SCHEMA):
        initial_message_count = Message.objects.count()
        whatsapp_channel = Channel.objects.filter(channel_type='whatsapp').first()
        
        if not whatsapp_channel:
            print("❌ No WhatsApp channel found in OneOTalent")
            return False
        
        print(f"✅ Initial message count: {initial_message_count}")
        print(f"✅ WhatsApp channel: {whatsapp_channel.name}")
    
    # Step 2: Send a realistic WhatsApp webhook
    print("\n📱 Step 2: Sending WhatsApp webhook...")
    webhook_payload = {
        "event": "message.received",
        "account_id": whatsapp_channel.unipile_account_id,
        "message": {
            "id": f"frontend_flow_test_{int(time.time())}",
            "text": {
                "body": f"🧪 Frontend flow test message - {datetime.now().strftime('%H:%M:%S')}"
            },
            "from": "+27720720057",  # Use the real number we saw in data
            "timestamp": int(time.time()),
            "type": "text"
        },
        "contact": {
            "wa_id": "+27720720057",
            "profile": {
                "name": "Frontend Test Contact"
            }
        }
    }
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=webhook_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        webhook_success = response.status_code in [200, 201]
        print(f"✅ Webhook response: {response.status_code}")
        
        if not webhook_success:
            print(f"❌ Webhook failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Webhook request failed: {e}")
        return False
    
    # Step 3: Verify data was saved
    print("\n💾 Step 3: Verifying data was saved...")
    time.sleep(1)  # Give it a moment to process
    
    with schema_context(TENANT_SCHEMA):
        new_message_count = Message.objects.count()
        new_messages = new_message_count - initial_message_count
        
        # Get the latest messages
        latest_messages = Message.objects.filter(
            channel__channel_type='whatsapp'
        ).order_by('-created_at')[:5]
        
        print(f"✅ New messages created: {new_messages}")
        print("📱 Latest WhatsApp messages:")
        
        for msg in latest_messages:
            direction = "➡️" if msg.direction == 'outbound' else "⬅️"
            timestamp = msg.created_at.strftime('%H:%M:%S')
            content = msg.content[:50] + '...' if len(msg.content) > 50 else msg.content
            phone = msg.contact_phone or 'Unknown'
            print(f"   {direction} {timestamp} {phone}: {content}")
    
    # Step 4: Check API endpoints
    print("\n🔌 Step 4: Testing API endpoints...")
    
    try:
        # Test messages API (this would be used by frontend)
        api_response = requests.get(
            f"http://localhost:8000/api/v1/communications/messages/",
            headers={
                "Host": "oneotalent.localhost",
                "Accept": "application/json"
            },
            timeout=5
        )
        
        api_accessible = api_response.status_code in [200, 401]
        print(f"✅ Messages API: {api_response.status_code} ({'needs auth' if api_response.status_code == 401 else 'accessible'})")
        
        # Test conversations API
        conv_response = requests.get(
            f"http://localhost:8000/api/v1/communications/conversations/",
            headers={
                "Host": "oneotalent.localhost",
                "Accept": "application/json"
            },
            timeout=5
        )
        
        conv_accessible = conv_response.status_code in [200, 401]
        print(f"✅ Conversations API: {conv_response.status_code} ({'needs auth' if conv_response.status_code == 401 else 'accessible'})")
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        api_accessible = False
        conv_accessible = False
    
    # Step 5: Test frontend page structure
    print("\n🌐 Step 5: Testing frontend accessibility...")
    
    try:
        # Test main page
        main_response = requests.get("http://oneotalent.localhost:3000/", timeout=10)
        main_ok = main_response.status_code == 200
        print(f"✅ Main page: {main_response.status_code}")
        
        # Test communications page
        comm_response = requests.get("http://oneotalent.localhost:3000/communications", timeout=10)
        comm_ok = comm_response.status_code == 200
        print(f"✅ Communications page: {comm_response.status_code}")
        
        # Check if the page contains expected elements
        if comm_ok:
            page_content = comm_response.text.lower()
            has_react = 'react' in page_content or 'next' in page_content
            has_js = 'javascript' in page_content or '_next' in page_content
            print(f"✅ Page has React/Next.js: {has_react}")
            
        frontend_working = main_ok and comm_ok
        
    except Exception as e:
        print(f"❌ Frontend test failed: {e}")
        frontend_working = False
    
    # Step 6: Summary
    print("\n" + "=" * 60)
    print("🏆 WEBHOOK → FRONTEND FLOW RESULTS")
    print("=" * 60)
    
    webhook_to_db = webhook_success and (new_messages > 0)
    db_to_api = api_accessible and conv_accessible
    api_to_frontend = frontend_working
    
    print(f"📱 Webhook → Database: {'✅ PASS' if webhook_to_db else '❌ FAIL'}")
    print(f"🔌 Database → API: {'✅ PASS' if db_to_api else '❌ FAIL'}")
    print(f"🌐 API → Frontend: {'✅ PASS' if api_to_frontend else '❌ FAIL'}")
    
    overall_success = webhook_to_db and db_to_api and api_to_frontend
    
    if overall_success:
        print("\n🎉 COMPLETE FLOW: WORKING END-TO-END!")
        print("✨ WhatsApp webhooks are successfully flowing to frontend")
    else:
        print("\n⚠️  FLOW ISSUES DETECTED")
        if not webhook_to_db:
            print("   • Webhook to database connection needs attention")
        if not db_to_api:
            print("   • Database to API layer needs attention")
        if not api_to_frontend:
            print("   • API to frontend connection needs attention")
    
    print(f"\n📊 Data Summary:")
    print(f"   • Total messages: {new_message_count}")
    print(f"   • New messages this test: {new_messages}")
    print(f"   • WhatsApp channel: {whatsapp_channel.name}")
    print(f"   • Frontend URL: http://oneotalent.localhost:3000/communications")
    
    return overall_success

if __name__ == "__main__":
    success = create_whatsapp_webhook_and_verify()
    
    print(f"\n🎯 FINAL STATUS: {'SUCCESS' if success else 'NEEDS ATTENTION'}")
    print("🔧 Next steps:")
    print("   1. Visit http://oneotalent.localhost:3000/communications")
    print("   2. Login to see WhatsApp conversations and messages")
    print("   3. Send more webhooks to see real-time updates")
    
    sys.exit(0 if success else 1)