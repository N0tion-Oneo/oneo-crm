"""
Management command to update conversation names using smart naming logic
"""
import asyncio
from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.services.conversation_naming import conversation_naming_service
from communications.models import Conversation, Message


class Command(BaseCommand):
    help = 'Update conversation names using smart naming logic'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Specific tenant schema to update (default: all tenants)'
        )
        parser.add_argument(
            '--channel-type',
            type=str,
            help='Specific channel type to update (e.g., whatsapp, email)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Limit number of conversations to update per tenant (default: 100)'
        )

    def handle(self, *args, **options):
        tenant_schema = options.get('tenant')
        channel_type = options.get('channel_type')
        dry_run = options.get('dry_run', False)
        limit = options.get('limit', 100)

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        if tenant_schema:
            try:
                tenants = [Tenant.objects.get(schema_name=tenant_schema)]
            except Tenant.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Tenant '{tenant_schema}' not found")
                )
                return
        else:
            tenants = list(Tenant.objects.exclude(schema_name='public'))

        total_updated = 0

        for tenant in tenants:
            self.stdout.write(f"\n🏢 Processing tenant: {tenant.schema_name}")

            try:
                with schema_context(tenant):
                    updated_count = self.update_tenant_conversations(
                        tenant.schema_name,
                        channel_type,
                        dry_run,
                        limit
                    )
                    total_updated += updated_count

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing tenant {tenant.schema_name}: {e}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Total conversations {'analyzed' if dry_run else 'updated'}: {total_updated}"
            )
        )

    def update_tenant_conversations(self, tenant_schema, channel_type, dry_run, limit):
        """Update conversations for a specific tenant"""
        
        # Build filter for conversations that need updating
        filters = {}
        if channel_type:
            filters['channel__channel_type'] = channel_type

        # Find conversations with generic names that could be improved
        from django.db.models import Q
        
        conversations = Conversation.objects.filter(
            **filters
        ).filter(
            Q(subject__iregex=r'^(conversation|chat|whatsapp|email|contact).*[a-zA-Z0-9]{6,8}$') |
            Q(subject='') |
            Q(subject__isnull=True) |
            Q(subject__iregex=r'^Chat [a-zA-Z0-9_-]{8}$')
        ).select_related('channel').order_by('-created_at')[:limit]

        updated_count = 0
        analyzed_count = 0

        for conversation in conversations:
            try:
                analyzed_count += 1
                
                # Get the first message for contact info
                first_message = conversation.messages.order_by('created_at').first()
                if not first_message:
                    continue

                # Extract contact info from message
                contact_info = {
                    'from': first_message.contact_phone or first_message.contact_email,
                    'phone': first_message.contact_phone,
                    'email': first_message.contact_email,
                }

                # Add metadata if available
                if hasattr(first_message, 'metadata') and first_message.metadata:
                    contact_info.update(first_message.metadata)

                # Generate new name
                new_subject = conversation_naming_service.generate_conversation_name(
                    channel_type=conversation.channel.channel_type,
                    contact_info=contact_info,
                    message_content=first_message.content if first_message.content else '',
                    external_thread_id=str(conversation.external_thread_id) if conversation.external_thread_id else ''
                )

                # Check if name would be better
                old_subject = conversation.subject
                name_improved = (
                    new_subject != old_subject and
                    not new_subject.startswith('Conversation ') and
                    not new_subject.startswith('Chat ') and
                    (any(indicator in new_subject for indicator in ['Contact +', '@', '.']) or
                     len(new_subject.split()) > 2)
                )

                if name_improved:
                    self.stdout.write(
                        f"  📝 {conversation.channel.channel_type.upper()}: "
                        f"'{old_subject}' → '{new_subject}'"
                    )

                    if not dry_run:
                        conversation.subject = new_subject
                        conversation.save(update_fields=['subject'])
                        updated_count += 1

                elif dry_run:
                    self.stdout.write(
                        f"  ⏭️  {conversation.channel.channel_type.upper()}: "
                        f"'{old_subject}' (no improvement found)"
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ❌ Error updating conversation {conversation.id}: {e}")
                )

        if analyzed_count > 0:
            improvement_rate = (updated_count / analyzed_count) * 100 if not dry_run else 0
            self.stdout.write(
                f"  📊 Analyzed: {analyzed_count}, "
                f"{'Would update' if dry_run else 'Updated'}: {updated_count}"
                f"{f' ({improvement_rate:.1f}% improvement rate)' if not dry_run else ''}"
            )
        else:
            self.stdout.write("  ℹ️  No conversations found matching criteria")

        return updated_count

    def update_conversations_from_contacts(self, tenant_schema, channel_type, dry_run, limit):
        """
        Alternative method: Update conversations by linking with contact records
        This can find better names by using CRM contact data
        """
        try:
            # Run async method
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                if channel_type:
                    # Update specific channel type
                    account_ids = list(
                        Conversation.objects.filter(
                            channel__channel_type=channel_type
                        ).values_list('channel__unipile_account_id', flat=True).distinct()
                    )
                    
                    updated_count = 0
                    for account_id in account_ids:
                        if not dry_run:
                            count = loop.run_until_complete(
                                conversation_naming_service.update_conversation_names_from_contacts(
                                    channel_type, account_id
                                )
                            )
                            updated_count += count
                        else:
                            self.stdout.write(f"  Would update conversations for {channel_type} account {account_id}")
                    
                    return updated_count
                else:
                    # Update all channel types
                    channel_types = ['whatsapp', 'email', 'linkedin', 'sms']
                    total_updated = 0
                    
                    for ch_type in channel_types:
                        account_ids = list(
                            Conversation.objects.filter(
                                channel__channel_type=ch_type
                            ).values_list('channel__unipile_account_id', flat=True).distinct()
                        )
                        
                        for account_id in account_ids:
                            if not dry_run:
                                count = loop.run_until_complete(
                                    conversation_naming_service.update_conversation_names_from_contacts(
                                        ch_type, account_id
                                    )
                                )
                                total_updated += count
                            else:
                                self.stdout.write(f"  Would update conversations for {ch_type} account {account_id}")
                    
                    return total_updated
                    
            finally:
                loop.close()
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error in async conversation update: {e}")
            )
            return 0