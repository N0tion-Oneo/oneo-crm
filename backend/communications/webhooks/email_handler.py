"""
Dedicated Email Webhook Handler for UniPile Gmail Integration
Handles the complexity of email processing separate from WhatsApp
Now with selective storage based on contact resolution
"""
import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from communications.models import (
    UserChannelConnection, Message, Conversation, Channel, 
    ChannelType, MessageDirection, MessageStatus, Participant, ConversationParticipant
)
from communications.services.participant_resolution import (
    ParticipantResolutionService, ConversationStorageDecider
)
from communications.record_communications.storage.participant_link_manager import ParticipantLinkManager
from communications.utils.email_extractor import (
    extract_email_from_webhook,
    extract_email_subject_from_webhook,
    extract_email_name_from_webhook,
    determine_email_direction,
    extract_email_thread_id,
    extract_email_message_id,
    extract_email_attachments,
    extract_email_folder_labels,
    extract_email_recipients_info,
    extract_email_sender_info,
    get_display_name_or_email
)

logger = logging.getLogger(__name__)


class EmailWebhookHandler:
    """Specialized handler for email webhook events from UniPile"""
    
    def __init__(self):
        self.resolution_service = ParticipantResolutionService()
        self.storage_decider = ConversationStorageDecider()
        self.link_manager = ParticipantLinkManager()
    
    def handle_email_received(self, account_id: str, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming email webhook with selective storage based on contact resolution
        
        Args:
            account_id: UniPile account ID
            webhook_data: Raw email webhook data from UniPile
            
        Returns:
            Dict with processing result including storage decision
        """
        try:
            logger.info(f"Processing email webhook for account {account_id}")
            
            # Get user connection
            from communications.webhooks.routing import account_router
            connection = account_router.get_user_connection(account_id)
            if not connection:
                logger.error(f"No user connection found for account {account_id}")
                return {'success': False, 'error': 'User connection not found'}
            
            # Validate that this is actually an email connection
            if connection.channel_type not in ['gmail', 'outlook', 'mail', 'email']:
                logger.warning(f"Account {account_id} is not an email account: {connection.channel_type}")
                return {'success': False, 'error': f'Invalid channel type for email: {connection.channel_type}'}
            
            # Extract email-specific data using our email extractors
            normalized_email = self._normalize_email_webhook(webhook_data, connection)
            
            # Extract all participants and check resolution
            should_store, participants = self._check_participant_resolution(normalized_email, connection)
            
            # Prepare response data (always return data even if not storing)
            has_contact = any(p.contact_record for p in participants)
            response_data = {
                'success': True,
                'channel_type': connection.channel_type,
                'email_specific': True,
                'subject': normalized_email['subject'],
                'thread_id': normalized_email['thread_id'],
                'external_message_id': normalized_email['message_id'],
                'storage_decision': {
                    'should_store': should_store,
                    'reason': 'contact_match' if should_store else 'no_contact_match'
                },
                'participants': [
                    {
                        'id': str(p.id),
                        'email': p.email,
                        'name': p.name,
                        'has_contact': bool(p.contact_record),
                        'contact_id': str(p.contact_record.id) if p.contact_record else None,
                        'confidence': p.resolution_confidence
                    } for p in participants
                ],
                'contact_resolution': {
                    'found': has_contact,
                    'participant_count': len(participants),
                    'with_contacts': sum(1 for p in participants if p.contact_record)
                }
            }
            
            # Only store if at least one participant has a contact match
            if should_store:
                logger.info(f"Contact found for email, storing message. {sum(1 for p in participants if p.contact_record)} participants with contacts")
                
                # Check for duplicate emails using tracking_id first, then external_message_id
                tracking_id = webhook_data.get('tracking_id')
                external_message_id = normalized_email['message_id']
                existing_message = None
                
                # First try to find by tracking_id (for messages we sent)
                if tracking_id:
                    existing_message = Message.objects.filter(
                        metadata__tracking_id=tracking_id
                    ).first()
                    
                    if existing_message:
                        logger.info(f"Found existing message by tracking_id {tracking_id} (ID: {existing_message.id})")
                        
                        # Update the existing message with webhook data
                        existing_message.external_message_id = external_message_id  # Update with Gmail Message-ID
                        
                        # Merge metadata - keep existing but add webhook data
                        if not existing_message.metadata:
                            existing_message.metadata = {}
                        
                        # Store the raw webhook data
                        existing_message.metadata['raw_webhook_data'] = webhook_data
                        existing_message.metadata['webhook_processed'] = True
                        existing_message.metadata['gmail_message_id'] = external_message_id
                        
                        # Update attachments if present (important for sent messages)
                        if normalized_email.get('attachments'):
                            existing_message.metadata['attachments'] = normalized_email['attachments']
                            existing_message.metadata['has_attachments'] = True
                            existing_message.metadata['attachment_count'] = len(normalized_email['attachments'])
                            logger.info(f"Updated message {existing_message.id} with {len(normalized_email['attachments'])} attachments from webhook")
                        
                        # Update status if needed
                        if normalized_email.get('status'):
                            existing_message.status = normalized_email['status']
                        
                        # Update participant if we didn't have one
                        if not existing_message.sender_participant_id:
                            # Find sender participant
                            sender_info = normalized_email.get('sender_info', {})
                            sender_email = sender_info.get('email', '')
                            if sender_email:
                                for p in participants:
                                    if p.email and p.email.lower() == sender_email.lower():
                                        existing_message.sender_participant = p
                                        break
                        
                        # Update contact record if we found one
                        if not existing_message.contact_record_id:
                            # Determine contact based on direction
                            if normalized_email['direction'] == MessageDirection.OUTBOUND:
                                recipients = normalized_email.get('recipients', {}).get('to', [])
                                contact_email = recipients[0].get('email', '') if recipients else ''
                            else:
                                contact_email = sender_email
                            
                            if contact_email:
                                for p in participants:
                                    if p.email and p.email.lower() == contact_email.lower() and p.contact_record:
                                        existing_message.contact_record = p.contact_record
                                        break
                        
                        existing_message.save()
                        
                        logger.info(f"Updated existing message {existing_message.id} with webhook data")
                        response_data.update({
                            'message_id': str(existing_message.id),
                            'conversation_id': str(existing_message.conversation.id),
                            'note': 'Updated existing message with webhook data',
                            'was_created': False,
                            'stored': True,
                            'updated': True
                        })
                        return response_data
                
                # If not found by tracking_id, check by external_message_id
                if not existing_message and external_message_id:
                    existing_message = Message.objects.filter(
                        external_message_id=external_message_id
                    ).first()
                    
                    if existing_message:
                        logger.info(f"Email {external_message_id} already exists (ID: {existing_message.id}), skipping duplicate")
                        response_data.update({
                            'message_id': str(existing_message.id),
                            'conversation_id': str(existing_message.conversation.id),
                            'note': 'Email already exists, skipped duplicate',
                            'was_created': False,
                            'stored': True
                        })
                        return response_data
                
                # Get or create email conversation
                conversation = self._get_or_create_email_conversation(connection, normalized_email)
                
                # Create email message record with participant links
                # This is now a sync method, so we can call it directly
                message, was_created = self._create_email_message_with_participants(
                    connection, conversation, normalized_email, webhook_data, participants
                )
                
                # Link participants to records using ParticipantLinkManager
                try:
                    from communications.record_communications.services import RecordIdentifierExtractor
                    identifier_extractor = RecordIdentifierExtractor()
                    participants_linked = 0
                    
                    for participant in participants:
                        # If participant is not already linked to a record, try to find one by email
                        if not participant.contact_record and participant.email:
                            # Find records that have this email as an identifier
                            identifiers = {'email': [participant.email]}
                            matching_records = identifier_extractor.find_records_by_identifiers(identifiers)
                            if matching_records and len(matching_records) == 1:
                                # Use ParticipantLinkManager for consistent linking
                                if self.link_manager.link_participant_to_record(
                                    participant=participant,
                                    record=matching_records[0],
                                    confidence=0.95,
                                    method='email_webhook'
                                ):
                                    participants_linked += 1
                                    logger.info(f"Linked participant {participant.id} (email: {participant.email}) to record {matching_records[0].id}")
                        
                        # Also check for company records by domain (secondary record)
                        if participant.email and '@' in participant.email and not participant.secondary_record:
                            domain = participant.email.split('@')[1]
                            # Skip personal email domains
                            personal_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com']
                            if domain.lower() not in personal_domains:
                                company_records = identifier_extractor.find_company_records_by_domain(domain)
                                if company_records and len(company_records) == 1:
                                    # Found exactly one matching company
                                    participant.secondary_record = company_records[0]
                                    participant.secondary_pipeline = company_records[0].pipeline.slug
                                    participant.secondary_resolution_method = 'domain'
                                    participant.secondary_confidence = 0.8
                                    participant.save()
                                    participants_linked += 1
                                    logger.info(f"Linked participant {participant.id} to company record {company_records[0].id} via domain {domain}")
                    
                    if participants_linked > 0:
                        logger.info(f"Linked {participants_linked} participants to records (contacts + companies)")
                        
                except Exception as e:
                    logger.warning(f"Failed to link participants to records: {e}")
                
                if was_created:
                    logger.info(f"Created new email message {message.id} for account {account_id} with linked contact")
                    
                    # Trigger real-time updates
                    self._trigger_email_real_time_update(message, conversation, connection.user)
                    
                    # Trigger historical sync for any newly linked contacts
                    for participant in participants:
                        if participant.contact_record:
                            self._trigger_historical_sync_if_needed(participant.contact_record, normalized_email, connection)
                    
                    # Check if any participants need auto-creation
                    self._check_auto_creation_for_participants(participants)
                else:
                    logger.info(f"Email message {message.id} already existed")
                
                response_data.update({
                    'message_id': str(message.id),
                    'conversation_id': str(conversation.id),
                    'was_created': was_created,
                    'stored': True
                })
            else:
                # Not storing, but return metadata for frontend display
                logger.info(f"No contact found for email, not storing. {len(participants)} participants identified")
                response_data.update({
                    'stored': False,
                    'display_only': True,
                    'reason': 'no_contact_found'
                })
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error handling email received for account {account_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def _normalize_email_webhook(self, webhook_data: Dict[str, Any], connection: UserChannelConnection = None) -> Dict[str, Any]:
        """
        Normalize email webhook data using our email extractors
        
        Args:
            webhook_data: Raw webhook data
            connection: User channel connection for account email
            
        Returns:
            Dict with normalized email data
        """
        # Use our email extraction utilities
        # Get the connected account's email for proper direction detection
        account_email = connection.user.email if connection and connection.user else None
        
        contact_email = extract_email_from_webhook(webhook_data, account_email or '')
        contact_name = extract_email_name_from_webhook(webhook_data, account_email or '')
        subject = extract_email_subject_from_webhook(webhook_data)
        direction = determine_email_direction(webhook_data, account_email)
        thread_id = extract_email_thread_id(webhook_data)
        message_id = extract_email_message_id(webhook_data)
        attachments = extract_email_attachments(webhook_data)
        folder_labels = extract_email_folder_labels(webhook_data)
        recipients_info = extract_email_recipients_info(webhook_data)
        sender_info = extract_email_sender_info(webhook_data)
        
        # Extract email content (handle both HTML and text)
        email_content = webhook_data.get('body', '')
        content = ''
        html_content = ''
        
        if isinstance(email_content, dict):
            # UniPile format: {"text": "...", "html": "..."}
            content = email_content.get('text', '')
            html_content = email_content.get('html', '')
            # If no plain text, use HTML as fallback
            if not content and html_content:
                # Strip HTML tags for plain text version
                import re
                content = re.sub('<[^<]+?>', '', html_content)
        else:
            # Simple string format - check if it's HTML
            content_str = str(email_content)
            if '<html' in content_str.lower() or '<body' in content_str.lower():
                html_content = content_str
                # Strip HTML tags for plain text version
                import re
                content = re.sub('<[^<]+?>', '', content_str)
            else:
                content = content_str
        
        # Create display name
        display_name = get_display_name_or_email(contact_name, contact_email)
        
        # Determine message status based on folder/labels
        status = MessageStatus.DELIVERED
        if folder_labels['read']:
            status = MessageStatus.READ
        elif direction == MessageDirection.OUTBOUND:
            status = MessageStatus.SENT
        
        # Parse timestamp
        timestamp = webhook_data.get('date')
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    # Parse ISO format: "2025-08-19T04:15:22.000Z"
                    parsed_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    parsed_time = timestamp
            except (ValueError, AttributeError):
                parsed_time = timezone.now()
        else:
            parsed_time = timezone.now()
        
        return {
            'contact_email': contact_email,
            'contact_name': contact_name,
            'display_name': display_name,
            'subject': subject,
            'content': content,
            'html_content': html_content,  # Add HTML content
            'direction': direction,
            'thread_id': thread_id,
            'message_id': message_id,
            'status': status,
            'attachments': attachments,
            'folder': folder_labels['folder'],
            'labels': folder_labels['labels'],
            'read': folder_labels['read'],
            'recipients': recipients_info,
            'sender_info': sender_info,
            'timestamp': parsed_time,
            'raw_webhook_data': webhook_data
        }
    
    def _get_or_create_email_conversation(self, connection: UserChannelConnection, 
                                        normalized_email: Dict[str, Any]) -> Conversation:
        """
        Get or create email conversation using thread ID
        Email conversations are grouped by thread_id (email threading)
        """
        thread_id = normalized_email['thread_id']
        
        # Try to find existing conversation by thread ID
        if thread_id:
            conversation = Conversation.objects.filter(
                external_thread_id=thread_id,
                channel__unipile_account_id=connection.unipile_account_id
            ).first()
            if conversation:
                return conversation
        
        # Create new email conversation
        channel, _ = Channel.objects.get_or_create(
            unipile_account_id=connection.unipile_account_id,
            channel_type=connection.channel_type,
            defaults={
                'name': f"Gmail - {connection.account_name}",
                'auth_status': connection.auth_status,
                'created_by': connection.user
            }
        )
        
        # Create meaningful subject for conversation
        email_subject = normalized_email['subject']
        display_name = normalized_email['display_name']
        
        if email_subject:
            conversation_subject = f"{email_subject}"
        elif display_name:
            conversation_subject = f"{display_name}"
        else:
            conversation_subject = "Email conversation"
        
        conversation = Conversation.objects.create(
            channel=channel,
            external_thread_id=thread_id or f"email_{normalized_email['message_id']}",
            subject=conversation_subject,
            status='active',
            metadata={
                'email_thread': True,
                'original_subject': email_subject,
                'participants': [normalized_email['contact_email']] if normalized_email['contact_email'] else []
            }
        )
        
        logger.info(f"Created email conversation {conversation.id} with thread ID {thread_id}")
        return conversation
    
    def _create_email_message_with_participants(self, connection: UserChannelConnection, 
                                   conversation: Conversation, normalized_email: Dict[str, Any],
                                   raw_webhook_data: Dict[str, Any], participants: List[Participant]) -> tuple[Message, bool]:
        """
        Create email message record with full email metadata and optional linked contact
        """
        with transaction.atomic():
            # Check for existing message (prevent duplicates)
            existing_message = Message.objects.select_for_update().filter(
                external_message_id=normalized_email['message_id'],
                conversation=conversation
            ).first()
            
            if existing_message:
                # Update existing message with webhook data (especially attachments)
                # This is important for sent messages that need attachment IDs from webhook
                if existing_message.metadata:
                    # Check if this message has pending attachments
                    existing_attachments = existing_message.metadata.get('attachments', [])
                    has_pending = any(att.get('pending', False) for att in existing_attachments)
                    
                    if has_pending and normalized_email.get('attachments'):
                        # Update with real attachment data from webhook
                        existing_message.metadata['attachments'] = normalized_email['attachments']
                        existing_message.metadata['has_attachments'] = len(normalized_email['attachments']) > 0
                        existing_message.metadata['attachment_count'] = len(normalized_email['attachments'])
                        existing_message.save(update_fields=['metadata'])
                        logger.info(f"Updated message {existing_message.id} with {len(normalized_email['attachments'])} attachments from webhook")
                
                return existing_message, False
            
            # Prepare email-specific metadata
            # Format sender info for frontend compatibility
            sender_info = normalized_email.get('sender_info', {})
            from_field = {
                'email': sender_info.get('email', ''),
                'name': sender_info.get('name', '')
            }
            
            # Format recipients for frontend compatibility
            recipients = normalized_email.get('recipients', {})
            to_field = [{'email': r.get('email', ''), 'name': r.get('name', '')} 
                       for r in recipients.get('to', [])]
            cc_field = [{'email': r.get('email', ''), 'name': r.get('name', '')} 
                       for r in recipients.get('cc', [])]
            
            email_metadata = {
                'raw_webhook_data': raw_webhook_data,
                'email_specific': True,
                'folder': normalized_email['folder'],
                'labels': normalized_email['labels'],
                'read_status': normalized_email['read'],
                'read_date': normalized_email.get('read_date'),  # Store when email was read
                'recipients': normalized_email['recipients'],  # Keep original for backend
                'sender_info': normalized_email['sender_info'],  # Keep original for backend
                'from': from_field,  # Add frontend-compatible field
                'to': to_field,  # Add frontend-compatible field
                'cc': cc_field,  # Add frontend-compatible field
                'attachment_count': len(normalized_email['attachments']),
                'has_attachments': len(normalized_email['attachments']) > 0,
                'processed_at': timezone.now().isoformat(),
                'processing_version': 'email_v1.0',
                
                # Store UniPile IDs for reply threading
                'unipile_id': raw_webhook_data.get('email_id'),  # UniPile message ID for reply_to
                'provider_id': raw_webhook_data.get('provider_id'),  # Provider-specific ID
                'gmail_message_id': raw_webhook_data.get('message_id'),  # Gmail Message-ID
                'tracking_id': raw_webhook_data.get('tracking_id'),  # Tracking ID for sent messages
            }
            
            # Add HTML content if present
            if normalized_email.get('html_content'):
                email_metadata['html_content'] = normalized_email['html_content']
            
            # Add attachment details
            if normalized_email['attachments']:
                email_metadata['attachments'] = normalized_email['attachments']
            
            # Find sender participant using sender_info, NOT contact_email
            sender_participant = None
            sender_info = normalized_email.get('sender_info', {})
            sender_email = sender_info.get('email', '')
            
            # For proper participant matching, use the actual sender's email
            if sender_email:
                for p in participants:
                    if p.email and p.email.lower() == sender_email.lower():
                        sender_participant = p
                        break
            
            # Log for debugging
            logger.info(f"Sender email from sender_info: {sender_email}, Found participant: {sender_participant is not None}")
            
            # Determine contact_email and contact_record based on direction
            # For INBOUND: contact is the sender
            # For OUTBOUND: contact is the primary recipient
            contact_participant = None
            if normalized_email['direction'] == MessageDirection.INBOUND:
                contact_email_for_message = sender_email
                contact_participant = sender_participant
            else:
                # For outbound, get the first recipient
                recipients = normalized_email.get('recipients', {}).get('to', [])
                contact_email_for_message = recipients[0].get('email', '') if recipients else ''
                
                # Find the recipient participant
                if contact_email_for_message:
                    for p in participants:
                        if p.email and p.email.lower() == contact_email_for_message.lower():
                            contact_participant = p
                            break
            
            # Create email message with participant link
            message = Message.objects.create(
                channel=conversation.channel,
                conversation=conversation,
                external_message_id=normalized_email['message_id'],
                direction=normalized_email['direction'],
                content=normalized_email['content'],
                subject=normalized_email['subject'],
                contact_email=contact_email_for_message,  # Use correct email based on direction
                contact_phone='',  # Emails don't have phone numbers
                sender_participant=sender_participant,  # Link to sender participant
                contact_record=contact_participant.contact_record if contact_participant else None,  # Link contact record for timeline
                status=normalized_email['status'],
                metadata=email_metadata,
                sent_at=normalized_email['timestamp'] if normalized_email['direction'] == MessageDirection.OUTBOUND else None,
                received_at=normalized_email['timestamp'] if normalized_email['direction'] == MessageDirection.INBOUND else None
            )
            
            # Update conversation's unread_count if this is an inbound unread message
            if (normalized_email['direction'] == MessageDirection.INBOUND and 
                normalized_email['status'] != MessageStatus.READ):
                # Calculate the new unread count for the conversation
                unread_count = conversation.messages.filter(
                    direction=MessageDirection.INBOUND,
                    status__in=[MessageStatus.DELIVERED, MessageStatus.SENT, MessageStatus.PENDING]
                ).exclude(status=MessageStatus.READ).count()
                
                # Update the conversation's unread_count field
                conversation.unread_count = unread_count
                conversation.last_message_at = message.created_at
                conversation.save(update_fields=['unread_count', 'last_message_at'])
                logger.info(f"Updated conversation {conversation.id} unread_count to {unread_count}")
            
            # Link all participants to the conversation
            for participant in participants:
                # Determine role based on email position
                role = 'member'
                if participant.email and participant.email.lower() == sender_email.lower():
                    role = 'sender'
                elif participant.email and participant.email.lower() in [r.get('email', '').lower() for r in normalized_email.get('recipients', {}).get('to', [])]:
                    role = 'recipient'
                elif participant.email and participant.email.lower() in [r.get('email', '').lower() for r in normalized_email.get('recipients', {}).get('cc', [])]:
                    role = 'cc'
                elif participant.email and participant.email.lower() in [r.get('email', '').lower() for r in normalized_email.get('recipients', {}).get('bcc', [])]:
                    role = 'bcc'
                
                ConversationParticipant.objects.update_or_create(
                    conversation=conversation,
                    participant=participant,
                    defaults={
                        'role': role,
                        'is_active': True,
                        'message_count': 1 if participant == sender_participant else 0,
                        'last_message_at': normalized_email['timestamp'] if participant == sender_participant else None
                    }
                )
            
            # Log with correct direction and sender info
            direction_str = "outbound" if normalized_email['direction'] == MessageDirection.OUTBOUND else "inbound"
            logger.info(f"Created email message {message.id}: {direction_str} "
                       f"from {sender_email} "
                       f"subject: {normalized_email['subject'][:50]}")
            
            return message, True
    
    def _attempt_email_contact_resolution(self, message: Message, normalized_email: Dict[str, Any]):
        """
        Attempt to resolve email contact using email address and name
        """
        try:
            # Import here to avoid circular imports
            from communications.resolvers.contact_identifier import ContactIdentifier
            
            contact_identifier = ContactIdentifier(tenant_id=1)  # TODO: Get actual tenant ID
            
            # Prepare contact data for email resolution
            contact_data = {
                'email': normalized_email['contact_email'],
                'name': normalized_email['contact_name'],
                'channel_type': 'email'
            }
            
            # Filter out empty values
            contact_data = {k: v for k, v in contact_data.items() if v}
            
            if contact_data:
                contact_record = contact_identifier.identify_contact(contact_data)
                
                if contact_record:
                    # Link message to contact
                    message.contact_record = contact_record
                    message.save(update_fields=['contact_record'])
                    
                    # Update conversation if needed
                    if not message.conversation.primary_contact_record:
                        message.conversation.primary_contact_record = contact_record
                        message.conversation.save(update_fields=['primary_contact_record'])
                    
                    # Update metadata
                    if not message.metadata:
                        message.metadata = {}
                    message.metadata['email_contact_resolved'] = True
                    message.metadata['contact_record_id'] = contact_record.id
                    message.save(update_fields=['metadata'])
                    
                    logger.info(f"Auto-resolved email message {message.id} to contact {contact_record.id}")
                else:
                    logger.debug(f"No matching contact found for email {normalized_email['contact_email']}")
            
        except Exception as e:
            logger.warning(f"Error in email contact resolution for message {message.id}: {e}")
    
    def _trigger_email_real_time_update(self, message: Message, conversation: Conversation, user):
        """
        Trigger real-time updates for email messages in unified inbox
        """
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.debug("No channel layer available for email broadcasting")
                return
            
            # Prepare email message data for frontend
            message_data = {
                'type': 'message_update',
                'message': {
                    'id': str(message.id),
                    'type': 'email',  # Important: email type for proper frontend handling
                    'subject': message.subject,  # Email-specific: subject line
                    'content': message.content,
                    'direction': message.direction,
                    'contact_email': message.contact_email,
                    'sender': {
                        'name': message.metadata.get('sender_info', {}).get('name', 'Unknown') if message.metadata else 'Unknown',
                        'email': message.contact_email,
                        'avatar': None  # TODO: Email avatars/Gravatar
                    },
                    'recipient': {
                        'name': user.get_full_name() or user.username if user else 'Business',
                        'email': user.email if user else ''
                    },
                    'timestamp': message.created_at.isoformat(),
                    'is_read': message.metadata.get('read_status', False) if message.metadata else False,
                    'is_starred': False,  # TODO: Email starring
                    'conversation_id': str(conversation.id),
                    'account_id': conversation.channel.unipile_account_id,
                    'external_id': message.external_message_id,
                    'metadata': {
                        'email_thread_id': conversation.external_thread_id,
                        'folder': message.metadata.get('folder', '') if message.metadata else '',
                        'labels': message.metadata.get('labels', []) if message.metadata else [],
                        'recipients': message.metadata.get('recipients', {}) if message.metadata else {},
                        'attachment_count': message.metadata.get('attachment_count', 0) if message.metadata else 0
                    },
                    'channel': {
                        'name': conversation.channel.name,
                        'channel_type': 'email'
                    },
                    'attachments': message.metadata.get('attachments', []) if message.metadata else []
                }
            }
            
            # Broadcast to conversation room
            room_name = f"conversation_{conversation.id}"
            async_to_sync(channel_layer.group_send)(room_name, message_data)
            
            # Broadcast to inbox for conversation list updates
            inbox_room = f"channel_{conversation.channel.id}"
            async_to_sync(channel_layer.group_send)(inbox_room, {
                'type': 'new_conversation',
                'conversation': {
                    'id': str(conversation.id),
                    'last_message': message_data['message'],
                    'unread_count': conversation.messages.filter(
                        direction=MessageDirection.INBOUND,
                        status__in=[MessageStatus.DELIVERED, MessageStatus.SENT]
                    ).exclude(status=MessageStatus.READ).count(),
                    'type': 'email',
                    'created_at': conversation.created_at.isoformat(),
                    'updated_at': timezone.now().isoformat(),
                    'participants': [{
                        'name': message.metadata.get('sender_info', {}).get('name', 'Unknown') if message.metadata else 'Unknown',
                        'email': message.contact_email,
                        'platform': 'email'
                    }] if message.contact_email else []
                }
            })
            
            logger.info(f"Broadcasted real-time email message to rooms: {room_name}, {inbox_room}")
            
        except Exception as e:
            logger.warning(f"Failed to broadcast real-time email message: {e}")
    
    def handle_email_sent(self, account_id: str, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle outbound email webhook - create the message if it doesn't exist
        Similar to handle_email_received but for outbound emails
        """
        try:
            external_message_id = webhook_data.get('message_id') or webhook_data.get('id')
            
            # First check if message already exists
            if external_message_id:
                existing_message = Message.objects.filter(
                    external_message_id=external_message_id
                ).first()
                
                if existing_message:
                    # Just update the status if message already exists
                    existing_message.status = MessageStatus.SENT
                    existing_message.sent_at = timezone.now()
                    existing_message.save(update_fields=['status', 'sent_at'])
                    
                    logger.info(f"Updated existing email message {existing_message.id} status to sent")
                    return {'success': True, 'message_id': str(existing_message.id), 'action': 'updated'}
            
            # Message doesn't exist, create it like we do for received emails
            # This handles outbound emails that we're notified about via webhook
            logger.info(f"Creating new outbound email message from mail_sent webhook")
            
            # Use the same logic as handle_email_received but we know it's outbound
            return self.handle_email_received(account_id, webhook_data)
            
        except Exception as e:
            logger.error(f"Error handling email sent for account {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_email_delivered(self, account_id: str, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle email delivery confirmation webhook
        """
        try:
            external_message_id = webhook_data.get('message_id') or webhook_data.get('id')
            
            if external_message_id:
                message = Message.objects.filter(
                    external_message_id=external_message_id
                ).first()
                
                if message:
                    message.status = MessageStatus.DELIVERED
                    message.save(update_fields=['status'])
                    
                    logger.info(f"Updated email message {message.id} status to delivered")
                    return {'success': True, 'message_id': str(message.id)}
            
            logger.warning(f"No email message record found for external ID {external_message_id}")
            return {'success': True, 'note': 'No local email message record to update'}
            
        except Exception as e:
            logger.error(f"Error handling email delivered for account {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_email_read(self, account_id: str, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle email read receipt webhook - fired when an email is marked as read
        """
        try:
            # Get message ID from webhook - could be email_id or message_id
            external_message_id = webhook_data.get('email_id') or webhook_data.get('message_id') or webhook_data.get('id')
            read_date = webhook_data.get('read_date')
            
            if external_message_id:
                # Try to find message by external_message_id or by metadata unipile_id
                message = Message.objects.filter(
                    models.Q(external_message_id=external_message_id) |
                    models.Q(metadata__unipile_id=external_message_id)
                ).first()
                
                if message:
                    # Update status to READ
                    message.status = MessageStatus.READ
                    
                    # Update metadata with read information
                    if message.metadata:
                        message.metadata['read_status'] = True
                        message.metadata['read_date'] = read_date
                    else:
                        message.metadata = {
                            'read_status': True,
                            'read_date': read_date
                        }
                    
                    message.save(update_fields=['status', 'metadata'])
                    
                    # Update conversation's unread_count when marking as read
                    if message.conversation:
                        unread_count = message.conversation.messages.filter(
                            direction=MessageDirection.INBOUND,
                            status__in=[MessageStatus.DELIVERED, MessageStatus.SENT, MessageStatus.PENDING]
                        ).exclude(status=MessageStatus.READ).count()
                        
                        message.conversation.unread_count = unread_count
                        message.conversation.save(update_fields=['unread_count'])
                        logger.info(f"Updated conversation {message.conversation.id} unread_count to {unread_count} after marking message as read")
                    
                    # Log based on direction
                    if message.direction == MessageDirection.OUTBOUND:
                        logger.info(f"Updated outbound email {message.id} - recipient read at {read_date}")
                    else:
                        logger.info(f"Updated inbound email {message.id} - marked as read at {read_date}")
                    
                    return {'success': True, 'message_id': str(message.id), 'read_date': read_date}
            
            logger.warning(f"No email message record found for external ID {external_message_id}")
            return {'success': True, 'note': 'No local email message record to update'}
            
        except Exception as e:
            logger.error(f"Error handling email read for account {account_id}: {e}")
            return {'success': False, 'error': str(e)}


    def _check_participant_resolution(self, normalized_email: Dict[str, Any], connection: UserChannelConnection) -> Tuple[bool, List[Participant]]:
        """
        Check all email participants and determine if we should store
        
        Returns:
            Tuple of (should_store, list of resolved participants)
        """
        try:
            from asgiref.sync import async_to_sync
            
            # Get tenant from current schema context
            # In webhook context, we're already in the correct tenant schema
            # from the routing layer, so we can get the current tenant
            from django.db import connection as db_connection
            tenant = getattr(db_connection, 'tenant', None)
            
            # If still no tenant, try to get from the user's tenant
            if not tenant and hasattr(connection, 'user') and hasattr(connection.user, 'tenant'):
                tenant = connection.user.tenant
            
            # Initialize storage decider with tenant
            storage_decider = ConversationStorageDecider(tenant)
            
            # Build conversation data from normalized email
            # Extract recipients and transform to expected format
            recipients = normalized_email.get('recipients', {})
            
            # Transform recipients to have identifier/display_name format
            def transform_recipient(recipient):
                """Transform recipient from email/name to identifier/display_name format"""
                if not recipient:
                    return recipient
                return {
                    'identifier': recipient.get('email', ''),
                    'display_name': recipient.get('name', '')
                }
            
            to_attendees = [transform_recipient(r) for r in recipients.get('to', [])]
            cc_attendees = [transform_recipient(r) for r in recipients.get('cc', [])]
            bcc_attendees = [transform_recipient(r) for r in recipients.get('bcc', [])]
            
            # Log for debugging
            logger.info(f"Building conversation data - Direction: {normalized_email.get('direction')}")
            logger.info(f"  Sender: {normalized_email.get('sender_info', {}).get('email')}")
            logger.info(f"  TO recipients: {[r.get('identifier') for r in to_attendees]}")
            logger.info(f"  CC recipients: {[r.get('identifier') for r in cc_attendees]}")
            
            conversation_data = {
                'from_attendee': {
                    'identifier': normalized_email.get('sender_info', {}).get('email') or normalized_email.get('contact_email'),
                    'display_name': normalized_email.get('sender_info', {}).get('name') or normalized_email.get('contact_name')
                },
                'to_attendees': to_attendees,
                'cc_attendees': cc_attendees,
                'bcc_attendees': bcc_attendees
            }
            
            # Use storage decider to check all participants
            # The method is async, so we need to use async_to_sync
            # In Daphne ASGI, we need to ensure we're not in an event loop
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            try:
                # Check if there's a running event loop
                asyncio.get_running_loop()
                # There is a running loop - we need to run in a thread to avoid conflict
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        async_to_sync(storage_decider.should_store_conversation),
                        conversation_data,
                        connection.channel_type
                    )
                    should_store, participants = future.result(timeout=5)
            except RuntimeError:
                # No running loop, we can call async_to_sync directly
                should_store, participants = async_to_sync(storage_decider.should_store_conversation)(
                    conversation_data,
                    connection.channel_type
                )
            
            # IMPORTANT: The storage decider only checks if participants have contact_record already set,
            # which causes a chicken-and-egg problem. We need to also search for records by email.
            # We also need to check for secondary (company) records even if contact records are found.
            # Always enhance participant resolution with additional searches
            if participants:
                from communications.record_communications.services import RecordIdentifierExtractor
                identifier_extractor = RecordIdentifierExtractor()
                
                # Check each participant's email against CRM records
                for participant in participants:
                    if participant.email:
                        # Search for contact records by email (if not already linked)
                        if not participant.contact_record:
                            identifiers = {'email': [participant.email]}
                            matching_records = identifier_extractor.find_records_by_identifiers(identifiers)
                            
                            if matching_records:
                                # Found a matching record! We should store this message
                                should_store = True
                                # Link the participant to the record
                                participant.contact_record = matching_records[0]
                                participant.save()
                                logger.info(f"Found CRM record {matching_records[0].id} for email {participant.email}")
                        
                        # Always search for company records by domain (even if contact exists)
                        if '@' in participant.email and not participant.secondary_record:
                            domain = participant.email.split('@')[1]
                            # Skip personal email domains
                            personal_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com']
                            if domain.lower() not in personal_domains:
                                company_records = identifier_extractor.find_company_records_by_domain(domain)
                                if company_records:
                                    # Found a matching company! Link as secondary record
                                    participant.secondary_record = company_records[0]
                                    participant.secondary_pipeline = company_records[0].pipeline.slug
                                    participant.secondary_resolution_method = 'domain'
                                    participant.secondary_confidence = 0.8
                                    participant.save()
                                    logger.info(f"Found company record {company_records[0].id} for domain {domain}")
                                    should_store = True  # Company match is also enough to store
            
            return should_store, participants
            
        except Exception as e:
            logger.error(f"Error checking participant resolution: {e}")
            # On error, default to not storing
            return False, []
    
    def _trigger_historical_sync_if_needed(self, contact_record: Any, normalized_email: Dict[str, Any], connection: UserChannelConnection):
        """
        Trigger historical sync for a newly linked contact
        Only triggers if this is the first communication with this contact
        """
        try:
            # Check if we already have messages for this contact via participants
            from communications.models import ConversationParticipant
            existing_conversations = ConversationParticipant.objects.filter(
                participant__contact_record=contact_record
            ).count()
            
            if existing_conversations <= 1:  # This is the first or second conversation
                logger.info(f"First communication with contact {contact_record.id}, triggering historical sync")
                
                # Import here to avoid circular dependency
                from communications.tasks import sync_contact_history
                
                # Trigger async task to sync historical communications
                sync_contact_history.delay(
                    contact_record_id=str(contact_record.id),
                    account_id=connection.unipile_account_id,
                    identifiers={
                        'email': normalized_email.get('contact_email'),
                        'name': normalized_email.get('contact_name')
                    }
                )
            else:
                logger.debug(f"Contact {contact_record.id} already has {existing_conversations} conversations, skipping historical sync")
                
        except Exception as e:
            logger.error(f"Error triggering historical sync: {e}")
            # Don't fail the main process if historical sync fails
    
    def _check_auto_creation_for_participants(self, participants: List[Participant]):
        """
        Check if any participants should trigger auto-creation after message processing
        
        Args:
            participants: List of participants to check
        """
        try:
            from communications.models import ParticipantSettings
            from communications.services.auto_create_service import AutoCreateContactService
            
            # Get settings for current tenant
            settings = ParticipantSettings.get_or_create_for_tenant()
            
            # Skip if auto-creation is disabled or not real-time
            if not settings.auto_create_enabled or not settings.enable_real_time_creation:
                return
            
            # Create service
            service = AutoCreateContactService()
            
            # Check each participant
            for participant in participants:
                # Skip if already has contact
                if participant.contact_record:
                    continue
                
                # Check if eligible for auto-creation
                should_create, reason = service.should_auto_create(participant)
                
                if should_create:
                    logger.info(f"Webhook triggered auto-creation for participant {participant.id}: {reason}")
                    try:
                        record = service.create_contact_from_participant(
                            participant=participant,
                            user=None,  # System-created
                            force=False
                        )
                        logger.info(f"Successfully created contact {record.id} for participant {participant.id} via webhook")
                    except Exception as e:
                        logger.error(f"Failed to auto-create contact in webhook handler: {e}")
                        
        except Exception as e:
            logger.error(f"Error checking auto-creation in webhook handler: {e}")


# Global email handler instance
email_webhook_handler = EmailWebhookHandler()