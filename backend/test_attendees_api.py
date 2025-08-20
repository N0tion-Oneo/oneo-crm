#!/usr/bin/env python3
"""
Test script to debug the attendees API call
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

async def test_attendees_api():
    """Test the attendees API call to debug the 400 error"""
    
    # Use the same account ID that's failing
    account_id = "mp9Gis3IRtuh9V5oSxZdSA"
    
    try:
        client = unipile_service.get_client()
        logger.info(f"✅ Got Unipile client")
        
        # Test the exact call that's failing
        logger.info(f"🔄 Testing chat_attendees API call with account_id: {account_id}")
        
        # Try with minimal parameters first
        logger.info(f"📋 Test 1: Minimal parameters")
        try:
            response = await client.messaging.get_all_attendees(
                account_id=account_id
            )
            logger.info(f"✅ Success with minimal params: {response}")
            
        except Exception as e:
            logger.error(f"❌ Failed with minimal params: {e}")
            
            # Try without account_id
            logger.info(f"📋 Test 2: Without account_id")
            try:
                response = await client.messaging.get_all_attendees()
                logger.info(f"✅ Success without account_id: {response}")
                
            except Exception as e2:
                logger.error(f"❌ Failed without account_id: {e2}")
                
                # Try with limit only
                logger.info(f"📋 Test 3: With limit only")
                try:
                    response = await client.messaging.get_all_attendees(limit=10)
                    logger.info(f"✅ Success with limit only: {response}")
                    
                except Exception as e3:
                    logger.error(f"❌ Failed with limit only: {e3}")
                    
                    # Try direct API call
                    logger.info(f"📋 Test 4: Direct API call")
                    try:
                        response = await client._make_request('GET', 'chat_attendees', params={'limit': 10})
                        logger.info(f"✅ Success with direct call: {response}")
                        
                    except Exception as e4:
                        logger.error(f"❌ Failed with direct call: {e4}")
                        
    except Exception as e:
        logger.error(f"Failed to test attendees API: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_attendees_api())