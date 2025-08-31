#!/usr/bin/env python
"""
Test record-level sync for Saul Chilchik in oneotalent tenant
"""
import os
import sys
import django
import asyncio
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection
from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Record
from communications.models import UserChannelConnection, Conversation, Message
from communications.record_communications.services.record_sync_manager import RecordSyncManager
from communications.record_communications.models import (
    RecordCommunicationProfile,
    RecordAttendeeMapping,
    RecordCommunicationLink,
    RecordSyncJob
)
from tenants.models import Tenant
from django.contrib.auth import get_user_model

User = get_user_model()


def find_saul_record():
    """Find Saul Chilchik's record in oneotalent tenant"""
    print("\n🔍 Finding Saul Chilchik's Record")
    print("=" * 60)
    
    # Get oneotalent tenant
    try:
        tenant = Tenant.objects.get(schema_name='oneotalent')
        print(f"✅ Found tenant: {tenant.name} (schema: {tenant.schema_name})")
    except Tenant.DoesNotExist:
        print("❌ Tenant 'oneotalent' not found")
        return None, None
    
    # Switch to tenant schema
    with schema_context(tenant.schema_name):
        # Find contact pipeline
        try:
            pipeline = Pipeline.objects.get(slug='contacts')
            print(f"✅ Found pipeline: {pipeline.name} (ID: {pipeline.id})")
        except Pipeline.DoesNotExist:
            # Try alternative names
            pipelines = Pipeline.objects.filter(pipeline_type='contacts')
            if pipelines.exists():
                pipeline = pipelines.first()
                print(f"✅ Found pipeline: {pipeline.name} (ID: {pipeline.id})")
            else:
                print("❌ No contact pipeline found")
                return None, None
        
        # Search for Saul Chilchik
        # Try different search strategies
        records = Record.objects.filter(pipeline=pipeline)
        
        # Search by name in data field
        saul_records = []
        for record in records:
            data = record.data or {}
            # Check various name fields
            name_fields = ['name', 'full_name', 'first_name', 'contact_name']
            for field in name_fields:
                if field in data:
                    name = str(data[field]).lower()
                    if 'saul' in name and 'chilchik' in name:
                        saul_records.append(record)
                        break
            
            # Also check if first_name + last_name matches
            first_name = str(data.get('first_name', '')).lower()
            last_name = str(data.get('last_name', '')).lower()
            if 'saul' in first_name and 'chilchik' in last_name:
                if record not in saul_records:
                    saul_records.append(record)
        
        if saul_records:
            record = saul_records[0]
            print(f"✅ Found Saul Chilchik's record: ID {record.id}")
            print(f"   Record data fields: {list(record.data.keys())}")
            
            # Display key identifiers
            print("\n📧 Contact Information:")
            for key in ['email', 'phone', 'mobile', 'linkedin', 'website']:
                if key in record.data and record.data[key]:
                    print(f"   {key}: {record.data[key]}")
            
            return tenant, record
        else:
            print("❌ Saul Chilchik's record not found")
            print(f"   Total records in pipeline: {records.count()}")
            
            # Show some sample records
            print("\n   Sample records (first 5):")
            for r in records[:5]:
                name = r.data.get('name') or r.data.get('full_name') or r.data.get('contact_name') or 'Unknown'
                print(f"   - {name} (ID: {r.id})")
            
            return tenant, None


def check_channel_connections(tenant):
    """Check available channel connections for the tenant"""
    print("\n📡 Checking Channel Connections")
    print("=" * 60)
    
    with schema_context(tenant.schema_name):
        connections = UserChannelConnection.objects.filter(
            account_status='active'
        )
        
        print(f"Active connections: {connections.count()}")
        
        for conn in connections:
            print(f"\n📌 {conn.channel_type.upper()} Connection:")
            print(f"   Account: {conn.account_name}")
            print(f"   User: {conn.user.email if conn.user else 'N/A'}")
            print(f"   Status: {conn.account_status}")
            print(f"   UniPile ID: {conn.unipile_account_id[:20]}..." if conn.unipile_account_id else "   UniPile ID: Not set")
        
        return connections


