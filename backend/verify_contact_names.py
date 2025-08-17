#!/usr/bin/env python3
"""
Verify contact names are displaying properly (Vanessa, Warren, etc.)
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Message, Conversation

def verify_contact_names():
    """Verify that contact names are displaying properly"""
    
    # Get the oneotalent tenant
    try:
        tenant = Tenant.objects.get(schema_name='oneotalent')
    except Tenant.DoesNotExist:
        print("❌ oneotalent tenant not found")
        return
    
    with schema_context(tenant.schema_name):
        print("🔍 Checking WhatsApp contact names...")
        
        # Get all WhatsApp conversations
        whatsapp_messages = Message.objects.filter(
            channel__channel_type='whatsapp'
        ).order_by('-created_at')[:20]
        
        print(f"📊 Found {whatsapp_messages.count()} recent WhatsApp messages")
        
        # Known contacts mapping (from identity handler)
        known_contacts = {
            '27849977040': 'Vanessa',
            '27836851686': 'Warren', 
            '27836587900': 'Pearl',
            '27720720057': 'Robbie Cowan',
            '27665830939': 'Contact +27 66 583 0939',
            '27725750914': 'Contact +27 72 575 0914'
        }
        
        business_account = '27720720047@s.whatsapp.net'
        
        print("\n📋 Recent WhatsApp messages:")
        print("=" * 80)
        
        for message in whatsapp_messages:
            contact_email = message.contact_email or ''
            phone_number = contact_email.replace('@s.whatsapp.net', '')
            
            # Determine contact name
            contact_name = 'Unknown'
            is_business = contact_email == business_account
            
            if is_business:
                contact_name = "OneOTalent Business"
            elif phone_number in known_contacts:
                contact_name = known_contacts[phone_number]
            elif contact_email and '@s.whatsapp.net' in contact_email:
                contact_name = f"+{phone_number}" if phone_number else contact_email
            
            # Check metadata for additional contact info
            metadata_name = message.metadata.get('contact_name', '') if message.metadata else ''
            
            direction_symbol = "←" if message.direction == 'inbound' else "→"
            
            print(f"{direction_symbol} {contact_name:<20} | {phone_number:<15} | {message.content[:40]:<40} | {message.created_at.strftime('%H:%M')}")
            
            if metadata_name and metadata_name != contact_email:
                print(f"   📝 Metadata name: {metadata_name}")
        
        print("=" * 80)
        
        # Summary of contacts found
        contact_emails = set()
        for message in whatsapp_messages:
            if message.contact_email:
                contact_emails.add(message.contact_email)
        
        print(f"\n📊 Contact Summary:")
        print(f"Total unique contacts: {len(contact_emails)}")
        
        for email in sorted(contact_emails):
            phone = email.replace('@s.whatsapp.net', '')
            is_business = email == business_account
            
            if is_business:
                name = "OneOTalent Business"
                status = "✅ Business account (correctly identified)"
            elif phone in known_contacts:
                name = known_contacts[phone]
                status = "✅ Known contact (named properly)"
            else:
                name = f"+{phone}"
                status = "⚠️  Unknown contact (showing phone number)"
            
            print(f"  • {name:<25} | {phone:<15} | {status}")

if __name__ == '__main__':
    verify_contact_names()