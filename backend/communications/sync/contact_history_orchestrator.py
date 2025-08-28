"""
Contact History Sync Orchestrator
Orchestrates historical sync across ALL channels when a contact is linked
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from asgiref.sync import sync_to_async, async_to_sync

from communications.models import (
    Participant, Conversation, ConversationParticipant,
    Message, Channel, UserChannelConnection
)
from communications.services.participant_resolution import (
    ParticipantResolutionService, ConversationStorageDecider
)
from communications.unipile.clients.email import UnipileEmailClient
from communications.unipile.clients.messaging import UnipileMessagingClient

logger = logging.getLogger(__name__)


class ContactHistorySyncOrchestrator:
    """
    When a contact is linked, sync ALL their historical communications
    across all connected channels
    """
    
    def __init__(self, tenant=None):
        self.tenant = tenant
        self.resolution_service = ParticipantResolutionService(tenant)
        self.storage_decider = ConversationStorageDecider(tenant)
    
    async def sync_contact_communications(
        self,
        contact_record,
        trigger_source: str = 'manual'
    ) -> Dict[str, Any]:
        """
        Main entry point for contact-based sync
        
        Args:
            contact_record: The pipelines.Record object for the contact
            trigger_source: What triggered this sync ('manual', 'new_link', 'contact_created')
            
        Returns:
            Summary of sync results
        """
        logger.info(f"Starting contact history sync for {contact_record.id} triggered by {trigger_source}")
        
        # Extract all identifiers from the contact record
        identifiers = await self.extract_contact_identifiers(contact_record)
        
        if not identifiers:
            logger.warning(f"No identifiers found for contact {contact_record.id}")
            return {
                'success': False,
                'error': 'No identifiers found for contact'
            }
        
        # Get or create participant for this contact
        participant = await self.ensure_participant_for_contact(contact_record, identifiers)
        
        # Get all user's connected channels
        channels = await self.get_user_channels(contact_record.created_by)
        
        # Prepare sync tasks for each channel
        sync_tasks = []
        
        for channel in channels:
            if channel.channel_type in ['gmail', 'outlook', 'mail']:
                sync_tasks.append(self.sync_email_history(channel, participant, identifiers))
            elif channel.channel_type == 'whatsapp':
                sync_tasks.append(self.sync_whatsapp_history(channel, participant, identifiers))
            elif channel.channel_type == 'linkedin':
                sync_tasks.append(self.sync_linkedin_history(channel, participant, identifiers))
            elif channel.channel_type == 'instagram':
                sync_tasks.append(self.sync_instagram_history(channel, participant, identifiers))
            elif channel.channel_type == 'messenger':
                sync_tasks.append(self.sync_messenger_history(channel, participant, identifiers))
            elif channel.channel_type == 'telegram':
                sync_tasks.append(self.sync_telegram_history(channel, participant, identifiers))
            # Add other channel types as needed
        
        # Run all channel syncs in parallel
        results = await asyncio.gather(*sync_tasks, return_exceptions=True)
        
        # Process results
        successful_syncs = []
        failed_syncs = []
        total_conversations = 0
        total_messages = 0
        
        for i, result in enumerate(results):
            channel = channels[i]
            if isinstance(result, Exception):
                logger.error(f"Sync failed for channel {channel.name}: {result}")
                failed_syncs.append({
                    'channel': channel.name,
                    'error': str(result)
                })
            else:
                successful_syncs.append({
                    'channel': channel.name,
                    'conversations': result.get('conversation_count', 0),
                    'messages': result.get('message_count', 0)
                })
                total_conversations += result.get('conversation_count', 0)
                total_messages += result.get('message_count', 0)
        
        # Update participant statistics
        participant.total_conversations = total_conversations
        participant.total_messages = total_messages
        await sync_to_async(participant.save)()
        
        return {
            'success': True,
            'contact_id': str(contact_record.id),
            'participant_id': str(participant.id),
            'synced_conversations': total_conversations,
            'synced_messages': total_messages,
            'channels_synced': len(successful_syncs),
            'successful_syncs': successful_syncs,
            'failed_syncs': failed_syncs
        }
    
    async def extract_contact_identifiers(self, contact_record) -> Dict[str, Any]:
        """
        Extract all communication identifiers from a contact record
        
        Looks for fields like email, phone, linkedin_url, etc.
        """
        identifiers = {}
        
        # Get the contact's data from the JSONB field
        contact_data = contact_record.data or {}
        
        # Common field names to look for
        email_fields = ['email', 'work_email', 'personal_email', 'contact_email']
        phone_fields = ['phone', 'mobile', 'work_phone', 'cell_phone', 'whatsapp']
        linkedin_fields = ['linkedin', 'linkedin_url', 'linkedin_profile']
        
        # Extract email
        for field in email_fields:
            if contact_data.get(field):
                identifiers['email'] = contact_data[field]
                break
        
        # Extract phone
        for field in phone_fields:
            if contact_data.get(field):
                phone = contact_data[field]
                # Normalize phone number
                if not phone.startswith('+'):
                    phone = f"+{phone}"
                identifiers['phone'] = phone
                break
        
        # Extract LinkedIn
        for field in linkedin_fields:
            if contact_data.get(field):
                identifiers['linkedin_url'] = contact_data[field]
                break
        
        # Extract name
        name_fields = ['name', 'full_name', 'display_name', 'contact_name']
        for field in name_fields:
            if contact_data.get(field):
                identifiers['name'] = contact_data[field]
                break
        
        # If no name, try to combine first and last
        if not identifiers.get('name'):
            first = contact_data.get('first_name', '')
            last = contact_data.get('last_name', '')
            if first or last:
                identifiers['name'] = f"{first} {last}".strip()
        
        logger.info(f"Extracted identifiers for contact {contact_record.id}: {identifiers}")
        return identifiers
    
    async def ensure_participant_for_contact(
        self,
        contact_record,
        identifiers: Dict
    ) -> Participant:
        """
        Get or create participant record for a contact
        """
        # Build participant data from identifiers
        participant_data = {
            'email': identifiers.get('email', ''),
            'phone': identifiers.get('phone', ''),
            'name': identifiers.get('name', ''),
        }
        
        # Extract LinkedIn member URN if available
        if identifiers.get('linkedin_url'):
            # Extract member URN from URL if possible
            # e.g., linkedin.com/in/john-doe -> john-doe
            url = identifiers['linkedin_url']
            if '/in/' in url:
                member_urn = url.split('/in/')[-1].strip('/')
                participant_data['linkedin_member_urn'] = member_urn
        
        # Find or create participant
        participant, created = await self.resolution_service.resolve_or_create_participant(
            participant_data
        )
        
        # Link to contact if not already linked
        if not participant.contact_record:
            participant.contact_record = contact_record
            participant.resolution_confidence = 1.0  # Manual link = 100% confidence
            participant.resolution_method = 'manual_sync'
            participant.resolved_at = timezone.now()
            await sync_to_async(participant.save)()
        
        return participant
    
    async def get_user_channels(self, user) -> List[Channel]:
        """
        Get all connected channels for a user
        """
        connections = await sync_to_async(list)(
            UserChannelConnection.objects.filter(
                user=user,
                auth_status='connected'
            ).select_related()
        )
        
        channels = []
        for conn in connections:
            # Get or create channel for this connection
            channel, _ = await sync_to_async(Channel.objects.get_or_create)(
                unipile_account_id=conn.unipile_account_id,
                defaults={
                    'channel_type': conn.channel_type,
                    'name': conn.account_name,
                    'auth_status': conn.auth_status,
                    'created_by': user
                }
            )
            channels.append(channel)
        
        return channels
    
    async def sync_email_history(
        self,
        channel: Channel,
        participant: Participant,
        identifiers: Dict
    ) -> Dict[str, Any]:
        """
        Search and store all emails involving these identifiers
        """
        email = identifiers.get('email')
        if not email:
            return {'conversation_count': 0, 'message_count': 0}
        
        logger.info(f"Syncing email history for {email} on channel {channel.name}")
        
        try:
            # Initialize UniPile email client
            email_client = UnipileEmailClient()
            
            # Search for all emails involving this address
            # We'll search both FROM and TO to get complete history
            all_threads = []
            
            # Search emails FROM this address
            from_result = await email_client.search_emails(
                account_id=channel.unipile_account_id,
                from_email=email,
                limit=100  # Adjust based on requirements
            )
            if from_result.get('success'):
                all_threads.extend(from_result.get('emails', []))
            
            # Search emails TO this address
            to_result = await email_client.search_emails(
                account_id=channel.unipile_account_id,
                to_email=email,
                limit=100
            )
            if to_result.get('success'):
                all_threads.extend(to_result.get('emails', []))
            
            # Deduplicate threads by thread_id
            unique_threads = {}
            for thread in all_threads:
                thread_id = thread.get('thread_id') or thread.get('id')
                if thread_id and thread_id not in unique_threads:
                    unique_threads[thread_id] = thread
            
            # Process and store each thread
            conversation_count = 0
            message_count = 0
            
            for thread_id, thread_data in unique_threads.items():
                # Create or update conversation
                conversation = await self.store_email_thread(
                    thread_data,
                    channel,
                    participant
                )
                if conversation:
                    conversation_count += 1
                    # Count messages in thread
                    message_count += thread_data.get('message_count', 1)
            
            logger.info(
                f"Email sync complete: {conversation_count} conversations, "
                f"{message_count} messages for {email}"
            )
            
            return {
                'conversation_count': conversation_count,
                'message_count': message_count
            }
            
        except Exception as e:
            logger.error(f"Error syncing email history: {e}")
            raise
    
    async def sync_whatsapp_history(
        self,
        channel: Channel,
        participant: Participant,
        identifiers: Dict
    ) -> Dict[str, Any]:
        """
        Search and store all WhatsApp chats involving these identifiers
        """
        phone = identifiers.get('phone')
        if not phone:
            return {'conversation_count': 0, 'message_count': 0}
        
        logger.info(f"Syncing WhatsApp history for {phone} on channel {channel.name}")
        
        try:
            # Initialize UniPile messaging client
            messaging_client = UnipileMessagingClient()
            
            # Search for all chats with this phone number
            # WhatsApp uses phone@s.whatsapp.net format
            whatsapp_id = f"{phone.replace('+', '')}@s.whatsapp.net"
            
            # Get all chats
            chats_result = await messaging_client.get_chats(
                account_id=channel.unipile_account_id,
                limit=100
            )
            
            if not chats_result.get('success'):
                logger.warning(f"Failed to get WhatsApp chats: {chats_result.get('error')}")
                return {'conversation_count': 0, 'message_count': 0}
            
            # Filter chats that include this participant
            relevant_chats = []
            for chat in chats_result.get('chats', []):
                # Check if participant is in attendees
                attendees = chat.get('attendees', [])
                for attendee in attendees:
                    if whatsapp_id in attendee.get('provider_id', ''):
                        relevant_chats.append(chat)
                        break
            
            # Process and store each chat
            conversation_count = 0
            message_count = 0
            
            for chat_data in relevant_chats:
                conversation = await self.store_whatsapp_chat(
                    chat_data,
                    channel,
                    participant
                )
                if conversation:
                    conversation_count += 1
                    # Get message count for this chat
                    chat_id = chat_data.get('id')
                    messages_result = await messaging_client.get_messages(
                        account_id=channel.unipile_account_id,
                        chat_id=chat_id,
                        limit=100
                    )
                    if messages_result.get('success'):
                        messages = messages_result.get('messages', [])
                        message_count += len(messages)
                        # Store messages
                        await self.store_chat_messages(conversation, messages, participant)
            
            logger.info(
                f"WhatsApp sync complete: {conversation_count} conversations, "
                f"{message_count} messages for {phone}"
            )
            
            return {
                'conversation_count': conversation_count,
                'message_count': message_count
            }
            
        except Exception as e:
            logger.error(f"Error syncing WhatsApp history: {e}")
            raise
    
    async def sync_linkedin_history(
        self,
        channel: Channel,
        participant: Participant,
        identifiers: Dict
    ) -> Dict[str, Any]:
        """
        Search and store all LinkedIn conversations involving these identifiers
        """
        # Implementation similar to WhatsApp but for LinkedIn
        # Uses linkedin_member_urn for matching
        return {'conversation_count': 0, 'message_count': 0}
    
    async def sync_instagram_history(
        self,
        channel: Channel,
        participant: Participant,
        identifiers: Dict
    ) -> Dict[str, Any]:
        """
        Search and store all Instagram DMs involving these identifiers
        """
        # Implementation for Instagram
        return {'conversation_count': 0, 'message_count': 0}
    
    async def sync_messenger_history(
        self,
        channel: Channel,
        participant: Participant,
        identifiers: Dict
    ) -> Dict[str, Any]:
        """
        Search and store all Messenger chats involving these identifiers
        """
        # Implementation for Facebook Messenger
        return {'conversation_count': 0, 'message_count': 0}
    
    async def sync_telegram_history(
        self,
        channel: Channel,
        participant: Participant,
        identifiers: Dict
    ) -> Dict[str, Any]:
        """
        Search and store all Telegram chats involving these identifiers
        """
        # Implementation for Telegram
        return {'conversation_count': 0, 'message_count': 0}
    
    async def store_email_thread(
        self,
        thread_data: Dict,
        channel: Channel,
        participant: Participant
    ) -> Optional[Conversation]:
        """
        Store an email thread as a conversation with participant links
        """
        try:
            thread_id = thread_data.get('thread_id') or thread_data.get('id')
            
            # Create or update conversation
            conversation, created = await sync_to_async(Conversation.objects.update_or_create)(
                channel=channel,
                external_thread_id=thread_id,
                defaults={
                    'subject': thread_data.get('subject', '(no subject)'),
                    'conversation_type': 'direct',  # Will update if multiple recipients
                    'status': 'active',
                    'metadata': {
                        'email_thread': True,
                        'original_data': thread_data
                    }
                }
            )
            
            # Extract and link all participants
            participants = self.resolution_service.extract_email_participants(thread_data)
            
            for participant_data in participants:
                # Get or create participant
                p, _ = await self.resolution_service.resolve_or_create_participant(
                    participant_data,
                    channel_type='email'
                )
                
                # Link to conversation
                await sync_to_async(ConversationParticipant.objects.update_or_create)(
                    conversation=conversation,
                    participant=p,
                    defaults={
                        'role': participant_data.get('role', 'member'),
                        'is_active': True
                    }
                )
            
            # Update conversation type if group email
            if len(participants) > 2:
                conversation.conversation_type = 'group'
                await sync_to_async(conversation.save)()
            
            logger.info(f"Stored email thread {thread_id} as conversation {conversation.id}")
            return conversation
            
        except Exception as e:
            logger.error(f"Error storing email thread: {e}")
            return None
    
    async def store_whatsapp_chat(
        self,
        chat_data: Dict,
        channel: Channel,
        participant: Participant
    ) -> Optional[Conversation]:
        """
        Store a WhatsApp chat as a conversation with participant links
        """
        try:
            chat_id = chat_data.get('id')
            
            # Determine conversation type
            is_group = chat_data.get('is_group', False) or len(chat_data.get('attendees', [])) > 2
            
            # Create or update conversation
            conversation, created = await sync_to_async(Conversation.objects.update_or_create)(
                channel=channel,
                external_thread_id=chat_id,
                defaults={
                    'subject': chat_data.get('name', 'WhatsApp Chat'),
                    'conversation_type': 'group' if is_group else 'direct',
                    'status': 'active',
                    'metadata': {
                        'whatsapp_chat': True,
                        'is_group': is_group,
                        'original_data': chat_data
                    }
                }
            )
            
            # Link all participants
            participants = self.resolution_service.extract_whatsapp_participants(chat_data)
            
            for participant_data in participants:
                p, _ = await self.resolution_service.resolve_or_create_participant(
                    participant_data,
                    channel_type='whatsapp'
                )
                
                await sync_to_async(ConversationParticipant.objects.update_or_create)(
                    conversation=conversation,
                    participant=p,
                    defaults={
                        'role': participant_data.get('role', 'member'),
                        'is_active': True
                    }
                )
            
            logger.info(f"Stored WhatsApp chat {chat_id} as conversation {conversation.id}")
            return conversation
            
        except Exception as e:
            logger.error(f"Error storing WhatsApp chat: {e}")
            return None
    
    async def store_chat_messages(
        self,
        conversation: Conversation,
        messages: List[Dict],
        participant: Participant
    ):
        """
        Store messages for a conversation
        """
        for message_data in messages:
            try:
                # Determine sender participant
                sender_id = message_data.get('attendee_id')
                sender_participant = participant  # Default to our target participant
                
                # Try to find actual sender
                if sender_id:
                    # Look up sender in conversation participants
                    conv_participant = await sync_to_async(
                        ConversationParticipant.objects.filter(
                            conversation=conversation,
                            provider_participant_id=sender_id
                        ).first
                    )()
                    if conv_participant:
                        sender_participant = conv_participant.participant
                
                # Create message
                await sync_to_async(Message.objects.update_or_create)(
                    external_message_id=message_data.get('id'),
                    conversation=conversation,
                    defaults={
                        'channel': conversation.channel,
                        'sender_participant': sender_participant,
                        'content': message_data.get('text', ''),
                        'direction': 'inbound' if message_data.get('is_received') else 'outbound',
                        'status': 'delivered',
                        'metadata': message_data
                    }
                )
            except Exception as e:
                logger.error(f"Error storing message: {e}")
                continue