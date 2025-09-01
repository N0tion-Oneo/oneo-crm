#!/usr/bin/env python
"""
Test that the email webhook now correctly:
1. Searches for records by email
2. Stores messages when records are found
3. Creates RecordCommunicationLinks for timeline visibility
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
from communications.models import Message, Conversation, Participant
from communications.record_communications.models import RecordCommunicationLink
from communications.record_communications.services import RecordIdentifierExtractor
from pipelines.models import Record
from django.db.models import Q

print("=" * 80)
print("TESTING EMAIL WEBHOOK FIX")
print("=" * 80)

# Get tenant
tenant = Tenant.objects.get(schema_name='oneotalent')

with schema_context(tenant.schema_name):
    # Test 1: Check if RecordIdentifierExtractor can find Saul's record by email
    print("\n1. Testing RecordIdentifierExtractor:")
    print("-" * 40)
    
    identifier_extractor = RecordIdentifierExtractor()
    
    # Saul's emails from earlier investigation
    test_emails = ['saul@oneodigital.com']
    
    for email in test_emails:
        identifiers = {'email': [email]}
        matching_records = identifier_extractor.find_records_by_identifiers(identifiers)
        
        if matching_records:
            print(f"✅ Found {len(matching_records)} record(s) for {email}:")
            for record in matching_records:
                print(f"   - Record #{record.id}: {record.data}")
        else:
            print(f"❌ No records found for {email}")
    
    # Test 2: Check recent messages and their RecordCommunicationLinks
    print("\n2. Checking Recent Messages and Links:")
    print("-" * 40)
    
    # Get messages from today
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    recent_messages = Message.objects.filter(
        created_at__gte=today
    ).select_related('conversation').order_by('-created_at')[:5]
    
    print(f"Found {recent_messages.count()} recent messages today")
    
    for msg in recent_messages:
        print(f"\n📧 Message: {msg.id}")
        print(f"   Created: {msg.created_at}")
        print(f"   Direction: {msg.direction}")
        print(f"   Conversation: {msg.conversation.id}")
        
        # Check for RecordCommunicationLinks
        links = RecordCommunicationLink.objects.filter(
            conversation=msg.conversation
        ).select_related('record')
        
        if links:
            print(f"   ✅ Has {links.count()} RecordCommunicationLink(s):")
            for link in links:
                print(f"      - Record #{link.record.id}: {link.match_type} ({link.match_identifier})")
        else:
            print(f"   ❌ No RecordCommunicationLinks")
    
    # Test 3: Check Saul's record specifically
    print("\n3. Checking Saul's Record (#66):")
    print("-" * 40)
    
    try:
        saul_record = Record.objects.get(id=66)
        print(f"✅ Found Saul's record")
        
        # Check his communication links
        saul_links = RecordCommunicationLink.objects.filter(
            record=saul_record
        ).select_related('conversation').order_by('-created_at')[:5]
        
        print(f"   Has {saul_links.count()} total communication links")
        
        # Check recent ones
        recent_links = saul_links.filter(created_at__gte=today)
        if recent_links:
            print(f"   ✅ {recent_links.count()} links created today:")
            for link in recent_links:
                print(f"      - Conversation: {link.conversation.subject}")
                print(f"        Created: {link.created_at}")
                print(f"        By sync: {link.created_by_sync}")
        else:
            print(f"   ⚠️ No links created today")
            
    except Record.DoesNotExist:
        print(f"❌ Saul's record #66 not found")
    
    # Test 4: Simulate webhook behavior
    print("\n4. Simulating Webhook Participant Resolution:")
    print("-" * 40)
    
    from communications.webhooks.email_handler import EmailWebhookHandler
    from communications.models import UserChannelConnection
    
    # Get a connection for testing
    connection = UserChannelConnection.objects.filter(
        channel_type__in=['gmail', 'email'],
        is_active=True
    ).first()
    
    if connection:
        handler = EmailWebhookHandler()
        
        # Test 1: Saul as sender (outbound email)
        test_email_data = {
            'sender_info': {'email': 'saul@oneodigital.com', 'name': 'Saul Chilchik'},
            'recipients': {
                'to': [{'email': 'test@example.com', 'name': 'Test User'}],
                'cc': [],
                'bcc': []
            },
            'direction': 'outbound'
        }
        
        try:
            should_store, participants = handler._check_participant_resolution(
                test_email_data, connection
            )
            
            print(f"Test 1 - Saul as sender:")
            print(f"  Should store: {should_store}")
            print(f"  Participants found: {len(participants)}")
            
            for p in participants:
                if p.email == 'saul@oneodigital.com':
                    if p.contact_record:
                        print(f"  ✅ Saul's participant linked to record #{p.contact_record.id}")
                    else:
                        print(f"  ⚠️ Saul's participant not linked to any record")
                        
        except Exception as e:
            print(f"❌ Error testing participant resolution: {e}")
            
        # Test 2: Saul as recipient (inbound email)
        test_email_data2 = {
            'sender_info': {'email': 'test@example.com', 'name': 'Test User'},
            'recipients': {
                'to': [{'email': 'saul@oneodigital.com', 'name': 'Saul Chilchik'}],
                'cc': [],
                'bcc': []
            },
            'direction': 'inbound'
        }
        
        try:
            should_store2, participants2 = handler._check_participant_resolution(
                test_email_data2, connection
            )
            
            print(f"\nTest 2 - Saul as recipient:")
            print(f"  Should store: {should_store2}")
            print(f"  Participants found: {len(participants2)}")
            
            for p in participants2:
                if p.email == 'saul@oneodigital.com':
                    if p.contact_record:
                        print(f"  ✅ Saul's participant linked to record #{p.contact_record.id}")
                    else:
                        print(f"  ⚠️ Saul's participant not linked to any record")
                        
        except Exception as e:
            print(f"❌ Error testing participant resolution: {e}")
    else:
        print("❌ No email connection found for testing")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)