"""
Message Enricher - Enriches messages with sender information

This module infers sender information from message data without
needing to fetch all attendees (which can be slow).
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class MessageEnricher:
    """Enriches messages with inferred sender information"""
    
    def enrich_messages(
        self,
        messages: List[Dict[str, Any]],
        channel_type: str,
        account_identifier: Optional[str] = None,
        attendee_id_to_info: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Enrich messages with inferred sender information
        
        Args:
            messages: List of raw message data
            channel_type: Type of channel (whatsapp, linkedin)
            account_identifier: Account owner's identifier for direction detection
            
        Returns:
            Enriched messages with sender information
        """
        # Log attendee_id_to_info mapping for debugging
        if attendee_id_to_info:
            logger.info(f"MessageEnricher: Received {len(attendee_id_to_info)} attendee mappings for {channel_type}")
            # Log first 5 keys to see what format they are in
            sample_keys = list(attendee_id_to_info.keys())[:5]
            logger.info(f"MessageEnricher: Sample attendee_id_to_info keys: {sample_keys}")
        else:
            logger.info(f"MessageEnricher: No attendee_id_to_info provided for {channel_type}")
        
        enriched_messages = []
        
        # Track unique sender IDs we see in messages
        unique_sender_attendee_ids = set()
        unique_sender_ids = set()
        
        for msg in messages:
            enriched_msg = msg.copy()
            
            # Get basic message info
            provider_id = msg.get('provider_id', '')  # This is the message ID
            is_sender = msg.get('is_sender', 0)
            sender_attendee_id = msg.get('sender_attendee_id', '')  # This is UniPile's internal ID
            sender_id = msg.get('sender_id', '')  # This is the actual provider ID (e.g., phone@s.whatsapp.net)
            
            # Track unique sender IDs for debugging
            if sender_attendee_id:
                unique_sender_attendee_ids.add(sender_attendee_id)
            if sender_id:
                unique_sender_ids.add(sender_id)
            
            # Build sender info based on channel type
            sender_info = {}
            
            if channel_type == 'whatsapp':
                # For WhatsApp, infer phone from various sources
                if is_sender == 1 and account_identifier:
                    # Message is from account owner
                    if '@s.whatsapp.net' in account_identifier:
                        phone = account_identifier.replace('@s.whatsapp.net', '')
                    else:
                        phone = account_identifier
                    # Look up name from attendee info if available
                    name = ''
                    if attendee_id_to_info and sender_attendee_id in attendee_id_to_info:
                        name = attendee_id_to_info[sender_attendee_id].get('name', '')
                    
                    sender_info = {
                        'phone': phone,
                        'name': name,  # Use pre-fetched name
                        'provider_id': sender_attendee_id,  # Use attendee ID, not message ID
                        'is_account_owner': True
                    }
                else:
                    # Message is from other party
                    # For WhatsApp, use sender_id (provider ID) to look up name
                    name = ''
                    phone = ''
                    
                    # Extract phone from sender_id if available
                    if sender_id and '@s.whatsapp.net' in sender_id:
                        phone = sender_id.replace('@s.whatsapp.net', '')
                        
                        # Look up name using phone or full sender_id
                        if attendee_id_to_info:
                            # Try phone number first
                            if phone in attendee_id_to_info:
                                name = attendee_id_to_info[phone].get('name', '')
                                logger.info(f"MessageEnricher: Found name '{name}' for phone '{phone}'")
                            # Try full sender_id
                            elif sender_id in attendee_id_to_info:
                                name = attendee_id_to_info[sender_id].get('name', '')
                                logger.info(f"MessageEnricher: Found name '{name}' for sender_id '{sender_id}'")
                            # Also try the attendee ID as fallback
                            elif sender_attendee_id in attendee_id_to_info:
                                attendee_info = attendee_id_to_info[sender_attendee_id]
                                name = attendee_info.get('name', '')
                                logger.info(f"MessageEnricher: Found name '{name}' for attendee_id '{sender_attendee_id}'")
                            else:
                                logger.debug(f"MessageEnricher: Could not find name for phone '{phone}' or sender_id '{sender_id}'")
                    
                    sender_info = {
                        'phone': phone,  # Use extracted phone from attendee info
                        'name': name,    # Use pre-fetched name
                        'provider_id': sender_attendee_id,  # Use attendee ID for consistency
                        'is_account_owner': False
                    }
                
                # Add phone-specific enrichment
                enriched_msg['from'] = sender_info.get('phone', provider_id)
                
            elif channel_type == 'linkedin':
                # For LinkedIn, we may need to use sender_id or other fields
                if is_sender == 1 and account_identifier:
                    # Message is from account owner
                    # Look up name from attendee info if available
                    name = ''
                    if attendee_id_to_info:
                        # Try sender_id first if available
                        if sender_id and sender_id in attendee_id_to_info:
                            name = attendee_id_to_info[sender_id].get('name', '')
                        # Fall back to attendee ID
                        elif sender_attendee_id in attendee_id_to_info:
                            name = attendee_id_to_info[sender_attendee_id].get('name', '')
                    
                    sender_info = {
                        'linkedin_urn': account_identifier,
                        'name': name,  # Use pre-fetched name
                        'provider_id': sender_id or sender_attendee_id,  # Prefer sender_id
                        'is_account_owner': True
                    }
                else:
                    # Message is from other party
                    # Look up name and LinkedIn URN from attendee info if available
                    name = ''
                    linkedin_urn = sender_id or ''  # Use sender_id as the URN if available
                    
                    if attendee_id_to_info:
                        # Try sender_id first
                        if sender_id and sender_id in attendee_id_to_info:
                            attendee_info = attendee_id_to_info[sender_id]
                            name = attendee_info.get('name', '')
                            linkedin_urn = sender_id
                        # Fall back to attendee ID
                        elif sender_attendee_id in attendee_id_to_info:
                            attendee_info = attendee_id_to_info[sender_attendee_id]
                            name = attendee_info.get('name', '')
                            # The provider_id for LinkedIn is the URN
                            linkedin_urn = attendee_info.get('provider_id', '') or linkedin_urn
                    
                    sender_info = {
                        'linkedin_urn': linkedin_urn,  # Use URN from attendee info
                        'name': name,  # Use pre-fetched name
                        'provider_id': sender_id or sender_attendee_id,  # Prefer sender_id
                        'is_account_owner': False
                    }
                
                # Don't set 'from' field for LinkedIn to avoid confusion with email
                # The participant will be identified by provider_id
            
            # Add sender info to message
            if sender_info:
                enriched_msg['sender'] = sender_info
                enriched_msg['sender_name'] = sender_info.get('name', '')
                enriched_msg['channel_type'] = channel_type  # Store channel type for participant creation
                
                # Store provider_id in metadata for participant creation
                if not enriched_msg.get('provider_id'):
                    enriched_msg['provider_id'] = sender_info.get('provider_id', provider_id)
            
            enriched_messages.append(enriched_msg)
        
        # Log summary of sender IDs we saw vs what we had in mapping
        if unique_sender_ids or unique_sender_attendee_ids:
            logger.info(f"MessageEnricher: Saw {len(unique_sender_ids)} unique sender_ids (provider IDs) in messages")
            if unique_sender_ids:
                logger.info(f"MessageEnricher: Sample sender_ids: {list(unique_sender_ids)[:5]}")
            
            logger.info(f"MessageEnricher: Saw {len(unique_sender_attendee_ids)} unique sender_attendee_ids (internal IDs) in messages")
            if unique_sender_attendee_ids:
                logger.info(f"MessageEnricher: Sample sender_attendee_ids: {list(unique_sender_attendee_ids)[:5]}")
            
            # Check how many we could match
            if attendee_id_to_info:
                # Check sender_ids (these should match better)
                matched_sender_ids = sum(1 for sid in unique_sender_ids if sid in attendee_id_to_info)
                # Also check if phone numbers extracted from sender_ids match
                matched_phones = 0
                for sid in unique_sender_ids:
                    if '@s.whatsapp.net' in sid:
                        phone = sid.replace('@s.whatsapp.net', '')
                        if phone in attendee_id_to_info:
                            matched_phones += 1
                
                logger.info(f"MessageEnricher: Matched {matched_sender_ids}/{len(unique_sender_ids)} sender_ids directly")
                logger.info(f"MessageEnricher: Matched {matched_phones}/{len(unique_sender_ids)} phone numbers from sender_ids")
        
        logger.info(
            f"Enriched {len(enriched_messages)} {channel_type} messages with inferred sender info"
        )
        
        return enriched_messages