#!/usr/bin/env python3
"""
Test WhatsApp sync only
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
from communications.record_communications.services.record_sync_orchestrator import RecordSyncOrchestrator
from communications.unipile.core.client import UnipileClient
from django.conf import settings
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_whatsapp_only():
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
        
        # Get WhatsApp connection
        whatsapp_conn = UserChannelConnection.objects.filter(
            channel_type='whatsapp',
            is_active=True,
            account_status='active'
        ).first()
        
        if not whatsapp_conn:
            print('❌ No WhatsApp connection found')
            return
            
        print(f'✓ WhatsApp connection: {whatsapp_conn.account_name} ({whatsapp_conn.unipile_account_id})')
        
        # Initialize UniPile client
        client = UnipileClient(
            dsn=settings.UNIPILE_DSN,
            access_token=settings.UNIPILE_API_KEY
        )
        
        # Test the WhatsApp sync flow manually
        from communications.record_communications.utils import ProviderIdBuilder
        from communications.record_communications.services.identifier_extractor import RecordIdentifierExtractor
        from asgiref.sync import async_to_sync
        
        # Step 1: Extract identifiers from record
        extractor = RecordIdentifierExtractor()
        identifiers = extractor.extract_identifiers_from_record(saul)
        print(f'\n📞 Extracted phone numbers: {identifiers.get("phone", [])}')
        
        # Step 2: Build provider ID from phone
        phones = identifiers.get('phone', [])
        if phones:
            provider_ids = ProviderIdBuilder.build_whatsapp_ids(phones)
            print(f'\n📱 WhatsApp Provider IDs: {provider_ids}')
            
            if provider_ids:
                provider_id = provider_ids[0]
                
                # Step 2: Get 1-to-1 chats for this provider ID
                print(f'\n🔍 Getting chats for {provider_id}...')
                try:
                    response = async_to_sync(client.messaging.get_chats_from_attendee)(
                        attendee_id=provider_id,
                        account_id=whatsapp_conn.unipile_account_id,
                        limit=10
                    )
                    
                    chats = response.get('items', [])
                    print(f'✓ Found {len(chats)} WhatsApp chats')
                    
                    # Step 3: Get messages from first chat
                    if chats:
                        chat = chats[0]
                        chat_id = chat.get('id')
                        print(f'\n📬 Getting messages from chat {chat_id}...')
                        
                        msg_response = async_to_sync(client.messaging.get_all_messages)(
                            chat_id=chat_id,
                            limit=100  # Get more messages
                        )
                        
                        messages = msg_response.get('items', [])
                        print(f'✓ Found {len(messages)} messages')
                        
                        # Show first message as example
                        if messages:
                            msg = messages[0]
                            print(f'\nExample message:')
                            print(f'  From: {msg.get("sender", {}).get("name", "Unknown")}')
                            print(f'  Text: {msg.get("text", "")[:100]}...')
                            print(f'  Time: {msg.get("timestamp", "")}')
                    
                except Exception as e:
                    print(f'❌ Error: {e}')
                    import traceback
                    traceback.print_exc()
        else:
            print('❌ No phone number found for Saul')

if __name__ == '__main__':
    test_whatsapp_only()