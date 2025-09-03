"""
Data Transformer - Transforms UniPile API data to our internal models

Handles the conversion of UniPile response data to our Django model format.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone
import hashlib
import json

from ..utils import ProviderIdBuilder

logger = logging.getLogger(__name__)


class DataTransformer:
    """Transforms UniPile data to internal model format"""
    
    def transform_email_thread(
        self,
        thread_data: Dict[str, Any],
        channel_id: int
    ) -> Dict[str, Any]:
        """
        Transform UniPile email thread to Conversation format
        
        Args:
            thread_data: UniPile email thread data
            channel_id: Internal channel ID
            
        Returns:
            Dict ready for Conversation model creation
        """
        return {
            'external_conversation_id': thread_data.get('thread_id') or thread_data.get('id'),
            'channel_id': channel_id,
            'subject': thread_data.get('subject', ''),
            'last_message_at': self._parse_timestamp(
                thread_data.get('latest_date') or thread_data.get('last_message_at') or thread_data.get('updated_at')
            ),
            'metadata': {
                'thread_id': thread_data.get('thread_id'),
                'labels': thread_data.get('labels', []),
                'folder': thread_data.get('folder'),
                'unipile_data': thread_data
            },
            'unread_count': thread_data.get('unread_count', 0)
            # Note: is_read field doesn't exist on Conversation model
        }
    
    def transform_email_message(
        self,
        message_data: Dict[str, Any],
        conversation_id: str,
        channel_id: int
    ) -> Dict[str, Any]:
        """
        Transform UniPile email message to Message format
        
        Args:
            message_data: UniPile email message data
            conversation_id: Internal conversation ID
            channel_id: Internal channel ID
            
        Returns:
            Dict ready for Message model creation
        """
        # Log if we see quotes in display names
        from_attendee = message_data.get('from_attendee', {})
        if from_attendee and from_attendee.get('display_name', ''):
            if '"' in from_attendee['display_name'] or "'" in from_attendee['display_name']:
                logger.warning(f"UniPile sent quoted display_name in from_attendee: {from_attendee['display_name']}")
        
        for field in ['to_attendees', 'cc_attendees', 'bcc_attendees']:
            for att in message_data.get(field, []):
                if att and att.get('display_name', ''):
                    if '"' in att['display_name'] or "'" in att['display_name']:
                        logger.warning(f"UniPile sent quoted display_name in {field}: {att['display_name']}")
        
        # Extract subject from the message data
        subject = message_data.get('subject', '')
        
        # Log if subject is missing for debugging
        if not subject:
            logger.debug(f"Email message {message_data.get('id', 'unknown')} has no subject field")
        
        # Determine direction based on from/to fields
        direction = self._determine_email_direction(message_data, channel_id)
        
        # Get user's name for outbound messages
        user_name = None
        if direction == 'outbound':
            from communications.models import Channel, UserChannelConnection
            try:
                channel = Channel.objects.get(id=channel_id)
                # Get the user connection to find the actual user
                connection = UserChannelConnection.objects.filter(
                    unipile_account_id=channel.unipile_account_id
                ).first()
                if connection and connection.user:
                    user_name = connection.user.get_full_name() or connection.user.username
            except Exception as e:
                logger.warning(f"Error getting user name: {e}")
        
        # Convert UniPile format to our expected format
        # UniPile uses from_attendee, to_attendees, etc.
        from_data = None
        from_attendee = message_data.get('from_attendee', {})
        if from_attendee:
            # Clean quotes that UniPile preserves from email headers
            display_name = from_attendee.get('display_name', '')
            if display_name:
                display_name = display_name.strip('\'"')
            from_data = {
                'email': from_attendee.get('identifier', ''),
                'name': display_name
            }
        
        # Convert to_attendees to simpler format
        to_data = []
        for attendee in message_data.get('to_attendees', []):
            # Clean quotes that UniPile preserves from email headers
            display_name = attendee.get('display_name', '')
            if display_name:
                display_name = display_name.strip('\'"')
            to_data.append({
                'email': attendee.get('identifier', ''),
                'name': display_name
            })
        
        # Convert cc_attendees
        cc_data = []
        for attendee in message_data.get('cc_attendees', []):
            # Clean quotes that UniPile preserves from email headers
            display_name = attendee.get('display_name', '')
            if display_name:
                display_name = display_name.strip('\'"')
            cc_data.append({
                'email': attendee.get('identifier', ''),
                'name': display_name
            })
        
        # Convert bcc_attendees
        bcc_data = []
        for attendee in message_data.get('bcc_attendees', []):
            # Clean quotes that UniPile preserves from email headers
            display_name = attendee.get('display_name', '')
            if display_name:
                display_name = display_name.strip('\'"')
            bcc_data.append({
                'email': attendee.get('identifier', ''),
                'name': display_name
            })
        
        # Extract content - UniPile provides body (HTML) and body_plain (text)
        # For emails:
        # - body: Contains the HTML version of the email
        # - body_plain: Contains the plain text version
        
        body = message_data.get('body', '')
        body_plain = message_data.get('body_plain', '')
        
        # Determine content and html_content based on what's available
        html_content = ''
        content = ''
        
        if body and body_plain:
            # Both HTML and plain text available (typical email)
            html_content = body
            content = body_plain
        elif body:
            # Only body field available
            # Check if it's HTML
            if isinstance(body, str) and ('<html' in body.lower() or '<' in body):
                html_content = body
                # Use body_plain if available, otherwise strip HTML tags for plain text
                if not body_plain:
                    import re
                    content = re.sub('<[^<]+?>', '', body)
                else:
                    content = body_plain
            else:
                # Body is plain text
                content = body
        elif body_plain:
            # Only plain text available
            content = body_plain
        
        # Fallback to text_content if available (for other message types)
        if not content and message_data.get('text_content'):
            content = message_data.get('text_content')
        
        metadata = {
            'from': from_data,  # Now properly formatted
            'to': to_data,      # Now properly formatted
            'cc': cc_data,      # Now properly formatted
            'bcc': bcc_data,    # Now properly formatted
            'reply_to': message_data.get('reply_to'),
            'message_id': message_data.get('message_id'),
            'in_reply_to': message_data.get('in_reply_to'),
            'references': message_data.get('references', []),
            'attachments': message_data.get('attachments', []),
            'subject': subject,  # Also store subject in metadata for redundancy
            'unipile_id': message_data.get('id'),  # Store UniPile ID for reference
            'unipile_data': message_data
        }
        
        # Add user's name to metadata
        if user_name:
            metadata['user_name'] = user_name
            if direction == 'outbound':
                metadata['account_owner_name'] = user_name  # For outbound sender
            else:
                metadata['recipient_user_name'] = user_name  # For inbound recipient
        
        # Add HTML content if present
        if html_content:
            metadata['html_content'] = html_content
        
        # Parse the timestamp
        timestamp = self._parse_timestamp(message_data.get('sent_at') or message_data.get('date'))
        
        # Set sent_at or received_at based on direction
        result = {
            'external_message_id': message_data.get('id'),
            'conversation_id': conversation_id,
            'channel_id': channel_id,
            'direction': direction,
            'content': content,
            'subject': subject,  # Use the subject we extracted earlier
            'created_at': self._parse_timestamp(message_data.get('created_at') or message_data.get('date')),
            'metadata': metadata,
            'status': 'delivered'  # Emails are always delivered if we received them
        }
        
        # Set the appropriate timestamp field based on direction
        if direction == 'outbound':
            result['sent_at'] = timestamp
            result['received_at'] = None
        else:
            result['sent_at'] = None
            result['received_at'] = timestamp
        
        return result
    
    def transform_chat_conversation(
        self,
        chat_data: Dict[str, Any],
        channel_id: int,
        channel_type: str
    ) -> Dict[str, Any]:
        """
        Transform UniPile chat to Conversation format
        
        Args:
            chat_data: UniPile chat data
            channel_id: Internal channel ID
            channel_type: Type of channel (whatsapp, linkedin, etc.)
            
        Returns:
            Dict ready for Conversation model creation
        """
        # Build a subject/title for the chat
        subject = self._build_chat_subject(chat_data, channel_type)
        
        return {
            'external_conversation_id': chat_data.get('id'),
            'channel_id': channel_id,
            'subject': subject,
            'last_message_at': self._parse_timestamp(
                chat_data.get('last_message_at') or 
                chat_data.get('updated_at')
            ),
            'metadata': {
                'chat_type': chat_data.get('type'),  # individual, group
                'attendees': chat_data.get('attendees', []),
                'provider_chat_id': chat_data.get('provider_id'),
                'unipile_data': chat_data
            },
            'unread_count': chat_data.get('unread_count', 0)
            # Note: is_read field doesn't exist on Conversation model
        }
    
    def transform_chat_message(
        self,
        message_data: Dict[str, Any],
        conversation_id: str,
        channel_id: int,
        channel_type: str,
        account_identifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transform UniPile chat message to Message format
        
        Args:
            message_data: UniPile message data
            conversation_id: Internal conversation ID
            channel_id: Internal channel ID
            channel_type: Type of channel
            account_identifier: Account owner's identifier for direction detection
            
        Returns:
            Dict ready for Message model creation
        """
        # Determine direction
        direction = self._determine_message_direction(
            message_data, 
            channel_type,
            account_identifier
        )
        
        # Get user's name for outbound messages
        user_name = None
        if direction == 'outbound':
            from communications.models import Channel, UserChannelConnection
            try:
                channel = Channel.objects.get(id=channel_id)
                # Get the user connection to find the actual user
                connection = UserChannelConnection.objects.filter(
                    unipile_account_id=channel.unipile_account_id
                ).first()
                if connection and connection.user:
                    user_name = connection.user.get_full_name() or connection.user.username
            except Exception as e:
                logger.warning(f"Error getting user name: {e}")
        
        # Extract content - handle empty text with attachments
        content = message_data.get('text') or message_data.get('content', '')
        
        # If content is empty but there are attachments, create a description
        if not content and message_data.get('attachments'):
            attachments = message_data.get('attachments', [])
            for att in attachments:
                if att.get('type') == 'linkedin_post' and att.get('url'):
                    content = f"Shared a LinkedIn post: {att['url']}"
                    break
            if not content and attachments:
                content = f"Shared {len(attachments)} attachment(s)"
        
        # Parse the timestamp
        timestamp = self._parse_timestamp(
            message_data.get('timestamp') or 
            message_data.get('sent_at') or
            message_data.get('created_at')
        )
        
        # Build the result with appropriate timestamp field based on direction
        result = {
            'external_message_id': message_data.get('id'),
            'conversation_id': conversation_id,
            'channel_id': channel_id,
            'direction': direction,
            'content': content,
            'created_at': self._parse_timestamp(
                message_data.get('created_at') or
                message_data.get('timestamp')
            ),
            'metadata': {
                'from': message_data.get('from'),
                'to': message_data.get('to'),
                'sender_id': message_data.get('sender_attendee_id') or message_data.get('sender', {}).get('id') if isinstance(message_data.get('sender'), dict) else message_data.get('sender_id'),
                'sender_name': message_data.get('sender', {}).get('name') if isinstance(message_data.get('sender'), dict) else message_data.get('sender_name'),
                'provider_id': message_data.get('provider_id'),
                'is_sender': message_data.get('is_sender', 0),  # Store UniPile's is_sender flag
                'sender_attendee_id': message_data.get('sender_attendee_id'),  # Store actual sender's attendee ID
                'message_type': message_data.get('type'),  # text, image, video, etc.
                'attachments': message_data.get('attachments', []),
                'reactions': message_data.get('reactions', []),
                'reply_to': message_data.get('reply_to'),
                'user_name': user_name,  # Always store the user's name
                'account_owner_name': user_name if direction == 'outbound' else None,  # For outbound sender
                'recipient_user_name': user_name if direction == 'inbound' else None,  # For inbound recipient
                'unipile_data': message_data
            },
            # Preserve enriched sender info if present
            'sender': message_data.get('sender'),
            'channel_type': message_data.get('channel_type'),
            'status': self._map_message_status(message_data)
        }
        
        # Set the appropriate timestamp field based on direction
        if direction == 'outbound':
            result['sent_at'] = timestamp
            result['received_at'] = None
        else:
            result['sent_at'] = None
            result['received_at'] = timestamp
        
        return result
    
    def transform_participant(
        self,
        participant_data: Dict[str, Any],
        channel_type: str
    ) -> Dict[str, Any]:
        """
        Transform UniPile participant/attendee to Participant format
        
        Args:
            participant_data: UniPile participant data
            channel_type: Type of channel
            
        Returns:
            Dict ready for Participant model creation
        """
        # Extract identifiers based on channel type
        identifiers = self._extract_participant_identifiers(
            participant_data,
            channel_type
        )
        
        return {
            'email': identifiers.get('email', ''),
            'phone': identifiers.get('phone', ''),
            'linkedin_member_urn': identifiers.get('linkedin', ''),
            'instagram_username': identifiers.get('instagram', ''),
            'telegram_id': identifiers.get('telegram', ''),
            'name': participant_data.get('name', ''),
            'avatar_url': participant_data.get('picture_url', ''),
            'metadata': {
                'provider_id': participant_data.get('provider_id'),
                'external_id': participant_data.get('id'),
                'original_data': participant_data
            }
        }
    
    def _parse_timestamp(self, timestamp: Any) -> Optional[datetime]:
        """Parse various timestamp formats to datetime"""
        if not timestamp:
            return None
        
        if isinstance(timestamp, datetime):
            return timestamp if timestamp.tzinfo else timezone.make_aware(timestamp)
        
        if isinstance(timestamp, (int, float)):
            # Unix timestamp
            return datetime.fromtimestamp(timestamp, tz=dt_timezone.utc)
        
        if isinstance(timestamp, str):
            try:
                # ISO format
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt if dt.tzinfo else timezone.make_aware(dt)
            except:
                logger.warning(f"Failed to parse timestamp: {timestamp}")
                return None
        
        return None
    
    def _determine_email_direction(self, message_data: Dict[str, Any], channel_id: Optional[int] = None) -> str:
        """Determine if email is inbound or outbound"""
        # Check if the sender is the account owner
        from communications.models import Channel, UserChannelConnection
        
        if channel_id:
            try:
                channel = Channel.objects.get(id=channel_id)
                connection = UserChannelConnection.objects.filter(
                    unipile_account_id=channel.unipile_account_id
                ).first()
                
                if connection and connection.account_email:
                    # Get the sender email
                    from_attendee = message_data.get('from_attendee', {})
                    sender_email = from_attendee.get('identifier', '') if from_attendee else ''
                    
                    # Check if sender is the account owner
                    if sender_email.lower() == connection.account_email.lower():
                        return 'outbound'
            except Exception as e:
                logger.warning(f"Error checking email direction: {e}")
        
        return 'inbound'  # Default to inbound for received emails
    
    def _determine_message_direction(
        self,
        message_data: Dict[str, Any],
        channel_type: str,
        account_identifier: Optional[str]
    ) -> str:
        """Determine if message is inbound or outbound"""
        
        # Primary: Check is_sender field from UniPile (most reliable)
        # is_sender = 1 means the message was sent by the account owner
        is_sender = message_data.get('is_sender', 0)
        if is_sender == 1:
            return 'outbound'
        elif is_sender == 0:
            return 'inbound'
        
        # Fallback: Check is_from_me flag (WhatsApp specific)
        if message_data.get('is_from_me'):
            return 'outbound'
        
        # Fallback: Check sender information against account identifier
        if account_identifier:
            sender = message_data.get('sender', {})
            sender_id = sender.get('id') or message_data.get('from')
            
            if sender_id == account_identifier:
                return 'outbound'
        
        # Default to inbound if we can't determine
        return 'inbound'
    
    def _build_chat_subject(self, chat_data: Dict[str, Any], channel_type: str) -> str:
        """Build a subject/title for a chat conversation"""
        # Use attendee names for the subject
        attendees = chat_data.get('attendees', [])
        
        if len(attendees) == 1:
            return f"{channel_type.title()}: {attendees[0].get('name', 'Unknown')}"
        elif len(attendees) > 1:
            names = [a.get('name', 'Unknown') for a in attendees[:2]]
            return f"{channel_type.title()}: {', '.join(names)}"
        else:
            return f"{channel_type.title()} Chat"
    
    def _map_message_status(self, message_data: Dict[str, Any]) -> str:
        """Map UniPile message status to our status values"""
        status = message_data.get('status', '').lower()
        
        status_map = {
            'sent': 'sent',
            'delivered': 'delivered',
            'read': 'read',
            'failed': 'failed',
            'pending': 'pending'
        }
        
        return status_map.get(status, 'sent')
    
    def _extract_participant_identifiers(
        self,
        participant_data: Dict[str, Any],
        channel_type: str
    ) -> Dict[str, str]:
        """Extract identifiers from participant data based on channel type"""
        identifiers = {}
        
        # Common fields
        if participant_data.get('email'):
            identifiers['email'] = participant_data['email']
        
        if participant_data.get('phone'):
            identifiers['phone'] = participant_data['phone']
        
        # Channel-specific extraction
        if channel_type == 'whatsapp':
            # Extract phone from provider_id if needed
            provider_id = participant_data.get('provider_id', '')
            if '@s.whatsapp.net' in provider_id:
                phone = ProviderIdBuilder.extract_phone_from_whatsapp_id(provider_id)
                identifiers['phone'] = phone
        
        elif channel_type == 'linkedin':
            # Extract LinkedIn identifier
            if participant_data.get('linkedin_id'):
                identifiers['linkedin'] = participant_data['linkedin_id']
            elif participant_data.get('profile_url'):
                # Extract from URL
                import re
                match = re.search(r'linkedin\.com/in/([^/]+)', participant_data['profile_url'])
                if match:
                    identifiers['linkedin'] = match.group(1)
        
        elif channel_type == 'instagram':
            if participant_data.get('username'):
                identifiers['instagram'] = participant_data['username'].replace('@', '')
        
        elif channel_type == 'telegram':
            if participant_data.get('telegram_id'):
                identifiers['telegram'] = participant_data['telegram_id']
        
        return identifiers