#!/usr/bin/env python
"""
Link Vanessa's participant record to her contact record
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import Participant
from pipelines.models import Record

print("=" * 80)
print("LINKING VANESSA'S PARTICIPANT TO CONTACT")
print("=" * 80)

with schema_context('oneotalent'):
    # Find Vanessa's contact record
    print("\n1. Finding Vanessa's contact record...")
    contact_record = Record.objects.filter(
        data__personal_email='vanessa.c.brown86@gmail.com'
    ).first()
    
    if not contact_record:
        print("   ❌ Contact record not found!")
        sys.exit(1)
    
    print(f"   ✅ Found contact: Record ID {contact_record.id}")
    print(f"      Pipeline: {contact_record.pipeline.name}")
    print(f"      Email: {contact_record.data.get('personal_email')}")
    
    # Find participant record
    print("\n2. Finding participant record...")
    participant = Participant.objects.filter(
        email__iexact='vanessa.c.brown86@gmail.com'
    ).first()
    
    if not participant:
        print("   ❌ Participant not found!")
        sys.exit(1)
    
    print(f"   ✅ Found participant: {participant.id}")
    print(f"      Email: {participant.email}")
    print(f"      Current contact: {participant.contact_record}")
    
    # Link them
    print("\n3. Linking participant to contact...")
    if participant.contact_record == contact_record:
        print("   ℹ️ Already linked!")
    else:
        participant.contact_record = contact_record
        participant.resolution_confidence = 100  # High confidence since we manually linked
        participant.resolution_method = 'manual_link'
        participant.save()
        print(f"   ✅ Successfully linked participant to contact!")
        print(f"      Contact ID: {contact_record.id}")
        print(f"      Confidence: 100%")
        print(f"      Method: manual_link")
    
    # Verify the link
    print("\n4. Verifying link...")
    participant.refresh_from_db()
    if participant.contact_record:
        print(f"   ✅ Participant is now linked to contact ID: {participant.contact_record.id}")
        print("\n   🎉 SUCCESS! Future emails to/from vanessa.c.brown86@gmail.com will be stored!")
    else:
        print("   ❌ Link failed!")

print("\n" + "=" * 80)