#!/usr/bin/env python
"""
Test secondary record functionality - company matching via domain
"""
import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.record_communications.services import RecordIdentifierExtractor
from pipelines.models import Record

print("=" * 80)
print("TESTING SECONDARY RECORD FUNCTIONALITY")
print("=" * 80)

# Get tenant
tenant = Tenant.objects.get(schema_name='oneotalent')

with schema_context(tenant.schema_name):
    extractor = RecordIdentifierExtractor()
    
    # Test 1: Check if domain search works
    print("\n1. Testing domain search for companies:")
    print("-" * 40)
    
    test_domains = ['oneodigital.com', 'nethunt.com', 'acme.com']
    
    for domain in test_domains:
        print(f"\nSearching for companies with domain: {domain}")
        company_records = extractor.find_company_records_by_domain(domain)
        
        if company_records:
            print(f"✅ Found {len(company_records)} company record(s):")
            for record in company_records:
                print(f"   - Company #{record.id}: {record.data.get('company_name', 'Unknown')}")
        else:
            print(f"❌ No companies found for domain {domain}")
    
    # Test 2: Simulate webhook participant resolution
    print("\n2. Testing webhook participant resolution with company matching:")
    print("-" * 40)
    
    from communications.webhooks.email_handler import EmailWebhookHandler
    from communications.models import UserChannelConnection
    
    connection = UserChannelConnection.objects.filter(
        channel_type__in=['gmail', 'email'],
        is_active=True
    ).first()
    
    if connection:
        handler = EmailWebhookHandler()
        
        # Test with an email from Saul at Oneo Digital
        test_email_data = {
            'sender_info': {'email': 'saul@oneodigital.com', 'name': 'Saul Chilchik'},
            'recipients': {
                'to': [{'email': 'client@example.com', 'name': 'Client'}],
                'cc': [],
                'bcc': []
            },
            'direction': 'outbound'
        }
        
        try:
            should_store, participants = handler._check_participant_resolution(
                test_email_data, connection
            )
            
            print(f"\nTest with saul@oneodigital.com:")
            print(f"  Should store: {should_store}")
            print(f"  Participants: {len(participants)}")
            
            for p in participants:
                if p.email == 'saul@oneodigital.com':
                    print(f"\n  Saul's participant:")
                    print(f"    Email: {p.email}")
                    if p.contact_record:
                        print(f"    ✅ Primary record (contact): #{p.contact_record.id}")
                    else:
                        print(f"    ❌ No primary record")
                    
                    if p.secondary_record:
                        print(f"    ✅ Secondary record (company): #{p.secondary_record.id} - {p.secondary_record.data.get('company_name', 'Unknown')}")
                        print(f"       Pipeline: {p.secondary_pipeline}")
                        print(f"       Method: {p.secondary_resolution_method}")
                    else:
                        print(f"    ❌ No secondary record")
                        
        except Exception as e:
            print(f"❌ Error testing participant resolution: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ No email connection found")
    
    # Test 3: Check if RecordCommunicationLinks would be created
    print("\n3. Checking RecordCommunicationLink creation:")
    print("-" * 40)
    
    from communications.record_communications.models import RecordCommunicationLink
    
    # Check if Oneo Digital company has any communication links
    oneo_company = Record.objects.filter(
        pipeline__slug='companies',
        data__company_name='Oneo Digital'
    ).first()
    
    if oneo_company:
        links = RecordCommunicationLink.objects.filter(record=oneo_company)
        print(f"\nOneo Digital (Company #{oneo_company.id}):")
        print(f"  Has {links.count()} communication links")
        
        if links.exists():
            print("  Recent links:")
            for link in links[:5]:
                print(f"    - Conversation: {link.conversation.subject}")
                print(f"      Match type: {link.match_type}")
                print(f"      Created: {link.created_at}")
    else:
        print("❌ Oneo Digital company record not found")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)