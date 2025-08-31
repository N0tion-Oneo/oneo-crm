#!/usr/bin/env python
"""
Simple test to verify provider ID construction and API setup
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Record
from communications.models import UserChannelConnection
from communications.record_communications.services.record_sync_manager import RecordSyncManager
from communications.record_communications.services.identifier_extractor import RecordIdentifierExtractor
from tenants.models import Tenant

# Get oneotalent tenant
tenant = Tenant.objects.get(schema_name='oneotalent')

with schema_context(tenant.schema_name):
    print("\n🔍 Testing Record-Level Sync Components")
    print("=" * 60)
    
    # Get Saul's record
    record = Record.objects.select_related('pipeline').get(id=66)
    print(f"✅ Record: Saul Chilchik")
    print(f"   Pipeline: {record.pipeline.name}")
    
    # Extract identifiers
    extractor = RecordIdentifierExtractor()
    identifiers = extractor.extract_identifiers_from_record(record)
    
    print("\n📧 Extracted Identifiers:")
    for key, values in identifiers.items():
        if values:
            print(f"   {key}: {values}")
    
    # Build provider IDs
    sync_manager = RecordSyncManager()
    
    print("\n🆔 Provider IDs for API Calls:")
    for channel in ['whatsapp', 'linkedin', 'instagram', 'telegram']:
        provider_ids = sync_manager._build_provider_ids(identifiers, channel)
        if provider_ids:
            print(f"\n   {channel.upper()}:")
            for pid in provider_ids:
                print(f"      - {pid}")
    
    # Check channel connections
    connections = UserChannelConnection.objects.filter(account_status='active')
    
    print("\n📡 Active Channel Connections:")
    for conn in connections:
        print(f"   - {conn.channel_type}: {conn.account_name}")
        print(f"     UniPile ID: {conn.unipile_account_id[:30]}...")
    
    print("\n✅ Components Ready for Sync!")
    print("\nNext steps would be:")
    print("1. For each channel connection:")
    print("   a. Use provider IDs as attendee_id in /api/v1/chats call")
    print("   b. For each chat found, get messages using chat_id")
    print("   c. Store attendee mappings and link conversations to record")
    
    # Show example API calls
    print("\n📝 Example API Calls:")
    
    linkedin_conn = connections.filter(channel_type='linkedin').first()
    if linkedin_conn and 'chilchik' in str(provider_ids):
        print(f"\nLinkedIn:")
        print(f"  GET /api/v1/chats")
        print(f"    account_id: {linkedin_conn.unipile_account_id}")
        print(f"    attendee_id: chilchik")
        print(f"  → Returns chats with Saul")
        print(f"  GET /api/v1/messages")
        print(f"    account_id: {linkedin_conn.unipile_account_id}")
        print(f"    chat_id: <chat_id_from_previous_call>")
        print(f"  → Returns messages in that chat")
    
    whatsapp_conn = connections.filter(channel_type='whatsapp').first()
    if whatsapp_conn and identifiers.get('phone'):
        print(f"\nWhatsApp:")
        print(f"  GET /api/v1/chats")
        print(f"    account_id: {whatsapp_conn.unipile_account_id}")
        print(f"    attendee_id: 27782270354@s.whatsapp.net")
        print(f"  → Returns WhatsApp chats with this number")
    
    gmail_conn = connections.filter(channel_type='gmail').first()
    if gmail_conn and identifiers.get('email'):
        print(f"\nGmail (Email uses different approach):")
        print(f"  GET /api/v1/emails")
        print(f"    account_id: {gmail_conn.unipile_account_id}")
        print(f"    participants: saul@oneodigital.com")
        print(f"  → Returns emails to/from Saul")
    
    print("\n" + "=" * 60)