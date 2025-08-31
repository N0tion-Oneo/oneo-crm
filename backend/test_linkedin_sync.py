#!/usr/bin/env python3
"""
Test LinkedIn sync following the specified flow:
1) Retrieve a profile (with normalized LinkedIn from duplicate detection)
2) List all 1-to-1 chats for the attendee
3) List all messages from chats
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

def test_linkedin_sync():
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
        
        # Extract LinkedIn identifier
        extractor = RecordIdentifierExtractor()
        identifiers = extractor.extract_identifiers_from_record(saul)
        linkedin_ids = identifiers.get('linkedin', [])
        
        print(f'\n🔗 LinkedIn identifiers: {linkedin_ids}')
        
        if not linkedin_ids:
            print('❌ No LinkedIn identifier found for Saul')
            return
        
        # Get LinkedIn connection
        linkedin_conn = UserChannelConnection.objects.filter(
            channel_type='linkedin',
            is_active=True,
            account_status='active'
        ).first()
        
        if not linkedin_conn:
            print('❌ No LinkedIn connection found')
            return
            
        print(f'✓ LinkedIn connection: {linkedin_conn.account_name} ({linkedin_conn.unipile_account_id})')
        
        # Initialize UniPile client
        client = UnipileClient(
            dsn=settings.UNIPILE_DSN,
            access_token=settings.UNIPILE_API_KEY
        )
        
        # Step 1: Retrieve LinkedIn profile
        linkedin_username = linkedin_ids[0]  # Use first LinkedIn ID
        print(f'\n📋 Step 1: Retrieving LinkedIn profile for username: {linkedin_username}...')
        
        try:
            profile_response = async_to_sync(client.users.retrieve_profile)(
                identifier=linkedin_username,
                account_id=linkedin_conn.unipile_account_id
            )
            
            if profile_response:
                provider_id = profile_response.get('provider_id')
                print(f'✓ Profile retrieved. Provider ID: {provider_id}')
                print(f'  Name: {profile_response.get("name", "Unknown")}')
                
                if not provider_id:
                    print('❌ No provider_id in profile response')
                    return
                
                # Step 2: Get 1-to-1 chats for this provider_id
                print(f'\n🔍 Step 2: Getting chats for provider_id {provider_id}...')
                
                chats_response = async_to_sync(client.messaging.get_chats_from_attendee)(
                    attendee_id=provider_id,
                    account_id=linkedin_conn.unipile_account_id,
                    limit=50
                )
                
                chats = chats_response.get('items', [])
                print(f'✓ Found {len(chats)} LinkedIn chats')
                
                # Step 3: Get messages from chats
                total_messages = 0
                for i, chat in enumerate(chats[:5], 1):  # Process first 5 chats
                    chat_id = chat.get('id')
                    chat_name = chat.get('name', 'Unknown')
                    print(f'\n📬 Chat {i}: {chat_name} (ID: {chat_id})')
                    
                    # Fetch messages with pagination
                    all_messages = []
                    cursor = None
                    
                    while True:
                        msg_response = async_to_sync(client.messaging.get_all_messages)(
                            chat_id=chat_id,
                            limit=100,
                            cursor=cursor
                        )
                        
                        messages = msg_response.get('items', [])
                        if messages:
                            all_messages.extend(messages)
                            
                        cursor = msg_response.get('cursor')
                        if not cursor or not messages:
                            break
                    
                    print(f'  Messages: {len(all_messages)}')
                    total_messages += len(all_messages)
                    
                    # Show sample message
                    if all_messages:
                        msg = all_messages[0]
                        print(f'  Sample: "{msg.get("text", "")[:100]}..."')
                        print(f'  From: {msg.get("sender", {}).get("name", "Unknown")}')
                        print(f'  Time: {msg.get("timestamp", "")}')
                
                print(f'\n✅ Total LinkedIn messages found: {total_messages}')
            else:
                print('❌ No profile response received')
                
        except Exception as e:
            print(f'❌ Error: {e}')
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_linkedin_sync()