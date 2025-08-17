#!/usr/bin/env python3
"""
Analyze WhatsApp identity separation: Connected Account vs. Conversation Contacts
"""

import os
import django
import json

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import Message, UserChannelConnection, ChannelType

def analyze_whatsapp_identity_separation():
    """Analyze the separation between connected account and conversation contacts"""
    print("🔍 WHATSAPP IDENTITY SEPARATION ANALYSIS")
    print("=" * 80)
    
    with schema_context('oneotalent'):
        # Get the connected WhatsApp account
        whatsapp_connection = UserChannelConnection.objects.filter(
            channel_type=ChannelType.WHATSAPP,
            auth_status='authenticated'
        ).first()
        
        if not whatsapp_connection:
            print("❌ No authenticated WhatsApp connection found")
            return
        
        print(f"📱 CONNECTED WHATSAPP ACCOUNT")
        print(f"=" * 50)
        print(f"   Account Name: {whatsapp_connection.account_name}")
        print(f"   UniPile Account ID: {whatsapp_connection.unipile_account_id}")
        print(f"   Connected User: {whatsapp_connection.user.username}")
        print(f"   Business Owner: josh@oneodigital.com")
        
        # Analyze messages to find the account's own phone number
        messages = Message.objects.filter(
            channel__channel_type='whatsapp'
        ).order_by('-created_at')
        
        # Find self-messages (is_self: 1) to identify the business phone
        business_phone = None
        business_attendee_id = None
        
        for msg in messages:
            if msg.metadata and msg.metadata.get('is_sender') == 1:
                # This message was sent by the business account
                business_phone = msg.contact_email
                business_attendee_id = msg.metadata.get('sender_attendee_id')
                break
        
        if not business_phone:
            # Look for the business phone in attendee data from previous analysis
            business_phone = "27720720047@s.whatsapp.net"  # From the analysis
            business_attendee_id = "S6t5wOmzXYGs4j9ZDt6vZg"
        
        print(f"   Business Phone: {business_phone}")
        print(f"   Business Attendee ID: {business_attendee_id}")
        
        # Analyze conversation contacts (people messaging with the business)
        print(f"\n👥 CONVERSATION CONTACTS (People messaging the business)")
        print(f"=" * 60)
        
        # Get unique conversation contacts
        conversation_contacts = {}
        
        for msg in messages[:20]:  # Analyze recent messages
            contact_email = msg.contact_email
            metadata = msg.metadata or {}
            
            # Skip messages from the business itself
            if contact_email == business_phone:
                continue
            
            attendee_id = metadata.get('sender_attendee_id')
            contact_name = metadata.get('contact_name', contact_email)
            
            if contact_email not in conversation_contacts:
                conversation_contacts[contact_email] = {
                    'name': contact_name,
                    'attendee_id': attendee_id,
                    'phone_number': contact_email.replace('@s.whatsapp.net', ''),
                    'message_count': 0,
                    'last_message': None,
                    'sample_content': None
                }
            
            conversation_contacts[contact_email]['message_count'] += 1
            if not conversation_contacts[contact_email]['last_message']:
                conversation_contacts[contact_email]['last_message'] = msg.created_at
                conversation_contacts[contact_email]['sample_content'] = msg.content[:50]
        
        # Display conversation contacts
        print(f"Found {len(conversation_contacts)} unique conversation contacts:")
        
        for i, (contact_email, details) in enumerate(conversation_contacts.items(), 1):
            print(f"\n👤 Contact {i}: {details['name']}")
            print(f"   Phone: {details['phone_number']}")
            print(f"   WhatsApp ID: {contact_email}")
            print(f"   Attendee ID: {details['attendee_id']}")
            print(f"   Messages: {details['message_count']}")
            print(f"   Last Message: {details['last_message']}")
            print(f"   Sample: '{details['sample_content']}...'")
        
        return whatsapp_connection, conversation_contacts

