#!/usr/bin/env python3
"""
Test Email sync
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Record, Pipeline
from communications.models import UserChannelConnection
from communications.unipile.core.client import UnipileClient
from communications.record_communications.services.identifier_extractor import RecordIdentifierExtractor
from django.conf import settings
from asgiref.sync import async_to_sync
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_email_sync():
    tenant_schema = 'oneotalent'
    
    with schema_context(tenant_schema):
        # Get Saul's record
        contact_pipeline = Pipeline.objects.get(name='Contacts')
        saul = Record.objects.filter(
            pipeline=contact_pipeline,
            data__first_name__icontains='saul'
        ).first()
        
        if not saul:
            print('❌ No record found for Saul')
            return
            
        print(f'✓ Found Saul: Record #{saul.id}')
        print(f'  Data: {saul.data}')
        
        # Extract email identifier
        extractor = RecordIdentifierExtractor()
        identifiers = extractor.extract_identifiers_from_record(saul)
        emails = identifiers.get('email', [])
        
        print(f'\n📧 Email addresses: {emails}')
        
        if not emails:
            print('❌ No email address found for Saul')
            return
        
        # Get Gmail connection
        gmail_conn = UserChannelConnection.objects.filter(
            channel_type='gmail',
            is_active=True,
            account_status='active'
        ).first()
        
        if not gmail_conn:
            print('❌ No Gmail connection found')
            return
            
        print(f'✓ Gmail connection: {gmail_conn.account_name} ({gmail_conn.unipile_account_id})')
        
        # Initialize UniPile client
        client = UnipileClient(
            dsn=settings.UNIPILE_DSN,
            access_token=settings.UNIPILE_API_KEY
        )
        
        # Get emails for this address
        email_address = emails[0]  # Use first email
        print(f'\n📬 Getting emails for {email_address}...')
        
        try:
            # Fetch all emails with pagination
            all_emails = []
            cursor = None
            page = 1
            
            while True:
                print(f'\n📄 Page {page}:')
                
                response = async_to_sync(client.email.get_emails)(
                    account_id=gmail_conn.unipile_account_id,
                    any_email=email_address,
                    limit=100,
                    cursor=cursor
                )
                
                emails_batch = response.get('items', [])
                print(f'  Emails in batch: {len(emails_batch)}')
                
                if emails_batch:
                    all_emails.extend(emails_batch)
                    
                    # Show sample email
                    email = emails_batch[0]
                    print(f'  Sample: "{email.get("subject", "No subject")}"')
                    print(f'  From: {email.get("from", {}).get("email", "Unknown")}')
                    print(f'  Date: {email.get("timestamp", "")}')
                
                cursor = response.get('cursor')
                print(f'  Cursor: {cursor if cursor else "None (no more pages)"}')
                
                if not cursor or not emails_batch:
                    break
                    
                page += 1
                
                if page > 10:  # Safety limit
                    print('\n⚠️ Stopping after 10 pages for safety')
                    break
            
            print(f'\n✅ Total emails found: {len(all_emails)}')
            
            if all_emails:
                # Sort by timestamp and show range
                sorted_emails = sorted(all_emails, key=lambda x: x.get('timestamp', ''))
                print(f'\n📅 Date range:')
                print(f'  Oldest: {sorted_emails[0].get("timestamp", "unknown")}')
                print(f'  Newest: {sorted_emails[-1].get("timestamp", "unknown")}')
                
        except Exception as e:
            print(f'❌ Error: {e}')
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_email_sync()