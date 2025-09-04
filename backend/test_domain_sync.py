#!/usr/bin/env python
"""Test domain-only sync with detailed logging"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Record
from communications.record_communications.tasks.sync_tasks import sync_record_communications

# Use demo tenant context
with schema_context('demo'):
    # Get SearchKings Africa record
    record = Record.objects.get(id=32)
    print(f"Testing sync for record: {record.name} (ID: {record.id})")
    print(f"Record data: {record.data}")
    print()
    
    # Update the domain field to trigger sync
    print("Updating company_website field to trigger domain-only sync...")
    record.data['company_website'] = 'https://searchkingsafrica.com'
    record.save()
    print()
    
    # The signal should have triggered automatically
    # Let's wait a moment and check the logs
    import time
    time.sleep(2)
    
    # Now let's manually trigger to see the logging
    print("\nManually triggering domain-only sync for debugging...")
    from communications.record_communications.services.record_sync_orchestrator import RecordSyncOrchestrator
    from communications.unipile.core.client import UnipileClient
    from django.conf import settings
    
    # Initialize client
    unipile_client = None
    if settings.UNIPILE_SETTINGS.is_configured():
        unipile_client = UnipileClient(
            dsn=settings.UNIPILE_DSN,
            access_token=settings.UNIPILE_API_KEY
        )
    
    # Create orchestrator
    orchestrator = RecordSyncOrchestrator(unipile_client)
    
    # Sync with domain-only channel
    result = orchestrator.sync_record(
        record_id=record.id,
        trigger_reason='Manual domain-only sync test',
        channels_to_sync=['domain']
    )
    
    print(f"\nSync result: {result}")
    
    # Check if participants were linked
    from communications.models import Participant
    linked_participants = Participant.objects.filter(
        secondary_record=record
    )
    
    print(f"\nParticipants linked to {record.name} as secondary:")
    for p in linked_participants:
        print(f"  - {p.name} ({p.email})")
    
    print(f"\nTotal linked: {linked_participants.count()}")