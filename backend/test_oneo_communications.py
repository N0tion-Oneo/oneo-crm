#!/usr/bin/env python
"""
Test that Oneo Digital company communications are accessible via API
"""
import os
import sys
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from pipelines.models import Record
from communications.record_communications.models import RecordCommunicationProfile, RecordCommunicationLink
from communications.models import Conversation, Message

print("=" * 80)
print("TESTING ONEO DIGITAL COMMUNICATIONS VISIBILITY")
print("=" * 80)

# Get tenant
tenant = Tenant.objects.get(schema_name='oneotalent')

with schema_context(tenant.schema_name):
    # Get Oneo Digital company record
    oneo = Record.objects.filter(
        pipeline__slug='companies',
        data__company_name='Oneo Digital'
    ).first()
    
    if not oneo:
        print("❌ Oneo Digital company record not found")
        sys.exit(1)
    
    print(f"\n✅ Found Oneo Digital (Record #{oneo.id})")
    print("-" * 40)
    
    # 1. Check RecordCommunicationProfile
    profile = RecordCommunicationProfile.objects.filter(record=oneo).first()
    if profile:
        print(f"\n1. RecordCommunicationProfile:")
        print(f"   Total conversations: {profile.total_conversations}")
        print(f"   Total messages: {profile.total_messages}")
        print(f"   Last message: {profile.last_message_at}")
        
        if profile.total_conversations > 0:
            print(f"   ✅ Profile has conversation counts")
        else:
            print(f"   ❌ Profile shows 0 conversations (needs update)")
    else:
        print(f"\n1. ❌ No RecordCommunicationProfile found")
    
    # 2. Check RecordCommunicationLinks
    links = RecordCommunicationLink.objects.filter(record=oneo).select_related('conversation')
    print(f"\n2. RecordCommunicationLinks: {links.count()}")
    
    if links.exists():
        # Show first 3 links
        for link in links[:3]:
            print(f"   - Link to conversation: {link.conversation.subject[:50]}...")
            print(f"     Match type: {link.match_type}")
            print(f"     Created: {link.created_at}")
    
    # 3. Check actual conversations (what the API would return)
    conversation_ids = links.values_list('conversation_id', flat=True).distinct()
    conversations = Conversation.objects.filter(
        id__in=conversation_ids
    ).order_by('-last_message_at')
    
    print(f"\n3. Accessible Conversations: {conversations.count()}")
    
    if conversations.exists():
        for conv in conversations[:3]:
            msg_count = Message.objects.filter(conversation=conv).count()
            print(f"   - {conv.subject[:50]}... ({msg_count} messages)")
            print(f"     Channel: {conv.channel.channel_type}")
            print(f"     Last message: {conv.last_message_at}")
    
    # 4. Check timeline messages (what would show in "All" tab)
    all_messages = Message.objects.filter(
        conversation_id__in=conversation_ids
    ).order_by('-sent_at')
    
    print(f"\n4. Timeline Messages: {all_messages.count()}")
    
    if all_messages.exists():
        for msg in all_messages[:3]:
            print(f"   - {msg.sent_at}: {msg.content[:80]}...")
    
    # 5. Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    
    if profile and profile.total_conversations > 0:
        print("✅ Oneo Digital profile is properly configured")
    else:
        print("⚠️  Profile needs conversation/message counts updated")
    
    if links.count() > 0:
        print(f"✅ {links.count()} RecordCommunicationLinks exist")
    else:
        print("❌ No RecordCommunicationLinks found")
    
    if conversations.count() > 0:
        print(f"✅ {conversations.count()} conversations are accessible via API")
    else:
        print("❌ No conversations accessible")
    
    if all_messages.count() > 0:
        print(f"✅ {all_messages.count()} messages would show in timeline")
    else:
        print("❌ No messages in timeline")
    
    print("=" * 80)
    
    # Test what the API endpoint would return
    print("\nTESTING API RESPONSE SIMULATION:")
    print("-" * 40)
    
    # Simulate the conversations endpoint
    from communications.record_communications.api import RecordCommunicationsViewSet
    from django.http import HttpRequest
    from rest_framework.request import Request
    from authentication.models import User
    
    # Get a user for the request
    user = User.objects.filter(is_superuser=True).first()
    if user:
        # Create a mock request
        django_request = HttpRequest()
        django_request.user = user
        request = Request(django_request)
        
        viewset = RecordCommunicationsViewSet()
        viewset.request = request
        
        # Get profile
        response = viewset.profile(request, pk=oneo.id)
        if response.status_code == 200:
            data = response.data
            print(f"Profile API Response:")
            print(f"  Total conversations: {data.get('total_conversations', 0)}")
            print(f"  Total messages: {data.get('total_messages', 0)}")
            
            if data.get('total_conversations', 0) > 0:
                print("  ✅ API returns conversation data")
            else:
                print("  ❌ API returns 0 conversations")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")