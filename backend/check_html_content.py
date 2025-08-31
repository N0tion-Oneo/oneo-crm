#!/usr/bin/env python
"""
Script to check HTML content in messages
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Message

def check_html_content():
    """Check HTML content in messages"""
    
    print("🔍 Checking HTML content in messages...")
    
    # Get the oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    # Use schema context for proper tenant isolation
    with schema_context(tenant.schema_name):
        # Get email messages
        email_messages = Message.objects.filter(
            channel__channel_type='gmail'
        ).order_by('-created_at')[:5]
        
        print(f"\n📧 Found {email_messages.count()} recent email messages")
        
        for msg in email_messages:
            print(f"\n--- Message {msg.id} ---")
            print(f"Subject: {msg.subject[:50] if msg.subject else 'No subject'}")
            print(f"Content length: {len(msg.content) if msg.content else 0}")
            
            # Check metadata for html_content
            if msg.metadata:
                has_html = 'html_content' in msg.metadata
                print(f"Has html_content in metadata: {has_html}")
                
                if has_html:
                    html = msg.metadata.get('html_content', '')
                    print(f"HTML content length: {len(html)}")
                    
                    # Check for images
                    if '<img' in html:
                        import re
                        img_tags = re.findall(r'<img[^>]*>', html)
                        print(f"Found {len(img_tags)} image tags")
                        for i, img in enumerate(img_tags[:3], 1):
                            print(f"  Image {i}: {img[:200]}...")
                    else:
                        print("No image tags found in HTML")
                        
                    # Check first 500 chars of HTML
                    print(f"HTML preview: {html[:500]}...")
            else:
                print("No metadata found")

if __name__ == "__main__":
    check_html_content()