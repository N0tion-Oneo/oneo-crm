#!/usr/bin/env python
"""
Direct test of record-level sync for Saul Chilchik (without Celery)
"""
import os
import sys
import django
import asyncio
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection
from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Record
from communications.models import UserChannelConnection, Conversation, Message
from communications.record_communications.services.record_sync_manager import RecordSyncManager
from communications.record_communications.models import (
    RecordCommunicationProfile,
    RecordAttendeeMapping,
    RecordCommunicationLink,
    RecordSyncJob
)
from tenants.models import Tenant
from django.contrib.auth import get_user_model

User = get_user_model()


async def test_sync():
    """Test sync directly using async methods"""
    print("\n🚀 Direct Test of Record-Level Sync")
    print("=" * 60)
    
    # Get oneotalent tenant
    tenant = await Tenant.objects.aget(schema_name='oneotalent')
    print(f"✅ Tenant: {tenant.name}")
    
    # We need to use sync context for schema switching
    from django.db import connection
    from asgiref.sync import sync_to_async
    
    def get_record_sync():
        with schema_context(tenant.schema_name):
            return Record.objects.select_related('pipeline').get(id=66)
    
    # Get Saul's record in sync context
    record = await sync_to_async(get_record_sync)()
    print(f"✅ Record: Saul Chilchik (ID: {record.id})")
    print(f"   Pipeline: {record.pipeline.name}")
    
    # Initialize sync manager
    sync_manager = RecordSyncManager()
    
    # Extract identifiers
    from communications.record_communications.services.identifier_extractor import RecordIdentifierExtractor
    extractor = RecordIdentifierExtractor()
    identifiers = extractor.extract_identifiers_from_record(record)
    
    print("\n🔑 Extracted Identifiers:")
    for key, values in identifiers.items():
        if values:
            print(f"   {key}: {values}")
    
    # Build provider IDs
    print("\n🆔 Provider IDs by Channel:")
    for channel in ['whatsapp', 'linkedin', 'instagram']:
        provider_ids = sync_manager._build_provider_ids(identifiers, channel)
        if provider_ids:
            print(f"   {channel}: {provider_ids}")
    
    # Get active user for triggering
    user = await User.objects.filter(is_active=True).afirst()
    
    print("\n🔄 Starting Direct Sync...")
    print("-" * 40)
    
    try:
        # Run the sync directly
        sync_job = await sync_manager.sync_record_communications(
            record_id=record.id,
            triggered_by=user,
            trigger_reason='Direct test sync for Saul Chilchik'
        )
        
        print(f"\n✅ Sync Completed!")
        print(f"   Job ID: {sync_job.id}")
        print(f"   Status: {sync_job.status}")
        print(f"   Conversations found: {sync_job.conversations_found}")
        print(f"   Messages found: {sync_job.messages_found}")
        print(f"   New links created: {sync_job.new_links_created}")
        
        # Check results
        print("\n📊 Checking Results...")
        print("-" * 40)
        
        # Check attendee mappings
        mappings = RecordAttendeeMapping.objects.filter(record=record)
        mapping_count = await mappings.acount()
        print(f"\n🗺️  Attendee Mappings: {mapping_count}")
        
        async for mapping in mappings[:5]:
            print(f"   {mapping.channel_type}: {mapping.provider_id} -> {mapping.attendee_name or 'Unknown'}")
        
        # Check communication links
        links = RecordCommunicationLink.objects.filter(record=record)
        link_count = await links.acount()
        print(f"\n🔗 Communication Links: {link_count}")
        
        async for link in links[:5]:
            conv = await Conversation.objects.aget(id=link.conversation_id)
            print(f"   {conv.subject or 'No subject'}: {link.match_type} ({link.match_identifier})")
        
        # Check conversations
        if link_count > 0:
            conversation_ids = await links.values_list('conversation_id', flat=True).adistinct()
            conversations = Conversation.objects.filter(id__in=conversation_ids)
            conv_count = await conversations.acount()
            
            print(f"\n💬 Conversations: {conv_count}")
            async for conv in conversations[:5]:
                print(f"   {conv.subject or 'No subject'} ({conv.message_count} messages)")
                
                # Show first message
                first_message = await Message.objects.filter(conversation=conv).order_by('created_at').afirst()
                if first_message:
                    content_preview = first_message.content[:100] if first_message.content else 'No content'
                    print(f"      First message: {content_preview}...")
        
    except Exception as e:
        print(f"\n❌ Sync failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function"""
    print("\n🚀 Direct Record-Level Sync Test (No Celery)")
    print("=" * 70)
    
    # Run async test
    asyncio.run(test_sync())
    
    print("\n" + "=" * 70)
    print("✅ Test completed!")


if __name__ == '__main__':
    main()