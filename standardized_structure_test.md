# Standardized Data Structure Implementation

## Changes Made

We've standardized the workflow builder to use the same flat configuration structure as the test schema page, and fixed pipeline fields passing.

### Before (Nested Structure):
```javascript
node.data = {
  config: {
    pipeline_id: "123",
    form_mode: "internal_full",
    // ... other config
  },
  // other node properties...
}
```

### After (Flat Structure):
```javascript
node.data = {
  pipeline_id: "123",
  form_mode: "internal_full",
  // ... config directly in data
}
```

## Files Modified:

### 3. **FieldSelector.tsx**
- Updated to handle both array and object formats for pipelineFields
- Extracts fields based on selected pipeline IDs when pipelineFields is an object
- Maintains backward compatibility with array format

### 1. **WorkflowBuilderRedesigned.tsx**
- Removed `node.data?.config || node.data` logic
- Now passes `node.data` directly to `testNodeStandalone`
- Updated `handleNodeUpdate` to replace data entirely instead of merging

### 2. **NodeParametersTab.tsx**
- Changed from `nodeData.config` to `nodeData` directly
- Updated `handleConfigChange` to pass config as flat data
- Removed nested structure in `onUpdate` callback
- Fixed pipeline fields passing: now passes complete `pipelineFields` object instead of pre-filtered array
- Added pipeline field fetching for `pipeline_ids` (plural) to support triggers like Record Updated

## Testing Instructions:

1. Navigate to http://oneotalent.localhost:3000/workflows
2. Create or edit a workflow with triggers that support stage tracking:
   - **Form Submission trigger**: Shows stage options when form mode is set
   - **Record Updated trigger**: Shows stage tracking toggle when watching a select field
3. Configure the trigger:
   - Select a pipeline
   - For Form Submission: Choose form mode, stage field options should appear
   - For Record Updated: Watch a single select/choice field, stage tracking toggle should appear
4. Verify the configuration saves correctly
5. Test the node execution

## Expected Behavior:

Both the test schema page and workflow builder should now:
- Store configuration in the same flat structure
- Pass the same data format to the backend
- Behave consistently when testing nodes
- Show the same form fields and validation
- **Display stage tracking options when applicable**:
  - Form Submission: stage options appear when form mode is internal_filtered or public_filtered
  - Record Updated: stage tracking toggle appears when watching a single select/choice field
- **Extract field options correctly** from pipeline fields for stage selection

## Benefits:

1. **Consistency**: Single data structure across the application
2. **Simplicity**: No need to check for nested vs flat structures
3. **Maintainability**: Easier to understand and debug
4. **Reliability**: Eliminates edge cases from structure differences

The workflow builder and test schema page now use identical data handling!