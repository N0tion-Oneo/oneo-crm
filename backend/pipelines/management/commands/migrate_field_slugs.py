"""
Django Management Command: Migrate Field Slugs from Hyphens to Underscores
Usage: python manage.py migrate_field_slugs
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field, Record, field_slugify


class Command(BaseCommand):
    help = 'Migrate existing field slugs from hyphens to underscores to match data key format'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            default='oneotalent',
            help='Tenant schema to migrate (default: oneotalent)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without making changes'
        )

    def handle(self, *args, **options):
        tenant_schema = options['tenant']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 DRY RUN MODE - No changes will be made')
            )
        
        self.stdout.write(f"🔄 Field Slug Migration: {tenant_schema}")
        self.stdout.write("=" * 60)
        
        with schema_context(tenant_schema):
            # Find fields with hyphens that need migration
            fields_to_migrate = Field.objects.filter(slug__contains='-')
            
            self.stdout.write(f"🔍 Found {fields_to_migrate.count()} fields with hyphens in slugs")
            
            if not fields_to_migrate.exists():
                self.stdout.write(self.style.SUCCESS("✅ No fields need migration"))
                return
            
            # Plan the migration
            migration_plan = []
            self.stdout.write("\n📋 Fields to migrate:")
            
            for field in fields_to_migrate:
                old_slug = field.slug
                new_slug = field_slugify(field.name)
                
                if old_slug != new_slug:
                    migration_plan.append({
                        'field': field,
                        'old_slug': old_slug,
                        'new_slug': new_slug
                    })
                    self.stdout.write(
                        f"   {field.pipeline.name:20} | {field.name:15} | {old_slug:15} → {new_slug}"
                    )
            
            if not migration_plan:
                self.stdout.write(self.style.SUCCESS("✅ All field slugs are already correct"))
                return
            
            if dry_run:
                self.stdout.write(f"\n📊 Dry run complete: {len(migration_plan)} fields would be migrated")
                return
            
            # Execute migration
            self.stdout.write(f"\n🚀 Starting migration of {len(migration_plan)} fields...")
            
            with transaction.atomic():
                success_count = 0
                error_count = 0
                
                for migration in migration_plan:
                    field = migration['field']
                    old_slug = migration['old_slug']
                    new_slug = migration['new_slug']
                    
                    try:
                        self.stdout.write(f"   Updating {field.name}: {old_slug} → {new_slug}")
                        field.slug = new_slug
                        field.save()
                        success_count += 1
                        
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"   ❌ Failed to update {field.name}: {e}")
                        )
                        error_count += 1
                
                # Summary
                self.stdout.write(f"\n📊 Migration Summary:")
                self.stdout.write(f"   ✅ Successfully migrated: {success_count} fields")
                if error_count > 0:
                    self.stdout.write(f"   ❌ Failed migrations: {error_count} fields")
                
                if error_count == 0:
                    self.stdout.write(self.style.SUCCESS(f"\n🎉 Migration completed successfully!"))
                    
                    # Verify the fix
                    self._verify_migration(tenant_schema)
                else:
                    self.stdout.write(
                        self.style.ERROR(f"\n⚠️  Migration completed with {error_count} errors")
                    )

    def _verify_migration(self, tenant_schema):
        """Verify that field slugs now match data keys"""
        self.stdout.write(f"\n🔍 Verifying data access after migration...")
        
        with schema_context(tenant_schema):
            # Test with Sales Pipeline
            sales_pipeline = Pipeline.objects.filter(name__icontains='sales').first()
            if not sales_pipeline:
                self.stdout.write("   ❓ No sales pipeline found for verification")
                return
            
            fields = sales_pipeline.fields.all()[:5]  # Test first 5 fields
            sample_record = sales_pipeline.records.filter(is_deleted=False).first()
            
            if not sample_record:
                self.stdout.write("   ❓ No sample record found for verification")
                return
            
            self.stdout.write(f"   Testing with record {sample_record.id}:")
            data_keys = list(sample_record.data.keys()) if sample_record.data else []
            self.stdout.write(f"   Record data keys: {data_keys}")
            
            matches = 0
            total_fields = 0
            
            for field in fields:
                field_slug = field.slug
                has_data = field_slug in (sample_record.data or {})
                status = "✅" if has_data else "❌"
                
                total_fields += 1
                if has_data:
                    matches += 1
                    
                self.stdout.write(f"     {field.name:15} | slug: {field_slug:15} | data exists: {status}")
            
            self.stdout.write(f"\n   📊 Verification Results:")
            self.stdout.write(f"     ✅ Fields with matching data: {matches}/{total_fields}")
            
            if matches > total_fields // 2:
                self.stdout.write(self.style.SUCCESS("   🎉 SUCCESS: Field slugs now match data keys!"))
            else:
                self.stdout.write(self.style.WARNING("   ⚠️  Some fields still don't have matching data"))