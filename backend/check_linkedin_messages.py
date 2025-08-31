#!/usr/bin/env python
"""
Script to check LinkedIn message directions
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Message, UserChannelConnection

def check_linkedin_messages():
    """Check LinkedIn message directions"""
    
    print("🔍 Checking LinkedIn messages and directions...")
    
    # Get the oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    # Use schema context for proper tenant isolation
    with schema_context(tenant.schema_name):
        # Get LinkedIn connection
        connection = UserChannelConnection.objects.filter(
            channel_type='linkedin',
            is_active=True
        ).first()
        
        if connection:
            print(f"✓ LinkedIn connection found")
            print(f"  Account ID: {connection.unipile_account_id}")
        
        # Get LinkedIn messages
        messages = Message.objects.filter(
            channel__channel_type='linkedin'
        ).order_by('sent_at')
        
        print(f"\n📊 Found {messages.count()} LinkedIn messages")
        
        if messages.exists():
            # Count by direction
            inbound = messages.filter(direction='inbound').count()
            outbound = messages.filter(direction='outbound').count()
            
            print(f"  Inbound: {inbound}")
            print(f"  Outbound: {outbound}")
            
            print("\n📝 Message details:")
            for msg in messages[:20]:  # Show all messages
                # Get sender info from metadata
                metadata = msg.metadata or {}
                is_sender = metadata.get('is_sender', 0)
                sender_id = metadata.get('sender_attendee_id') or metadata.get('sender_id')
                sender_name = metadata.get('sender_name', 'Unknown')
                
                # Skip enriched sender check for now
                
                print(f"\n  Message {str(msg.id)[:8]}...")
                print(f"    Direction: {msg.direction}")
                print(f"    is_sender flag: {is_sender}")
                print(f"    Sender: {sender_name}")
                print(f"    Sender ID: {sender_id}")
                print(f"    Content: {msg.content[:50]}...")
                print(f"    Sent at: {msg.sent_at}")
                
                # Check if this should be outbound
                if is_sender == 1 and msg.direction != 'outbound':
                    print(f"    ⚠️  MISMATCH: is_sender=1 but direction={msg.direction}")
                elif is_sender == 0 and msg.direction != 'inbound':
                    print(f"    ⚠️  MISMATCH: is_sender=0 but direction={msg.direction}")

if __name__ == "__main__":
    check_linkedin_messages()