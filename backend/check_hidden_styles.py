#!/usr/bin/env python
"""
Script to check for hidden styles in email HTML
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

def check_hidden_styles():
    """Check for hidden styles in email HTML"""
    
    print("🔍 Checking for hidden styles in email HTML...")
    
    # Get the oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    # Use schema context for proper tenant isolation
    with schema_context(tenant.schema_name):
        # Get an email message with HTML content
        msg = Message.objects.filter(
            channel__channel_type='gmail',
            metadata__html_content__isnull=False
        ).exclude(metadata__html_content='').first()
        
        if not msg:
            print("❌ No email messages with HTML content found")
            return
            
        print(f"✓ Found message: {msg.id}")
        html = msg.metadata.get('html_content', '')
        
        # Check for problematic styles
        print("\n📋 Checking for problematic styles:")
        
        # Check for display:none on images
        img_display_none = re.findall(
            r'<img[^>]*style\s*=\s*["\'][^"\']*display\s*:\s*none[^"\']*["\'][^>]*>',
            html, re.IGNORECASE
        )
        if img_display_none:
            print(f"  ⚠️  Found {len(img_display_none)} images with display:none")
            for i, img in enumerate(img_display_none[:2], 1):
                print(f"    {i}. {img[:150]}...")
        else:
            print("  ✓ No images with display:none")
        
        # Check for max-width:0 on images
        img_max_width_0 = re.findall(
            r'<img[^>]*style\s*=\s*["\'][^"\']*max-width\s*:\s*0[^"\']*["\'][^>]*>',
            html, re.IGNORECASE
        )
        if img_max_width_0:
            print(f"  ⚠️  Found {len(img_max_width_0)} images with max-width:0")
            for i, img in enumerate(img_max_width_0[:2], 1):
                print(f"    {i}. {img[:150]}...")
        else:
            print("  ✓ No images with max-width:0")
        
        # Check for visibility:hidden on images
        img_visibility_hidden = re.findall(
            r'<img[^>]*style\s*=\s*["\'][^"\']*visibility\s*:\s*hidden[^"\']*["\'][^>]*>',
            html, re.IGNORECASE
        )
        if img_visibility_hidden:
            print(f"  ⚠️  Found {len(img_visibility_hidden)} images with visibility:hidden")
        else:
            print("  ✓ No images with visibility:hidden")
        
        # Check for width:0 or height:0 on images
        img_zero_size = re.findall(
            r'<img[^>]*style\s*=\s*["\'][^"\']*(?:width|height)\s*:\s*0[^"\']*["\'][^>]*>',
            html, re.IGNORECASE
        )
        if img_zero_size:
            print(f"  ⚠️  Found {len(img_zero_size)} images with width:0 or height:0")
        else:
            print("  ✓ No images with zero dimensions")
        
        # Sample some regular HTTP images
        http_imgs = re.findall(
            r'<img[^>]*src\s*=\s*["\']https?://[^"\']+["\'][^>]*>',
            html, re.IGNORECASE
        )
        
        if http_imgs:
            print(f"\n📷 Sample HTTP images ({len(http_imgs)} total):")
            for i, img in enumerate(http_imgs[:3], 1):
                # Extract style attribute if present
                style_match = re.search(r'style\s*=\s*["\']([^"\']*)["\']', img, re.IGNORECASE)
                if style_match:
                    style = style_match.group(1)
                    print(f"  {i}. Style: {style[:100]}...")
                else:
                    print(f"  {i}. No style attribute")

if __name__ == "__main__":
    check_hidden_styles()