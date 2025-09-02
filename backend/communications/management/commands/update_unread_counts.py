"""
Management command to recalculate unread counts for all conversations
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django_tenants.utils import schema_context, get_tenant_model

from communications.models import Conversation, Message, MessageStatus, MessageDirection


class Command(BaseCommand):
    help = 'Recalculate unread_count for all conversations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Specific tenant schema to update (optional)',
        )

    def handle(self, *args, **options):
        tenant_schema = options.get('tenant')
        
        if tenant_schema:
            # Update specific tenant
            self.update_tenant_conversations(tenant_schema)
        else:
            # Update all tenants
            TenantModel = get_tenant_model()
            for tenant in TenantModel.objects.all():
                self.update_tenant_conversations(tenant.schema_name)
    
    def update_tenant_conversations(self, schema_name):
        """Update conversations for a specific tenant"""
        with schema_context(schema_name):
            self.stdout.write(f"\nUpdating conversations in tenant: {schema_name}")
            
            conversations = Conversation.objects.all()
            total = conversations.count()
            updated = 0
            
            for conversation in conversations:
                # Calculate unread count: inbound messages that are not read
                unread_count = conversation.messages.filter(
                    direction=MessageDirection.INBOUND,
                    status__in=[
                        MessageStatus.DELIVERED, 
                        MessageStatus.SENT, 
                        MessageStatus.PENDING
                    ]
                ).exclude(status=MessageStatus.READ).count()
                
                # Update if different
                if conversation.unread_count != unread_count:
                    old_count = conversation.unread_count
                    conversation.unread_count = unread_count
                    conversation.save(update_fields=['unread_count'])
                    updated += 1
                    
                    self.stdout.write(
                        f"  Updated conversation {conversation.id}: "
                        f"{old_count} → {unread_count} unread"
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Updated {updated}/{total} conversations in {schema_name}"
                )
            )