#!/usr/bin/env python3
"""
Test script for record communications sync
"""
import django
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection
from django_tenants.utils import schema_context
from pipelines.models import Record, Pipeline
from communications.models import UserChannelConnection
from communications.record_communications.services.record_sync_orchestrator import RecordSyncOrchestrator
from communications.unipile.core.client import UnipileClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use the correct tenant
tenant_schema = 'oneotalent'

def test_sync():
    # Switch to tenant schema
    with schema_context(tenant_schema):
        try:
            # Get the contact pipeline
            contact_pipeline = Pipeline.objects.get(name='Contacts')
            print(f'Found contact pipeline: {contact_pipeline.id}')
            
            # Find Saul's record
            saul_records = Record.objects.filter(
                pipeline=contact_pipeline,
                data__first_name__icontains='saul'
            )
            
            print(f'Found {saul_records.count()} records matching "Saul"')
            
            if saul_records.exists():
                saul = saul_records.first()
                print(f'\nUsing record: {saul.id}')
                print(f'Record data: {saul.data}')
                
                # Extract identifiers
                from communications.record_communications.services.identifier_extractor import RecordIdentifierExtractor
                extractor = RecordIdentifierExtractor()
                identifiers = extractor.extract_identifiers_from_record(saul)
                print(f'\nExtracted identifiers:')
                for key, values in identifiers.items():
                    print(f'  {key}: {values}')
                
                # Get active connections
                connections = UserChannelConnection.objects.filter(
                    is_active=True,
                    account_status='active'
                )
                
                print(f'\nActive connections:')
                for conn in connections:
                    print(f'  - {conn.channel_type}: {conn.account_name} (ID: {conn.unipile_account_id})')
                
                # Initialize UniPile client
                from django.conf import settings
                client = UnipileClient(
                    dsn=settings.UNIPILE_DSN,
                    access_token=settings.UNIPILE_API_KEY
                )
                
                # Initialize orchestrator
                orchestrator = RecordSyncOrchestrator(unipile_client=client)
                
                # Run sync with more detailed logging
                print(f'\nStarting sync for record {saul.id}...')
                print('=' * 60)
                
                result = orchestrator.sync_record(
                    record_id=saul.id,
                    trigger_reason='Testing sync with WhatsApp/LinkedIn fixes'
                )
                
                print('\n' + '=' * 60)
                print(f'SYNC RESULT:')
                print(f'Success: {result.get("success")}')
                print(f'Total conversations: {result.get("total_conversations", 0)}')
                print(f'Total messages: {result.get("total_messages", 0)}')
                
                if 'channel_results' in result:
                    print(f'\nChannel breakdown:')
                    for channel, stats in result['channel_results'].items():
                        print(f'  {channel}: {stats.get("conversations", 0)} conversations, {stats.get("messages", 0)} messages')
                
                if 'error' in result:
                    print(f'\nError: {result["error"]}')
                    
        except Pipeline.DoesNotExist:
            print('Contact pipeline not found')
        except Exception as e:
            print(f'Error: {e}')
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_sync()
