#!/usr/bin/env python
"""Test domain-only sync with existing SearchKings record"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model

User = get_user_model()

# Use oneotalent tenant context  
with schema_context('oneotalent'):
    from pipelines.models import Record, Pipeline
    from communications.models import Participant
    
    # Get the SearchKings record that already exists (ID: 99)
    record = Record.objects.get(id=99)
    print(f"Using existing record: {record.title} (ID: {record.id})")
    print(f"Current data: {record.data}")
    print(f"Company website: {record.data.get('company_website')}")
    print(f"Domain field: {record.data.get('domain')}")
    
    # Check participants with searchkings domain
    print("\n" + "="*60)
    print("CHECKING SEARCHKINGS PARTICIPANTS")
    print("="*60)
    
    searchkings_participants = Participant.objects.filter(
        email__iendswith='@searchkingsafrica.com'
    )
    print(f"\nFound {searchkings_participants.count()} participants with @searchkingsafrica.com:")
    for p in searchkings_participants:
        print(f"  - {p.name} ({p.email})")
        print(f"    Primary: {p.contact_record.title if p.contact_record else 'None'}")
        print(f"    Secondary: {p.secondary_record.title if p.secondary_record else 'None'} (ID: {p.secondary_record.id if p.secondary_record else 'None'})")
    
    # Check if any need linking
    unlinked = [p for p in searchkings_participants if not p.secondary_record]
    if unlinked:
        print(f"\nFound {len(unlinked)} unlinked participants - will trigger sync")
        
        # Update the record to trigger domain-only sync
        print("\n" + "="*60)
        print("TRIGGERING DOMAIN UPDATE")  
        print("="*60)
        
        # Toggle the trailing slash to trigger a change
        current_website = record.data.get('company_website', '')
        if current_website.endswith('/'):
            new_website = current_website.rstrip('/')
        else:
            new_website = current_website + '/'
        
        print(f"Updating company_website from '{current_website}' to '{new_website}'")
        
        # Get a user for updated_by
        admin_user = User.objects.filter(email='admin@oneo.com').first()
        if admin_user:
            record.updated_by = admin_user
        
        record.data['company_website'] = new_website
        record.save()
        print("Save completed - signal should have triggered domain-only sync")
        
        # Wait for async processing
        import time
        print("\nWaiting 3 seconds for async processing...")
        time.sleep(3)
        
        # Re-check participants
        searchkings_participants = Participant.objects.filter(
            email__iendswith='@searchkingsafrica.com'
        )
        print(f"\nRe-checking participants after sync:")
        for p in searchkings_participants:
            print(f"  - {p.name} ({p.email})")
            print(f"    Primary: {p.contact_record.title if p.contact_record else 'None'}")
            print(f"    Secondary: {p.secondary_record.title if p.secondary_record else 'None'} (ID: {p.secondary_record.id if p.secondary_record else 'None'})")
        
        # Check sync jobs
        from communications.record_communications.models import RecordSyncJob
        recent_jobs = RecordSyncJob.objects.filter(record=record).order_by('-created_at')[:5]
        
        print(f"\nRecent sync jobs for record {record.id}:")
        for job in recent_jobs:
            print(f"  - {job.created_at.strftime('%H:%M:%S')}: {job.status} - {job.trigger_reason}")
    else:
        print("\nAll participants already linked!")