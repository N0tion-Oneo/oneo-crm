#!/usr/bin/env python
"""
Script to check ALL URLs in email HTML, not just img tags
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

def check_all_urls():
    """Check ALL URLs in email HTML"""
    
    print("🔍 Checking ALL URLs in email HTML (not just img tags)...")
    
    # Get the oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    # Use schema context for proper tenant isolation
    with schema_context(tenant.schema_name):
        # Get an email that likely has a signature
        msg = Message.objects.filter(
            channel__channel_type='gmail',
            metadata__html_content__icontains='rocketseed'
        ).first()
        
        if not msg:
            # Try any email
            msg = Message.objects.filter(
                channel__channel_type='gmail',
                metadata__html_content__isnull=False
            ).exclude(metadata__html_content='').first()
        
        if not msg:
            print("❌ No emails with HTML content found")
            return
            
        print(f"✓ Found message: {msg.conversation.subject[:50]}")
        html = msg.metadata.get('html_content', '')
        
        # Find ALL HTTP/HTTPS URLs in the HTML
        all_urls = re.findall(r'https?://[^\s<>"\']+', html, re.IGNORECASE)
        
        print(f"\n📊 Found {len(all_urls)} total HTTP/HTTPS URLs")
        
        # Categorize URLs
        image_urls = []
        rocketseed_urls = []
        tracking_urls = []
        other_urls = []
        
        for url in all_urls:
            url_lower = url.lower()
            if 'rocketseed' in url_lower:
                rocketseed_urls.append(url)
            elif any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', 'image']):
                if 'track' in url_lower or 'pixel' in url_lower:
                    tracking_urls.append(url)
                else:
                    image_urls.append(url)
            elif 'track' in url_lower or 'pixel' in url_lower or 'analytics' in url_lower:
                tracking_urls.append(url)
            else:
                other_urls.append(url)
        
        if rocketseed_urls:
            print(f"\n🚀 RocketSeed URLs: {len(rocketseed_urls)}")
            for i, url in enumerate(list(set(rocketseed_urls))[:5], 1):
                print(f"  {i}. {url}")
                # Check if it's in an img tag
                if f'src="{url}"' in html or f"src='{url}'" in html:
                    print("     ✓ Used in img src")
                elif f'href="{url}"' in html or f"href='{url}'" in html:
                    print("     Used in href (link)")
                else:
                    print("     Used elsewhere")
        
        if image_urls:
            print(f"\n🖼️ Image URLs (non-tracking): {len(image_urls)}")
            for i, url in enumerate(list(set(image_urls))[:5], 1):
                print(f"  {i}. {url}")
                # Check if it's in an img tag
                if f'src="{url}"' in html or f"src='{url}'" in html:
                    print("     ✓ Used in img src")
                    # Find the full img tag
                    img_match = re.search(f'<img[^>]*src=["\']?{re.escape(url)}[^>]*>', html, re.IGNORECASE)
                    if img_match:
                        img_tag = img_match.group(0)
                        # Check style
                        style_match = re.search(r'style=["\'](.*?)["\']', img_tag, re.IGNORECASE)
                        if style_match:
                            style = style_match.group(1)
                            if 'display:none' in style or 'display: none' in style:
                                print("     ⚠️  Has display:none")
                            elif 'width:0' in style or 'height:0' in style:
                                print("     ⚠️  Has zero dimensions")
                            else:
                                print(f"     Style: {style[:80]}")
        
        if tracking_urls:
            print(f"\n📊 Tracking URLs: {len(tracking_urls)}")
            for url in list(set(tracking_urls))[:2]:
                print(f"  - {url[:80]}")
        
        if other_urls:
            print(f"\n🔗 Other URLs: {len(other_urls)}")
            for url in list(set(other_urls))[:3]:
                print(f"  - {url[:80]}")
        
        # Look specifically for RocketSeed image patterns
        print("\n🔍 Looking for RocketSeed image patterns...")
        
        # Check for background images in styles
        bg_images = re.findall(r'background(?:-image)?:\s*url\(["\']?(https?://[^"\')]+)["\']?\)', html, re.IGNORECASE)
        if bg_images:
            print(f"Found {len(bg_images)} background images:")
            for i, url in enumerate(bg_images[:3], 1):
                print(f"  {i}. {url}")

if __name__ == "__main__":
    check_all_urls()