// Simple test to debug the share API endpoint
// Run this in the browser console on the frontend app

async function debugShareAPI() {
    console.log('🔧 Debugging Share API...');
    
    // Get authentication token from cookies
    const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('oneo_access_token='))
        ?.split('=')[1];
    
    if (!token) {
        console.error('❌ No access token found in cookies');
        return;
    }
    
    console.log('✅ Found access token:', token.substring(0, 20) + '...');
    
    // Test API base URL
    const baseURL = `http://${window.location.hostname}:8000`;
    console.log('🌐 API Base URL:', baseURL);
    
    // Try to get pipelines first to test basic auth
    try {
        console.log('\n📋 Testing pipeline access...');
        const pipelineResponse = await fetch(`${baseURL}/api/pipelines/`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            }
        });
        
        console.log('Pipeline API Status:', pipelineResponse.status);
        
        if (pipelineResponse.ok) {
            const pipelines = await pipelineResponse.json();
            console.log('✅ Pipeline access successful:', pipelines.results?.length || 0, 'pipelines');
            
            if (pipelines.results && pipelines.results.length > 0) {
                const pipeline = pipelines.results[0];
                console.log('📋 Using pipeline:', pipeline.name, '(ID:', pipeline.id, ')');
                
                // Get records for this pipeline
                console.log('\n📝 Testing record access...');
                const recordResponse = await fetch(`${baseURL}/api/pipelines/${pipeline.id}/records/`, {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    }
                });
                
                console.log('Record API Status:', recordResponse.status);
                
                if (recordResponse.ok) {
                    const records = await recordResponse.json();
                    console.log('✅ Record access successful:', records.results?.length || 0, 'records');
                    
                    if (records.results && records.results.length > 0) {
                        const record = records.results[0];
                        console.log('📝 Using record:', record.id);
                        
                        // Test the share link generation endpoint
                        console.log('\n🔗 Testing share link generation...');
                        
                        // Test both URL patterns
                        const endpoints = [
                            `/api/pipelines/${pipeline.id}/records/${record.id}/generate_share_link/`,
                            `/api/v1/pipelines/${pipeline.id}/records/${record.id}/generate_share_link/`
                        ];
                        
                        for (const endpoint of endpoints) {
                            try {
                                console.log(`\n🧪 Testing endpoint: ${endpoint}`);
                                const shareResponse = await fetch(`${baseURL}${endpoint}`, {
                                    method: 'POST',
                                    headers: {
                                        'Authorization': `Bearer ${token}`,
                                        'Content-Type': 'application/json',
                                    }
                                });
                                
                                console.log(`Status: ${shareResponse.status} ${shareResponse.statusText}`);
                                
                                if (shareResponse.ok) {
                                    const shareData = await shareResponse.json();
                                    console.log('✅ Share link generated successfully!');
                                    console.log('🔐 Encrypted token length:', shareData.encrypted_token?.length || 'N/A');
                                    console.log('🔗 Share URL:', shareData.share_url);
                                    return shareData;
                                } else {
                                    const errorText = await shareResponse.text();
                                    console.log('❌ Error response:', errorText);
                                }
                            } catch (error) {
                                console.log('❌ Request failed:', error.message);
                            }
                        }
                    } else {
                        console.log('❌ No records available to test with');
                    }
                } else {
                    const errorText = await recordResponse.text();
                    console.log('❌ Record access failed:', errorText);
                }
            } else {
                console.log('❌ No pipelines available to test with');
            }
        } else {
            const errorText = await pipelineResponse.text();
            console.log('❌ Pipeline access failed:', errorText);
        }
    } catch (error) {
        console.error('❌ API test failed:', error);
    }
}

// Run the debug function
debugShareAPI();