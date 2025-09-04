"""
Record Sync Orchestrator - Orchestrates the entire record sync process

This is the main service that coordinates all the components to sync
communications for a specific record.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from pipelines.models import Record
from communications.models import UserChannelConnection, Channel
from communications.unipile.core.client import UnipileClient

from ..models import (
    RecordCommunicationProfile, RecordSyncJob, RecordAttendeeMapping
)
from ..unipile_integration import (
    AttendeeResolver, MessageFetcher, DataTransformer
)
from ..unipile_integration.message_enricher import MessageEnricher
from ..unipile_integration.email_fetcher_v2 import EmailFetcherV2
from ..unipile_integration.conversation_fetcher import ConversationFetcher
from ..storage import (
    ConversationStore, MessageStore, ParticipantLinkManager, MetricsUpdater
)
from ..utils import get_sync_config, ProviderIdBuilder
from .identifier_extractor import RecordIdentifierExtractor
from communications.services.field_manager import field_manager

logger = logging.getLogger(__name__)


class RecordSyncOrchestrator:
    """Orchestrates the complete record sync process"""
    
    def __init__(self, unipile_client: Optional[UnipileClient] = None):
        """
        Initialize the orchestrator
        
        Args:
            unipile_client: Optional UnipileClient instance
        """
        self.unipile_client = unipile_client
        self.sync_config = get_sync_config()
        
        # Initialize services
        self.identifier_extractor = RecordIdentifierExtractor()
        
        # UniPile integration
        self.attendee_resolver = AttendeeResolver(unipile_client) if unipile_client else None
        self.email_fetcher = EmailFetcherV2(unipile_client) if unipile_client else None
        self.message_fetcher = MessageFetcher(unipile_client) if unipile_client else None
        self.conversation_fetcher = ConversationFetcher(unipile_client) if unipile_client else None
        self.data_transformer = DataTransformer()
        self.message_enricher = MessageEnricher()
        
        # Storage
        self.conversation_store = ConversationStore()
        self.message_store = MessageStore()
        self.participant_link_manager = ParticipantLinkManager()
        self.metrics_updater = MetricsUpdater()
    
    def sync_record(
        self,
        record_id: int,
        triggered_by=None,
        trigger_reason: str = 'Manual sync',
        sync_job: Optional[RecordSyncJob] = None,
        channels_to_sync: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Sync all communications for a record
        
        This is the main entry point for record sync.
        
        Args:
            record_id: ID of the record to sync
            triggered_by: User who triggered the sync
            trigger_reason: Why this sync was triggered
            sync_job: Optional existing sync job
            channels_to_sync: Optional list of specific channels to sync (e.g., ['gmail', 'whatsapp'])
            
        Returns:
            Dict with sync results
        """
        try:
            # Get the record
            record = Record.objects.select_related('pipeline').get(id=record_id)
            
            # Get or create communication profile
            profile, created = RecordCommunicationProfile.objects.get_or_create(
                record=record,
                defaults={
                    'pipeline': record.pipeline,
                    'created_by': triggered_by
                }
            )
            
            # Create sync job if not provided, otherwise update existing one
            if not sync_job:
                sync_job = RecordSyncJob.objects.create(
                    record=record,
                    profile=profile,
                    job_type='full_history',
                    triggered_by=triggered_by,
                    trigger_reason=trigger_reason,
                    status='running',
                    started_at=timezone.now()
                )
                
                # Use field manager to set trigger information
                field_manager.set_sync_job_trigger(
                    sync_job, 
                    user=triggered_by, 
                    reason=trigger_reason or 'Manual sync'
                )
            else:
                # Update existing sync job status if it's still pending
                if sync_job.status == 'pending':
                    sync_job.status = 'running'
                    sync_job.started_at = timezone.now()
                    sync_job.save(update_fields=['status', 'started_at'])
                    logger.info(f"Updated existing sync job {sync_job.id} to running status")
            
            # Mark sync in progress
            profile.mark_sync_started()
            
            try:
                # Step 1: Extract identifiers from record
                logger.info(f"Extracting identifiers for record {record_id}")
                identifiers = self.identifier_extractor.extract_identifiers_from_record(record)
                identifier_fields = self.identifier_extractor.get_identifier_fields(record.pipeline_id)
                
                # Store identifiers in profile
                profile.communication_identifiers = identifiers
                profile.identifier_fields = identifier_fields
                profile.save()
                
                # Step 2: Get available channel connections
                connections = UserChannelConnection.objects.filter(
                    is_active=True,
                    account_status='active'
                ).select_related('user')
                
                # Log channel filter if provided
                if channels_to_sync:
                    logger.info(f"Filtering sync to specific channels: {channels_to_sync}")
                else:
                    logger.info("Syncing all available channels")
                
                # Track overall results
                total_conversations = 0
                total_messages = 0
                channel_results = {}
                
                # Special case: If only syncing 'domain' channel, skip API calls and just link participants
                if channels_to_sync == ['domain']:
                    logger.info(f"🔗 Domain-only sync requested - skipping API calls, doing lightweight participant linking")
                    logger.info(f"   📊 Extracted identifiers: {identifiers}")
                    logger.info(f"   🌐 Domain identifiers: {identifiers.get('domain', [])}")
                    # Skip the expensive API sync and go straight to domain linking below
                else:
                    # Step 3: Sync each channel
                    for connection in connections:
                        channel_type = connection.channel_type
                        
                        # Check if we should sync this channel based on filter
                        if channels_to_sync and channel_type not in channels_to_sync:
                            logger.info(f"Skipping channel {channel_type} - not in channels_to_sync filter: {channels_to_sync}")
                            continue
                        
                        # Check if channel is enabled
                        if not self.sync_config.is_channel_enabled(channel_type):
                            logger.info(f"Skipping disabled channel: {channel_type}")
                            continue
                        
                        # Get or create channel
                        channel, _ = Channel.objects.get_or_create(
                            channel_type=channel_type,
                            unipile_account_id=connection.unipile_account_id,
                            defaults={
                                'name': f"{channel_type.title()} Channel",
                                'auth_status': 'authenticated'
                            }
                        )
                        
                        # Sync this channel
                        logger.info(f"Syncing {channel_type} for record {record_id}")
                        
                        if channel_type in ['email', 'gmail']:
                            result = self._sync_email_channel(
                            identifiers.get('email', []),
                            record,
                            channel,
                            connection,
                            sync_job,
                            identifiers
                        )
                        else:
                            # Use messaging sync for WhatsApp/LinkedIn
                            result = self._sync_messaging_channel(
                            identifiers,
                            record,
                            channel,
                            connection,
                            channel_type,
                            sync_job
                        )
                        
                        channel_results[channel_type] = result
                        total_conversations += result.get('conversations', 0)
                        total_messages += result.get('messages', 0)
                
                # Step 4: Link any existing participants that match this record's identifiers
                logger.info(f"Linking existing participants to record {record_id}")
                self._link_existing_participants_to_record(record, identifiers)
                
                # Step 4b: Link participants by domain if this record has domain identifiers
                logger.info(f"Checking for domain-based secondary linking for record {record_id}")
                # Pass the extracted domains from identifiers
                domains = identifiers.get('domain', [])
                logger.info(f"   🌐 Domains to link: {domains}")
                if domains:
                    logger.info(f"   🔗 Calling _link_existing_participants_by_domain with domains: {domains}")
                    self._link_existing_participants_by_domain(record, domains)
                else:
                    logger.info(f"   ⏭️  No domains found in identifiers, skipping domain linking")
                
                # Step 5: Update metrics
                logger.info(f"Updating metrics for record {record_id}")
                self.metrics_updater.update_profile_metrics(record)
                
                # Mark sync successful
                sync_job.messages_found = total_messages
                sync_job.conversations_found = total_conversations
                sync_job.save(update_fields=['messages_found', 'conversations_found'])
                
                # Update sync job progress with field manager
                field_manager.update_sync_job_progress(
                    sync_job,
                    accounts_synced=len(connections),
                    total_accounts=len(connections)
                )
                
                sync_job.mark_completed()
                
                logger.info(
                    f"Sync completed for record {record_id}: "
                    f"{total_conversations} conversations, {total_messages} messages"
                )
                
                return {
                    'success': True,
                    'record_id': record_id,
                    'total_conversations': total_conversations,
                    'total_messages': total_messages,
                    'channel_results': channel_results
                }
                
            except Exception as e:
                # Handle sync errors
                logger.error(f"Error during sync for record {record_id}: {e}")
                
                sync_job.mark_failed(str(e))
                
                raise
                
            finally:
                # Mark sync complete in profile
                if sync_job.status == 'completed':
                    profile.mark_sync_completed(sync_job.messages_found)
                    
                    # Schedule next auto-sync if enabled
                    field_manager.schedule_auto_sync(profile)
                else:
                    # Just clear the in_progress flag if sync failed
                    profile.sync_in_progress = False
                    profile.save(update_fields=['sync_in_progress'])
                
        except Exception as e:
            logger.error(f"Failed to sync record {record_id}: {e}")
            return {
                'success': False,
                'record_id': record_id,
                'error': str(e)
            }
    
    def _sync_email_channel(
        self,
        email_addresses: List[str],
        record: Record,
        channel: Channel,
        connection: UserChannelConnection,
        sync_job: RecordSyncJob,
        identifiers: Dict[str, List[str]] = None
    ) -> Dict[str, int]:
        """
        Sync email channel for a record
        
        Args:
            email_addresses: List of email addresses to sync
            record: Record instance
            channel: Channel instance
            connection: UserChannelConnection instance
            sync_job: RecordSyncJob instance
            
        Returns:
            Dict with sync statistics
        """
        logger.info(f"=== EMAIL CHANNEL SYNC START for Record {record.id} ===")
        logger.info(f"Email addresses to sync: {email_addresses}")
        
        if not email_addresses or not self.email_fetcher:
            logger.warning(f"No email addresses or email fetcher not available")
            return {'conversations': 0, 'messages': 0}
        
        try:
            # Get sync configuration - use the actual channel type
            channel_type = connection.channel_type
            config = self.sync_config.get_channel_config(channel_type if channel_type == 'gmail' else 'email')
            
            logger.info(f"Channel type: {channel_type}")
            logger.info(f"Account ID: {connection.unipile_account_id}")
            logger.info(f"Config - Historical days: {config['historical_days']}, Max messages: {config['max_messages']}")
            
            # Fetch emails from UniPile
            logger.info(f"Calling email_fetcher.fetch_emails_for_addresses...")
            email_data = self.email_fetcher.fetch_emails_for_addresses(
                email_addresses=email_addresses,
                account_id=connection.unipile_account_id,
                days_back=config['historical_days'],
                max_emails=config['max_messages']
            )
            
            total_conversations = 0
            total_messages = 0
            
            # Collect ALL email messages first to build shared participant cache
            all_email_messages = []
            threads_to_process = []
            all_attendee_info = {}  # Initialize for email sync as well
            
            # Collect attendee names from email threads
            # PRIORITIZE FROM (sender) names as they're more reliable
            all_attendee_names = {}
            from_names = {}  # Track names from FROM field separately
            
            # Process each email address
            for email_address, threads in email_data.items():
                logger.info(f"Processing {len(threads)} threads for email {email_address}")
                for thread_idx, thread_data in enumerate(threads):
                    thread_messages = thread_data.get('messages', [])
                    logger.info(f"  Thread {thread_idx + 1}: {thread_data.get('subject', 'No subject')[:50]}...")
                    logger.info(f"    Thread ID: {thread_data.get('thread_id', 'None')}")
                    logger.info(f"    Message count: {len(thread_messages)}")
                    
                    if not thread_messages:
                        logger.warning(f"    ⚠️ EMPTY THREAD - no messages returned by UniPile!")
                    
                    # First pass: Collect FROM names (most reliable)
                    for msg_data in thread_messages:
                        from_attendee = msg_data.get('from_attendee', {})
                        if from_attendee:
                            email_id = from_attendee.get('identifier', '').lower()
                            display_name = from_attendee.get('display_name', '')
                            
                            # Clean up display name - remove quotes and check if it's just the email
                            if display_name:
                                # Strip surrounding quotes
                                cleaned_name = display_name.strip().strip("'\"")
                                
                                # If it's not just the email address, store it
                                if cleaned_name and cleaned_name.lower() != email_id:
                                    # FROM names are the most reliable - always use them
                                    from_names[email_id] = cleaned_name
                                    all_attendee_names[email_id] = cleaned_name
                                    logger.debug(f"Found FROM name for {email_id}: '{cleaned_name}'")
                    
                    # Second pass: Collect TO/CC/BCC names only if we don't have a FROM name
                    for msg_data in thread_data.get('messages', []):
                        for field in ['to_attendees', 'cc_attendees', 'bcc_attendees']:
                            for attendee in msg_data.get(field, []):
                                email_id = attendee.get('identifier', '').lower()
                                display_name = attendee.get('display_name', '')
                                
                                # Only use TO/CC/BCC names if we don't have a FROM name for this email
                                if email_id not in from_names and display_name:
                                    # Clean up display name
                                    cleaned_name = display_name.strip().strip("'\"")
                                    
                                    # If it's not just the email address and better than what we have
                                    if cleaned_name and cleaned_name.lower() != email_id:
                                        if email_id not in all_attendee_names or len(cleaned_name) > len(all_attendee_names.get(email_id, '')):
                                            all_attendee_names[email_id] = cleaned_name
                                            logger.debug(f"Found TO/CC/BCC name for {email_id}: '{cleaned_name}'")
                    
                    # Also check thread participants (but FROM names still take priority)
                    for participant in thread_data.get('participants', []):
                        email_id = participant.get('email', '').lower()
                        name = participant.get('name', '')
                        
                        # Only use participant name if we don't have a FROM name
                        if email_id not in from_names and email_id and name and name != email_id:
                            cleaned_name = name.strip().strip("'\"")
                            if cleaned_name and cleaned_name.lower() != email_id:
                                if email_id not in all_attendee_names or len(cleaned_name) > len(all_attendee_names.get(email_id, '')):
                                    all_attendee_names[email_id] = cleaned_name
                    
                    # Transform and store conversation
                    conv_data = self.data_transformer.transform_email_thread(
                        thread_data,
                        channel.id
                    )
                    conversation = self.conversation_store.store_conversation(
                        conv_data,
                        channel
                    )
                    
                    # Transform all messages for bulk storage
                    messages_data = thread_data.get('messages', [])
                    transformed_messages = []
                    for msg_data in messages_data:
                        msg_transformed = self.data_transformer.transform_email_message(
                            msg_data,
                            conversation.id,
                            channel.id
                        )
                        transformed_messages.append(msg_transformed)
                        all_email_messages.append(msg_transformed)  # Collect for cache building
                    
                    # Store for processing
                    threads_to_process.append({
                        'conversation': conversation,
                        'messages': transformed_messages,
                        'email_address': email_address
                    })
                    
                    total_conversations += 1
                    total_messages += len(messages_data)
            
            logger.info(f"Collected {len(all_attendee_names)} unique email attendee names")
            
            # DEBUG: Log what names we collected
            for email, name in list(all_attendee_names.items())[:5]:
                logger.info(f"  Attendee: {email} -> '{name}'")
            
            # Build shared participant cache for ALL email messages with attendee names
            logger.info(f"Building participant cache for {len(all_email_messages)} email messages")
            participant_cache = self.message_store.build_participant_cache_for_all_messages(
                all_email_messages,
                attendee_names=all_attendee_names,
                attendee_info=all_attendee_info
            )
            
            # Now store all messages using the shared cache
            for thread_info in threads_to_process:
                if thread_info['messages']:
                    self.message_store.store_bulk_messages(
                        thread_info['messages'],
                        thread_info['conversation'],
                        channel,
                        participant_cache  # Pass shared cache
                    )
                
                # Link participants to record instead of creating RecordCommunicationLinks
                # The participants are in the cache, link them to this record
                if identifiers:
                    for participant in participant_cache.values():
                        if not participant.contact_record and participant.email:
                            # Check if this participant's email matches any of the record's identifiers
                            if participant.email in identifiers.get('email', []):
                                self.participant_link_manager.link_participant_to_record(
                                    participant=participant,
                                    record=record,
                                    confidence=0.95,
                                    method='sync_email_match'
                                )
                                logger.info(f"Linked participant {participant.id} ({participant.email}) to record {record.id}")
            
            logger.info(f"Synced {total_conversations} email conversations for record {record.id}")
            return {'conversations': total_conversations, 'messages': total_messages}
            
        except Exception as e:
            logger.error(f"Error syncing emails for record {record.id}: {e}")
            return {'conversations': 0, 'messages': 0}
    
    def _sync_messaging_channel(
        self,
        identifiers: Dict[str, List[str]],
        record: Record,
        channel: Channel,
        connection: UserChannelConnection,
        channel_type: str,
        sync_job: RecordSyncJob
    ) -> Dict[str, int]:
        """
        Sync messaging channel (WhatsApp, LinkedIn, etc.) for a record
        Uses per-chat attendee fetching for accurate name resolution
        
        Args:
            identifiers: All identifiers for the record
            record: Record instance
            channel: Channel instance
            connection: UserChannelConnection instance
            channel_type: Type of messaging channel
            sync_job: RecordSyncJob instance
            
        Returns:
            Dict with sync statistics
        """
        if not self.attendee_resolver or not self.message_fetcher:
            return {'conversations': 0, 'messages': 0}
        
        try:
            # Get sync configuration
            config = self.sync_config.get_channel_config(channel_type)
            
            # Step 1: Resolve record identifiers to specific attendees
            logger.info(f"Resolving {channel_type} identifiers to attendees")
            attendee_map = self.attendee_resolver.resolve_messaging_attendees(
                identifiers=identifiers,
                channel_type=channel_type,
                account_id=connection.unipile_account_id
            )
            
            if not attendee_map:
                logger.info(f"No attendees found for {channel_type} identifiers")
                return {'conversations': 0, 'messages': 0}
            
            logger.info(f"Found {len(attendee_map)} attendees for {channel_type}")
            
            # Store attendee mappings for future use
            self._store_attendee_mappings(
                attendee_map,
                record,
                channel_type,
                sync_job.profile
            )
            
            # Step 2: Fetch messages for those specific attendees
            message_data = self.message_fetcher.fetch_messages_for_attendees(
                attendee_map=attendee_map,
                account_id=connection.unipile_account_id,
                channel_type=channel_type,
                days_back=config.get('historical_days', 30),
                max_messages_per_attendee=config.get('max_messages', 500)
            )
            
            if not message_data:
                logger.info(f"No {channel_type} messages found")
                return {'conversations': 0, 'messages': 0}
            
            total_conversations = 0
            total_messages = 0
            
            # Get account owner's provider ID from connection config
            account_provider_id = connection.provider_config.get('provider_id') or connection.provider_config.get('account_provider_id')
            if not account_provider_id:
                account_provider_id = connection.unipile_account_id
                logger.warning(f"No provider_id in connection config for {channel_type}, using unipile_account_id: {account_provider_id}")
            
            # Step 3: Process conversations and fetch chat-specific attendees
            all_channel_messages = []
            conversations_to_process = []
            
            from asgiref.sync import async_to_sync
            
            for attendee_id, attendee_data in message_data.items():
                # Get the original resolved attendee info for this attendee
                original_attendee_info = attendee_map.get(attendee_id, {}) if attendee_map else {}
                for conv_data in attendee_data['conversations']:
                    chat_id = conv_data.get('chat_id')
                    
                    # Step 3a: Fetch chat-specific attendees for better name resolution
                    chat_attendees = {}
                    if chat_id and self.unipile_client:
                        try:
                            logger.debug(f"Fetching attendees for chat {chat_id}")
                            response = async_to_sync(self.unipile_client.messaging.get_attendees_from_chat)(
                                chat_id=chat_id,
                                limit=100
                            )
                            
                            if response and 'items' in response:
                                for attendee in response['items']:
                                    att_id = attendee.get('id', '')
                                    if att_id:
                                        attendee_info = {
                                            'name': attendee.get('name', ''),
                                            'provider_id': attendee.get('provider_id', '')
                                        }
                                        # Store by multiple keys for better matching
                                        chat_attendees[att_id] = attendee_info
                                        if attendee.get('provider_id'):
                                            chat_attendees[attendee['provider_id']] = attendee_info
                                            # For WhatsApp, also store by phone
                                            if channel_type == 'whatsapp' and '@s.whatsapp.net' in attendee['provider_id']:
                                                phone = attendee['provider_id'].replace('@s.whatsapp.net', '')
                                                if phone:
                                                    chat_attendees[phone] = attendee_info
                                
                                logger.debug(f"Found {len(response['items'])} attendees for chat {chat_id}")
                        except Exception as e:
                            logger.warning(f"Failed to fetch attendees for chat {chat_id}: {e}")
                    
                    # Add account owner's name to attendees if available
                    if connection.account_name and account_provider_id:
                        # For WhatsApp, extract phone from account name if needed
                        account_phone = None
                        if channel_type == 'whatsapp':
                            # Try to extract phone from account name like "WhatsApp (27720720047)"
                            import re
                            phone_match = re.search(r'\((\+?\d+)\)', connection.account_name)
                            if phone_match:
                                account_phone = phone_match.group(1).replace('+', '')
                                logger.debug(f"Extracted phone {account_phone} from account name")
                        
                        # Store account owner's name by multiple keys
                        account_owner_info = {
                            'name': connection.account_name,
                            'provider_id': account_provider_id,
                            'is_account_owner': True
                        }
                        
                        # For WhatsApp, add phone info if available
                        if account_phone:
                            account_owner_info['phone'] = account_phone
                            logger.info(f"Added phone {account_phone} to account owner info for {channel_type}")
                        
                        chat_attendees[account_provider_id] = account_owner_info
                        
                        # For WhatsApp, also store by phone
                        if channel_type == 'whatsapp':
                            if '@s.whatsapp.net' in account_provider_id:
                                phone = account_provider_id.replace('@s.whatsapp.net', '')
                                if phone:
                                    chat_attendees[phone] = account_owner_info
                            elif account_phone:
                                # If we extracted a phone from the name, store by that
                                chat_attendees[account_phone] = account_owner_info
                        
                        logger.debug(f"Added account owner '{connection.account_name}' to attendees")
                    
                    # Transform conversation
                    chat_transformed = self.data_transformer.transform_chat_conversation(
                        conv_data.get('chat_data', {}),
                        channel.id,
                        channel_type
                    )
                    conversation = self.conversation_store.store_conversation(
                        chat_transformed,
                        channel
                    )
                    
                    # Enrich messages with sender information before transformation
                    enriched_messages = self.message_enricher.enrich_messages(
                        conv_data.get('messages', []),
                        channel_type,
                        account_provider_id,
                        attendee_id_to_info=chat_attendees  # Use chat-specific attendees
                    )
                    
                    # Transform messages
                    transformed_messages = []
                    for msg_data in enriched_messages:
                        msg_transformed = self.data_transformer.transform_chat_message(
                            msg_data,
                            conversation.id,
                            channel.id,
                            channel_type,
                            account_provider_id
                        )
                        transformed_messages.append(msg_transformed)
                        all_channel_messages.append(msg_transformed)
                    
                    # Store conversation info with attendees
                    conversations_to_process.append({
                        'conversation': conversation,
                        'messages': transformed_messages,
                        'attendees': chat_attendees,  # Store chat attendees for cache building
                        'attendee_info': attendee_data.get('attendee_info', {}),
                        'original_attendee_info': original_attendee_info  # Store the resolved attendee info
                    })
                    
                    total_conversations += 1
                    total_messages += len(conv_data.get('messages', []))
            
            # Step 4: Build participant cache from chat attendees
            logger.info(f"Building participant cache for {len(all_channel_messages)} {channel_type} messages")
            
            # Collect all attendee names AND full info from all chats
            all_attendee_names = {}
            all_attendee_info = {}  # Store full attendee info for metadata
            
            # First, add the original resolved attendee info (has linkedin_id for LinkedIn)
            for conv_info in conversations_to_process:
                if conv_info.get('original_attendee_info'):
                    orig_info = conv_info['original_attendee_info']
                    if orig_info.get('provider_id'):
                        # IMPORTANT: Store by provider_id so participant creation can find it
                        all_attendee_names[orig_info['provider_id']] = orig_info.get('name', '')
                        all_attendee_info[orig_info['provider_id']] = orig_info
                        
                        # For LinkedIn, also store by linkedin_id
                        if orig_info.get('linkedin_id'):
                            all_attendee_names[orig_info['linkedin_id']] = orig_info.get('name', '')
                            # Don't overwrite the provider_id entry, just add another entry by linkedin_id
                            all_attendee_info[orig_info['linkedin_id']] = orig_info
                            logger.info(f"Added resolved LinkedIn attendee: {orig_info['linkedin_id']} -> {orig_info.get('name')} with provider_id {orig_info['provider_id']}")
            
            for conv_info in conversations_to_process:
                for attendee_id, attendee_info in conv_info['attendees'].items():
                    if attendee_info.get('name'):
                        # Store by various identifiers
                        all_attendee_names[attendee_id] = attendee_info['name']
                        # Only store attendee_info if we don't already have better info from resolved attendees
                        if attendee_id not in all_attendee_info:
                            all_attendee_info[attendee_id] = attendee_info
                        
                        if attendee_info.get('provider_id'):
                            all_attendee_names[attendee_info['provider_id']] = attendee_info['name']
                            # Only store if we don't already have better info from resolved attendees
                            if attendee_info['provider_id'] not in all_attendee_info:
                                all_attendee_info[attendee_info['provider_id']] = attendee_info
                            
                        # For WhatsApp, also store by phone
                        if channel_type == 'whatsapp' and '@s.whatsapp.net' in str(attendee_info.get('provider_id', '')):
                            phone = attendee_info['provider_id'].replace('@s.whatsapp.net', '')
                            if phone:
                                all_attendee_names[phone] = attendee_info['name']
                                all_attendee_info[phone] = attendee_info
                                
                        # If attendee has explicit phone field (account owner), store by that
                        elif attendee_info.get('phone'):
                            all_attendee_names[attendee_info['phone']] = attendee_info['name']
                            all_attendee_info[attendee_info['phone']] = attendee_info
                            
                        # For LinkedIn, also store by linkedin_id if present
                        if attendee_info.get('linkedin_id'):
                            all_attendee_names[attendee_info['linkedin_id']] = attendee_info['name']
                            all_attendee_info[attendee_info['linkedin_id']] = attendee_info
            
            logger.info(f"Collected {len(all_attendee_names)} unique attendee names from chats")
            
            # Debug log attendee_info contents
            if all_attendee_info and channel_type == 'linkedin':
                logger.info(f"LinkedIn attendee_info has {len(all_attendee_info)} entries")
                for key, value in all_attendee_info.items():
                    logger.info(f"  key='{key}': linkedin_id={value.get('linkedin_id')}, provider_id={value.get('provider_id')}, name={value.get('name')}")
            # Debug log for WhatsApp to see if phone is being passed
            if channel_type == 'whatsapp':
                for key, value in all_attendee_names.items():
                    if 'mp9G' in key or '27720720047' in key:
                        logger.info(f"WhatsApp attendee mapping: {key} -> {value}")
            
            participant_cache = self.message_store.build_participant_cache_for_all_messages(
                all_channel_messages,
                attendee_names=all_attendee_names,
                attendee_info=all_attendee_info
            )
            
            # Step 5: Store messages using the shared cache
            for conv_info in conversations_to_process:
                if conv_info['messages']:
                    self.message_store.store_bulk_messages(
                        conv_info['messages'],
                        conv_info['conversation'],
                        channel,
                        participant_cache
                    )
            
            # Link participants to record instead of creating RecordCommunicationLinks
            # The participants are in the cache, link them to this record
            for participant in participant_cache.values():
                if not participant.contact_record:
                    # Check if this participant matches any of the record's identifiers
                    
                    # Check phone matching for WhatsApp
                    if participant.phone and participant.phone in identifiers.get('phone', []):
                        self.participant_link_manager.link_participant_to_record(
                            participant=participant,
                            record=record,
                            confidence=0.85,
                            method='sync_phone_match'
                        )
                    
                    # Check LinkedIn URN matching
                    elif participant.linkedin_member_urn and participant.linkedin_member_urn in identifiers.get('linkedin', []):
                        self.participant_link_manager.link_participant_to_record(
                            participant=participant,
                            record=record,
                            confidence=0.85,
                            method='sync_linkedin_match'
                        )
            
            logger.info(
                f"Synced {total_conversations} {channel_type} conversations for record {record.id}"
            )
            return {'conversations': total_conversations, 'messages': total_messages}
            
        except Exception as e:
            logger.error(f"Error syncing {channel_type} for record {record.id}: {e}")
            return {'conversations': 0, 'messages': 0}
    
    def _link_existing_participants_to_record(
        self,
        record: Record,
        identifiers: Dict[str, List[str]]
    ):
        """
        Link any existing participants that match this record's identifiers.
        This ensures participants from previous syncs or webhooks get linked.
        
        Args:
            record: Record instance
            identifiers: Dict of identifier types to lists of values
        """
        from communications.models import Participant
        
        linked_count = 0
        
        # Link by email
        for email in identifiers.get('email', []):
            participants = Participant.objects.filter(
                email=email,
                contact_record__isnull=True  # Only unlinked participants
            )
            for participant in participants:
                self.participant_link_manager.link_participant_to_record(
                    participant=participant,
                    record=record,
                    confidence=0.95,
                    method='sync_email_match'
                )
                linked_count += 1
                logger.info(f"Linked participant {participant.id} ({email}) to record {record.id}")
        
        # Link by phone
        for phone in identifiers.get('phone', []):
            participants = Participant.objects.filter(
                phone=phone,
                contact_record__isnull=True
            )
            for participant in participants:
                self.participant_link_manager.link_participant_to_record(
                    participant=participant,
                    record=record,
                    confidence=0.90,
                    method='sync_phone_match'
                )
                linked_count += 1
                logger.info(f"Linked participant {participant.id} ({phone}) to record {record.id}")
        
        # Link by LinkedIn URN (note: identifiers might have username, need to match URN or metadata)
        for linkedin in identifiers.get('linkedin', []):
            # Try exact match first
            participants = Participant.objects.filter(
                linkedin_member_urn=linkedin,
                contact_record__isnull=True
            )
            
            # If no exact match and it's not a URN, try contains match
            if not participants.exists() and not linkedin.startswith('urn:'):
                participants = Participant.objects.filter(
                    linkedin_member_urn__icontains=linkedin,
                    contact_record__isnull=True
                )
            
            # If still no match, try matching on metadata linkedin_id
            if not participants.exists():
                # Use Q objects to check metadata JSON field
                from django.db.models import Q
                participants = Participant.objects.filter(
                    Q(metadata__linkedin_id=linkedin) | 
                    Q(metadata__linkedin_username=linkedin),
                    contact_record__isnull=True
                )
                if participants.exists():
                    logger.info(f"Found LinkedIn participant by metadata for username: {linkedin}")
            
            for participant in participants:
                self.participant_link_manager.link_participant_to_record(
                    participant=participant,
                    record=record,
                    confidence=0.85,
                    method='sync_linkedin_match'
                )
                linked_count += 1
                logger.info(f"Linked participant {participant.id} (LinkedIn: {linkedin}) to record {record.id}")
        
        if linked_count > 0:
            logger.info(f"Linked {linked_count} existing participants to record {record.id}")
        else:
            logger.debug(f"No unlinked participants found matching record {record.id}")
    
    def _link_existing_participants_by_domain(self, record: Record, domains: List[str] = None):
        """
        Link existing participants to this record as secondary (company) based on domain.
        Uses either provided domains or extracts them from record fields.
        
        Args:
            record: Record instance
            domains: Optional list of domains already extracted from the record
        """
        from communications.models import Participant
        
        logger.info(f"🔗 _link_existing_participants_by_domain called for record {record.id}")
        logger.info(f"   📊 Input domains: {domains}")
        
        # If domains weren't provided, try to extract them from the record
        if not domains:
            from communications.record_communications.signals import get_identifier_fields_from_duplicate_rules
            from duplicates.models import URLExtractionRule
            
            # Get identifier fields from duplicate rules for this pipeline
            identifier_fields_info = get_identifier_fields_from_duplicate_rules(record.pipeline)
            if not identifier_fields_info:
                logger.debug(f"No duplicate rules configured for pipeline {record.pipeline.name}")
                return
            
            # Check if any field uses url_normalized with domain extraction rules
            domain_fields = []
            for field_slug, field_info in identifier_fields_info.items():
                if field_info.get('match_type') == 'url_normalized':
                    # Check if this field has URL extraction rules for domains
                    url_rule_ids = field_info.get('url_extraction_rules', [])
                    if url_rule_ids:
                        # Check if any of the rules are domain extraction rules
                        domain_rules = URLExtractionRule.objects.filter(
                            id__in=url_rule_ids,
                            template_type='domain',
                            is_active=True
                        ).exists()
                        if domain_rules:
                            domain_fields.append(field_slug)
                    else:
                        # No specific rules, but url_normalized fields can contain domains
                        domain_fields.append(field_slug)
            
            if not domain_fields:
                logger.debug(f"No domain-normalized fields in pipeline {record.pipeline.name}")
                return
            
            # Extract domains from the record
            domains = set()
            for field_slug in domain_fields:
                domain_value = record.data.get(field_slug)
                if domain_value:
                    # Clean the domain (remove www., lowercase)
                    clean_domain = str(domain_value).lower().strip()
                    if clean_domain.startswith('www.'):
                        clean_domain = clean_domain[4:]
                    if clean_domain:  # Only add non-empty domains
                        domains.add(clean_domain)
        else:
            # Clean provided domains
            clean_domains = set()
            for domain in domains:
                clean_domain = str(domain).lower().strip()
                if clean_domain.startswith('www.'):
                    clean_domain = clean_domain[4:]
                if clean_domain:
                    clean_domains.add(clean_domain)
            domains = clean_domains
        
        if not domains:
            logger.debug(f"No domain values found in record {record.id}")
            return
        
        logger.info(f"   🌐 Processing domains for secondary linking: {domains}")
        
        # Personal email domains to skip
        PERSONAL_EMAIL_DOMAINS = [
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 
            'icloud.com', 'me.com', 'aol.com', 'msn.com', 'live.com'
        ]
        
        linked_count = 0
        
        # Link participants with matching email domains as secondary
        for domain in domains:
            # Skip personal domains
            if domain in PERSONAL_EMAIL_DOMAINS:
                logger.debug(f"Skipping personal domain: {domain}")
                continue
            
            logger.info(f"   🔍 Searching for participants with domain: {domain}")
            
            # Find participants with this email domain who don't have a secondary record
            participants = Participant.objects.filter(
                email__iendswith=f"@{domain}",
                secondary_record__isnull=True
            )
            
            logger.info(f"   👥 Found {participants.count()} unlinked participants with @{domain}")
            
            for participant in participants:
                # Link as secondary (company) record
                if self.participant_link_manager.link_participant_to_record(
                    participant=participant,
                    record=record,
                    confidence=0.8,
                    method='domain_match',
                    as_secondary=True
                ):
                    linked_count += 1
                    logger.info(
                        f"Linked participant {participant.id} ({participant.email}) "
                        f"to company record {record.id} via domain {domain}"
                    )
        
        if linked_count > 0:
            logger.info(f"Linked {linked_count} participants to company record {record.id} via domain matching")
        else:
            logger.debug(f"No unlinked participants found with domains matching record {record.id}")
    
    def _store_attendee_mappings(
        self,
        attendee_map: Dict[str, Dict[str, Any]],
        record: Record,
        channel_type: str,
        profile: RecordCommunicationProfile
    ):
        """
        Store attendee mappings for future reference
        
        Args:
            attendee_map: Map of provider_id to attendee info
            record: Record instance
            channel_type: Channel type
            profile: RecordCommunicationProfile instance
        """
        for provider_id, attendee_info in attendee_map.items():
            RecordAttendeeMapping.objects.get_or_create(
                record=record,
                attendee_id=attendee_info['attendee_id'],
                channel_type=channel_type,
                defaults={
                    'profile': profile,
                    'provider_id': provider_id,
                    'matched_identifier': provider_id,
                    'identifier_type': channel_type,
                    'attendee_name': attendee_info.get('name', ''),
                    'attendee_data': attendee_info.get('metadata', {})
                }
            )