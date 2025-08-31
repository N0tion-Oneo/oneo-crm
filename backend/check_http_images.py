#!/usr/bin/env python
"""
Script to check for HTTP images in email HTML
"""
import os
import sys
import django
import re

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Message

def check_http_images():
    """Check for HTTP images in email HTML"""
    
    print("🔍 Checking for HTTP images in email HTML...")
    
    # Get the oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    # Use schema context for proper tenant isolation
    with schema_context(tenant.schema_name):
        # Get email messages with HTML content
        messages = Message.objects.filter(
            channel__channel_type='gmail'
        ).exclude(metadata__html_content__isnull=True)[:10]
        
        print(f"\n📧 Checking {messages.count()} messages with HTML content")
        
        total_http_images = 0
        total_cid_images = 0
        
        for msg in messages:
            html = msg.metadata.get('html_content', '')
            
            # Find HTTP/HTTPS images
            http_imgs = re.findall(r'<img[^>]*src=["\'](https?://[^"\']+)["\'][^>]*>', html, re.IGNORECASE)
            
            # Find CID images
            cid_imgs = re.findall(r'<img[^>]*src=["\']cid:([^"\']+)["\'][^>]*>', html, re.IGNORECASE)
            
            if http_imgs or cid_imgs:
                print(f"\nMessage {msg.id}:")
                print(f"  HTTP images: {len(http_imgs)}")
                print(f"  CID images: {len(cid_imgs)}")
                
                if http_imgs:
                    print("  Sample HTTP images:")
                    for img_url in http_imgs[:3]:
                        print(f"    - {img_url[:100]}...")
                
                total_http_images += len(http_imgs)
                total_cid_images += len(cid_imgs)
        
        print(f"\n📊 Summary:")
        print(f"  Total HTTP/HTTPS images: {total_http_images}")
        print(f"  Total CID images: {total_cid_images}")
        
        if total_http_images == 0:
            print("\n⚠️  No HTTP images found. All images are CID attachments.")
            print("   CID images require backend processing to display.")
        else:
            print("\n✅ HTTP images found! These should now be displaying in the frontend.")

if __name__ == "__main__":
    check_http_images()