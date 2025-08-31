#!/usr/bin/env python
"""
Test script to verify attendee name syncing is working
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Record
from communications.unipile.core.client import UnipileClient
from communications.record_communications.services.record_sync_orchestrator import RecordSyncOrchestrator
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_attendee_name_sync():
    """Test that attendee names are properly fetched and used during sync"""
    
    # Use demo tenant
    schema_name = 'demo'
    
    with schema_context(schema_name):
        # Get a record with WhatsApp or LinkedIn identifiers
        records = Record.objects.filter(
            data__phone__isnull=False
        ).first()
        
        if not records:
            logger.error("No records found with phone numbers to test")
            return
        
        record = records
        logger.info(f"Testing with record {record.id}: {record.data}")
        
        # Initialize UniPile client
        unipile_client = UnipileClient(
            api_url='https://api18.unipile.com:14890/api/v1',
            access_token='<unipile_token>'  # This should come from settings
        )
        
        # Initialize orchestrator
        orchestrator = RecordSyncOrchestrator(unipile_client)
        
        # Run sync for WhatsApp only (to test the new attendee name feature)
        logger.info("Starting sync with attendee name fetching...")
        result = orchestrator.sync_record(
            record_id=record.id,
            trigger_reason='Testing attendee name sync',
            channels_to_sync=['whatsapp']  # Only sync WhatsApp for this test
        )
        
        logger.info(f"Sync result: {result}")
        
        # Check if participants have names
        from communications.models import Participant
        participants = Participant.objects.filter(
            phone__isnull=False
        ).exclude(name='')[:10]
        
        logger.info(f"\nParticipants with names after sync:")
        for p in participants:
            logger.info(f"  - {p.phone}: {p.name}")
        
        # Count participants with and without names
        total_with_phone = Participant.objects.filter(phone__isnull=False).count()
        with_names = Participant.objects.filter(phone__isnull=False).exclude(name='').count()
        
        logger.info(f"\nStatistics:")
        logger.info(f"  Total participants with phone: {total_with_phone}")
        logger.info(f"  Participants with names: {with_names}")
        logger.info(f"  Percentage with names: {(with_names/total_with_phone*100):.1f}%" if total_with_phone > 0 else "N/A")

if __name__ == '__main__':
    test_attendee_name_sync()