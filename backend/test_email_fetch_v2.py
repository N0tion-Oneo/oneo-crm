#!/usr/bin/env python
"""Test improved email fetching with complete thread retrieval"""
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
    """Test fetching complete email threads"""
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
        print("=" * 60)
        
        result = fetcher.fetch_emails_for_addresses(
            email_addresses=[email_address],
            account_id=connection.unipile_account_id,
            days_back=30,  # Last 30 days
            max_emails=10  # Get 10 threads
        )
        
        # Analyze results
        for email_addr, threads in result.items():
            print(f"\n📧 Results for {email_addr}:")
            print(f"Total threads: {len(threads)}")
            print("-" * 60)
            
            total_messages = 0
            empty_threads = 0
            
            for i, thread in enumerate(threads, 1):
                msg_count = len(thread.get('messages', []))
                total_messages += msg_count
                
                if msg_count == 0:
                    empty_threads += 1
                
                print(f"\n{i}. Thread: {thread.get('subject', 'No subject')[:60]}...")
                print(f"   Thread ID: {thread.get('thread_id', 'None')[:30]}...")
                print(f"   Messages: {msg_count}")
                
                if msg_count == 0:
                    print(f"   ⚠️ EMPTY THREAD!")
                else:
                    # Show message details
                    for j, msg in enumerate(thread['messages'][:3], 1):  # Show first 3 messages
                        print(f"   Message {j}:")
                        print(f"     From: {msg.get('from_attendee', {}).get('identifier', 'Unknown')}")
                        print(f"     Date: {msg.get('date', 'Unknown')[:19]}")
                        
                        # Check if Robbie is involved
                        robbie_in_from = email_address in msg.get('from_attendee', {}).get('identifier', '').lower()
                        robbie_in_to = any(
                            email_address in att.get('identifier', '').lower() 
                            for att in msg.get('to_attendees', [])
                        )
                        
                        if robbie_in_from:
                            print(f"     ➡️ Robbie sent this")
                        elif robbie_in_to:
                            print(f"     ⬅️ Robbie received this")
                    
                    if msg_count > 3:
                        print(f"   ... and {msg_count - 3} more messages")
            
            # Summary
            print(f"\n📊 SUMMARY:")
            print(f"  - Total threads: {len(threads)}")
            print(f"  - Total messages: {total_messages}")
            print(f"  - Empty threads: {empty_threads}")
            print(f"  - Average messages per thread: {total_messages / len(threads) if threads else 0:.1f}")

if __name__ == '__main__':
    test_email_fetch()