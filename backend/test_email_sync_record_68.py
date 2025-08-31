#!/usr/bin/env python
"""
Test email sync for Record 68 (Saul Chilchik)
This script tests the record sync system with enhanced logging.
"""

import os
import sys
import django
import logging
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Configure logging to be very verbose
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'email_sync_record_68_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

# Set specific loggers to INFO level
logging.getLogger('communications.record_communications').setLevel(logging.INFO)
logging.getLogger('communications.unipile').setLevel(logging.INFO)
logging.getLogger('django.db.backends').setLevel(logging.WARNING)  # Reduce SQL noise

from django_tenants.utils import schema_context
from pipelines.models import Record
from communications.models import UserChannelConnection
from communications.record_communications.services.record_sync_orchestrator import RecordSyncOrchestrator
from communications.unipile.core.client import UnipileClient
from django.conf import settings

logger = logging.getLogger(__name__)

def test_email_sync_record_68():
    """Test email sync for Saul Chilchik (Record 66 in oneotalent)"""
    
    # Use the oneotalent tenant
    tenant_schema = 'oneotalent'
    record_id = 66  # Saul is ID 66 in oneotalent tenant
    
    print("\n" + "="*80)
    print("EMAIL SYNC TEST - RECORD 66 (Saul Chilchik)")
    print("="*80)
    print(f"Timestamp: {datetime.now()}")
    print(f"Tenant: {tenant_schema}")
    print(f"Record ID: {record_id}")
    print("="*80 + "\n")
    
    with schema_context(tenant_schema):
        try:
            # 1. Verify record exists
            print("1. Verifying record exists...")
            record = Record.objects.get(id=record_id)
            print(f"   ✓ Found record: {record.data.get('first_name', '')} {record.data.get('last_name', '')}")
            print(f"   ✓ Pipeline: {record.pipeline.name}")
            
            # 2. Check for email in record data
            print("\n2. Checking record for email addresses...")
            email_fields = ['email', 'email_address', 'work_email', 'personal_email']
            found_emails = []
            
            for field in email_fields:
                if field in record.data and record.data[field]:
                    found_emails.append(record.data[field])
                    print(f"   ✓ Found {field}: {record.data[field]}")
            
            if not found_emails:
                print("   ⚠ No email addresses found in record data")
                print(f"   Record data keys: {list(record.data.keys())}")
            else:
                print(f"   Total emails found: {len(found_emails)}")
            
            # 3. Check email connections
            print("\n3. Checking email channel connections...")
            email_connections = UserChannelConnection.objects.filter(
                channel_type__in=['email', 'gmail', 'outlook'],
                is_active=True,
                account_status='active'
            )
            
            for conn in email_connections:
                print(f"   ✓ {conn.channel_type}: {conn.unipile_account_id} (User: {conn.user.email})")
            
            if not email_connections:
                print("   ⚠ No active email connections found")
                return
            
            # 4. Initialize UniPile client
            print("\n4. Initializing UniPile client...")
            if not settings.UNIPILE_SETTINGS.is_configured():
                print("   ✗ UniPile is not configured in environment")
                return
            
            unipile_client = UnipileClient(
                dsn=settings.UNIPILE_DSN,
                access_token=settings.UNIPILE_API_KEY
            )
            print(f"   ✓ UniPile client initialized")
            print(f"   ✓ DSN: {settings.UNIPILE_SETTINGS.base_url}")
            
            # 5. Run the sync with detailed configuration
            print("\n5. Starting email sync...")
            print("   Configuration:")
            print("   - Historical days: 0 (fetch all)")
            print("   - Max emails: 100 (for testing)")
            print("   - Batch size: 100")
            print("\n" + "-"*60)
            
            orchestrator = RecordSyncOrchestrator(unipile_client)
            
            # Override sync config for testing with 500 emails
            # Set channel-specific config to limit emails
            from communications.record_communications.utils import SyncConfig
            test_config = SyncConfig()
            test_config.email_config = {
                'enabled': True,
                'historical_days': 0,  # Fetch all history
                'max_messages': 500,    # Fetch 500 emails for volume testing
                'batch_size': 100       # Use 100 per batch for efficiency
            }
            test_config.gmail_config = {
                'enabled': True,
                'historical_days': 0,
                'max_messages': 500,    # Fetch 500 emails for volume testing
                'batch_size': 100
            }
            orchestrator.sync_config = test_config
            
            # Run the sync
            start_time = datetime.now()
            result = orchestrator.sync_record(
                record_id=record_id,
                trigger_reason='Manual test sync for email debugging'
            )
            end_time = datetime.now()
            
            print("-"*60)
            
            # 6. Display results
            print("\n6. Sync Results:")
            if result.get('success'):
                print("   ✓ SYNC SUCCESSFUL")
                print(f"   - Total conversations: {result.get('total_conversations', 0)}")
                print(f"   - Total messages: {result.get('total_messages', 0)}")
                print(f"   - Duration: {(end_time - start_time).total_seconds():.2f} seconds")
                
                # Show channel-specific results
                channel_results = result.get('channel_results', {})
                if channel_results:
                    print("\n   Channel breakdown:")
                    for channel, stats in channel_results.items():
                        if 'email' in channel.lower() or 'gmail' in channel.lower():
                            print(f"   - {channel}: {stats.get('messages', 0)} messages in {stats.get('conversations', 0)} conversations")
            else:
                print("   ✗ SYNC FAILED")
                print(f"   Error: {result.get('error', 'Unknown error')}")
            
            # 7. Check stored data
            print("\n7. Checking stored data...")
            from communications.record_communications.models import (
                RecordCommunicationProfile, 
                RecordCommunicationLink
            )
            
            profile = RecordCommunicationProfile.objects.filter(record_id=record_id).first()
            if profile:
                print(f"   ✓ Communication profile exists")
                print(f"   - Total messages: {profile.total_messages}")
                print(f"   - Total conversations: {profile.total_conversations}")
                print(f"   - Last sync: {profile.last_full_sync}")
                print(f"   - Identifiers: {profile.communication_identifiers}")
            
            links = RecordCommunicationLink.objects.filter(record_id=record_id).count()
            print(f"   ✓ Communication links: {links}")
            
        except Record.DoesNotExist:
            print(f"✗ Record {record_id} not found in tenant {tenant_schema}")
        except Exception as e:
            print(f"✗ Error during sync: {e}")
            logger.exception("Detailed error:")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_email_sync_record_68()