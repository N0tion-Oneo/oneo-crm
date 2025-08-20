#!/usr/bin/env python3
"""
Test WebSocket authentication using a real JWT token
"""
import asyncio
import websockets
import json
import requests
from urllib.parse import urlencode

async def test_websocket_with_auth():
    """Test WebSocket connection with JWT authentication"""
    print("🔑 Testing WebSocket Authentication")
    print("=" * 60)
    
    # First, get a JWT token by logging in via the REST API
    login_url = "http://oneotalent.localhost:8000/auth/login/"
    
    # Test credentials (you might need to adjust these)
    test_credentials = {
        "email": "josh@oneodigital.com",
        "password": "admin123"
    }
    
    print(f"1. Attempting login to: {login_url}")
    print(f"   Credentials: {test_credentials['email']}")
    
    try:
        # Login to get JWT token
        login_response = requests.post(login_url, json=test_credentials, timeout=10)
        print(f"   Login response status: {login_response.status_code}")
        
        if login_response.status_code == 200:
            token_data = login_response.json()
            access_token = token_data.get('access')
            
            if access_token:
                print(f"   ✅ Got access token: {access_token[:20]}...")
                
                # Test WebSocket connection with token
                ws_urls_to_test = [
                    f"ws://oneotalent.localhost:8000/ws/realtime/?token={access_token}",
                    f"ws://localhost:8000/ws/realtime/?token={access_token}"
                ]
                
                for ws_url in ws_urls_to_test:
                    print(f"\n2. Testing WebSocket URL: {ws_url[:80]}...")
                    
                    try:
                        # Add origin header to match frontend
                        extra_headers = {
                            'Origin': 'http://oneotalent.localhost:3000'
                        }
                        websocket = await websockets.connect(ws_url, timeout=10, extra_headers=extra_headers)
                        print("   ✅ WebSocket connection successful!")
                        
                        # Wait for authentication response
                        try:
                            auth_response = await asyncio.wait_for(websocket.recv(), timeout=5)
                            print(f"   📨 Auth response: {auth_response}")
                            
                            # Test subscription to conversation room
                            test_subscription = {
                                "type": "subscribe",
                                "channel": "conversation_1T1s9uwKX3yXDdHr9p9uWQ"
                            }
                            
                            await websocket.send(json.dumps(test_subscription))
                            print(f"   📡 Sent subscription: {test_subscription}")
                            
                            # Wait for subscription response
                            sub_response = await asyncio.wait_for(websocket.recv(), timeout=3)
                            print(f"   📨 Subscription response: {sub_response}")
                            
                        except asyncio.TimeoutError:
                            print("   ⏰ No immediate response (might be normal)")
                        
                        await websocket.close()
                        print("   ✅ Connection closed cleanly")
                        break  # Success, no need to test other URLs
                        
                    except websockets.exceptions.InvalidStatusCode as e:
                        print(f"   ❌ WebSocket rejected with status: {e.status_code}")
                        if hasattr(e, 'response_headers'):
                            print(f"   📋 Response headers: {dict(e.response_headers)}")
                    except Exception as e:
                        print(f"   ❌ WebSocket connection failed: {e}")
            else:
                print("   ❌ No access token in login response")
                print(f"   📋 Response data: {token_data}")
        else:
            print(f"   ❌ Login failed: {login_response.status_code}")
            print(f"   📋 Response: {login_response.text}")
            
            # Also try with the demo tenant
            print(f"\n🔄 Trying demo tenant...")
            demo_login_url = "http://demo.localhost:8000/auth/login/"
            demo_response = requests.post(demo_login_url, json=test_credentials, timeout=10)
            print(f"   Demo login response: {demo_response.status_code}")
            if demo_response.status_code == 200:
                demo_token = demo_response.json().get('access')
                if demo_token:
                    print(f"   ✅ Got demo token: {demo_token[:20]}...")
                    demo_ws_url = f"ws://demo.localhost:8000/ws/realtime/?token={demo_token}"
                    print(f"   Testing: {demo_ws_url[:80]}...")
                    
                    try:
                        demo_websocket = await websockets.connect(demo_ws_url, timeout=10)
                        print("   ✅ Demo WebSocket connection successful!")
                        await demo_websocket.close()
                    except Exception as e:
                        print(f"   ❌ Demo WebSocket failed: {e}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ HTTP request failed: {e}")
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_with_auth())