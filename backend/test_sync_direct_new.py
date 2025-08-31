#!/usr/bin/env python
"""Test record sync directly without Celery"""

import os
import sys
import django
from pathlib import Path

# Setup Django environment
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

import asyncio
from asgiref.sync import sync_to_async
from django.conf import settings
from django_tenants.utils import schema_context
from communications.record_communications.services.record_sync_orchestrator import RecordSyncOrchestrator
from communications.record_communications.models import RecordCommunicationProfile
from communications.unipile.core.client import UnipileClient
from pipelines.models import Pipeline, Record

async def main():
    print("🧪 Testing Direct Record Sync")
    print("=" * 60)
    
    tenant_schema = 'oneotalent'
    record_id = 66
    
    # Get the record with sync_to_async
    @sync_to_async
    def get_record():
        with schema_context(tenant_schema):
            return Record.objects.filter(id=record_id).first()
    
    record = await get_record()
    if not record:
        print(f"❌ Record {record_id} not found")
        return
        
    name = record.data.get('first_name', 'Unknown')
    print(f"✅ Record: {name} (ID: {record_id})")
    
    # Get or create communication profile with sync_to_async
    @sync_to_async
    def get_or_create_profile():
        with schema_context(tenant_schema):
            return RecordCommunicationProfile.objects.get_or_create(
                record_id=record_id
            )
    
    profile, created = await get_or_create_profile()
    print(f"✅ Communication Profile: {'Created' if created else 'Existing'}")
    
    # Create UnipileClient and orchestrator
    unipile_client = UnipileClient(
        dsn=settings.UNIPILE_DSN,
        access_token=settings.UNIPILE_API_KEY
    )
    orchestrator = RecordSyncOrchestrator(unipile_client)
    print(f"✅ Orchestrator created with UnipileClient for tenant: {tenant_schema}")
    
    # Run sync
    print("\n🚀 Starting sync...")
    try:
        # sync_record is not async, need to wrap it
        @sync_to_async
        def run_sync():
            # Run the sync within schema context
            with schema_context(tenant_schema):
                return orchestrator.sync_record(record_id)
        
        result = await run_sync()
        
        print(f"\n✅ Sync completed!")
        print(f"   Messages synced: {result.get('messages_synced', 0)}")
        print(f"   Conversations: {result.get('conversations', 0)}")
        print(f"   Status: {result.get('status', 'unknown')}")
        
        if 'error' in result:
            print(f"   ⚠️ Error: {result['error']}")
            
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ Test completed!")

if __name__ == '__main__':
    asyncio.run(main())