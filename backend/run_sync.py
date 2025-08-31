#!/usr/bin/env python3
"""
Simple sync runner
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Django first
django.setup()

# Now import the rest
from django_tenants.utils import schema_context
from pipelines.models import Record, Pipeline
from communications.models import UserChannelConnection
from communications.record_communications.services.record_sync_orchestrator import RecordSyncOrchestrator
from communications.unipile.core.client import UnipileClient
from django.conf import settings

def run_sync():
    tenant_schema = 'oneotalent'
    
    with schema_context(tenant_schema):
        # Get the contact pipeline
        contact_pipeline = Pipeline.objects.get(name='Contacts')
        print(f'✓ Found contact pipeline: {contact_pipeline.id}')
        
        # Find Saul's record
        saul = Record.objects.filter(
            pipeline=contact_pipeline,
            data__first_name__icontains='saul'
        ).first()
        
        if not saul:
            print('✗ No record found for Saul')
            return
            
        print(f'✓ Found Saul: Record #{saul.id}')
        print(f'  Name: {saul.data.get("first_name", "")} {saul.data.get("last_name", "")}')
        print(f'  Email: {saul.data.get("email", "")}')
        print(f'  Phone: {saul.data.get("phone", "")}')
        print(f'  LinkedIn: {saul.data.get("linkedin", "")}')
        
        # Check connections
        connections = UserChannelConnection.objects.filter(
            is_active=True,
            account_status='active'
        )
        
        print(f'\n✓ Active connections: {connections.count()}')
        for conn in connections:
            print(f'  - {conn.channel_type}: {conn.account_name}')
        
        # Initialize UniPile client
        # Get settings with defaults - note: settings uses UNIPILE_API_KEY not ACCESS_TOKEN
        dsn = getattr(settings, 'UNIPILE_DSN', os.environ.get('UNIPILE_DSN', ''))
        api_key = getattr(settings, 'UNIPILE_API_KEY', os.environ.get('UNIPILE_API_KEY', ''))
        
        if not dsn or not api_key:
            print('⚠️  UniPile credentials not configured')
            print('  Set UNIPILE_DSN and UNIPILE_API_KEY in settings or environment')
            # Try to use the UnipileSettings object
            from oneo_crm.settings import unipile_settings
            dsn = unipile_settings.dsn
            api_key = unipile_settings.api_key
            if not dsn or not api_key:
                print('  Could not get credentials from UnipileSettings either')
                return
            print(f'  Using UnipileSettings: DSN={dsn[:30]}...')
            
        client = UnipileClient(
            dsn=dsn,
            access_token=api_key  # UnipileClient expects 'access_token' parameter
        )
        
        # Initialize orchestrator
        orchestrator = RecordSyncOrchestrator(unipile_client=client)
        
        # Run sync
        print(f'\n🔄 Starting sync for record #{saul.id}...\n')
        print('=' * 60)
        
        try:
            result = orchestrator.sync_record(
                record_id=saul.id,
                trigger_reason='Manual sync test'
            )
            
            print('=' * 60)
            
            if result.get('success'):
                print('\n✅ SYNC SUCCESSFUL!')
                print(f'\n📊 Summary:')
                print(f'  Total conversations: {result.get("total_conversations", 0)}')
                print(f'  Total messages: {result.get("total_messages", 0)}')
                
                if 'channel_results' in result:
                    print(f'\n📱 Channel breakdown:')
                    for channel, stats in result['channel_results'].items():
                        if stats.get('conversations', 0) > 0 or stats.get('messages', 0) > 0:
                            print(f'  {channel.upper()}:')
                            print(f'    - Conversations: {stats.get("conversations", 0)}')
                            print(f'    - Messages: {stats.get("messages", 0)}')
            else:
                print('\n❌ SYNC FAILED!')
                if 'error' in result:
                    print(f'  Error: {result["error"]}')
                    
        except Exception as e:
            print(f'\n❌ Exception during sync: {e}')
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    run_sync()