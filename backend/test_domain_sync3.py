#!/usr/bin/env python
"""Test domain-only sync with existing records"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django_tenants.utils import schema_context, get_tenant_model
from django.contrib.auth import get_user_model

# Get the oneotalent tenant
Tenant = get_tenant_model()
tenant = Tenant.objects.get(schema_name='oneotalent')
print(f"Using tenant: {tenant.schema_name} ({tenant.name})")

User = get_user_model()

# Use oneotalent tenant context  
with schema_context('oneotalent'):
    from pipelines.models import Record, Pipeline
    from communications.models import Participant
    
    # Get a user for created_by
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.first()
    print(f"Using user: {admin_user.email if admin_user else 'None'}")
    
    # Get the companies pipeline
    companies_pipeline = Pipeline.objects.get(slug='companies')
    print(f"Found companies pipeline: {companies_pipeline.name} (ID: {companies_pipeline.id})")
    
    # List existing companies with website fields
    print("\nExisting companies with website data:")
    for r in Record.objects.filter(pipeline=companies_pipeline):
        website = r.data.get('company_website', '')
        if website:
            print(f"  - {r.title} (ID: {r.id}): {website}")
    
    # Try to find or create SearchKings
    try:
        record = Record.objects.get(title__icontains='Search Kings', pipeline=companies_pipeline)
        print(f"\nFound record: {record.title} (ID: {record.id})")
    except Record.DoesNotExist:
        # Create it with proper user
        print("\nCreating Search Kings Africa record...")
        record = Record.objects.create(
            pipeline=companies_pipeline,
            title="Search Kings Africa",
            created_by=admin_user,
            data={
                'company_name': 'Search Kings Africa',
                'company_website': 'https://searchkingsafrica.com',
                'domain': 'searchkingsafrica.com'  # Add domain field directly
            }
        )
        print(f"Created record: {record.title} (ID: {record.id})")
    
    print(f"Current data: {record.data}")
    
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
        print(f"    Secondary: {p.secondary_record.title if p.secondary_record else 'None'}")
    
    # Now trigger domain linking manually
    if searchkings_participants.count() > 0 and not any(p.secondary_record == record for p in searchkings_participants):
        print("\n" + "="*60)
        print("MANUALLY LINKING PARTICIPANTS")
        print("="*60)
        
        from communications.record_communications.storage.participant_link_manager import ParticipantLinkManager
        link_manager = ParticipantLinkManager()
        
        linked_count = 0
        for p in searchkings_participants:
            if not p.secondary_record:
                success = link_manager.link_participant_to_record(
                    participant=p,
                    record=record,
                    confidence=0.8,
                    method='domain_match',
                    as_secondary=True
                )
                if success:
                    linked_count += 1
                    print(f"  ✅ Linked {p.name} to {record.title} as secondary")
        
        print(f"\nLinked {linked_count} participants")
    
    # Now let's trigger an update to test the signal
    print("\n" + "="*60)
    print("TESTING DOMAIN UPDATE SIGNAL")
    print("="*60)
    
    # Make a small change to trigger the signal
    current_website = record.data.get('company_website', '')
    new_website = current_website.rstrip('/') + '/'  # Toggle trailing slash
    print(f"Updating company_website from '{current_website}' to '{new_website}'")
    
    record.data['company_website'] = new_website
    record.save()
    print("Save completed - signal should trigger domain-only sync")
    
    # Check sync job creation
    from communications.record_communications.models import RecordSyncJob
    recent_jobs = RecordSyncJob.objects.filter(record=record).order_by('-created_at')[:3]
    
    print("\nRecent sync jobs for this record:")
    for job in recent_jobs:
        print(f"  - {job.created_at}: {job.status} - {job.trigger_reason}")