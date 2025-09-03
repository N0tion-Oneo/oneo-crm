#!/usr/bin/env python
"""
Direct test of UniPile API to capture raw response
"""

import os
import sys
import django
import json
import requests
from datetime import datetime

# Setup Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'oneo_crm.settings'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from django.conf import settings
from communications.models import UserChannelConnection

def test_unipile_direct():
    """Make direct HTTP request to UniPile API"""
    
    with schema_context('oneotalent'):
        # Get connection details
        connection = UserChannelConnection.objects.filter(
            channel_type__in=['email', 'gmail'],
            is_active=True
        ).first()
        
        if not connection:
            print("No active email connection found")
            return
        
        print(f"Using connection: {connection.id}")
        print(f"UniPile Account ID: {connection.unipile_account_id}")
        
        # Get UniPile settings
        dsn = getattr(settings, 'UNIPILE_DSN', 'https://api.unipile.com:13424')
        access_token = getattr(settings, 'UNIPILE_API_KEY', '')
        
        print(f"DSN: {dsn}")
        
        # Make direct HTTP request
        url = f"{dsn}/api/v1/emails"
        headers = {
            'accept': 'application/json',
            'X-API-KEY': access_token
        }
        params = {
            'account_id': connection.unipile_account_id,
            'folder': 'INBOX',
            'limit': 30,
            'any_email': 'cowanr@credos.co.uk'
        }
        
        print(f"\n=== DIRECT HTTP REQUEST TO UNIPILE ===")
        print(f"URL: {url}")
        print(f"Params: {params}")
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Save raw response
            filename = f"/tmp/unipile_direct_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\nRaw response saved to: {filename}")
            
            # Check for quoted display names
            found_quotes = False
            for item in data.get('items', []):
                # Check to_attendees
                for to_att in item.get('to_attendees', []):
                    if 'cowanr' in to_att.get('identifier', '').lower():
                        display = to_att.get('display_name', '')
                        if display == "'cowanr@credos.co.uk'" or display == '"cowanr@credos.co.uk"':
                            print(f"\n=== FOUND QUOTED DISPLAY NAME ===")
                            print(f"Display name: {repr(display)}")
                            print(f"Full attendee: {to_att}")
                            found_quotes = True
                            break
                if found_quotes:
                    break
            
            if not found_quotes:
                print("\nNo quoted display names found")
                print(f"Total emails: {len(data.get('items', []))}")
                
                # Check first few emails
                for i, item in enumerate(data.get('items', [])[:3]):
                    print(f"\nEmail {i+1}:")
                    print(f"  Subject: {item.get('subject', 'No subject')}")
                    from_att = item.get('from_attendee', {})
                    if 'cowanr' in from_att.get('identifier', '').lower():
                        print(f"  From: {from_att.get('identifier')} -> {repr(from_att.get('display_name', ''))}")
                    for to_att in item.get('to_attendees', []):
                        if 'cowanr' in to_att.get('identifier', '').lower():
                            print(f"  To: {to_att.get('identifier')} -> {repr(to_att.get('display_name', ''))}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

if __name__ == '__main__':
    test_unipile_direct()