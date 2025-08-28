"""
Email Message Synchronization
Syncs individual email messages with proper status mapping
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from asgiref.sync import async_to_sync

from communications.models import Message, Conversation, MessageStatus, MessageDirection
from communications.utils.message_direction import determine_email_direction
from ..service import EmailService
from .config import EMAIL_SYNC_CONFIG

logger = logging.getLogger(__name__)


class EmailMessageSyncService:
    """Service for syncing email messages"""
    
    def __init__(
        self,
        channel: Any,
        connection: Optional[Any] = None,
        progress_tracker: Optional[Any] = None
    ):
        self.channel = channel
        self.connection = connection
        self.progress_tracker = progress_tracker
        self.service = EmailService(channel=channel)
        self.messages_synced = 0
        self.messages_created = 0
        self.messages_updated = 0
    
    def sync_messages_for_thread(
        self,
        conversation: Conversation,
        thread_id: str,
        max_messages: int = 50,
        since_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Sync messages for a specific email thread
        
        Args:
            conversation: Conversation object for this thread
            thread_id: Email thread ID
            max_messages: Maximum messages to sync
            since_date: Only sync messages after this date
            
        Returns:
            Sync statistics
        """
        stats = {
            'messages_synced': 0,
            'messages_created': 0,
            'messages_updated': 0,
            'errors': []
        }
        
        try:
            # Get account ID
            account_id = self.connection.unipile_account_id if self.connection else None
            if not account_id:
                raise ValueError("No account ID available for sync")
            
            # Get user's email for direction determination
            user_email = self._get_user_email()
            
            # Fetch messages for this thread
            after = since_date.isoformat() if since_date else None
            
            result = async_to_sync(self.service.get_emails)(
                account_id=account_id,
                thread_id=thread_id,
                limit=max_messages,
                meta_only=False,  # Get full content
                after=after
            )
            
            if not result.get('success'):
                error_msg = f"Failed to fetch thread messages: {result.get('error')}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
                return stats
            
            emails = result.get('emails', [])
            
            # Process each email
            for email_data in emails:
                try:
                    self._process_email_message(email_data, conversation, user_email)
                    stats['messages_synced'] += 1
                    
                    # Update progress
                    if self.progress_tracker:
                        self.progress_tracker.increment_stat('messages_synced', 1)
                    
                except Exception as e:
                    error_msg = f"Failed to process message {email_data.get('id')}: {e}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
            
            stats['messages_created'] = self.messages_created
            stats['messages_updated'] = self.messages_updated
            
        except Exception as e:
            error_msg = f"Message sync failed for thread {thread_id}: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
        
        return stats
    
    def _process_email_message(
        self,
        email_data: Dict[str, Any],
        conversation: Conversation,
        user_email: Optional[str] = None
    ) -> None:
        """
        Process a single email message
        
        Args:
            email_data: Email data from UniPile
            conversation: Associated conversation
            user_email: User's email for direction determination
        """
        # Extract message ID
        message_id = email_data.get('id')
        provider_id = email_data.get('provider_id') or email_data.get('message_id')
        
        if not message_id:
            logger.warning("Email without ID, skipping")
            return
        
        # Determine message direction using unified utility
        direction_str = determine_email_direction(email_data, user_email)
        direction = MessageDirection.OUTBOUND if direction_str == 'out' else MessageDirection.INBOUND
        
        # Map message status
        status = self._map_email_status(email_data, direction)
        
        # Extract content
        content = email_data.get('body', '') or email_data.get('body_plain', '')
        subject = email_data.get('subject', '')
        
        # Extract sender info
        from_attendee = email_data.get('from_attendee', {})
        sender_email = from_attendee.get('identifier', '') if isinstance(from_attendee, dict) else ''
        sender_name = from_attendee.get('display_name', '') if isinstance(from_attendee, dict) else ''
        
        # Parse timestamp
        timestamp = self._parse_date(email_data.get('date'))
        
        # Extract attachments
        attachments = self._process_attachments(email_data.get('attachments', []))
        
        # Create or update message
        with transaction.atomic():
            message, created = Message.objects.update_or_create(
                conversation=conversation,
                external_message_id=message_id,
                defaults={
                    'content': content,
                    'sender_identifier': sender_email,
                    'sender_name': sender_name or sender_email,
                    'timestamp': timestamp,
                    'direction': direction,
                    'status': status,
                    'metadata': {
                        'subject': subject,
                        'provider_id': provider_id,
                        'thread_id': email_data.get('thread_id'),
                        'folders': email_data.get('folders', []),
                        'role': email_data.get('role'),
                        'has_attachments': email_data.get('has_attachments', False),
                        'to_attendees': email_data.get('to_attendees', []),
                        'cc_attendees': email_data.get('cc_attendees', []),
                        'bcc_attendees': email_data.get('bcc_attendees', []),
                        'in_reply_to': email_data.get('in_reply_to'),
                        'headers': email_data.get('headers', []) if email_data.get('headers') else []
                    },
                    'attachments': attachments
                }
            )
            
            if created:
                self.messages_created += 1
                logger.debug(f"Created email message: {subject[:50] if subject else message_id}")
            else:
                self.messages_updated += 1
                logger.debug(f"Updated email message: {subject[:50] if subject else message_id}")
    
    def _map_email_status(self, email_data: Dict[str, Any], direction: str) -> str:
        """
        Map email status based on read_date and direction
        
        Args:
            email_data: Email data from API
            direction: Message direction (INBOUND/OUTBOUND)
            
        Returns:
            MessageStatus value
        """
        # Check if email has been read (has read_date)
        read_date = email_data.get('read_date')
        if read_date:
            return MessageStatus.READ
        
        # Check folder role for sent emails
        role = email_data.get('role', '').lower()
        if role == 'sent' or direction == MessageDirection.OUTBOUND:
            return MessageStatus.SENT
        
        # For historical synced emails without explicit read status,
        # mark as READ to avoid flooding with unread notifications
        if EMAIL_SYNC_CONFIG.get('auto_mark_read_historical', True):
            # Check if this is a historical email (older than 1 day)
            email_date = self._parse_date(email_data.get('date'))
            if email_date and (timezone.now() - email_date).days > 1:
                return MessageStatus.READ
        
        # Default to DELIVERED for inbound emails
        if direction == MessageDirection.INBOUND:
            return MessageStatus.DELIVERED
        
        # Default to SENT for outbound
        return MessageStatus.SENT
    
    def _process_attachments(self, attachments_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process email attachments
        
        Args:
            attachments_data: List of attachment data from API
            
        Returns:
            Processed attachments list
        """
        processed = []
        
        for attachment in attachments_data:
            if isinstance(attachment, dict):
                processed.append({
                    'id': attachment.get('id'),
                    'name': attachment.get('name'),
                    'size': attachment.get('size', 0),
                    'mime_type': attachment.get('mime'),
                    'extension': attachment.get('extension'),
                    'cid': attachment.get('cid')  # Content ID for inline images
                })
        
        return processed
    
    def _get_user_email(self) -> Optional[str]:
        """
        Get the user's email address for direction determination
        
        Returns:
            User's email address or None
        """
        # Try from service
        email = self.service.get_account_email()
        if email:
            return email
        
        # Try from connection
        if self.connection and self.connection.account_name:
            # Account name often contains email
            if '@' in self.connection.account_name:
                return self.connection.account_name
        
        # Try from channel configuration
        if self.channel and self.channel.connection_config:
            return self.channel.connection_config.get('email_address')
        
        return None
    
    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse ISO date string to datetime
        
        Args:
            date_str: ISO format date string
            
        Returns:
            Parsed datetime or now
        """
        if not date_str:
            return timezone.now()
        
        try:
            # Remove microseconds if present for compatibility
            if '.' in date_str:
                date_str = date_str.split('.')[0] + 'Z'
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse date: {date_str}")
            return timezone.now()
    
    def sync_all_messages(
        self,
        folder: str = 'inbox',
        max_messages: int = 250,
        since_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Sync all messages from a folder (not thread-grouped)
        
        Args:
            folder: Folder to sync from
            max_messages: Maximum messages to sync
            since_date: Only sync messages after this date
            
        Returns:
            Sync statistics
        """
        stats = {
            'messages_synced': 0,
            'messages_created': 0,
            'messages_updated': 0,
            'errors': []
        }
        
        try:
            # Get account ID
            account_id = self.connection.unipile_account_id if self.connection else None
            if not account_id:
                raise ValueError("No account ID available for sync")
            
            # Get user's email
            user_email = self._get_user_email()
            
            # Fetch messages
            after = since_date.isoformat() if since_date else None
            
            result = async_to_sync(self.service.get_emails)(
                account_id=account_id,
                folder=folder,
                limit=max_messages,
                meta_only=False,
                after=after
            )
            
            if not result.get('success'):
                error_msg = f"Failed to fetch emails: {result.get('error')}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
                return stats
            
            emails = result.get('emails', [])
            
            # Process each email
            for email_data in emails:
                try:
                    # Find or create conversation for this email
                    thread_id = email_data.get('thread_id') or email_data.get('id')
                    conversation = self._get_or_create_conversation(email_data, thread_id)
                    
                    # Process the message
                    self._process_email_message(email_data, conversation, user_email)
                    stats['messages_synced'] += 1
                    
                    # Update progress
                    if self.progress_tracker:
                        self.progress_tracker.increment_stat('messages_synced', 1)
                    
                except Exception as e:
                    error_msg = f"Failed to process message: {e}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
            
            stats['messages_created'] = self.messages_created
            stats['messages_updated'] = self.messages_updated
            
        except Exception as e:
            error_msg = f"Message sync failed: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
        
        return stats
    
    def _get_or_create_conversation(self, email_data: Dict[str, Any], thread_id: str) -> Conversation:
        """
        Get or create conversation for an email
        
        Args:
            email_data: Email data
            thread_id: Thread identifier
            
        Returns:
            Conversation object
        """
        subject = email_data.get('subject', 'No Subject')
        timestamp = self._parse_date(email_data.get('date'))
        
        conversation, created = Conversation.objects.get_or_create(
            channel=self.channel,
            external_thread_id=thread_id,
            defaults={
                'subject': subject[:255] if subject else 'No Subject',
                'last_message_at': timestamp,
                'created_at': timestamp,
                'metadata': {
                    'thread_id': thread_id,
                    'folder': email_data.get('role', 'inbox')
                }
            }
        )
        
        return conversation