#!/usr/bin/env python
"""
Test attachment validation to debug attachment-only message issue
"""
import os
import sys
import django
import json
import requests

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection, ChannelType

User = get_user_model()

def test_attachment_validation():
    """Test both attachment-with-text and attachment-only scenarios"""
    
    # Get tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        # Get test user and connection
        try:
            user = User.objects.get(username='josh@oneodigital.com')
        except User.DoesNotExist:
            print("❌ User 'josh@oneodigital.com' not found")
            return
        
        # Get WhatsApp connection
        try:
            connection = UserChannelConnection.objects.filter(
                user=user,
                channel_type=ChannelType.WHATSAPP,
                is_active=True
            ).first()
            
            if not connection:
                print("❌ No active WhatsApp connection found")
                return
                
        except Exception as e:
            print(f"❌ Error getting connection: {e}")
            return
    
    # Test data for attachment upload (simulate successful upload)
    test_attachment = {
        'id': 'test-attachment-123',
        'name': 'test_image.png',
        'size': 12345,
        'type': 'image/png',
        'url': 'http://localhost:8000/media/attachments/test.png',
        'storage_path': 'attachments/oneotalent/1/test.png'
    }
    
    # Base URL
    base_url = 'http://oneotalent.localhost:8000'
    
    # Get JWT token (simplified - in reality you'd login)
    print("=== TESTING ATTACHMENT VALIDATION ===")
    print(f"Using connection: {connection.id}")
    print(f"Account: {connection.account_name}")
    
    # Test 1: Message with text AND attachments (should work)
    print("\n--- Test 1: Message with text + attachments ---")
    data_with_text = {
        'content': 'Here is a test image',
        'account_id': str(connection.id),
        'recipient': '+1234567890@s.whatsapp.net',
        'attachments': [test_attachment]
    }
    
    print(f"📤 Sending: content='{data_with_text['content']}', attachments={len(data_with_text['attachments'])}")
    
    # Test 2: Message with ONLY attachments (should work but currently fails)
    print("\n--- Test 2: Attachment-only message ---")
    data_attachment_only = {
        'content': '',  # Empty content
        'account_id': str(connection.id),
        'recipient': '+1234567890@s.whatsapp.net',
        'attachments': [test_attachment]
    }
    
    print(f"📤 Sending: content='{data_attachment_only['content']}', attachments={len(data_attachment_only['attachments'])}")
    
    # Test 3: Message with WHITESPACE content (frontend might send this)
    print("\n--- Test 3: Message with whitespace + attachments ---")
    data_with_whitespace = {
        'content': '   ',  # Only whitespace
        'account_id': str(connection.id),
        'recipient': '+1234567890@s.whatsapp.net',
        'attachments': [test_attachment]
    }
    
    print(f"📤 Sending: content='{data_with_whitespace['content']}', attachments={len(data_with_whitespace['attachments'])}")
    
    print("\n=== VALIDATION LOGIC ANALYSIS ===")
    print("Current validation in MessageSendSerializer.validate():")
    print("1. content.strip() - strips whitespace")
    print("2. if not content and not attachments: raise error")
    print("3. Should allow: empty content + attachments")
    
    print("\n=== EXPECTED RESULTS ===")
    print("✅ Test 1 (text + attachments): PASS")
    print("✅ Test 2 (empty + attachments): PASS") 
    print("✅ Test 3 (whitespace + attachments): PASS")
    
    print(f"\n🔍 Check server logs for actual results when frontend sends these requests")
    print(f"🔍 Look for debug statements: '🚨 ENDPOINT REACHED' and '🚨 VALIDATING ATTACHMENTS'")

if __name__ == '__main__':
    test_attachment_validation()