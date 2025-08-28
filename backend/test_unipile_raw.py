#!/usr/bin/env python
import os
import sys
import django
import requests
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')
django.setup()

from oneo_crm.settings import unipile_settings

# Get UniPile configuration
dsn = unipile_settings.dsn
api_key = unipile_settings.api_key
account_id = "mp9Gis3IRtuh9V5oSxZdSA"  # From previous response

# Build request
url = f"{dsn}/api/v1/chats"
headers = {
    'X-API-KEY': api_key,
    'Accept': 'application/json'
}

params = {
    'limit': 2,
    'account_id': account_id,
    'account_type': 'WHATSAPP'
}

print("Fetching raw UniPile chats data...")
print("=" * 70)

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    data = response.json()
    
    # Show the raw UniPile response
    print("\nRAW UNIPILE RESPONSE:")
    print(json.dumps(data, indent=2))
    
    # Check what fields are available in each chat
    if 'items' in data and data['items']:
        print("\n\nFIELDS IN FIRST CHAT:")
        print("-" * 50)
        first_chat = data['items'][0]
        for key in first_chat.keys():
            value = first_chat[key]
            if isinstance(value, (str, int, float, bool, type(None))):
                print(f"  {key}: {value}")
            elif isinstance(value, dict):
                print(f"  {key}: <dict with {len(value)} keys>")
            elif isinstance(value, list):
                print(f"  {key}: <list with {len(value)} items>")
                
        # Check if there's name data we're missing
        if 'name' in first_chat:
            print(f"\n  Chat name field: '{first_chat['name']}'")
        if 'attendee_name' in first_chat:
            print(f"  Attendee name field: '{first_chat['attendee_name']}'")
        if 'attendees' in first_chat:
            print(f"  Has attendees field: {len(first_chat['attendees'])} attendees")
            
else:
    print(f"Error: {response.status_code}")
    print(response.text[:500])