"""
Message Normalizer Service - Creates unified message structure across all channels
Handles Email, LinkedIn, WhatsApp, and other Unipile-supported channels
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.utils import timezone

from communications.models import ChannelType, MessageDirection, MessageStatus

logger = logging.getLogger(__name__)


class ChannelMessageNormalizer:
    """Normalizes messages from different channels into a unified format"""
    
    def __init__(self):
        self.logger = logger
        
        # Channel-specific normalization handlers
        self.normalizers = {
            ChannelType.LINKEDIN: self._normalize_linkedin_message,
            ChannelType.GOOGLE: self._normalize_email_message,
            ChannelType.OUTLOOK: self._normalize_email_message,
            ChannelType.MAIL: self._normalize_email_message,
            ChannelType.WHATSAPP: self._normalize_whatsapp_message,
            ChannelType.INSTAGRAM: self._normalize_social_message,
            ChannelType.MESSENGER: self._normalize_social_message,
            ChannelType.TELEGRAM: self._normalize_messaging_app,
            ChannelType.TWITTER: self._normalize_social_message
        }
    
    def normalize_unipile_message(self, raw_message: Dict[str, Any], channel_type: str) -> Dict[str, Any]:
        """
        Normalize a message from Unipile API into unified format
        
        Args:
            raw_message: Raw message data from Unipile API
            channel_type: Type of channel (linkedin, gmail, whatsapp, etc.)
            
        Returns:
            Normalized message dictionary
        """
        try:
            # Get appropriate normalizer
            normalizer = self.normalizers.get(channel_type, self._normalize_generic_message)
            
            # Base normalized structure
            normalized = {
                'id': raw_message.get('id'),
                'external_id': raw_message.get('id'),
                'channel_type': channel_type,
                'content': '',
                'subject': '',
                'direction': MessageDirection.INBOUND,
                'status': MessageStatus.DELIVERED,
                'created_at': None,
                'sent_at': None,
                'contact_email': '',
                'contact_phone': '',
                'contact_name': '',
                'conversation_id': '',
                'thread_id': '',
                'attachments': [],
                'metadata': {},
                'formatted_content': {},
                'channel_specific_data': raw_message
            }
            
            # Apply channel-specific normalization
            channel_normalized = normalizer(raw_message)
            normalized.update(channel_normalized)
            
            # Apply common post-processing
            normalized = self._apply_common_normalization(normalized)
            
            return normalized
            
        except Exception as e:
            self.logger.error(f"Error normalizing message from {channel_type}: {e}")
            return self._create_error_message(raw_message, channel_type, str(e))
    
    def _normalize_email_message(self, raw_message: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize email message (Gmail, Outlook, generic email)"""
        
        # Extract email-specific fields
        headers = raw_message.get('headers', {})
        body = raw_message.get('body', {})
        
        return {
            'content': body.get('text', body.get('html', '')),
            'subject': raw_message.get('subject', headers.get('Subject', '')),
            'direction': self._determine_email_direction(raw_message),
            'status': self._map_email_status(raw_message.get('status')),
            'created_at': self._parse_timestamp(raw_message.get('date') or headers.get('Date')),
            'sent_at': self._parse_timestamp(raw_message.get('date') or headers.get('Date')),
            'contact_email': self._extract_email_contact(raw_message),
            'contact_name': self._extract_email_name(raw_message),
            'conversation_id': raw_message.get('conversation_id'),
            'thread_id': headers.get('Message-ID') or raw_message.get('thread_id'),
            'attachments': self._extract_email_attachments(raw_message),
            'metadata': {
                'email_headers': headers,
                'message_id': headers.get('Message-ID'),
                'in_reply_to': headers.get('In-Reply-To'),
                'references': headers.get('References'),
                'folder': raw_message.get('folder'),
                'labels': raw_message.get('labels', []),
                'importance': headers.get('X-Priority', 'normal')
            },
            'formatted_content': {
                'html': body.get('html', ''),
                'text': body.get('text', ''),
                'preview': self._create_preview(body.get('text', body.get('html', '')))
            }
        }
    
    def _normalize_linkedin_message(self, raw_message: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize LinkedIn message"""
        
        return {
            'content': raw_message.get('text', raw_message.get('content', '')),
            'subject': '',  # LinkedIn messages don't have subjects
            'direction': self._determine_linkedin_direction(raw_message),
            'status': self._map_linkedin_status(raw_message.get('status')),
            'created_at': self._parse_timestamp(raw_message.get('created_at') or raw_message.get('timestamp')),
            'sent_at': self._parse_timestamp(raw_message.get('sent_at') or raw_message.get('timestamp')),
            'contact_email': '',  # LinkedIn uses profile IDs
            'contact_name': self._extract_linkedin_name(raw_message),
            'conversation_id': raw_message.get('conversation_id') or raw_message.get('chat_id'),
            'thread_id': raw_message.get('conversation_id') or raw_message.get('chat_id'),
            'attachments': self._extract_linkedin_attachments(raw_message),
            'metadata': {
                'profile_id': raw_message.get('from_profile_id') or raw_message.get('sender_id'),
                'connection_status': raw_message.get('connection_status'),
                'inmail': raw_message.get('is_inmail', False),
                'inmail_credits_used': raw_message.get('inmail_credits_used', 0),
                'company_info': raw_message.get('company_info', {}),
                'job_title': raw_message.get('job_title', ''),
                'mutual_connections': raw_message.get('mutual_connections', [])
            },
            'formatted_content': {
                'text': raw_message.get('text', raw_message.get('content', '')),
                'preview': self._create_preview(raw_message.get('text', raw_message.get('content', '')))
            }
        }
    
    def _normalize_whatsapp_message(self, raw_message: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize WhatsApp message"""
        
        return {
            'content': raw_message.get('text', raw_message.get('body', '')),
            'subject': '',  # WhatsApp messages don't have subjects
            'direction': self._determine_whatsapp_direction(raw_message),
            'status': self._map_whatsapp_status(raw_message.get('status')),
            'created_at': self._parse_timestamp(raw_message.get('timestamp') or raw_message.get('created_at')),
            'sent_at': self._parse_timestamp(raw_message.get('timestamp') or raw_message.get('created_at')),
            'contact_email': self._extract_whatsapp_email(raw_message),
            'contact_phone': self._extract_whatsapp_phone(raw_message),
            'contact_name': self._extract_whatsapp_name(raw_message),
            'conversation_id': raw_message.get('chat_id') or raw_message.get('conversation_id'),
            'thread_id': raw_message.get('chat_id') or raw_message.get('conversation_id'),
            'attachments': self._extract_whatsapp_media(raw_message),
            'metadata': {
                'whatsapp_id': raw_message.get('id'),
                'message_type': raw_message.get('type', 'text'),
                'business_account': raw_message.get('business_account', False),
                'forwarded': raw_message.get('forwarded', False),
                'quoted_message': raw_message.get('quoted_message'),
                'group_chat': raw_message.get('group_chat', False),
                'group_participants': raw_message.get('group_participants', []),
                'delivery_receipt': raw_message.get('delivery_receipt', False),
                'read_receipt': raw_message.get('read_receipt', False)
            },
            'formatted_content': {
                'text': raw_message.get('text', raw_message.get('body', '')),
                'media_type': raw_message.get('type', 'text'),
                'preview': self._create_preview(raw_message.get('text', raw_message.get('body', '')))
            }
        }
    
    def _normalize_social_message(self, raw_message: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize social media message (Instagram, Messenger, Twitter)"""
        
        return {
            'content': raw_message.get('text', raw_message.get('content', raw_message.get('message', ''))),
            'subject': '',
            'direction': self._determine_social_direction(raw_message),
            'status': self._map_social_status(raw_message.get('status')),
            'created_at': self._parse_timestamp(raw_message.get('timestamp') or raw_message.get('created_at')),
            'sent_at': self._parse_timestamp(raw_message.get('timestamp') or raw_message.get('created_at')),
            'contact_email': '',
            'contact_name': self._extract_social_name(raw_message),
            'conversation_id': raw_message.get('conversation_id') or raw_message.get('thread_id'),
            'thread_id': raw_message.get('conversation_id') or raw_message.get('thread_id'),
            'attachments': self._extract_social_media(raw_message),
            'metadata': {
                'platform_user_id': raw_message.get('user_id') or raw_message.get('sender_id'),
                'username': raw_message.get('username'),
                'platform_specific': raw_message
            },
            'formatted_content': {
                'text': raw_message.get('text', raw_message.get('content', '')),
                'preview': self._create_preview(raw_message.get('text', raw_message.get('content', '')))
            }
        }
    
    def _normalize_messaging_app(self, raw_message: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize messaging app message (Telegram)"""
        
        return {
            'content': raw_message.get('text', raw_message.get('message', '')),
            'subject': '',
            'direction': self._determine_messaging_direction(raw_message),
            'status': self._map_messaging_status(raw_message.get('status')),
            'created_at': self._parse_timestamp(raw_message.get('date') or raw_message.get('timestamp')),
            'sent_at': self._parse_timestamp(raw_message.get('date') or raw_message.get('timestamp')),
            'contact_email': '',
            'contact_name': self._extract_messaging_name(raw_message),
            'conversation_id': raw_message.get('chat_id'),
            'thread_id': raw_message.get('chat_id'),
            'attachments': self._extract_messaging_media(raw_message),
            'metadata': {
                'user_id': raw_message.get('from', {}).get('id'),
                'username': raw_message.get('from', {}).get('username'),
                'chat_type': raw_message.get('chat', {}).get('type'),
                'forwarded': raw_message.get('forward_from') is not None
            },
            'formatted_content': {
                'text': raw_message.get('text', raw_message.get('message', '')),
                'preview': self._create_preview(raw_message.get('text', raw_message.get('message', '')))
            }
        }
    
    def _normalize_generic_message(self, raw_message: Dict[str, Any]) -> Dict[str, Any]:
        """Generic normalization for unknown channel types"""
        
        return {
            'content': raw_message.get('content', raw_message.get('text', raw_message.get('message', ''))),
            'subject': raw_message.get('subject', ''),
            'direction': MessageDirection.INBOUND,
            'status': MessageStatus.DELIVERED,
            'created_at': self._parse_timestamp(raw_message.get('created_at') or raw_message.get('timestamp')),
            'sent_at': self._parse_timestamp(raw_message.get('sent_at') or raw_message.get('timestamp')),
            'contact_email': raw_message.get('from_email', raw_message.get('email', '')),
            'contact_name': raw_message.get('from_name', raw_message.get('name', '')),
            'conversation_id': raw_message.get('conversation_id', raw_message.get('thread_id', '')),
            'thread_id': raw_message.get('thread_id', raw_message.get('conversation_id', '')),
            'attachments': raw_message.get('attachments', []),
            'metadata': {
                'original_data': raw_message
            },
            'formatted_content': {
                'text': raw_message.get('content', raw_message.get('text', '')),
                'preview': self._create_preview(raw_message.get('content', raw_message.get('text', '')))
            }
        }
    
    def _apply_common_normalization(self, normalized: Dict[str, Any]) -> Dict[str, Any]:
        """Apply common normalization rules across all channels"""
        
        # Ensure required fields have defaults
        if not normalized.get('created_at'):
            normalized['created_at'] = timezone.now()
        
        if not normalized.get('sent_at'):
            normalized['sent_at'] = normalized['created_at']
        
        # Clean and validate content
        normalized['content'] = self._clean_content(normalized.get('content', ''))
        normalized['subject'] = self._clean_subject(normalized.get('subject', ''))
        
        # Ensure contact information is clean
        normalized['contact_email'] = self._clean_email(normalized.get('contact_email', ''))
        normalized['contact_phone'] = self._clean_phone(normalized.get('contact_phone', ''))
        normalized['contact_name'] = self._clean_name(normalized.get('contact_name', ''))
        
        # Add processing metadata
        normalized['metadata']['normalized_at'] = timezone.now().isoformat()
        normalized['metadata']['normalizer_version'] = '1.0'
        
        return normalized
    
    # Helper methods for extracting and parsing data
    
    def _determine_email_direction(self, raw_message: Dict[str, Any]) -> str:
        """Determine if email is inbound or outbound"""
        # This would check sender vs account owner
        return MessageDirection.INBOUND  # Simplified for now
    
    def _determine_linkedin_direction(self, raw_message: Dict[str, Any]) -> str:
        """Determine LinkedIn message direction"""
        return MessageDirection.INBOUND  # Simplified for now
    
    def _determine_whatsapp_direction(self, raw_message: Dict[str, Any]) -> str:
        """Determine WhatsApp message direction"""
        return MessageDirection.INBOUND  # Simplified for now
    
    def _determine_social_direction(self, raw_message: Dict[str, Any]) -> str:
        """Determine social media message direction"""
        return MessageDirection.INBOUND  # Simplified for now
    
    def _determine_messaging_direction(self, raw_message: Dict[str, Any]) -> str:
        """Determine messaging app direction"""
        return MessageDirection.INBOUND  # Simplified for now
    
    def _map_email_status(self, status: str) -> str:
        """Map email status to standard status"""
        status_mapping = {
            'read': MessageStatus.READ,
            'unread': MessageStatus.DELIVERED,
            'sent': MessageStatus.SENT,
            'draft': MessageStatus.PENDING
        }
        return status_mapping.get(status, MessageStatus.DELIVERED)
    
    def _map_linkedin_status(self, status: str) -> str:
        """Map LinkedIn status to standard status"""
        return MessageStatus.DELIVERED  # LinkedIn messages are typically delivered
    
    def _map_whatsapp_status(self, status: str) -> str:
        """Map WhatsApp status to standard status"""
        status_mapping = {
            'sent': MessageStatus.SENT,
            'delivered': MessageStatus.DELIVERED,
            'read': MessageStatus.READ,
            'failed': MessageStatus.FAILED
        }
        return status_mapping.get(status, MessageStatus.DELIVERED)
    
    def _map_social_status(self, status: str) -> str:
        """Map social media status to standard status"""
        return MessageStatus.DELIVERED
    
    def _map_messaging_status(self, status: str) -> str:
        """Map messaging app status to standard status"""
        return MessageStatus.DELIVERED
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse timestamp string to datetime object"""
        if not timestamp_str:
            return None
        
        try:
            # Handle various timestamp formats
            if isinstance(timestamp_str, (int, float)):
                return datetime.fromtimestamp(timestamp_str, tz=timezone.utc)
            
            # Try ISO format first
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            try:
                # Try other common formats
                from datetime import datetime
                return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return None
    
    def _extract_email_contact(self, raw_message: Dict[str, Any]) -> str:
        """Extract email contact information"""
        from_field = raw_message.get('from', raw_message.get('sender', ''))
        if isinstance(from_field, dict):
            return from_field.get('email', '')
        return str(from_field) if from_field else ''
    
    def _extract_email_name(self, raw_message: Dict[str, Any]) -> str:
        """Extract email sender name"""
        from_field = raw_message.get('from', raw_message.get('sender', ''))
        if isinstance(from_field, dict):
            return from_field.get('name', '')
        return ''
    
    def _extract_linkedin_name(self, raw_message: Dict[str, Any]) -> str:
        """Extract LinkedIn contact name"""
        sender = raw_message.get('sender', raw_message.get('from', {}))
        if isinstance(sender, dict):
            return f"{sender.get('first_name', '')} {sender.get('last_name', '')}".strip()
        return str(sender) if sender else ''
    
    def _extract_whatsapp_email(self, raw_message: Dict[str, Any]) -> str:
        """Extract WhatsApp contact email (if available)"""
        # WhatsApp typically doesn't have email, but business accounts might
        return raw_message.get('contact_email', '')
    
    def _extract_whatsapp_phone(self, raw_message: Dict[str, Any]) -> str:
        """Extract WhatsApp phone number"""
        phone = raw_message.get('from', raw_message.get('phone', ''))
        if phone and phone.endswith('@s.whatsapp.net'):
            return phone.replace('@s.whatsapp.net', '')
        return phone
    
    def _extract_whatsapp_name(self, raw_message: Dict[str, Any]) -> str:
        """Extract WhatsApp contact name"""
        return raw_message.get('sender_name', raw_message.get('contact_name', ''))
    
    def _extract_social_name(self, raw_message: Dict[str, Any]) -> str:
        """Extract social media contact name"""
        sender = raw_message.get('sender', raw_message.get('from', {}))
        if isinstance(sender, dict):
            return sender.get('name', sender.get('username', ''))
        return str(sender) if sender else ''
    
    def _extract_messaging_name(self, raw_message: Dict[str, Any]) -> str:
        """Extract messaging app contact name"""
        from_field = raw_message.get('from', {})
        if isinstance(from_field, dict):
            return from_field.get('first_name', '') + ' ' + from_field.get('last_name', '')
        return str(from_field) if from_field else ''
    
    def _extract_email_attachments(self, raw_message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract email attachments"""
        attachments = raw_message.get('attachments', [])
        if not isinstance(attachments, list):
            return []
        
        return [
            {
                'filename': att.get('filename', 'attachment'),
                'content_type': att.get('content_type', 'application/octet-stream'),
                'size': att.get('size', 0),
                'attachment_id': att.get('id'),
                'download_url': att.get('download_url')
            }
            for att in attachments
        ]
    
    def _extract_linkedin_attachments(self, raw_message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract LinkedIn attachments"""
        # LinkedIn messages can have limited attachments
        return []
    
    def _extract_whatsapp_media(self, raw_message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract WhatsApp media attachments"""
        media = raw_message.get('media', [])
        if not isinstance(media, list):
            media = [raw_message.get('media')] if raw_message.get('media') else []
        
        return [
            {
                'filename': m.get('filename', 'media'),
                'content_type': m.get('mime_type', 'application/octet-stream'),
                'media_type': m.get('type', 'unknown'),
                'size': m.get('size', 0),
                'media_id': m.get('id'),
                'download_url': m.get('url')
            }
            for m in media if m
        ]
    
    def _extract_social_media(self, raw_message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract social media attachments"""
        return []
    
    def _extract_messaging_media(self, raw_message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract messaging app media"""
        return []
    
    def _clean_content(self, content: str) -> str:
        """Clean and sanitize message content"""
        if not content:
            return ''
        return str(content).strip()
    
    def _clean_subject(self, subject: str) -> str:
        """Clean and sanitize subject line"""
        if not subject:
            return ''
        return str(subject).strip()
    
    def _clean_email(self, email: str) -> str:
        """Clean and validate email address"""
        if not email:
            return ''
        email = str(email).strip().lower()
        # Basic email validation could be added here
        return email
    
    def _clean_phone(self, phone: str) -> str:
        """Clean and format phone number"""
        if not phone:
            return ''
        # Remove common phone number formatting
        return ''.join(filter(str.isdigit, str(phone)))
    
    def _clean_name(self, name: str) -> str:
        """Clean contact name"""
        if not name:
            return ''
        return str(name).strip()
    
    def _create_preview(self, content: str, max_length: int = 100) -> str:
        """Create content preview"""
        if not content:
            return ''
        
        # Strip HTML if present
        import re
        clean_content = re.sub(r'<[^>]+>', '', content)
        clean_content = clean_content.strip()
        
        if len(clean_content) <= max_length:
            return clean_content
        
        return clean_content[:max_length - 3] + '...'
    
    def _create_error_message(self, raw_message: Dict[str, Any], channel_type: str, error: str) -> Dict[str, Any]:
        """Create error message when normalization fails"""
        return {
            'id': raw_message.get('id', 'error'),
            'external_id': raw_message.get('id', 'error'),
            'channel_type': channel_type,
            'content': f"Error processing message: {error}",
            'subject': '',
            'direction': MessageDirection.INBOUND,
            'status': MessageStatus.FAILED,
            'created_at': timezone.now(),
            'sent_at': timezone.now(),
            'contact_email': '',
            'contact_phone': '',
            'contact_name': '',
            'conversation_id': '',
            'thread_id': '',
            'attachments': [],
            'metadata': {
                'error': error,
                'original_data': raw_message,
                'normalization_failed': True
            },
            'formatted_content': {
                'text': f"Error processing message: {error}",
                'preview': f"Error: {error}"
            },
            'channel_specific_data': raw_message
        }


# Global normalizer instance
message_normalizer = ChannelMessageNormalizer()