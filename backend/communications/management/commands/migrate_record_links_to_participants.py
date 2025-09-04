"""
Management command to migrate RecordCommunicationLink data to participant-based links

This command migrates existing RecordCommunicationLink records to the new
participant-based linking system where participants are directly linked to records.
"""
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context, get_tenant_model
from django.utils import timezone

from communications.models import Participant, ConversationParticipant
from communications.record_communications.models import RecordCommunicationLink
from communications.record_communications.storage.participant_link_manager import ParticipantLinkManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate RecordCommunicationLink data to participant-based links'
    
    def __init__(self):
        super().__init__()
        self.link_manager = ParticipantLinkManager()
        
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run the migration without making changes'
        )
        parser.add_argument(
            '--tenant',
            type=str,
            help='Specific tenant schema to migrate (default: all tenants)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of links to process in each batch'
        )
        
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        specific_tenant = options.get('tenant')
        batch_size = options.get('batch_size', 100)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get tenants to process
        Tenant = get_tenant_model()
        if specific_tenant:
            tenants = Tenant.objects.filter(schema_name=specific_tenant)
            if not tenants.exists():
                self.stdout.write(self.style.ERROR(f'Tenant {specific_tenant} not found'))
                return
        else:
            tenants = Tenant.objects.exclude(schema_name='public')
        
        total_migrated = 0
        total_failed = 0
        
        for tenant in tenants:
            self.stdout.write(f'\nProcessing tenant: {tenant.schema_name}')
            
            with schema_context(tenant.schema_name):
                migrated, failed = self._migrate_tenant_links(dry_run, batch_size)
                total_migrated += migrated
                total_failed += failed
                
                self.stdout.write(
                    self.style.SUCCESS(f'  Migrated: {migrated} links')
                )
                if failed > 0:
                    self.stdout.write(
                        self.style.WARNING(f'  Failed: {failed} links')
                    )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Total links migrated: {total_migrated}'))
        if total_failed > 0:
            self.stdout.write(self.style.WARNING(f'Total links failed: {total_failed}'))
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS('\nMigration completed successfully!'))
            self.stdout.write('\nNext steps:')
            self.stdout.write('1. Verify the migration by checking participant links')
            self.stdout.write('2. Run tests to ensure functionality')
            self.stdout.write('3. Create and run migration to remove RecordCommunicationLink model')
    
    def _migrate_tenant_links(self, dry_run, batch_size):
        """Migrate links for a single tenant"""
        migrated = 0
        failed = 0
        
        # Get all RecordCommunicationLink records
        links = RecordCommunicationLink.objects.select_related(
            'record', 'conversation', 'participant'
        ).order_by('created_at')
        
        total = links.count()
        self.stdout.write(f'  Found {total} RecordCommunicationLink records')
        
        # Process in batches
        for i in range(0, total, batch_size):
            batch = links[i:i+batch_size]
            
            for link in batch:
                try:
                    if self._migrate_single_link(link, dry_run):
                        migrated += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f'Error migrating link {link.id}: {e}')
                    failed += 1
            
            # Progress indicator
            processed = min(i + batch_size, total)
            self.stdout.write(f'  Processed {processed}/{total} links...', ending='\r')
        
        return migrated, failed
    
    def _migrate_single_link(self, link, dry_run):
        """Migrate a single RecordCommunicationLink to participant-based link"""
        try:
            # If link has a participant, use that
            if link.participant:
                participant = link.participant
            else:
                # Find participant based on the conversation and identifier
                participants = self._find_participants_for_link(link)
                
                if not participants:
                    logger.warning(
                        f'No participant found for link {link.id} '
                        f'(conversation: {link.conversation_id}, identifier: {link.match_identifier})'
                    )
                    return False
                
                # Use the first matching participant
                participant = participants[0]
            
            # Check if participant is already linked to a record
            if participant.contact_record_id:
                if participant.contact_record_id != link.record_id:
                    logger.warning(
                        f'Participant {participant.id} already linked to different record '
                        f'(current: {participant.contact_record_id}, link: {link.record_id})'
                    )
                return True  # Already migrated
            
            # Link the participant to the record
            if not dry_run:
                with transaction.atomic():
                    self.link_manager.link_participant_to_record(
                        participant=participant,
                        record=link.record,
                        confidence=link.confidence_score,
                        method=f'migration_{link.match_type}'
                    )
                    
                    logger.info(
                        f'Migrated link {link.id}: participant {participant.id} -> record {link.record_id}'
                    )
            
            return True
            
        except Exception as e:
            logger.error(f'Failed to migrate link {link.id}: {e}')
            return False
    
    def _find_participants_for_link(self, link):
        """Find participants that match the link's criteria"""
        # Get all participants in the conversation
        conversation_participants = ConversationParticipant.objects.filter(
            conversation=link.conversation
        ).select_related('participant')
        
        participants = [cp.participant for cp in conversation_participants]
        
        # Filter by match identifier and type
        matching = []
        for participant in participants:
            if link.match_type == 'email' and participant.email == link.match_identifier:
                matching.append(participant)
            elif link.match_type == 'phone' and participant.phone == link.match_identifier:
                matching.append(participant)
            elif link.match_type == 'linkedin' and participant.linkedin_member_urn == link.match_identifier:
                matching.append(participant)
            elif link.match_type == 'domain' and participant.email:
                if '@' in participant.email:
                    domain = participant.email.split('@')[1]
                    if domain == link.match_identifier:
                        matching.append(participant)
        
        return matching