#!/usr/bin/env python
"""
Script to check email signature images
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

def check_signature_images():
    """Check email signature images"""
    
    print("🔍 Checking email signature images...")
    
    # Get the oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    # Use schema context for proper tenant isolation
    with schema_context(tenant.schema_name):
        # Get emails that likely have signatures
        messages = Message.objects.filter(
            channel__channel_type='gmail',
            metadata__html_content__isnull=False
        ).exclude(metadata__html_content='')[:5]
        
        for msg in messages:
            html = msg.metadata.get('html_content', '')
            subject = msg.conversation.subject
            
            print(f"\n📧 Email: {subject[:50]}...")
            
            # Find ALL img tags
            all_imgs = re.findall(r'<img[^>]*>', html, re.IGNORECASE)
            
            # Separate by type
            http_images = []
            cid_images = []
            
            for img in all_imgs:
                src_match = re.search(r'src=["\'](.*?)["\']', img, re.IGNORECASE)
                if src_match:
                    src = src_match.group(1)
                    if src.startswith('cid:'):
                        cid_images.append((src, img))
                    elif src.startswith('http'):
                        http_images.append((src, img))
            
            if http_images:
                print(f"  Found {len(http_images)} HTTP/HTTPS images:")
                for i, (src, img) in enumerate(http_images[:3], 1):
                    print(f"\n  {i}. URL: {src}")
                    
                    # Check if it's a tracking pixel
                    if 'track' in src.lower() or 'pixel' in src.lower():
                        print("     Type: Tracking pixel")
                    elif 'rocketseed' in src.lower():
                        print("     Type: RocketSeed signature image")
                    elif 'logo' in src.lower() or 'signature' in src.lower():
                        print("     Type: Likely signature/logo")
                    else:
                        print("     Type: Content image")
                    
                    # Check style
                    style_match = re.search(r'style=["\'](.*?)["\']', img, re.IGNORECASE)
                    if style_match:
                        style = style_match.group(1)
                        # Check for tiny dimensions (tracking pixels)
                        if re.search(r'width:\s*[01]px|height:\s*[01]px|width:\s*0\.|height:\s*0\.', style):
                            print("     ⚠️  Very small dimensions (likely tracking)")
                        else:
                            print(f"     Style: {style[:100]}")
                    
                    # Check width/height attributes
                    width_match = re.search(r'width=["\'](.*?)["\']', img, re.IGNORECASE)
                    height_match = re.search(r'height=["\'](.*?)["\']', img, re.IGNORECASE)
                    if width_match or height_match:
                        w = width_match.group(1) if width_match else 'auto'
                        h = height_match.group(1) if height_match else 'auto'
                        print(f"     Dimensions: {w} x {h}")
            
            if cid_images:
                print(f"\n  Found {len(cid_images)} CID images (embedded attachments)")
                # Check if these look like signature images
                for i, (src, img) in enumerate(cid_images[:2], 1):
                    cid_id = src.replace('cid:', '')
                    if 'rocketseed' in cid_id or 'signature' in cid_id.lower() or 'logo' in cid_id.lower():
                        print(f"    {i}. {cid_id} - Likely signature image")
                    else:
                        print(f"    {i}. {cid_id}")

if __name__ == "__main__":
    check_signature_images()