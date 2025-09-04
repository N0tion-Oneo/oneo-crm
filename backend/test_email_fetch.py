#!/usr/bin/env python
"""Test email fetching to debug empty conversations"""
import os
import sys
import django
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from django_tenants.utils import schema_context
from communications.models import UserChannelConnection
from communications.unipile.core.client import UnipileClient
from communications.record_communications.unipile_integration.email_fetcher_v2 import EmailFetcherV2
from django.conf import settings

def test_email_fetch():
    """Test fetching emails for Robbie"""
    with schema_context('oneotalent'):
        # Get Gmail connection
        connection = UserChannelConnection.objects.filter(
            channel_type='gmail',
            is_active=True
        ).first()
        
        if not connection:
            print("No active Gmail connection found")
            return
            
        print(f"Using Gmail connection: {connection.unipile_account_id}")
        
        # Initialize UniPile client
        if not settings.UNIPILE_SETTINGS.is_configured():
            print("UniPile not configured")
            return
            
        unipile_client = UnipileClient(
            dsn=settings.UNIPILE_DSN,
            access_token=settings.UNIPILE_API_KEY
        )
        
        # Initialize email fetcher
        fetcher = EmailFetcherV2(unipile_client)
        
        # Fetch emails for Robbie
        email_address = 'cowanr@credos.co.uk'
        print(f"\nFetching emails for: {email_address}")
        
        result = fetcher.fetch_emails_for_addresses(
            email_addresses=[email_address],
            account_id=connection.unipile_account_id,
            days_back=30,  # Last 30 days
            max_emails=100
        )
        
        # Analyze results
        for email_addr, threads in result.items():
            print(f"\nResults for {email_addr}:")
            print(f"Total threads: {len(threads)}")
            
            for i, thread in enumerate(threads[:15], 1):  # Show first 15
                msg_count = len(thread.get('messages', []))
                print(f"\n{i}. Thread: {thread.get('subject', 'No subject')[:60]}...")
                print(f"   Thread ID: {thread.get('thread_id', 'None')}")
                print(f"   Messages: {msg_count}")
                
                if msg_count == 0:
                    print(f"   ⚠️ EMPTY THREAD!")
                else:
                    # Show first message details
                    first_msg = thread['messages'][0]
                    print(f"   First message:")
                    print(f"     From: {first_msg.get('from_attendee', {}).get('identifier', 'Unknown')}")
                    print(f"     Date: {first_msg.get('date', 'Unknown')}")
                    
                    # Check if Robbie is in this message
                    robbie_in_from = email_address in first_msg.get('from_attendee', {}).get('identifier', '').lower()
                    robbie_in_to = any(
                        email_address in att.get('identifier', '').lower() 
                        for att in first_msg.get('to_attendees', [])
                    )
                    robbie_in_cc = any(
                        email_address in att.get('identifier', '').lower() 
                        for att in first_msg.get('cc_attendees', [])
                    )
                    
                    if robbie_in_from:
                        print(f"     Robbie is SENDER")
                    if robbie_in_to:
                        print(f"     Robbie is in TO")
                    if robbie_in_cc:
                        print(f"     Robbie is in CC")

if __name__ == '__main__':
    test_email_fetch()