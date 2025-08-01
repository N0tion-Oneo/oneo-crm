"""
Management command to set up system relationship types
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from relationships.models import RelationshipType


class Command(BaseCommand):
    help = 'Set up system relationship types'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of relationship types',
        )

    def handle(self, *args, **options):
        self.stdout.write('Setting up system relationship types...')
        
        try:
            with transaction.atomic():
                if options['force']:
                    # Delete existing system types
                    deleted_count = RelationshipType.objects.filter(is_system=True).delete()[0]
                    if deleted_count > 0:
                        self.stdout.write(
                            self.style.WARNING(f'Deleted {deleted_count} existing system relationship types')
                        )
                
                # Create system relationship types
                initial_count = RelationshipType.objects.filter(is_system=True).count()
                RelationshipType.create_system_types()
                final_count = RelationshipType.objects.filter(is_system=True).count()
                
                created_count = final_count - initial_count
                
                if created_count > 0:
                    self.stdout.write(
                        self.style.SUCCESS(f'Created {created_count} system relationship types')
                    )
                else:
                    self.stdout.write('All system relationship types already exist')
                
                # List all system types
                system_types = RelationshipType.objects.filter(is_system=True)
                self.stdout.write('\nSystem relationship types:')
                for rel_type in system_types:
                    self.stdout.write(f'  - {rel_type.name} ({rel_type.slug}) - {rel_type.cardinality}')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error setting up relationship types: {e}')
            )
            raise