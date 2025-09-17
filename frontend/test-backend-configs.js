#!/usr/bin/env node

/**
 * Test script to verify backend-only node configurations are working
 */

const fetch = require('node-fetch');

async function testBackendConfigs() {
    console.log('🧪 Testing Backend-Only Configuration System\n');
    console.log('=' .repeat(60));

    // Test nodes that previously had frontend configs
    const testNodes = [
        'trigger_record_updated',
        'trigger_email_received',
        'trigger_form_submitted',
        'send_email',
        'create_follow_up_task'
    ];

    const results = {
        success: [],
        failed: []
    };

    for (const nodeType of testNodes) {
        try {
            // Simulate what workflowSchemaService.getNodeConfig does
            console.log(`\nTesting ${nodeType}...`);

            // Check if backend would provide this schema
            const response = await fetch('http://localhost:8000/api/v1/workflows/node_schemas/');

            if (!response.ok) {
                throw new Error(`API returned ${response.status}`);
            }

            const schemas = await response.json();

            if (schemas[nodeType]) {
                console.log(`✅ ${nodeType}: Found in backend schemas`);
                console.log(`   Properties: ${Object.keys(schemas[nodeType].config_schema?.properties || {}).length}`);
                results.success.push(nodeType);
            } else {
                console.log(`❌ ${nodeType}: Not found in backend schemas`);
                results.failed.push(nodeType);
            }
        } catch (error) {
            console.log(`❌ ${nodeType}: Error - ${error.message}`);
            results.failed.push(nodeType);
        }
    }

    console.log('\n' + '=' .repeat(60));
    console.log('📊 Test Results:');
    console.log(`   ✅ Success: ${results.success.length}/${testNodes.length}`);
    console.log(`   ❌ Failed: ${results.failed.length}/${testNodes.length}`);

    if (results.failed.length > 0) {
        console.log(`\n   Failed nodes: ${results.failed.join(', ')}`);
    }

    console.log('\n🎯 Backend-only configuration status:',
        results.failed.length === 0 ? '✅ WORKING' : '❌ ISSUES FOUND');
}

// Run the test
testBackendConfigs().catch(console.error);