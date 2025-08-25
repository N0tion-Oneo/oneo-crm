"""
WhatsApp Message Formatter
Formats messages for WhatsApp display and sending
"""
import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class WhatsAppMessageFormatter:
    """Formats messages for WhatsApp"""
    
    # WhatsApp formatting markers
    BOLD_MARKER = '*'
    ITALIC_MARKER = '_'
    STRIKETHROUGH_MARKER = '~'
    MONOSPACE_MARKER = '```'
    
    def format_outgoing_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Format message content for sending via WhatsApp
        
        Args:
            content: Raw message content
            metadata: Optional metadata for formatting hints
            
        Returns:
            Formatted message content
        """
        if not content:
            return ""
        
        # Clean up HTML if present
        content = self._strip_html(content)
        
        # Apply WhatsApp formatting if metadata provides hints
        if metadata:
            if metadata.get('bold'):
                content = self.make_bold(content)
            if metadata.get('italic'):
                content = self.make_italic(content)
            if metadata.get('code'):
                content = self.make_monospace(content)
        
        # Ensure message doesn't exceed WhatsApp limits
        return self._truncate_if_needed(content)
    
    def format_incoming_message(self, raw_message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format incoming WhatsApp message for storage
        
        Args:
            raw_message: Raw message data from UniPile
            
        Returns:
            Formatted message dictionary
        """
        formatted = {
            'content': raw_message.get('text', '') or raw_message.get('body', ''),
            'external_id': raw_message.get('id') or raw_message.get('message_id'),
            'timestamp': self._parse_timestamp(raw_message.get('timestamp')),
            'is_deleted': raw_message.get('is_deleted', False),
            'is_edited': raw_message.get('is_edited', False),
            'reply_to': raw_message.get('reply_to_message_id'),
            'forwarded': raw_message.get('is_forwarded', False),
            'media_type': None,
            'media_url': None,
            'media_caption': None
        }
        
        # Handle media messages
        media = raw_message.get('media', {})
        if media:
            formatted['media_type'] = media.get('type')
            formatted['media_url'] = media.get('url')
            formatted['media_caption'] = media.get('caption')
            
            # If no text content, use caption or media type as content
            if not formatted['content']:
                if formatted['media_caption']:
                    formatted['content'] = formatted['media_caption']
                else:
                    formatted['content'] = f"[{formatted['media_type'] or 'Media'} message]"
        
        # Handle attachments (alternative format)
        attachments = raw_message.get('attachments', [])
        if attachments and not formatted['media_type']:
            first_attachment = attachments[0] if attachments else {}
            formatted['media_type'] = first_attachment.get('type')
            formatted['media_url'] = first_attachment.get('url')
            formatted['media_caption'] = first_attachment.get('name') or first_attachment.get('caption')
        
        # Handle reactions
        reactions = raw_message.get('reactions', [])
        if reactions:
            formatted['reactions'] = [
                {
                    'emoji': r.get('emoji'),
                    'from': r.get('from_id'),
                    'timestamp': self._parse_timestamp(r.get('timestamp'))
                }
                for r in reactions
            ]
        
        return formatted
    
    def format_conversation_name(self, chat_data: Dict[str, Any], attendees: List[Any] = None) -> str:
        """
        Generate a formatted conversation name
        
        Args:
            chat_data: Chat data from API
            attendees: Optional list of attendees
            
        Returns:
            Formatted conversation name
        """
        # Use provided name if available
        name = chat_data.get('name') or chat_data.get('subject')
        if name:
            return self._clean_name(name)
        
        # For group chats
        if chat_data.get('is_group'):
            participant_count = len(attendees) if attendees else chat_data.get('participant_count', 0)
            if participant_count > 0:
                return f"Group chat ({participant_count} members)"
            return "Group chat"
        
        # For 1-1 chats, try to get the other person's name
        if attendees:
            # Handle both dict and object formats
            non_self = []
            for a in attendees:
                # Check if it's a dict or object
                if isinstance(a, dict):
                    if not a.get('is_self', False):
                        non_self.append(a)
                else:
                    if not getattr(a, 'is_self', False):
                        non_self.append(a)
            
            if non_self:
                # Get name from dict or object
                first_attendee = non_self[0]
                if isinstance(first_attendee, dict):
                    name = first_attendee.get('name')
                else:
                    name = getattr(first_attendee, 'name', None)
                
                if name:
                    return self._clean_name(name)
        
        # Try to extract from recipient info
        recipient = chat_data.get('recipient', {})
        if recipient:
            recipient_name = recipient.get('name') or recipient.get('phone')
            if recipient_name:
                return self._clean_name(recipient_name)
        
        # Fallback
        chat_id = chat_data.get('id', 'Unknown')
        return f"WhatsApp Chat {chat_id[:8] if len(chat_id) > 8 else chat_id}"
    
    def make_bold(self, text: str) -> str:
        """Make text bold in WhatsApp format"""
        return f"{self.BOLD_MARKER}{text}{self.BOLD_MARKER}"
    
    def make_italic(self, text: str) -> str:
        """Make text italic in WhatsApp format"""
        return f"{self.ITALIC_MARKER}{text}{self.ITALIC_MARKER}"
    
    def make_strikethrough(self, text: str) -> str:
        """Make text strikethrough in WhatsApp format"""
        return f"{self.STRIKETHROUGH_MARKER}{text}{self.STRIKETHROUGH_MARKER}"
    
    def make_monospace(self, text: str) -> str:
        """Make text monospace/code in WhatsApp format"""
        if '\n' in text:
            # Multi-line code block
            return f"{self.MONOSPACE_MARKER}\n{text}\n{self.MONOSPACE_MARKER}"
        else:
            # Inline code
            return f"`{text}`"
    
    def extract_phone_numbers(self, text: str) -> List[str]:
        """
        Extract phone numbers from text
        
        Args:
            text: Text to search
            
        Returns:
            List of phone numbers found
        """
        # Pattern for various phone number formats
        patterns = [
            r'\+?1?\d{10,15}',  # International format
            r'\(\d{3}\)\s*\d{3}-\d{4}',  # (123) 456-7890
            r'\d{3}-\d{3}-\d{4}',  # 123-456-7890
            r'\d{3}\.\d{3}\.\d{4}',  # 123.456.7890
        ]
        
        phone_numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            phone_numbers.extend(matches)
        
        # Clean and deduplicate
        cleaned_numbers = []
        seen = set()
        for number in phone_numbers:
            cleaned = re.sub(r'[^\d+]', '', number)
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                cleaned_numbers.append(cleaned)
        
        return cleaned_numbers
    
    def extract_urls(self, text: str) -> List[str]:
        """
        Extract URLs from text
        
        Args:
            text: Text to search
            
        Returns:
            List of URLs found
        """
        # Simple URL pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.findall(url_pattern, text)
    
    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text"""
        if not text:
            return ""
        
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        import html
        clean = html.unescape(clean)
        
        return clean.strip()
    
    def _truncate_if_needed(self, text: str, max_length: int = 4096) -> str:
        """
        Truncate text if it exceeds WhatsApp limits
        
        Args:
            text: Text to truncate
            max_length: Maximum allowed length
            
        Returns:
            Truncated text if needed
        """
        if len(text) <= max_length:
            return text
        
        # Truncate and add ellipsis
        return text[:max_length - 3] + "..."
    
    def _parse_timestamp(self, timestamp: Any) -> Optional[datetime]:
        """
        Parse timestamp from various formats
        
        Args:
            timestamp: Timestamp in various formats
            
        Returns:
            datetime object or None
        """
        if not timestamp:
            return None
        
        try:
            if isinstance(timestamp, datetime):
                return timestamp
            elif isinstance(timestamp, str):
                # Try ISO format first
                try:
                    return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    # Try other common formats
                    from dateutil import parser
                    return parser.parse(timestamp)
            elif isinstance(timestamp, (int, float)):
                # Unix timestamp
                return datetime.fromtimestamp(timestamp)
        except Exception as e:
            logger.warning(f"Failed to parse timestamp {timestamp}: {e}")
            return None
        
        return None
    
    def _clean_name(self, name: str) -> str:
        """
        Clean and format a name for display
        
        Args:
            name: Raw name string
            
        Returns:
            Cleaned name
        """
        if not name:
            return "Unknown"
        
        # Remove excess whitespace
        name = ' '.join(name.split())
        
        # Remove special characters that might cause issues
        name = re.sub(r'[<>"/\\|?*]', '', name)
        
        # Truncate if too long
        if len(name) > 100:
            name = name[:97] + "..."
        
        return name or "Unknown"