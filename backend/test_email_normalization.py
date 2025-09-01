#!/usr/bin/env python
"""
Test email normalization to debug participant extraction
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from datetime import datetime
from communications.utils.email_extractor import (
    extract_email_recipients_info,
    extract_email_sender_info,
    determine_email_direction
)

# Test webhook data
webhook_data = {
    "event": "mail_sent",
    "from": {
        "email": "josh@oneodigital.com",
        "name": "Josh"
    },
    "to": [{
        "email": "vanessa.c.brown86@gmail.com",
        "name": "Vanessa Brown"
    }],
    "subject": "test outbound email"
}

print("Testing email extraction functions:")
print("=" * 60)

# Test recipient extraction
recipients = extract_email_recipients_info(webhook_data)
print(f"Recipients extracted: {recipients}")

# Test sender extraction
sender = extract_email_sender_info(webhook_data)
print(f"Sender extracted: {sender}")

# Test direction
direction = determine_email_direction(webhook_data, "josh@oneodigital.com")
print(f"Direction: {direction}")

print("\n" + "=" * 60)
print("Recipients structure:")
print(f"  to: {recipients.get('to', [])}")
print(f"  cc: {recipients.get('cc', [])}")
print(f"  bcc: {recipients.get('bcc', [])}")

if recipients.get('to'):
    print("\nFirst TO recipient:")
    first_to = recipients['to'][0]
    print(f"  email: {first_to.get('email')}")
    print(f"  name: {first_to.get('name')}")