#!/usr/bin/env python
"""
Test the actual system sync for cowanr@credos.co.uk
"""

import os
import sys
import django
import json

# Setup Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'oneo_crm.settings'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Record
from communications.record_communications.services.record_sync_orchestrator import RecordSyncOrchestrator
from communications.models import Participant
from django.contrib.auth import get_user_model
from django.conf import settings
from communications.unipile.core.client import UnipileClient
import logging

User = get_user_model()

# Configure logging to see everything
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def test_system_sync_for_cowanr():
    """Test the actual system sync specifically for cowanr@credos.co.uk"""
    
    with schema_context('oneotalent'):
        print("=== TESTING SYSTEM SYNC FOR cowanr@credos.co.uk ===\n")
        
        # Get the user for created_by context
        user = User.objects.filter(email='josh@oneodigital.com').first()
        if not user:
            print("User josh@oneodigital.com not found. Creating it...")
            user = User.objects.create_user(
                username='josh',
                email='josh@oneodigital.com',
                password='admin123'
            )
        
        # First, let's clear existing participants with cowanr
        print("1. Clearing existing cowanr participants...")
        deleted = Participant.objects.filter(email__icontains='cowanr').delete()
        print(f"   Deleted {deleted[0]} participants\n")
        
        # Find or create a test record with cowanr email
        print("2. Finding/creating test record with cowanr email...")
        
        # Find a record with email field containing cowanr
        record = Record.objects.filter(
            data__email__icontains='cowanr'
        ).first()
        
        if not record:
            # Create a test record
            from pipelines.models import Pipeline, Field
            
            # Get or create a test pipeline
            pipeline = Pipeline.objects.first()
            if not pipeline:
                print("   No pipeline found. Creating test pipeline...")
                pipeline = Pipeline.objects.create(
                    name='Test Pipeline',
                    slug='test_pipeline',
                    description='Test pipeline for cowanr sync'
                )
                
                # Create email field
                Field.objects.create(
                    pipeline=pipeline,
                    name='email',
                    slug='email',
                    field_type='email',
                    label='Email',
                    is_required=True,
                    order=1
                )
            
            # Create record with cowanr email
            record = Record.objects.create(
                pipeline=pipeline,
                created_by=user,
                updated_by=user,
                data={
                    'email': 'cowanr@credos.co.uk',
                    'name': 'Test Cowanr Record'
                }
            )
            print(f"   Created test record: {record.id}")
        else:
            print(f"   Found existing record: {record.id}")
        
        print(f"   Record data: {record.data}\n")
        
        # Initialize the orchestrator with UnipileClient
        print("3. Initializing sync orchestrator with UnipileClient...")
        
        # Get UniPile settings
        dsn = getattr(settings, 'UNIPILE_DSN', 'https://api.unipile.com:13424')
        access_token = getattr(settings, 'UNIPILE_API_KEY', '')
        
        print(f"   DSN: {dsn}")
        print(f"   Access Token: {access_token[:10]}...\\n" if access_token else "   No access token\\n")
        
        # Create UnipileClient
        unipile_client = UnipileClient(
            access_token=access_token,
            dsn=dsn
        )
        
        orchestrator = RecordSyncOrchestrator(unipile_client=unipile_client)
        
        # Run sync for this specific record
        print("4. Running sync for record...")
        print("   This will extract identifiers and sync communications\n")
        
        try:
            result = orchestrator.sync_record(record.id)
            print(f"\n5. Sync completed with result: {result}\n")
        except Exception as e:
            print(f"\n   Sync error: {e}")
            import traceback
            traceback.print_exc()
        
        # Check what participants were created
        print("6. Checking participants created...")
        participants = Participant.objects.filter(email__icontains='cowanr')
        
        for p in participants:
            print(f"\n   Participant ID: {p.id}")
            print(f"   Email: {p.email}")
            print(f"   Name: '{p.name}'")
            print(f"   Name repr: {repr(p.name)}")
            if p.name and ("'" in p.name or '"' in p.name):
                print(f"   *** NAME CONTAINS QUOTES ***")
            print(f"   Display name: {p.get_display_name()}")
            print(f"   Created: {p.created_at}")

if __name__ == '__main__':
    test_system_sync_for_cowanr()