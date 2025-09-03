"""
Management command to fix message timestamps from historical sync
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F, Case, When, Max
from django.utils import timezone
from django_tenants.utils import get_tenant_model, schema_context
from datetime import datetime
from communications.models import Message, Conversation
import json


class Command(BaseCommand):
    help = 'Fix message timestamps that were incorrectly set to sync time instead of actual message time'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Specific tenant schema to fix (default: all tenants)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit number of messages to process (0 = no limit)'
        )

    def handle(self, *args, **options):
        tenant_schema = options.get('tenant')
        dry_run = options.get('dry_run')
        limit = options.get('limit', 0)
        
        if tenant_schema:
            # Process single tenant
            self.process_tenant(tenant_schema, dry_run, limit)
        else:
            # Process all tenants
            Tenant = get_tenant_model()
            for tenant in Tenant.objects.exclude(schema_name='public'):
                self.stdout.write(f"\n{self.style.NOTICE('=' * 50)}")
                self.stdout.write(f"Processing tenant: {tenant.schema_name}")
                self.stdout.write(f"{self.style.NOTICE('=' * 50)}")
                self.process_tenant(tenant.schema_name, dry_run, limit)
    
    def process_tenant(self, schema_name, dry_run, limit):
        """Process messages for a single tenant"""
        with schema_context(schema_name):
            # Find messages where timestamps appear to be set to sync time
            messages_to_fix = self.find_messages_to_fix(limit)
            
            if not messages_to_fix:
                self.stdout.write(self.style.SUCCESS(f"No messages need fixing in {schema_name}"))
                return
            
            self.stdout.write(f"Found {len(messages_to_fix)} messages to fix")
            
            if dry_run:
                self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
                for msg in messages_to_fix[:10]:  # Show first 10 as examples
                    self.show_fix_preview(msg)
                if len(messages_to_fix) > 10:
                    self.stdout.write(f"... and {len(messages_to_fix) - 10} more")
            else:
                fixed_count = self.fix_messages(messages_to_fix)
                self.stdout.write(self.style.SUCCESS(f"Fixed {fixed_count} messages"))
                
                # Update conversation timestamps
                self.stdout.write("Updating conversation timestamps...")
                conv_count = self.update_conversation_timestamps()
                self.stdout.write(self.style.SUCCESS(f"Updated {conv_count} conversations"))
    
    def find_messages_to_fix(self, limit):
        """Find messages that need timestamp fixes"""
        # Get messages with unipile_data in metadata
        query = Message.objects.filter(
            metadata__unipile_data__isnull=False
        )
        
        if limit > 0:
            query = query[:limit]
        
        messages_to_fix = []
        
        for message in query:
            unipile_data = message.metadata.get('unipile_data', {})
            
            # Check if we have timestamp data from UniPile
            unipile_timestamp = None
            if 'timestamp' in unipile_data:
                unipile_timestamp = self.parse_timestamp(unipile_data['timestamp'])
            elif 'date' in unipile_data:
                unipile_timestamp = self.parse_timestamp(unipile_data['date'])
            
            if not unipile_timestamp:
                continue
            
            # Check if timestamps need fixing
            needs_fix = False
            
            if message.direction == 'outbound':
                # For outbound, sent_at should match UniPile timestamp
                if not message.sent_at or abs((message.sent_at - message.created_at).total_seconds()) < 1:
                    # sent_at is missing or same as created_at (likely wrong)
                    needs_fix = True
            else:  # inbound
                # For inbound, received_at should match UniPile timestamp
                if not message.received_at or abs((message.received_at - message.created_at).total_seconds()) < 1:
                    # received_at is missing or same as created_at (likely wrong)
                    needs_fix = True
            
            if needs_fix:
                messages_to_fix.append({
                    'message': message,
                    'unipile_timestamp': unipile_timestamp
                })
        
        return messages_to_fix
    
    def parse_timestamp(self, timestamp_str):
        """Parse various timestamp formats"""
        if not timestamp_str:
            return None
        
        try:
            # Handle ISO format with Z timezone
            if isinstance(timestamp_str, str):
                timestamp_str = timestamp_str.replace('Z', '+00:00')
                return datetime.fromisoformat(timestamp_str)
            return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to parse timestamp: {timestamp_str} - {e}"))
            return None
    
    def show_fix_preview(self, fix_data):
        """Show preview of what would be fixed"""
        msg = fix_data['message']
        new_timestamp = fix_data['unipile_timestamp']
        
        self.stdout.write(f"\nMessage ID: {msg.id}")
        self.stdout.write(f"  Direction: {msg.direction}")
        self.stdout.write(f"  Created: {msg.created_at}")
        
        if msg.direction == 'outbound':
            self.stdout.write(f"  Current sent_at: {msg.sent_at}")
            self.stdout.write(self.style.SUCCESS(f"  New sent_at: {new_timestamp}"))
        else:
            self.stdout.write(f"  Current received_at: {msg.received_at}")
            self.stdout.write(self.style.SUCCESS(f"  New received_at: {new_timestamp}"))
    
    def fix_messages(self, messages_to_fix):
        """Fix the message timestamps"""
        fixed_count = 0
        
        with transaction.atomic():
            for fix_data in messages_to_fix:
                msg = fix_data['message']
                new_timestamp = fix_data['unipile_timestamp']
                
                if msg.direction == 'outbound':
                    msg.sent_at = timezone.make_aware(new_timestamp) if timezone.is_naive(new_timestamp) else new_timestamp
                    msg.save(update_fields=['sent_at'])
                else:
                    msg.received_at = timezone.make_aware(new_timestamp) if timezone.is_naive(new_timestamp) else new_timestamp
                    msg.save(update_fields=['received_at'])
                
                fixed_count += 1
        
        return fixed_count
    
    def update_conversation_timestamps(self):
        """Update all conversation last_message_at based on fixed message timestamps"""
        conversations = Conversation.objects.all()
        updated_count = 0
        
        for conversation in conversations:
            # Get the last message using actual timestamps
            last_message = conversation.messages.annotate(
                actual_timestamp=Case(
                    When(sent_at__isnull=False, then=F('sent_at')),
                    When(received_at__isnull=False, then=F('received_at')),
                    default=F('created_at')
                )
            ).order_by('-actual_timestamp').first()
            
            if last_message:
                new_timestamp = last_message.sent_at or last_message.received_at or last_message.created_at
                if conversation.last_message_at != new_timestamp:
                    conversation.last_message_at = new_timestamp
                    conversation.save(update_fields=['last_message_at'])
                    updated_count += 1
        
        return updated_count