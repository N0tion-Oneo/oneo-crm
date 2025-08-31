#!/usr/bin/env python
"""
Script to test what the frontend API actually returns
"""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Message
from communications.record_communications.serializers import RecordMessageSerializer

def test_frontend_api():
    """Test what the frontend API returns"""
    
    print("🔍 Testing what the frontend receives...")
    
    # Get the oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    # Use schema context for proper tenant isolation
    with schema_context(tenant.schema_name):
        # Get an email message
        msg = Message.objects.filter(
            channel__channel_type='gmail'
        ).first()
        
        if not msg:
            print("❌ No email messages found")
            return
            
        print(f"✓ Found message: {msg.id}")
        print(f"  Subject: {msg.conversation.subject}")
        
        # Serialize it
        serializer = RecordMessageSerializer(msg)
        data = serializer.data
        
        # Check what's being sent
        print(f"\n📋 Serialized data keys: {list(data.keys())}")
        
        # Check content
        content = data.get('content', '')
        html_content = data.get('html_content', '')
        
        print(f"\n📝 Content:")
        print(f"  Plain text length: {len(content)}")
        print(f"  HTML content length: {len(html_content)}")
        
        if html_content:
            # Check what's in the HTML
            import re
            
            # Count images
            all_imgs = re.findall(r'<img[^>]*>', html_content, re.IGNORECASE)
            cid_imgs = re.findall(r'<img[^>]*src=["\'](cid:[^"\']+)["\']', html_content, re.IGNORECASE)
            http_imgs = re.findall(r'<img[^>]*src=["\'](https?://[^"\']+)["\']', html_content, re.IGNORECASE)
            
            print(f"\n🖼️ Images in HTML content:")
            print(f"  Total img tags: {len(all_imgs)}")
            print(f"  CID images: {len(cid_imgs)}")
            print(f"  HTTP images: {len(http_imgs)}")
            
            if http_imgs:
                print(f"\n  HTTP images found:")
                for i, img in enumerate(http_imgs[:3], 1):
                    print(f"    {i}. {img[:80]}")
            
            # Save a sample to file for inspection
            with open('/tmp/frontend_html_sample.html', 'w') as f:
                f.write(html_content)
            print(f"\n✓ HTML content saved to /tmp/frontend_html_sample.html")
            
            # Also save the full serialized data
            with open('/tmp/frontend_api_response.json', 'w') as f:
                json.dump(data, f, indent=2, default=str)
            print(f"✓ Full API response saved to /tmp/frontend_api_response.json")

if __name__ == "__main__":
    test_frontend_api()