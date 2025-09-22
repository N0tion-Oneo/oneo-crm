# Testing Workflow Builder Fix

## Test Steps:

1. **Navigate to workflows**: http://oneotalent.localhost:3000/workflows
2. **Create or edit a workflow** that has a Form Submission trigger
3. **Configure the trigger**:
   - Select a pipeline
   - Choose form mode (e.g., "internal_full" or "public_filtered")
   - Optionally select a stage
4. **Test the node**:
   - Click "Test Node" button in the configuration panel
   - Select a test record from the pipeline (if available)
   - Check the output

## Expected Results:

### Before Fix:
- The test would fail or return incomplete data
- Form data fields would not be properly extracted
- Missing metadata like submission_id, submitted_at

### After Fix (Using testNodeStandalone):
- ✅ All record fields appear at the top level of the output
- ✅ Nested `form_data` object contains all the record data
- ✅ Metadata fields are included:
  - submission_id
  - submitted_at
  - pipeline_id
  - record_id
  - user_info (with ip_address, user_agent, referrer)
  - ip_address
  - referrer_url

## What Changed:

The workflow builder now uses the same `testNodeStandalone` API endpoint that the working test schema page uses. This ensures:

1. Proper configuration wrapping: `{'data': {'config': node_config}}`
2. Correct trigger data building in the backend
3. Consistent behavior between test schema page and workflow builder

## API Calls Comparison:

### Old (Not Working):
```javascript
await workflowsApi.testNode(workflowId, {
  node_id: nodeId,
  node_type: node.type,
  node_config: node.data,
  test_record_id: testRecordId,
  test_context: {...}
});
```

### New (Working):
```javascript
await workflowsApi.testNodeStandalone({
  node_type: node.type,
  node_config: node.data?.config || node.data,
  test_data_id: testRecordId,
  test_data_type: testRecordId ? 'record' : undefined
});
```