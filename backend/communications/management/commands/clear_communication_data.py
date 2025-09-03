"""
Management command to clear all communication data for fresh sync
"""
import logging
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clear all communication data to allow for a fresh sync'

    def add_arguments(self, parser):
        parser.add_argument(
            '--record-id',
            type=int,
            help='Clear data only for a specific record ID'
        )
        parser.add_argument(
            '--pipeline-id',
            type=int,
            help='Clear data only for records in a specific pipeline'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt'
        )
        parser.add_argument(
            '--keep-profiles',
            action='store_true',
            help='Keep communication profiles (only clear messages/conversations)'
        )
        parser.add_argument(
            '--clear-sync-jobs',
            action='store_true',
            default=True,
            help='Also clear sync job history (default: True)'
        )

    def handle(self, *args, **options):
        record_id = options.get('record_id')
        pipeline_id = options.get('pipeline_id')
        confirm = options.get('confirm')
        keep_profiles = options.get('keep_profiles')
        clear_sync_jobs = options.get('clear_sync_jobs')
        
        # Import models here to ensure they're loaded
        from communications.models import (
            Conversation, Message, Participant, 
            ConversationParticipant, Channel,
            UserChannelConnection
        )
        from communications.record_communications.models import (
            RecordCommunicationProfile,
            RecordCommunicationLink,
            RecordSyncJob,
            RecordAttendeeMapping
        )
        from pipelines.models import Record
        
        # Determine scope
        if record_id:
            scope_msg = f"for record {record_id}"
            try:
                record = Record.objects.get(id=record_id)
                self.stdout.write(f"Found record: {record}")
            except Record.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Record {record_id} not found"))
                return
        elif pipeline_id:
            scope_msg = f"for all records in pipeline {pipeline_id}"
            record_count = Record.objects.filter(pipeline_id=pipeline_id).count()
            self.stdout.write(f"Found {record_count} records in pipeline {pipeline_id}")
        else:
            scope_msg = "for ALL records in the system"
            total_records = Record.objects.count()
            self.stdout.write(self.style.WARNING(f"This will affect {total_records} records"))
        
        # Get current counts
        self.stdout.write("\n" + "="*50)
        self.stdout.write("CURRENT DATA COUNTS:")
        self.stdout.write("="*50)
        
        # Build filters based on scope
        if record_id:
            # Get conversations linked to this record
            conversation_ids = RecordCommunicationLink.objects.filter(
                record_id=record_id
            ).values_list('conversation_id', flat=True)
            
            conversations_count = len(conversation_ids)
            messages_count = Message.objects.filter(conversation_id__in=conversation_ids).count()
            links_count = RecordCommunicationLink.objects.filter(record_id=record_id).count()
            profiles_count = RecordCommunicationProfile.objects.filter(record_id=record_id).count()
            sync_jobs_count = RecordSyncJob.objects.filter(record_id=record_id).count()
            attendee_mappings_count = RecordAttendeeMapping.objects.filter(record_id=record_id).count()
            
        elif pipeline_id:
            record_ids = Record.objects.filter(pipeline_id=pipeline_id).values_list('id', flat=True)
            conversation_ids = RecordCommunicationLink.objects.filter(
                record_id__in=record_ids
            ).values_list('conversation_id', flat=True).distinct()
            
            conversations_count = len(conversation_ids)
            messages_count = Message.objects.filter(conversation_id__in=conversation_ids).count()
            links_count = RecordCommunicationLink.objects.filter(record_id__in=record_ids).count()
            profiles_count = RecordCommunicationProfile.objects.filter(record_id__in=record_ids).count()
            sync_jobs_count = RecordSyncJob.objects.filter(record_id__in=record_ids).count()
            attendee_mappings_count = RecordAttendeeMapping.objects.filter(record_id__in=record_ids).count()
            
        else:
            conversations_count = Conversation.objects.count()
            messages_count = Message.objects.count()
            links_count = RecordCommunicationLink.objects.count()
            profiles_count = RecordCommunicationProfile.objects.count()
            sync_jobs_count = RecordSyncJob.objects.count()
            attendee_mappings_count = RecordAttendeeMapping.objects.count()
        
        self.stdout.write(f"Conversations: {conversations_count}")
        self.stdout.write(f"Messages: {messages_count}")
        self.stdout.write(f"Record Links: {links_count}")
        self.stdout.write(f"Communication Profiles: {profiles_count}")
        self.stdout.write(f"Sync Jobs: {sync_jobs_count}")
        self.stdout.write(f"Attendee Mappings: {attendee_mappings_count}")
        
        if not any([conversations_count, messages_count, links_count, 
                   profiles_count, sync_jobs_count, attendee_mappings_count]):
            self.stdout.write(self.style.SUCCESS("\nNo communication data to clear."))
            return
        
        # Confirmation
        if not confirm:
            self.stdout.write("\n" + "="*50)
            self.stdout.write(self.style.WARNING(f"WARNING: This will DELETE communication data {scope_msg}"))
            self.stdout.write("="*50)
            
            self.stdout.write("\nData to be deleted:")
            self.stdout.write(f"  - {messages_count} messages")
            self.stdout.write(f"  - {conversations_count} conversations")
            self.stdout.write(f"  - {links_count} record-conversation links")
            self.stdout.write(f"  - {attendee_mappings_count} attendee mappings")
            if clear_sync_jobs:
                self.stdout.write(f"  - {sync_jobs_count} sync job records")
            if not keep_profiles:
                self.stdout.write(f"  - {profiles_count} communication profiles")
            
            response = input("\nAre you sure you want to proceed? Type 'yes' to confirm: ")
            if response.lower() != 'yes':
                self.stdout.write(self.style.ERROR("Operation cancelled."))
                return
        
        # Perform deletion
        self.stdout.write("\n" + "="*50)
        self.stdout.write("CLEARING DATA...")
        self.stdout.write("="*50)
        
        try:
            with transaction.atomic():
                # Delete messages first (foreign key constraints)
                if record_id or pipeline_id:
                    deleted = Message.objects.filter(conversation_id__in=conversation_ids).delete()
                    self.stdout.write(f"✓ Deleted {deleted[0]} messages")
                else:
                    deleted = Message.objects.all().delete()
                    self.stdout.write(f"✓ Deleted {deleted[0]} messages")
                
                # Delete conversation participants
                if record_id or pipeline_id:
                    deleted = ConversationParticipant.objects.filter(conversation_id__in=conversation_ids).delete()
                    self.stdout.write(f"✓ Deleted {deleted[0]} conversation participants")
                else:
                    deleted = ConversationParticipant.objects.all().delete()
                    self.stdout.write(f"✓ Deleted {deleted[0]} conversation participants")
                
                # Delete record communication links
                if record_id:
                    deleted = RecordCommunicationLink.objects.filter(record_id=record_id).delete()
                elif pipeline_id:
                    deleted = RecordCommunicationLink.objects.filter(record_id__in=record_ids).delete()
                else:
                    deleted = RecordCommunicationLink.objects.all().delete()
                self.stdout.write(f"✓ Deleted {deleted[0]} record communication links")
                
                # Delete conversations
                if record_id or pipeline_id:
                    # Only delete conversations that are no longer linked to any records
                    orphaned_conversations = Conversation.objects.filter(
                        id__in=conversation_ids
                    ).exclude(
                        id__in=RecordCommunicationLink.objects.values_list('conversation_id', flat=True)
                    )
                    deleted = orphaned_conversations.delete()
                    self.stdout.write(f"✓ Deleted {deleted[0]} orphaned conversations")
                else:
                    deleted = Conversation.objects.all().delete()
                    self.stdout.write(f"✓ Deleted {deleted[0]} conversations")
                
                # Delete attendee mappings
                if record_id:
                    deleted = RecordAttendeeMapping.objects.filter(record_id=record_id).delete()
                elif pipeline_id:
                    deleted = RecordAttendeeMapping.objects.filter(record_id__in=record_ids).delete()
                else:
                    deleted = RecordAttendeeMapping.objects.all().delete()
                self.stdout.write(f"✓ Deleted {deleted[0]} attendee mappings")
                
                # Delete sync jobs if requested
                if clear_sync_jobs:
                    if record_id:
                        deleted = RecordSyncJob.objects.filter(record_id=record_id).delete()
                    elif pipeline_id:
                        deleted = RecordSyncJob.objects.filter(record_id__in=record_ids).delete()
                    else:
                        deleted = RecordSyncJob.objects.all().delete()
                    self.stdout.write(f"✓ Deleted {deleted[0]} sync jobs")
                
                # Handle communication profiles
                if not keep_profiles:
                    if record_id:
                        deleted = RecordCommunicationProfile.objects.filter(record_id=record_id).delete()
                    elif pipeline_id:
                        deleted = RecordCommunicationProfile.objects.filter(record_id__in=record_ids).delete()
                    else:
                        deleted = RecordCommunicationProfile.objects.all().delete()
                    self.stdout.write(f"✓ Deleted {deleted[0]} communication profiles")
                else:
                    # Reset profile sync status
                    if record_id:
                        profiles = RecordCommunicationProfile.objects.filter(record_id=record_id)
                    elif pipeline_id:
                        profiles = RecordCommunicationProfile.objects.filter(record_id__in=record_ids)
                    else:
                        profiles = RecordCommunicationProfile.objects.all()
                    
                    updated = profiles.update(
                        last_full_sync=None,
                        last_incremental_sync=None,
                        sync_in_progress=False,
                        total_messages=0,
                        total_conversations=0,
                        total_unread=0,
                        last_message_at=None
                    )
                    self.stdout.write(f"✓ Reset {updated} communication profiles")
                
                # Optional: Clear orphaned participants (not linked to any conversation)
                if not (record_id or pipeline_id):
                    orphaned_participants = Participant.objects.filter(
                        conversation_memberships__isnull=True,
                        sent_messages_new__isnull=True
                    )
                    deleted = orphaned_participants.delete()
                    if deleted[0] > 0:
                        self.stdout.write(f"✓ Deleted {deleted[0]} orphaned participants")
                
                self.stdout.write("\n" + "="*50)
                self.stdout.write(self.style.SUCCESS("✅ COMMUNICATION DATA CLEARED SUCCESSFULLY"))
                self.stdout.write("="*50)
                
                # Provide next steps
                self.stdout.write("\n📝 Next steps:")
                self.stdout.write("1. Run a fresh sync using the API or admin interface")
                self.stdout.write("2. Monitor sync jobs for completion")
                if record_id:
                    self.stdout.write(f"\nTo sync this record via API:")
                    self.stdout.write(f"POST /api/v1/records/{record_id}/communications/sync/")
                    self.stdout.write('{"force": true}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error clearing data: {str(e)}"))
            raise