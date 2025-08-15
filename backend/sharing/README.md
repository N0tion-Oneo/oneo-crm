# Oneo CRM Sharing System

The Oneo CRM Sharing System provides secure, token-based sharing of filtered data views with external users. This system allows users to share specific records and data with people outside their organization while maintaining strict security boundaries and access controls.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Security Model](#security-model)
- [Sharing Process](#sharing-process)
- [API Endpoints](#api-endpoints)
- [Filter Validation](#filter-validation)
- [Access Modes](#access-modes)
- [Development Guide](#development-guide)

## Overview

The sharing system enables users to:
- **Share filtered record views** with external users via secure links
- **Control access permissions** with granular access modes
- **Enforce filter boundaries** to ensure data security
- **Track access and usage** for audit and analytics
- **Manage share lifecycle** with expiration and revocation

### Key Features

- 🔒 **Secure Token-Based Access** - Encrypted tokens prevent unauthorized access
- 🎯 **Filter-Based Security** - Only records matching the saved filter are accessible
- 📊 **Multiple Access Modes** - View-only, filtered editing, commenting, and export
- 🗑️ **Soft Delete Handling** - Deleted records are automatically excluded
- 📈 **Access Analytics** - Track usage patterns and access logs
- ⏰ **Expiration Control** - Automatic link expiration with configurable timeouts

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   SavedFilter   │────│   SharedFilter   │────│  Access Token   │
│                 │    │                  │    │                 │
│ • Filter Config │    │ • Access Mode    │    │ • Encrypted     │
│ • Pipeline      │    │ • Expiration     │    │ • Time-based    │
│ • Visibility    │    │ • Permissions    │    │ • Revocable     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                       │                       │
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│    Records      │    │  Filter Engine   │    │  Public API     │
│                 │    │                  │    │                 │
│ • Pipeline Data │    │ • Query Builder  │    │ • No Auth Req   │
│ • Field Values  │    │ • Security Check │    │ • CORS Enabled  │
│ • Relationships │    │ • Result Filter  │    │ • Rate Limited  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Security Model

### 1. Token-Based Authentication

```python
# Token Structure
{
    'record_id': saved_filter.id,
    'timestamp': creation_time,
    'expires': expiration_time
}
# Encrypted with AES-256 and base64 encoded
```

### 2. Filter Validation

Every request validates that records match the saved filter criteria:

```python
def _record_matches_filter(record, saved_filter):
    """
    Validates if a record matches the saved filter's criteria.
    Returns True if record is accessible, False if blocked.
    """
    # Apply BooleanQuery structure validation
    # Handle complex field types (user arrays, relationships)
    # Enforce security boundaries
```

### 3. Access Control Matrix

| Access Mode | View Records | Edit Records | Export Data | Add Comments |
|-------------|-------------|-------------|-------------|--------------|
| `view_only` | ✅ | ❌ | ❌ | ❌ |
| `filtered_edit` | ✅ | ✅* | ❌ | ❌ |
| `comment` | ✅ | ❌ | ❌ | ✅ |
| `export` | ✅ | ❌ | ✅ | ❌ |

*Only records matching filter criteria can be edited

## Sharing Process

### Step 1: Create a Saved Filter

```python
# Create a saved filter with specific criteria
saved_filter = SavedFilter.objects.create(
    name="Josh's Deals",
    pipeline=sales_pipeline,
    filter_config={
        "groups": [{
            "id": "group-1",
            "logic": "AND",
            "filters": [{
                "field": "sales_agent",
                "value": '{"user_id":"1"}',
                "operator": "contains"
            }]
        }],
        "groupLogic": "AND"
    },
    created_by=user
)
```

### Step 2: Create a Share

```python
# Create a shared filter with access controls
shared_filter = SharedFilter.objects.create(
    saved_filter=saved_filter,
    shared_by=user,
    intended_recipient_email="external@example.com",
    access_mode="filtered_edit",
    expires_at=timezone.now() + timedelta(days=7),
    shared_fields=["company_name", "deal_value", "contact_email"]
)
```

### Step 3: Generate Secure Token

```python
# System automatically generates encrypted token
token = shared_filter.encrypted_token
share_url = f"https://app.oneo.com/shared/{token}"
```

### Step 4: External User Access

```javascript
// External user accesses via public API
const response = await fetch(`/api/v1/public-filters/${token}/records/`);
const data = await response.json();

// Only records matching the filter criteria are returned
console.log(data.results); // Filtered records
console.log(data.count);   // Total matching records
```

## API Endpoints

### Public Endpoints (No Authentication Required)

#### Get Shared Filter Info
```http
GET /api/v1/public-filters/{token}/
```

#### Get Pipeline Details
```http
GET /api/v1/public-filters/{token}/pipeline/
```

#### List Filtered Records
```http
GET /api/v1/public-filters/{token}/records/
```

**Response:**
```json
{
    "results": [
        {
            "id": 38,
            "data": {
                "company_name": "Test Company",
                "deal_value": {"amount": 123121, "currency": "GBP"},
                "sales_agent": [{"user_id": 1, "name": "Josh Cowan"}]
            },
            "created_at": "2025-08-15T10:33:57.788412+00:00",
            "updated_at": "2025-08-15T10:33:57.788412+00:00"
        }
    ],
    "count": 1,
    "page": 1,
    "page_size": 50
}
```

#### Update Record (Filtered Edit Mode Only)
```http
PATCH /api/v1/public-filters/{token}/records/{record_id}/
Content-Type: application/json

{
    "data": {
        "company_name": "Updated Company Name",
        "deal_value": {"amount": 150000, "currency": "USD"}
    }
}
```

**Security Validation:**
- ✅ Token must be valid and not expired
- ✅ Access mode must be `filtered_edit`
- ✅ Record must match the saved filter criteria
- ✅ Only shareable fields can be updated

### Authenticated Endpoints (Require User Login)

#### Create Share
```http
POST /api/v1/saved-filters/{filter_id}/share/
Content-Type: application/json

{
    "intended_recipient_email": "external@example.com",
    "access_mode": "filtered_edit",
    "expires_in_days": 7,
    "shared_fields": ["company_name", "deal_value"]
}
```

#### List Shares
```http
GET /api/v1/saved-filters/{filter_id}/shares/
```

#### Revoke Share
```http
POST /api/v1/shared-filters/{share_id}/revoke/
```

## Filter Validation

The system implements sophisticated filter validation to ensure security:

### Simple Text Filters
```json
{
    "field": "company_name",
    "value": "Acme Corp",
    "operator": "contains"
}
```

### User Field Arrays (Complex JSON)
```json
{
    "field": "sales_agent",
    "value": "{\"user_id\":\"1\"}",
    "operator": "contains"
}
```

**Validation Logic:**
```python
# For user fields, parse JSON and check array contents
if isinstance(record_value, list):
    filter_obj = json.loads(filter_value)
    target_user_id = filter_obj['user_id']
    
    for user in record_value:
        if user.get('user_id') == target_user_id:
            return True  # Record matches filter
    return False  # Record blocked
```

### Supported Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `contains` | Field contains value | `"name contains 'John'"` |
| `equals` | Exact match | `"status equals 'active'"` |
| `gt` / `gte` | Greater than (or equal) | `"price gt 1000"` |
| `lt` / `lte` | Less than (or equal) | `"age lt 65"` |
| `starts_with` | Starts with value | `"email starts_with 'admin'"` |
| `ends_with` | Ends with value | `"domain ends_with '.com'"` |
| `is_empty` | Field is empty | `"notes is_empty"` |
| `is_not_empty` | Field has value | `"phone is_not_empty"` |

## Access Modes

### View Only (`view_only`)
- **Purpose**: Read-only access to filtered records
- **Use Cases**: Reports, dashboards, data verification
- **Permissions**: View records and pipeline structure only

### Filtered Edit (`filtered_edit`)
- **Purpose**: Edit records that match filter criteria
- **Use Cases**: External data updates, collaborative editing
- **Permissions**: View + edit records matching filter
- **Security**: Records must pass filter validation for each update

### Comment (`comment`)
- **Purpose**: Add comments and annotations
- **Use Cases**: Feedback collection, review processes
- **Permissions**: View records + add comments only

### Export (`export`)
- **Purpose**: Data export capabilities
- **Use Cases**: External reporting, data migration
- **Permissions**: View + export records in various formats

## Development Guide

### Creating Custom Filters

```python
# Define filter configuration
filter_config = {
    "groups": [
        {
            "id": "group-1",
            "logic": "AND",  # AND/OR within group
            "filters": [
                {
                    "field": "status",
                    "value": "active",
                    "operator": "equals"
                },
                {
                    "field": "assigned_user",
                    "value": '{"user_id":"123"}',
                    "operator": "contains"
                }
            ]
        }
    ],
    "groupLogic": "AND"  # AND/OR between groups
}
```

### Adding New Field Types

```python
# Extend _evaluate_filter_condition for new field types
def _evaluate_filter_condition(self, record_value, operator, filter_value):
    if operator == 'contains':
        # Add custom logic for new field types
        if isinstance(record_value, CustomFieldType):
            return self._handle_custom_field(record_value, filter_value)
        
        # Existing logic...
```

### Testing Shares

```bash
# Test share creation
curl -X POST "http://tenant.localhost:8000/api/v1/saved-filters/1/share/" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "intended_recipient_email": "test@example.com",
    "access_mode": "view_only",
    "expires_in_days": 1
  }'

# Test public access
curl "http://tenant.localhost:8000/api/v1/public-filters/<token>/records/"

# Test record update (filtered_edit mode)
curl -X PATCH "http://tenant.localhost:8000/api/v1/public-filters/<token>/records/123/" \
  -H "Content-Type: application/json" \
  -d '{"data": {"company_name": "Updated Name"}}'
```

### Debugging Filter Issues

```python
# Enable debug logging
import logging
logging.getLogger('sharing').setLevel(logging.DEBUG)

# Test filter validation manually
from sharing.models import SharedFilter
from pipelines.models import Record

shared_filter = SharedFilter.objects.get(encrypted_token='...')
record = Record.objects.get(id=123)

# Check if record matches filter
matches = view._record_matches_filter(record, shared_filter.saved_filter)
print(f"Record {record.id} matches filter: {matches}")
```

## Security Considerations

### Data Protection
- **Encryption**: All tokens use AES-256 encryption
- **Expiration**: Automatic token expiration prevents long-term access
- **Revocation**: Immediate access revocation capability
- **Audit Trail**: Complete access logging for compliance

### Filter Security
- **Validation Required**: Every record access validates filter criteria
- **No Bypass**: Cannot access records outside filter scope
- **Error Handling**: Secure error messages don't leak data structure
- **Performance**: Efficient filtering avoids N+1 queries

### Best Practices
1. **Principle of Least Privilege**: Use most restrictive access mode needed
2. **Short Expiration Times**: Default to 7 days or less
3. **Field Restrictions**: Only share necessary fields
4. **Regular Audits**: Monitor access logs for unusual patterns
5. **Immediate Revocation**: Revoke shares when no longer needed

## Troubleshooting

### Common Issues

**403 Forbidden Errors:**
- Check if record matches filter criteria
- Verify access mode allows the requested operation
- Ensure token hasn't expired

**No Records Returned:**
- Verify filter configuration is correct
- Check if records exist in the pipeline
- Ensure records aren't soft-deleted

**Token Decryption Failures:**
- Verify token hasn't been corrupted
- Check token expiration
- Ensure proper URL encoding

### Monitoring

```python
# Monitor share usage
from sharing.models import SharedFilter

# Get analytics
shares = SharedFilter.objects.filter(is_active=True)
for share in shares:
    print(f"Share {share.id}: {share.access_count} accesses")
    print(f"Last accessed: {share.last_accessed_at}")
    print(f"Expires: {share.expires_at}")
```

---

## Contributing

When modifying the sharing system:

1. **Security First**: All changes must maintain or improve security
2. **Test Coverage**: Add tests for new functionality
3. **Documentation**: Update this README for API changes
4. **Backwards Compatibility**: Maintain existing token compatibility

For questions or support, contact the development team or create an issue in the repository.