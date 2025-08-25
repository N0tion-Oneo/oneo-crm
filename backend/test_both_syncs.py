#!/usr/bin/env python
"""
Test both frontend and background sync methods
Verify: chats, messages, attendees, and direction
"""
import os
import sys
import django
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from django.contrib.auth import get_user_model
from communications.models import UserChannelConnection, Channel, Conversation, Message, ChatAttendee
from communications.channels.whatsapp.background_sync import (
    _run_comprehensive_sync_simplified,
    sync_account_comprehensive_background
)

User = get_user_model()

def test_sync_method(method_name, sync_function, channel, user, connection, tenant, use_celery=False):
    """Test a sync method and return results"""
    
    print(f"\n{'=' * 60}")
    print(f"🧪 TESTING {method_name}")
    print(f"{'=' * 60}")
    
    # Clear existing data for a fresh test
    print("🧹 Clearing existing data...")
    Message.objects.all().delete()
    Conversation.objects.all().delete()
    ChatAttendee.objects.all().delete()
    print("   ✅ Data cleared")
    
    # Run sync
    print(f"🔄 Running {method_name}...")
    
    sync_options = {
        'days_back': 7,  # Reduced for faster testing
        'max_messages_per_chat': 20,  # Reduced for faster testing
    }
    
    start_time = time.time()
    
    if use_celery:
        # Background sync via Celery
        result = sync_function.delay(
            channel_id=str(channel.id),
            user_id=str(user.id),
            sync_options=sync_options,
            tenant_schema=tenant.schema_name
        )
        
        print(f"   📋 Task queued with ID: {result.id}")
        print(f"   ⏳ Waiting for completion...")
        
        # Wait for task with timeout
        max_wait = 120  # 2 minutes
        while not result.ready() and (time.time() - start_time) < max_wait:
            time.sleep(2)
        
        if result.successful():
            stats = result.result
            print(f"   ✅ Task completed successfully")
        else:
            print(f"   ❌ Task failed or timed out")
            stats = {'success': False}
    else:
        # Direct sync
        stats = sync_function(
            channel=channel,
            options=sync_options,
            connection=connection
        )
    
    sync_time = time.time() - start_time
    
    # Collect results
    conversations = Conversation.objects.all()
    messages = Message.objects.all()
    attendees = ChatAttendee.objects.all()
    
    # Count by direction
    in_messages = messages.filter(direction='inbound')
    out_messages = messages.filter(direction='outbound')
    
    # Count attendees by type
    account_owners = attendees.filter(is_self=True)
    regular_attendees = attendees.filter(is_self=False)
    
    # Check for issues
    out_without_sender = messages.filter(direction='out', sender__isnull=True)
    
    results = {
        'method': method_name,
        'sync_time': sync_time,
        'stats': stats,
        'chats_count': conversations.count(),
        'messages_count': messages.count(),
        'attendees_count': attendees.count(),
        'account_owners_count': account_owners.count(),
        'regular_attendees_count': regular_attendees.count(),
        'in_messages_count': in_messages.count(),
        'out_messages_count': out_messages.count(),
        'out_without_sender_count': out_without_sender.count(),
        'sample_messages': [],
        'sample_attendees': []
    }
    
    # Get sample messages with direction
    for msg in messages[:10]:
        sender_name = msg.sender.name if msg.sender else "No sender"
        sender_is_self = msg.sender.is_self if msg.sender else False
        results['sample_messages'].append({
            'direction': msg.direction,
            'sender': sender_name,
            'is_self': sender_is_self,
            'content': msg.content[:30] if msg.content else "No content"
        })
    
    # Get sample attendees
    for att in attendees[:5]:
        results['sample_attendees'].append({
            'name': att.name,
            'phone': att.phone_number,
            'is_self': att.is_self
        })
    
    return results

def print_results(results):
    """Print test results in a formatted way"""
    
    print(f"\n📊 RESULTS FOR {results['method']}")
    print(f"   ⏱️ Sync time: {results['sync_time']:.2f} seconds")
    
    if results['stats'].get('success'):
        print(f"   ✅ Sync successful")
        print(f"      Reported chats synced: {results['stats'].get('chats_synced', 'N/A')}")
        print(f"      Reported messages synced: {results['stats'].get('messages_synced', 'N/A')}")
    else:
        print(f"   ❌ Sync failed")
    
    print(f"\n   📱 CHATS: {results['chats_count']}")
    
    print(f"\n   👥 ATTENDEES: {results['attendees_count']}")
    print(f"      Account owners (is_self=True): {results['account_owners_count']}")
    print(f"      Regular attendees: {results['regular_attendees_count']}")
    
    if results['sample_attendees']:
        print(f"      Sample attendees:")
        for att in results['sample_attendees'][:3]:
            self_marker = " 🔵" if att['is_self'] else ""
            print(f"         - {att['name']} ({att['phone']}){self_marker}")
    
    print(f"\n   📨 MESSAGES: {results['messages_count']}")
    print(f"      Inbound (in): {results['in_messages_count']}")
    print(f"      Outbound (out): {results['out_messages_count']}")
    
    if results['out_messages_count'] > 0:
        ratio = (results['in_messages_count'] / results['out_messages_count']) if results['out_messages_count'] > 0 else 0
        print(f"      In/Out ratio: {ratio:.2f}")
    
    if results['out_without_sender_count'] > 0:
        print(f"      ⚠️ Outbound without sender: {results['out_without_sender_count']}")
    
    if results['sample_messages']:
        print(f"\n   📝 Sample messages:")
        for msg in results['sample_messages'][:5]:
            direction_emoji = "📤" if msg['direction'] == 'out' else "📥"
            self_marker = " (You)" if msg['is_self'] else ""
            print(f"      {direction_emoji} [{msg['direction']}] {msg['sender']}{self_marker}: {msg['content']}")

