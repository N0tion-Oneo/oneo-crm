// Debug script to manually test WebSocket connection
// Run this in browser console to test WebSocket connectivity

console.log('🧪 Manual WebSocket Debug Test');

// Test 1: Check if we can create a WebSocket connection
const wsUrl = 'ws://oneotalent.localhost:8000/ws/realtime/';
console.log('🔌 Attempting WebSocket connection to:', wsUrl);

try {
  const ws = new WebSocket(wsUrl);
  
  ws.onopen = function(event) {
    console.log('✅ WebSocket connection opened successfully!');
    console.log('Connection event:', event);
    
    // Try subscribing to a test channel
    const testMessage = {
      type: 'subscribe',
      channel: 'conversation_1T1s9uwKX3yXDdHr9p9uWQ'
    };
    
    ws.send(JSON.stringify(testMessage));
    console.log('📡 Sent subscription message:', testMessage);
  };
  
  ws.onmessage = function(event) {
    console.log('📨 WebSocket message received:', event.data);
    try {
      const parsed = JSON.parse(event.data);
      console.log('📨 Parsed message:', parsed);
    } catch (e) {
      console.log('📨 Non-JSON message:', event.data);
    }
  };
  
  ws.onerror = function(error) {
    console.error('❌ WebSocket error:', error);
    console.error('❌ Error details:', {
      type: error.type,
      target: error.target,
      readyState: error.target?.readyState
    });
  };
  
  ws.onclose = function(event) {
    console.log('🔌 WebSocket closed:', {
      code: event.code,
      reason: event.reason,
      wasClean: event.wasClean
    });
  };
  
  // Store reference for manual testing
  window.debugWS = ws;
  
} catch (error) {
  console.error('❌ Failed to create WebSocket:', error);
}

// Test 2: Check current cookies
console.log('🍪 Current cookies:', document.cookie);

// Test 3: Check if access token exists
const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(';').shift();
  return null;
};

const accessToken = getCookie('oneo_access_token');
console.log('🔑 Access token:', accessToken ? 'PRESENT' : 'MISSING');
if (accessToken) {
  console.log('🔑 Token length:', accessToken.length);
  try {
    const payload = JSON.parse(atob(accessToken.split('.')[1]));
    console.log('🔑 Token payload:', {
      user_id: payload.user_id,
      username: payload.username,
      exp: new Date(payload.exp * 1000),
      expired: Date.now() > payload.exp * 1000
    });
  } catch (e) {
    console.error('🔑 Could not decode token:', e);
  }
}