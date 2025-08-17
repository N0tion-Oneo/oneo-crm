#!/usr/bin/env python3
"""
Examine existing WhatsApp data in the oneotalent tenant
"""

import os
import django
import json
from datetime import datetime

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import UserChannelConnection, Message, Channel, ChannelType
from django.contrib.auth import get_user_model
from django.db import connection

User = get_user_model()

def examine_whatsapp_connections():
    """Examine existing WhatsApp connections in oneotalent"""
    print("📱 EXAMINING WHATSAPP CONNECTIONS IN ONEOTALENT")
    print("=" * 60)
    
    with schema_context('oneotalent'):
        # Get WhatsApp user connections
        whatsapp_connections = UserChannelConnection.objects.filter(
            channel_type=ChannelType.WHATSAPP
        )
        
        print(f"Found {whatsapp_connections.count()} WhatsApp user connections")
        
        for conn in whatsapp_connections:
            print(f"\n📱 Connection: {conn.id}")
            print(f"   User: {conn.user.username if conn.user else 'None'}")
            print(f"   Account Name: {conn.account_name}")
            print(f"   UniPile Account ID: {conn.unipile_account_id}")
            print(f"   Auth Status: {conn.auth_status}")
            print(f"   Account Status: {conn.account_status}")
            print(f"   Last Sync: {conn.last_sync_at}")
            print(f"   Created: {conn.created_at}")
            print(f"   Active: {conn.is_active}")
            
            # Show additional fields
            if conn.external_account_id:
                print(f"   External Account ID: {conn.external_account_id}")
            if hasattr(conn, 'phone_number') and conn.phone_number:
                print(f"   Phone Number: {conn.phone_number}")
        
        return whatsapp_connections

def examine_whatsapp_channels():
    """Examine WhatsApp channels"""
    print(f"\n📺 EXAMINING WHATSAPP CHANNELS")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        whatsapp_channels = Channel.objects.filter(
            channel_type=ChannelType.WHATSAPP
        )
        
        print(f"Found {whatsapp_channels.count()} WhatsApp channels")
        
        for channel in whatsapp_channels:
            print(f"\n📺 Channel: {channel.id}")
            print(f"   Name: {channel.name}")
            print(f"   Provider: {channel.provider}")
            print(f"   Active: {channel.is_active}")
            print(f"   Created: {channel.created_at}")
            
            # Get associated user connections
            connections = UserChannelConnection.objects.filter(
                channel_id=channel.id
            )
            print(f"   Connected Users: {connections.count()}")
            
            for conn in connections:
                print(f"      - {conn.user.username if conn.user else 'No user'} ({conn.auth_status})")
        
        return whatsapp_channels

def examine_whatsapp_messages():
    """Examine WhatsApp messages and their metadata"""
    print(f"\n📩 EXAMINING WHATSAPP MESSAGES")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        whatsapp_messages = Message.objects.filter(
            channel__channel_type=ChannelType.WHATSAPP
        ).order_by('-created_at')[:10]  # Get latest 10 messages
        
        print(f"Found {whatsapp_messages.count()} WhatsApp messages (showing latest 10)")
        
        for i, msg in enumerate(whatsapp_messages, 1):
            print(f"\n📩 Message {i}: {msg.id}")
            print(f"   Direction: {msg.direction}")
            print(f"   Content: {msg.content[:100]}..." if len(msg.content) > 100 else f"   Content: {msg.content}")
            print(f"   Contact: {msg.contact_email}")
            print(f"   Contact Name: {msg.contact_name}")
            print(f"   External ID: {msg.external_message_id}")
            print(f"   Created: {msg.created_at}")
            print(f"   Channel: {msg.channel.name if msg.channel else 'None'}")
            
            # Show metadata - this is the key information for WhatsApp
            if msg.metadata:
                print(f"   📊 Metadata:")
                metadata = msg.metadata
                for key, value in metadata.items():
                    if key in ['sender_attendee_id', 'chat_id', 'chat_type', 'message_source', 'delivery_status', 'from', 'to']:
                        print(f"      {key}: {value}")
                
                # Show all metadata keys
                print(f"   📋 All Metadata Keys: {list(metadata.keys())}")
                
                # Show full metadata for first few messages
                if i <= 3:
                    print(f"   📊 Full Metadata:")
                    print(json.dumps(metadata, indent=6))
            else:
                print(f"   📊 Metadata: None")
            
            # Show attachments if any
            if hasattr(msg, 'attachments') and msg.attachments:
                print(f"   📎 Attachments: {len(msg.attachments)}")
        
        return whatsapp_messages

