#!/usr/bin/env python
import os
import sys
import django
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Configure logging to see our debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s %(name)s: %(message)s'
)

from communications.record_communications.tasks import sync_record_communications
from pipelines.models import Record
from django_tenants.utils import schema_context

# Use oneotalent schema where we have data
with schema_context('oneotalent'):
    # Get record 66 which exists in oneotalent
    record = Record.objects.filter(id=66).first()
    if record:
        print(f'Found record {record.id}')
        print('Triggering sync...')
        
        # Call the task synchronously to see logs immediately
        # Pass tenant schema since we're calling directly
        result = sync_record_communications(
            record.id,
            tenant_schema='oneotalent',
            trigger_reason='Manual test'
        )
        print(f'\nSync Result: {result}')
    else:
        print('Record 68 not found')