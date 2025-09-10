"""
Management command to clean up old scheduling permissions before adding new ones
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from authentication.models import UserType


class Command(BaseCommand):
    help = 'Clean up old top-level scheduling permissions'

    def handle(self, *args, **options):
        """Remove old scheduling permissions from all user types"""
        
        self.stdout.write('Cleaning up old scheduling permissions...')
        
        with transaction.atomic():
            # Get all user types
            user_types = UserType.objects.all()
            
            for user_type in user_types:
                # Remove top-level scheduling permission if it exists
                if 'scheduling' in user_type.base_permissions:
                    del user_type.base_permissions['scheduling']
                    user_type.save(update_fields=['base_permissions'])
                    self.stdout.write(self.style.SUCCESS(f'✓ Removed old scheduling permission from {user_type.name}'))
                else:
                    self.stdout.write(f'  No old scheduling permission found for {user_type.name}')
        
        # Clear permission cache to ensure changes take effect
        from django.core.cache import cache
        cache.clear()
        
        self.stdout.write(self.style.SUCCESS('\n✓ Successfully cleaned up old scheduling permissions'))
        self.stdout.write(self.style.SUCCESS('✓ Cache cleared - ready for new permissions'))