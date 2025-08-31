#!/usr/bin/env python
"""
Script to check ALL emails for actual HTTP images
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

def check_all_emails_images():
    """Check ALL emails for actual HTTP images"""
    
    print("🔍 Checking ALL emails for actual HTTP images (not tracking pixels)...")
    
    # Get the oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    # Use schema context for proper tenant isolation
    with schema_context(tenant.schema_name):
        # Get ALL email messages
        messages = Message.objects.filter(
            channel__channel_type='gmail',
            metadata__html_content__isnull=False
        ).exclude(metadata__html_content='')
        
        print(f"\n📧 Checking {messages.count()} emails...")
        print("=" * 80)
        
        emails_with_real_images = []
        
        for msg in messages:
            html = msg.metadata.get('html_content', '')
            subject = msg.conversation.subject
            
            # Find all HTTP/HTTPS image URLs in img tags
            img_tags = re.findall(r'<img[^>]*src=["\'](https?://[^"\']+)["\'][^>]*>', html, re.IGNORECASE)
            
            real_images = []
            tracking_pixels = []
            
            for img_tag in img_tags:
                # Extract the URL
                url_match = re.search(r'src=["\'](https?://[^"\']+)["\']', img_tag, re.IGNORECASE)
                if url_match:
                    url = url_match.group(1)
                    
                    # Check if it's a tracking pixel
                    is_tracking = False
                    
                    # Check URL for tracking keywords
                    if any(word in url.lower() for word in ['track', 'pixel', 'analytics', 'beacon', 'open']):
                        is_tracking = True
                    
                    # Check dimensions
                    if not is_tracking:
                        # Check style for tiny dimensions
                        style_match = re.search(r'style=["\'](.*?)["\']', img_tag, re.IGNORECASE)
                        if style_match:
                            style = style_match.group(1)
                            if any(pattern in style.lower() for pattern in [
                                'width:0', 'width:1px', 'width:.0', 
                                'height:0', 'height:1px', 'height:.0',
                                'display:none', 'display: none',
                                'visibility:hidden', 'visibility: hidden'
                            ]):
                                is_tracking = True
                        
                        # Check width/height attributes
                        width_match = re.search(r'width=["\']([\d]+)["\']', img_tag, re.IGNORECASE)
                        height_match = re.search(r'height=["\']([\d]+)["\']', img_tag, re.IGNORECASE)
                        if width_match and height_match:
                            w = int(width_match.group(1)) if width_match.group(1).isdigit() else 999
                            h = int(height_match.group(1)) if height_match.group(1).isdigit() else 999
                            if w <= 1 or h <= 1:
                                is_tracking = True
                    
                    if is_tracking:
                        tracking_pixels.append(url)
                    else:
                        real_images.append((url, img_tag))
            
            if real_images:
                emails_with_real_images.append({
                    'subject': subject,
                    'message_id': msg.id,
                    'images': real_images,
                    'tracking_count': len(tracking_pixels)
                })
        
        # Report findings
        print(f"\n📊 SUMMARY:")
        print(f"  Total emails checked: {messages.count()}")
        print(f"  Emails with real HTTP images: {len(emails_with_real_images)}")
        
        if emails_with_real_images:
            print(f"\n✅ EMAILS WITH REAL HTTP IMAGES:")
            for email_data in emails_with_real_images:
                print(f"\n  📧 {email_data['subject'][:60]}")
                print(f"     Message ID: {email_data['message_id']}")
                print(f"     Real images: {len(email_data['images'])}")
                print(f"     Tracking pixels: {email_data['tracking_count']}")
                
                for i, (url, img_tag) in enumerate(email_data['images'][:3], 1):
                    print(f"\n     Image {i}:")
                    print(f"       URL: {url[:100]}")
                    
                    # Check what type of image
                    if 'logo' in url.lower():
                        print(f"       Type: Logo image")
                    elif 'signature' in url.lower():
                        print(f"       Type: Signature image")
                    elif 'banner' in url.lower():
                        print(f"       Type: Banner image")
                    elif any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg']):
                        print(f"       Type: Content image")
                    else:
                        print(f"       Type: Unknown")
                    
                    # Check dimensions if available
                    style_match = re.search(r'style=["\'](.*?)["\']', img_tag, re.IGNORECASE)
                    if style_match:
                        style = style_match.group(1)
                        # Extract width/height from style
                        width_style = re.search(r'width:\s*([^;]+)', style, re.IGNORECASE)
                        height_style = re.search(r'height:\s*([^;]+)', style, re.IGNORECASE)
                        if width_style or height_style:
                            print(f"       Dimensions: {width_style.group(1) if width_style else 'auto'} x {height_style.group(1) if height_style else 'auto'}")
        else:
            print("\n❌ NO emails found with real HTTP images (only tracking pixels and CID attachments)")
            
            # Show what we do have
            print("\n📊 What we found instead:")
            cid_count = 0
            tracking_count = 0
            
            for msg in messages[:10]:  # Sample first 10
                html = msg.metadata.get('html_content', '')
                cid_imgs = len(re.findall(r'<img[^>]*src=["\'](cid:[^"\']+)["\']', html, re.IGNORECASE))
                track_imgs = len(re.findall(r'<img[^>]*src=["\'](https?://[^"\']*(?:track|pixel|analytics)[^"\']*)["\']', html, re.IGNORECASE))
                cid_count += cid_imgs
                tracking_count += track_imgs
            
            print(f"  - CID embedded images (need backend processing): {cid_count}")
            print(f"  - Tracking pixels: {tracking_count}")

if __name__ == "__main__":
    check_all_emails_images()