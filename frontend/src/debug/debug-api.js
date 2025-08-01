/**
 * Frontend API Debug Script
 * Run this in browser console to test API connectivity and JWT tokens
 */

// Debug API connectivity and JWT token status
async function debugAPIConnectivity() {
  console.log('🔍 Debugging Frontend API Connectivity...\n');
  
  // Check current hostname and API base URL
  const currentHost = window.location.hostname;
  const baseURL = `http://${currentHost}:8000`;
  console.log('📍 Current hostname:', currentHost);
  console.log('📍 API Base URL:', baseURL);
  
  // Check stored JWT tokens
  const accessToken = document.cookie.split('; ').find(row => row.startsWith('oneo_access_token='));
  const refreshToken = document.cookie.split('; ').find(row => row.startsWith('oneo_refresh_token='));
  
  console.log('🔑 Access Token:', accessToken ? 'Present' : 'Missing');
  console.log('🔑 Refresh Token:', refreshToken ? 'Present' : 'Missing');
  
  if (accessToken) {
    const tokenValue = accessToken.split('=')[1];
    try {
      // Decode JWT payload (basic decode, no verification)
      const payload = JSON.parse(atob(tokenValue.split('.')[1]));
      console.log('🔑 Token Payload:', payload);
      console.log('🔑 Token Expires:', new Date(payload.exp * 1000));
      console.log('🔑 Token Expired:', Date.now() > payload.exp * 1000);
    } catch (e) {
      console.log('❌ Failed to decode token:', e.message);
    }
  }
  
  // Test API endpoint
  console.log('\n🔄 Testing API endpoint...');
  try {
    const response = await fetch(`${baseURL}/auth/users/`, {
      method: 'GET',
      headers: {
        'Authorization': accessToken ? `Bearer ${accessToken.split('=')[1]}` : '',
        'Content-Type': 'application/json'
      },
      credentials: 'include'
    });
    
    console.log('📡 API Response Status:', response.status);
    
    if (response.ok) {
      const data = await response.json();
      console.log('✅ API Request Successful');
      console.log('👥 Users found:', data.results?.length || data.length || 'Unknown');
    } else {
      const errorData = await response.text();
      console.log('❌ API Request Failed');
      console.log('📄 Error Response:', errorData);
    }
  } catch (error) {
    console.log('❌ Network Error:', error.message);
  }
  
  // Test user deactivation
  console.log('\n🔄 Testing user deactivation endpoint...');
  try {
    const response = await fetch(`${baseURL}/auth/users/4/deactivate/`, {
      method: 'POST',
      headers: {
        'Authorization': accessToken ? `Bearer ${accessToken.split('=')[1]}` : '',
        'Content-Type': 'application/json'
      },
      credentials: 'include'
    });
    
    console.log('📡 Deactivation Response Status:', response.status);
    
    if (response.ok) {
      const data = await response.json();
      console.log('✅ Deactivation Request Successful');
      console.log('👤 User Status:', data.is_active ? 'Active' : 'Inactive');
    } else {
      const errorData = await response.text();
      console.log('❌ Deactivation Request Failed');
      console.log('📄 Error Response:', errorData);
    }
  } catch (error) {
    console.log('❌ Deactivation Network Error:', error.message);
  }
}

// Run the debug
debugAPIConnectivity();

// Provide instructions
console.log('\n📋 Instructions:');
console.log('1. Open browser dev tools (F12)');
console.log('2. Go to Console tab');
console.log('3. Copy and paste this script');
console.log('4. Look for any errors or token issues');
console.log('5. If tokens are missing or expired, try logging in again');