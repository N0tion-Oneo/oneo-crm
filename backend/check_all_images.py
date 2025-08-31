#!/usr/bin/env python
"""
Script to check all images in emails
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

def check_all_images():
    """Check all images in emails"""
    
    print("🔍 Checking all images in emails...")
    
    # Get the oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    # Use schema context for proper tenant isolation
    with schema_context(tenant.schema_name):
        # Get all email messages with HTML content
        messages = Message.objects.filter(
            channel__channel_type='gmail',
            metadata__html_content__isnull=False
        ).exclude(metadata__html_content='')[:5]
        
        for msg in messages:
            html = msg.metadata.get('html_content', '')
            subject = msg.metadata.get('subject') or msg.conversation.subject
            
            print(f"\n📧 Email: {subject[:50]}...")
            
            # Find ALL images
            all_imgs = re.findall(r'<img[^>]*>', html, re.IGNORECASE)
            
            if all_imgs:
                print(f"  Total images: {len(all_imgs)}")
                
                # Categorize images
                tracking_pixels = []
                content_images = []
                cid_images = []
                
                for img in all_imgs:
                    src_match = re.search(r'src=["\']([^"\']+)["\']', img, re.IGNORECASE)
                    if src_match:
                        src = src_match.group(1)
                        
                        if src.startswith('cid:'):
                            cid_images.append(img)
                        else:
                            # Check if it's a tracking pixel (very small dimensions)
                            style_match = re.search(r'style=["\']([^"\']+)["\']', img, re.IGNORECASE)
                            width_match = re.search(r'width=["\']([^"\']+)["\']', img, re.IGNORECASE)
                            height_match = re.search(r'height=["\']([^"\']+)["\']', img, re.IGNORECASE)
                            
                            is_tracking = False
                            if style_match:
                                style = style_match.group(1)
                                # Check for tiny dimensions
                                if re.search(r'(?:width|height)\s*:\s*(?:0|1px|\.00|\.01)', style, re.IGNORECASE):
                                    is_tracking = True
                            
                            if width_match and height_match:
                                width = width_match.group(1)
                                height = height_match.group(1)
                                if width in ['1', '0'] or height in ['1', '0']:
                                    is_tracking = True
                            
                            if 'pixel' in src.lower() or 'track' in src.lower():
                                is_tracking = True
                            
                            if is_tracking:
                                tracking_pixels.append(img)
                            else:
                                content_images.append(img)
                
                print(f"  - Content images: {len(content_images)}")
                print(f"  - Tracking pixels: {len(tracking_pixels)}")
                print(f"  - CID images: {len(cid_images)}")
                
                if content_images:
                    print("  Sample content images:")
                    for i, img in enumerate(content_images[:2], 1):
                        src_match = re.search(r'src=["\']([^"\']+)["\']', img, re.IGNORECASE)
                        if src_match:
                            src = src_match.group(1)
                            # Get dimensions if available
                            style_match = re.search(r'style=["\']([^"\']+)["\']', img, re.IGNORECASE)
                            if style_match:
                                print(f"    {i}. {src[:80]}")
                                print(f"       Style: {style_match.group(1)[:100]}")
                            else:
                                print(f"    {i}. {src[:80]}")

if __name__ == "__main__":
    check_all_images()