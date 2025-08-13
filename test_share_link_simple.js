// Simple test to verify share link functionality works with our test record
// Copy and paste this into the browser console when logged into http://demo.localhost:3000

async function testShareLinkWithTestRecord() {
    console.log('🔧 Testing Share Link with Test Record...');
    
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
    
    // Test with our known test record
    const pipelineId = '1';  // Test Business Rules Pipeline
    const recordId = '15';   // Our newly created test record
    
    console.log(`\n🧪 Testing Share Link Generation`);
    console.log(`   Pipeline ID: ${pipelineId}`);
    console.log(`   Record ID: ${recordId}`);
    
    const endpoint = `/api/pipelines/${pipelineId}/records/${recordId}/generate_share_link/`;
    
    try {
        console.log(`\n🔗 POST ${baseURL}${endpoint}`);
        const response = await fetch(`${baseURL}${endpoint}`, {
            method: 'POST',
            headers
        });
        
        console.log(`Status: ${response.status} ${response.statusText}`);
        
        if (response.ok) {
            const data = await response.json();
            console.log('✅ SUCCESS! Share link generated');
            console.log('📊 Response data:', data);
            console.log('🔐 Encrypted token length:', data.encrypted_token?.length);
            console.log('⏰ Expires at:', new Date(data.expires_at * 1000).toLocaleString());
            console.log('📅 Working days remaining:', data.working_days_remaining);
            
            // Test the shared record access
            const sharedUrl = `/api/v1/shared-records/${data.encrypted_token}/`;
            console.log(`\n🔍 Testing Shared Record Access: GET ${baseURL}${sharedUrl}`);
            
            const sharedResponse = await fetch(`${baseURL}${sharedUrl}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                    // No Authorization header - public access
                }
            });
            
            console.log(`Shared Access Status: ${sharedResponse.status} ${sharedResponse.statusText}`);
            
            if (sharedResponse.ok) {
                const sharedData = await sharedResponse.json();
                console.log('✅ SUCCESS! Shared record accessible');
                console.log('📋 Shared record data keys:', Object.keys(sharedData));
                console.log('📧 Email field:', sharedData.form_schema?.fields?.find(f => f.name.includes('email')));
            } else {
                const errorText = await sharedResponse.text();
                console.log(`❌ Shared access failed: ${errorText}`);
            }
            
            return data;
        } else {
            const errorText = await response.text();
            console.log(`❌ Share link generation failed: ${errorText}`);
        }
    } catch (error) {
        console.error('❌ Request failed:', error);
    }
}

// Run the test
testShareLinkWithTestRecord();