#!/usr/bin/env python
"""
Script to enrich messages with contact names from raw webhook data
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection
from django_tenants.utils import schema_context
from communications.models import Message
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def enrich_contact_names(schema_name=None):
    """Enrich messages with contact names from raw webhook data"""
    
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
            # Get all messages with raw webhook data
            messages = Message.objects.filter(
                metadata__raw_webhook_data__isnull=False
            ).select_related('channel')
            
            total = messages.count()
            logger.info(f"Found {total} messages with raw webhook data")
            
            updated_count = 0
            
            for i, message in enumerate(messages):
                if i % 100 == 0:
                    logger.info(f"Processing message {i}/{total}")
                
                updated = False
                raw_data = message.metadata.get('raw_webhook_data', {})
                
                # Extract contact name based on channel type
                if message.channel and message.channel.channel_type == 'whatsapp':
                    from communications.utils.phone_extractor import extract_whatsapp_contact_name
                    
                    contact_name = extract_whatsapp_contact_name(raw_data)
                    if contact_name and contact_name != message.metadata.get('contact_name'):
                        message.metadata['contact_name'] = contact_name
                        updated = True
                        logger.debug(f"Added WhatsApp contact name: {contact_name} to message {message.id}")
                
                elif message.channel and message.channel.channel_type == 'linkedin':
                    # Extract LinkedIn contact name
                    if message.direction == 'inbound':
                        # For inbound, the sender is the contact
                        sender_data = raw_data.get('sender', {})
                        if isinstance(sender_data, dict):
                            contact_name = sender_data.get('name', '')
                            if contact_name and contact_name != message.metadata.get('contact_name'):
                                message.metadata['contact_name'] = contact_name
                                updated = True
                                logger.debug(f"Added LinkedIn contact name: {contact_name} to message {message.id}")
                    else:
                        # For outbound, need to extract recipient info
                        # This might be in 'to' or 'recipients' field
                        to_data = raw_data.get('to', {})
                        if isinstance(to_data, dict):
                            contact_name = to_data.get('name', '')
                            if contact_name and contact_name != message.metadata.get('contact_name'):
                                message.metadata['contact_name'] = contact_name
                                updated = True
                
                # Save if updated
                if updated:
                    message.save(update_fields=['metadata'])
                    updated_count += 1
            
            logger.info(f"Updated {updated_count} messages with contact names in schema {schema}")
    
    logger.info("\nContact name enrichment complete!")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enrich messages with contact names')
    parser.add_argument('--schema', help='Specific schema to process')
    args = parser.parse_args()
    
    enrich_contact_names(args.schema)


if __name__ == '__main__':
    main()