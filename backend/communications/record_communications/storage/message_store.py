"""
Message Store - Handles persistence of message data

Stores messages from UniPile and manages updates.
"""
import logging
from typing import Dict, List, Optional, Any
from django.db import transaction
from django.utils import timezone

from communications.models import Message, Conversation, Channel, Participant
from communications.services.field_manager import field_manager

logger = logging.getLogger(__name__)


class MessageStore:
    """Stores and manages message data"""
    
    def store_message(
        self,
        message_data: Dict[str, Any],
        conversation: Conversation,
        channel: Channel,
        sender_participant: Optional[Participant] = None
    ) -> Message:
        """
        Store or update a message
        
        Args:
            message_data: Transformed message data
            conversation: Conversation instance
            channel: Channel instance
            sender_participant: Optional sender Participant
            
        Returns:
            Message instance
        """
        external_id = message_data.get('external_message_id')
        
        if not external_id:
            raise ValueError("Message must have external_message_id")
        
        # Get or create message
        message, created = Message.objects.get_or_create(
            external_message_id=external_id,
            conversation=conversation,
            defaults={
                'channel': channel,
                'sender_participant': sender_participant,
                'direction': message_data.get('direction', 'inbound'),
                'content': message_data.get('content', ''),
                'subject': message_data.get('subject', ''),  # Include subject for emails
                'sent_at': message_data.get('sent_at'),
                'created_at': message_data.get('created_at', timezone.now()),
                'metadata': message_data.get('metadata', {}),
                'status': message_data.get('status', 'sent')
            }
        )
        
        if not created:
            # Update existing message
            message.content = message_data.get('content', message.content)
            message.metadata.update(message_data.get('metadata', {}))
            message.status = message_data.get('status', message.status)
            
            # Update sender if provided
            if sender_participant:
                message.sender_participant = sender_participant
            
            message.save()
        else:
            # New message created - use field manager to set additional fields
            # Set proper timestamps
            field_manager.set_message_timestamps(
                message,
                sent_at=message_data.get('sent_at'),
                received_at=message_data.get('received_at')
            )
            
            # Set subject for email messages
            if message_data.get('subject'):
                field_manager.set_message_subject(message, message_data['subject'])
            
            # Update channel statistics
            if channel:
                field_manager.update_channel_stats(channel)
        
        logger.debug(
            f"{'Created' if created else 'Updated'} message {message.id} "
            f"(external: {external_id})"
        )
        
        return message
    
    def store_bulk_messages(
        self,
        messages_data: List[Dict[str, Any]],
        conversation: Conversation,
        channel: Channel,
        participant_cache: Optional[Dict[str, Participant]] = None
    ) -> List[Message]:
        """
        Store multiple messages efficiently using bulk_create
        
        Args:
            messages_data: List of transformed message data
            conversation: Conversation instance
            channel: Channel instance
            participant_cache: Optional shared participant cache to avoid rebuilding
            
        Returns:
            List of Message instances
        """
        if not messages_data:
            return []
        
        with transaction.atomic():
            # First, get all existing message IDs for this conversation
            existing_ids = set(
                Message.objects.filter(
                    conversation=conversation,
                    external_message_id__in=[
                        msg.get('external_message_id') 
                        for msg in messages_data 
                        if msg.get('external_message_id')
                    ]
                ).values_list('external_message_id', flat=True)
            )
            
            # Build participant cache if not provided (for backward compatibility)
            if participant_cache is None:
                participant_cache = self._build_participant_cache(messages_data)
            
            # Prepare messages for bulk creation
            messages_to_create = []
            messages_to_update = []
            
            for msg_data in messages_data:
                external_id = msg_data.get('external_message_id')
                if not external_id:
                    logger.warning("Skipping message without external_message_id")
                    continue
                
                # Skip if message already exists
                if external_id in existing_ids:
                    messages_to_update.append(msg_data)
                    continue
                
                # Get participant from cache
                sender_participant = self._get_participant_from_cache(msg_data, participant_cache)
                
                # Create Message instance (not saved yet)
                message = Message(
                    external_message_id=external_id,
                    conversation=conversation,
                    channel=channel,
                    sender_participant=sender_participant,
                    direction=msg_data.get('direction', 'inbound'),
                    content=msg_data.get('content', ''),
                    subject=msg_data.get('subject', ''),  # Include subject field
                    sent_at=msg_data.get('sent_at'),
                    received_at=msg_data.get('received_at'),
                    created_at=msg_data.get('created_at', timezone.now()),
                    metadata=msg_data.get('metadata', {}),
                    status=msg_data.get('status', 'sent')
                )
                messages_to_create.append(message)
            
            # Bulk create new messages
            created_messages = []
            if messages_to_create:
                # Bulk create in batches of 500 to avoid database limits
                batch_size = 500
                for i in range(0, len(messages_to_create), batch_size):
                    batch = messages_to_create[i:i + batch_size]
                    created = Message.objects.bulk_create(batch, ignore_conflicts=True)
                    created_messages.extend(created)
                
                logger.info(f"Bulk created {len(created_messages)} messages for conversation {conversation.id}")
                
                # Since bulk_create doesn't trigger signals, manually populate fields
                for message in created_messages:
                    # Set received_at for inbound messages
                    if message.direction == 'inbound' and not message.received_at:
                        message.received_at = message.created_at
                        
                # Bulk update the received_at field
                if any(msg.direction == 'inbound' for msg in created_messages):
                    Message.objects.bulk_update(
                        [msg for msg in created_messages if msg.direction == 'inbound'],
                        ['received_at']
                    )
                
                # Update conversation statistics
                if conversation:
                    field_manager.update_conversation_stats(conversation)
                    field_manager.detect_conversation_type(conversation)
                
                # Update channel statistics after bulk creation
                if channel and created_messages:
                    field_manager.update_channel_stats(channel)
            
            # Handle updates - update ALL messages to ensure metadata is current
            updated_count = 0
            if messages_to_update:
                # Batch update existing messages with new metadata
                for msg_data in messages_to_update:
                    try:
                        external_id = msg_data.get('external_message_id')
                        if external_id:
                            # Get the correct sender participant from cache
                            sender_participant = self._get_participant_from_cache(msg_data, participant_cache)
                            
                            # Update the message with new metadata (especially is_sender flag)
                            update_fields = {
                                'direction': msg_data.get('direction', 'inbound'),
                                'metadata': msg_data.get('metadata', {}),
                                'status': msg_data.get('status', 'sent')
                            }
                            
                            # Only update sender_participant if we found one
                            if sender_participant:
                                update_fields['sender_participant'] = sender_participant
                            
                            Message.objects.filter(
                                external_message_id=external_id,
                                conversation=conversation
                            ).update(**update_fields)
                            updated_count += 1
                    except Exception as e:
                        logger.error(f"Failed to update message {external_id}: {e}")
                
                logger.info(f"Updated {updated_count} existing messages with new metadata")
            
            total_processed = len(created_messages) + updated_count
            logger.info(f"Processed {total_processed} messages (created: {len(created_messages)}, updated: {updated_count})")
            
            # Create ConversationParticipant links for all participants in this conversation
            self._create_conversation_participants(messages_data, conversation, participant_cache)
            
            # Return all messages (fetch existing ones if needed)
            all_external_ids = [msg.get('external_message_id') for msg in messages_data if msg.get('external_message_id')]
            return list(Message.objects.filter(
                conversation=conversation,
                external_message_id__in=all_external_ids
            ))
    
    def _create_conversation_participants(
        self, 
        messages_data: List[Dict[str, Any]], 
        conversation: Conversation,
        participant_cache: Dict[str, Participant]
    ):
        """
        Create ConversationParticipant links for all participants in this conversation
        
        Args:
            messages_data: List of message data dictionaries  
            conversation: Conversation instance
            participant_cache: Cache of participants
        """
        from communications.models import ConversationParticipant
        
        # Track unique participants and their roles
        participants_roles = {}  # participant_id: set of roles
        
        for msg_data in messages_data:
            metadata = msg_data.get('metadata', {})
            
            # Process sender - handle both email-style and messaging-style
            # Try to find the sender participant from the cache
            sender_participant = self._get_participant_from_cache(msg_data, participant_cache)
            if sender_participant:
                if sender_participant.id not in participants_roles:
                    participants_roles[sender_participant.id] = set()
                participants_roles[sender_participant.id].add('sender')
            # Also try email-style from field
            elif metadata.get('from'):
                participant = self._get_participant_from_metadata(metadata['from'], participant_cache)
                if participant:
                    if participant.id not in participants_roles:
                        participants_roles[participant.id] = set()
                    participants_roles[participant.id].add('sender')
            
            # Process recipients (email-style)
            for field, role in [('to', 'recipient'), ('cc', 'cc'), ('bcc', 'bcc')]:
                recipients = metadata.get(field, [])
                if isinstance(recipients, list):
                    for recipient in recipients:
                        participant = self._get_participant_from_metadata(recipient, participant_cache)
                        if participant:
                            if participant.id not in participants_roles:
                                participants_roles[participant.id] = set()
                            participants_roles[participant.id].add(role)
        
        # Get existing ConversationParticipant records
        existing = ConversationParticipant.objects.filter(
            conversation=conversation,
            participant_id__in=participants_roles.keys()
        ).values_list('participant_id', flat=True)
        
        # Create missing ConversationParticipant records
        to_create = []
        for participant_id, roles in participants_roles.items():
            if participant_id not in existing:
                # Choose the most specific role
                if 'sender' in roles:
                    role = 'sender'
                elif 'recipient' in roles:
                    role = 'recipient'
                elif 'cc' in roles:
                    role = 'cc'
                elif 'bcc' in roles:
                    role = 'bcc'
                else:
                    role = 'member'
                
                to_create.append(
                    ConversationParticipant(
                        conversation=conversation,
                        participant_id=participant_id,
                        role=role,
                        message_count=0  # Will be updated separately
                    )
                )
        
        if to_create:
            created = ConversationParticipant.objects.bulk_create(to_create, ignore_conflicts=True)
            logger.info(f"Created {len(to_create)} ConversationParticipant links")
            
            # Since bulk_create doesn't trigger signals, update participant statistics
            for cp in created:
                field_manager.update_participant_activity(cp)
    
    def _get_participant_from_metadata(
        self, 
        data: Any, 
        participant_cache: Dict[str, Participant]
    ) -> Optional[Participant]:
        """
        Get participant from metadata using cache
        
        Args:
            data: Email/phone/provider data (dict or string)
            participant_cache: Cache of participants
            
        Returns:
            Participant instance or None
        """
        if isinstance(data, dict):
            # Try email first
            email = data.get('email', '').lower()
            if email and f"email:{email}" in participant_cache:
                return participant_cache[f"email:{email}"]
            
            # Try phone
            phone = data.get('phone', '')
            if phone and f"phone:{phone}" in participant_cache:
                return participant_cache[f"phone:{phone}"]
            
            # Try provider_id (for WhatsApp/LinkedIn)
            provider_id = data.get('provider_id', '')
            if provider_id:
                # Check if it's WhatsApp
                if '@s.whatsapp.net' in provider_id:
                    phone = provider_id.replace('@s.whatsapp.net', '')
                    if f"phone:{phone}" in participant_cache:
                        return participant_cache[f"phone:{phone}"]
                
                # Check by provider_id directly
                if f"provider:{provider_id}" in participant_cache:
                    return participant_cache[f"provider:{provider_id}"]
                
                # Check if it's LinkedIn
                if provider_id.startswith('ACo') and f"linkedin:{provider_id}" in participant_cache:
                    return participant_cache[f"linkedin:{provider_id}"]
                
        elif isinstance(data, str):
            # Handle string data (email, phone, or provider_id)
            if '@' in data and '.' in data:
                # Likely an email
                email = data.lower()
                if f"email:{email}" in participant_cache:
                    return participant_cache[f"email:{email}"]
            elif '@s.whatsapp.net' in data:
                # WhatsApp ID
                phone = data.replace('@s.whatsapp.net', '')
                if f"phone:{phone}" in participant_cache:
                    return participant_cache[f"phone:{phone}"]
            elif data.startswith('+'):
                # Phone number
                if f"phone:{data}" in participant_cache:
                    return participant_cache[f"phone:{data}"]
        
        return None
    
    def _identify_sender_participant(self, message_data: Dict[str, Any]) -> Optional[Participant]:
        """
        Identify the sender participant from message data
        
        Args:
            message_data: Message data with metadata
            
        Returns:
            Participant instance or None
        """
        metadata = message_data.get('metadata', {})
        
        # Try to find participant by various fields
        sender_id = metadata.get('sender_id')
        sender_email = None
        sender_phone = None
        
        # Extract sender info from metadata
        if metadata.get('from'):
            from_data = metadata['from']
            if isinstance(from_data, dict):
                sender_email = from_data.get('email')
                sender_phone = from_data.get('phone')
            elif isinstance(from_data, str):
                # Could be email or phone
                if '@' in from_data:
                    sender_email = from_data
                else:
                    sender_phone = from_data
        
        # Build query for participant
        from django.db.models import Q
        query = Q()
        
        if sender_email:
            query |= Q(email__iexact=sender_email)
        if sender_phone:
            query |= Q(phone=sender_phone)
        if sender_id:
            query |= Q(metadata__external_id=sender_id)
        
        # Also check provider_id
        provider_id = metadata.get('provider_id')
        if provider_id:
            query |= Q(metadata__provider_id=provider_id)
        
        if query:
            participant = Participant.objects.filter(query).first()
            
            if participant:
                return participant
        
        # Create participant if we have enough info
        if sender_email or sender_phone:
            participant = Participant.objects.create(
                email=sender_email or '',
                phone=sender_phone or '',
                name=metadata.get('sender_name', ''),
                metadata={
                    'external_id': sender_id,
                    'provider_id': provider_id,
                    'created_from': 'message_store'
                }
            )
            logger.debug(f"Created participant from message sender: {participant.id}")
            return participant
        
        return None
    
    def update_message_status(
        self,
        message: Message,
        status: str
    ):
        """
        Update message status
        
        Args:
            message: Message instance
            status: New status
        """
        message.status = status
        message.save(update_fields=['status'])
    
    def get_conversation_message_count(self, conversation: Conversation) -> int:
        """
        Get total message count for a conversation
        
        Args:
            conversation: Conversation instance
            
        Returns:
            Message count
        """
        return Message.objects.filter(conversation=conversation).count()
    
    def get_conversation_unread_count(self, conversation: Conversation) -> int:
        """
        Get unread message count for a conversation
        
        Args:
            conversation: Conversation instance
            
        Returns:
            Unread message count
        """
        # Note: Message model doesn't have is_read field
        # Unread count should be tracked at the conversation level
        return 0
    
    def build_participant_cache_for_all_messages(
        self, 
        all_messages_data: List[Dict[str, Any]],
        attendee_names: Optional[Dict[str, str]] = None
    ) -> Dict[str, Participant]:
        """
        Build a participant cache for ALL messages across all conversations
        This should be called once at the beginning of a sync operation
        
        Args:
            all_messages_data: List of ALL message data dictionaries across all conversations
            attendee_names: Optional pre-fetched mapping of identifier to name from UniPile
            
        Returns:
            Dict mapping identifier keys to Participant instances
        """
        logger.info(f"Building participant cache for {len(all_messages_data)} messages")
        if attendee_names:
            logger.info(f"Using pre-fetched names: {len(attendee_names)} names available")
        return self._build_participant_cache(all_messages_data, attendee_names)
    
    def _build_participant_cache(
        self, 
        messages_data: List[Dict[str, Any]],
        attendee_names: Optional[Dict[str, str]] = None
    ) -> Dict[str, Participant]:
        """
        Build a cache of participants for all messages to avoid N queries
        
        Args:
            messages_data: List of message data dictionaries
            attendee_names: Optional pre-fetched mapping of identifier to name from UniPile
            
        Returns:
            Dict mapping identifier keys to Participant instances
        """
        from django.db.models import Q
        
        # Initialize attendee_names if not provided
        if attendee_names is None:
            attendee_names = {}
        
        # Collect all unique participant identifiers WITH names
        # Structure: {email/phone: name}
        email_to_name = {}
        phone_to_name = {}
        provider_to_info = {}  # {provider_id: {name, phone, email, linkedin}}
        
        for i, msg_data in enumerate(messages_data):
            metadata = msg_data.get('metadata', {})
            
            # Debug logging for first few messages
            if i < 3:
                logger.debug(f"Message {i+1} data sample:")
                logger.debug(f"  - Has sender: {bool(msg_data.get('sender'))}")
                logger.debug(f"  - Has metadata.from: {bool(metadata.get('from'))}")
                logger.debug(f"  - Channel type: {msg_data.get('channel_type', 'none')}")
                if msg_data.get('sender'):
                    sender = msg_data['sender']
                    logger.debug(f"  - Sender info: name='{sender.get('name', '')}', provider_id='{sender.get('provider_id', '')}'")
            
            # Extract from EMAIL messages (existing logic)
            if metadata.get('from'):
                from_data = metadata['from']
                if isinstance(from_data, dict):
                    email = from_data.get('email', '').lower()
                    name = from_data.get('name', '')
                    if email:
                        # Use pre-fetched name if available and better
                        pre_fetched_name = attendee_names.get(email, '')
                        final_name = pre_fetched_name if pre_fetched_name else name
                        # Keep the best name (longest non-empty)
                        if email not in email_to_name or len(final_name) > len(email_to_name.get(email, '')):
                            email_to_name[email] = final_name
                    
                    phone = from_data.get('phone', '')
                    if phone:
                        # Use pre-fetched name if available and better
                        pre_fetched_name = attendee_names.get(phone, '')
                        final_name = pre_fetched_name if pre_fetched_name else name
                        if phone not in phone_to_name or len(final_name) > len(phone_to_name.get(phone, '')):
                            phone_to_name[phone] = final_name
                elif isinstance(from_data, str):
                    # WhatsApp/LinkedIn may put phone/provider_id here
                    if '@' in from_data:
                        # When from is just an email string, try to get name from metadata
                        sender_name = metadata.get('sender_name', '')
                        email_to_name[from_data.lower()] = sender_name
                    elif from_data.startswith('+') or from_data.replace('@s.whatsapp.net', ''):
                        # WhatsApp phone format
                        phone = from_data.replace('@s.whatsapp.net', '')
                        # Use pre-fetched name if available
                        pre_fetched_name = attendee_names.get(phone, '') or attendee_names.get(from_data, '')
                        phone_to_name[phone] = pre_fetched_name if pre_fetched_name else metadata.get('sender_name', '')
                    else:
                        # Could be LinkedIn provider_id
                        pre_fetched_name = attendee_names.get(from_data, '')
                        provider_to_info[from_data] = {
                            'name': pre_fetched_name if pre_fetched_name else metadata.get('sender_name', ''),
                            'provider_id': from_data
                        }
            
            # Extract enriched sender info (from message enricher)
            sender_info = msg_data.get('sender', {})
            if sender_info:
                # Handle WhatsApp sender
                if sender_info.get('phone'):
                    phone = sender_info['phone']
                    name = sender_info.get('name', '')
                    # Use pre-fetched name if available and better
                    pre_fetched_name = attendee_names.get(phone, '')
                    final_name = pre_fetched_name if pre_fetched_name else name
                    if phone:
                        if phone not in phone_to_name or len(final_name) > len(phone_to_name.get(phone, '')):
                            phone_to_name[phone] = final_name
                
                # Handle LinkedIn sender (use account identifier as LinkedIn URN)
                elif sender_info.get('linkedin_urn'):
                    linkedin_urn = sender_info['linkedin_urn']
                    name = sender_info.get('name', '')
                    # Use provider_id as key for consistency
                    prov_id = sender_info.get('provider_id', '')
                    # Use pre-fetched name if available and better
                    pre_fetched_name = attendee_names.get(prov_id, '') or attendee_names.get(linkedin_urn, '')
                    final_name = pre_fetched_name if pre_fetched_name else name
                    if prov_id:
                        provider_to_info[prov_id] = {
                            'name': final_name,
                            'linkedin': linkedin_urn,
                            'provider_id': prov_id
                        }
                
                # Handle generic sender by provider_id (including LinkedIn without URN)
                elif sender_info.get('provider_id'):
                    prov_id = sender_info['provider_id']
                    if prov_id and prov_id not in provider_to_info:
                        # Check channel type from enriched message
                        channel_type = msg_data.get('channel_type', '')
                        
                        # For WhatsApp, extract phone from provider_id
                        if channel_type == 'whatsapp' and '@s.whatsapp.net' in prov_id:
                            phone = prov_id.replace('@s.whatsapp.net', '')
                            # Use pre-fetched name if available (keyed by phone without suffix)
                            pre_fetched_name = attendee_names.get(phone, '') or attendee_names.get(prov_id, '')
                            sender_name = pre_fetched_name if pre_fetched_name else sender_info.get('name', '')
                            provider_to_info[prov_id] = {
                                'name': sender_name,
                                'phone': phone,  # Store actual phone number
                                'provider_id': prov_id
                            }
                        elif channel_type == 'linkedin':
                            # Use pre-fetched name if available
                            pre_fetched_name = attendee_names.get(prov_id, '')
                            sender_name = pre_fetched_name if pre_fetched_name else sender_info.get('name', '')
                            # This is a LinkedIn participant without URN
                            provider_to_info[prov_id] = {
                                'name': sender_name,
                                'provider_id': prov_id,
                                'linkedin': '',  # Empty URN but mark as LinkedIn
                                'is_linkedin': True
                            }
                        else:
                            # Use pre-fetched name if available
                            pre_fetched_name = attendee_names.get(prov_id, '')
                            sender_name = pre_fetched_name if pre_fetched_name else sender_info.get('name', '')
                            provider_to_info[prov_id] = {
                                'name': sender_name,
                                'provider_id': prov_id
                            }
            
            # ALSO check unipile_data.sender (for stored messages being re-processed)
            unipile_data = metadata.get('unipile_data', {})
            unipile_sender = unipile_data.get('sender', {})
            if unipile_sender and not sender_info:  # Only if not already processed above
                # Handle LinkedIn with URN
                if unipile_sender.get('linkedin_urn'):
                    linkedin_urn = unipile_sender['linkedin_urn']
                    name = unipile_sender.get('name', '')
                    prov_id = unipile_sender.get('provider_id', '')
                    if prov_id and prov_id not in provider_to_info:
                        provider_to_info[prov_id] = {
                            'name': name,
                            'linkedin': linkedin_urn,
                            'provider_id': prov_id
                        }
                # Handle WhatsApp with phone
                elif unipile_sender.get('phone'):
                    phone = unipile_sender['phone']
                    name = unipile_sender.get('name', '')
                    if phone and (phone not in phone_to_name or len(name) > len(phone_to_name.get(phone, ''))):
                        phone_to_name[phone] = name
                # Handle generic by provider_id
                elif unipile_sender.get('provider_id'):
                    prov_id = unipile_sender['provider_id']
                    if prov_id and prov_id not in provider_to_info:
                        provider_to_info[prov_id] = {
                            'name': unipile_sender.get('name', ''),
                            'provider_id': prov_id
                        }
            else:
                # Fallback to old extraction logic for un-enriched messages
                sender_name = metadata.get('sender_name', '')
                sender_id = metadata.get('sender_id', '')
                provider_id = metadata.get('provider_id', '')
            
            # Extract to/cc/bcc participants with names (EMAIL)
            for field in ['to', 'cc', 'bcc']:
                recipients = metadata.get(field, [])
                if isinstance(recipients, list):
                    for recipient in recipients:
                        if isinstance(recipient, dict):
                            email = recipient.get('email', '').lower()
                            name = recipient.get('name', '')
                            # Use pre-fetched name if available
                            pre_fetched_name = attendee_names.get(email, '')
                            final_name = pre_fetched_name if pre_fetched_name else name
                            if email:
                                if email not in email_to_name or len(final_name) > len(email_to_name.get(email, '')):
                                    email_to_name[email] = final_name
                        elif isinstance(recipient, str) and '@' in recipient:
                            # Sometimes recipients are just email strings
                            email = recipient.lower()
                            # Try to get name from attendee_names
                            pre_fetched_name = attendee_names.get(email, '')
                            if email not in email_to_name or len(pre_fetched_name) > len(email_to_name.get(email, '')):
                                email_to_name[email] = pre_fetched_name
        
        logger.info(f"Participant extraction summary:")
        logger.info(f"  - Emails: {len(email_to_name)}")
        logger.info(f"  - Phones: {len(phone_to_name)}")
        logger.info(f"  - Provider IDs: {len(provider_to_info)}")
        
        # Build query to fetch all existing participants at once
        query = Q()
        all_emails = set(email_to_name.keys())
        all_phones = set(phone_to_name.keys())
        all_provider_ids = set(provider_to_info.keys())
        all_linkedin_urns = set()
        
        # Extract LinkedIn URNs from provider_to_info
        for info in provider_to_info.values():
            if info.get('linkedin'):
                all_linkedin_urns.add(info['linkedin'])
        
        logger.info(f"  - LinkedIn URNs: {len(all_linkedin_urns)}")
        
        if all_emails:
            query |= Q(email__in=list(all_emails))
        if all_phones:
            query |= Q(phone__in=list(all_phones))
        if all_linkedin_urns:
            query |= Q(linkedin_member_urn__in=list(all_linkedin_urns))
        if all_provider_ids:
            query |= Q(metadata__provider_id__in=list(all_provider_ids))
        
        # Fetch all matching participants in one query
        participant_cache = {}
        if query:
            participants = Participant.objects.filter(query)
            
            # Index by all possible keys AND update names if better ones found
            for participant in participants:
                if participant.email:
                    email_key = f"email:{participant.email.lower()}"
                    participant_cache[email_key] = participant
                    
                    # Update name if we have a better one
                    new_name = email_to_name.get(participant.email.lower(), '')
                    if new_name and (not participant.name or len(new_name) > len(participant.name)):
                        participant.name = new_name
                        participant.save(update_fields=['name'])
                        
                if participant.phone:
                    phone_key = f"phone:{participant.phone}"
                    participant_cache[phone_key] = participant
                    
                    # Update name if we have a better one
                    new_name = phone_to_name.get(participant.phone, '')
                    if new_name and (not participant.name or len(new_name) > len(participant.name)):
                        participant.name = new_name
                        participant.save(update_fields=['name'])
                        
                if participant.linkedin_member_urn:
                    linkedin_key = f"linkedin:{participant.linkedin_member_urn}"
                    participant_cache[linkedin_key] = participant
                    
                    # Update name if we have a better one from provider_to_info
                    for prov_id, info in provider_to_info.items():
                        if info.get('linkedin') == participant.linkedin_member_urn:
                            new_name = info.get('name', '')
                            if new_name and (not participant.name or len(new_name) > len(participant.name)):
                                participant.name = new_name
                                participant.save(update_fields=['name'])
                                break
                        
                if participant.metadata.get('provider_id'):
                    provider_id = participant.metadata['provider_id']
                    participant_cache[f"provider:{provider_id}"] = participant
                    
                    # Update name from pre-fetched attendee names if available
                    if attendee_names:
                        # Check if we have a name for this provider_id
                        new_name = attendee_names.get(provider_id, '')
                        if new_name and (not participant.name or len(new_name) > len(participant.name)):
                            participant.name = new_name
                            participant.save(update_fields=['name'])
                            logger.info(f"Updated participant {participant.id} name to '{new_name}' from pre-fetched attendee data")
                        elif provider_id in attendee_names:
                            logger.debug(f"Skipped updating participant {participant.id}: existing name '{participant.name}' is better than '{attendee_names[provider_id]}'")
                        else:
                            logger.debug(f"No name found for provider_id '{provider_id}' in attendee_names")
        
        logger.info(f"Built participant cache with {len(participant_cache)} existing participants")
        
        # Update existing participants with better names
        participants_to_update = []
        for email, name in email_to_name.items():
            cache_key = f"email:{email}"
            if cache_key in participant_cache and name:
                participant = participant_cache[cache_key]
                # Update if participant has no name, email as name, or a shorter name
                if not participant.name or participant.name == email or '@' in participant.name or len(name) > len(participant.name):
                    participant.name = name
                    participants_to_update.append(participant)
        
        # Also update phone participants with better names
        for phone, name in phone_to_name.items():
            cache_key = f"phone:{phone}"
            if cache_key in participant_cache and name:
                participant = participant_cache[cache_key]
                # Update if participant has no name or a shorter name
                if not participant.name or len(name) > len(participant.name):
                    participant.name = name
                    participants_to_update.append(participant)
        
        # Bulk update participant names
        if participants_to_update:
            Participant.objects.bulk_update(participants_to_update, ['name'])
            logger.info(f"Updated {len(participants_to_update)} participant names")
        
        # Create missing participants in bulk WITH NAMES
        participants_to_create = []
        
        for email, name in email_to_name.items():
            if f"email:{email}" not in participant_cache:
                participants_to_create.append(
                    Participant(
                        email=email, 
                        name=name or '',  # Use the extracted name
                        metadata={'created_from': 'bulk_message_store'}
                    )
                )
        
        for phone, name in phone_to_name.items():
            if f"phone:{phone}" not in participant_cache:
                # Log when creating WhatsApp participants with names
                if name:
                    logger.info(f"Creating WhatsApp participant with phone '{phone}' and name '{name}'")
                participants_to_create.append(
                    Participant(
                        phone=phone, 
                        name=name or '',  # Use the extracted name
                        metadata={'created_from': 'bulk_message_store'}
                    )
                )
        
        # Create participants for WhatsApp and LinkedIn from provider_to_info
        for provider_id, info in provider_to_info.items():
            participant_exists = False
            
            # Check if participant exists by phone (WhatsApp)
            if info.get('phone') and f"phone:{info['phone']}" in participant_cache:
                participant_exists = True
                
            # Check if participant exists by LinkedIn URN
            if info.get('linkedin') and f"linkedin:{info['linkedin']}" in participant_cache:
                participant_exists = True
                
            # Check if participant exists by provider_id
            if f"provider:{provider_id}" in participant_cache:
                participant_exists = True
                
            if not participant_exists:
                # Create new participant with appropriate identifiers
                # Ensure name is always set (even if empty string) to avoid NULL constraint
                participant_name = info.get('name') or ''
                
                # Log when creating LinkedIn participants with names
                if info.get('linkedin') and participant_name:
                    logger.info(f"Creating LinkedIn participant with provider_id '{provider_id}' and name '{participant_name}'")
                elif info.get('phone') and participant_name:
                    logger.info(f"Creating messaging participant with phone '{info['phone']}' and name '{participant_name}'")
                
                participant_data = {
                    'name': participant_name,  # Always provide a name, even if empty
                    'email': '',  # Explicitly set empty string for required fields
                    'phone': '',
                    'metadata': {
                        'created_from': 'bulk_message_store',
                        'provider_id': provider_id
                    }
                }
                
                # Add phone for WhatsApp
                if info.get('phone'):
                    participant_data['phone'] = info['phone']
                    
                # Add LinkedIn URN
                if info.get('linkedin'):
                    participant_data['linkedin_member_urn'] = info['linkedin']
                    
                participants_to_create.append(Participant(**participant_data))
        
        if participants_to_create:
            created = Participant.objects.bulk_create(participants_to_create, ignore_conflicts=True)
            logger.info(f"Bulk created {len(created)} new participants")
            
            # Since bulk_create doesn't trigger signals, set initial fields
            now = timezone.now()
            for participant in created:
                participant.first_seen = now
                participant.last_seen = now
                
            # Bulk update the timestamps
            if created:
                Participant.objects.bulk_update(created, ['first_seen', 'last_seen'])
            
            # Add newly created participants to cache
            for participant in created:
                if participant.email:
                    participant_cache[f"email:{participant.email.lower()}"] = participant
                if participant.phone:
                    participant_cache[f"phone:{participant.phone}"] = participant
                if participant.linkedin_member_urn:
                    participant_cache[f"linkedin:{participant.linkedin_member_urn}"] = participant
                if participant.metadata.get('provider_id'):
                    participant_cache[f"provider:{participant.metadata['provider_id']}"] = participant
        
        return participant_cache
    
    def _get_participant_from_cache(
        self, 
        message_data: Dict[str, Any], 
        participant_cache: Dict[str, Participant]
    ) -> Optional[Participant]:
        """
        Get participant from cache without database query
        
        Args:
            message_data: Message data dictionary
            participant_cache: Pre-built participant cache
            
        Returns:
            Participant instance or None
        """
        metadata = message_data.get('metadata', {})
        
        # FIRST: Try enriched sender info (WhatsApp, LinkedIn, etc.)
        sender_info = message_data.get('sender', {})
        if sender_info:
            # Try by phone (WhatsApp)
            if sender_info.get('phone'):
                phone_key = f"phone:{sender_info['phone']}"
                if phone_key in participant_cache:
                    return participant_cache[phone_key]
            
            # Try by LinkedIn URN
            if sender_info.get('linkedin_urn'):
                linkedin_key = f"linkedin:{sender_info['linkedin_urn']}"
                if linkedin_key in participant_cache:
                    return participant_cache[linkedin_key]
            
            # Try by provider_id from enriched data
            if sender_info.get('provider_id'):
                provider_key = f"provider:{sender_info['provider_id']}"
                if provider_key in participant_cache:
                    return participant_cache[provider_key]
        
        # SECOND: Try unipile_data.sender (for already-stored messages)
        unipile_data = metadata.get('unipile_data', {})
        unipile_sender = unipile_data.get('sender', {})
        if unipile_sender:
            # Try by LinkedIn URN
            if unipile_sender.get('linkedin_urn'):
                linkedin_key = f"linkedin:{unipile_sender['linkedin_urn']}"
                if linkedin_key in participant_cache:
                    return participant_cache[linkedin_key]
            
            # Try by phone
            if unipile_sender.get('phone'):
                phone_key = f"phone:{unipile_sender['phone']}"
                if phone_key in participant_cache:
                    return participant_cache[phone_key]
            
            # Try by provider_id
            if unipile_sender.get('provider_id'):
                provider_key = f"provider:{unipile_sender['provider_id']}"
                if provider_key in participant_cache:
                    return participant_cache[provider_key]
        
        # THIRD: Try metadata.from (emails)
        if metadata.get('from'):
            from_data = metadata['from']
            if isinstance(from_data, dict):
                email = from_data.get('email')
                phone = from_data.get('phone')
                if email and f"email:{email.lower()}" in participant_cache:
                    return participant_cache[f"email:{email.lower()}"]
                if phone and f"phone:{phone}" in participant_cache:
                    return participant_cache[f"phone:{phone}"]
            elif isinstance(from_data, str):
                if '@' in from_data:
                    cache_key = f"email:{from_data.lower()}"
                else:
                    cache_key = f"phone:{from_data}"
                if cache_key in participant_cache:
                    return participant_cache[cache_key]
        
        # FOURTH: Try provider_id from metadata
        provider_id = metadata.get('provider_id')
        if provider_id and f"provider:{provider_id}" in participant_cache:
            return participant_cache[f"provider:{provider_id}"]
        
        return None