from django.core.management.base import BaseCommand
from django.db import transaction
from pipelines.models import Pipeline, Record
from pipelines.record_operations import RecordUtils


class Command(BaseCommand):
    help = 'Regenerate titles for all records using their pipeline\'s current title template'

    def add_arguments(self, parser):
        parser.add_argument(
            '--pipeline-id',
            type=str,
            help='Only regenerate titles for records in this specific pipeline',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually updating records',
        )

    def handle(self, *args, **options):
        pipeline_id = options.get('pipeline_id')
        dry_run = options.get('dry_run')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        # Get pipelines to process
        if pipeline_id:
            try:
                pipelines = [Pipeline.objects.get(id=pipeline_id)]
                self.stdout.write(f'Processing specific pipeline: {pipelines[0].name}')
            except Pipeline.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Pipeline with ID {pipeline_id} not found')
                )
                return
        else:
            pipelines = Pipeline.objects.all()
            self.stdout.write(f'Processing all {pipelines.count()} pipelines')

        total_updated = 0
        
        for pipeline in pipelines:
            self.stdout.write(f'\n🔄 Processing pipeline: {pipeline.name}')
            
            # Get current title template
            title_template = pipeline.get_title_template()
            self.stdout.write(f'   Template: "{title_template}"')
            
            # Get all records for this pipeline
            records = Record.objects.filter(pipeline=pipeline)
            pipeline_updated = 0
            
            for record in records:
                # Generate new title using current template
                new_title = RecordUtils.generate_title(
                    record.data, 
                    pipeline.name,
                    pipeline
                )
                
                if record.title != new_title:
                    if dry_run:
                        self.stdout.write(
                            f'   Would update record {record.id}: '
                            f'"{record.title}" → "{new_title}"'
                        )
                    else:
                        old_title = record.title
                        record.title = new_title
                        record.save(update_fields=['title'])
                        self.stdout.write(
                            f'   ✅ Updated record {record.id}: '
                            f'"{old_title}" → "{new_title}"'
                        )
                    pipeline_updated += 1
            
            if pipeline_updated > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'   {pipeline_updated} records {"would be " if dry_run else ""}updated in {pipeline.name}'
                    )
                )
            else:
                self.stdout.write(f'   No records need updating in {pipeline.name}')
                
            total_updated += pipeline_updated

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\nDRY RUN COMPLETE: {total_updated} records would be updated'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ COMPLETE: {total_updated} record titles regenerated'
                )
            )