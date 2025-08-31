#!/usr/bin/env python
"""
Script to test HTML extraction from UniPile emails
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection, Message
from communications.unipile.clients.email import UnipileEmailClient
from communications.record_communications.unipile_integration.data_transformer import DataTransformer
import json

def test_html_extraction():
    """Test HTML extraction from UniPile emails"""
    
    print("🔍 Testing HTML extraction from UniPile...")
    
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
            
        print(f"✓ Found connection: {connection.unipile_account_id}")
        
        # Create UniPile client
        client = UnipileEmailClient(base_url='https://api18.unipile.com:14890')
        
        # Fetch a few emails
        response = client.list_emails(
            account_id=connection.unipile_account_id,
            limit=3
        )
        
        if response.get('items'):
            transformer = DataTransformer()
            
            for i, email in enumerate(response['items'], 1):
                print(f"\n📧 Email {i}:")
                print(f"  Subject: {email.get('subject', 'No subject')}")
                
                # Check body structure
                body = email.get('body', {})
                print(f"  Body type: {type(body)}")
                
                if isinstance(body, dict):
                    print(f"  Body keys: {list(body.keys())}")
                    if 'html' in body:
                        print(f"  ✓ HTML content found: {len(body['html'])} chars")
                    else:
                        print("  ❌ No HTML content in body dict")
                else:
                    print(f"  Body is string: {len(str(body))} chars")
                
                # Transform the email
                transformed = transformer.transform_email_message(
                    email,
                    conversation_id='test-conv',
                    channel_id=connection.channel_id
                )
                
                # Check if HTML was extracted
                metadata = transformed.get('metadata', {})
                if 'html_content' in metadata:
                    print(f"  ✅ HTML extracted to metadata: {len(metadata['html_content'])} chars")
                    
                    # Check for images in HTML
                    html = metadata['html_content']
                    if '<img' in html:
                        import re
                        img_count = len(re.findall(r'<img[^>]*>', html))
                        print(f"  📷 Found {img_count} images in HTML")
                        
                        # Check for hidden images
                        hidden_imgs = len(re.findall(r'display\s*:\s*none', html, re.IGNORECASE))
                        if hidden_imgs:
                            print(f"  ⚠️  Found {hidden_imgs} hidden image styles")
                else:
                    print("  ❌ No HTML content in transformed metadata")
        
        # Now check existing messages in database
        print("\n\n📊 Checking existing messages in database:")
        messages = Message.objects.filter(
            channel__channel_type='gmail'
        ).order_by('-created_at')[:5]
        
        for msg in messages:
            print(f"\nMessage {msg.id}:")
            print(f"  Created: {msg.created_at}")
            if msg.metadata and 'html_content' in msg.metadata:
                print(f"  ✅ Has HTML content: {len(msg.metadata['html_content'])} chars")
            else:
                print("  ❌ No HTML content in metadata")

if __name__ == "__main__":
    test_html_extraction()