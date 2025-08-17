#!/usr/bin/env python3
"""
Check local inbox data structure to see contact names
"""

import os
import django
import json

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import Message, Conversation, Channel

def check_local_inbox_data():
    """Check what data we have in local database for conversations"""
    print("🔍 CHECKING LOCAL INBOX DATA")
    print("=" * 80)
    
    with schema_context('oneotalent'):
        # Get conversations similar to how the local inbox API works
        conversations = Conversation.objects.all().order_by('-updated_at')[:5]
        
        print(f"📊 Found {conversations.count()} conversations")
        
        for i, conv in enumerate(conversations, 1):
            print(f"\n💬 Conversation {i}: {conv.id}")
            print(f"   Subject: {conv.subject}")
            print(f"   Channel: {conv.channel.name}")
            print(f"   Thread ID: {conv.external_thread_id}")
            
            # Get latest message for this conversation
            latest_message = Message.objects.filter(
                conversation=conv
            ).order_by('-created_at').first()
            
            if latest_message:
                print(f"\n   📨 Latest Message:")
                print(f"      Contact Email: {latest_message.contact_email}")
                print(f"      Content: {latest_message.content[:50]}...")
                print(f"      Direction: {latest_message.direction}")
                
                # Check metadata for contact names
                metadata = latest_message.metadata or {}
                contact_name = metadata.get('contact_name')
                print(f"      Metadata Contact Name: {contact_name}")
                
                # Show what the API would return for sender name
                sender_name = 'Unknown'
                
                # First priority: Enhanced contact name from metadata (real WhatsApp names)
                if latest_message.metadata and latest_message.metadata.get('contact_name'):
                    sender_name = latest_message.metadata['contact_name']
                    print(f"      ✅ Using metadata name: {sender_name}")
                # Second priority: Contact record
                elif latest_message.contact_record:
                    sender_name = latest_message.contact_record.data.get('name', 'Unknown')
                    print(f"      📋 Using contact record: {sender_name}")
                # Third priority: Extract from email
                elif latest_message.contact_email:
                    if '@' in latest_message.contact_email:
                        sender_name = latest_message.contact_email.split('@')[0].replace('.', ' ').title()
                    else:
                        sender_name = latest_message.contact_email
                    print(f"      📧 Using email extraction: {sender_name}")
                
                print(f"      🎯 Final sender name: {sender_name}")
                
                # Show what the conversation list would display
                print(f"\n   🖥️  What Frontend Should Display:")
                print(f"      Contact Name: {sender_name}")
                print(f"      Phone Number: {latest_message.contact_email.replace('@s.whatsapp.net', '') if '@s.whatsapp.net' in latest_message.contact_email else latest_message.contact_email}")

def show_sample_api_response():
    """Show what the API should return"""
    print(f"\n📡 SAMPLE API RESPONSE STRUCTURE")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        conversation = Conversation.objects.first()
        if conversation:
            latest_message = Message.objects.filter(
                conversation=conversation
            ).order_by('-created_at').first()
            
            if latest_message:
                # Simulate the API response
                metadata = latest_message.metadata or {}
                sender_name = 'Unknown'
                
                if metadata.get('contact_name'):
                    sender_name = metadata['contact_name']
                elif latest_message.contact_email:
                    if '@' in latest_message.contact_email:
                        sender_name = latest_message.contact_email.split('@')[0].replace('.', ' ').title()
                
                api_response = {
                    "conversations": [
                        {
                            "id": str(conversation.id),
                            "type": conversation.channel.channel_type,
                            "participants": [
                                {
                                    "name": sender_name,
                                    "email": latest_message.contact_email,
                                    "platform": conversation.channel.channel_type
                                }
                            ],
                            "last_message": {
                                "content": latest_message.content[:50] + "..." if len(latest_message.content) > 50 else latest_message.content,
                                "sender": {
                                    "name": sender_name,
                                    "email": latest_message.contact_email
                                },
                                "contact_email": latest_message.contact_email,
                                "metadata": metadata
                            }
                        }
                    ]
                }
                
                print(json.dumps(api_response, indent=2))

def main():
    """Main function"""
    check_local_inbox_data()
    show_sample_api_response()

if __name__ == '__main__':
    main()