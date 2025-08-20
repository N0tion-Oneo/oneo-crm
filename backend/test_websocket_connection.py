#!/usr/bin/env python3
"""
Test WebSocket connection from the perspective of what frontend should be doing
"""
import asyncio
import websockets
import json
import ssl

async def test_websocket_connection():
    """Test WebSocket connection like the frontend would"""
    print("🔌 Testing WebSocket Connection Like Frontend")
    print("=" * 60)
    
    # Test URLs that frontend might be using
    test_urls = [
        "ws://localhost:8000/ws/realtime/",
        "ws://oneotalent.localhost:8000/ws/realtime/", 
        "ws://127.0.0.1:8000/ws/realtime/"
    ]
    
    for url in test_urls:
        print(f"\n🧪 Testing URL: {url}")
        
        try:
            # Test connection without token first
            print("   Attempting connection without token...")
            websocket = await websockets.connect(url, timeout=5)
            print("   ✅ Connection successful!")
            
            # Test subscribing to conversation room
            subscription_message = {
                "type": "subscribe",
                "channel": "conversation_d39d8667-24bc-4e32-8944-239017479484"
            }
            
            await websocket.send(json.dumps(subscription_message))
            print(f"   ✅ Subscription sent to conversation room")
            
            # Wait for any response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2)
                print(f"   📨 Response: {response}")
            except asyncio.TimeoutError:
                print("   ⏰ No immediate response (normal)")
            
            await websocket.close()
            print("   ✅ Connection closed cleanly")
            
        except websockets.exceptions.ConnectionRefused:
            print("   ❌ Connection refused - server not accepting connections")
        except websockets.exceptions.InvalidStatusCode as e:
            print(f"   ❌ Invalid status code: {e.status_code}")
        except Exception as e:
            print(f"   ❌ Connection failed: {e}")
    
    print("\n🎯 Next Steps:")
    print("   1. Check which URL worked (if any)")
    print("   2. Check if frontend is using the correct URL")
    print("   3. Check browser console for WebSocket errors")
    print("   4. Verify JWT token is being passed correctly")

if __name__ == "__main__":
    asyncio.run(test_websocket_connection())