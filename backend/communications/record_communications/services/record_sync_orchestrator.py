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
    ConversationStore, MessageStore, LinkManager, MetricsUpdater
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
        self.link_manager = LinkManager()
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
            
            # Create sync job if not provided
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
                            sync_job
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
                
                # Step 4: Update metrics
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
        sync_job: RecordSyncJob
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
            
            # Process each email address
            for email_address, threads in email_data.items():
                for thread_data in threads:
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
            
            # Build shared participant cache for ALL email messages
            logger.info(f"Building participant cache for {len(all_email_messages)} email messages")
            participant_cache = self.message_store.build_participant_cache_for_all_messages(all_email_messages)
            
            # Now store all messages using the shared cache
            for thread_info in threads_to_process:
                if thread_info['messages']:
                    self.message_store.store_bulk_messages(
                        thread_info['messages'],
                        thread_info['conversation'],
                        channel,
                        participant_cache  # Pass shared cache
                    )
                
                # Link conversation to record
                self.link_manager.create_link(
                    record=record,
                    conversation=thread_info['conversation'],
                    match_type='email',
                    matched_identifier=thread_info['email_address'],
                    confidence=1.0
                )
            
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
                        # Store account owner's name by multiple keys
                        account_owner_info = {
                            'name': connection.account_name,
                            'provider_id': account_provider_id,
                            'is_account_owner': True
                        }
                        chat_attendees[account_provider_id] = account_owner_info
                        
                        # For WhatsApp, also store by phone
                        if channel_type == 'whatsapp' and '@s.whatsapp.net' in account_provider_id:
                            phone = account_provider_id.replace('@s.whatsapp.net', '')
                            if phone:
                                chat_attendees[phone] = account_owner_info
                        
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
                        'attendee_info': attendee_data.get('attendee_info', {})
                    })
                    
                    total_conversations += 1
                    total_messages += len(conv_data.get('messages', []))
            
            # Step 4: Build participant cache from chat attendees
            logger.info(f"Building participant cache for {len(all_channel_messages)} {channel_type} messages")
            
            # Collect all attendee names from all chats
            all_attendee_names = {}
            for conv_info in conversations_to_process:
                for attendee_id, attendee_info in conv_info['attendees'].items():
                    if attendee_info.get('name'):
                        # Store by various identifiers
                        all_attendee_names[attendee_id] = attendee_info['name']
                        if attendee_info.get('provider_id'):
                            all_attendee_names[attendee_info['provider_id']] = attendee_info['name']
                        # For WhatsApp, also store by phone
                        if channel_type == 'whatsapp' and '@s.whatsapp.net' in str(attendee_info.get('provider_id', '')):
                            phone = attendee_info['provider_id'].replace('@s.whatsapp.net', '')
                            if phone:
                                all_attendee_names[phone] = attendee_info['name']
            
            logger.info(f"Collected {len(all_attendee_names)} unique attendee names from chats")
            
            participant_cache = self.message_store.build_participant_cache_for_all_messages(
                all_channel_messages,
                attendee_names=all_attendee_names
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
                
                # Link conversation to record
                provider_id = conv_info['attendee_info'].get('provider_id', '')
                self.link_manager.create_link(
                    record=record,
                    conversation=conv_info['conversation'],
                    match_type='provider_id',
                    matched_identifier=provider_id,
                    confidence=0.9
                )
            
            logger.info(
                f"Synced {total_conversations} {channel_type} conversations for record {record.id}"
            )
            return {'conversations': total_conversations, 'messages': total_messages}
            
        except Exception as e:
            logger.error(f"Error syncing {channel_type} for record {record.id}: {e}")
            return {'conversations': 0, 'messages': 0}
    
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