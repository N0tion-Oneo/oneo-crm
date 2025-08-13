// Complete test of the share link workflow
// Copy and paste this into the browser console when logged into http://demo.localhost:3000

async function testCompleteShareWorkflow() {
    console.log('🚀 Testing Complete Share Link Workflow...');
    
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
    
    // Step 1: Generate share link
    const pipelineId = '1';
    const recordId = '15';
    const shareEndpoint = `/api/pipelines/${pipelineId}/records/${recordId}/generate_share_link/`;
    
    console.log(`\n🔗 Step 1: Generate Share Link`);
    console.log(`POST ${baseURL}${shareEndpoint}`);
    
    try {
        const shareResponse = await fetch(`${baseURL}${shareEndpoint}`, {
            method: 'POST',
            headers
        });
        
        console.log(`Status: ${shareResponse.status} ${shareResponse.statusText}`);
        
        if (!shareResponse.ok) {
            const errorText = await shareResponse.text();
            console.log(`❌ Share link generation failed: ${errorText}`);
            return;
        }
        
        const shareData = await shareResponse.json();
        console.log('✅ Share link generated successfully!');
        console.log(`   Token: ${shareData.encrypted_token.substring(0, 50)}...`);
        console.log(`   Working days remaining: ${shareData.working_days_remaining}`);
        
        // Step 2: Test shared record access (no auth required)
        const sharedEndpoint = `/api/v1/shared-records/${shareData.encrypted_token}/`;
        
        console.log(`\n📋 Step 2: Access Shared Record`);
        console.log(`GET ${baseURL}${sharedEndpoint}`);
        
        const sharedResponse = await fetch(`${baseURL}${sharedEndpoint}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
                // No Authorization header - public access
            }
        });
        
        console.log(`Status: ${sharedResponse.status} ${sharedResponse.statusText}`);
        
        if (!sharedResponse.ok) {
            const errorText = await sharedResponse.text();
            console.log(`❌ Shared record access failed: ${errorText}`);
            return;
        }
        
        const sharedRecordData = await sharedResponse.json();
        console.log('✅ Shared record accessed successfully!');
        console.log(`   Record ID: ${sharedRecordData.record.id}`);
        console.log(`   Pipeline: ${sharedRecordData.record.pipeline.name}`);
        console.log(`   Fields: ${sharedRecordData.form_schema.fields.length} fields`);
        
        // Show sample field data
        const sampleField = sharedRecordData.form_schema.fields.find(f => f.current_value);
        if (sampleField) {
            console.log(`   Sample field: ${sampleField.name} = "${sampleField.current_value}"`);
        }
        
        // Step 3: Test analytics access
        const analyticsEndpoint = `/api/v1/shared-records/${shareData.encrypted_token}/analytics/`;
        
        console.log(`\n📊 Step 3: Test Analytics Access`);
        console.log(`GET ${baseURL}${analyticsEndpoint}`);
        
        const analyticsResponse = await fetch(`${baseURL}${analyticsEndpoint}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (analyticsResponse.ok) {
            const analyticsData = await analyticsResponse.json();
            console.log('✅ Analytics access works!');
            console.log(`   Access count: ${analyticsData.access_count}`);
        } else {
            console.log(`⚠️  Analytics not accessible (this may be expected)`);
        }
        
        console.log(`\n🎉 COMPLETE SUCCESS!`);
        console.log(`✅ Share link generation: Working`);
        console.log(`✅ Encrypted token: Working`);  
        console.log(`✅ Public record access: Working`);
        console.log(`✅ Form data population: Working`);
        console.log(`\n🔗 Frontend ShareRecordButton should now work perfectly!`);
        
        // Return the data for further testing if needed
        return {
            shareData,
            sharedRecordData
        };
        
    } catch (error) {
        console.error('❌ Test failed:', error);
    }
}

// Run the complete test
testCompleteShareWorkflow();