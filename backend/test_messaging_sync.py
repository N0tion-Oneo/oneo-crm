#!/usr/bin/env python
"""
Test WhatsApp and LinkedIn sync for a record
"""
import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from pipelines.models import Record
from communications.models import UserChannelConnection, Channel
from communications.record_communications.services.record_sync_orchestrator import RecordSyncOrchestrator
from django.contrib.auth import get_user_model

User = get_user_model()

# Use oneotalent tenant
tenant = Tenant.objects.get(schema_name='oneotalent')

with schema_context(tenant.schema_name):
    print("🏢 Testing in tenant: oneotalent")
    
    # Get a user
    user = User.objects.filter(is_active=True).first()
    print(f"👤 User: {user.email}")
    
    # Get record 93
    record = Record.objects.get(id=93)
    print(f"\n📄 Testing with Record {record.id}: {record.title}")
    
    # Get record data
    print("\n📊 Record data:")
    for key, value in record.data.items():
        print(f"   {key}: {value}")
    
    # Check connections
    print("\n📡 Available channel connections:")
    connections = UserChannelConnection.objects.filter(user=user)
    for conn in connections:
        print(f"   - {conn.channel_type}: {conn.account_name} (Active: {conn.is_active})")
    
    # Initialize UnipileClient
    from django.conf import settings
    from communications.unipile.core.client import UnipileClient
    
    unipile_client = None
    if hasattr(settings, 'UNIPILE_DSN') and hasattr(settings, 'UNIPILE_API_KEY'):
        unipile_client = UnipileClient(
            dsn=settings.UNIPILE_DSN,
            access_token=settings.UNIPILE_API_KEY
        )
        print("✅ UnipileClient initialized")
    
    # Initialize orchestrator with UnipileClient
    orchestrator = RecordSyncOrchestrator(unipile_client=unipile_client)
    
    # Test WhatsApp sync
    print("\n" + "="*60)
    print("📱 TESTING WHATSAPP SYNC")
    print("="*60)
    
    whatsapp_conn = connections.filter(channel_type='whatsapp').first()
    if whatsapp_conn:
        print(f"Using connection: {whatsapp_conn.account_name}")
        
        # Prepare identifiers for WhatsApp (phone numbers)
        identifiers = {
            'phone': [],
            'whatsapp': []
        }
        
        # Check for phone in record data
        if 'phone' in record.data and record.data['phone']:
            identifiers['phone'].append(record.data['phone'])
            identifiers['whatsapp'].append(record.data['phone'])
        if 'mobile' in record.data and record.data['mobile']:
            identifiers['phone'].append(record.data['mobile'])
            identifiers['whatsapp'].append(record.data['mobile'])
        if 'whatsapp' in record.data and record.data['whatsapp']:
            identifiers['whatsapp'].append(record.data['whatsapp'])
        if 'phone_number' in record.data and record.data['phone_number']:
            identifiers['phone'].append(record.data['phone_number'])
            identifiers['whatsapp'].append(record.data['phone_number'])
            
        # If no phone found, add a test number for demonstration
        if not identifiers['phone']:
            print("   ⚠️ No phone number in record data - WhatsApp sync will return 0 results")
            
        print(f"Identifiers: {identifiers}")
        
        try:
            # Sync WhatsApp
            result = orchestrator.sync_record(
                record_id=record.id,
                triggered_by=user,
                trigger_reason="Manual WhatsApp test",
                channels_to_sync=['whatsapp']
            )
            
            print(f"\n✅ WhatsApp sync result: {result}")
            
            # Check what was synced
            from communications.models import Conversation, Participant
            whatsapp_conversations = Conversation.objects.filter(
                channel__channel_type='whatsapp'
            ).order_by('-updated_at')[:5]
            
            print(f"\n📋 Latest WhatsApp conversations:")
            for conv in whatsapp_conversations:
                participants = Participant.objects.filter(
                    conversation_memberships__conversation=conv
                )
                linked_participants = participants.filter(contact_record__isnull=False)
                print(f"   - {conv.subject[:50]}...")
                print(f"     Participants: {participants.count()} (Linked: {linked_participants.count()})")
                if linked_participants:
                    for p in linked_participants:
                        print(f"     ✅ Linked: {p.name} -> Record {p.contact_record_id}")
                        
        except Exception as e:
            print(f"❌ WhatsApp sync error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ No WhatsApp connection found")
    
    # Test LinkedIn sync
    print("\n" + "="*60)
    print("💼 TESTING LINKEDIN SYNC")
    print("="*60)
    
    linkedin_conn = connections.filter(channel_type='linkedin').first()
    if linkedin_conn:
        print(f"Using connection: {linkedin_conn.account_name}")
        
        # Prepare identifiers for LinkedIn
        identifiers = {
            'linkedin': []
        }
        
        # Check for LinkedIn in record data
        if 'linkedin' in record.data:
            linkedin_value = record.data['linkedin']
            # Extract username from URL if it's a URL
            if 'linkedin.com' in linkedin_value:
                if '/in/' in linkedin_value:
                    username = linkedin_value.split('/in/')[-1].strip('/')
                    identifiers['linkedin'].append(username)
                    print(f"   Extracted LinkedIn username: {username}")
            else:
                identifiers['linkedin'].append(linkedin_value)
        if 'linkedin_url' in record.data:
            # Extract username from URL
            url = record.data['linkedin_url']
            if '/in/' in url:
                username = url.split('/in/')[-1].strip('/')
                identifiers['linkedin'].append(username)
                
        print(f"Identifiers: {identifiers}")
        
        try:
            # Sync LinkedIn
            result = orchestrator.sync_record(
                record_id=record.id,
                triggered_by=user,
                trigger_reason="Manual LinkedIn test",
                channels_to_sync=['linkedin']
            )
            
            print(f"\n✅ LinkedIn sync result: {result}")
            
            # Check what was synced
            linkedin_conversations = Conversation.objects.filter(
                channel__channel_type='linkedin'
            ).order_by('-updated_at')[:5]
            
            print(f"\n📋 Latest LinkedIn conversations:")
            for conv in linkedin_conversations:
                participants = Participant.objects.filter(
                    conversation_memberships__conversation=conv
                )
                linked_participants = participants.filter(contact_record__isnull=False)
                print(f"   - {conv.subject[:50]}...")
                print(f"     Participants: {participants.count()} (Linked: {linked_participants.count()})")
                if linked_participants:
                    for p in linked_participants:
                        print(f"     ✅ Linked: {p.name} -> Record {p.contact_record_id}")
                        
        except Exception as e:
            print(f"❌ LinkedIn sync error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ No LinkedIn connection found")
    
    print("\n" + "="*60)
    print("📊 SYNC TEST COMPLETE")
    print("="*60)