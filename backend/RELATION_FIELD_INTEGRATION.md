# Relation Field & Dot Notation Traversal - Complete Integration Guide

## Overview

This document describes the complete end-to-end integration of relation field traversal using dot notation in workflows, enabling expressions like `company.name`, `deal.company.industry.category`, and `contacts[0].email`.

## Architecture Components

### 1. FieldPathResolver (`pipelines/field_path_resolver.py`)

**Purpose**: Core utility for resolving field paths with relationship traversal support.

**Key Features**:
- Single-hop traversal: `company.name`
- Multi-hop traversal: `deal.company.industry.category`
- Array access: `contacts[0].email`
- Redis caching with 5-minute TTL
- Request-level caching to avoid duplicate DB queries
- Max depth protection (default 3 hops)
- Soft-delete aware (skips `is_deleted=True` records)

**Usage**:
```python
from pipelines.field_path_resolver import FieldPathResolver, resolve_field_path

# Method 1: Using resolver instance
resolver = FieldPathResolver(max_depth=3, enable_caching=True)
value = resolver.resolve(record, 'company.industry.name')

# Method 2: Convenience function
value = resolve_field_path(record, 'company.name')
```

**Implementation Details**:
- **Lines 64-156**: Core `resolve()` method with caching
- **Lines 158-205**: Recursive `_resolve_path()` for traversal
- **Lines 207-272**: Relation traversal via RelationFieldHandler
- **Lines 364-417**: Helper methods for ID extraction and dict traversal

---

### 2. Workflow Integration

#### 2.1 Signal Layer (`workflows/signals.py`)

**What Changed**:
```python
# BEFORE
record_data = {
    'id': str(instance.id),
    'data': instance.data,  # Dict only
}

# AFTER
record_data = {
    'id': str(instance.id),
    'data': instance.data,
    'record_object': instance,  # ✅ Pass actual Record instance
}
```

**Location**: Lines 22-30 (create/update), Lines 59-64 (delete)

#### 2.2 Trigger View Layer (`workflows/views/trigger_events.py`)

**What Changed**:
```python
trigger_data = {
    'record_id': record_data.get('id'),
    'record_data': record_data,
    'record': record_data.get('record_object'),  # ✅ Extract Record instance
}
```

**Location**: Lines 122-130

#### 2.3 Workflow Engine (`workflows/engine.py`)

**What Changed**: Added lazy loading fallback for Record objects.

```python
# Ensure Record object is available for FieldPathResolver
if 'record' not in context and 'record_id' in context:
    # Fetch Record from database if not in context
    record = await fetch_record()
    if record:
        context['record'] = record
```

**Location**: Lines 222-242

---

### 3. Node Processor Integration

#### 3.1 BaseNodeProcessor (`workflows/nodes/base.py`)

**Enhanced `_get_nested_value()`** (Lines 234-305):

```python
def _get_nested_value(self, data, path):
    # Check if we have a record for relationship traversal
    if 'record' in data and isinstance(data['record'], Record):
        # Try FieldPathResolver first
        resolver = FieldPathResolver(max_depth=3, enable_caching=True)
        resolved_value = resolver.resolve(record, path)

        if resolved_value is not None:
            return resolved_value

    # Fall back to standard dictionary traversal
    return dict_traversal(data, path)
```

**Backwards Compatibility**: ✅ Complete
- If no Record object: falls back to dict traversal
- Existing workflows continue to work unchanged
- New workflows automatically get relation traversal

---

#### 3.2 Condition Evaluator (`workflows/utils/condition_evaluator.py`)

**Enhanced `_get_nested_value()`** (Lines 269-321):

Same pattern as BaseNodeProcessor - checks for Record object, uses FieldPathResolver, falls back to dict traversal.

**Usage in Workflows**:
```json
{
  "conditions": [
    {
      "field": "company.industry.category",
      "operator": "equals",
      "value": "Technology"
    }
  ]
}
```

---

#### 3.3 WorkflowEngine (`workflows/engine.py`)

