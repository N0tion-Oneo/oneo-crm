#!/usr/bin/env python
"""
Script to enrich existing messages with account owner names
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection
from django_tenants.utils import schema_context
from communications.models import Message, Channel, UserChannelConnection
from communications.utils.account_utils import get_account_owner_name
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def enrich_messages_with_names(schema_name=None):
    """Enrich all messages with account owner and contact names"""
    
    if schema_name:
        schemas = [schema_name]
    else:
        # Get all tenant schemas
        cursor = connection.cursor()
        cursor.execute("SELECT schema_name FROM public.tenants_domain")
        results = cursor.fetchall()
        schemas = [r[0] for r in results if r[0] != 'public']
    
    for schema in schemas:
        logger.info(f"\nProcessing schema: {schema}")
        
        with schema_context(schema):
            # Get all messages
            messages = Message.objects.select_related('channel', 'conversation').all()
            total = messages.count()
            logger.info(f"Found {total} messages to process")
            
            updated_count = 0
            
            for i, message in enumerate(messages):
                if i % 100 == 0:
                    logger.info(f"Processing message {i}/{total}")
                
                # Initialize metadata if needed
                if not message.metadata:
                    message.metadata = {}
                
                updated = False
                
                # For outbound messages, add account owner name
                if message.direction == 'outbound' and message.channel:
                    account_owner = get_account_owner_name(channel=message.channel)
                    if account_owner and account_owner != 'Unknown Account':
                        if message.metadata.get('account_owner_name') != account_owner:
                            message.metadata['account_owner_name'] = account_owner
                            updated = True
                            logger.debug(f"Added account owner: {account_owner} to message {message.id}")
                
                # For WhatsApp/LinkedIn messages, try to extract contact names from metadata
                if message.channel and message.channel.channel_type in ['whatsapp', 'linkedin']:
                    # Check if we have raw webhook data with contact info
                    if message.metadata.get('raw_webhook_data'):
                        raw_data = message.metadata['raw_webhook_data']
                        
                        # For WhatsApp
                        if message.channel.channel_type == 'whatsapp':
                            from communications.utils.phone_extractor import extract_whatsapp_contact_name
                            contact_name = extract_whatsapp_contact_name(raw_data)
                            if contact_name and not message.metadata.get('contact_name'):
                                message.metadata['contact_name'] = contact_name
                                updated = True
                                logger.debug(f"Added WhatsApp contact: {contact_name} to message {message.id}")
                        
                        # For LinkedIn
                        elif message.channel.channel_type == 'linkedin':
                            # Extract LinkedIn contact name from raw data
                            sender_data = raw_data.get('sender', {})
                            if isinstance(sender_data, dict):
                                contact_name = sender_data.get('name', '')
                                if contact_name and not message.metadata.get('contact_name'):
                                    message.metadata['contact_name'] = contact_name
                                    updated = True
                                    logger.debug(f"Added LinkedIn contact: {contact_name} to message {message.id}")
                
                # For email messages, extract names from from/to fields
                if message.channel and message.channel.channel_type in ['email', 'gmail', 'outlook']:
                    # Extract sender name from 'from' field
                    from_data = message.metadata.get('from')
                    if isinstance(from_data, dict) and from_data.get('name'):
                        if not message.metadata.get('sender_name'):
                            message.metadata['sender_name'] = from_data['name']
                            updated = True
                    
                    # Extract recipient names from 'to' field
                    to_data = message.metadata.get('to')
                    if isinstance(to_data, list) and to_data:
                        recipient_names = []
                        for recipient in to_data:
                            if isinstance(recipient, dict) and recipient.get('name'):
                                recipient_names.append(recipient['name'])
                        if recipient_names and not message.metadata.get('recipient_names'):
                            message.metadata['recipient_names'] = recipient_names
                            updated = True
                
                # Save if updated
                if updated:
                    message.save(update_fields=['metadata'])
                    updated_count += 1
            
            logger.info(f"Updated {updated_count} messages in schema {schema}")
    
    logger.info("\nEnrichment complete!")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enrich messages with account owner names')
    parser.add_argument('--schema', help='Specific schema to process')
    args = parser.parse_args()
    
    enrich_messages_with_names(args.schema)


if __name__ == '__main__':
    main()