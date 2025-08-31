#!/usr/bin/env python
"""
Script to fix message sender participants based on direction
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import Message, Participant
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_message_senders(schema_name='oneotalent'):
    """
    Fix message sender participants based on direction and metadata
    """
    with schema_context(schema_name):
        # Get messages with potentially wrong senders
        messages = Message.objects.filter(
            channel__channel_type__in=['whatsapp', 'linkedin']
        ).select_related('sender_participant', 'channel')[:100]
        
        fixed_count = 0
        
        for message in messages:
            metadata = message.metadata or {}
            is_sender = metadata.get('is_sender', 0)
            sender_attendee_id = metadata.get('sender_attendee_id')
            
            # Check if direction matches is_sender flag
            should_be_outbound = (is_sender == 1)
            is_outbound = (message.direction == 'outbound')
            
            if should_be_outbound != is_outbound:
                logger.info(f"Fixing direction for message {message.id}: {message.direction} -> {'outbound' if should_be_outbound else 'inbound'}")
                message.direction = 'outbound' if should_be_outbound else 'inbound'
                message.save(update_fields=['direction'])
                fixed_count += 1
            
            # Also check if sender_participant needs updating
            if sender_attendee_id and message.sender_participant:
                # Check if the current sender_participant matches the attendee_id
                current_provider_id = message.sender_participant.metadata.get('provider_id')
                if current_provider_id != sender_attendee_id:
                    # Try to find the correct participant
                    correct_participant = Participant.objects.filter(
                        metadata__provider_id=sender_attendee_id
                    ).first()
                    
                    if correct_participant and correct_participant != message.sender_participant:
                        logger.info(f"Fixing sender for message {message.id}: {message.sender_participant.name or 'Unknown'} -> {correct_participant.name or 'Unknown'}")
                        message.sender_participant = correct_participant
                        message.save(update_fields=['sender_participant'])
                        fixed_count += 1
        
        logger.info(f"Fixed {fixed_count} messages")

if __name__ == '__main__':
    schema = sys.argv[1] if len(sys.argv) > 1 else 'oneotalent'
    fix_message_senders(schema)