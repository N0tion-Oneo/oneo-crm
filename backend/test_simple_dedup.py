#!/usr/bin/env python
"""
Simple test to verify email deduplication is working
"""
import os
import sys
import django
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Message, Conversation

def test_simple_dedup():
    """Check if deduplication is working"""
    
    print("=" * 60)
    print("Testing Email Deduplication Status")
    print("=" * 60)
    
    # Get tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    print(f"✅ Tenant: {tenant.name}")
    
    with schema_context(tenant.schema_name):
        # Get recent conversations
        recent_conversations = Conversation.objects.filter(
            created_at__date=datetime.now().date()
        ).order_by('-created_at')[:5]
        
        print(f"\n📧 Recent conversations today: {recent_conversations.count()}")
        
        for conv in recent_conversations:
            print(f"\n📬 Conversation: {conv.id}")
            print(f"   Subject: {conv.subject}")
            print(f"   Thread ID: {conv.external_thread_id}")
            print(f"   Created: {conv.created_at.strftime('%H:%M:%S')}")
            
            # Get messages in this conversation
            messages = Message.objects.filter(conversation=conv).order_by('created_at')
            print(f"   Messages: {messages.count()}")
            
            # Check for duplicates
            tracking_ids = []
            duplicates_found = False
            
            for msg in messages:
                print(f"\n     Message {msg.id}:")
                print(f"       Direction: {msg.direction}")
                print(f"       Subject: {msg.subject}")
                print(f"       External ID: {msg.external_message_id[:30]}..." if len(msg.external_message_id or '') > 30 else f"       External ID: {msg.external_message_id}")
                
                tracking_id = msg.metadata.get('tracking_id') if msg.metadata else None
                webhook_processed = msg.metadata.get('webhook_processed', False) if msg.metadata else False
                
                print(f"       Tracking ID: {tracking_id}")
                print(f"       Webhook Processed: {webhook_processed}")
                
                # Check for duplicate tracking IDs
                if tracking_id:
                    if tracking_id in tracking_ids:
                        print(f"       ⚠️ DUPLICATE TRACKING ID FOUND!")
                        duplicates_found = True
                    else:
                        tracking_ids.append(tracking_id)
            
            if duplicates_found:
                print(f"\n   ❌ DUPLICATES DETECTED in conversation")
            else:
                print(f"\n   ✅ NO DUPLICATES - Deduplication working!")
        
        # Check overall deduplication status
        print("\n" + "=" * 60)
        print("DEDUPLICATION STATUS SUMMARY")
        print("=" * 60)
        
        # Find messages with tracking_id
        messages_with_tracking = Message.objects.filter(
            metadata__tracking_id__isnull=False,
            created_at__date=datetime.now().date()
        )
        
        # Count webhook processed messages
        webhook_processed = messages_with_tracking.filter(
            metadata__webhook_processed=True
        ).count()
        
        print(f"📊 Messages with tracking_id today: {messages_with_tracking.count()}")
        print(f"📊 Messages with webhook processed: {webhook_processed}")
        
        # Check for any duplicates by tracking_id
        from django.db.models import Count
        duplicates = messages_with_tracking.values('metadata__tracking_id').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        if duplicates.exists():
            print(f"\n❌ FOUND {duplicates.count()} duplicate tracking IDs!")
            for dup in duplicates[:5]:
                print(f"   Tracking ID {dup['metadata__tracking_id']}: {dup['count']} messages")
        else:
            print(f"\n✅ NO DUPLICATE TRACKING IDs - Deduplication is working correctly!")
        
        return not duplicates.exists()

if __name__ == "__main__":
    success = test_simple_dedup()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ EMAIL DEDUPLICATION TEST PASSED")
    else:
        print("❌ EMAIL DEDUPLICATION TEST FAILED")
    print("=" * 60)
    
    sys.exit(0 if success else 1)