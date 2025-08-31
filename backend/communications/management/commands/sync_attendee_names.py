"""
Management command to sync attendee names from UniPile
"""
import logging
from typing import Dict, List, Optional

from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context

from communications.models import Participant, UserChannelConnection
from communications.unipile.clients.messaging import MessagingClient
from communications.unipile.clients.users import UsersClient
from tenants.models import Tenant

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync attendee names from UniPile for all participants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Specific tenant schema to sync (default: all tenants)'
        )
        parser.add_argument(
            '--channel-type',
            type=str,
            choices=['whatsapp', 'linkedin', 'all'],
            default='all',
            help='Channel type to sync (default: all)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes'
        )

    def handle(self, *args, **options):
        tenant_schema = options.get('tenant')
        channel_type = options.get('channel_type')
        dry_run = options.get('dry_run')
        
        if tenant_schema:
            tenants = Tenant.objects.filter(schema_name=tenant_schema)
            if not tenants.exists():
                self.stdout.write(self.style.ERROR(f'Tenant {tenant_schema} not found'))
                return
        else:
            tenants = Tenant.objects.exclude(schema_name='public')
        
        for tenant in tenants:
            self.stdout.write(f'\nProcessing tenant: {tenant.schema_name}')
            self.sync_tenant_attendees(
                tenant.schema_name,
                channel_type,
                dry_run
            )
    
    def sync_tenant_attendees(
        self,
        schema_name: str,
        channel_type: str,
        dry_run: bool
    ):
        """Sync attendees for a specific tenant"""
        with schema_context(schema_name):
            # Get channel connections
            connections = UserChannelConnection.objects.filter(
                is_active=True
            )
            
            if channel_type != 'all':
                connections = connections.filter(channel_type=channel_type)
            
            for connection in connections:
                self.stdout.write(f'  Processing {connection.channel_type} connection: {connection.account_name}')
                
                try:
                    self.sync_connection_attendees(connection, dry_run)
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'    Error syncing {connection.channel_type}: {str(e)}')
                    )
    
    def sync_connection_attendees(
        self,
        connection: UserChannelConnection,
        dry_run: bool
    ):
        """Sync attendees for a specific connection"""
        
        # Initialize UniPile client
        if connection.channel_type == 'whatsapp':
            client = MessagingClient(
                api_url='https://api18.unipile.com:14890/api/v1',
                access_token='<unipile_token>'  # This should come from settings
            )
        else:
            # For LinkedIn and others
            client = UsersClient(
                api_url='https://api18.unipile.com:14890/api/v1', 
                access_token='<unipile_token>'
            )
        
        # Get all attendees from UniPile
        self.stdout.write(f'    Fetching attendees from UniPile...')
        attendees = self.fetch_all_attendees(client, connection)
        
        if not attendees:
            self.stdout.write('    No attendees found')
            return
        
        self.stdout.write(f'    Found {len(attendees)} attendees')
        
        # Update participants with names
        updated_count = 0
        for attendee in attendees:
            if self.update_participant_from_attendee(attendee, connection.channel_type, dry_run):
                updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'    Updated {updated_count} participants with names')
        )
    
    def fetch_all_attendees(
        self,
        client,
        connection: UserChannelConnection
    ) -> List[Dict]:
        """Fetch all attendees from UniPile"""
        try:
            if connection.channel_type == 'whatsapp':
                # For WhatsApp, use messaging client
                response = client.list_all_chats(
                    account_id=connection.unipile_account_id
                )
                
                attendees = []
                if response and response.get('items'):
                    for chat in response['items']:
                        # Extract attendees from chat
                        if 'attendees' in chat:
                            for attendee in chat['attendees']:
                                attendees.append({
                                    'id': attendee.get('id'),
                                    'name': attendee.get('name', ''),
                                    'phone': attendee.get('phone_number', attendee.get('id', '')),
                                    'type': 'whatsapp'
                                })
                return attendees
                
            elif connection.channel_type == 'linkedin':
                # For LinkedIn, use users client
                response = client.list_attendees(
                    account_id=connection.unipile_account_id
                )
                
                attendees = []
                if response and response.get('items'):
                    for attendee in response['items']:
                        attendees.append({
                            'id': attendee.get('id'),
                            'name': attendee.get('name', ''),
                            'linkedin_urn': attendee.get('id'),
                            'type': 'linkedin'
                        })
                return attendees
                
        except Exception as e:
            logger.error(f'Error fetching attendees: {str(e)}')
            return []
    
    def update_participant_from_attendee(
        self,
        attendee: Dict,
        channel_type: str,
        dry_run: bool
    ) -> bool:
        """Update a participant with attendee name"""
        
        # Find matching participant
        participant = None
        
        if channel_type == 'whatsapp' and attendee.get('phone'):
            # Match by phone number
            participant = Participant.objects.filter(
                phone=attendee['phone']
            ).first()
            
        elif channel_type == 'linkedin' and attendee.get('linkedin_urn'):
            # Match by LinkedIn URN
            participant = Participant.objects.filter(
                linkedin_member_urn=attendee['linkedin_urn']
            ).first()
        
        if participant and attendee.get('name'):
            if not participant.name or participant.name != attendee['name']:
                old_name = participant.name or '<empty>'
                
                if dry_run:
                    self.stdout.write(
                        f'      Would update: {old_name} -> {attendee["name"]}'
                    )
                else:
                    participant.name = attendee['name']
                    participant.save(update_fields=['name'])
                    self.stdout.write(
                        f'      Updated: {old_name} -> {attendee["name"]}'
                    )
                return True
        
        return False