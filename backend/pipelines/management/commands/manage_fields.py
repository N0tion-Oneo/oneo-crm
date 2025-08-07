"""
Management command for field operations
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from pipelines.models import Pipeline, Field
from pipelines.migrator import FieldSchemaMigrator
import json

User = get_user_model()


class Command(BaseCommand):
    help = 'Manage pipeline fields: soft delete, restore, hard delete, migrate schema'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['list', 'soft_delete', 'restore', 'schedule_hard_delete', 'migrate', 'impact_analysis'],
            help='Action to perform'
        )
        
        parser.add_argument(
            '--pipeline-id',
            type=int,
            help='Pipeline ID'
        )
        
        parser.add_argument(
            '--field-slug',
            type=str,
            help='Field slug'
        )
        
        parser.add_argument(
            '--admin-user',
            type=str,
            help='Admin username for operations'
        )
        
        parser.add_argument(
            '--reason',
            type=str,
            default='',
            help='Reason for deletion'
        )
        
        parser.add_argument(
            '--grace-days',
            type=int,
            default=7,
            help='Days before hard deletion (default: 7)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform dry run of migration'
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for migration (default: 100)'
        )
        
        parser.add_argument(
            '--include-deleted',
            action='store_true',
            help='Include soft deleted fields in listing'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        try:
            if action == 'list':
                self.list_fields(options)
            elif action == 'soft_delete':
                self.soft_delete_field(options)
            elif action == 'restore':
                self.restore_field(options)
            elif action == 'schedule_hard_delete':
                self.schedule_hard_delete(options)
            elif action == 'migrate':
                self.migrate_field_schema(options)
            elif action == 'impact_analysis':
                self.analyze_impact(options)
                
        except CommandError:
            raise
        except Exception as e:
            raise CommandError(f"Command failed: {str(e)}")

    def list_fields(self, options):
        """List fields in pipeline"""
        pipeline_id = options.get('pipeline_id')
        include_deleted = options.get('include_deleted')
        
        if pipeline_id:
            pipelines = Pipeline.objects.filter(id=pipeline_id)
        else:
            pipelines = Pipeline.objects.all()
        
        for pipeline in pipelines:
            self.stdout.write(f"\nPipeline: {pipeline.name} (ID: {pipeline.id})")
            self.stdout.write("-" * 50)
            
            if include_deleted:
                fields = pipeline.fields.with_deleted()
            else:
                fields = pipeline.fields.all()
            
            for field in fields.order_by('display_order', 'name'):
                status = "ACTIVE"
                if field.is_deleted:
                    status = "DELETED"
                    if field.scheduled_for_hard_delete:
                        status = f"SCHEDULED FOR HARD DELETE ({field.scheduled_for_hard_delete})"
                
                self.stdout.write(
                    f"  {field.slug:30} | {field.field_type:15} | {status}"
                )
                
                if field.is_deleted:
                    self.stdout.write(
                        f"    Deleted: {field.deleted_at} by {field.deleted_by}"
                    )

    def soft_delete_field(self, options):
        """Soft delete a field"""
        pipeline_id = options.get('pipeline_id')
        field_slug = options.get('field_slug')
        admin_username = options.get('admin_user')
        reason = options.get('reason')
        
        if not all([pipeline_id, field_slug, admin_username]):
            raise CommandError("--pipeline-id, --field-slug, and --admin-user are required")
        
        try:
            pipeline = Pipeline.objects.get(id=pipeline_id)
            field = pipeline.fields.with_deleted().get(slug=field_slug)
            admin_user = User.objects.get(username=admin_username)
        except Pipeline.DoesNotExist:
            raise CommandError(f"Pipeline {pipeline_id} not found")
        except Field.DoesNotExist:
            raise CommandError(f"Field {field_slug} not found in pipeline {pipeline_id}")
        except User.DoesNotExist:
            raise CommandError(f"Admin user {admin_username} not found")
        
        # Get impact analysis first
        impact = field.get_impact_analysis()
        
        self.stdout.write("\nField Deletion Impact Analysis:")
        self.stdout.write(f"  Records with data: {impact['records_with_data']}")
        self.stdout.write(f"  Risk level: {impact['risk_level']}")
        self.stdout.write(f"  Dependent systems: {len(impact['dependent_systems'])}")
        
        if impact['dependent_systems']:
            for dep in impact['dependent_systems']:
                self.stdout.write(f"    - {dep['system']}: {dep['count']} dependencies")
        
        # Perform soft delete
        success, message = field.soft_delete(admin_user, reason)
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(f"Field {field_slug} soft deleted successfully")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"Failed to soft delete field: {message}")
            )

    def restore_field(self, options):
        """Restore soft deleted field"""
        pipeline_id = options.get('pipeline_id')
        field_slug = options.get('field_slug')
        admin_username = options.get('admin_user')
        
        if not all([pipeline_id, field_slug, admin_username]):
            raise CommandError("--pipeline-id, --field-slug, and --admin-user are required")
        
        try:
            pipeline = Pipeline.objects.get(id=pipeline_id)
            field = pipeline.fields.with_deleted().get(slug=field_slug)
            admin_user = User.objects.get(username=admin_username)
        except Pipeline.DoesNotExist:
            raise CommandError(f"Pipeline {pipeline_id} not found")
        except Field.DoesNotExist:
            raise CommandError(f"Field {field_slug} not found in pipeline {pipeline_id}")
        except User.DoesNotExist:
            raise CommandError(f"Admin user {admin_username} not found")
        
        success, message = field.restore(admin_user)
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(f"Field {field_slug} restored successfully")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"Failed to restore field: {message}")
            )

    def schedule_hard_delete(self, options):
        """Schedule field for hard deletion"""
        pipeline_id = options.get('pipeline_id')
        field_slug = options.get('field_slug')
        admin_username = options.get('admin_user')
        reason = options.get('reason')
        grace_days = options.get('grace_days')
        
        if not all([pipeline_id, field_slug, admin_username, reason]):
            raise CommandError("--pipeline-id, --field-slug, --admin-user, and --reason are required")
        
        try:
            pipeline = Pipeline.objects.get(id=pipeline_id)
            field = pipeline.fields.with_deleted().get(slug=field_slug)
            admin_user = User.objects.get(username=admin_username)
        except Pipeline.DoesNotExist:
            raise CommandError(f"Pipeline {pipeline_id} not found")
        except Field.DoesNotExist:
            raise CommandError(f"Field {field_slug} not found in pipeline {pipeline_id}")
        except User.DoesNotExist:
            raise CommandError(f"Admin user {admin_username} not found")
        
        # Calculate delete date
        from datetime import timedelta
        delete_date = timezone.now() + timedelta(days=grace_days)
        
        success, message = field.schedule_hard_delete(admin_user, reason, delete_date)
        
        if success:
            self.stdout.write(
                self.style.WARNING(f"Field {field_slug} scheduled for hard deletion: {message}")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"Failed to schedule hard deletion: {message}")
            )

    def migrate_field_schema(self, options):
        """Migrate field schema changes"""
        pipeline_id = options.get('pipeline_id')
        dry_run = options.get('dry_run')
        batch_size = options.get('batch_size')
        
        if not pipeline_id:
            raise CommandError("--pipeline-id is required")
        
        try:
            pipeline = Pipeline.objects.get(id=pipeline_id)
        except Pipeline.DoesNotExist:
            raise CommandError(f"Pipeline {pipeline_id} not found")
        
        migrator = FieldSchemaMigrator(pipeline)
        
        # This is a simplified version - in practice, you'd pass specific field changes
        # For now, just show what this would look like
        
        self.stdout.write(f"Field schema migration for pipeline: {pipeline.name}")
        self.stdout.write(f"Dry run: {dry_run}")
        self.stdout.write(f"Batch size: {batch_size}")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("This is a dry run - no actual changes will be made")
            )
        
        # In a real implementation, you'd accept field change specifications
        # and perform the migration here
        
        self.stdout.write(
            self.style.SUCCESS("Migration framework is ready - specify field changes to proceed")
        )

    def analyze_impact(self, options):
        """Analyze impact of field changes"""
        pipeline_id = options.get('pipeline_id')
        field_slug = options.get('field_slug')
        
        if not all([pipeline_id, field_slug]):
            raise CommandError("--pipeline-id and --field-slug are required")
        
        try:
            pipeline = Pipeline.objects.get(id=pipeline_id)
            field = pipeline.fields.with_deleted().get(slug=field_slug)
        except Pipeline.DoesNotExist:
            raise CommandError(f"Pipeline {pipeline_id} not found")
        except Field.DoesNotExist:
            raise CommandError(f"Field {field_slug} not found in pipeline {pipeline_id}")
        
        migrator = FieldSchemaMigrator(pipeline)
        impact = migrator.analyze_field_change_impact(field)
        
        self.stdout.write(f"\nImpact Analysis for field: {field.name} ({field.slug})")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total records: {impact['total_records']}")
        self.stdout.write(f"Records with data: {impact['records_with_data']}")
        self.stdout.write(f"Affected records: {impact['affected_records']}")
        self.stdout.write(f"Migration required: {impact['migration_required']}")
        self.stdout.write(f"Estimated time: {impact['estimated_time_minutes']} minutes")
        
        if impact['breaking_changes']:
            self.stdout.write(f"\nBreaking changes:")
            for change in impact['breaking_changes']:
                self.stdout.write(f"  - {change}")
        
        if impact['warnings']:
            self.stdout.write(f"\nWarnings:")
            for warning in impact['warnings']:
                self.stdout.write(f"  - {warning}")
        
        if impact['dependent_fields']:
            self.stdout.write(f"\nDependent fields:")
            for dep in impact['dependent_fields']:
                self.stdout.write(f"  - {dep['field_name']} ({dep['dependency_type']})")