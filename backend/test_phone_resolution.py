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

async def test_phone_resolution():
    # Get tenant
    tenant = await sync_to_async(Tenant.objects.get)(schema_name='oneotalent')
    
    # Initialize resolution service
    resolution_service = ParticipantResolutionService(tenant)
    
    # Test with a phone number from the WhatsApp chats
    test_phones = ['27782270354', '27815116582', '27827736571']
    
    print("Testing phone number resolution:")
    print("=" * 50)
    
    for phone in test_phones:
        print(f"\nPhone: {phone}")
        
        # Try the actual resolve_or_create_participant method
        identifier_data = {
            'phone': phone,
            'name': f'WhatsApp User {phone}'
        }
        
        try:
            participant, created = await resolution_service.resolve_or_create_participant(
                identifier_data=identifier_data,
                channel_type='whatsapp'
            )
            
            print(f"  Participant: {participant.name}")
            print(f"  Has Contact: {participant.contact_record_id is not None}")
            if participant.contact_record_id:
                print(f"  Contact ID: {participant.contact_record_id}")
                print(f"  Contact Name: {participant.contact_name}")
                
        except Exception as e:
            print(f"  Error: {e}")

# Run the async function
asyncio.run(test_phone_resolution())