"""
Management command for batch contact resolution and auto-creation
"""
import asyncio
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

from communications.models import Conversation, Message
from communications.contact_resolver import contact_resolver

User = get_user_model()


class Command(BaseCommand):
    help = 'Batch resolve and create contacts from conversations and messages'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--conversations',
            action='store_true',
            help='Resolve contacts from conversations'
        )
        
        parser.add_argument(
            '--messages',
            action='store_true',
            help='Resolve contacts from individual messages'
        )
        
        parser.add_argument(
            '--unlinked-only',
            action='store_true',
            help='Only process conversations/messages without linked contacts'
        )
        
        parser.add_argument(
            '--deduplicate',
            action='store_true',
            help='Run contact deduplication after resolution'
        )
        
        parser.add_argument(
            '--enrich',
            action='store_true',
            help='Enrich contacts with external data sources'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of items to process (default: 100)'
        )
        
        parser.add_argument(
            '--tenant',
            type=str,
            help='Specify tenant schema (for multi-tenant setups)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making changes'
        )
    
    def handle(self, *args, **options):
        """Handle the command execution"""
        
        try:
            # Set up tenant context if specified
            if options.get('tenant'):
                self._setup_tenant_context(options['tenant'])
            
            # Run async processing
            asyncio.run(self._run_contact_resolution(options))
            
        except Exception as e:
            raise CommandError(f'Contact resolution failed: {e}')
    
    def _setup_tenant_context(self, tenant_schema):
        """Setup tenant context for multi-tenant environments"""
        try:
            from django_tenants.utils import schema_context
            from tenants.models import Tenant
            
            tenant = Tenant.objects.get(schema_name=tenant_schema)
            schema_context(tenant.schema_name).__enter__()
            
            self.stdout.write(
                self.style.SUCCESS(f'Using tenant: {tenant.name} ({tenant_schema})')
            )
            
        except ImportError:
            self.stdout.write(
                self.style.WARNING('django-tenants not available, using default schema')
            )
        except Exception as e:
            raise CommandError(f'Failed to setup tenant context: {e}')
    
    async def _run_contact_resolution(self, options):
        """Run the contact resolution process"""
        
        conversations = options.get('conversations', False)
        messages = options.get('messages', False)
        unlinked_only = options.get('unlinked_only', False)
        deduplicate = options.get('deduplicate', False)
        enrich = options.get('enrich', False)
        limit = options.get('limit', 100)
        dry_run = options.get('dry_run', False)
        
        # Default to processing conversations if nothing specified
        if not conversations and not messages:
            conversations = True
        
        total_processed = 0
        total_created = 0
        total_errors = 0
        
        # Process conversations
        if conversations:
            self.stdout.write('\n--- Processing Conversations ---')
            
            result = await self._process_conversations(unlinked_only, limit, dry_run)
            total_processed += result['processed']
            total_created += result['created']
            total_errors += result['errors']
        
        # Process individual messages
        if messages:
            self.stdout.write('\n--- Processing Messages ---')
            
            result = await self._process_messages(unlinked_only, limit, dry_run)
            total_processed += result['processed']
            total_created += result['created']
            total_errors += result['errors']
        
        # Run deduplication
        if deduplicate and not dry_run:
            self.stdout.write('\n--- Contact Deduplication ---')
            await self._run_deduplication()
        
        # Run enrichment
        if enrich and not dry_run:
            self.stdout.write('\n--- Contact Enrichment ---')
            await self._run_enrichment(limit)
        
        # Show summary
        self._show_summary(total_processed, total_created, total_errors, dry_run)
    
    async def _process_conversations(self, unlinked_only, limit, dry_run):
        """Process conversations for contact resolution"""
        
        try:
            # Build query
            query = Conversation.objects.select_related('user_channel', 'primary_contact')
            
            if unlinked_only:
                query = query.filter(primary_contact__isnull=True)
            
            conversations = await sync_to_async(list)(query[:limit])
            
            if not conversations:
                self.stdout.write('No conversations found to process')
                return {'processed': 0, 'created': 0, 'errors': 0}
            
            self.stdout.write(f'Found {len(conversations)} conversations to process')
            
            if dry_run:
                self.stdout.write('[DRY RUN] Would process these conversations:')
                for conv in conversations[:10]:  # Show first 10
                    status = 'unlinked' if not conv.primary_contact else 'linked'
                    participants = len(conv.participants)
                    self.stdout.write(f'  - {conv.id}: {participants} participants ({status})')
                
                if len(conversations) > 10:
                    self.stdout.write(f'  ... and {len(conversations) - 10} more')
                
                return {'processed': len(conversations), 'created': 0, 'errors': 0}
            
            # Process in batches
            batch_size = 10
            processed = 0
            created = 0
            errors = 0
            
            for i in range(0, len(conversations), batch_size):
                batch = conversations[i:i + batch_size]
                
                self.stdout.write(f'Processing batch {i//batch_size + 1}...')
                
                batch_result = await contact_resolver.batch_resolve_contacts(batch)
                
                if batch_result['success']:
                    processed += batch_result['successful_resolutions']
                    created += batch_result['contacts_created']
                    errors += batch_result['errors']
                    
                    self.stdout.write(
                        f'  Batch complete: {batch_result["successful_resolutions"]} resolved, '
                        f'{batch_result["contacts_created"]} created'
                    )
                else:
                    errors += len(batch)
                    self.stdout.write(
                        self.style.ERROR(f'  Batch failed: {batch_result["error"]}')
                    )
            
            return {'processed': processed, 'created': created, 'errors': errors}
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Conversation processing failed: {e}'))
            return {'processed': 0, 'created': 0, 'errors': 1}
    
    async def _process_messages(self, unlinked_only, limit, dry_run):
        """Process individual messages for contact resolution"""
        
        try:
            # Build query for messages without linked conversations or contacts
            query = Message.objects.select_related(
                'conversation', 
                'conversation__user_channel',
                'conversation__primary_contact'
            ).filter(direction='inbound')
            
            if unlinked_only:
                query = query.filter(conversation__primary_contact__isnull=True)
            
            messages = await sync_to_async(list)(query[:limit])
            
            if not messages:
                self.stdout.write('No messages found to process')
                return {'processed': 0, 'created': 0, 'errors': 0}
            
            self.stdout.write(f'Found {len(messages)} messages to process')
            
            if dry_run:
                self.stdout.write('[DRY RUN] Would process these messages:')
                for msg in messages[:10]:  # Show first 10
                    sender = msg.sender_name or msg.sender_email or 'Unknown'
                    self.stdout.write(f'  - {msg.id}: from {sender} ({msg.created_at})')
                
                if len(messages) > 10:
                    self.stdout.write(f'  ... and {len(messages) - 10} more')
                
                return {'processed': len(messages), 'created': 0, 'errors': 0}
            
            # Process messages individually
            processed = 0
            created = 0
            errors = 0
            
            for i, message in enumerate(messages):
                try:
                    if i % 10 == 0:
                        self.stdout.write(f'Processing message {i + 1}/{len(messages)}...')
                    
                    # Extract message data
                    message_data = {
                        'id': message.external_message_id,
                        'content': message.content,
                        'sender': {
                            'email': message.sender_email,
                            'name': message.sender_name,
                            'phone': message.sender_phone
                        },
                        'timestamp': message.created_at.isoformat()
                    }
                    
                    # Resolve contact
                    result = await contact_resolver.resolve_contact_from_message(
                        message_data=message_data,
                        user_channel=message.conversation.user_channel,
                        direction='inbound'
                    )
                    
                    if result['success']:
                        processed += 1
                        if result.get('created'):
                            created += 1
                            
                        # Link conversation if not already linked
                        if not message.conversation.primary_contact:
                            message.conversation.primary_contact = result['contact_record']
                            await sync_to_async(message.conversation.save)()
                    else:
                        errors += 1
                        if i < 5:  # Show first few errors
                            self.stdout.write(
                                self.style.WARNING(f'  Message {message.id}: {result["error"]}')
                            )
                        
                except Exception as e:
                    errors += 1
                    self.stdout.write(
                        self.style.ERROR(f'Failed to process message {message.id}: {e}')
                    )
            
            return {'processed': processed, 'created': created, 'errors': errors}
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Message processing failed: {e}'))
            return {'processed': 0, 'created': 0, 'errors': 1}
    
    async def _run_deduplication(self):
        """Run contact deduplication"""
        
        try:
            from pipelines.models import Pipeline
            
            # Get all pipelines with contacts
            pipelines = await sync_to_async(list)(
                Pipeline.objects.filter(
                    records__isnull=False
                ).distinct()
            )
            
            if not pipelines:
                self.stdout.write('No pipelines with contacts found')
                return
            
            total_duplicates = 0
            total_merged = 0
            
            for pipeline in pipelines:
                self.stdout.write(f'Deduplicating contacts in pipeline: {pipeline.name}')
                
                result = await contact_resolver.deduplicate_contacts(
                    pipeline=pipeline,
                    similarity_threshold=0.8
                )
                
                if result['success']:
                    duplicates = result['duplicates_found']
                    merged = result['contacts_merged']
                    
                    total_duplicates += duplicates
                    total_merged += merged
                    
                    if duplicates > 0:
                        self.stdout.write(
                            f'  Found {duplicates} duplicate groups, merged {merged} contacts'
                        )
                    else:
                        self.stdout.write('  No duplicates found')
                else:
                    self.stdout.write(
                        self.style.ERROR(f'  Deduplication failed: {result["error"]}')
                    )
            
            if total_duplicates > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Deduplication complete: {total_duplicates} duplicate groups, '
                        f'{total_merged} contacts merged'
                    )
                )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Deduplication failed: {e}'))
    
    async def _run_enrichment(self, limit):
        """Run contact enrichment"""
        
        try:
            from pipelines.models import Record
            
            # Get contacts with email addresses that haven't been enriched recently
            contacts = await sync_to_async(list)(
                Record.objects.filter(
                    data__email__isnull=False,
                    data___enrichment__isnull=True,
                    is_deleted=False
                )[:limit]
            )
            
            if not contacts:
                self.stdout.write('No contacts found for enrichment')
                return
            
            self.stdout.write(f'Enriching {len(contacts)} contacts...')
            
            enriched_count = 0
            
            for i, contact in enumerate(contacts):
                try:
                    if i % 10 == 0:
                        self.stdout.write(f'Enriching contact {i + 1}/{len(contacts)}...')
                    
                    result = await contact_resolver.enrich_contact_from_external_sources(
                        contact=contact,
                        sources=['clearbit', 'hunter']  # Enable when API keys available
                    )
                    
                    if result['success'] and result['fields_enriched']:
                        enriched_count += 1
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Failed to enrich contact {contact.id}: {e}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f'Enrichment complete: {enriched_count} contacts enriched')
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Enrichment failed: {e}'))
    
    def _show_summary(self, processed, created, errors, dry_run):
        """Show processing summary"""
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write('CONTACT RESOLUTION SUMMARY')
        self.stdout.write('='*50)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN] No changes were made'))
        
        self.stdout.write(f'Total processed: {processed}')
        self.stdout.write(f'Contacts created: {created}')
        
        if errors > 0:
            self.stdout.write(self.style.ERROR(f'Errors: {errors}'))
        else:
            self.stdout.write(self.style.SUCCESS('No errors'))
        
        if processed > 0 and not dry_run:
            success_rate = ((processed - errors) / processed) * 100
            self.stdout.write(f'Success rate: {success_rate:.1f}%')
        
        self.stdout.write('='*50)