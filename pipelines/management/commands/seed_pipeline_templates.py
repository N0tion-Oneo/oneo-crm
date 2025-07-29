"""
Management command to seed pipeline templates
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from pipelines.models import PipelineTemplate
from pipelines.templates import SYSTEM_TEMPLATES
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Seed system pipeline templates'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing templates',
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Seed only specific category (crm, ats, cms, project)',
        )
    
    def handle(self, *args, **options):
        force = options['force']
        category = options['category']
        
        self.stdout.write(
            self.style.SUCCESS('Starting pipeline template seeding...')
        )
        
        # Get or create system user for templates
        system_user, created = User.objects.get_or_create(
            username='system',
            defaults={
                'email': 'system@oneo.crm',
                'is_active': False,
                'is_staff': False,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('Created system user for templates')
            )
        
        templates_to_create = SYSTEM_TEMPLATES
        if category:
            if category not in SYSTEM_TEMPLATES:
                self.stdout.write(
                    self.style.ERROR(f'Unknown category: {category}')
                )
                return
            templates_to_create = {category: SYSTEM_TEMPLATES[category]}
        
        created_count = 0
        updated_count = 0
        
        for template_category, template_func in templates_to_create.items():
            try:
                with transaction.atomic():
                    template_data = template_func()
                    pipeline_data = template_data['pipeline']
                    
                    # Check if template already exists
                    template_slug = f"system-{template_category}"
                    existing_template = PipelineTemplate.objects.filter(
                        slug=template_slug
                    ).first()
                    
                    if existing_template:
                        if force:
                            # Update existing template
                            existing_template.name = pipeline_data['name']
                            existing_template.description = pipeline_data['description']
                            existing_template.template_data = template_data
                            existing_template.save()
                            
                            updated_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'Updated template: {pipeline_data["name"]}'
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Template already exists: {pipeline_data["name"]} '
                                    f'(use --force to update)'
                                )
                            )
                    else:
                        # Create new template
                        template = PipelineTemplate.objects.create(
                            name=pipeline_data['name'],
                            slug=template_slug,
                            description=pipeline_data['description'],
                            category=template_category,
                            template_data=template_data,
                            is_system=True,
                            is_public=True,
                            created_by=system_user,
                            preview_config={
                                'icon': pipeline_data.get('icon', 'database'),
                                'color': pipeline_data.get('color', '#3B82F6'),
                                'field_count': len(template_data.get('fields', [])),
                                'ai_fields': len([
                                    f for f in template_data.get('fields', [])
                                    if f.get('is_ai_field', False)
                                ])
                            },
                            sample_data={
                                'description': f'Sample {template_category.upper()} data',
                                'records_count': 0
                            }
                        )
                        
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Created template: {template.name}'
                            )
                        )
            
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to create template {template_category}: {e}'
                    )
                )
                logger.error(f'Template creation failed: {e}', exc_info=True)
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'Template seeding completed: '
                f'{created_count} created, {updated_count} updated'
            )
        )
        
        # List all system templates
        system_templates = PipelineTemplate.objects.filter(is_system=True)
        self.stdout.write('\nSystem templates:')
        for template in system_templates:
            ai_field_count = len([
                f for f in template.template_data.get('fields', [])
                if f.get('is_ai_field', False)
            ])
            self.stdout.write(
                f'  - {template.name} ({template.category}) - '
                f'{len(template.template_data.get("fields", []))} fields, '
                f'{ai_field_count} AI fields'
            )