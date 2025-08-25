#!/usr/bin/env python
"""
Delete WhatsApp Chat, Message, and Attendee Data
Safely removes all WhatsApp communication data for a clean slate
"""
import os
import sys
import django
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.utils import timezone
from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from django.db import transaction
from communications.models import (
    Channel, Conversation, Message, ChatAttendee, ConversationAttendee,
    SyncJob, SyncJobProgress, UserChannelConnection
)

User = get_user_model()


def delete_whatsapp_data():
    """Delete all WhatsApp chat, message, and attendee data for oneotalent"""
    print("\n" + "=" * 60)
    print("WhatsApp Data Deletion - OneOTalent")
    print("=" * 60)
    
    # Use oneotalent tenant context
    with schema_context('oneotalent'):
        print("\n⚠️  WARNING: This will delete all WhatsApp data!")
        print("   - All conversations/chats")
        print("   - All messages")
        print("   - All attendees/contacts")
        print("   - All sync job history")
        
        # Get user confirmation
        confirmation = input("\n❓ Are you sure you want to proceed? Type 'DELETE' to confirm: ")
        if confirmation != 'DELETE':
            print("❌ Deletion cancelled")
            return
        
        print("\n🔍 Finding WhatsApp channels...")
        
        # Get all WhatsApp channels
        channels = Channel.objects.filter(channel_type='whatsapp')
        
        if not channels.exists():
            print("❌ No WhatsApp channels found")
            return
        
        print(f"✅ Found {channels.count()} WhatsApp channel(s)")
        
        for channel in channels:
            print(f"\n📡 Processing channel: {channel.name}")
            print(f"   ID: {channel.id}")
            print(f"   UniPile Account: {channel.unipile_account_id}")
            
            # Count existing data
            conversations_count = Conversation.objects.filter(channel=channel).count()
            messages_count = Message.objects.filter(channel=channel).count()
            attendees_count = ChatAttendee.objects.filter(channel=channel).count()
            sync_jobs_count = SyncJob.objects.filter(channel=channel).count()
            
            print(f"\n📊 Current data for channel '{channel.name}':")
            print(f"   Conversations: {conversations_count}")
            print(f"   Messages: {messages_count}")
            print(f"   Attendees: {attendees_count}")
            print(f"   Sync Jobs: {sync_jobs_count}")
            
            if conversations_count == 0 and messages_count == 0 and attendees_count == 0:
                print("   ℹ️  No data to delete")
                continue
            
            print(f"\n🗑️  Deleting data for channel '{channel.name}'...")
            
            with transaction.atomic():
                # Delete in order to respect foreign key constraints
                
                # 1. Delete ConversationAttendee junction records first
                conversation_attendees = ConversationAttendee.objects.filter(
                    conversation__channel=channel
                )
                ca_count = conversation_attendees.count()
                conversation_attendees.delete()
                print(f"   ✅ Deleted {ca_count} conversation-attendee links")
                
                # 2. Delete Messages
                messages = Message.objects.filter(channel=channel)
                msg_count = messages.count()
                messages.delete()
                print(f"   ✅ Deleted {msg_count} messages")
                
                # 3. Delete Conversations
                conversations = Conversation.objects.filter(channel=channel)
                conv_count = conversations.count()
                conversations.delete()
                print(f"   ✅ Deleted {conv_count} conversations")
                
                # 4. Delete ChatAttendees
                attendees = ChatAttendee.objects.filter(channel=channel)
                att_count = attendees.count()
                attendees.delete()
                print(f"   ✅ Deleted {att_count} attendees")
                
                # 5. Delete SyncJobProgress records
                sync_progress = SyncJobProgress.objects.filter(
                    sync_job__channel=channel
                )
                sp_count = sync_progress.count()
                sync_progress.delete()
                print(f"   ✅ Deleted {sp_count} sync progress records")
                
                # 6. Delete SyncJobs
                sync_jobs = SyncJob.objects.filter(channel=channel)
                sj_count = sync_jobs.count()
                sync_jobs.delete()
                print(f"   ✅ Deleted {sj_count} sync jobs")
                
                # Reset channel statistics
                channel.message_count = 0
                channel.last_message_at = None
                channel.last_sync_at = None
                channel.save()
                print(f"   ✅ Reset channel statistics")
            
            print(f"\n✅ Successfully deleted all data for channel '{channel.name}'")
            
            # Verify deletion
            print(f"\n🔍 Verifying deletion for channel '{channel.name}':")
            print(f"   Conversations remaining: {Conversation.objects.filter(channel=channel).count()}")
            print(f"   Messages remaining: {Message.objects.filter(channel=channel).count()}")
            print(f"   Attendees remaining: {ChatAttendee.objects.filter(channel=channel).count()}")
            print(f"   Sync Jobs remaining: {SyncJob.objects.filter(channel=channel).count()}")
        
        print("\n" + "=" * 60)
        print("✅ Data deletion complete!")
        print("=" * 60)
        
        # Show summary
        print("\n📊 Final Summary:")
        for channel in channels:
            print(f"\n   Channel: {channel.name}")
            print(f"   - Conversations: {Conversation.objects.filter(channel=channel).count()}")
            print(f"   - Messages: {Message.objects.filter(channel=channel).count()}")
            print(f"   - Attendees: {ChatAttendee.objects.filter(channel=channel).count()}")
            print(f"   - Sync Jobs: {SyncJob.objects.filter(channel=channel).count()}")
        
        print("\n💡 Next steps:")
        print("   1. You can now run a fresh sync to repopulate data")
        print("   2. Use the background sync API to import messages")
        print("   3. Or test with clean/empty state")


def check_user_permissions():
    """Check if the user has permission to delete data"""
    with schema_context('oneotalent'):
        print("\n🔐 Checking permissions...")
        
        # Get admin user
        try:
            user = User.objects.get(email='josh@oneodigital.com')
            print(f"✅ Authenticated as: {user.email}")
            
            # Check if user is superuser or has admin permissions
            if user.is_superuser:
                print("   ✅ Superuser privileges confirmed")
                return True
            elif user.is_staff:
                print("   ✅ Staff privileges confirmed")
                return True
            else:
                print("   ⚠️  Warning: User may not have full deletion permissions")
                response = input("   Continue anyway? (y/n): ")
                return response.lower() == 'y'
        except User.DoesNotExist:
            print("❌ User not found")
            return False


def main():
    """Run the deletion process"""
    try:
        # Check permissions first
        if not check_user_permissions():
            print("\n❌ Deletion aborted: Insufficient permissions")
            sys.exit(1)
        
        # Run the deletion
        delete_whatsapp_data()
        
    except KeyboardInterrupt:
        print("\n\n❌ Deletion cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during deletion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()