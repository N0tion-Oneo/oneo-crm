#!/usr/bin/env python
import os
import sys
import django
import asyncio

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')
django.setup()

from django_tenants.utils import schema_context
from communications.services.participant_resolution import ParticipantResolutionService
from tenants.models import Tenant
from asgiref.sync import sync_to_async
from pipelines.models import Record, Pipeline

async def test_resolution():
    # Get tenant
    tenant = await sync_to_async(Tenant.objects.get)(schema_name='oneotalent')
    
    # Initialize resolution service
    resolution_service = ParticipantResolutionService(tenant)
    
    # Test phone numbers
    test_phones = [
        '27782270354',      # Without +
        '+27782270354',     # With +
    ]
    
    print("Testing participant resolution:")
    print("=" * 50)
    
    # First check what contact exists
    def check_contact():
        with schema_context('oneotalent'):
            contacts_pipeline = Pipeline.objects.filter(slug='contacts').first()
            if contacts_pipeline:
                existing_contact = Record.objects.filter(
                    pipeline=contacts_pipeline,
                    data__phone_number__icontains='27782270354'
                ).first()
                if existing_contact:
                    return existing_contact
        return None
    
    existing_contact = await sync_to_async(check_contact)()
    if existing_contact:
        print(f"Found contact in DB:")
        print(f"  ID: {existing_contact.id}")
        print(f"  Name: {existing_contact.data.get('first_name', 'N/A')}")
        print(f"  Phone: {existing_contact.data.get('phone_number', 'N/A')}")
        print()
    
    for phone in test_phones:
        print(f"\nTesting phone: {phone}")
        
        # Create identifier data
        identifier_data = {
            'phone': phone,
            'name': f'WhatsApp User'
        }
        
        try:
            # Resolve or create participant
            participant, created = await resolution_service.resolve_or_create_participant(
                identifier_data=identifier_data,
                channel_type='whatsapp'
            )
            
            print(f"  Participant created: {created}")
            print(f"  Participant ID: {participant.id}")
            print(f"  Participant name: {participant.name}")
            print(f"  Participant phone: {participant.phone}")
            print(f"  Has contact: {participant.contact_record_id is not None}")
            
            if participant.contact_record_id:
                print(f"  ✅ Contact ID: {participant.contact_record_id}")
                print(f"  Contact name: {participant.contact_name}")
                print(f"  Resolution confidence: {participant.resolution_confidence}")
            else:
                print(f"  ❌ No contact resolved")
                
        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()

# Run the async function
asyncio.run(test_resolution())