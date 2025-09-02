"""
Management command to fix out-of-sync unread counts for conversations
"""
from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from communications.models import Conversation, Message, MessageDirection, MessageStatus
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fix out-of-sync unread counts for all conversations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )
        parser.add_argument(
            '--conversation-id',
            type=str,
            help='Fix a specific conversation by ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        conversation_id = options.get('conversation_id')
        
        if conversation_id:
            conversations = Conversation.objects.filter(id=conversation_id)
        else:
            conversations = Conversation.objects.all()
        
        total_conversations = conversations.count()
        fixed_count = 0
        
        self.stdout.write(f"Checking {total_conversations} conversations...")
        
        for conversation in conversations:
            # Calculate the actual unread count
            actual_unread = Message.objects.filter(
                conversation=conversation,
                direction=MessageDirection.INBOUND
            ).exclude(
                status__in=[MessageStatus.READ, 'read']  # Check both uppercase and lowercase
            ).count()
            
            # Check if it matches the stored unread_count
            if conversation.unread_count != actual_unread:
                self.stdout.write(
                    f"Conversation {conversation.id} ({conversation.subject}): "
                    f"stored={conversation.unread_count}, actual={actual_unread}"
                )
                
                if not dry_run:
                    conversation.unread_count = actual_unread
                    conversation.save(update_fields=['unread_count'])
                    fixed_count += 1
                else:
                    self.stdout.write(f"  Would fix: {conversation.unread_count} -> {actual_unread}")
                    fixed_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Dry run complete: {fixed_count} conversations would be fixed")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Fixed {fixed_count} out of {total_conversations} conversations")
            )