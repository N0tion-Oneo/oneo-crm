#!/usr/bin/env python
"""Test domain-only sync with detailed logging"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django_tenants.utils import schema_context, get_tenant_model

# Get the oneotalent tenant
Tenant = get_tenant_model()
tenant = Tenant.objects.get(schema_name='oneotalent')
print(f"Using tenant: {tenant.schema_name} ({tenant.name})")

# Use oneotalent tenant context  
with schema_context('oneotalent'):
    from pipelines.models import Record, Pipeline
    from communications.models import Participant
    
    # Get the companies pipeline
    try:
        companies_pipeline = Pipeline.objects.get(slug='companies')
        print(f"Found companies pipeline: {companies_pipeline.name} (ID: {companies_pipeline.id})")
    except Pipeline.DoesNotExist:
        print("Companies pipeline not found, listing available pipelines:")
        for p in Pipeline.objects.all():
            print(f"  - {p.slug}: {p.name} (ID: {p.id})")
        sys.exit(1)
    
    # Get SearchKings Africa record - it should be in companies pipeline
    try:
        record = Record.objects.get(title__icontains='Search Kings', pipeline=companies_pipeline)
        print(f"\nFound record: {record.title} (ID: {record.id})")
        print(f"Current data: {record.data}")
    except Record.DoesNotExist:
        print("\nSearchKings not found, listing companies:")
        for r in Record.objects.filter(pipeline=companies_pipeline)[:10]:
            print(f"  - {r.title} (ID: {r.id})")
        
        # Let's create SearchKings if it doesn't exist
        print("\nCreating Search Kings Africa record...")
        record = Record.objects.create(
            pipeline=companies_pipeline,
            title="Search Kings Africa",
            data={
                'company_name': 'Search Kings Africa',
                'company_website': 'https://searchkingsafrica.com'
            }
        )
        print(f"Created record: {record.title} (ID: {record.id})")
    
    # Now update the domain to trigger sync
    print("\n" + "="*60)
    print("TRIGGERING DOMAIN-ONLY SYNC")
    print("="*60)
    
    # First check existing participants with searchkings domain
    searchkings_participants = Participant.objects.filter(
        email__iendswith='@searchkingsafrica.com'
    )
    print(f"\nParticipants with @searchkingsafrica.com BEFORE linking:")
    for p in searchkings_participants:
        print(f"  - {p.name} ({p.email})")
        print(f"    Primary: {p.contact_record.title if p.contact_record else 'None'}")
        print(f"    Secondary: {p.secondary_record.title if p.secondary_record else 'None'}")
    
    # Make a small change to the domain field to trigger signal
    print(f"\nUpdating company_website from '{record.data.get('company_website')}' to 'https://searchkingsafrica.com/'")
    record.data['company_website'] = 'https://searchkingsafrica.com/'  # Add trailing slash to trigger change
    record.save()
    print("Save completed - signal should have triggered")
    
    # Wait a moment for async processing
    import time
    time.sleep(3)
    
    # Check if participants were linked
    searchkings_participants = Participant.objects.filter(
        email__iendswith='@searchkingsafrica.com'
    )
    print(f"\nParticipants with @searchkingsafrica.com AFTER sync:")
    for p in searchkings_participants:
        print(f"  - {p.name} ({p.email})")
        print(f"    Primary: {p.contact_record.title if p.contact_record else 'None'}")
        print(f"    Secondary: {p.secondary_record.title if p.secondary_record else 'None'}")
    
    # Check specifically for secondary links to our company
    linked_to_company = Participant.objects.filter(secondary_record=record)
    print(f"\nParticipants linked to {record.title} as secondary: {linked_to_company.count()}")