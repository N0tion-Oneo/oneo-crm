#!/usr/bin/env python3
"""
Fix business account message directions
All messages with contact_email=business_account should be OUTBOUND, not INBOUND
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
from communications.models import Message, MessageDirection

def fix_business_account_messages():
    """Fix incorrectly stored business account messages"""
    
    print("🔧 FIXING BUSINESS ACCOUNT MESSAGE DIRECTIONS")
    print("=" * 60)
    
    # Get the oneotalent tenant
    try:
        tenant = Tenant.objects.get(schema_name='oneotalent')
    except Tenant.DoesNotExist:
        print("❌ oneotalent tenant not found")
        return False
    
    with schema_context(tenant.schema_name):
        business_account = '27720720047@s.whatsapp.net'
        
        # Find all messages with business account as contact_email
        business_messages = Message.objects.filter(
            contact_email=business_account,
            channel__channel_type='whatsapp'
        )
        
        print(f"📊 Found {business_messages.count()} business account messages")
        
        # Check their current directions
        inbound_count = business_messages.filter(direction='inbound').count()
        outbound_count = business_messages.filter(direction='outbound').count()
        
        print(f"📥 Currently inbound: {inbound_count}")
        print(f"📤 Currently outbound: {outbound_count}")
        
        if inbound_count > 0:
            print(f"\n🔧 Fixing {inbound_count} incorrectly stored inbound messages...")
            
            # Update all inbound business messages to outbound
            updated_count = business_messages.filter(direction='inbound').update(
                direction=MessageDirection.OUTBOUND
            )
            
            print(f"✅ Updated {updated_count} messages from inbound → outbound")
            
            # Also need to fix the contact_email - business should NOT be the contact
            # These messages should have the recipient's phone number as contact_email
            print(f"\n🔧 Clearing contact_email for business outbound messages...")
            
            # For outbound messages, contact_email should be empty or the recipient
            # Since we can't determine the original recipient, we'll clear it
            business_outbound_messages = Message.objects.filter(
                contact_email=business_account,
                direction=MessageDirection.OUTBOUND,
                channel__channel_type='whatsapp'
            )
            
            cleared_count = business_outbound_messages.update(contact_email='')
            print(f"✅ Cleared contact_email for {cleared_count} outbound business messages")
            
        else:
            print("✅ No inbound business messages found - already correct!")
        
        # Final verification
        print(f"\n🔍 FINAL VERIFICATION:")
        remaining_inbound = Message.objects.filter(
            contact_email=business_account,
            direction='inbound',
            channel__channel_type='whatsapp'
        ).count()
        
        remaining_outbound = Message.objects.filter(
            contact_email=business_account,
            direction='outbound', 
            channel__channel_type='whatsapp'
        ).count()
        
        print(f"📥 Business account inbound messages: {remaining_inbound}")
        print(f"📤 Business account outbound messages: {remaining_outbound}")
        
        if remaining_inbound == 0:
            print("🎉 SUCCESS: No more inbound business account messages!")
            return True
        else:
            print("❌ Still have inbound business account messages")
            return False

if __name__ == '__main__':
    success = fix_business_account_messages()
    sys.exit(0 if success else 1)