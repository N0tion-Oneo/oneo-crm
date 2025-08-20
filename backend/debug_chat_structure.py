#!/usr/bin/env python3
"""
Debug script to see the actual structure of chat data from Unipile API
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

async def debug_chat_structure():
    """Debug the structure of chat data from Unipile API"""
    
    account_id = "mp9Gis3IRtuh9V5oSxZdSA"
    
    try:
        client = unipile_service.get_client()
        
        # Get chats from Unipile
        chats_data = await client.messaging.get_all_chats(
            account_id=account_id,
            limit=1,  # Just 1 conversation for analysis
            account_type='WHATSAPP'
        )
        
        chats = chats_data.get('items', [])
        logger.info(f"📨 Got {len(chats)} chats")
        
        for i, chat in enumerate(chats):
            if chat:
                logger.info(f"\n💬 Chat {i+1}:")
                logger.info(f"  - ID: {chat.get('id')}")
                logger.info(f"  - Name: {chat.get('name')}")
                logger.info(f"  - Provider ID: {chat.get('provider_id')}")
                logger.info(f"  - Attendee Provider ID: {chat.get('attendee_provider_id')}")
                logger.info(f"  - Type: {chat.get('type')}")
                logger.info(f"  - All keys: {list(chat.keys())}")
                
                # Show a sample of the raw data
                logger.info(f"\n📋 Raw chat data:")
                import json
                logger.info(json.dumps(chat, indent=2)[:500] + "...")
                
    except Exception as e:
        logger.error(f"Failed to debug chat structure: {e}")

if __name__ == "__main__":
    asyncio.run(debug_chat_structure())