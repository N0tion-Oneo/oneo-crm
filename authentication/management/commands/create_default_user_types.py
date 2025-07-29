"""
Management command to create default user types
Uses Django's async capabilities for database operations
"""

import asyncio
from django.core.management.base import BaseCommand
from django.utils import timezone
from authentication.models import UserType


class Command(BaseCommand):
    help = 'Create default user types for the tenant'
    
    def handle(self, *args, **options):
        """Run the async user type creation"""
        asyncio.run(self.acreate_user_types())
    
    async def acreate_user_types(self):
        """Create default user types asynchronously"""
        self.stdout.write('Creating default user types...')
        
        try:
            await UserType.acreate_default_types()
            self.stdout.write(
                self.style.SUCCESS('Successfully created default user types')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating user types: {str(e)}')
            )