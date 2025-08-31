#!/usr/bin/env python
"""
Script to test fetching an attachment from UniPile
"""
import os
import sys
import django
import requests

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Message, UserChannelConnection
from django.conf import settings
import base64

def test_attachment_api():
    """Test fetching an attachment from UniPile"""
    
    print("🔍 Testing UniPile attachment API...")
    
    # Get the oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    # Use schema context for proper tenant isolation
    with schema_context(tenant.schema_name):
        # Get Gmail connection
        connection = UserChannelConnection.objects.filter(
            channel_type='gmail',
            is_active=True
        ).first()
        
        if not connection:
            print("❌ No active Gmail connection found")
            return
            
        # Get an email with attachments
        msg = Message.objects.filter(
            channel__channel_type='gmail',
            metadata__attachments__isnull=False
        ).exclude(metadata__attachments=[]).first()
        
        if not msg:
            print("❌ No emails with attachments found")
            return
            
        print(f"✓ Found message with attachments")
        print(f"  Subject: {msg.conversation.subject}")
        print(f"  External message ID: {msg.external_message_id}")
        
        attachments = msg.metadata.get('attachments', [])
        if attachments and len(attachments) > 0:
            # Try the first attachment
            att = attachments[0]
            att_id = att.get('id')
            
            print(f"\n📎 Testing attachment:")
            print(f"  Attachment ID: {att_id}")
            
            # Check if it's base64 encoded ID
            if att_id and len(att_id) > 100:  # Looks like base64
                print(f"  ID appears to be base64 encoded (length: {len(att_id)})")
                
                # Try to decode it
                try:
                    decoded = base64.b64decode(att_id).decode('utf-8', errors='ignore')
                    print(f"  Decoded ID preview: {decoded[:100]}...")
                except:
                    print("  Could not decode as base64")
            
            # Try to fetch the attachment
            url = f"https://api18.unipile.com:14890/api/v1/emails/{msg.external_message_id}/attachments/{att_id}"
            headers = {
                "X-API-KEY": settings.UNIPILE_API_KEY,
                "Accept": "application/json"
            }
            
            print(f"\n📡 Making API call to fetch attachment...")
            print(f"  URL: {url[:100]}...")
            
            response = requests.get(url, headers=headers)
            
            print(f"  Response status: {response.status_code}")
            
            if response.status_code == 200:
                # Check content type
                content_type = response.headers.get('Content-Type', '')
                content_length = len(response.content)
                
                print(f"  ✅ Success!")
                print(f"  Content-Type: {content_type}")
                print(f"  Content size: {content_length} bytes")
                
                # If it's an image, save it to check
                if 'image' in content_type:
                    filename = f"/tmp/test_attachment.{content_type.split('/')[-1]}"
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    print(f"  Saved to: {filename}")
                    
                    # Also check if this looks like a signature image
                    if content_length < 50000:  # Less than 50KB
                        print("  Size suggests this could be a signature logo")
            else:
                print(f"  ❌ Failed: {response.status_code}")
                print(f"  Response: {response.text[:500]}")
        
        # Also check the raw UniPile data structure
        print("\n📦 Checking raw UniPile data structure:")
        unipile_data = msg.metadata.get('unipile_data', {})
        if unipile_data and 'attachments' in unipile_data:
            unipile_atts = unipile_data['attachments']
            if unipile_atts and len(unipile_atts) > 0:
                print(f"  UniPile attachments: {len(unipile_atts)}")
                for i, att in enumerate(unipile_atts[:2], 1):
                    print(f"\n  Attachment {i}:")
                    for key in ['id', 'filename', 'content_type', 'size', 'content_id', 'url']:
                        if key in att:
                            val = att[key]
                            if key == 'id' and len(str(val)) > 50:
                                print(f"    {key}: {str(val)[:50]}...")
                            else:
                                print(f"    {key}: {val}")

if __name__ == "__main__":
    test_attachment_api()