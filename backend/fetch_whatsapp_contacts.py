#!/usr/bin/env python3
"""
Fetch WhatsApp contact names from UniPile attendees API
"""

import os
import django
import requests
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import Message

def main():
    print("🔍 FETCHING WHATSAPP CONTACT NAMES")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        # Get WhatsApp messages with sender_attendee_id
        whatsapp_messages = Message.objects.filter(
            channel__channel_type='whatsapp'
        ).exclude(
            metadata__sender_attendee_id__isnull=True
        )[:5]  # Get first 5 messages
        
        print(f"Found {whatsapp_messages.count()} WhatsApp messages with attendee IDs")
        
        # UniPile API setup
        unipile_settings = settings.UNIPILE_SETTINGS
        headers = {
            'X-API-KEY': unipile_settings.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        attendee_ids = set()
        
        # Extract unique attendee IDs
        for msg in whatsapp_messages:
            attendee_id = msg.metadata.get('sender_attendee_id')
            if attendee_id:
                attendee_ids.add(attendee_id)
                print(f"Message: '{msg.content[:30]}...' - Attendee ID: {attendee_id}")
        
        print(f"\nUnique attendee IDs: {len(attendee_ids)}")
        
        # Fetch attendee details from UniPile
        for attendee_id in attendee_ids:
            try:
                print(f"\n🔍 Fetching attendee: {attendee_id}")
                
                # Try the attendee detail endpoint
                attendee_url = f"{unipile_settings.dsn}/api/v1/chat_attendees/{attendee_id}"
                response = requests.get(attendee_url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    attendee_data = response.json()
                    print(f"✅ Attendee data: {attendee_data}")
                    
                    # Show relevant fields
                    if isinstance(attendee_data, dict):
                        name = attendee_data.get('name', 'Unknown')
                        email = attendee_data.get('email', '')
                        phone = attendee_data.get('phone', '')
                        print(f"  📝 Name: {name}")
                        print(f"  📧 Email: {email}")
                        print(f"  📱 Phone: {phone}")
                else:
                    print(f"❌ Failed to fetch attendee: {response.status_code}")
                    print(f"Response: {response.text[:200]}")
                    
            except Exception as e:
                print(f"❌ Error fetching attendee {attendee_id}: {e}")
        
        # Also try the list attendees endpoint
        print(f"\n📋 FETCHING ALL ATTENDEES")
        print("-" * 30)
        
        try:
            attendees_url = f"{unipile_settings.dsn}/api/v1/chat_attendees"
            params = {'limit': 10}  # Get first 10
            
            response = requests.get(attendees_url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                attendees_data = response.json()
                print(f"✅ Attendees response: {type(attendees_data)}")
                
                # Handle response format (likely items array)
                if isinstance(attendees_data, dict) and 'items' in attendees_data:
                    attendees = attendees_data['items']
                else:
                    attendees = attendees_data
                
                print(f"Found {len(attendees)} attendees")
                
                for attendee in attendees[:5]:  # Show first 5
                    print(f"  - ID: {attendee.get('id', 'No ID')}")
                    print(f"    Name: {attendee.get('name', 'Unknown')}")
                    print(f"    Phone: {attendee.get('phone', '')}")
                    print(f"    Email: {attendee.get('email', '')}")
                    print()
            else:
                print(f"❌ Failed to fetch attendees: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ Error fetching attendees: {e}")

if __name__ == '__main__':
    main()