def show_proper_data_structure():
    """Show how to properly structure WhatsApp data"""
    print(f"\n📊 PROPER WHATSAPP DATA STRUCTURE")
    print(f"=" * 60)
    
    structure = {
        "connected_account": {
            "description": "The business WhatsApp account connected to OneOTalent",
            "example": {
                "account_id": "mp9Gis3IRtuh9V5oSxZdSA",
                "business_phone": "+27720720047",
                "business_name": "OneOTalent",
                "connected_user": "josh@oneodigital.com",
                "account_type": "WhatsApp Business",
                "verification_status": "verified"
            },
            "purpose": "This is the business sending/receiving messages"
        },
        "conversation_contacts": {
            "description": "People who message the business WhatsApp account",
            "examples": [
                {
                    "contact_name": "Vanessa",
                    "phone_number": "+27849977040",
                    "whatsapp_id": "27849977040@s.whatsapp.net",
                    "attendee_id": "LI-rNlCvUIu80uk2O0q_Iw",
                    "profile_picture": "wapp://mp9Gis3IRtuh9V5oSxZdSA/27849977040@s.whatsapp.net.jpg",
                    "relationship": "Customer/Contact"
                },
                {
                    "contact_name": "Warren",
                    "phone_number": "+27836851686", 
                    "whatsapp_id": "27836851686@s.whatsapp.net",
                    "attendee_id": "yVT7kUViW1KbUiHFIDgm3Q",
                    "relationship": "Customer/Contact"
                }
            ],
            "purpose": "These are the customers/contacts messaging the business"
        }
    }
    
    print(json.dumps(structure, indent=2))

def show_message_direction_handling():
    """Show how to properly handle message directions"""
    print(f"\n📩 MESSAGE DIRECTION HANDLING")
    print(f"=" * 50)
    
    direction_examples = {
        "inbound_message": {
            "description": "Customer messaging the business",
            "from": "27849977040@s.whatsapp.net",  # Customer (Vanessa)
            "to": "27720720047@s.whatsapp.net",    # Business (OneOTalent)
            "direction": "inbound",
            "sender_attendee_id": "LI-rNlCvUIu80uk2O0q_Iw",  # Vanessa's attendee ID
            "is_sender": 0,  # False - customer is sending
            "content": "Should I get Nivea deodorant while I'm there?",
            "display_as": "Message FROM Vanessa TO OneOTalent Business"
        },
        "outbound_message": {
            "description": "Business messaging the customer",
            "from": "27720720047@s.whatsapp.net",   # Business (OneOTalent)
            "to": "27849977040@s.whatsapp.net",     # Customer (Vanessa)
            "direction": "outbound",
            "sender_attendee_id": "S6t5wOmzXYGs4j9ZDt6vZg",  # Business attendee ID
            "is_sender": 1,  # True - business is sending
            "content": "Yes, please get the Nivea deodorant",
            "display_as": "Message FROM OneOTalent Business TO Vanessa"
        }
    }
    
    print(json.dumps(direction_examples, indent=2))

def show_ui_recommendations():
    """Show UI recommendations for displaying WhatsApp data"""
    print(f"\n🎨 UI DISPLAY RECOMMENDATIONS")
    print(f"=" * 50)
    
    recommendations = [
        "1. NEVER show the business phone number as a 'contact'",
        "2. Business account should be shown as 'Connected Account' or 'Your WhatsApp'",
        "3. Conversation contacts are the customers/people messaging the business",
        "4. In message lists, show customer names (Vanessa, Warren) not phone numbers",
        "5. Use profile pictures from UniPile attendee data",
        "6. Group messages by conversation (chat_id)",
        "7. Show clear message direction (you sent vs. they sent)",
        "8. Display business verification status prominently",
        "9. Use contact_name from metadata when available",
        "10. Fall back to phone number only if no name available"
    ]
    
    for rec in recommendations:
        print(f"   ✅ {rec}")

def main():
    """Main analysis function"""
    print("🚀 WHATSAPP IDENTITY SEPARATION - COMPLETE ANALYSIS")
    print("=" * 80)
    
    # Analyze current setup
    connection, contacts = analyze_whatsapp_identity_separation()
    
    # Show proper structure
    show_proper_data_structure()
    
    # Show message direction handling
    show_message_direction_handling()
    
    # Show UI recommendations
    show_ui_recommendations()
    
    print(f"\n🎯 KEY TAKEAWAYS")
    print(f"=" * 30)
    print(f"✅ Business Account: 27720720047@s.whatsapp.net (OneOTalent)")
    print(f"✅ Conversation Contacts: Vanessa, Warren, Robbie, etc.")
    print(f"✅ Message Direction: Clear inbound/outbound separation")
    print(f"✅ UniPile Integration: Attendee IDs for rich contact data")
    print(f"✅ UI Safety: Never confuse business with customers")

if __name__ == '__main__':
    main()