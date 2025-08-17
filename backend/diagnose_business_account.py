#!/usr/bin/env python3
"""
Diagnose business account message direction issues
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
from communications.models import Message

def diagnose_business_account():
    """Diagnose business account message direction issues"""
    
    try:
        tenant = Tenant.objects.get(schema_name='oneotalent')
    except Tenant.DoesNotExist:
        print("❌ oneotalent tenant not found")
        return
    
    with schema_context(tenant.schema_name):
        business_account = '27720720047@s.whatsapp.net'
        
        print("🔍 BUSINESS ACCOUNT ANALYSIS")
        print("=" * 50)
        print(f"Business Account: {business_account}")
        
        # Get all business account messages
        business_messages = Message.objects.filter(
            contact_email=business_account,
            channel__channel_type='whatsapp'
        ).order_by('-created_at')
        
        print(f"\n📊 Total business account messages: {business_messages.count()}")
        
        # Count by direction
        inbound_count = business_messages.filter(direction='inbound').count()
        outbound_count = business_messages.filter(direction='outbound').count()
        
        print(f"📥 Inbound messages: {inbound_count}")
        print(f"📤 Outbound messages: {outbound_count}")
        
        print(f"\n🚨 ISSUE IDENTIFIED:")
        print(f"The business account has {inbound_count} inbound messages!")
        print(f"Business accounts should ONLY have outbound messages.")
        print(f"This suggests messages FROM the business TO customers are incorrectly")
        print(f"being categorized as inbound messages FROM customers.")
        
        print(f"\n📋 Sample inbound business messages (these are incorrect):")
        print("-" * 50)
        
        incorrect_messages = business_messages.filter(direction='inbound')[:5]
        for msg in incorrect_messages:
            print(f"• {msg.created_at.strftime('%H:%M')} | {msg.content[:50]}")
            print(f"  External ID: {msg.external_message_id}")
            print(f"  Conversation: {msg.conversation.external_thread_id if msg.conversation else 'None'}")
            
            # Check metadata for clues
            if msg.metadata:
                sender_info = msg.metadata.get('sender', {})
                if sender_info:
                    print(f"  Metadata sender: {sender_info}")
            print()
        
        print(f"\n📋 Sample outbound business messages (these are correct):")
        print("-" * 50)
        
        correct_messages = business_messages.filter(direction='outbound')[:3]
        for msg in correct_messages:
            print(f"• {msg.created_at.strftime('%H:%M')} | {msg.content[:50]}")
            print(f"  External ID: {msg.external_message_id}")
            print(f"  Conversation: {msg.conversation.external_thread_id if msg.conversation else 'None'}")
            print()
        
        print(f"\n💡 ROOT CAUSE ANALYSIS:")
        print(f"This issue likely occurs when:")
        print(f"1. Messages sent FROM business TO customers are incorrectly marked as inbound")
        print(f"2. The webhook processing or message creation logic has wrong direction logic")
        print(f"3. The contact_email field is being set to business account for customer messages")
        
        print(f"\n🔧 SOLUTION:")
        print(f"The business account (27720720047@s.whatsapp.net) should:")
        print(f"• NEVER appear in contact_email for inbound messages")
        print(f"• ONLY appear in contact_email for outbound messages we send")
        print(f"• Customer phone numbers should be in contact_email for inbound messages")

if __name__ == '__main__':
    diagnose_business_account()