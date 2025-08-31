#!/usr/bin/env python
"""
Script to fix ALL message directions and metadata based on UniPile data
This script re-syncs metadata for all existing messages
"""
import os
import sys
import django
import logging
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from django.utils import timezone
from communications.models import Message, Participant, UserChannelConnection
from communications.unipile.clients.messaging import UnipileMessagingClient
from communications.unipile.clients.email import UnipileEmailClient
from communications.record_communications.unipile_integration.data_transformer import DataTransformer
from communications.record_communications.unipile_integration.message_enricher import MessageEnricher
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_all_message_directions(schema_name='oneotalent', limit=None):
    """
    Re-fetch message data from UniPile and update metadata for proper direction
    """
    with schema_context(schema_name):
        # Get UniPile connections
        connections = UserChannelConnection.objects.filter(
            is_active=True,
            channel_type__in=['whatsapp', 'linkedin', 'email']
        )
        
        if not connections:
            logger.warning("No active UniPile connections found")
            return
        
        data_transformer = DataTransformer()
        message_enricher = MessageEnricher()
        
        total_fixed = 0
        
        for connection in connections:
            logger.info(f"Processing connection: {connection.account_name} ({connection.channel_type})")
            
            # Get account provider ID from connection
            account_provider_id = (
                connection.provider_config.get('provider_id') or 
                connection.provider_config.get('account_provider_id') or
                connection.unipile_account_id
            )
            
            logger.info(f"Account provider ID: {account_provider_id}")
            
            # Get messages for this channel
            channel = connection.channel
            messages = Message.objects.filter(
                channel=channel
            ).select_related('sender_participant')
            
            if limit:
                messages = messages[:limit]
            
            fixed_count = 0
            
            for message in messages:
                try:
                    metadata = message.metadata or {}
                    external_id = message.external_message_id
                    
                    if not external_id:
                        continue
                    
                    # Check if we have is_sender flag
                    is_sender = metadata.get('is_sender')
                    
                    # If we don't have is_sender, try to determine from other data
                    if is_sender is None:
                        # Try to get from unipile_data if stored
                        unipile_data = metadata.get('unipile_data', {})
                        is_sender = unipile_data.get('is_sender')
                        
                        if is_sender is not None:
                            # Store it directly in metadata
                            metadata['is_sender'] = is_sender
                            metadata['sender_attendee_id'] = unipile_data.get('sender_attendee_id')
                    
                    # Determine correct direction
                    if is_sender == 1:
                        correct_direction = 'outbound'
                    elif is_sender == 0:
                        correct_direction = 'inbound'
                    else:
                        # Fallback: check sender against account
                        if message.sender_participant:
                            sender_metadata = message.sender_participant.metadata or {}
                            sender_provider_id = sender_metadata.get('provider_id')
                            
                            if sender_provider_id == account_provider_id:
                                correct_direction = 'outbound'
                                is_sender = 1
                            else:
                                correct_direction = 'inbound'
                                is_sender = 0
                        else:
                            # Can't determine, skip
                            continue
                    
                    # Check if update needed
                    update_needed = False
                    
                    if message.direction != correct_direction:
                        logger.info(f"Fixing direction for message {message.id}: {message.direction} -> {correct_direction}")
                        message.direction = correct_direction
                        update_needed = True
                    
                    if metadata.get('is_sender') != is_sender:
                        metadata['is_sender'] = is_sender
                        message.metadata = metadata
                        update_needed = True
                    
                    # Also ensure sender_participant is correct if we have metadata
                    sender_attendee_id = metadata.get('sender_attendee_id')
                    if sender_attendee_id and message.sender_participant:
                        current_provider_id = message.sender_participant.metadata.get('provider_id', '')
                        if current_provider_id != sender_attendee_id:
                            # Try to find correct participant
                            correct_participant = Participant.objects.filter(
                                metadata__provider_id=sender_attendee_id
                            ).first()
                            
                            if correct_participant and correct_participant != message.sender_participant:
                                logger.info(f"Fixing sender for message {message.id}")
                                message.sender_participant = correct_participant
                                update_needed = True
                    
                    if update_needed:
                        message.save(update_fields=['direction', 'metadata', 'sender_participant'])
                        fixed_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing message {message.id}: {e}")
                    continue
            
            logger.info(f"Fixed {fixed_count} messages for connection {connection.account_name}")
            total_fixed += fixed_count
        
        logger.info(f"Total messages fixed: {total_fixed}")

if __name__ == '__main__':
    schema = sys.argv[1] if len(sys.argv) > 1 else 'oneotalent'
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    fix_all_message_directions(schema, limit)