#!/usr/bin/env python
"""
Test script to capture raw UniPile API response
"""

import os
import sys
import django
import json
from datetime import datetime, timedelta

# Setup Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'oneo_crm.settings'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from django.conf import settings
from communications.models import UserChannelConnection
from communications.record_communications.unipile_integration.email_fetcher_v2 import EmailFetcherV2
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_unipile_response():
    """Test UniPile API and capture raw response"""
    
    with schema_context('oneotalent'):
        # Get the email connection
        try:
            connection = UserChannelConnection.objects.filter(
                channel_type__in=['email', 'gmail'],
                is_active=True
            ).first()
            
            if not connection:
                print("No active email connection found")
                return
            
            print(f"Using connection: {connection.id}")
            print(f"UniPile Account ID: {connection.unipile_account_id}")
            
            # Get UniPile settings from Django settings
            dsn = getattr(settings, 'UNIPILE_DSN', 'https://api.unipile.com:13424')
            access_token = getattr(settings, 'UNIPILE_API_KEY', '')
            
            print(f"DSN: {dsn}")
            print(f"Access Token: {access_token[:10]}..." if access_token else "No token")
            
            # Prepare to fetch emails
            headers = {
                'accept': 'application/json',
                'X-API-KEY': access_token
            }
            
            # Search for emails - try without path filter
            url = f"{dsn}/api/v1/emails"
            params = {
                'account_id': connection.unipile_account_id,
                'limit': 30,  # Get more emails
                # Don't filter by path to search all folders
            }
            
            print(f"\n=== CALLING UNIPILE API ===")
            print(f"URL: {url}")
            print(f"Params: {params}")
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                emails = response.json().get('items', [])
                
                # Check for any emails with quoted display names
                found_quotes = False
                for email in emails:
                    from_attendee = email.get('from_attendee', {})
                    to_attendees = email.get('to_attendees', [])
                    
                    # Check from_attendee for quotes
                    from_display = from_attendee.get('display_name', '')
                    if from_display and (from_display.startswith("'") or from_display.startswith('"')):
                        print(f"\n=== FOUND EMAIL WITH QUOTED FROM DISPLAY NAME ===")
                        print(f"Subject: {email.get('subject', 'No subject')}")
                        print(f"From identifier: {from_attendee.get('identifier', '')}")
                        print(f"From display_name: '{from_display}'")
                        print(f"From display_name repr: {repr(from_display)}")
                        found_quotes = True
                        
                    # Check to_attendees for quotes
                    for to_att in to_attendees:
                        to_display = to_att.get('display_name', '')
                        if to_display and (to_display.startswith("'") or to_display.startswith('"')):
                            print(f"\n=== FOUND EMAIL WITH QUOTED TO DISPLAY NAME ===")
                            print(f"Subject: {email.get('subject', 'No subject')}")
                            print(f"To identifier: {to_att.get('identifier', '')}")
                            print(f"To display_name: '{to_display}'")
                            print(f"To display_name repr: {repr(to_display)}")
                            found_quotes = True
                            
                            # Save this email
                            filename = f"unipile_email_with_quotes_{email.get('id', 'unknown')}.json"
                            with open(filename, 'w') as f:
                                json.dump(email, f, indent=2)
                            print(f"\nFull email saved to: {filename}")
                            break
                    
                    if found_quotes:
                        break
                
                if not found_quotes:
                    print("\nNo emails with quoted display names found.")
                    print("Checking all emails for cowanr or empty display names...")
                    for email in emails:
                        from_att = email.get('from_attendee', {})
                        if 'cowanr' in from_att.get('identifier', '').lower() or not from_att.get('display_name', ''):
                            print(f"\n  From: {from_att.get('identifier', 'Unknown')}")
                            print(f"  Display: '{from_att.get('display_name', '')}'")
                            print(f"  Subject: {email.get('subject', 'No subject')[:50]}")
            else:
                print(f"Error: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_unipile_response()