def main():
    """Run tests for both sync methods"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print("\n🚀 COMPREHENSIVE SYNC TEST")
        print("=" * 60)
        
        # Get user and connection
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ No active user found")
            return
            
        print(f"✅ User: {user.username}")
        
        connection = UserChannelConnection.objects.filter(
            user=user,
            channel_type='whatsapp',
            is_active=True,
            unipile_account_id__isnull=False
        ).first()
        
        if not connection:
            print("❌ No active WhatsApp connections found")
            return
            
        print(f"✅ Connection: {connection.account_name}")
        
        # Get or create channel
        channel, _ = Channel.objects.get_or_create(
            unipile_account_id=connection.unipile_account_id,
            channel_type='whatsapp',
            defaults={
                'name': f"WhatsApp Account {connection.account_name}",
                'auth_status': 'authenticated',
                'is_active': True,
                'created_by': user
            }
        )
        
        # Test 1: Frontend sync
        frontend_results = test_sync_method(
            "FRONTEND SYNC (_run_comprehensive_sync_simplified)",
            _run_comprehensive_sync_simplified,
            channel,
            user,
            connection,
            tenant,
            use_celery=False
        )
        
        print_results(frontend_results)
        
        # Test 2: Background sync
        background_results = test_sync_method(
            "BACKGROUND SYNC (via Celery)",
            sync_account_comprehensive_background,
            channel,
            user,
            connection,
            tenant,
            use_celery=True
        )
        
        print_results(background_results)
        
        # Comparison
        print("\n" + "=" * 60)
        print("📊 COMPARISON")
        print("=" * 60)
        
        print(f"\n{'Metric':<30} {'Frontend':<15} {'Background':<15}")
        print("-" * 60)
        print(f"{'Chats':<30} {frontend_results['chats_count']:<15} {background_results['chats_count']:<15}")
        print(f"{'Messages':<30} {frontend_results['messages_count']:<15} {background_results['messages_count']:<15}")
        print(f"{'Attendees':<30} {frontend_results['attendees_count']:<15} {background_results['attendees_count']:<15}")
        print(f"{'Account Owners':<30} {frontend_results['account_owners_count']:<15} {background_results['account_owners_count']:<15}")
        print(f"{'Inbound Messages':<30} {frontend_results['in_messages_count']:<15} {background_results['in_messages_count']:<15}")
        print(f"{'Outbound Messages':<30} {frontend_results['out_messages_count']:<15} {background_results['out_messages_count']:<15}")
        print(f"{'Sync Time (seconds)':<30} {frontend_results['sync_time']:.2f}{'':>13} {background_results['sync_time']:.2f}")
        
        # Check for issues
        print("\n🔍 ISSUES DETECTED:")
        issues = []
        
        if frontend_results['account_owners_count'] == 0:
            issues.append("Frontend sync: No account owner (is_self=True) created")
        if background_results['account_owners_count'] == 0:
            issues.append("Background sync: No account owner (is_self=True) created")
            
        if frontend_results['out_without_sender_count'] > 0:
            issues.append(f"Frontend sync: {frontend_results['out_without_sender_count']} outbound messages without sender")
        if background_results['out_without_sender_count'] > 0:
            issues.append(f"Background sync: {background_results['out_without_sender_count']} outbound messages without sender")
            
        if frontend_results['out_messages_count'] == 0:
            issues.append("Frontend sync: No outbound messages detected")
        if background_results['out_messages_count'] == 0:
            issues.append("Background sync: No outbound messages detected")
            
        if frontend_results['in_messages_count'] == 0:
            issues.append("Frontend sync: No inbound messages detected")
        if background_results['in_messages_count'] == 0:
            issues.append("Background sync: No inbound messages detected")
        
        if issues:
            for issue in issues:
                print(f"   ⚠️ {issue}")
        else:
            print("   ✅ No issues detected!")
        
        print("\n" + "=" * 60)
        print("✅ TEST COMPLETE!")
        print("=" * 60)

if __name__ == "__main__":
    main()