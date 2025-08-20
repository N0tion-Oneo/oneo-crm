#!/usr/bin/env python3
"""
Debug script to check message direction mapping
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')

import django
django.setup()

from communications.unipile_sdk import unipile_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_message_direction():
    """Debug message direction mapping from Unipile API"""
    
    account_id = "mp9Gis3IRtuh9V5oSxZdSA"
    chat_id = "Koj4tacYXrii5kAkW86dNw"  # From the logs
    
    try:
        client = unipile_service.get_client()
        
        # Get messages for this chat
        messages_data = await client.messaging.get_all_messages(
            chat_id=chat_id,
            limit=3
        )
        
        messages = messages_data.get('items', [])
        logger.info(f"📨 Got {len(messages)} messages")
        
        for i, msg in enumerate(messages):
            if msg:
                logger.info(f"\n📨 Message {i+1}:")
                logger.info(f"  - ID: {msg.get('id')}")
                logger.info(f"  - Text: {msg.get('text', '')[:50]}...")
                logger.info(f"  - from_me: {msg.get('from_me')}")
                logger.info(f"  - direction: {msg.get('direction')}")
                logger.info(f"  - from: {msg.get('from')}")
                logger.info(f"  - to: {msg.get('to')}")
                logger.info(f"  - All keys: {list(msg.keys())}")
                
    except Exception as e:
        logger.error(f"Failed to debug message direction: {e}")

if __name__ == "__main__":
    asyncio.run(debug_message_direction())