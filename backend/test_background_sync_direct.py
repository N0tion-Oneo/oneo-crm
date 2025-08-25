#!/usr/bin/env python
"""
Test the background sync directly via Celery
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from django.contrib.auth import get_user_model
from communications.models import UserChannelConnection, Channel, Conversation, Message, ChatAttendee
from communications.channels.whatsapp.background_sync import sync_account_comprehensive_background

User = get_user_model()

def test_background_sync():
    """Test the background sync via Celery"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print("\n🚀 TESTING BACKGROUND SYNC VIA CELERY")
        print("=" * 60)
        
        # Get a user
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ No active user found")
            return
            
        print(f"✅ User: {user.username}")
        
        # Get WhatsApp connections
        connection = UserChannelConnection.objects.filter(
            user=user,
            channel_type='whatsapp',
            is_active=True,
            unipile_account_id__isnull=False
        ).first()
        
        if not connection:
            print("❌ No active WhatsApp connections found")
            return
            
        print(f"\n📊 Using connection: {connection.account_name}")
        
        # Clear existing data for a fresh test
        print("\n🧹 Clearing existing data for fresh sync...")
        Message.objects.all().delete()
        Conversation.objects.all().delete()
        ChatAttendee.objects.all().delete()
        print("   ✅ Data cleared")
        
        # Get or create channel
        channel, created = Channel.objects.get_or_create(
            unipile_account_id=connection.unipile_account_id,
            channel_type='whatsapp',
            defaults={
                'name': f"WhatsApp Account {connection.account_name}",
                'auth_status': 'authenticated',
                'is_active': True,
                'created_by': user
            }
        )
        
        print(f"   Channel: {channel.name} (created: {created})")
        
        # Trigger background sync
        print(f"\n📱 Triggering background sync via Celery...")
        
        sync_options = {
            'days_back': 30,
            'max_messages_per_chat': 50,  # Limit for testing
        }
        
        # Queue the task
        result = sync_account_comprehensive_background.delay(
            channel_id=str(channel.id),
            user_id=str(user.id),
            sync_options=sync_options,
            tenant_schema=tenant.schema_name
        )
        
        print(f"   ✅ Task queued with ID: {result.id}")
        print(f"   Waiting for task to complete...")
        
        # Wait for task to complete (with timeout)
        import time
        max_wait = 60  # 60 seconds timeout
        start_time = time.time()
        
        while not result.ready() and (time.time() - start_time) < max_wait:
            time.sleep(2)
            print(f"   ⏳ Status: {result.state}")
        
        if result.successful():
            task_result = result.result
            print(f"\n   ✅ TASK COMPLETED SUCCESSFULLY:")
            print(f"      Success: {task_result.get('success')}")
            print(f"      Conversations synced: {task_result.get('conversations_synced', 0)}")
            print(f"      Messages synced: {task_result.get('messages_synced', 0)}")
            
            if task_result.get('sync_job_id'):
                print(f"      Sync job ID: {task_result.get('sync_job_id')}")
        elif result.failed():
            print(f"\n   ❌ Task failed: {result.info}")
        else:
            print(f"\n   ⏱️ Task timed out (state: {result.state})")
        
        # Verify results in database
        print("\n" + "=" * 60)
        print("📊 DATABASE VERIFICATION")
        print("=" * 60)
        
        conversations = Conversation.objects.all()
        messages = Message.objects.all()
        attendees = ChatAttendee.objects.all()
        
        print(f"\n📱 Conversations: {conversations.count()}")
        for conv in conversations[:3]:
            print(f"   - {conv.subject or 'No subject'} (Messages: {conv.messages.count()})")
        
        print(f"\n👥 Attendees: {attendees.count()}")
        account_owners = attendees.filter(is_self=True)
        print(f"   Account owners (is_self=True): {account_owners.count()}")
        
        print(f"\n📨 Messages: {messages.count()}")
        in_messages = messages.filter(direction='inbound').count()
        out_messages = messages.filter(direction='outbound').count()
        print(f"   Inbound: {in_messages}")
        print(f"   Outbound: {out_messages}")
        
        if messages.count() == 0:
            print(f"\n   ❌ ISSUE: No messages synced via background task!")
        
        print("\n" + "=" * 60)
        print("✅ BACKGROUND SYNC TEST COMPLETE!")
        print("=" * 60)

if __name__ == "__main__":
    test_background_sync()