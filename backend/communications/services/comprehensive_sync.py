"""
Comprehensive Sync Service for Unipile Data
Fetches all attendees, chats, and messages in a coordinated manner
Maps everything together properly for accurate conversation naming
"""
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict

from django.db import transaction
from django.utils import timezone as django_timezone
from asgiref.sync import sync_to_async

from ..models import (
    Channel, Conversation, Message, ChatAttendee, UserChannelConnection, SyncJob,
    ConversationStatus, MessageDirection, MessageStatus
)
from ..unipile_sdk import unipile_service
from ..services.conversation_naming import conversation_naming_service
from pipelines.models import Record

logger = logging.getLogger(__name__)


class ComprehensiveSyncService:
    """
    Comprehensive sync service that fetches all data from Unipile
    and maps it together properly in our database
    """
    
    def __init__(self):
        self.unipile_service = unipile_service
        
    async def sync_account_comprehensive(
        self,
        channel: Channel,
        days_back: int = 30,
        max_messages_per_chat: int = 100,
        connection: Optional['UserChannelConnection'] = None,
        sync_job: Optional['SyncJob'] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive sync for a channel account using chat-centric approach
        
        Args:
            channel: Channel to sync
            days_back: How many days of history to sync
            max_messages_per_chat: Maximum messages to sync per chat
            connection: User connection for proper direction detection
            sync_job: Sync job for progress updates and WebSocket broadcasting
            
        Returns:
            Dict with sync statistics and results
        """
        stats = {
            'attendees_synced': 0,
            'chats_synced': 0,
            'messages_synced': 0,
            'conversations_created': 0,
            'conversations_updated': 0,
            'errors': []
        }
        
        try:
            logger.info(f"🔄 Starting chat-centric comprehensive sync for {channel.name}")
            if connection:
                logger.info(f"🔍 Direction detection enabled with connection: {connection.account_name}")
            else:
                logger.warning(f"⚠️ No connection provided - direction detection will use fallback methods")
            
            # New approach: Get all chats, then sync attendees and messages for each chat
            sync_result = await self._sync_chats_with_attendees_and_messages(
                channel, 
                days_back, 
                max_messages_per_chat,
                connection,
                sync_job
            )
            
            stats.update(sync_result)
            
            # Update conversation metadata and counts
            await self._update_conversation_metadata(channel)
            
            logger.info(f"✅ Chat-centric comprehensive sync complete for {channel.name}: {stats}")
            
        except Exception as e:
            logger.error(f"❌ Comprehensive sync failed for {channel.name}: {e}")
            stats['errors'].append(str(e))
            raise
            
        return stats
    
    async def _sync_chats_with_attendees_and_messages(
        self,
        channel: Channel,
        days_back: int = 30,
        max_messages_per_chat: int = 100,
        connection: Optional['UserChannelConnection'] = None,
        sync_job: Optional['SyncJob'] = None
    ) -> Dict[str, Any]:
        """
        Chat-centric sync: Get all chats, then sync attendees and messages for each
        """
        stats = {
            'attendees_synced': 0,
            'chats_synced': 0,
            'messages_synced': 0,
            'conversations_created': 0,
            'conversations_updated': 0,
            'errors': []
        }
        
        try:
            client = self.unipile_service.get_client()
            
            # Map channel type to account type
            account_type_map = {
                'whatsapp': 'WHATSAPP',
                'linkedin': 'LINKEDIN',
                'gmail': 'GOOGLE',
                'outlook': 'OUTLOOK'
            }
            account_type = account_type_map.get(channel.channel_type, channel.channel_type.upper())
            
            # Step 1: Get all chats
            logger.info(f"📱 Getting all chats for {channel.name}")
            chats_data = await client.messaging.get_all_chats(
                account_id=channel.unipile_account_id,
                limit=100,  # Start with small number for testing
                account_type=account_type
            )
            
            chats = chats_data.get('items', [])
            logger.info(f"📱 Found {len(chats)} chats to process")
            
            # Update sync job with total chat count
            if sync_job:
                await sync_job.aupdate_progress(
                    conversations_total=len(chats),
                    conversations_processed=0,
                    current_phase='processing_conversations',
                    current_step=f'Found {len(chats)} conversations to sync'
                )
            
            # Step 2: Process each chat to get its attendees and messages
            for i, chat_data in enumerate(chats, 1):
                try:
                    chat_id = chat_data.get('id')
                    if not chat_id:
                        continue
                    
                    chat_name = chat_data.get('name', f'Chat {i}')
                    logger.info(f"🔄 Processing chat {i}/{len(chats)}: {chat_name}")
                    logger.info(f"🔍 Chat ID from UniPile: {chat_id}")
                    logger.info(f"🔍 Raw chat_data keys: {list(chat_data.keys())}")
                    logger.info(f"🔍 Raw chat_data: {chat_data}")
                    
                    # Update progress for this chat
                    if sync_job:
                        await sync_job.aupdate_progress(
                            conversations_processed=i-1,  # Previous chats completed
                            current_step=f'Processing chat: {chat_name}',
                            current_conversation_name=chat_name
                        )
                    
                    # Get attendees for this specific chat
                    chat_attendees = await self._get_chat_attendees(client, chat_id)
                    
                    # Process attendee records using unified processor
                    from .unified_processor import unified_processor
                    
                    normalized_attendees = [
                        unified_processor.normalize_attendee_data(attendee_data, 'api')
                        for attendee_data in chat_attendees
                    ]
                    
                    attendees_list = await unified_processor.process_attendees(
                        normalized_attendees, channel
                    )
                    
                    # Create attendees map for conversation processing
                    attendees_map = {att.provider_id: att for att in attendees_list}
                    stats['attendees_synced'] += len(attendees_list)
                    
                    # Process conversation using unified processor
                    normalized_conversation = unified_processor.normalize_conversation_data(chat_data, 'api')
                    
                    conversation, created = await unified_processor.process_conversation(
                        normalized_conversation,
                        channel,
                        attendees_list
                    )
                    
                    if created:
                        stats['conversations_created'] += 1
                    else:
                        stats['conversations_updated'] += 1
                    
                    stats['chats_synced'] += 1
                    
                    # Get messages for this specific chat
                    logger.info(f"🔍 About to fetch messages for chat_id: {chat_id}")
                    logger.info(f"🔍 Using account_id: {channel.unipile_account_id}")
                    chat_messages = await self._get_chat_messages(client, chat_id, channel.unipile_account_id, max_messages_per_chat)
                    logger.info(f"🔍 Got {len(chat_messages)} messages back from UniPile")
                    
                    # Process messages using unified processor  
                    messages_created = 0
                    for i, message_data in enumerate(chat_messages):
                        try:
                            logger.info(f"🔍 Processing message {i+1}/{len(chat_messages)}: {message_data.get('id')}")
                            
                            # Normalize message data
                            normalized_message = unified_processor.normalize_message_data(message_data, 'api')
                            # Set chat_id for API messages
                            normalized_message['chat_id'] = chat_id
                            
                            logger.info(f"📝 Normalized message - ID: {normalized_message.get('external_message_id')}, Content: {normalized_message.get('content', '')[:50]}...")
                            
                            # Process the message
                            message, created = await unified_processor.process_message(
                                normalized_message,
                                channel,
                                conversation,
                                connection  # Pass connection for direction detection
                            )
                            
                            logger.info(f"✅ Message processed - Created: {created}, DB ID: {message.id if message else 'None'}")
                            
                            # Count both created and updated messages as "processed"
                            if message:  # If message was processed successfully (created OR updated)
                                messages_created += 1
                        except Exception as e:
                            logger.error(f"❌ Failed to process message {message_data.get('id')}: {e}")
                            import traceback
                            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
                            continue
                    
                    stats['messages_synced'] += messages_created
                    logger.info(f"✅ Chat {chat_name}: {len(chat_attendees)} attendees, {messages_created} messages")
                    
                    # Update progress after completing this chat
                    if sync_job:
                        await sync_job.aupdate_progress(
                            conversations_processed=i,
                            messages_processed=stats['messages_synced'],
                            current_step=f'Completed chat: {chat_name}'
                        )
                    
                except Exception as e:
                    logger.error(f"Failed to process chat {chat_data.get('id', 'unknown')}: {e}")
                    stats['errors'].append(f"Chat {chat_data.get('id', 'unknown')}: {str(e)}")
                    continue
            
            logger.info(f"✅ Processed {stats['chats_synced']} chats with {stats['attendees_synced']} attendees and {stats['messages_synced']} messages")
            
            # Final progress update
            if sync_job:
                await sync_job.aupdate_progress(
                    conversations_processed=stats['chats_synced'],
                    messages_processed=stats['messages_synced'],
                    current_phase='completed',
                    current_step='Comprehensive sync completed'
                )
            
        except Exception as e:
            logger.error(f"Failed chat-centric sync for {channel.name}: {e}")
            
            # Update sync job with error
            if sync_job:
                await sync_job.aupdate_progress(
                    current_phase='error',
                    current_step=f'Sync failed: {str(e)}'
                )
            raise
        
        return stats
    
    async def _get_chat_attendees(self, client, chat_id: str) -> List[Dict[str, Any]]:
        """Get attendees for a specific chat using the chat attendees endpoint"""
        try:
            logger.info(f"👥 Getting attendees for chat {chat_id}")
            chat_attendees_data = await client._make_request(
                'GET', 
                f'chats/{chat_id}/attendees'
            )
            
            attendees = chat_attendees_data.get('items', []) if chat_attendees_data else []
            logger.info(f"👥 Found {len(attendees)} attendees for chat {chat_id}")
            
            return attendees
            
        except Exception as e:
            logger.error(f"Failed to get attendees for chat {chat_id}: {e}")
            return []
    
    async def _get_chat_messages(self, client, chat_id: str, account_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get messages for a specific chat using the same method as frontend"""
        try:
            logger.info(f"📨 Getting messages for chat {chat_id} with account {account_id} and limit {limit}")
            # Use the SDK properly with account_id parameter
            chat_messages_data = await client.messaging.get_all_messages(
                chat_id=chat_id,
                account_id=account_id,  # This was missing!
                limit=limit,
                cursor=None
            )
            
            logger.info(f"📨 Raw API response for chat {chat_id}: {type(chat_messages_data)}")
            if chat_messages_data:
                logger.info(f"📨 Response keys: {list(chat_messages_data.keys()) if isinstance(chat_messages_data, dict) else 'Not a dict'}")
            
            messages = chat_messages_data.get('items', []) if chat_messages_data else []
            logger.info(f"📨 Raw messages count for chat {chat_id}: {len(messages)}")
            
            # Filter out null/invalid messages
            valid_messages = []
            for i, msg in enumerate(messages):
                if msg and isinstance(msg, dict) and msg.get('id'):
                    valid_messages.append(msg)
                    message_text = msg.get('text') or msg.get('body') or 'No text'
                    message_text_preview = message_text[:50] if message_text else 'No text'
                    logger.debug(f"📨 Valid message {i}: {msg.get('id')} - {message_text_preview}")
                else:
                    logger.warning(f"Skipping invalid message {i}: {msg}")
            
            logger.info(f"📨 FINAL RESULT for chat {chat_id}: {len(messages)} raw, {len(valid_messages)} valid messages")
            return valid_messages
            
        except Exception as e:
            logger.error(f"❌ Failed to get messages for chat {chat_id}: {e}")
            logger.error(f"❌ Chat ID: {chat_id}")
            logger.error(f"❌ Account ID: {account_id}")
            logger.error(f"❌ Limit: {limit}")
            logger.error(f"❌ Exception type: {type(e)}")
            
            # Check if it's a UnipileConnectionError with more details
            if hasattr(e, '__dict__'):
                logger.error(f"❌ Exception attributes: {e.__dict__}")
            
            # If it's a 400 error, try with a smaller limit
            error_message = str(e)
            if "400" in error_message and limit > 50:
                logger.info(f"🔄 Retrying with smaller limit for chat {chat_id}")
                try:
                    # Retry with much smaller limit
                    chat_messages_data = await client.messaging.get_all_messages(
                        chat_id=chat_id,
                        account_id=account_id,
                        limit=100,  # Much smaller limit
                        cursor=None
                    )
                    
                    if chat_messages_data:
                        messages = chat_messages_data.get('items', [])
                        logger.info(f"✅ Retry successful: got {len(messages)} messages with smaller limit")
                        
                        # Filter out null/invalid messages
                        valid_messages = []
                        for i, msg in enumerate(messages):
                            if msg and isinstance(msg, dict) and msg.get('id'):
                                valid_messages.append(msg)
                        
                        logger.info(f"📨 RETRY RESULT for chat {chat_id}: {len(messages)} raw, {len(valid_messages)} valid messages")
                        return valid_messages
                    
                except Exception as retry_error:
                    logger.error(f"❌ Retry also failed for chat {chat_id}: {retry_error}")
            
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            logger.warning(f"⚠️ Continuing sync without messages for chat {chat_id}")
            return []
    
    async def _sync_attendees(self, channel: Channel) -> Dict[str, Any]:
        """Sync all attendees for a channel"""
        logger.info(f"📋 Syncing attendees for {channel.name} (account_id: {channel.unipile_account_id})")
        
        try:
            client = self.unipile_service.get_client()
            logger.info(f"✅ Got Unipile client for comprehensive sync")
            
            # Get all attendees from Unipile
            # Use small limit for testing
            logger.info(f"🔄 Calling get_all_attendees with account_id: {channel.unipile_account_id}, limit: 10")
            attendees_data = await client.messaging.get_all_attendees(
                account_id=channel.unipile_account_id,
                limit=10  # Small limit for testing
            )
            logger.info(f"✅ Successfully got attendees response: {len(attendees_data.get('items', []))} attendees")
            
            attendees = attendees_data.get('items', [])
            attendees_map = {}
            synced_count = 0
            
            for attendee_data in attendees:
                try:
                    # Create or update attendee record
                    attendee = await self._create_or_update_attendee(channel, attendee_data)
                    if attendee:
                        attendees_map[attendee.provider_id] = attendee
                        synced_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to sync attendee {attendee_data.get('id')}: {e}")
            
            logger.info(f"✅ Synced {synced_count} attendees for {channel.name}")
            
            return {
                'count': synced_count,
                'attendees_map': attendees_map
            }
            
        except Exception as e:
            logger.error(f"Failed to sync attendees for {channel.name}: {e}")
            raise
    
    # =========================================================================
    # DEPRECATED METHODS - Use unified_processor instead
    # =========================================================================
    
    async def _create_or_update_attendee(
        self, 
        channel: Channel, 
        attendee_data: Dict[str, Any]
    ) -> Optional[ChatAttendee]:
        """DEPRECATED: Use unified_processor.process_attendees() instead"""
        """Create or update a single attendee record"""
        
        external_id = attendee_data.get('id')
        provider_id = attendee_data.get('provider_id')
        
        if not external_id or not provider_id:
            logger.warning(f"Attendee missing ID or provider_id: {attendee_data}")
            return None
        
        try:
            # Use sync_to_async for database operations
            attendee, created = await sync_to_async(ChatAttendee.objects.get_or_create)(
                channel=channel,
                external_attendee_id=external_id,
                defaults={
                    'provider_id': provider_id,
                    'name': attendee_data.get('name', 'Unknown'),
                    'picture_url': attendee_data.get('picture_url', ''),
                    'is_self': attendee_data.get('is_self', False),
                    'metadata': attendee_data,
                    'sync_status': 'active'
                }
            )
            
            if not created:
                # Update existing record
                attendee.name = attendee_data.get('name', attendee.name)
                attendee.picture_url = attendee_data.get('picture_url', attendee.picture_url)
                attendee.is_self = attendee_data.get('is_self', attendee.is_self)
                attendee.metadata = attendee_data
                attendee.sync_status = 'active'
                await sync_to_async(attendee.save)()
            
            return attendee
            
        except Exception as e:
            logger.error(f"Failed to create/update attendee {external_id}: {e}")
            return None
    
    async def _retrieve_specific_attendee(
        self,
        channel: Channel,
        provider_id: str,
        chat_id: str
    ) -> Optional[ChatAttendee]:
        """Retrieve a specific attendee by getting attendees from the specific chat"""
        try:
            # First, try to find if we already have this attendee in the database
            existing_attendee = await sync_to_async(ChatAttendee.objects.filter(
                channel=channel,
                provider_id=provider_id
            ).first)()
            
            if existing_attendee:
                return existing_attendee
            
            # Get the client
            client = self.unipile_service.get_client()
            
            # Use the chat-specific attendees endpoint - much better approach!
            logger.info(f"🔍 Getting attendees for chat {chat_id} to find provider_id: {provider_id}")
            
            # Get attendees specifically for this chat
            try:
                chat_attendees_data = await client._make_request(
                    'GET', 
                    f'chats/{chat_id}/attendees'
                )
                
                attendees = chat_attendees_data.get('items', []) if chat_attendees_data else []
                logger.info(f"📋 Found {len(attendees)} attendees for chat {chat_id}")
                
                # Look for the attendee with matching provider_id
                target_attendee_data = None
                for attendee_data in attendees:
                    if attendee_data.get('provider_id') == provider_id:
                        target_attendee_data = attendee_data
                        logger.info(f"✅ Found matching attendee: '{attendee_data.get('name', 'Unknown')}' ({provider_id})")
                        break
                
                if not target_attendee_data:
                    logger.warning(f"❌ No attendee found with provider_id {provider_id} in chat {chat_id}")
                    return None
                
                # Create the attendee record
                attendee = await self._create_or_update_attendee(channel, target_attendee_data)
                if attendee:
                    logger.info(f"✅ Successfully retrieved chat-specific attendee: '{attendee.name}' ({provider_id})")
                    return attendee
                else:
                    logger.error(f"❌ Failed to create attendee for provider_id: {provider_id}")
                    return None
                    
            except Exception as chat_api_error:
                logger.warning(f"Chat attendees API failed: {chat_api_error}, falling back to global search")
                # Fallback to the original approach if the chat-specific API fails
                return await self._fallback_attendee_search(channel, provider_id)
                
        except Exception as e:
            logger.error(f"Failed to retrieve specific attendee {provider_id}: {e}")
            return None
    
    async def _fallback_attendee_search(
        self,
        channel: Channel,
        provider_id: str
    ) -> Optional[ChatAttendee]:
        """Fallback method to search through all attendees"""
        try:
            client = self.unipile_service.get_client()
            
            logger.info(f"🔄 Fallback: searching through all attendees for provider_id: {provider_id}")
            
            # Search through attendees to find the one with matching provider_id
            attendees_data = await client.messaging.get_all_attendees(
                account_id=channel.unipile_account_id,
                limit=200  # Increased limit for better coverage
            )
            
            attendees = attendees_data.get('items', [])
            target_attendee_data = None
            
            for attendee_data in attendees:
                if attendee_data.get('provider_id') == provider_id:
                    target_attendee_data = attendee_data
                    break
            
            if not target_attendee_data:
                logger.warning(f"❌ Attendee not found in fallback search for provider_id: {provider_id}")
                return None
            
            # Create the attendee record
            attendee = await self._create_or_update_attendee(channel, target_attendee_data)
            if attendee:
                logger.info(f"✅ Fallback found attendee: '{attendee.name}' ({provider_id})")
                return attendee
            else:
                logger.error(f"❌ Failed to create attendee for provider_id: {provider_id}")
                return None
                
        except Exception as e:
            logger.error(f"Fallback attendee search failed for {provider_id}: {e}")
            return None
    
    async def _sync_chats(
        self, 
        channel: Channel, 
        attendees_map: Dict[str, ChatAttendee]
    ) -> Dict[str, Any]:
        """Sync all chats for a channel with on-demand attendee retrieval"""
        logger.info(f"💬 Syncing chats with on-demand attendee retrieval for {channel.name}")
        
        try:
            client = self.unipile_service.get_client()
            
            # Map channel type to account type
            account_type_map = {
                'whatsapp': 'WHATSAPP',
                'linkedin': 'LINKEDIN',
                'gmail': 'GOOGLE',
                'outlook': 'OUTLOOK'
            }
            account_type = account_type_map.get(channel.channel_type, channel.channel_type.upper())
            
            # Get all chats from Unipile  
            chats_data = await client.messaging.get_all_chats(
                account_id=channel.unipile_account_id,
                limit=1,  # Just 1 conversation for testing
                account_type=account_type
            )
            
            chats = chats_data.get('items', [])
            conversations_created = 0
            conversations_updated = 0
            chat_ids = []
            attendees_retrieved = 0
            
            for chat_data in chats:
                try:
                    chat_id = chat_data.get('id')
                    if not chat_id:
                        continue
                        
                    chat_ids.append(chat_id)
                    
                    # Get the specific attendee for this chat on-demand
                    provider_id = chat_data.get('provider_id') or chat_data.get('attendee_provider_id')
                    if provider_id and provider_id not in attendees_map:
                        logger.info(f"🔍 Retrieving specific attendee for provider_id: {provider_id}")
                        attendee = await self._retrieve_specific_attendee(channel, provider_id, chat_id)
                        if attendee:
                            attendees_map[provider_id] = attendee
                            attendees_retrieved += 1
                    
                    # Enrich chat with attendee data (now should have the specific attendee)
                    enriched_chat = self._enrich_chat_with_attendee_data(chat_data, attendees_map)
                    
                    # Create or update conversation
                    conversation, created = await self._create_or_update_conversation(
                        channel, enriched_chat
                    )
                    
                    if created:
                        conversations_created += 1
                    else:
                        conversations_updated += 1
                        
                except Exception as e:
                    logger.error(f"Failed to sync chat {chat_data.get('id')}: {e}")
            
            logger.info(f"✅ Synced {len(chat_ids)} chats, retrieved {attendees_retrieved} specific attendees for {channel.name}")
            
            return {
                'count': len(chat_ids),
                'chat_ids': chat_ids,
                'conversations_created': conversations_created,
                'conversations_updated': conversations_updated,
                'attendees_retrieved': attendees_retrieved
            }
            
        except Exception as e:
            logger.error(f"Failed to sync chats for {channel.name}: {e}")
            raise
    
    async def _sync_missing_attendees(
        self, 
        channel: Channel, 
        missing_provider_ids: List[str],
        attendees_map: Dict[str, ChatAttendee]
    ):
        """Sync specific missing attendees by searching for them"""
        try:
            client = self.unipile_service.get_client()
            
            # Get a larger sample of attendees to find the missing ones
            attendees_data = await client.messaging.get_all_attendees(
                account_id=channel.unipile_account_id,
                limit=100  # Larger limit to find missing attendees
            )
            
            attendees = attendees_data.get('items', [])
            found_count = 0
            
            for attendee_data in attendees:
                provider_id = attendee_data.get('provider_id')
                if provider_id in missing_provider_ids:
                    # Create this missing attendee
                    attendee = await self._create_or_update_attendee(channel, attendee_data)
                    if attendee:
                        attendees_map[provider_id] = attendee
                        found_count += 1
                        logger.info(f"✅ Synced missing attendee: {attendee.name} ({provider_id})")
            
            logger.info(f"✅ Synced {found_count} missing attendees")
            
        except Exception as e:
            logger.error(f"Failed to sync missing attendees: {e}")
    
    async def _update_conversations_with_new_attendees(
        self, 
        channel: Channel, 
        chats: List[Dict[str, Any]], 
        attendees_map: Dict[str, ChatAttendee]
    ):
        """Update conversations with newly synced attendee data"""
        try:
            for chat_data in chats:
                chat_id = chat_data.get('id')
                if not chat_id:
                    continue
                    
                provider_id = chat_data.get('provider_id') or chat_data.get('attendee_provider_id')
                if provider_id and provider_id in attendees_map:
                    # Re-enrich and update the conversation
                    enriched_chat = self._enrich_chat_with_attendee_data(chat_data, attendees_map)
                    
                    # Update existing conversation with enriched data
                    conversation = await sync_to_async(Conversation.objects.filter(
                        channel=channel,
                        external_thread_id=chat_id
                    ).first)()
                    
                    if conversation:
                        # Generate new name with attendee data or fallback to provider_id
                        contact_info = {}
                        attendees = enriched_chat.get('attendees', [])
                        if attendees:
                            attendee = attendees[0]
                            contact_info.update({
                                'name': attendee.get('name'),
                                'provider_id': attendee.get('provider_id'),
                                'contact_record_id': attendee.get('contact_record_id')
                            })
                        else:
                            # Fallback: use the provider_id from chat data as phone info
                            chat_provider_id = chat_data.get('provider_id') or chat_data.get('attendee_provider_id')
                            if chat_provider_id:
                                # Extract phone number for better display
                                phone_number = chat_provider_id.split('@')[0] if '@' in chat_provider_id else chat_provider_id
                                contact_info = {
                                    'from': phone_number,
                                    'phone': phone_number
                                }
                        
                        new_subject = conversation_naming_service.generate_conversation_name(
                            channel_type=channel.channel_type,
                            contact_info=contact_info,
                            external_thread_id=chat_id
                        )
                        
                        # Update conversation with new name and attendee metadata
                        conversation.subject = new_subject
                        conversation.metadata.update({
                            'attendees': attendees
                        })
                        
                        await sync_to_async(conversation.save)(
                            update_fields=['subject', 'metadata']
                        )
                        
                        logger.info(f"✅ Updated conversation name: '{conversation.subject}' with attendee data")
                        
        except Exception as e:
            logger.error(f"Failed to update conversations with new attendees: {e}")
    
    def _enrich_chat_with_attendee_data(
        self, 
        chat_data: Dict[str, Any], 
        attendees_map: Dict[str, ChatAttendee]
    ) -> Dict[str, Any]:
        """DEPRECATED: Use unified_processor.normalize_conversation_data() instead"""
        enriched_chat = chat_data.copy()
        
        # Look up attendee by provider_id
        provider_id = chat_data.get('provider_id') or chat_data.get('attendee_provider_id')
        
        if provider_id and provider_id in attendees_map:
            attendee = attendees_map[provider_id]
            
            # Add enriched attendee data
            enriched_chat['attendees'] = [{
                'id': attendee.external_attendee_id,
                'name': attendee.name,
                'provider_id': attendee.provider_id,
                'picture_url': attendee.picture_url,
                'is_self': attendee.is_self,
                'contact_record_id': attendee.contact_record_id
            }]
            
            # Use attendee name as chat name if available and not a phone number
            if not enriched_chat.get('name') and not attendee.is_phone_number_name:
                enriched_chat['name'] = attendee.name
        
        return enriched_chat
    
    async def _create_or_update_conversation(
        self, 
        channel: Channel, 
        chat_data: Dict[str, Any]
    ) -> Tuple[Conversation, bool]:
        """DEPRECATED: Use unified_processor.process_conversation() instead"""
        """Create or update a conversation from chat data"""
        
        external_thread_id = chat_data.get('id')
        if not external_thread_id:
            raise ValueError("Chat data missing ID")
        
        # Generate smart conversation name
        contact_info = {}
        attendees = chat_data.get('attendees', [])
        if attendees:
            attendee = attendees[0]
            contact_info.update({
                'name': attendee.get('name'),
                'provider_id': attendee.get('provider_id'),
                'contact_record_id': attendee.get('contact_record_id')
            })
        else:
            # Fallback: use provider_id from chat data for phone info
            chat_provider_id = chat_data.get('provider_id') or chat_data.get('attendee_provider_id')
            if chat_provider_id:
                # Extract phone number for better display
                phone_number = chat_provider_id.split('@')[0] if '@' in chat_provider_id else chat_provider_id
                contact_info = {
                    'from': phone_number,
                    'phone': phone_number
                }
        
        # Add chat name if available
        if chat_data.get('name'):
            contact_info['chat_name'] = chat_data.get('name')
        
        subject = conversation_naming_service.generate_conversation_name(
            channel_type=channel.channel_type,
            contact_info=contact_info,
            external_thread_id=external_thread_id
        )
        
        # Get primary contact record if available
        primary_contact_record = None
        if attendees and attendees[0].get('contact_record_id'):
            try:
                primary_contact_record = await sync_to_async(Record.objects.get)(
                    id=attendees[0]['contact_record_id']
                )
            except Record.DoesNotExist:
                pass
        
        # Create or update conversation
        conversation, created = await sync_to_async(Conversation.objects.get_or_create)(
            channel=channel,
            external_thread_id=external_thread_id,
            defaults={
                'subject': subject,
                'status': ConversationStatus.ARCHIVED if chat_data.get('archived') else ConversationStatus.ACTIVE,
                'primary_contact_record': primary_contact_record,
                'last_message_at': self._parse_timestamp(chat_data.get('timestamp')),
                'metadata': {
                    'is_group': chat_data.get('type') == 1,
                    'is_muted': bool(chat_data.get('muted_until')),
                    'is_pinned': chat_data.get('is_pinned', False),
                    'attendees': attendees,
                    'unread_count': chat_data.get('unread_count', 0),
                    'picture_url': chat_data.get('picture_url')
                }
            }
        )
        
        if not created:
            # Update existing conversation
            conversation.subject = subject
            conversation.status = ConversationStatus.ARCHIVED if chat_data.get('archived') else ConversationStatus.ACTIVE
            conversation.primary_contact_record = primary_contact_record
            conversation.last_message_at = self._parse_timestamp(chat_data.get('timestamp'))
            conversation.metadata.update({
                'is_group': chat_data.get('type') == 1,
                'is_muted': bool(chat_data.get('muted_until')),
                'is_pinned': chat_data.get('is_pinned', False),
                'attendees': attendees,
                'unread_count': chat_data.get('unread_count', 0),
                'picture_url': chat_data.get('picture_url')
            })
            await sync_to_async(conversation.save)()
        
        return conversation, created
    
    async def _sync_messages(
        self, 
        channel: Channel, 
        chat_ids: List[str], 
        days_back: int,
        max_messages_per_chat: int
    ) -> Dict[str, Any]:
        """Sync messages for all chats"""
        logger.info(f"📨 Syncing messages for {len(chat_ids)} chats in {channel.name}")
        
        total_messages = 0
        
        # Process chats in batches to avoid overwhelming the API
        batch_size = 5
        for i in range(0, len(chat_ids), batch_size):
            batch = chat_ids[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [
                self._sync_chat_messages(channel, chat_id, days_back, max_messages_per_chat)
                for chat_id in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Message sync failed: {result}")
                else:
                    total_messages += result
        
        logger.info(f"✅ Synced {total_messages} messages for {channel.name}")
        
        return {'count': total_messages}
    
    async def _sync_chat_messages(
        self, 
        channel: Channel, 
        chat_id: str, 
        days_back: int,
        max_messages: int
    ) -> int:
        """Sync messages for a single chat"""
        
        try:
            client = self.unipile_service.get_client()
            
            # Get messages for this chat
            messages_data = await client.messaging.get_all_messages(
                chat_id=chat_id,
                limit=10  # Small limit for testing
            )
            
            messages = messages_data.get('items', [])
            synced_count = 0
            
            # Filter out null/invalid messages
            valid_messages = []
            for msg in messages:
                if msg and isinstance(msg, dict) and msg.get('id'):
                    valid_messages.append(msg)
                else:
                    logger.warning(f"Skipping invalid message: {msg}")
            
            logger.info(f"📨 Got {len(messages)} messages, {len(valid_messages)} valid for chat {chat_id}")
            
            # Get the conversation for this chat
            try:
                conversation = await sync_to_async(Conversation.objects.get)(
                    channel=channel,
                    external_thread_id=chat_id
                )
            except Conversation.DoesNotExist:
                logger.warning(f"No conversation found for chat {chat_id}")
                return 0
            
            # Sync each valid message
            for message_data in valid_messages:
                try:
                    message_created = await self._create_or_update_message(
                        channel, conversation, message_data
                    )
                    if message_created:
                        synced_count += 1
                        
                except Exception as e:
                    message_id = message_data.get('id') if message_data and isinstance(message_data, dict) else 'unknown'
                    logger.error(f"Failed to sync message {message_id}: {e}")
            
            return synced_count
            
        except Exception as e:
            logger.error(f"Failed to sync messages for chat {chat_id}: {e}")
            return 0
    
    async def _create_or_update_message(
        self, 
        channel: Channel, 
        conversation: Conversation, 
        message_data: Dict[str, Any]
    ) -> bool:
        """DEPRECATED: Use unified_processor.process_message() instead"""
        """Create or update a single message"""
        
        # Check if message_data is None or empty
        if not message_data or not isinstance(message_data, dict):
            logger.warning(f"Invalid message data: {message_data}")
            return False
        
        external_message_id = message_data.get('id')
        if not external_message_id:
            logger.warning(f"Message missing ID: {message_data}")
            return False
        
        # Check if message already exists
        if await sync_to_async(Message.objects.filter(
            external_message_id=external_message_id
        ).exists)():
            return False  # Already exists
        
        # Determine message direction using correct Unipile API fields
        is_sender = message_data.get('is_sender', False)
        direction = MessageDirection.OUTBOUND if is_sender else MessageDirection.INBOUND
        
        # Extract content safely
        content = (
            message_data.get('text') or 
            message_data.get('body') or 
            message_data.get('content') or
            ''
        )
        
        # Get subject safely
        subject = message_data.get('subject', '') or ''
        if subject and len(subject) > 500:
            subject = subject[:500]
        
        # Get timestamp safely
        received_at = None
        try:
            received_at = self._parse_timestamp(message_data.get('date'))
        except Exception as ts_error:
            logger.warning(f"Failed to parse timestamp for message {external_message_id}: {ts_error}")
        
        # Create message with safe defaults
        try:
            await sync_to_async(Message.objects.create)(
                external_message_id=external_message_id,
                channel=channel,
                conversation=conversation,
                direction=direction,
                content=content,
                subject=subject,
                status=MessageStatus.DELIVERED,  # Assume delivered if we got it
                received_at=received_at,
                metadata=message_data or {}
            )
        except Exception as create_error:
            logger.error(f"Failed to create message {external_message_id}: {create_error}")
            logger.error(f"Message data: {message_data}")
            raise
        
        return True
    
    async def _update_conversation_metadata(self, channel: Channel):
        """Update conversation message counts and other metadata"""
        logger.info(f"🔄 Updating conversation metadata for {channel.name}")
        
        # Update message counts for all conversations in this channel
        conversations = await sync_to_async(list)(
            Conversation.objects.filter(channel=channel)
        )
        
        for conversation in conversations:
            # Count messages
            message_count = await sync_to_async(
                conversation.messages.count
            )()
            
            # Get latest message timestamp
            latest_message = await sync_to_async(
                lambda: conversation.messages.order_by('-created_at').first()
            )()
            
            # Update conversation
            conversation.message_count = message_count
            if latest_message:
                conversation.last_message_at = latest_message.created_at
            
            await sync_to_async(conversation.save)(
                update_fields=['message_count', 'last_message_at']
            )
    
    def _parse_timestamp(self, timestamp_value: Optional[any]) -> Optional[datetime]:
        """Parse timestamp string to datetime"""
        if not timestamp_value:
            return None
        
        # Ensure we have a string
        if not isinstance(timestamp_value, str):
            try:
                timestamp_str = str(timestamp_value)
            except:
                return None
        else:
            timestamp_str = timestamp_value
            
        try:
            # Handle ISO format timestamps
            if 'T' in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError):
            return None


# Global instance
comprehensive_sync_service = ComprehensiveSyncService()