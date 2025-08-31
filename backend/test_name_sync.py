#!/usr/bin/env python
"""
Test sync to verify participant names are being populated correctly
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from pipelines.models import Record
from communications.record_communications.tasks.sync_tasks import sync_record_communications

User = get_user_model()

def test_name_sync():
    """Run a sync and check if names are populated"""
    
    schema_name = 'oneotalent'
    record_id = 66
    
    with schema_context(schema_name):
        print(f"Running sync for record {record_id} in schema {schema_name}")
        
        # Get a user
        user = User.objects.filter(is_staff=True).first()
        
        try:
            # Call the task directly (synchronously)
            # Import the actual function, not the task
            from communications.record_communications.tasks.sync_tasks import sync_record_communications
            
            # When calling directly, skip self and pass record_id as first positional arg
            result = sync_record_communications.run(
                record_id,
                tenant_schema=schema_name,
                triggered_by_id=user.id if user else None,
                trigger_reason='Test sync for name verification'
            )
            
            print(f"\nSync completed: {result.get('success', False)}")
            print(f"Conversations: {result.get('total_conversations', 0)}")
            print(f"Messages: {result.get('total_messages', 0)}")
            
            # Check participant names
            from communications.models import Participant
            
            print("\n=== CHECKING PARTICIPANT NAMES ===")
            
            # Email participants
            email_participants = Participant.objects.exclude(email='').exclude(email__isnull=True)[:10]
            
            for p in email_participants:
                if not p.name or p.name == '':
                    print(f'❌ No name: email={p.email}')
                elif '@' in p.name or p.name == p.email:
                    print(f'⚠️  Email as name: name="{p.name}", email={p.email}')
                else:
                    print(f'✓ Proper name: name="{p.name}", email={p.email}')
            
            # WhatsApp/LinkedIn participants
            other_participants = Participant.objects.filter(email='').exclude(phone='')[:5]
            for p in other_participants:
                if p.name:
                    print(f'✓ Messaging participant: name="{p.name}", phone={p.phone}')
                else:
                    print(f'❌ No name: phone={p.phone}')
                    
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_name_sync()