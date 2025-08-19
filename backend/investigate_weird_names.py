#!/usr/bin/env python3
"""
Investigate weird contact names in messages
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

def investigate_weird_names():
    """Investigate messages with weird contact names"""
    
    print("🔍 INVESTIGATING WEIRD CONTACT NAMES")
    print("=" * 60)
    
    with schema_context('oneotalent'):
        from communications.models import Message
        
        # Find recent WhatsApp messages
        messages = Message.objects.filter(
            channel__channel_type='whatsapp'
        ).order_by('-created_at')[:15]
        
        print(f"📱 Checking {len(messages)} recent WhatsApp messages:")
        print()
        
        weird_names = []
        for msg in messages:
            metadata = msg.metadata or {}
            contact_name = metadata.get('contact_name', 'No contact_name')
            processing_version = metadata.get('processing_version', 'unknown')
            
            # Check for weird names
            is_weird = False
            if contact_name == 'No contact_name':
                is_weird = True
                reason = "No contact_name in metadata"
            elif len(contact_name) > 20 and ('@s.whatsapp.net' in contact_name or any(c.isdigit() for c in contact_name)):
                is_weird = True
                reason = "Looks like ID or phone number"
            elif contact_name.isdigit():
                is_weird = True
                reason = "Pure phone number"
            elif '@s.whatsapp.net' in contact_name:
                is_weird = True
                reason = "WhatsApp JID format"
            elif len(contact_name) == 22 and all(c.isalnum() or c in '-_' for c in contact_name):
                is_weird = True
                reason = "Looks like UniPile ID"
                
            status_icon = "❌" if is_weird else "✅"
            
            print(f"{status_icon} Message {str(msg.id)[:8]}...")
            print(f"   Contact Name: '{contact_name}'")
            print(f"   Contact Phone: {msg.contact_phone}")
            print(f"   Contact Email: {msg.contact_email}")
            print(f"   Direction: {msg.direction}")
            print(f"   Processing Version: {processing_version}")
            
            if is_weird:
                print(f"   ⚠️  Issue: {reason}")
                weird_names.append({
                    'id': msg.id,
                    'contact_name': contact_name,
                    'reason': reason,
                    'processing_version': processing_version
                })
                
                # Check raw webhook data for better info
                raw_data = metadata.get('raw_webhook_data', {})
                if raw_data:
                    provider_chat_id = raw_data.get('provider_chat_id', 'Not found')
                    sender = raw_data.get('sender', {})
                    attendees = raw_data.get('attendees', [])
                    
                    print(f"   🔍 Raw Data Analysis:")
                    print(f"      Provider Chat ID: {provider_chat_id}")
                    print(f"      Sender: {sender.get('attendee_name', 'No name')} ({sender.get('attendee_provider_id', 'No ID')})")
                    if attendees:
                        print(f"      Attendees:")
                        for att in attendees[:2]:  # Show first 2
                            print(f"        - {att.get('attendee_name', 'No name')} ({att.get('attendee_provider_id', 'No ID')})")
            
            print()
        
        # Summary
        print("📊 SUMMARY:")
        print(f"   Total messages checked: {len(messages)}")
        print(f"   Messages with weird names: {len(weird_names)}")
        
        if weird_names:
            print("\n🔧 ISSUES FOUND:")
            issue_counts = {}
            for item in weird_names:
                reason = item['reason']
                issue_counts[reason] = issue_counts.get(reason, 0) + 1
            
            for reason, count in issue_counts.items():
                print(f"   • {reason}: {count} messages")
                
        return weird_names

if __name__ == '__main__':
    weird_names = investigate_weird_names()
    
    if weird_names:
        print(f"\n❌ Found {len(weird_names)} messages with display issues")
        print("   Need to fix provider logic or clean up legacy data")
    else:
        print("\n✅ All messages have proper contact names!")