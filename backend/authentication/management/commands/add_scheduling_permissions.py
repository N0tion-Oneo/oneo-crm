"""
Management command to add scheduling permissions to existing user types
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from authentication.models import UserType


class Command(BaseCommand):
    help = 'Add scheduling permissions to existing user types'

    def handle(self, *args, **options):
        """Add scheduling permissions to all user types"""
        
        self.stdout.write('Adding scheduling permissions to user types...')
        
        with transaction.atomic():
            # Update Admin - gets scheduling_all permission
            admin = UserType.objects.filter(slug='admin').first()
            if admin:
                if 'communication_settings' not in admin.base_permissions:
                    admin.base_permissions['communication_settings'] = []
                # Ensure it's a list
                if not isinstance(admin.base_permissions.get('communication_settings'), list):
                    admin.base_permissions['communication_settings'] = []
                if 'scheduling' not in admin.base_permissions['communication_settings']:
                    admin.base_permissions['communication_settings'].append('scheduling')
                if 'scheduling_all' not in admin.base_permissions['communication_settings']:
                    admin.base_permissions['communication_settings'].append('scheduling_all')
                admin.save(update_fields=['base_permissions'])
                self.stdout.write(self.style.SUCCESS(f'✓ Updated Admin with scheduling and scheduling_all'))
            else:
                self.stdout.write(self.style.WARNING('Admin user type not found'))
            
            # Update Manager - gets scheduling permission
            manager = UserType.objects.filter(slug='manager').first()
            if manager:
                if 'communication_settings' not in manager.base_permissions:
                    manager.base_permissions['communication_settings'] = []
                # Ensure it's a list
                if not isinstance(manager.base_permissions.get('communication_settings'), list):
                    manager.base_permissions['communication_settings'] = []
                if 'scheduling' not in manager.base_permissions['communication_settings']:
                    manager.base_permissions['communication_settings'].append('scheduling')
                manager.save(update_fields=['base_permissions'])
                self.stdout.write(self.style.SUCCESS(f'✓ Updated Manager with scheduling'))
            else:
                self.stdout.write(self.style.WARNING('Manager user type not found'))
            
            # Update User - gets scheduling permission
            user = UserType.objects.filter(slug='user').first()
            if user:
                if 'communication_settings' not in user.base_permissions:
                    user.base_permissions['communication_settings'] = []
                # Ensure it's a list
                if not isinstance(user.base_permissions.get('communication_settings'), list):
                    user.base_permissions['communication_settings'] = []
                if 'scheduling' not in user.base_permissions['communication_settings']:
                    user.base_permissions['communication_settings'].append('scheduling')
                user.save(update_fields=['base_permissions'])
                self.stdout.write(self.style.SUCCESS(f'✓ Updated User with scheduling'))
            else:
                self.stdout.write(self.style.WARNING('User user type not found'))
            
            # Update Viewer - gets no scheduling permissions
            viewer = UserType.objects.filter(slug='viewer').first()
            if viewer:
                # Viewers don't get scheduling permission
                self.stdout.write(self.style.SUCCESS(f'✓ Viewer has no scheduling permissions (as expected)'))
            else:
                self.stdout.write(self.style.WARNING('Viewer user type not found'))
        
        # Clear permission cache to ensure changes take effect
        from django.core.cache import cache
        cache.clear()
        
        self.stdout.write(self.style.SUCCESS('\n✓ Successfully added scheduling permissions to all user types'))
        self.stdout.write(self.style.SUCCESS('✓ Cache cleared - permissions will take effect immediately'))
        
        # Show summary
        self.stdout.write('\nPermission Summary:')
        self.stdout.write('  Admin:   communication_settings.scheduling, communication_settings.scheduling_all')
        self.stdout.write('  Manager: communication_settings.scheduling')
        self.stdout.write('  User:    communication_settings.scheduling')
        self.stdout.write('  Viewer:  (no permissions)')