#!/usr/bin/env python
"""
Debug the sync orchestrator for LinkedIn
"""
import os
import django
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(name)s: %(message)s'
)

from django_tenants.utils import schema_context
from tenants.models import Tenant
from pipelines.models import Record
from communications.record_communications.services.record_sync_orchestrator import RecordSyncOrchestrator
from django.contrib.auth import get_user_model

User = get_user_model()

# Use oneotalent tenant
tenant = Tenant.objects.get(schema_name='oneotalent')

with schema_context(tenant.schema_name):
    print("🏢 Testing in tenant: oneotalent\n")
    
    # Get user
    user = User.objects.filter(is_active=True).first()
    
    # Get record 93
    record = Record.objects.get(id=93)
    print(f"📄 Record {record.id}: {record.title}")
    print(f"   LinkedIn data: {record.data.get('linkedin')}\n")
    
    # Initialize UnipileClient
    from django.conf import settings
    from communications.unipile.core.client import UnipileClient
    
    unipile_client = None
    if hasattr(settings, 'UNIPILE_DSN') and hasattr(settings, 'UNIPILE_API_KEY'):
        unipile_client = UnipileClient(
            dsn=settings.UNIPILE_DSN,
            access_token=settings.UNIPILE_API_KEY
        )
        print("✅ UnipileClient initialized\n")
    else:
        print("❌ UnipileClient not configured - sync will return 0 results\n")
    
    # Initialize orchestrator with UnipileClient
    orchestrator = RecordSyncOrchestrator(unipile_client=unipile_client)
    
    print("="*60)
    print("🔍 STARTING LINKEDIN SYNC")
    print("="*60)
    
    # Run sync with LinkedIn only
    result = orchestrator.sync_record(
        record_id=record.id,
        triggered_by=user,
        trigger_reason="Debug LinkedIn sync",
        channels_to_sync=['linkedin']
    )
    
    print("\n" + "="*60)
    print("📊 SYNC RESULT")
    print("="*60)
    print(f"Success: {result['success']}")
    print(f"Total Conversations: {result['total_conversations']}")
    print(f"Total Messages: {result['total_messages']}")
    
    if 'channel_results' in result:
        linkedin_result = result['channel_results'].get('linkedin', {})
        print(f"\nLinkedIn Channel Result:")
        print(f"  Conversations: {linkedin_result.get('conversations', 0)}")
        print(f"  Messages: {linkedin_result.get('messages', 0)}")