#!/usr/bin/env python
"""
Script to test fetching a single email from UniPile to see its structure
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection
from communications.unipile.clients.email import UnipileEmailClient
import json

def test_unipile_email():
    """Fetch a single email to inspect its structure"""
    
    print("🔍 Testing UniPile email structure...")
    
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
        
        # Create UniPile client
        client = UnipileEmailClient(base_url='https://api18.unipile.com:14890')
        
        # Fetch just one email
        response = client.list_emails(
            account_id=connection.unipile_account_id,
            limit=1
        )
        
        if response.get('items'):
            email = response['items'][0]
            print("\n📧 Email structure:")
            print(f"ID: {email.get('id')}")
            print(f"Subject: {email.get('subject', 'No subject')}")
            
            # Check body structure
            body = email.get('body', {})
            print(f"\nBody type: {type(body)}")
            
            if isinstance(body, dict):
                print(f"Body keys: {body.keys()}")
                if 'text' in body:
                    print(f"Text content length: {len(body['text'])}")
                if 'html' in body:
                    print(f"HTML content length: {len(body['html'])}")
                    # Show first 500 chars of HTML
                    html = body['html']
                    print(f"\nHTML preview:\n{html[:500]}")
                    
                    # Check for images
                    if '<img' in html:
                        import re
                        img_tags = re.findall(r'<img[^>]*>', html)
                        print(f"\nFound {len(img_tags)} images:")
                        for i, img in enumerate(img_tags[:3], 1):
                            print(f"  {i}. {img[:200]}")
            else:
                print(f"Body content (string): {str(body)[:500]}")
                
            # Save full structure to file for inspection
            with open('/tmp/unipile_email.json', 'w') as f:
                json.dump(email, f, indent=2)
            print("\n✓ Full email structure saved to /tmp/unipile_email.json")

if __name__ == "__main__":
    test_unipile_email()