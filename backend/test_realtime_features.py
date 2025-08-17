#!/usr/bin/env python3
"""
Test real-time WhatsApp features
"""
import os
import sys
import time
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.webhooks.handlers import webhook_handler

def test_realtime_features():
    """Test real-time WhatsApp features with a simulated webhook"""
    
    print("🚀 TESTING REAL-TIME WHATSAPP FEATURES")
    print("=" * 50)
    
    # Test incoming message from customer with attendee_id for profile picture
    test_webhook_data = {
        'event': 'message_received',
        'account_id': 'mp9Gis3IRtuh9V5oSxZdSA',
        'message_id': 'test_realtime_final_' + str(int(time.time())),
        'chat_id': '1T1s9uwKX3yXDdHr9p9uWQ',
        'message': 'Testing real-time features!',
        'attachments': [
            {
                'id': 'test_attachment_123',
                'type': 'image',
                'name': 'test_image.jpg'
            }
        ],
        'sender': {
            'attendee_id': 'LI-rNlCvUIu80uk2O0q_Iw',  # This should trigger profile picture fetch
            'attendee_provider_id': '27849977040@s.whatsapp.net',
            'attendee_name': 'Vanessa'
        }
    }
    
    print("📤 Sending test webhook with attendee_id and attachment...")
    
    # Process the webhook - this should trigger:
    # 1. Profile picture fetch
    # 2. Attachment processing  
    # 3. Real-time broadcasting
    result = webhook_handler.process_webhook('message_received', test_webhook_data)
    
    print(f"📥 Webhook result: {result}")
    
    if result.get('success'):
        print("✅ Webhook processed successfully")
        print("🔍 Check the logs above for:")
        print("  • 'Triggered async profile picture fetch for attendee LI-rNlCvUIu80uk2O0q_Iw'")
        print("  • 'Triggered async attachment processing for message test_channel_fix_789'")
        print("  • 'Broadcasted real-time WhatsApp message to rooms'")
        return True
    else:
        print(f"❌ Webhook failed: {result.get('error')}")
        return False

if __name__ == '__main__':
    success = test_realtime_features()
    sys.exit(0 if success else 1)