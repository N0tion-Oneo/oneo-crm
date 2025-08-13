"""
Management command to clean up expired shared records and related data.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q, Count
from datetime import timedelta
from django_tenants.utils import schema_context
from tenants.models import Tenant
from sharing.models import SharedRecord, SharedRecordAccess
from core.models import AuditLog
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up expired shared records and related data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days after expiration to keep records (default: 30)',
        )
        parser.add_argument(
            '--tenant',
            type=str,
            help='Only clean up records for specific tenant schema',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of records to process in each batch (default: 100)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        grace_days = options['days']
        target_tenant = options['tenant']
        batch_size = options['batch_size']
        verbose = options['verbose']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No records will be deleted')
            )

        # Calculate cutoff date (expired + grace period)
        cutoff_date = timezone.now() - timedelta(days=grace_days)
        
        self.stdout.write(
            f'Cleaning up shared records expired before: {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}'
        )

        # Get tenants to process
        if target_tenant:
            try:
                tenants = [Tenant.objects.get(schema_name=target_tenant)]
            except Tenant.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Tenant "{target_tenant}" does not exist')
                )
                return
        else:
            tenants = Tenant.objects.exclude(schema_name='public')

        total_deleted = {
            'shared_records': 0,
            'access_logs': 0,
            'audit_logs': 0
        }

        for tenant in tenants:
            self.stdout.write(f'\nProcessing tenant: {tenant.schema_name}')
            
            with schema_context(tenant.schema_name):
                tenant_deleted = self._cleanup_tenant_data(
                    cutoff_date, batch_size, dry_run, verbose
                )
                
                for key, value in tenant_deleted.items():
                    total_deleted[key] += value

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write('CLEANUP SUMMARY')
        self.stdout.write('='*50)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - Would delete:'))
        else:
            self.stdout.write(self.style.SUCCESS('Successfully deleted:'))
            
        self.stdout.write(f'Shared Records: {total_deleted["shared_records"]}')
        self.stdout.write(f'Access Logs: {total_deleted["access_logs"]}')
        self.stdout.write(f'Audit Logs: {total_deleted["audit_logs"]}')

    def _cleanup_tenant_data(self, cutoff_date, batch_size, dry_run, verbose):
        """Clean up expired data for a single tenant."""
        deleted_counts = {
            'shared_records': 0,
            'access_logs': 0,
            'audit_logs': 0
        }

        # Find expired shared records
        expired_records = SharedRecord.objects.filter(
            Q(expires_at__lt=cutoff_date) | Q(expires_at__isnull=True, created_at__lt=cutoff_date)
        ).select_related('shared_record')

        total_expired = expired_records.count()
        
        if total_expired == 0:
            self.stdout.write('  No expired records found')
            return deleted_counts

        self.stdout.write(f'  Found {total_expired} expired shared records')

        # Process in batches
        processed = 0
        while processed < total_expired:
            batch = expired_records[processed:processed + batch_size]
            batch_records = list(batch)
            
            if not batch_records:
                break

            if verbose:
                self.stdout.write(f'  Processing batch {processed + 1}-{processed + len(batch_records)}')

            # Collect related data before deletion
            shared_record_ids = [sr.id for sr in batch_records]
            record_ids = [sr.shared_record.record.id for sr in batch_records if sr.shared_record]

            # Count related access logs
            access_logs_count = SharedRecordAccess.objects.filter(
                shared_record_id__in=shared_record_ids
            ).count()

            # Count related audit logs (sharing-related)
            audit_logs_count = AuditLog.objects.filter(
                record_id__in=record_ids,
                action__in=['share_created', 'external_access', 'share_revoked', 'shared_record_edit']
            ).count()

            if not dry_run:
                # Delete access logs first (foreign key constraint)
                access_deleted = SharedRecordAccess.objects.filter(
                    shared_record_id__in=shared_record_ids
                ).delete()[0]

                # Delete audit logs
                audit_deleted = AuditLog.objects.filter(
                    record_id__in=record_ids,
                    action__in=['share_created', 'external_access', 'share_revoked', 'shared_record_edit']
                ).delete()[0]

                # Delete shared records
                shared_deleted = SharedRecord.objects.filter(
                    id__in=shared_record_ids
                ).delete()[0]

                deleted_counts['access_logs'] += access_deleted
                deleted_counts['audit_logs'] += audit_deleted
                deleted_counts['shared_records'] += shared_deleted

                if verbose:
                    self.stdout.write(
                        f'    Deleted: {shared_deleted} shared records, '
                        f'{access_deleted} access logs, {audit_deleted} audit logs'
                    )
            else:
                # Dry run - just count
                deleted_counts['access_logs'] += access_logs_count
                deleted_counts['audit_logs'] += audit_logs_count
                deleted_counts['shared_records'] += len(batch_records)

                if verbose:
                    self.stdout.write(
                        f'    Would delete: {len(batch_records)} shared records, '
                        f'{access_logs_count} access logs, {audit_logs_count} audit logs'
                    )

            processed += len(batch_records)

        return deleted_counts