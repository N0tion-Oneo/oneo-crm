#!/usr/bin/env python
import os
import sys
import django
import asyncio
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')
django.setup()

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

from django_tenants.utils import schema_context
from communications.services.participant_resolution import ParticipantResolutionService
from communications.resolution_gateway_v3 import ContactResolutionGatewayV3
from tenants.models import Tenant
from asgiref.sync import sync_to_async
from pipelines.models import Record, Pipeline

async def test_gateway_directly():
    # Get tenant
    tenant = await sync_to_async(Tenant.objects.get)(schema_name='oneotalent')
    
    print("Testing resolution gateway directly:")
    print("=" * 50)
    
    # Initialize gateway directly
    gateway = ContactResolutionGatewayV3(tenant)
    
    # Test with phone identifier
    identifiers = {'phone': '+27782270354'}
    
    print(f"\nCalling gateway.resolve_contacts with: {identifiers}")
    
    try:
        resolution = await gateway.resolve_contacts(
            identifiers,
            min_confidence=0.5
        )
        
        print(f"\nGateway response:")
        print(f"  Total matches: {resolution.get('total_matches', 0)}")
        print(f"  Pipelines checked: {resolution.get('pipelines_checked', [])}")
        print(f"  Pipelines skipped: {resolution.get('pipelines_skipped', [])}")
        
        if resolution.get('matches'):
            for match in resolution['matches']:
                print(f"\n  Match found:")
                print(f"    Record ID: {match['record'].id if 'record' in match else 'N/A'}")
                print(f"    Pipeline: {match.get('pipeline', 'N/A')}")
                print(f"    Confidence: {match.get('confidence', 0)}")
                print(f"    Match details: {match.get('match_details', {})}")
        else:
            print("  ❌ No matches found")
            
    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()

# Run the async function
asyncio.run(test_gateway_directly())