def analyze_whatsapp_metadata_structure():
    """Analyze the structure of WhatsApp metadata"""
    print(f"\n🔍 ANALYZING WHATSAPP METADATA STRUCTURE")
    print("=" * 60)
    
    with schema_context('oneotalent'):
        # Get all unique metadata keys from WhatsApp messages
        whatsapp_messages = Message.objects.filter(
            channel__channel_type=ChannelType.WHATSAPP
        ).exclude(metadata__isnull=True)
        
        print(f"Analyzing metadata from {whatsapp_messages.count()} WhatsApp messages")
        
        all_keys = set()
        metadata_examples = {}
        
        for msg in whatsapp_messages:
            if msg.metadata:
                for key, value in msg.metadata.items():
                    all_keys.add(key)
                    
                    # Store example values for each key
                    if key not in metadata_examples:
                        metadata_examples[key] = []
                    
                    if value not in metadata_examples[key] and len(metadata_examples[key]) < 3:
                        metadata_examples[key].append(value)
        
        print(f"\n📋 Found {len(all_keys)} unique metadata keys:")
        for key in sorted(all_keys):
            examples = metadata_examples.get(key, [])
            print(f"   {key}: {examples}")
        
        # Show common patterns
        print(f"\n🔍 METADATA ANALYSIS:")
        
        # Sender information
        sender_keys = [k for k in all_keys if 'sender' in k.lower() or 'from' in k.lower()]
        if sender_keys:
            print(f"   📤 Sender Info Keys: {sender_keys}")
        
        # Chat information
        chat_keys = [k for k in all_keys if 'chat' in k.lower()]
        if chat_keys:
            print(f"   💬 Chat Info Keys: {chat_keys}")
        
        # Delivery information
        delivery_keys = [k for k in all_keys if 'delivery' in k.lower() or 'status' in k.lower()]
        if delivery_keys:
            print(f"   📨 Delivery Info Keys: {delivery_keys}")
        
        # UniPile specific
        unipile_keys = [k for k in all_keys if 'unipile' in k.lower() or 'attendee' in k.lower()]
        if unipile_keys:
            print(f"   🔗 UniPile Keys: {unipile_keys}")
        
        return all_keys, metadata_examples

def check_whatsapp_contacts():
    """Check how WhatsApp contacts are handled"""
    print(f"\n👥 CHECKING WHATSAPP CONTACT HANDLING")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        # Get unique contacts from WhatsApp messages
        whatsapp_messages = Message.objects.filter(
            channel__channel_type=ChannelType.WHATSAPP
        ).values('contact_email', 'contact_name', 'metadata').distinct()
        
        print(f"Found {len(whatsapp_messages)} unique WhatsApp contacts")
        
        contact_patterns = {}
        
        for msg in whatsapp_messages[:10]:  # Check first 10
            contact_email = msg['contact_email']
            contact_name = msg['contact_name']
            metadata = msg['metadata'] or {}
            
            print(f"\n👤 Contact:")
            print(f"   Email/ID: {contact_email}")
            print(f"   Name: {contact_name}")
            
            # Check for phone numbers in metadata
            phone_indicators = ['from', 'to', 'phone', 'number']
            for key, value in metadata.items():
                if any(indicator in key.lower() for indicator in phone_indicators):
                    print(f"   {key}: {value}")
            
            # Look for attendee ID
            if 'sender_attendee_id' in metadata:
                print(f"   Attendee ID: {metadata['sender_attendee_id']}")
            
            # Track patterns
            if '@s.whatsapp.net' in contact_email:
                contact_patterns['whatsapp_net'] = contact_patterns.get('whatsapp_net', 0) + 1
            elif contact_email.startswith('+'):
                contact_patterns['phone_number'] = contact_patterns.get('phone_number', 0) + 1
            else:
                contact_patterns['other'] = contact_patterns.get('other', 0) + 1
        
        print(f"\n📊 Contact Patterns:")
        for pattern, count in contact_patterns.items():
            print(f"   {pattern}: {count}")

def main():
    """Main examination function"""
    print("🔍 ONEOTALENT WHATSAPP EXAMINATION")
    print("=" * 80)
    
    # Check current tenant
    with schema_context('oneotalent'):
        print(f"Current schema: {connection.schema_name}")
        print(f"Current tenant: oneotalent")
    
    # Examine all WhatsApp data
    connections = examine_whatsapp_connections()
    channels = examine_whatsapp_channels() 
    messages = examine_whatsapp_messages()
    
    # Analyze metadata structure
    if messages:
        keys, examples = analyze_whatsapp_metadata_structure()
        check_whatsapp_contacts()
    else:
        print("⚠️ No WhatsApp messages found to analyze")
    
    print(f"\n✅ EXAMINATION COMPLETE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Summary
    print(f"\n📊 SUMMARY:")
    print(f"   WhatsApp Connections: {connections.count() if connections else 0}")
    print(f"   WhatsApp Channels: {len(channels) if channels else 0}")
    print(f"   WhatsApp Messages: {messages.count() if messages else 0}")

if __name__ == '__main__':
    main()