def sync_record(tenant, record):
    """Trigger sync for the record"""
    print("\n🔄 Triggering Record Sync")
    print("=" * 60)
    
    with schema_context(tenant.schema_name):
        sync_manager = RecordSyncManager()
        
        # Get or create communication profile
        profile, created = RecordCommunicationProfile.objects.get_or_create(
            record=record,
            defaults={'pipeline_id': record.pipeline_id}
        )
        
        print(f"Communication Profile: {'Created' if created else 'Existing'}")
        
        # Extract identifiers
        from communications.record_communications.services.identifier_extractor import RecordIdentifierExtractor
        extractor = RecordIdentifierExtractor()
        identifiers = extractor.extract_identifiers_from_record(record)
        
        print("\n🔑 Extracted Identifiers:")
        for key, values in identifiers.items():
            if values:
                print(f"   {key}: {values}")
        
        # Update profile with identifiers
        profile.communication_identifiers = identifiers
        profile.save()
        
        # Build provider IDs for different channels
        print("\n🆔 Provider IDs by Channel:")
        for channel in ['whatsapp', 'linkedin', 'instagram', 'telegram']:
            provider_ids = sync_manager._build_provider_ids(identifiers, channel)
            if provider_ids:
                print(f"   {channel}: {provider_ids}")
        
        # Check if sync is already in progress
        if profile.sync_in_progress:
            print("⚠️  Sync already in progress")
            return None
        
        # Get a user for triggering
        user = User.objects.filter(is_active=True).first()
        
        print("\n🚀 Starting sync job via Celery task...")
        try:
            # Import and trigger the async task
            from communications.record_communications.tasks import sync_record_communications
            
            # Create sync job record
            sync_job = RecordSyncJob.objects.create(
                record=record,
                profile=profile,
                job_type='full_history',
                status='pending',
                triggered_by=user,
                trigger_reason='Test sync for Saul Chilchik'
            )
            
            # Queue the async task to background_sync queue
            result = sync_record_communications.apply_async(
                args=[record.id],
                kwargs={
                    'triggered_by_id': user.id if user else None,
                    'trigger_reason': 'Test sync for Saul Chilchik'
                },
                queue='background_sync'
            )
            
            sync_job.celery_task_id = result.id
            sync_job.save()
            
            print(f"✅ Sync job queued: {sync_job.id}")
            print(f"   Celery task ID: {result.id}")
            print(f"   Status: {sync_job.status}")
            
            # Wait for the task to process
            import time
            max_wait = 30  # Maximum 30 seconds
            wait_interval = 2
            elapsed = 0
            
            print("\n⏳ Waiting for sync to process...")
            while elapsed < max_wait:
                time.sleep(wait_interval)
                elapsed += wait_interval
                
                # Refresh sync job to get updated status
                sync_job.refresh_from_db()
                
                if sync_job.status != 'pending':
                    break
                    
                print(f"   {elapsed}s: Status = {sync_job.status}")
            
            print(f"\n📊 Final Sync Job Status: {sync_job.status}")
            if sync_job.status == 'completed':
                print(f"   ✅ Conversations found: {sync_job.conversations_found}")
                print(f"   ✅ Messages found: {sync_job.messages_found}")
                print(f"   ✅ New links created: {sync_job.new_links_created}")
            elif sync_job.status == 'failed':
                print(f"   ❌ Error: {sync_job.error_message}")
                if sync_job.error_details:
                    print(f"   Details: {sync_job.error_details}")
            elif sync_job.status == 'running':
                print(f"   ⚠️  Still running after {elapsed}s")
                print(f"   Progress: {sync_job.progress_percentage}%")
                print(f"   Current step: {sync_job.current_step}")
            else:
                print(f"   ⚠️  Status unchanged after {elapsed}s - check Celery logs")
            
            return sync_job
            
        except Exception as e:
            print(f"❌ Sync failed: {e}")
            import traceback
            traceback.print_exc()
            return None


def check_sync_results(tenant, record):
    """Check the results of the sync"""
    print("\n📊 Sync Results")
    print("=" * 60)
    
    with schema_context(tenant.schema_name):
        # Check attendee mappings
        mappings = RecordAttendeeMapping.objects.filter(record=record)
        print(f"\n🗺️  Attendee Mappings: {mappings.count()}")
        for mapping in mappings[:5]:
            print(f"   {mapping.channel_type}: {mapping.provider_id} -> {mapping.attendee_name or 'Unknown'}")
        
        # Check communication links
        links = RecordCommunicationLink.objects.filter(record=record)
        print(f"\n🔗 Communication Links: {links.count()}")
        for link in links[:5]:
            print(f"   Conversation {link.conversation_id}: {link.match_type} ({link.match_identifier})")
        
        # Check conversations
        if links.exists():
            conversation_ids = links.values_list('conversation_id', flat=True)
            conversations = Conversation.objects.filter(id__in=conversation_ids)
            print(f"\n💬 Conversations: {conversations.count()}")
            for conv in conversations[:5]:
                print(f"   {conv.subject or 'No subject'} ({conv.message_count} messages)")
        
        # Check sync jobs
        jobs = RecordSyncJob.objects.filter(record=record).order_by('-created_at')
        print(f"\n📋 Sync Jobs: {jobs.count()}")
        for job in jobs[:3]:
            print(f"   {job.created_at}: {job.status} - {job.messages_found} messages")


def main():
    """Main test function"""
    print("\n🚀 Testing Record-Level Sync for Saul Chilchik")
    print("=" * 70)
    
    # Find Saul's record
    tenant, record = find_saul_record()
    
    if not tenant:
        print("\n❌ Cannot proceed without tenant")
        return
    
    if not record:
        print("\n⚠️  Cannot find Saul Chilchik's record")
        print("Would you like to list all records to find the correct one?")
        return
    
    # Check available connections
    connections = check_channel_connections(tenant)
    
    if not connections.exists():
        print("\n❌ No active channel connections found")
        return
    
    # Run sync
    print("\n" + "=" * 70)
    sync_job = sync_record(tenant, record)
    
    # Check results
    if sync_job:
        check_sync_results(tenant, record)
    
    print("\n" + "=" * 70)
    print("✅ Test completed!")


if __name__ == '__main__':
    main()