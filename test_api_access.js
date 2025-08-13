// Simple test to verify basic API access
// Paste this into the browser console when logged into the app

async function testBasicApiAccess() {
    console.log('🔧 Testing Basic API Access...');
    
    // Get token from cookies
    const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('oneo_access_token='))
        ?.split('=')[1];
    
    if (!token) {
        console.error('❌ No access token found');
        return;
    }
    
    console.log('✅ Token found:', token.substring(0, 20) + '...');
    
    const baseURL = `http://${window.location.hostname}:8000`;
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    };
    
    // Test 1: Basic pipeline access
    console.log('\n📋 Test 1: Basic Pipeline Access');
    try {
        const response = await fetch(`${baseURL}/api/pipelines/`, { headers });
        console.log(`Status: ${response.status} ${response.statusText}`);
        
        if (response.ok) {
            const data = await response.json();
            console.log(`✅ Success: ${data.results?.length || 0} pipelines found`);
            
            if (data.results && data.results.length > 0) {
                const pipeline = data.results[0];
                console.log(`📋 Using pipeline: ${pipeline.name} (ID: ${pipeline.id})`);
                
                // Test 2: Records access
                console.log('\n📝 Test 2: Records Access');
                const recordsResponse = await fetch(`${baseURL}/api/pipelines/${pipeline.id}/records/`, { headers });
                console.log(`Status: ${recordsResponse.status} ${recordsResponse.statusText}`);
                
                if (recordsResponse.ok) {
                    const recordsData = await recordsResponse.json();
                    console.log(`✅ Success: ${recordsData.results?.length || 0} records found`);
                    
                    if (recordsData.results && recordsData.results.length > 0) {
                        const record = recordsData.results[0];
                        console.log(`📝 Using record: ${record.id}`);
                        
                        // Test 3: Try different endpoints for share link
                        console.log('\n🔗 Test 3: Share Link Endpoints');
                        
                        const endpoints = [
                            `/api/pipelines/${pipeline.id}/records/${record.id}/generate_share_link/`,
                            `/api/v1/pipelines/${pipeline.id}/records/${record.id}/generate_share_link/`,
                        ];
                        
                        for (const endpoint of endpoints) {
                            console.log(`\n🧪 Testing: ${endpoint}`);
                            try {
                                const response = await fetch(`${baseURL}${endpoint}`, {
                                    method: 'POST',
                                    headers
                                });
                                
                                console.log(`   Status: ${response.status} ${response.statusText}`);
                                
                                if (response.ok) {
                                    const data = await response.json();
                                    console.log('   ✅ SUCCESS! Share link generated');
                                    console.log('   🔐 Token length:', data.encrypted_token?.length);
                                    return data;
                                } else {
                                    const errorText = await response.text();
                                    console.log(`   ❌ Error: ${errorText}`);
                                }
                            } catch (error) {
                                console.log(`   ❌ Request failed: ${error.message}`);
                            }
                        }
                        
                        // Test 4: Try other record actions to see if it's a general issue
                        console.log('\n🔍 Test 4: Other Record Actions');
                        const testEndpoints = [
                            { path: `/api/pipelines/${pipeline.id}/records/${record.id}/`, method: 'GET', name: 'Get Record' },
                            { path: `/api/pipelines/${pipeline.id}/records/${record.id}/history/`, method: 'GET', name: 'Get History' },
                        ];
                        
                        for (const test of testEndpoints) {
                            try {
                                console.log(`\n🧪 Testing ${test.name}: ${test.method} ${test.path}`);
                                const response = await fetch(`${baseURL}${test.path}`, {
                                    method: test.method,
                                    headers
                                });
                                
                                console.log(`   Status: ${response.status} ${response.statusText}`);
                                
                                if (response.ok) {
                                    console.log(`   ✅ ${test.name} works`);
                                } else {
                                    console.log(`   ❌ ${test.name} failed`);
                                    const errorText = await response.text();
                                    console.log(`   Error: ${errorText}`);
                                }
                            } catch (error) {
                                console.log(`   ❌ ${test.name} request failed: ${error.message}`);
                            }
                        }
                        
                    } else {
                        console.log('❌ No records available for testing');
                    }
                } else {
                    const errorText = await recordsResponse.text();
                    console.log(`❌ Records access failed: ${errorText}`);
                }
            } else {
                console.log('❌ No pipelines available for testing');
            }
        } else {
            const errorText = await response.text();
            console.log(`❌ Pipeline access failed: ${errorText}`);
        }
    } catch (error) {
        console.error('❌ API test failed:', error);
    }
}

// Run the test
testBasicApiAccess();