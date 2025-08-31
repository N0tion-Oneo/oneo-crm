#!/usr/bin/env python
"""
Test bulk sync performance for record communications
"""
import os
import sys
import django
import time
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection
from django_tenants.utils import schema_context
from pipelines.models import Record
from communications.record_communications.services.record_sync_orchestrator import RecordSyncOrchestrator
from communications.unipile.core.client import UnipileClient

def test_bulk_sync():
    """Test bulk sync performance"""
    
    # Initialize client and orchestrator
    from django.conf import settings
    unipile_client = UnipileClient(
        dsn=settings.UNIPILE_DSN,
        access_token=settings.UNIPILE_ACCESS_TOKEN
    )
    orchestrator = RecordSyncOrchestrator(unipile_client)
    
    # Find Saul's record in demo tenant
    with schema_context('demo'):
        try:
            # Find record by name
            record = Record.objects.filter(
                field_values__name__icontains='Saul'
            ).first()
            
            if not record:
                print("❌ Could not find Saul's record")
                return
            
            print(f"✅ Found record: {record.id} - {record.field_values.get('name', 'Unknown')}")
            
            # Clear existing data for clean test
            from communications.models import Message, Conversation
            from communications.record_communications.models import RecordCommunicationLink
            
            # Get existing counts
            existing_messages = Message.objects.count()
            existing_conversations = Conversation.objects.count()
            existing_links = RecordCommunicationLink.objects.filter(record=record).count()
            
            print(f"\n📊 Existing data:")
            print(f"  - Messages: {existing_messages}")
            print(f"  - Conversations: {existing_conversations}")
            print(f"  - Links for this record: {existing_links}")
            
            # Clear data for this record
            links = RecordCommunicationLink.objects.filter(record=record)
            conversation_ids = links.values_list('conversation_id', flat=True)
            Message.objects.filter(conversation_id__in=conversation_ids).delete()
            Conversation.objects.filter(id__in=conversation_ids).delete()
            links.delete()
            
            print("\n🧹 Cleared existing data for this record")
            
            # Run sync with timing
            print("\n🚀 Starting bulk sync...")
            start_time = time.time()
            
            result = orchestrator.sync_record(
                record_id=record.id,
                triggered_by=None,
                trigger_reason='Bulk sync performance test'
            )
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            if result['success']:
                total_messages = result['total_messages']
                total_conversations = result['total_conversations']
                
                print(f"\n✅ Sync completed successfully!")
                print(f"\n📊 Results:")
                print(f"  - Total conversations: {total_conversations}")
                print(f"  - Total messages: {total_messages}")
                print(f"  - Time taken: {elapsed_time:.2f} seconds")
                
                if total_messages > 0:
                    messages_per_second = total_messages / elapsed_time
                    print(f"  - Performance: {messages_per_second:.1f} messages/second")
                
                # Channel breakdown
                print(f"\n📱 Channel breakdown:")
                for channel, stats in result.get('channel_results', {}).items():
                    print(f"  - {channel}: {stats.get('conversations', 0)} conversations, {stats.get('messages', 0)} messages")
                
                # Verify data in database
                new_messages = Message.objects.count()
                new_conversations = Conversation.objects.count()
                new_links = RecordCommunicationLink.objects.filter(record=record).count()
                
                print(f"\n✅ Database verification:")
                print(f"  - Total messages in DB: {new_messages}")
                print(f"  - Total conversations in DB: {new_conversations}")
                print(f"  - Links for this record: {new_links}")
                
            else:
                print(f"\n❌ Sync failed: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_bulk_sync()