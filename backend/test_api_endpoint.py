#!/usr/bin/env python
"""
Test the API endpoint
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Conversation
from pipelines.models import Record
from communications.record_communications.api import RecordCommunicationsViewSet

# Use oneotalent tenant
tenant = Tenant.objects.get(schema_name='oneotalent')

with schema_context(tenant.schema_name):
    print(f"🏢 Testing in tenant: {tenant.name} ({tenant.schema_name})")
    
    # Get the record and a conversation
    record = Record.objects.get(id=93)
    print(f"\n📄 Record: {record.id}")
    
    # Create viewset instance
    viewset = RecordCommunicationsViewSet()
    
    # Get conversation IDs for this record
    conversation_ids = viewset._get_record_conversation_ids(record)
    print(f"\n💬 Conversation IDs linked to record: {len(list(conversation_ids))}")
    for conv_id in list(conversation_ids)[:5]:
        print(f"   - {conv_id} (type: {type(conv_id)})")
    
    # Get actual conversations
    conversations = Conversation.objects.filter(id__in=conversation_ids)
    print(f"\n📋 Actual conversations: {conversations.count()}")
    for conv in conversations[:3]:
        print(f"   - {conv.id}: {conv.subject[:50]}")
    
    # Test UUID comparison
    if conversations.exists():
        test_conv = conversations.first()
        test_id_str = str(test_conv.id)
        print(f"\n🧪 Testing UUID comparison:")
        print(f"   String ID: {test_id_str}")
        print(f"   In list as is: {test_conv.id in conversation_ids}")
        
        import uuid
        test_uuid = uuid.UUID(test_id_str)
        print(f"   UUID object: {test_uuid}")
        print(f"   UUID in list: {test_uuid in conversation_ids}")