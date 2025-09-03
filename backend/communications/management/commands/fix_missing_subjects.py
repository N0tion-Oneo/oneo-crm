"""
Management command to fix email messages that are missing subject field
Extracts subject from metadata where available
"""
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context
from communications.models import Message
from tenants.models import Tenant

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fix email messages that are missing subject field by extracting from metadata'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Specific tenant schema to fix',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without actually updating',
        )
    
    def handle(self, *args, **options):
        tenant_schema = options.get('tenant')
        dry_run = options.get('dry_run', False)
        
        if tenant_schema:
            tenants = [tenant_schema]
        else:
            # Get all tenant schemas
            tenants = Tenant.objects.exclude(schema_name='public').values_list('schema_name', flat=True)
        
        total_missing = 0
        total_fixed = 0
        
        for tenant in tenants:
            self.stdout.write(f"\nProcessing tenant: {tenant}")
            
            with schema_context(tenant):
                missing, fixed = self._fix_tenant_subjects(tenant, dry_run)
                total_missing += missing
                total_fixed += fixed
        
        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"SUMMARY:"))
        self.stdout.write(f"Total messages with missing subjects: {total_missing}")
        if dry_run:
            self.stdout.write(f"Total that would be fixed: {total_fixed}")
            self.stdout.write(self.style.WARNING("This was a dry run - no messages were actually updated"))
        else:
            self.stdout.write(f"Total messages fixed: {total_fixed}")
    
    def _fix_tenant_subjects(self, tenant, dry_run):
        """Fix missing subjects for a specific tenant"""
        # Find email messages without subjects
        missing_subjects = Message.objects.filter(
            conversation__channel__channel_type__in=['gmail', 'outlook', 'email'],
            subject__isnull=True
        ) | Message.objects.filter(
            conversation__channel__channel_type__in=['gmail', 'outlook', 'email'],
            subject=''
        )
        
        missing_count = missing_subjects.count()
        fixed_count = 0
        
        self.stdout.write(f"  Found {missing_count} email messages without subjects")
        
        if missing_count == 0:
            return 0, 0
        
        with transaction.atomic():
            for msg in missing_subjects:
                subject = None
                
                if msg.metadata:
                    # Try multiple locations in metadata
                    if 'unipile_data' in msg.metadata:
                        subject = msg.metadata['unipile_data'].get('subject')
                    
                    if not subject and 'subject' in msg.metadata:
                        subject = msg.metadata['subject']
                    
                    if not subject and 'raw_webhook_data' in msg.metadata:
                        subject = msg.metadata['raw_webhook_data'].get('subject')
                
                if subject:
                    if not dry_run:
                        msg.subject = subject[:500]  # Truncate to field max length
                        msg.save(update_fields=['subject'])
                        fixed_count += 1
                        
                        if fixed_count <= 5:  # Show first 5 as examples
                            self.stdout.write(
                                self.style.SUCCESS(f"    ✓ Fixed: {subject[:50]}...")
                            )
                    else:
                        fixed_count += 1
                        if fixed_count <= 5:
                            self.stdout.write(
                                self.style.WARNING(f"    [DRY RUN] Would fix: {subject[:50]}...")
                            )
        
        percentage = (fixed_count / missing_count * 100) if missing_count > 0 else 0
        self.stdout.write(f"  Fixed {fixed_count}/{missing_count} messages ({percentage:.1f}%)")
        
        return missing_count, fixed_count