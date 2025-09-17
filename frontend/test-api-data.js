// Test script to verify API data fetching works
const axios = require('axios');

const API_BASE = 'http://demo.localhost:8000';

// Sample JWT token - replace with an actual token from login
const TOKEN = 'YOUR_JWT_TOKEN_HERE';

async function testDataFetching() {
  const headers = {
    'Authorization': `Bearer ${TOKEN}`,
    'Content-Type': 'application/json'
  };

  try {
    console.log('Testing data fetching from:', API_BASE);

    // Test pipelines
    console.log('\n1. Fetching pipelines...');
    const pipelines = await axios.get(`${API_BASE}/api/pipelines/`, { headers });
    console.log(`   ✓ Found ${pipelines.data.length || pipelines.data.results?.length || 0} pipelines`);
    if (pipelines.data[0] || pipelines.data.results?.[0]) {
      const firstPipeline = pipelines.data[0] || pipelines.data.results[0];
      console.log(`   First pipeline: ${firstPipeline.name} (${firstPipeline.id})`);
    }

    // Test users
    console.log('\n2. Fetching users...');
    const users = await axios.get(`${API_BASE}/auth/users/`, { headers });
    console.log(`   ✓ Found ${users.data.length || users.data.results?.length || 0} users`);
    if (users.data[0] || users.data.results?.[0]) {
      const firstUser = users.data[0] || users.data.results[0];
      console.log(`   First user: ${firstUser.email}`);
    }

    // Test user types
    console.log('\n3. Fetching user types...');
    const userTypes = await axios.get(`${API_BASE}/auth/user-types/`, { headers });
    console.log(`   ✓ Found ${userTypes.data.length || userTypes.data.results?.length || 0} user types`);
    if (userTypes.data[0] || userTypes.data.results?.[0]) {
      const firstType = userTypes.data[0] || userTypes.data.results[0];
      console.log(`   First type: ${firstType.name}`);
    }

    // Test pipeline fields (if we have a pipeline)
    if (pipelines.data[0] || pipelines.data.results?.[0]) {
      const pipelineId = (pipelines.data[0] || pipelines.data.results[0]).id;
      console.log(`\n4. Fetching fields for pipeline ${pipelineId}...`);
      const fields = await axios.get(`${API_BASE}/api/pipelines/${pipelineId}/fields/`, { headers });
      console.log(`   ✓ Found ${fields.data.length || fields.data.results?.length || 0} fields`);
      if (fields.data[0] || fields.data.results?.[0]) {
        const firstField = fields.data[0] || fields.data.results[0];
        console.log(`   First field: ${firstField.label || firstField.name} (${firstField.field_type})`);
      }
    }

    console.log('\n✅ All API endpoints working correctly!');

  } catch (error) {
    console.error('\n❌ Error:', error.response?.data || error.message);
    if (error.response?.status === 401) {
      console.log('\nPlease update the TOKEN variable with a valid JWT token.');
      console.log('You can get one by logging in at http://demo.localhost:3000');
    }
  }
}

// Note: To run this test, you need to:
// 1. npm install axios (if not already installed)
// 2. Get a valid JWT token by logging in
// 3. Replace YOUR_JWT_TOKEN_HERE with the actual token
// 4. Run: node test-api-data.js

console.log('API Data Fetching Test');
console.log('======================');
console.log('Note: You need to provide a valid JWT token first.');
console.log('Get one by logging in and checking browser cookies for "oneo_access_token"');

// Uncomment to run test:
// testDataFetching();