**Enhanced `_get_nested_value()`** (Lines 498-549):

Supports `record.field.path` syntax in workflow context:

```python
# In workflow nodes, you can reference:
context['record.company.name']           # → 'Acme Corporation'
context['record.deal.company.industry']  # → Multi-hop traversal
```

---

### 4. Relation Field Handler (`pipelines/relation_field_handler.py`)

**Core Methods Used by FieldPathResolver**:

```python
class RelationFieldHandler:
    def get_relationships(self, record):
        """Get all relationships for this field (bidirectional)"""

    def get_related_ids(self, record):
        """Get related record IDs"""

    def get_related_records_with_display(self, record):
        """Get related records with display values"""
```

**Integration Point**: Lines 207-272 in FieldPathResolver

The resolver:
1. Gets the field definition from pipeline
2. Creates RelationFieldHandler instance
3. Extracts related record IDs
4. Fetches related Records
5. Recursively resolves remaining path on related records

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Django Signal (Record.post_save)                         │
│    workflows/signals.py:22-30                                │
│    ✅ Includes: record_object (Record instance)              │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Trigger View (RecordEventTriggerView)                    │
│    views/trigger_events.py:122-130                           │
│    ✅ Extracts: record = record_data.get('record_object')    │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Trigger Registry (trigger_workflows)                     │
│    trigger_registry.py:169-173                               │
│    ✅ Passes trigger_data with 'record' key                  │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Workflow Engine (execute_workflow)                       │
│    engine.py:214-242                                         │
│    ✅ Adds 'record' to context (or lazy loads)               │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Node Processors (BaseNodeProcessor._get_nested_value)    │
│    nodes/base.py:234-305                                     │
│    ✅ Uses FieldPathResolver if 'record' in context          │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. FieldPathResolver (resolve)                              │
│    field_path_resolver.py:64-156                             │
│    ✅ Traverses relationships via RelationFieldHandler       │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. RelationFieldHandler (get_relationships)                 │
│    relation_field_handler.py:124-214                         │
│    ✅ Queries Relationship table, fetches related Records    │
└─────────────────────────────────────────────────────────────┘
```

---

## Usage Examples

### Example 1: Simple Field Access (Backwards Compatible)
```python
# Workflow condition
{
  "field": "email",
  "operator": "contains",
  "value": "@acme.com"
}

# Resolves to: record.data['email']
# Uses: Dict traversal (backwards compatible)
```

### Example 2: Single-Hop Relation Traversal
```python
# Workflow condition
{
  "field": "company.name",
  "operator": "equals",
  "value": "Acme Corporation"
}

# Resolves to:
# 1. Get company_id from record.data['company']
# 2. Fetch company Record
# 3. Return company.data['name']
# Uses: FieldPathResolver → RelationFieldHandler
```

### Example 3: Multi-Hop Relation Traversal
```python
# Workflow AI prompt
template = "Send email to {company.industry.category} companies"

# Resolves to:
# 1. Get company_id from record.data['company']
# 2. Fetch company Record
# 3. Get industry_id from company.data['industry']
# 4. Fetch industry Record
# 5. Return industry.data['category']
# Uses: Recursive FieldPathResolver traversal
```

### Example 4: Array Relation Access
```python
# Workflow condition
{
  "field": "contacts[0].email",
  "operator": "equals",
  "value": "john@acme.com"
}

# Resolves to:
# 1. Get contacts array from record.data['contacts']
# 2. Extract first contact ID: contacts[0]['id']
# 3. Fetch contact Record
# 4. Return contact.data['email']
# Uses: FieldPathResolver with array index support
```

---

## Testing

### Manual Test via Django Shell
```bash
cd backend
python manage.py shell
```

```python
from django_tenants.utils import schema_context
from pipelines.models import Record
from pipelines.field_path_resolver import resolve_field_path

