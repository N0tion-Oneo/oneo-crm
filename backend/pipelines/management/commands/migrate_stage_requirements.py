"""
Management command to migrate legacy stage_requirements to conditional_rules format
"""
import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pipelines.models import Pipeline, Field


class Command(BaseCommand):
    help = 'Migrate legacy stage_requirements to new conditional_rules format'

    def add_arguments(self, parser):
        parser.add_argument(
            '--pipeline-id',
            type=int,
            help='Migrate specific pipeline by ID (optional - migrates all if not specified)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without making changes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force migration even if conditional_rules already exist'
        )

    def handle(self, *args, **options):
        """Main migration handler"""
        pipeline_id = options.get('pipeline_id')
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)

        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 DRY RUN MODE - No changes will be made')
            )

        # Get pipelines to migrate
        if pipeline_id:
            try:
                pipelines = [Pipeline.objects.get(id=pipeline_id)]
            except Pipeline.DoesNotExist:
                raise CommandError(f'Pipeline with ID {pipeline_id} does not exist')
        else:
            pipelines = Pipeline.objects.all()

        if not pipelines:
            self.stdout.write(self.style.WARNING('No pipelines found to migrate'))
            return

        self.stdout.write(f'Found {len(pipelines)} pipeline(s) to analyze...\n')

        total_migrated = 0
        total_fields_migrated = 0

        for pipeline in pipelines:
            migrated_count = self.migrate_pipeline(pipeline, dry_run, force)
            if migrated_count > 0:
                total_migrated += 1
                total_fields_migrated += migrated_count

        # Summary
        self.stdout.write('\n' + '='*60)
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'📊 SUMMARY (DRY RUN): Would migrate {total_fields_migrated} fields '
                    f'across {total_migrated} pipelines'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ MIGRATION COMPLETE: Migrated {total_fields_migrated} fields '
                    f'across {total_migrated} pipelines'
                )
            )

    def migrate_pipeline(self, pipeline: Pipeline, dry_run: bool, force: bool) -> int:
        """Migrate a single pipeline's fields"""
        self.stdout.write(f'📋 Analyzing Pipeline: {pipeline.name} (ID: {pipeline.id})')

        # Find potential stage fields in this pipeline
        stage_fields = self.find_stage_fields(pipeline)
        if not stage_fields:
            self.stdout.write('   ⚠️  No select fields found to map stage values')

        fields_with_stage_requirements = []
        for field in pipeline.fields.all():
            business_rules = field.business_rules or {}
            stage_requirements = business_rules.get('stage_requirements', {})

            if stage_requirements:
                fields_with_stage_requirements.append((field, stage_requirements))

        if not fields_with_stage_requirements:
            self.stdout.write('   ✨ No legacy stage_requirements found - nothing to migrate')
            return 0

        self.stdout.write(f'   🔍 Found {len(fields_with_stage_requirements)} fields with stage_requirements')

        migrated_count = 0
        for field, stage_requirements in fields_with_stage_requirements:
            if self.migrate_field(field, stage_requirements, stage_fields, dry_run, force):
                migrated_count += 1

        if migrated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'   ✅ Migrated {migrated_count} fields in this pipeline')
            )

        return migrated_count

    def find_stage_fields(self, pipeline: Pipeline) -> dict:
        """Find all select fields and their options that could be stage fields"""
        stage_fields = {}

        for field in pipeline.fields.filter(field_type='select'):
            field_config = field.field_config or {}
            options = field_config.get('options', [])

            stage_options = []
            for option in options:
                if isinstance(option, dict):
                    option_value = option.get('value') or option.get('label')
                    if option_value:
                        stage_options.append(str(option_value))
                elif isinstance(option, str):
                    stage_options.append(option)

            if stage_options:
                stage_fields[field.slug] = {
                    'field': field,
                    'options': stage_options
                }

        return stage_fields

    def find_best_stage_field(self, stage_name: str, stage_fields: dict) -> str:
        """Find which stage field contains the given stage name"""
        for field_slug, field_info in stage_fields.items():
            if stage_name in field_info['options']:
                return field_slug
        return None

    def migrate_field(self, field: Field, stage_requirements: dict, stage_fields: dict, 
                     dry_run: bool, force: bool) -> bool:
        """Migrate a single field's stage_requirements to conditional_rules"""
        
        business_rules = field.business_rules or {}
        existing_conditional_rules = business_rules.get('conditional_rules', {})
        existing_require_when = existing_conditional_rules.get('require_when')

        # Check if field already has conditional rules
        if existing_require_when and not force:
            self.stdout.write(f'   ⏭️  {field.slug}: Already has conditional_rules (use --force to overwrite)')
            return False

        # Convert stage_requirements to conditional_rules
        new_require_when_rules = []

        for stage_name, requirements in stage_requirements.items():
            if not requirements.get('required', False):
                continue  # Skip non-required stages

            # Find which stage field contains this stage
            stage_field_slug = self.find_best_stage_field(stage_name, stage_fields)

            if stage_field_slug:
                new_require_when_rules.append({
                    "field": stage_field_slug,
                    "condition": "equals",
                    "value": stage_name,
                    "description": f"Required in {stage_name} stage (migrated from legacy format)"
                })
            else:
                # Create a generic stage rule that might match common stage field names
                new_require_when_rules.append({
                    "field": "stage",  # Generic stage field name
                    "condition": "equals", 
                    "value": stage_name,
                    "description": f"Required in {stage_name} stage (migrated - verify field name)"
                })
                self.stdout.write(
                    f'   ⚠️  {field.slug}: Could not map stage "{stage_name}" to a specific field'
                )

        if not new_require_when_rules:
            self.stdout.write(f'   ⏭️  {field.slug}: No required stages found to migrate')
            return False

        # Create the new conditional_rules structure
        if existing_require_when:
            # Merge with existing rules using OR logic
            if isinstance(existing_require_when, list):
                # Convert legacy array format to new object format
                existing_rules = existing_require_when
            else:
                # Extract rules from existing object format
                existing_rules = existing_require_when.get('rules', [])

            new_conditional_rules = {
                "logic": "OR",
                "rules": existing_rules + new_require_when_rules
            }
        else:
            # Create new conditional rules
            new_conditional_rules = {
                "logic": "OR", 
                "rules": new_require_when_rules
            }

        # Show migration details
        self.stdout.write(f'   🔄 {field.slug}: Migrating {len(new_require_when_rules)} stage requirements')
        
        for rule in new_require_when_rules:
            self.stdout.write(
                f'      → {rule["field"]} {rule["condition"]} "{rule["value"]}"'
            )

        if dry_run:
            self.stdout.write(f'   📝 {field.slug}: Would update conditional_rules (DRY RUN)')
            return True

        # Apply the migration
        try:
            with transaction.atomic():
                # Update conditional_rules
                business_rules['conditional_rules'] = {
                    **existing_conditional_rules,
                    'require_when': new_conditional_rules
                }

                # Remove old stage_requirements
                business_rules.pop('stage_requirements', None)

                # Save the field
                field.business_rules = business_rules
                field.save()

                self.stdout.write(
                    self.style.SUCCESS(f'   ✅ {field.slug}: Successfully migrated and removed legacy format')
                )
                return True

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'   ❌ {field.slug}: Migration failed - {str(e)}')
            )
            return False