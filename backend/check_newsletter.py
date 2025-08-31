#!/usr/bin/env python
"""
Script to check newsletter images
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

def check_newsletter():
    """Check newsletter images"""
    
    print("🔍 Checking newsletter images...")
    
    # Get the oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    # Use schema context for proper tenant isolation
    with schema_context(tenant.schema_name):
        # Find the newsletter email
        msg = Message.objects.filter(
            conversation__subject__icontains='Regulatory'
        ).first()
        
        if not msg:
            print("❌ Newsletter not found")
            return
            
        print(f"✓ Found newsletter: {msg.conversation.subject[:50]}")
        html = msg.metadata.get('html_content', '')
        
        # Find all images with beehiiv URLs
        all_imgs = re.findall(r'<img[^>]*>', html, re.IGNORECASE)
        beehiiv_imgs = []
        other_imgs = []
        
        for img in all_imgs:
            if 'beehiiv' in img:
                beehiiv_imgs.append(img)
            elif 'src=' in img and 'cid:' not in img:
                other_imgs.append(img)
        
        print(f"\n📷 Found {len(beehiiv_imgs)} beehiiv images")
        
        if beehiiv_imgs:
            print("\nSample beehiiv images:")
            for i, img in enumerate(beehiiv_imgs[:3], 1):
                # Extract src
                src_match = re.search(r'src=["\'](.*?)["\']', img, re.IGNORECASE)
                if src_match:
                    src = src_match.group(1)
                    print(f"\n  {i}. Source: {src[:100]}")
                    
                    # Extract style
                    style_match = re.search(r'style=["\'](.*?)["\']', img, re.IGNORECASE)
                    if style_match:
                        style = style_match.group(1)
                        # Check for problematic styles
                        if 'display:none' in style or 'display: none' in style:
                            print(f"     ⚠️  Has display:none")
                        elif 'max-width:0' in style or 'max-width: 0' in style:
                            print(f"     ⚠️  Has max-width:0")
                        else:
                            print(f"     Style: {style[:100]}")
                    
                    # Extract dimensions
                    width_match = re.search(r'width=["\'](.*?)["\']', img, re.IGNORECASE)
                    height_match = re.search(r'height=["\'](.*?)["\']', img, re.IGNORECASE)
                    if width_match or height_match:
                        print(f"     Dimensions: width={width_match.group(1) if width_match else 'auto'}, height={height_match.group(1) if height_match else 'auto'}")
        
        print(f"\n📷 Found {len(other_imgs)} other HTTP images")
        if other_imgs:
            for i, img in enumerate(other_imgs[:2], 1):
                src_match = re.search(r'src=["\'](.*?)["\']', img, re.IGNORECASE)
                if src_match:
                    print(f"  {i}. {src_match.group(1)[:100]}")

if __name__ == "__main__":
    check_newsletter()