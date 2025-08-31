#!/usr/bin/env python
"""
Test sync with name fetching
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.record_communications.tasks import sync_record_communications

with schema_context('oneotalent'):
    print("=" * 60)
    print("TRIGGERING SYNC FOR RECORD 66")
    print("=" * 60)
    
    # Run sync synchronously for debugging
    result = sync_record_communications(
        record_id=66,
        tenant_schema='oneotalent',
        triggered_by_id=1,
        trigger_reason='Test sync with name debugging'
    )
    
    print("\nSync result:")
    print(result)
    
    # Check if names were saved
    from communications.models import Participant
    
    print("\n" + "=" * 60)
    print("CHECKING PARTICIPANTS AFTER SYNC")
    print("=" * 60)
    
    # Check WhatsApp participants with provider_id
    participants = Participant.objects.filter(
        metadata__provider_id__isnull=False
    )[:5]
    
    for p in participants:
        provider_id = p.metadata.get('provider_id', '')
        print(f"\nParticipant {p.id}:")
        print(f"  Provider ID: {provider_id}")
        print(f"  Name: '{p.name}' (empty: {not p.name})")
        print(f"  Phone: {p.phone}")
