#!/usr/bin/env python
"""
Script to fix message names by using the actual user's name from the Django User model
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
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_message_user_names(schema_name=None):
    """Fix all messages to use actual user names from the Django User model"""
    
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
            # Get all UserChannelConnections with their users
            connections_map = {}
            for conn in UserChannelConnection.objects.select_related('user').all():
                if conn.unipile_account_id:
                    user_name = None
                    if conn.user:
                        user_name = conn.user.get_full_name() or conn.user.username
                    connections_map[conn.unipile_account_id] = {
                        'user_name': user_name,
                        'user_email': conn.user.email if conn.user else None,
                        'user_id': conn.user.id if conn.user else None
                    }
                    logger.info(f"Found connection: {conn.unipile_account_id} -> User: {user_name}")
            
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
                
                # Get the user info for this channel
                user_info = None
                if message.channel and message.channel.unipile_account_id:
                    user_info = connections_map.get(message.channel.unipile_account_id)
                
                if user_info and user_info['user_name']:
                    # For outbound messages, update with user's name
                    if message.direction == 'outbound':
                        if message.metadata.get('account_owner_name') != user_info['user_name']:
                            message.metadata['account_owner_name'] = user_info['user_name']
                            message.metadata['user_name'] = user_info['user_name']
                            message.metadata['user_id'] = user_info['user_id']
                            updated = True
                            logger.debug(f"Updated outbound message {message.id} with user: {user_info['user_name']}")
                    
                    # For inbound messages, we might want to store this for reference
                    else:
                        # Store the account user for inbound messages too (for "to" field)
                        if not message.metadata.get('recipient_user_name'):
                            message.metadata['recipient_user_name'] = user_info['user_name']
                            message.metadata['recipient_user_id'] = user_info['user_id']
                            updated = True
                
                # For WhatsApp/LinkedIn messages, ensure contact names are preserved
                if message.channel and message.channel.channel_type in ['whatsapp', 'linkedin']:
                    # Check if we have raw webhook data with contact info
                    if message.metadata.get('raw_webhook_data'):
                        raw_data = message.metadata['raw_webhook_data']
                        
                        # For WhatsApp
                        if message.channel.channel_type == 'whatsapp':
                            from communications.utils.phone_extractor import extract_whatsapp_contact_name
                            contact_name = extract_whatsapp_contact_name(raw_data)
                            if contact_name and contact_name != message.metadata.get('contact_name'):
                                message.metadata['contact_name'] = contact_name
                                updated = True
                                logger.debug(f"Updated WhatsApp contact: {contact_name} for message {message.id}")
                        
                        # For LinkedIn
                        elif message.channel.channel_type == 'linkedin':
                            # Extract LinkedIn contact name from raw data
                            sender_data = raw_data.get('sender', {})
                            if isinstance(sender_data, dict):
                                contact_name = sender_data.get('name', '')
                                if contact_name and contact_name != message.metadata.get('contact_name'):
                                    message.metadata['contact_name'] = contact_name
                                    updated = True
                                    logger.debug(f"Updated LinkedIn contact: {contact_name} for message {message.id}")
                
                # Save if updated
                if updated:
                    message.save(update_fields=['metadata'])
                    updated_count += 1
            
            logger.info(f"Updated {updated_count} messages in schema {schema}")
    
    logger.info("\nUser name fix complete!")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix messages to use actual user names')
    parser.add_argument('--schema', help='Specific schema to process')
    args = parser.parse_args()
    
    fix_message_user_names(args.schema)


if __name__ == '__main__':
    main()