"""
Management command to clean up expired relationship paths
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from relationships.models import RelationshipPath


class Command(BaseCommand):
    help = 'Clean up expired relationship paths'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--older-than-hours',
            type=int,
            default=0,
            help='Delete paths older than specified hours (in addition to expired ones)',
        )

    def handle(self, *args, **options):
        self.stdout.write('Cleaning up expired relationship paths...')
        
        try:
            # Find expired paths
            expired_paths = RelationshipPath.objects.filter(
                expires_at__lt=timezone.now()
            )
            
            # Find old paths if specified
            old_paths_query = RelationshipPath.objects.none()
            if options['older_than_hours'] > 0:
                cutoff_time = timezone.now() - timezone.timedelta(hours=options['older_than_hours'])
                old_paths_query = RelationshipPath.objects.filter(
                    computed_at__lt=cutoff_time
                )
            
            # Combine queries
            paths_to_delete = expired_paths.union(old_paths_query)
            total_count = paths_to_delete.count()
            
            if total_count == 0:
                self.stdout.write('No expired paths found to clean up')
                return
            
            if options['dry_run']:
                self.stdout.write(f'Would delete {total_count} expired/old paths:')
                for path in paths_to_delete[:10]:  # Show first 10
                    expired_status = "expired" if path.is_expired() else "old"
                    self.stdout.write(f'  - {path} ({expired_status})')
                if total_count > 10:
                    self.stdout.write(f'  ... and {total_count - 10} more')
            else:
                # Actually delete the paths
                deleted_count = paths_to_delete.delete()[0]
                self.stdout.write(
                    self.style.SUCCESS(f'Deleted {deleted_count} expired/old relationship paths')
                )
                
                # Show remaining paths
                remaining_count = RelationshipPath.objects.count()
                self.stdout.write(f'Remaining cached paths: {remaining_count}')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error cleaning up paths: {e}')
            )
            raise