#!/usr/bin/env python
"""
Script to remove all saved WhatsApp data from the system
This will delete all WhatsApp conversations, messages, and related data
"""
import os
import sys
import django

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import transaction
from django_tenants.utils import schema_context, get_tenant_model
from communications.models import (
    Conversation, Message, ConversationParticipant, 
    Participant, Channel, SyncJob, SyncJobProgress
)

def remove_whatsapp_data_for_tenant(tenant):
    """Remove all WhatsApp data for a specific tenant"""
    with schema_context(tenant.schema_name):
        print(f"\n🔍 Processing tenant: {tenant.schema_name}")
        
        # Get WhatsApp channels
        whatsapp_channels = Channel.objects.filter(channel_type='whatsapp')
        channel_count = whatsapp_channels.count()
        
        if channel_count == 0:
            print(f"  ℹ️  No WhatsApp channels found")
            return
        
        print(f"  📱 Found {channel_count} WhatsApp channel(s)")
        
        # Count data before deletion
        conversations = Conversation.objects.filter(channel__in=whatsapp_channels)
        conv_count = conversations.count()
        
        messages = Message.objects.filter(conversation__channel__in=whatsapp_channels)
        msg_count = messages.count()
        
        sync_jobs = SyncJob.objects.filter(channel__in=whatsapp_channels)
        sync_count = sync_jobs.count()
        
        print(f"  📊 Data to remove:")
        print(f"     - Conversations: {conv_count}")
        print(f"     - Messages: {msg_count}")
        print(f"     - Sync Jobs: {sync_count}")
        
        if conv_count == 0 and msg_count == 0 and sync_count == 0:
            print(f"  ✅ No WhatsApp data to remove")
            return
        
        # Confirm deletion
        if input(f"  ⚠️  Delete all WhatsApp data for {tenant.schema_name}? (y/N): ").lower() != 'y':
            print(f"  ⏭️  Skipped")
            return
        
        with transaction.atomic():
            # Delete sync job progress first
            progress_deleted = SyncJobProgress.objects.filter(sync_job__in=sync_jobs).delete()
            print(f"  🗑️  Deleted {progress_deleted[0]} sync job progress records")
            
            # Delete sync jobs
            sync_deleted = sync_jobs.delete()
            print(f"  🗑️  Deleted {sync_deleted[0]} sync jobs")
            
            # Delete messages
            msg_deleted = messages.delete()
            print(f"  🗑️  Deleted {msg_deleted[0]} messages")
            
            # Delete conversation participants
            conv_participants = ConversationParticipant.objects.filter(
                conversation__in=conversations
            )
            cp_deleted = conv_participants.delete()
            print(f"  🗑️  Deleted {cp_deleted[0]} conversation participants")
            
            # Delete conversations
            conv_deleted = conversations.delete()
            print(f"  🗑️  Deleted {conv_deleted[0]} conversations")
            
            # Clean up orphaned participants (WhatsApp specific)
            orphaned_participants = Participant.objects.filter(
                channel__in=whatsapp_channels,
                conversation_participants__isnull=True
            )
            orphan_count = orphaned_participants.count()
            if orphan_count > 0:
                orphan_deleted = orphaned_participants.delete()
                print(f"  🗑️  Deleted {orphan_deleted[0]} orphaned participants")
            
            print(f"  ✅ WhatsApp data removed successfully for {tenant.schema_name}")

def main():
    """Main function to remove WhatsApp data from all tenants"""
    print("=" * 60)
    print("🧹 WhatsApp Data Removal Script")
    print("=" * 60)
    print("\nThis script will remove ALL saved WhatsApp data including:")
    print("  • Conversations")
    print("  • Messages") 
    print("  • Sync Jobs")
    print("  • Participants")
    print("\n⚠️  This action cannot be undone!")
    print("=" * 60)
    
    # Get confirmation
    if input("\n🔴 Are you sure you want to proceed? Type 'DELETE' to confirm: ") != 'DELETE':
        print("❌ Aborted")
        return
    
    # Get all tenants
    Tenant = get_tenant_model()
    tenants = Tenant.objects.all()
    
    print(f"\n📋 Found {tenants.count()} tenant(s)")
    
    total_stats = {
        'conversations': 0,
        'messages': 0,
        'sync_jobs': 0,
        'tenants_processed': 0
    }
    
    # Process each tenant
    for tenant in tenants:
        try:
            with schema_context(tenant.schema_name):
                # Count before processing
                whatsapp_channels = Channel.objects.filter(channel_type='whatsapp')
                if whatsapp_channels.exists():
                    conversations = Conversation.objects.filter(channel__in=whatsapp_channels)
                    messages = Message.objects.filter(conversation__channel__in=whatsapp_channels)
                    sync_jobs = SyncJob.objects.filter(channel__in=whatsapp_channels)
                    
                    total_stats['conversations'] += conversations.count()
                    total_stats['messages'] += messages.count()
                    total_stats['sync_jobs'] += sync_jobs.count()
                    
            # Remove data
            remove_whatsapp_data_for_tenant(tenant)
            total_stats['tenants_processed'] += 1
            
        except Exception as e:
            print(f"  ❌ Error processing tenant {tenant.schema_name}: {e}")
            continue
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    print(f"  Tenants processed: {total_stats['tenants_processed']}")
    print(f"  Total conversations removed: {total_stats['conversations']}")
    print(f"  Total messages removed: {total_stats['messages']}")
    print(f"  Total sync jobs removed: {total_stats['sync_jobs']}")
    print("\n✅ WhatsApp data removal complete!")
    
    # Clear any Redis cache related to WhatsApp
    try:
        from django.core.cache import cache
        from django.core.cache import caches
        
        # Try to clear WhatsApp-related cache keys
        cache_cleared = 0
        for cache_name in caches:
            try:
                cache_instance = caches[cache_name]
                # Clear pattern-based if Redis backend
                if hasattr(cache_instance, '_cache'):
                    client = cache_instance._cache.get_client()
                    for key in client.scan_iter("*whatsapp*"):
                        client.delete(key)
                        cache_cleared += 1
            except:
                pass
        
        if cache_cleared > 0:
            print(f"\n🗑️  Cleared {cache_cleared} WhatsApp cache entries")
    except:
        pass

if __name__ == '__main__':
    main()