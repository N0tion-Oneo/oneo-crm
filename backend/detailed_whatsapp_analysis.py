#!/usr/bin/env python3
"""
Detailed WhatsApp analysis for oneotalent tenant
"""

import os
import django
import json
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import Message, UserChannelConnection, Channel, ChannelType

def analyze_whatsapp_messages():
    """Analyze WhatsApp message structure and metadata"""
    print("📩 DETAILED WHATSAPP MESSAGE ANALYSIS")
    print("=" * 60)
    
    with schema_context('oneotalent'):
        # Get all WhatsApp messages
        whatsapp_messages = Message.objects.filter(
            channel__channel_type='whatsapp'
        ).order_by('-created_at')[:20]  # Get latest 20
        
        print(f"Analyzing {whatsapp_messages.count()} WhatsApp messages")
        
        # Collect metadata structure
        all_metadata_keys = set()
        message_types = set()
        contact_patterns = {}
        
        for i, msg in enumerate(whatsapp_messages, 1):
            print(f"\n📩 Message {i}: {msg.id}")
            print(f"   Direction: {msg.direction}")
            print(f"   Content: '{msg.content[:50]}...'" if len(msg.content) > 50 else f"   Content: '{msg.content}'")
            print(f"   Contact Email: {msg.contact_email}")
            # Contact name might be in metadata or contact_record
            contact_name = "Unknown"
            if msg.metadata and 'contact_name' in msg.metadata:
                contact_name = msg.metadata['contact_name']
            elif msg.contact_record:
                contact_name = str(msg.contact_record)
            print(f"   Contact Name: {contact_name}")
            print(f"   External ID: {msg.external_message_id}")
            print(f"   Created: {msg.created_at}")
            print(f"   Channel: {msg.channel.name if msg.channel else 'None'}")
            
            # Analyze metadata
            if msg.metadata:
                metadata = msg.metadata
                all_metadata_keys.update(metadata.keys())
                
                print(f"   📊 Key Metadata:")
                
                # Show UniPile specific data
                if 'sender_attendee_id' in metadata:
                    print(f"      Sender Attendee ID: {metadata['sender_attendee_id']}")
                
                if 'chat_id' in metadata:
                    print(f"      Chat ID: {metadata['chat_id']}")
                
                if 'from' in metadata:
                    print(f"      From: {metadata['from']}")
                
                if 'to' in metadata:
                    print(f"      To: {metadata['to']}")
                
                if 'message_source' in metadata:
                    print(f"      Message Source: {metadata['message_source']}")
                
                if 'type' in metadata:
                    message_types.add(metadata['type'])
                    print(f"      Type: {metadata['type']}")
                
                # Analyze contact patterns
                contact = msg.contact_email
                if '@s.whatsapp.net' in contact:
                    contact_patterns['whatsapp_net'] = contact_patterns.get('whatsapp_net', 0) + 1
                elif contact.startswith('+'):
                    contact_patterns['phone_plus'] = contact_patterns.get('phone_plus', 0) + 1
                else:
                    contact_patterns['other'] = contact_patterns.get('other', 0) + 1
                
                # Show full metadata for first 3 messages
                if i <= 3:
                    print(f"   📊 Full Metadata:")
                    print(json.dumps(metadata, indent=6))
        
        # Summary analysis
        print(f"\n🔍 ANALYSIS SUMMARY")
        print(f"=" * 40)
        print(f"📋 All Metadata Keys Found: {sorted(all_metadata_keys)}")
        print(f"📝 Message Types: {sorted(message_types)}")
        print(f"👥 Contact Patterns: {contact_patterns}")
        
        return all_metadata_keys, message_types, contact_patterns

def analyze_whatsapp_connections():
    """Analyze WhatsApp connection data"""
    print(f"\n📱 WHATSAPP CONNECTION ANALYSIS")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        connections = UserChannelConnection.objects.filter(
            channel_type=ChannelType.WHATSAPP
        )
        
        print(f"Found {connections.count()} WhatsApp connections")
        
        for conn in connections:
            print(f"\n📱 Connection: {conn.id}")
            print(f"   User: {conn.user.username if conn.user else 'None'}")
            print(f"   Account Name: {conn.account_name}")
            print(f"   UniPile Account ID: {conn.unipile_account_id}")
            if hasattr(conn, 'external_account_id') and conn.external_account_id:
                print(f"   External Account ID: {conn.external_account_id}")
            print(f"   Auth Status: {conn.auth_status}")
            print(f"   Account Status: {conn.account_status}")
            print(f"   Last Sync: {conn.last_sync_at}")
            print(f"   Created: {conn.created_at}")
            print(f"   Active: {conn.is_active}")
            
            # Show phone number if available
            if hasattr(conn, 'phone_number') and conn.phone_number:
                print(f"   Phone: {conn.phone_number}")
        
        return connections

