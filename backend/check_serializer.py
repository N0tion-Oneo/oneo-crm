#!/usr/bin/env python
"""
Script to check if serializer is sending html_content
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
from communications.record_communications.serializers import RecordMessageSerializer

def check_serializer():
    """Check if serializer includes html_content"""
    
    print("🔍 Checking serializer output...")
    
    # Get the oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    # Use schema context for proper tenant isolation
    with schema_context(tenant.schema_name):
        # Get an email message
        msg = Message.objects.filter(channel__channel_type='gmail').first()
        
        if not msg:
            print("❌ No email messages found")
            return
            
        print(f"✓ Found message: {msg.id}")
        
        # Check raw metadata
        if msg.metadata and 'html_content' in msg.metadata:
            print(f"✓ Message has html_content in metadata (length: {len(msg.metadata['html_content'])})")
        else:
            print("❌ Message does NOT have html_content in metadata")
            
        # Serialize the message
        serializer = RecordMessageSerializer(msg)
        data = serializer.data
        
        print(f"\n📋 Serialized fields:")
        for key in sorted(data.keys()):
            if key == 'html_content':
                print(f"  ✓ {key}: {len(data[key]) if data[key] else 0} chars")
            else:
                print(f"  - {key}")
        
        if 'html_content' not in data:
            print("\n❌ ERROR: html_content field is missing from serializer output!")
            print("   The serializer is not including the html_content field.")
        elif not data['html_content']:
            print("\n⚠️  WARNING: html_content is empty in serializer output!")
        else:
            print(f"\n✅ SUCCESS: html_content is present with {len(data['html_content'])} characters")

if __name__ == "__main__":
    check_serializer()