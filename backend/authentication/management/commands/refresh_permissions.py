"""
Management command to manually refresh permissions and broadcast updates
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from authentication.models import UserType
from authentication.signals import trigger_manual_permission_refresh

User = get_user_model()


class Command(BaseCommand):
    help = 'Manually refresh permissions and broadcast updates to connected clients'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Refresh permissions for specific user ID'
        )
        parser.add_argument(
            '--user-type-id',
            type=int,
            help='Refresh permissions for all users with specific user type ID'
        )
        parser.add_argument(
            '--tenant-schema',
            type=str,
            help='Refresh permissions for specific tenant schema (default: current)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Refresh permissions for all users in current tenant'
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        user_type_id = options.get('user_type_id')
        tenant_schema = options.get('tenant_schema')
        refresh_all = options.get('all')

        if not any([user_id, user_type_id, refresh_all]):
            self.stdout.write(
                self.style.ERROR('Please specify --user-id, --user-type-id, or --all')
            )
            return

        try:
            if user_id:
                # Refresh specific user
                try:
                    user = User.objects.get(id=user_id)
                    affected_count = trigger_manual_permission_refresh(
                        user_id=user_id,
                        tenant_schema=tenant_schema
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully refreshed permissions for user {user.username} (ID: {user_id})'
                        )
                    )
                except User.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'User with ID {user_id} not found')
                    )
                    return

            elif user_type_id:
                # Refresh all users with specific user type
                try:
                    user_type = UserType.objects.get(id=user_type_id)
                    affected_count = trigger_manual_permission_refresh(
                        user_type_id=user_type_id,
                        tenant_schema=tenant_schema
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully refreshed permissions for {affected_count} users '
                            f'with user type "{user_type.name}" (ID: {user_type_id})'
                        )
                    )
                except UserType.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'UserType with ID {user_type_id} not found')
                    )
                    return

            elif refresh_all:
                # Refresh all users in tenant
                affected_count = trigger_manual_permission_refresh(
                    tenant_schema=tenant_schema
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully refreshed permissions for {affected_count} users in tenant'
                    )
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Permission refresh completed. Affected users: {affected_count}'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error refreshing permissions: {e}')
            )