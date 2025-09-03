#!/usr/bin/env python
"""
Test script to sync and debug cowanr@credos.co.uk emails specifically
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

# Configure logging to see everything
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def test_cowanr_sync():
    """Test fetching emails for cowanr@credos.co.uk specifically"""
    
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
            
            # Get UniPile settings
            dsn = getattr(settings, 'UNIPILE_DSN', 'https://api.unipile.com:13424')
            access_token = getattr(settings, 'UNIPILE_API_KEY', '')
            
            print(f"DSN: {dsn}")
            print(f"Access Token: {access_token[:10]}..." if access_token else "No token")
            
            # Create a mock UnipileClient for the fetcher
            from communications.integrations.unipile import UnipileClient
            
            unipile_client = UnipileClient(
                access_token=access_token,
                dsn=dsn
            )
            
            # Initialize email fetcher
            fetcher = EmailFetcherV2(unipile_client)
            
            print("\n=== FETCHING EMAILS FOR cowanr@credos.co.uk ===")
            
            # Fetch emails specifically for cowanr
            result = fetcher.fetch_email_threads(
                email_addresses=['cowanr@credos.co.uk'],
                account_id=connection.unipile_account_id,
                days_back=30,  # Last 30 days
                max_emails=10   # Get up to 10 emails
            )
            
            # Analyze the results
            if 'cowanr@credos.co.uk' in result:
                threads = result['cowanr@credos.co.uk']
                print(f"\nFound {len(threads)} threads for cowanr@credos.co.uk")
                
                for i, thread in enumerate(threads[:3]):  # First 3 threads
                    print(f"\n--- Thread {i+1} ---")
                    print(f"Subject: {thread.get('subject', 'No subject')}")
                    print(f"Messages: {thread.get('message_count', 0)}")
                    
                    # Check participants
                    print("\nParticipants:")
                    for p in thread.get('participants', []):
                        email = p.get('email', '')
                        name = p.get('name', '')
                        print(f"  Email: {email}")
                        print(f"  Name: '{name}'")
                        print(f"  Name repr: {repr(name)}")
                        if name and (name.startswith("'") or name.startswith('"')):
                            print(f"  *** HAS QUOTES ***")
                        print()
                    
                    # Check first message details
                    if thread.get('messages'):
                        msg = thread['messages'][0]
                        print("\nFirst message details:")
                        
                        # Check from_attendee
                        from_att = msg.get('from_attendee', {})
                        print(f"From attendee:")
                        print(f"  Identifier: {from_att.get('identifier', '')}")
                        print(f"  Display name: '{from_att.get('display_name', '')}'")
                        print(f"  Display name repr: {repr(from_att.get('display_name', ''))}")
                        
                        # Check to_attendees
                        to_atts = msg.get('to_attendees', [])
                        if to_atts:
                            print(f"\nTo attendees:")
                            for to_att in to_atts[:2]:  # First 2
                                print(f"  Identifier: {to_att.get('identifier', '')}")
                                print(f"  Display name: '{to_att.get('display_name', '')}'")
                                print(f"  Display name repr: {repr(to_att.get('display_name', ''))}")
                    
                    # Save thread to file for inspection
                    filename = f"thread_{i+1}_cowanr.json"
                    with open(filename, 'w') as f:
                        json.dump(thread, f, indent=2)
                    print(f"\nThread saved to: {filename}")
            else:
                print("\nNo threads found for cowanr@credos.co.uk")
                print(f"Result keys: {list(result.keys())}")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_cowanr_sync()