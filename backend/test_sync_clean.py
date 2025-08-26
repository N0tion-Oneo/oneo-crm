#!/usr/bin/env python3
"""
Test WhatsApp sync with WebSocket broadcasting
"""
import os
import sys
import django
import asyncio
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Configure logging to see debug messages
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from django_tenants.utils import schema_context
from communications.channels.whatsapp.sync.tasks import sync_account_comprehensive_background
from communications.models import Channel, UserChannelConnection
from tenants.models import User

def test_sync():
    """Test sync execution with broadcasting"""
    
    # Use demo tenant
    with schema_context('demo'):
        # Get channel
        channel = Channel.objects.filter(channel_type='whatsapp').first()
        if not channel:
            logger.error("No WhatsApp channel found")
            return
            
        logger.info(f"Found channel: {channel.id}")
        
        # Get connection
        connection = UserChannelConnection.objects.filter(
            channel_type='whatsapp',
            is_active=True
        ).first()
        
        if not connection:
            logger.error("No active connection found")
            return
            
        logger.info(f"Found connection: {connection.unipile_account_id}")
        
        # Get user
        user = User.objects.first()
        if not user:
            logger.error("No user found")
            return
            
        logger.info(f"Found user: {user.email}")
        
        # Trigger sync
        logger.info("Starting sync task...")
        result = sync_account_comprehensive_background.apply(
            args=[
                str(channel.id),
                str(user.id)
            ],
            kwargs={
                'sync_options': {
                    'max_conversations': 3,  # Small number for testing
                    'max_messages_per_chat': 5,
                    'days_back': 0
                },
                'tenant_schema': 'demo'
            }
        )
        
        logger.info(f"Task ID: {result.id}")
        logger.info("Waiting for result...")
        
        # Wait for result (with timeout)
        try:
            final_result = result.get(timeout=60)
            logger.info(f"Sync completed: {final_result}")
        except Exception as e:
            logger.error(f"Sync failed: {e}")

if __name__ == '__main__':
    test_sync()