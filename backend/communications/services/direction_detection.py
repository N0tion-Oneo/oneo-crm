"""
Enhanced message direction detection using stored account data
"""
import logging
from typing import Dict, Any, Optional, Tuple
from communications.models import UserChannelConnection, MessageDirection

logger = logging.getLogger(__name__)


class DirectionDetectionService:
    """
    Service for determining message direction using comprehensive account data
    """
    
    def determine_direction(self, connection: UserChannelConnection, message_data: Dict[str, Any], 
                          event_type: str = None) -> Tuple[MessageDirection, Dict[str, Any]]:
        """
        Determine message direction using stored account data and webhook context
        
        Args:
            connection: UserChannelConnection with stored account data
            message_data: Raw message data from UniPile webhook
            event_type: Webhook event type (message_received, message_sent, etc.)
            
        Returns:
            Tuple of (MessageDirection enum, metadata dict with detection details)
        """
        detection_metadata = {
            'detection_method': None,
            'confidence': 'high',
            'account_phone': None,
            'sender_info': None,
            'event_type': event_type
        }
        
        try:
            # Method 1: Use stored account data for phone/email comparison (highest confidence)
            if connection.channel_type == 'whatsapp':
                direction = self._detect_whatsapp_by_account_data(connection, message_data, detection_metadata)
                if direction:
                    return direction, detection_metadata
            
            # Method 2: Use stored email for email channels
            elif connection.channel_type in ['gmail', 'outlook', 'email']:
                direction = self._detect_email_by_account_data(connection, message_data, detection_metadata)
                if direction:
                    return direction, detection_metadata
            
            # Method 3: Use LinkedIn profile data
            elif connection.channel_type == 'linkedin':
                direction = self._detect_linkedin_by_account_data(connection, message_data, detection_metadata)
                if direction:
                    return direction, detection_metadata
            
            # Method 4: Use webhook event type (fallback for unknown channels)
            if event_type:
                direction = self._detect_by_event_type(event_type)
                if direction:
                    detection_metadata['detection_method'] = 'webhook_event_type_fallback'
                    detection_metadata['confidence'] = 'medium'
                    logger.debug(f"Direction detected by event type fallback {event_type}: {direction}")
                    return direction, detection_metadata
            
            # Method 5: Fallback to legacy direction detection
            direction = self._detect_by_legacy_methods(message_data, detection_metadata)
            return direction, detection_metadata
            
        except Exception as e:
            logger.error(f"Error detecting message direction: {e}")
            detection_metadata['detection_method'] = 'error_fallback'
            detection_metadata['confidence'] = 'low'
            detection_metadata['error'] = str(e)
            return MessageDirection.INBOUND, detection_metadata
    
    def _detect_by_event_type(self, event_type: str) -> Optional[MessageDirection]:
        """
        Detect direction based on webhook event type
        
        Most reliable method since UniPile sends specific events for sent vs received
        """
        event_type_lower = event_type.lower()
        
        # Incoming message events
        if event_type_lower in ['message_received', 'message.received', 'mail_received', 'incoming_message']:
            return MessageDirection.INBOUND
        
        # Outgoing message events  
        if event_type_lower in ['message_sent', 'message.sent', 'mail_sent', 'outgoing_message']:
            return MessageDirection.OUTBOUND
        
        # Delivery and read receipts are typically for outbound messages
        if event_type_lower in ['message_delivered', 'message.delivered', 'message_read', 'message.read']:
            return MessageDirection.OUTBOUND
        
        return None
    
    def _detect_whatsapp_by_account_data(self, connection: UserChannelConnection, 
                                       message_data: Dict[str, Any], 
                                       metadata: Dict[str, Any]) -> Optional[MessageDirection]:
        """
        Detect WhatsApp direction using stored account phone number
        """
        # Get stored phone number from account data
        account_phone = connection.connection_config.get('phone_number')
        if not account_phone:
            logger.debug("No phone number in stored account data")
            return None
        
        metadata['account_phone'] = account_phone
        
        # Extract sender information from webhook data
        sender_info = self._extract_sender_info(message_data)
        metadata['sender_info'] = sender_info
        
        if not sender_info:
            logger.debug("No sender information in message data")
            return None
        
        # Get sender phone from various possible fields
        sender_phone = (
            sender_info.get('phone_number') or 
            sender_info.get('attendee_provider_id') or 
            sender_info.get('provider_id', '')
        )
        
        if not sender_phone:
            logger.debug("No sender phone found in sender info")
            return None
        
        # Clean phone numbers for comparison
        account_phone_clean = self._clean_phone_number(account_phone)
        sender_phone_clean = self._clean_phone_number(sender_phone)
        
        logger.info(f"🔍 WhatsApp Direction Detection:")
        logger.info(f"   Business Phone: {account_phone} (cleaned: {account_phone_clean})")
        logger.info(f"   Sender Phone: {sender_phone} (cleaned: {sender_phone_clean})")
        
        if account_phone_clean and sender_phone_clean:
            if account_phone_clean == sender_phone_clean:
                metadata['detection_method'] = 'account_phone_match'
                metadata['confidence'] = 'high'
                logger.info(f"✅ OUTBOUND: Business phone {account_phone_clean} matches sender {sender_phone_clean}")
                return MessageDirection.OUTBOUND
            else:
                metadata['detection_method'] = 'account_phone_mismatch'
                metadata['confidence'] = 'high'  
                logger.info(f"✅ INBOUND: Business phone {account_phone_clean} != sender {sender_phone_clean}")
                return MessageDirection.INBOUND
        else:
            logger.warning(f"Could not clean phone numbers for comparison: account={account_phone}, sender={sender_phone}")
        
        return None
    
    def _detect_email_by_account_data(self, connection: UserChannelConnection, 
                                    message_data: Dict[str, Any],
                                    metadata: Dict[str, Any]) -> Optional[MessageDirection]:
        """
        Detect email direction using stored account email
        """
        # For email, we can use the user's email from the connection
        account_email = connection.user.email
        metadata['account_email'] = account_email
        
        # Extract sender email from message data
        sender_email = self._extract_email_sender(message_data)
        metadata['sender_email'] = sender_email
        
        if account_email and sender_email:
            if account_email.lower() == sender_email.lower():
                metadata['detection_method'] = 'account_email_match'
                metadata['confidence'] = 'high'
                return MessageDirection.OUTBOUND
            else:
                metadata['detection_method'] = 'account_email_mismatch'
                metadata['confidence'] = 'high'
                return MessageDirection.INBOUND
        
        return None
    
    def _detect_linkedin_by_account_data(self, connection: UserChannelConnection,
                                       message_data: Dict[str, Any],
                                       metadata: Dict[str, Any]) -> Optional[MessageDirection]:
        """
        Detect LinkedIn direction using stored profile data
        """
        # LinkedIn profile ID would be stored in provider_config
        account_profile_id = connection.provider_config.get('profile_id')
        if not account_profile_id:
            return None
        
        metadata['account_profile_id'] = account_profile_id
        
        # Extract sender profile ID
        sender_info = self._extract_sender_info(message_data)
        sender_profile_id = sender_info.get('profile_id') if sender_info else None
        metadata['sender_profile_id'] = sender_profile_id
        
        if account_profile_id and sender_profile_id:
            if account_profile_id == sender_profile_id:
                metadata['detection_method'] = 'account_profile_match'
                metadata['confidence'] = 'high'
                return MessageDirection.OUTBOUND
            else:
                metadata['detection_method'] = 'account_profile_mismatch'
                metadata['confidence'] = 'high'
                return MessageDirection.INBOUND
        
        return None
    
    def _detect_by_legacy_methods(self, message_data: Dict[str, Any], 
                                metadata: Dict[str, Any]) -> MessageDirection:
        """
        Fallback to legacy direction detection methods
        """
        metadata['detection_method'] = 'legacy_fallback'
        metadata['confidence'] = 'medium'
        
        # Use is_sender field if available
        if 'is_sender' in message_data:
            is_sender = message_data.get('is_sender', 0)
            direction = MessageDirection.OUTBOUND if is_sender else MessageDirection.INBOUND
            metadata['legacy_method'] = 'is_sender_field'
            return direction
        
        # Check direction field directly
        direction_field = message_data.get('direction', '').lower()
        if direction_field in ['in', 'inbound', 'received']:
            metadata['legacy_method'] = 'direction_field'
            return MessageDirection.INBOUND
        elif direction_field in ['out', 'outbound', 'sent']:
            metadata['legacy_method'] = 'direction_field'
            return MessageDirection.OUTBOUND
        
        # Check message type/source indicators
        message_type = message_data.get('type', '').lower()
        if message_type in ['received', 'incoming']:
            metadata['legacy_method'] = 'message_type'
            return MessageDirection.INBOUND
        elif message_type in ['sent', 'outgoing']:
            metadata['legacy_method'] = 'message_type'
            return MessageDirection.OUTBOUND
        
        # Final fallback: assume inbound
        metadata['legacy_method'] = 'assume_inbound'
        metadata['confidence'] = 'low'
        logger.warning(f"Unable to determine direction, assuming inbound. Data keys: {list(message_data.keys())}")
        return MessageDirection.INBOUND
    
    def _extract_sender_info(self, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract sender information from message data in various formats
        """
        # UniPile webhook format
        if 'sender' in message_data:
            sender = message_data['sender']
            if isinstance(sender, dict):
                return sender
        
        # Alternative formats
        sender_info = {}
        
        # Check for direct phone/provider_id fields
        if 'from' in message_data:
            from_field = message_data['from']
            if isinstance(from_field, str):
                sender_info['provider_id'] = from_field
            elif isinstance(from_field, dict):
                sender_info.update(from_field)
        
        # Check for attendee information
        if 'attendee_id' in message_data:
            sender_info['attendee_id'] = message_data['attendee_id']
        
        if 'attendee_provider_id' in message_data:
            sender_info['provider_id'] = message_data['attendee_provider_id']
        
        return sender_info if sender_info else None
    
    def _extract_email_sender(self, message_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract email sender from message data
        """
        # Check from field
        from_field = message_data.get('from')
        if isinstance(from_field, dict):
            return from_field.get('email')
        elif isinstance(from_field, str):
            return from_field
        
        # Check sender field
        sender = message_data.get('sender')
        if isinstance(sender, dict):
            return sender.get('email')
        elif isinstance(sender, str):
            return sender
        
        return None
    
    def _clean_phone_number(self, phone: str) -> str:
        """
        Clean phone number for comparison by removing common formatting and WhatsApp JID suffixes
        """
        if not phone:
            return ""
        
        # Remove WhatsApp JID suffix first
        if '@s.whatsapp.net' in phone:
            phone = phone.split('@s.whatsapp.net')[0]
        elif '@g.us' in phone:
            # This is a group ID, not a phone number
            return ""
        
        # Remove common formatting characters
        cleaned = phone.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
        
        # Keep only digits
        cleaned = ''.join(c for c in cleaned if c.isdigit())
        
        return cleaned
    
    def get_detection_summary(self, connection: UserChannelConnection) -> Dict[str, Any]:
        """
        Get a summary of available detection data for this connection
        """
        summary = {
            'connection_id': str(connection.id),
            'channel_type': connection.channel_type,
            'account_id': connection.unipile_account_id,
            'detection_capabilities': []
        }
        
        if connection.channel_type == 'whatsapp':
            phone = connection.connection_config.get('phone_number')
            if phone:
                summary['detection_capabilities'].append(f'phone_number_matching ({phone})')
                summary['account_phone'] = phone
        
        elif connection.channel_type in ['gmail', 'outlook', 'email']:
            email = connection.user.email
            if email:
                summary['detection_capabilities'].append(f'email_matching ({email})')
                summary['account_email'] = email
        
        elif connection.channel_type == 'linkedin':
            profile_id = connection.provider_config.get('profile_id')
            if profile_id:
                summary['detection_capabilities'].append(f'profile_id_matching ({profile_id})')
                summary['account_profile_id'] = profile_id
        
        summary['detection_capabilities'].append('webhook_event_type')
        summary['detection_capabilities'].append('legacy_fallback_methods')
        
        return summary


# Global service instance
direction_detection_service = DirectionDetectionService()