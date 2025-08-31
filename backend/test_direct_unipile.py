#!/usr/bin/env python
"""
Script to directly test UniPile API and see raw response
"""
import os
import sys
import django
import requests
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection
from django.conf import settings

def test_direct_unipile():
    """Test direct UniPile API call"""
    
    print("🔍 Testing direct UniPile API...")
    
    # Get the oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    # Use schema context for proper tenant isolation
    with schema_context(tenant.schema_name):
        # Get Gmail connection
        connection = UserChannelConnection.objects.filter(
            channel_type='gmail',
            is_active=True
        ).first()
        
        if not connection:
            print("❌ No active Gmail connection found")
            return
            
        print(f"✓ Found connection: {connection.unipile_account_id}")
        
        # Direct API call to UniPile
        url = f"https://api18.unipile.com:14890/api/v1/emails"
        headers = {
            "X-API-KEY": settings.UNIPILE_API_KEY,
            "Accept": "application/json"
        }
        params = {
            "account_id": connection.unipile_account_id,
            "limit": 2
        }
        
        print(f"\n📡 Making API call to: {url}")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Save full response
            with open('/tmp/unipile_raw_response.json', 'w') as f:
                json.dump(data, f, indent=2)
            print("✓ Full response saved to /tmp/unipile_raw_response.json")
            
            if data.get('items'):
                for i, email in enumerate(data['items'][:2], 1):
                    print(f"\n📧 Email {i}:")
                    print(f"  ID: {email.get('id')}")
                    print(f"  Subject: {email.get('subject', 'No subject')}")
                    
                    # Check body structure
                    body = email.get('body')
                    if body:
                        print(f"  Body type: {type(body)}")
                        if isinstance(body, dict):
                            print(f"  Body keys: {list(body.keys())}")
                            if 'html' in body:
                                html_content = body['html']
                                print(f"  ✓ HTML found: {len(html_content)} chars")
                                
                                # Check for images
                                if '<img' in html_content:
                                    import re
                                    imgs = re.findall(r'<img[^>]*src=["\'](.*?)["\']', html_content)
                                    print(f"  📷 Found {len(imgs)} images:")
                                    for img_src in imgs[:3]:
                                        if img_src.startswith('cid:'):
                                            print(f"    - CID: {img_src[:50]}")
                                        elif img_src.startswith('http'):
                                            print(f"    - HTTP: {img_src[:80]}")
                                        else:
                                            print(f"    - Other: {img_src[:50]}")
                                
                                # Check for hidden styles
                                if 'display:none' in html_content or 'display: none' in html_content:
                                    print("  ⚠️  Found display:none styles")
                                if 'max-width:0' in html_content or 'max-width: 0' in html_content:
                                    print("  ⚠️  Found max-width:0 styles")
                        else:
                            print(f"  Body is string: {len(str(body))} chars")
                    else:
                        print("  ❌ No body field")
                        
                    # Check other possible HTML fields
                    for field in ['html_content', 'html', 'content']:
                        if field in email and email[field]:
                            print(f"  Found {field}: {len(str(email[field]))} chars")
        else:
            print(f"❌ API call failed: {response.status_code}")
            print(f"Response: {response.text}")

if __name__ == "__main__":
    test_direct_unipile()