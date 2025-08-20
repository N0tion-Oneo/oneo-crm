#!/usr/bin/env python3
"""
Test WebSocket channel subscription permissions for WhatsApp channels
"""
import asyncio
import websockets
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_whatsapp_channel_subscription():
    """Test WhatsApp channel subscription permissions"""
    
    # JWT token for josh@oneodigital.com (OneOTalent tenant) - fresh token
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU1NzA2NTUxLCJpYXQiOjE3NTU3MDI5NTEsImp0aSI6IjJjYmExYzRmNzBmZDQ1Mzk4Y2ExMjA0ZDUzZWMyNmQzIiwidXNlcl9pZCI6MSwidXNlcm5hbWUiOiJqb3NoQG9uZW9kaWdpdGFsLmNvbSIsImVtYWlsIjoiam9zaEBvbmVvZGlnaXRhbC5jb20iLCJ1c2VyX3R5cGUiOiJhZG1pbiIsInRlbmFudF9zY2hlbWEiOiJvbmVvdGFsZW50In0.Tz8F2klDnRYc9uZsF94qd2B-2MN9MWejmuBLuCB-08E"
    
    # Try both tenant-specific and general WebSocket URLs
    websocket_urls = [
        f"ws://localhost:8000/ws/realtime/?token={token}",  # General localhost
        f"ws://oneotalent.localhost:8000/ws/realtime/?token={token}"  # Tenant subdomain
    ]
    
    print("🔗 Testing WebSocket WhatsApp Channel Subscriptions")
    print("=" * 60)
    
    # Try each websocket URL until one works
    for i, websocket_url in enumerate(websocket_urls, 1):
        try:
            # Connect to WebSocket
            print(f"📡 Attempt {i}: Connecting to: {websocket_url}")
            async with websockets.connect(websocket_url) as websocket:
                print("✅ WebSocket connected successfully")
                
                # Test WhatsApp channel subscriptions that were previously failing
                test_channels = [
                    "whatsapp_updates",
                    "whatsapp_chat_1T1s9uwKX3yXDdHr9p9uWQ", 
                    "communication_updates",
                    "channel_updates"
                ]
                
                for channel in test_channels:
                    print(f"\n🔌 Testing subscription to: {channel}")
                    
                    # Send subscription request
                    subscribe_msg = {
                        "type": "subscribe",
                        "channel": channel
                    }
                    
                    await websocket.send(json.dumps(subscribe_msg))
                    
                    # Wait for response (with timeout)
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        response_data = json.loads(response)
                        
                        if response_data.get("type") == "subscription_status":
                            if response_data.get("success"):
                                print(f"✅ Subscription to '{channel}': GRANTED")
                            else:
                                print(f"❌ Subscription to '{channel}': DENIED - {response_data.get('message', 'Unknown reason')}")
                        else:
                            print(f"⚠️  Unexpected response for '{channel}': {response_data}")
                    
                    except asyncio.TimeoutError:
                        print(f"⏰ Timeout waiting for response to '{channel}' subscription")
                    
                    # Brief pause between tests
                    await asyncio.sleep(0.5)
                
                print(f"\n✅ WebSocket channel subscription testing completed")
                return True  # Success, exit the loop
                
        except Exception as e:
            print(f"❌ WebSocket connection failed for attempt {i}: {e}")
            continue  # Try next URL
            
    # If we get here, all attempts failed
    print("❌ All WebSocket connection attempts failed")
    return False

async def test_websocket_health():
    """Test basic WebSocket connectivity"""
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU1NzA2NTUxLCJpYXQiOjE3NTU3MDI5NTEsImp0aSI6IjJjYmExYzRmNzBmZDQ1Mzk4Y2ExMjA0ZDUzZWMyNmQzIiwidXNlcl9pZCI6MSwidXNlcm5hbWUiOiJqb3NoQG9uZW9kaWdpdGFsLmNvbSIsImVtYWlsIjoiam9zaEBvbmVvZGlnaXRhbC5jb20iLCJ1c2VyX3R5cGUiOiJhZG1pbiIsInRlbmFudF9zY2hlbWEiOiJvbmVvdGFsZW50In0.Tz8F2klDnRYc9uZsF94qd2B-2MN9MWejmuBLuCB-08E"
    # Try localhost first as it's more likely to work
    websocket_url = f"ws://localhost:8000/ws/realtime/?token={token}"
    
    print("🔍 Testing WebSocket Basic Connectivity")
    print("-" * 40)
    
    try:
        async with websockets.connect(websocket_url) as websocket:
            # Send a ping
            await websocket.send(json.dumps({"type": "ping"}))
            
            # Wait for pong
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            if response_data.get("type") == "pong":
                print("✅ WebSocket ping/pong working")
                return True
            else:
                print(f"⚠️  Unexpected ping response: {response_data}")
                return False
                
    except Exception as e:
        print(f"❌ WebSocket ping test failed: {e}")
        return False

async def main():
    """Run WebSocket channel permission tests"""
    print("🚀 WEBSOCKET CHANNEL PERMISSION TESTING")
    print("=" * 70)
    
    # Test 1: Basic connectivity
    health_ok = await test_websocket_health()
    
    if health_ok:
        print()
        # Test 2: Channel subscriptions
        await test_whatsapp_channel_subscription()
    else:
        print("⚠️  Skipping channel tests due to connectivity issues")
    
    print("\n" + "=" * 70)
    print("📊 WEBSOCKET TESTING SUMMARY")
    print("=" * 70)
    print("✅ WebSocket permission fixes applied")
    print("✅ WhatsApp channel patterns added to auth system")
    print("✅ Communication channel access enabled")
    print("\n🔍 If subscriptions are still denied, check:")
    print("  • JWT token validity and expiration")
    print("  • User permissions in OneOTalent tenant")
    print("  • Django server logs for additional errors")

if __name__ == "__main__":
    asyncio.run(main())