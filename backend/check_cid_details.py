#!/usr/bin/env python
"""
Script to check CID image details from UniPile
"""
import os
import sys
import django
import re
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Message

def check_cid_details():
    """Check CID image details"""
    
    print("🔍 Checking CID image details from UniPile...")
    
    # Get the oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    # Use schema context for proper tenant isolation
    with schema_context(tenant.schema_name):
        # Get an email with CID images
        msg = Message.objects.filter(
            channel__channel_type='gmail',
            metadata__html_content__icontains='cid:'
        ).first()
        
        if not msg:
            print("❌ No emails with CID images found")
            return
            
        print(f"✓ Found message: {msg.id}")
        print(f"  Subject: {msg.conversation.subject}")
        
        # Check attachments in metadata
        attachments = msg.metadata.get('attachments', [])
        print(f"\n📎 Attachments in metadata: {len(attachments)}")
        
        if attachments:
            print("\nAttachment details:")
            for i, att in enumerate(attachments[:5], 1):
                print(f"\n  {i}. {att.get('filename', 'No filename')}")
                print(f"     Type: {att.get('content_type', 'Unknown')}")
                print(f"     Size: {att.get('size', 'Unknown')}")
                if 'content_id' in att:
                    print(f"     Content-ID: {att['content_id']}")
                if 'id' in att:
                    print(f"     Attachment ID: {att['id']}")
                if 'url' in att:
                    print(f"     URL: {att['url'][:100]}")
        
        # Extract CID references from HTML
        html = msg.metadata.get('html_content', '')
        cid_refs = re.findall(r'src=["\'](cid:[^"\']+)["\']', html, re.IGNORECASE)
        
        print(f"\n🖼️ CID references in HTML: {len(cid_refs)}")
        if cid_refs:
            print("\nSample CID references:")
            for i, cid in enumerate(set(cid_refs[:5]), 1):
                print(f"  {i}. {cid}")
                
                # Check if this CID has a matching attachment
                cid_id = cid.replace('cid:', '')
                matching_att = None
                for att in attachments:
                    if att.get('content_id') == cid_id or att.get('content_id') == f'<{cid_id}>':
                        matching_att = att
                        break
                
                if matching_att:
                    print(f"     ✓ Has matching attachment: {matching_att.get('filename')}")
                    if 'url' in matching_att:
                        print(f"     URL available: {matching_att['url'][:80]}")
                else:
                    print(f"     ❌ No matching attachment found")
        
        # Check the raw unipile_data if available
        unipile_data = msg.metadata.get('unipile_data', {})
        if unipile_data and 'attachments' in unipile_data:
            print(f"\n📦 Raw UniPile attachments: {len(unipile_data['attachments'])}")

if __name__ == "__main__":
    check_cid_details()