with schema_context('oneotalent'):
    # Find a record with relations
    record = Record.objects.filter(
        pipeline__fields__field_type='relation'
    ).first()

    if record:
        # Test single-hop
        result = resolve_field_path(record, 'company.name')
        print(f"Company name: {result}")

        # Test multi-hop
        result = resolve_field_path(record, 'company.industry.category')
        print(f"Industry category: {result}")
```

### Integration Test
See `/backend/test_field_path_resolver.py` for comprehensive test suite covering:
- ✅ Simple field access
- ✅ Single-hop traversal
- ✅ Multi-hop traversal
- ✅ Array relations
- ✅ Caching functionality
- ✅ Error handling
- ✅ BaseNodeProcessor integration
- ✅ Condition evaluator integration

---

## Performance Considerations

### Caching Strategy

**1. Redis Cache (5-minute TTL)**
- Key format: `field_path_resolver:{record_id}:{pipeline_id}:{field_path}`
- Shared across requests
- Automatic expiration

**2. Request-Level Cache**
- Stores results for single workflow execution
- Prevents duplicate queries within same workflow
- Cleared after workflow completes

### Query Optimization

**Efficient Queries**:
- Uses `select_related()` where possible
- Filters by `is_deleted=False` at query level
- Bulk fetches for array relations

**Max Depth Protection**:
- Default: 3 hops maximum
- Prevents infinite loops
- Configurable per resolver instance

---

## Backwards Compatibility

✅ **100% Backwards Compatible**

**Existing Workflows**:
- Continue to work without modification
- Dict traversal still works for nested objects
- No breaking changes to any APIs

**New Workflows**:
- Automatically get relation traversal if Record object available
- Falls back to dict traversal if Record not in context
- No configuration required

---

## Troubleshooting

### Issue: Relation traversal not working

**Check 1**: Is Record object in context?
```python
# In node processor
print(f"Has record: {'record' in context}")
print(f"Record type: {type(context.get('record'))}")
```

**Check 2**: Is field actually a relation field?
```python
field = record.pipeline.fields.get(slug='company')
print(f"Field type: {field.field_type}")  # Should be 'relation'
```

**Check 3**: Are there actual relationships in the database?
```python
from pipelines.relation_field_handler import RelationFieldHandler
handler = RelationFieldHandler(field)
relations = handler.get_relationships(record)
print(f"Found {len(relations)} relationships")
```

### Issue: "Record #X" showing instead of display value

**Root Cause**: Target record doesn't have data in the configured `display_field`.

**Solution**:
1. Check field config: `field.field_config['display_field']`
2. Verify target record has that field populated
3. Consider changing display_field to a field that has data

---

## Files Modified

### New Files Created (1)
1. `pipelines/field_path_resolver.py` - Core resolver (470 lines)

### Files Modified (6)
1. `workflows/signals.py` - Pass Record object (lines 22-30, 59-64)
2. `workflows/views/trigger_events.py` - Extract Record object (lines 122-130)
3. `workflows/engine.py` - Add Record lazy loading (lines 222-242)
4. `workflows/nodes/base.py` - Integrate FieldPathResolver (lines 234-305)
5. `workflows/utils/condition_evaluator.py` - Integrate FieldPathResolver (lines 269-321)
6. `oneo_crm/settings.py` - Comment out django_extensions (line 144)

### Test Files
1. `test_field_path_resolver.py` - Comprehensive integration tests
2. `test_dot_notation_simple.py` - Simple verification script

---

## Summary

**✅ Complete Integration Achieved**

The relation field system now fully supports dot notation traversal in workflows, enabling powerful relationship-aware automation without requiring explicit record fetching or manual relationship navigation.

**Key Benefits**:
- Natural syntax: `company.name` instead of manual lookups
- Multi-hop support: `deal.company.industry.category`
- Array relations: `contacts[0].email`
- High performance: Dual caching layer + query optimization
- Zero breaking changes: 100% backwards compatible

**Next Steps**:
1. Test with real workflow scenarios
2. Monitor performance in production
3. Consider adding more traversal features (e.g., filtering, aggregation)
