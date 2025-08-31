"""
Attendee Enricher - Enriches messages with attendee information

This module resolves sender_attendee_id to actual attendee information
for WhatsApp and LinkedIn messages.
"""
import logging
from typing import Dict, List, Any, Optional
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


class AttendeeEnricher:
    """Enriches messages with attendee information"""
    
    def __init__(self, unipile_client):
        """
        Initialize the enricher
        
        Args:
            unipile_client: UniPile client instance
        """
        self.unipile_client = unipile_client
        self._attendee_cache = {}  # Cache attendees by account_id
    
    def enrich_messages_with_attendees(
        self,
        messages: List[Dict[str, Any]],
        chat_data: Dict[str, Any],
        account_id: str,
        channel_type: str
    ) -> List[Dict[str, Any]]:
        """
        Enrich messages with attendee information
        
        Args:
            messages: List of raw message data
            chat_data: Chat/conversation data
            account_id: UniPile account ID
            channel_type: Type of channel (whatsapp, linkedin)
            
        Returns:
            Enriched messages with sender information
        """
        # Build attendee lookup map from chat data first
        attendee_map = {}
        
        # Check if chat_data has attendees
        chat_attendees = chat_data.get('attendees', [])
        for att in chat_attendees:
            if att.get('id'):
                attendee_map[att['id']] = att
        
        # Collect unique sender_attendee_ids that we don't have yet
        missing_attendee_ids = set()
        for msg in messages:
            sender_attendee_id = msg.get('sender_attendee_id')
            if sender_attendee_id and sender_attendee_id not in attendee_map:
                missing_attendee_ids.add(sender_attendee_id)
        
        # If we have missing attendees, try to fetch them specifically
        if missing_attendee_ids:
            logger.info(f"Need to fetch {len(missing_attendee_ids)} specific attendees")
            # For now, we'll use a simplified approach - just use what we have
            # In production, we'd fetch specific attendees by ID
        
        # Enrich each message
        enriched_messages = []
        for msg in messages:
            enriched_msg = msg.copy()
            
            # Get sender attendee ID
            sender_attendee_id = msg.get('sender_attendee_id')
            
            if sender_attendee_id and sender_attendee_id in attendee_map:
                attendee = attendee_map[sender_attendee_id]
                
                # Add sender information to message
                enriched_msg['sender'] = {
                    'id': attendee.get('id'),
                    'name': attendee.get('display_name', ''),
                    'provider_id': attendee.get('provider_id', ''),
                    'type': attendee.get('type', '')
                }
                
                # For WhatsApp, extract phone from provider_id
                if channel_type == 'whatsapp':
                    provider_id = attendee.get('provider_id', '')
                    if '@s.whatsapp.net' in provider_id:
                        phone = provider_id.replace('@s.whatsapp.net', '')
                        enriched_msg['sender']['phone'] = phone
                
                # For LinkedIn, store the provider_id as LinkedIn URN
                elif channel_type == 'linkedin':
                    provider_id = attendee.get('provider_id', '')
                    if provider_id:
                        enriched_msg['sender']['linkedin_urn'] = provider_id
            
            # Also set a simple from field for compatibility
            if enriched_msg.get('sender'):
                if channel_type == 'whatsapp' and enriched_msg['sender'].get('phone'):
                    enriched_msg['from'] = enriched_msg['sender']['phone']
                elif channel_type == 'linkedin' and enriched_msg['sender'].get('linkedin_urn'):
                    enriched_msg['from'] = enriched_msg['sender']['linkedin_urn']
                else:
                    enriched_msg['from'] = enriched_msg['sender'].get('provider_id', '')
                
                # Set sender_name for easy access
                enriched_msg['sender_name'] = enriched_msg['sender'].get('name', '')
            
            enriched_messages.append(enriched_msg)
        
        logger.info(
            f"Enriched {len(enriched_messages)} {channel_type} messages with attendee information"
        )
        
        return enriched_messages
    
    def _get_or_fetch_attendees(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Get attendees from cache or fetch from API
        
        Args:
            account_id: UniPile account ID
            
        Returns:
            List of attendee dictionaries
        """
        # Check cache
        if account_id in self._attendee_cache:
            return self._attendee_cache[account_id]
        
        # Fetch from API
        attendees = self._fetch_all_attendees(account_id)
        
        # Cache for future use
        self._attendee_cache[account_id] = attendees
        
        return attendees
    
    def _fetch_all_attendees(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Fetch all attendees for an account
        
        Args:
            account_id: UniPile account ID
            
        Returns:
            List of attendee dictionaries
        """
        try:
            logger.info(f"Fetching all attendees for account {account_id}")
            
            attendees = []
            cursor = None
            page = 1
            
            while True:
                # Fetch page of attendees
                response = async_to_sync(self.unipile_client.messaging.get_all_attendees)(
                    account_id=account_id,
                    cursor=cursor,
                    limit=100
                )
                
                if not response or 'items' not in response:
                    break
                
                batch = response.get('items', [])
                attendees.extend(batch)
                
                logger.debug(f"Page {page}: Got {len(batch)} attendees")
                
                # Check for more pages
                cursor = response.get('cursor')
                if not cursor:
                    break
                
                page += 1
            
            logger.info(f"Fetched {len(attendees)} attendees for account {account_id}")
            return attendees
            
        except Exception as e:
            logger.error(f"Error fetching attendees for account {account_id}: {e}")
            return []
    
    def clear_cache(self):
        """Clear the attendee cache"""
        self._attendee_cache.clear()
        logger.info("Cleared attendee cache")