def show_whatsapp_webhook_structure():
    """Show the webhook structure UniPile sends for WhatsApp"""
    print(f"\n📡 WHATSAPP WEBHOOK STRUCTURES")
    print("=" * 50)
    
    # Based on the actual data we're seeing
    webhook_examples = {
        "account_connected": {
            "event_type": "creation_success",
            "account_id": "mp9Gis3IRtuh9V5oSxZdSA",  # Real account ID from data
            "provider": "whatsapp",
            "account": {
                "id": "mp9Gis3IRtuh9V5oSxZdSA",
                "provider": "whatsapp",
                "phone_number": "+27720720047",  # Based on attendee data
                "display_name": "OneOTalent WhatsApp",
                "verified": True
            }
        },
        "message_received": {
            "event_type": "message.received",
            "account_id": "mp9Gis3IRtuh9V5oSxZdSA",
            "message": {
                "id": "unique_message_id",
                "chat_id": "chat_unique_id",
                "type": "text",
                "text": "Should I get Nivea deodorant with you?",  # Real message content
                "from": "27849977040@s.whatsapp.net",  # Real WhatsApp ID
                "to": "27720720047@s.whatsapp.net",
                "timestamp": "2024-08-16T19:00:00Z",
                "from_me": False,
                "attachments": [],
                "metadata": {
                    "sender_attendee_id": "LI-rNlCvUIu80uk2O0q_Iw",  # Real attendee ID
                    "chat_type": "individual",
                    "message_source": "whatsapp",
                    "delivery_status": "delivered",
                    "contact_name": "Vanessa"  # Real contact name
                }
            }
        },
        "attendee_info": {
            "object": "ChatAttendee",
            "id": "LI-rNlCvUIu80uk2O0q_Iw",
            "account_id": "mp9Gis3IRtuh9V5oSxZdSA", 
            "provider_id": "27849977040@s.whatsapp.net",
            "name": "Vanessa",
            "is_self": 0,
            "picture_url": "wapp://mp9Gis3IRtuh9V5oSxZdSA/27849977040@s.whatsapp.net.jpg",
            "specifics": {
                "provider": "WHATSAPP"
            }
        }
    }
    
    for event_name, structure in webhook_examples.items():
        print(f"\n📡 {event_name.replace('_', ' ').title()}:")
        print(json.dumps(structure, indent=2))

def analyze_whatsapp_contact_resolution():
    """Analyze how WhatsApp contacts are resolved"""
    print(f"\n👥 WHATSAPP CONTACT RESOLUTION ANALYSIS")
    print("=" * 60)
    
    with schema_context('oneotalent'):
        messages = Message.objects.filter(
            channel__channel_type='whatsapp'
        ).values('contact_email', 'metadata').distinct()
        
        print(f"Analyzing {len(messages)} unique WhatsApp contacts")
        
        # Patterns we've discovered
        contact_resolution_patterns = {
            "phone_with_whatsapp_net": [],  # 27849977040@s.whatsapp.net
            "named_contacts": [],  # Contacts with real names
            "self_contacts": [],  # is_self: 1 contacts
            "unknown_contacts": []  # Fallback patterns
        }
        
        for msg in messages:
            contact_email = msg['contact_email']
            metadata = msg['metadata'] or {}
            contact_name = metadata.get('contact_name', contact_email)
            
            # Categorize contact patterns
            if '@s.whatsapp.net' in contact_email:
                if contact_name and contact_name != contact_email:
                    contact_resolution_patterns['named_contacts'].append({
                        'email': contact_email,
                        'name': contact_name,
                        'phone': contact_email.replace('@s.whatsapp.net', ''),
                        'attendee_id': metadata.get('sender_attendee_id')
                    })
                else:
                    contact_resolution_patterns['phone_with_whatsapp_net'].append({
                        'email': contact_email,
                        'phone': contact_email.replace('@s.whatsapp.net', ''),
                        'attendee_id': metadata.get('sender_attendee_id')
                    })
            else:
                contact_resolution_patterns['unknown_contacts'].append({
                    'email': contact_email,
                    'name': contact_name
                })
        
        # Display analysis
        for pattern_name, contacts in contact_resolution_patterns.items():
            if contacts:
                print(f"\n📞 {pattern_name.replace('_', ' ').title()}: {len(contacts)}")
                for contact in contacts[:3]:  # Show first 3 examples
                    print(f"   - {contact}")
        
        # Key insights
        print(f"\n🔍 KEY INSIGHTS:")
        print(f"   • WhatsApp contacts use '@s.whatsapp.net' suffix")
        print(f"   • Phone numbers are international format (e.g., 27849977040)")
        print(f"   • Real names available via UniPile attendee lookup")
        print(f"   • Attendee IDs link to contact details and profile pictures")
        print(f"   • Contact resolution: phone@s.whatsapp.net → UniPile attendee → real name")

def main():
    """Main analysis function"""
    print("🚀 COMPREHENSIVE WHATSAPP ANALYSIS - ONEOTALENT")
    print("=" * 80)
    
    # Analyze all aspects
    connections = analyze_whatsapp_connections()
    metadata_keys, message_types, contact_patterns = analyze_whatsapp_messages()
    analyze_whatsapp_contact_resolution()
    show_whatsapp_webhook_structure()
    
    # Final summary
    print(f"\n✅ ANALYSIS COMPLETE")
    print(f"=" * 40)
    print(f"📱 Active WhatsApp account: mp9Gis3IRtuh9V5oSxZdSA")
    print(f"📞 Phone number: +27720720047 (South Africa)")
    print(f"👥 Contact examples: Vanessa, Kent Fourie, Mel Cook")
    print(f"📊 Message metadata includes: {', '.join(sorted(metadata_keys))}")
    print(f"🔗 UniPile provides attendee IDs for contact resolution")
    print(f"🌍 Cloudflare tunnel: webhooks.oneocrm.com/webhooks/unipile/")

if __name__ == '__main__':
    main()