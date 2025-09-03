"""
Management command to clean up duplicate email messages
Identifies emails stored with both Gmail Message-ID and UniPile ID
Keeps the UniPile ID version and removes the Gmail Message-ID version
"""
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q, Count
from django_tenants.utils import schema_context
from communications.models import Message, Conversation
from tenants.models import Tenant

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up duplicate email messages caused by webhook/sync using different IDs'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Specific tenant schema to clean up',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of duplicates to process (default: 100)',
        )
    
    def handle(self, *args, **options):
        tenant_schema = options.get('tenant')
        dry_run = options.get('dry_run', False)
        limit = options.get('limit', 100)
        
        if tenant_schema:
            tenants = [tenant_schema]
        else:
            # Get all tenant schemas
            tenants = Tenant.objects.exclude(schema_name='public').values_list('schema_name', flat=True)
        
        total_duplicates_found = 0
        total_duplicates_removed = 0
        
        for tenant in tenants:
            self.stdout.write(f"\nProcessing tenant: {tenant}")
            
            with schema_context(tenant):
                duplicates_found, duplicates_removed = self._clean_tenant_duplicates(
                    tenant, dry_run, limit
                )
                total_duplicates_found += duplicates_found
                total_duplicates_removed += duplicates_removed
        
        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"SUMMARY:"))
        self.stdout.write(f"Total duplicates found: {total_duplicates_found}")
        if dry_run:
            self.stdout.write(f"Total duplicates that would be removed: {total_duplicates_removed}")
            self.stdout.write(self.style.WARNING("This was a dry run - no messages were actually deleted"))
        else:
            self.stdout.write(f"Total duplicates removed: {total_duplicates_removed}")
    
    def _clean_tenant_duplicates(self, tenant, dry_run, limit):
        """Clean duplicates for a specific tenant"""
        duplicates_found = 0
        duplicates_removed = 0
        
        # Find messages that look like Gmail Message-IDs (start with < and end with >)
        gmail_id_messages = Message.objects.filter(
            external_message_id__startswith='<',
            external_message_id__endswith='>'
        )
        
        self.stdout.write(f"  Found {gmail_id_messages.count()} messages with Gmail Message-ID format")
        
        processed = 0
        for gmail_msg in gmail_id_messages[:limit]:
            if processed >= limit:
                break
                
            # Extract the Gmail Message-ID
            gmail_id = gmail_msg.external_message_id
            
            # Look for a duplicate with UniPile ID format
            # Check if this Gmail ID appears in any message's metadata
            unipile_msg = None
            
            # Check messages in the same conversation
            if gmail_msg.conversation:
                potential_duplicates = Message.objects.filter(
                    conversation=gmail_msg.conversation,
                    content=gmail_msg.content,
                    direction=gmail_msg.direction
                ).exclude(
                    external_message_id__startswith='<'  # Exclude other Gmail IDs
                ).exclude(
                    id=gmail_msg.id  # Exclude self
                )
                
                # Check if any have the Gmail ID in their metadata
                for msg in potential_duplicates:
                    if msg.metadata:
                        # Check various possible locations for the Gmail Message-ID
                        stored_gmail_id = (
                            msg.metadata.get('message_id') or
                            msg.metadata.get('gmail_message_id') or
                            (msg.metadata.get('unipile_data', {}).get('message_id') if 'unipile_data' in msg.metadata else None)
                        )
                        
                        if stored_gmail_id == gmail_id:
                            unipile_msg = msg
                            break
            
            if unipile_msg:
                duplicates_found += 1
                self.stdout.write(f"\n  Duplicate found:")
                self.stdout.write(f"    Gmail ID version: {gmail_msg.external_message_id[:50]}...")
                self.stdout.write(f"    UniPile ID version: {unipile_msg.external_message_id}")
                self.stdout.write(f"    Content: {gmail_msg.content[:50]}...")
                self.stdout.write(f"    Created: Gmail={gmail_msg.created_at}, UniPile={unipile_msg.created_at}")
                
                # Determine which to keep (prefer the one created by sync, which has more complete metadata)
                if not dry_run:
                    # Generally, the UniPile ID version has more complete metadata
                    # Delete the Gmail Message-ID version
                    with transaction.atomic():
                        gmail_msg.delete()
                        duplicates_removed += 1
                        self.stdout.write(self.style.SUCCESS(f"    ✓ Removed Gmail ID version"))
                else:
                    duplicates_removed += 1
                    self.stdout.write(self.style.WARNING(f"    [DRY RUN] Would remove Gmail ID version"))
            
            processed += 1
        
        if processed >= limit:
            self.stdout.write(self.style.WARNING(f"  Reached limit of {limit} messages"))
        
        return duplicates_found, duplicates_removed