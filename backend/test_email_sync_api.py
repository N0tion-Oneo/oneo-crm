#!/usr/bin/env python
"""
Test email sync via direct API calls (bypassing Celery)
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection
from communications.record_communications.services.record_sync_orchestrator import RecordSyncOrchestrator
from pipelines.models import Pipeline, Record

def test_email_sync():
    """Test email sync via direct API calls"""
    
    # Use oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print(f"🏢 Testing in tenant: {tenant.name} ({tenant.schema_name})")
        
        # Get a test record
        pipeline = Pipeline.objects.filter(name='Contacts').first()
        if not pipeline:
            print("❌ No Contacts pipeline found")
            return
            
        record = Record.objects.filter(pipeline=pipeline).first()
        if not record:
            print("❌ No records found in Contacts pipeline")
            # Create a test record
            record = Record.objects.create(
                pipeline=pipeline,
                data={
                    'first_name': 'Test',
                    'last_name': 'User',
                    'email': 'josh@oneotalent.com'
                }
            )
            print(f"✅ Created test record: {record.id}")
        else:
            print(f"✅ Using existing record: {record.id}")
        
        # Get Gmail connection
        email_connection = UserChannelConnection.objects.filter(
            channel_type='gmail',
            is_active=True
        ).first()
        
        if not email_connection:
            # Try email type
            email_connection = UserChannelConnection.objects.filter(
                channel_type='email',
                is_active=True
            ).first()
            
        if not email_connection:
            print("❌ No active email connection found")
            print("Available connections:")
            for conn in UserChannelConnection.objects.all():
                print(f"  - {conn.channel_type}: {conn.account_name} (Active: {conn.is_active})")
            return
            
        print(f"✅ Using email connection: {email_connection.account_name}")
        
        # Test sync using the orchestrator
        print("\n📧 Starting email sync...")
        try:
            from django.conf import settings
            from communications.unipile.core.client import UnipileClient
            
            # Create UniPile client
            unipile_client = UnipileClient(
                dsn=settings.UNIPILE_DSN,
                access_token=settings.UNIPILE_API_KEY
            )
            
            # Get an admin user for triggered_by
            from authentication.models import CustomUser
            admin_user = CustomUser.objects.filter(is_superuser=True).first()
            if not admin_user:
                # Just get any active user
                admin_user = CustomUser.objects.filter(is_active=True).first()
            
            # Initialize orchestrator with UniPile client
            orchestrator = RecordSyncOrchestrator(unipile_client=unipile_client)
            
            # Sync the record (this will sync emails and other communications)
            result = orchestrator.sync_record(
                record_id=record.id,
                triggered_by=admin_user,
                trigger_reason="Testing participant linking refactor",
                channels_to_sync=['gmail']  # Only sync Gmail
            )
            
            if result['success']:
                print(f"✅ Email sync successful!")
                print(f"   - Messages fetched: {result.get('messages_fetched', 0)}")
                print(f"   - Messages created: {result.get('messages_created', 0)}")
                print(f"   - Messages updated: {result.get('messages_updated', 0)}")
                print(f"   - Participants created: {result.get('participants_created', 0)}")
                print(f"   - Participants linked: {result.get('participants_linked', 0)}")
                
                # Check if participants were linked using the new system
                from communications.models import Participant
                linked_participants = Participant.objects.filter(
                    contact_record=record
                ).count()
                print(f"   - Total participants linked to record: {linked_participants}")
                
            else:
                print(f"❌ Email sync failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error during sync: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_email_sync()