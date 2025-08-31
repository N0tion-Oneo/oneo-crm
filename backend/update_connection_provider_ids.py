#!/usr/bin/env python
"""
Script to update UserChannelConnection provider_config with provider_id
This ensures the account owner's provider ID is stored for proper message direction
"""
import os
import sys
import django
import logging

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import UserChannelConnection
from communications.unipile.clients.users import UnipileUsersClient
from communications.unipile.core.client import UnipileClient
from communications.unipile.services.service import UnipileService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_connection_provider_ids(schema_name='oneotalent'):
    """
    Update all active connections with their provider IDs from UniPile
    """
    with schema_context(schema_name):
        # Get UniPile service
        unipile_service = UnipileService()
        client = unipile_service.get_client()
        
        if not client:
            logger.error("Could not initialize UniPile client")
            return
        
        users_client = UnipileUsersClient(client)
        
        # Get all active connections
        connections = UserChannelConnection.objects.filter(
            is_active=True,
            channel_type__in=['whatsapp', 'linkedin']
        )
        
        updated_count = 0
        
        for connection in connections:
            try:
                if not connection.unipile_account_id:
                    logger.warning(f"Skipping connection {connection.account_name} - no unipile_account_id")
                    continue
                
                logger.info(f"Processing connection: {connection.account_name} ({connection.channel_type})")
                
                # Get account info from UniPile
                account_info = users_client.get_account_info(connection.unipile_account_id)
                
                if account_info and account_info.get('success'):
                    account_data = account_info.get('data', {})
                    
                    # Extract provider_id based on channel type
                    provider_id = None
                    
                    if connection.channel_type == 'whatsapp':
                        # For WhatsApp, provider_id is usually phone@s.whatsapp.net
                        # Try to get from account data
                        phone = account_data.get('phone_number') or account_data.get('phone')
                        if phone:
                            # Ensure it's in the right format
                            if '@' not in phone:
                                provider_id = f"{phone}@s.whatsapp.net"
                            else:
                                provider_id = phone
                    
                    elif connection.channel_type == 'linkedin':
                        # For LinkedIn, provider_id is the LinkedIn URN
                        provider_id = account_data.get('provider_id') or account_data.get('linkedin_id')
                    
                    if provider_id:
                        # Update provider_config
                        if not connection.provider_config:
                            connection.provider_config = {}
                        
                        connection.provider_config['provider_id'] = provider_id
                        connection.provider_config['account_provider_id'] = provider_id  # Also store as account_provider_id
                        
                        # Store additional account info
                        if connection.channel_type == 'whatsapp':
                            connection.provider_config['phone_number'] = phone
                        
                        connection.save(update_fields=['provider_config'])
                        logger.info(f"Updated {connection.account_name} with provider_id: {provider_id}")
                        updated_count += 1
                    else:
                        logger.warning(f"Could not extract provider_id for {connection.account_name}")
                        logger.debug(f"Account data: {account_data}")
                else:
                    logger.error(f"Failed to get account info for {connection.unipile_account_id}")
                    
            except Exception as e:
                logger.error(f"Error updating connection {connection.account_name}: {e}")
                continue
        
        logger.info(f"Updated {updated_count} connections with provider IDs")

if __name__ == '__main__':
    schema = sys.argv[1] if len(sys.argv) > 1 else 'oneotalent'
    update_connection_provider_ids(schema)