"""
Management command to fix email metadata for existing messages
Adds proper 'from' and 'to' fields for frontend compatibility
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from communications.models import Message, ChannelType
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fix email metadata to include proper from/to fields for frontend display'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run in dry-run mode (no changes will be saved)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of messages to process',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        
        self.stdout.write(self.style.SUCCESS(
            f"{'DRY RUN: ' if dry_run else ''}Fixing email metadata..."
        ))
        
        # Query email messages that have the old metadata format
        email_messages = Message.objects.filter(
            channel__channel_type__in=['gmail', 'outlook', 'email', 'mail']
        ).exclude(
            metadata__has_key='from'  # Skip messages already fixed
        )
        
        if limit:
            email_messages = email_messages[:limit]
        
        total_messages = email_messages.count()
        self.stdout.write(f"Found {total_messages} email messages to process")
        
        fixed_count = 0
        error_count = 0
        
        for message in email_messages:
            try:
                metadata = message.metadata or {}
                
                # Check if this message needs fixing
                if 'from' in metadata and 'to' in metadata:
                    continue  # Already has the correct format
                
                # Initialize the new fields
                from_field = None
                to_field = []
                cc_field = []
                
                # Extract from field from sender_info
                if 'sender_info' in metadata:
                    sender_info = metadata['sender_info']
                    from_field = {
                        'email': sender_info.get('email', ''),
                        'name': sender_info.get('name', '')
                    }
                elif message.direction == 'outbound':
                    # For outbound without sender_info, use the account owner
                    # This is a fallback - ideally sender_info should be present
                    from_field = {
                        'email': message.channel.user_connection.user.email if hasattr(message.channel, 'user_connection') else '',
                        'name': message.channel.user_connection.user.get_full_name() if hasattr(message.channel, 'user_connection') else ''
                    }
                else:
                    # For inbound, use contact_email as fallback
                    from_field = {
                        'email': message.contact_email,
                        'name': ''
                    }
                
                # Extract to/cc fields from recipients
                if 'recipients' in metadata:
                    recipients = metadata['recipients']
                    
                    # Convert to list format for frontend
                    if 'to' in recipients:
                        to_field = [
                            {'email': r.get('email', ''), 'name': r.get('name', '')} 
                            for r in recipients['to']
                        ]
                    
                    if 'cc' in recipients:
                        cc_field = [
                            {'email': r.get('email', ''), 'name': r.get('name', '')} 
                            for r in recipients['cc']
                        ]
                else:
                    # Fallback: use contact_email for to field
                    if message.direction == 'inbound':
                        # For inbound, the TO was likely the account owner
                        to_field = [{
                            'email': message.channel.user_connection.user.email if hasattr(message.channel, 'user_connection') else '',
                            'name': message.channel.user_connection.user.get_full_name() if hasattr(message.channel, 'user_connection') else ''
                        }]
                    else:
                        # For outbound, use contact_email as the recipient
                        to_field = [{
                            'email': message.contact_email,
                            'name': ''
                        }]
                
                # Update metadata with the new fields
                metadata['from'] = from_field
                metadata['to'] = to_field
                metadata['cc'] = cc_field
                
                if not dry_run:
                    message.metadata = metadata
                    message.save(update_fields=['metadata'])
                
                fixed_count += 1
                
                if fixed_count % 100 == 0:
                    self.stdout.write(f"Processed {fixed_count}/{total_messages} messages...")
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"Error processing message {message.id}: {str(e)}")
                )
                logger.error(f"Error fixing metadata for message {message.id}", exc_info=True)
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'DRY RUN ' if dry_run else ''}Summary:\n"
                f"  Total messages: {total_messages}\n"
                f"  Fixed: {fixed_count}\n"
                f"  Errors: {error_count}"
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nThis was a dry run. No changes were saved.\n"
                    "Run without --dry-run to apply changes."
                )
            )