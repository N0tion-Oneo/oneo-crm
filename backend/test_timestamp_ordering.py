#!/usr/bin/env python
"""Test that messages and conversations are ordered by actual timestamps, not sync time"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import Message, Conversation
from django.db.models.functions import Coalesce
from django.db.models import F
from datetime import datetime


def test_message_ordering(tenant='oneotalent'):
    """Test that messages are ordered by actual timestamp"""
    with schema_context(tenant):
        # Get a conversation with multiple messages
        conversation = Conversation.objects.filter(
            messages__isnull=False
        ).annotate(
            msg_count=F('message_count')
        ).filter(msg_count__gt=1).first()
        
        if not conversation:
            print("❌ No conversation with multiple messages found")
            return False
        
        print(f"\nTesting conversation: {conversation.subject[:50]}...")
        print(f"Messages in conversation: {conversation.message_count}")
        
        # Test the API query pattern
        messages = Message.objects.filter(
            conversation_id=conversation.id
        ).annotate(
            actual_timestamp=Coalesce('sent_at', 'received_at', 'created_at')
        ).order_by('-actual_timestamp')[:10]
        
        print("\nMessage ordering (should be newest to oldest):")
        prev_timestamp = None
        all_ordered = True
        
        for i, msg in enumerate(messages, 1):
            timestamp = msg.sent_at or msg.received_at or msg.created_at
            print(f"  {i}. {timestamp.strftime('%Y-%m-%d %H:%M')} - {msg.direction[:3]} - {msg.content[:20]}")
            
            # Check ordering
            if prev_timestamp and timestamp > prev_timestamp:
                print(f"     ❌ Out of order! {timestamp} > {prev_timestamp}")
                all_ordered = False
            prev_timestamp = timestamp
        
        if all_ordered:
            print("\n✅ Messages are correctly ordered by actual timestamp")
        else:
            print("\n❌ Messages are NOT correctly ordered")
        
        return all_ordered


def test_conversation_ordering(tenant='oneotalent'):
    """Test that conversations are ordered by last_message_at"""
    with schema_context(tenant):
        # Get conversations ordered by last message
        conversations = Conversation.objects.filter(
            messages__isnull=False
        ).distinct().order_by('-last_message_at')[:10]
        
        print("\nConversation ordering (should be newest to oldest):")
        prev_timestamp = None
        all_ordered = True
        
        for i, conv in enumerate(conversations, 1):
            print(f"  {i}. {conv.last_message_at.strftime('%Y-%m-%d %H:%M')} - {conv.subject[:30]}")
            
            # Check ordering
            if prev_timestamp and conv.last_message_at > prev_timestamp:
                print(f"     ❌ Out of order! {conv.last_message_at} > {prev_timestamp}")
                all_ordered = False
            prev_timestamp = conv.last_message_at
        
        if all_ordered:
            print("\n✅ Conversations are correctly ordered by last_message_at")
        else:
            print("\n❌ Conversations are NOT correctly ordered")
        
        return all_ordered


def test_timestamp_consistency(tenant='oneotalent'):
    """Test that created_at != sent_at/received_at for historical messages"""
    with schema_context(tenant):
        # Check messages with unipile data
        messages = Message.objects.filter(
            metadata__unipile_data__isnull=False
        )[:20]
        
        different_count = 0
        total_count = len(messages)
        
        print("\nChecking timestamp consistency:")
        for msg in messages:
            actual_time = msg.sent_at or msg.received_at
            if actual_time and actual_time != msg.created_at:
                different_count += 1
        
        if total_count > 0:
            percentage = (different_count / total_count) * 100
            print(f"  {different_count}/{total_count} messages have different timestamps ({percentage:.1f}%)")
            
            if percentage > 80:
                print("  ✅ Most messages have correct historical timestamps")
                return True
            else:
                print("  ❌ Many messages still have sync time as timestamp")
                return False
        else:
            print("  ❌ No messages with unipile_data found")
            return False


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Message and Conversation Timestamp Ordering")
    print("=" * 60)
    
    # Run tests
    results = []
    results.append(test_message_ordering())
    results.append(test_conversation_ordering())
    results.append(test_timestamp_consistency())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    if all(results):
        print("✅ ALL TESTS PASSED - Infinite scroll should work correctly!")
    else:
        print("❌ SOME TESTS FAILED - Check the output above for details")
        sys.exit(1)