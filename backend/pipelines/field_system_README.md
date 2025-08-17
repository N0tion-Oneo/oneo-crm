# Field System Documentation

## Overview

The Oneo CRM Field System is a sophisticated, multi-layered architecture that provides dynamic field management with real-time updates, multi-tenant isolation, and comprehensive validation. This system allows for flexible pipeline configuration with drag-and-drop field organization, automatic data migration, and WebSocket-based real-time synchronization.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (React/TypeScript)                  │
├─────────────────────────────────────────────────────────────────┤
│  • Pipeline Field Builder (Drag & Drop)                        │
│  • Auto-Save Hooks (1.5s debounced)                           │
│  • WebSocket Context (Real-time updates)                       │
│  • Field Configuration Panels                                  │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Layer (Django REST)                    │
├─────────────────────────────────────────────────────────────────┤
│  • FieldViewSet (CRUD operations)                              │
│  • FieldSerializer (Validation & Serialization)               │
│  • Pipeline-scoped routing (/api/pipelines/{id}/fields/)       │
│  • Multi-tenant URL routing                                    │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Field Operations Layer                        │
├─────────────────────────────────────────────────────────────────┤
│  • FieldOperationManager (Business logic)                      │
│  • Field State Management                                      │
│  • Data Migration Engine                                       │
│  • Field Validation System                                     │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Database Layer                              │
├─────────────────────────────────────────────────────────────────┤
│  • Pipeline Model                                              │
│  • Field Model (with field_group ForeignKey)                  │
│  • FieldGroup Model                                            │
│  • Multi-tenant schema isolation                               │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Real-time Layer                               │
├─────────────────────────────────────────────────────────────────┤
│  • WebSocket Consumers                                          │
│  • Django Signals                                              │
│  • Channel Layers (Redis)                                      │
│  • Real-time field updates                                     │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Frontend Field Management

**Location:** `/frontend/src/components/pipelines/pipeline-field-builder.tsx`

**Key Features:**
- Drag-and-drop field organization between groups
- Real-time validation with 300ms debouncing
- Auto-save functionality (1.5s delay)
- WebSocket integration for live updates
- Field configuration panels for all 24+ field types

**Auto-Save Hook:** `/frontend/src/hooks/use-auto-save-fields.ts`
```typescript
// Automatically saves field changes with debouncing
const { scheduleAutoSave, cancelAutoSave, isFieldSaving } = useAutoSaveFields(pipelineId, {
  delay: 1500,
  onSaveSuccess: (field) => console.log('✅ Field saved:', field.name),
  onSaveError: (error, field) => console.error('❌ Save failed:', error)
})
```

### 2. API Layer

**FieldViewSet:** `/backend/api/views/pipelines.py`
```python
class FieldViewSet(viewsets.ModelViewSet):
    serializer_class = FieldSerializer
    permission_classes = [PipelinePermission]
    
    def get_queryset(self):
        pipeline_pk = self.kwargs.get('pipeline_pk')
        return Field.objects.filter(pipeline_id=pipeline_pk)
```

**FieldSerializer:** `/backend/api/serializers.py`
```python
class FieldSerializer(serializers.ModelSerializer):
    field_group = serializers.PrimaryKeyRelatedField(
        queryset=FieldGroup.objects.none(),  # Scoped in __init__
        allow_null=True,
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Scope field_group queryset to current pipeline
        if pipeline_id := self._get_pipeline_id():
            self.fields['field_group'].queryset = FieldGroup.objects.filter(
                pipeline_id=pipeline_id
            )
```

### 3. Field Operations Layer

**FieldOperationManager:** `/backend/pipelines/field_operations.py`

This is the core business logic layer that handles all field operations:

```python
class FieldOperationManager:
    def update_field(self, field_id: int, changes: Dict[str, Any], user: User):
        """Update field with automatic migration detection"""
        with transaction.atomic():
            # 1. Lock field for update
            field = Field.objects.select_for_update().get(id=field_id)
            
            # 2. Capture original state
            self.state_manager.capture_field_state(field.id)
            
            # 3. Validate changes
            validation_result = self.validator.validate_field_update(field, changes)
            
            # 4. Apply changes (with special ForeignKey handling)
            self._apply_field_changes(field, changes, user)
            
            # 5. Migrate data if required
            if change_analysis['requires_migration']:
                self.migrator.migrate_field_data(field, original_state)
```

**Critical Fix - ForeignKey Handling:**
```python
def _apply_field_changes(self, field: Field, changes: Dict[str, Any], user: User):
    """Apply changes with proper ForeignKey handling"""
    for key, value in changes.items():
        if key == 'field_group':
            if value is None:
                field.field_group = None
            else:
                # Look up FieldGroup instance by ID within current pipeline
                field_group = FieldGroup.objects.get(id=value, pipeline=field.pipeline)
                field.field_group = field_group
        else:
            setattr(field, key, value)
    
    field.save()
```

### 4. Database Models

**Field Model:** `/backend/pipelines/models.py`
```python
class Field(models.Model):
    pipeline = models.ForeignKey(Pipeline, related_name='fields')
    field_group = models.ForeignKey(FieldGroup, null=True, blank=True)
    name = models.CharField(max_length=255)
    field_type = models.CharField(max_length=50)
    field_config = models.JSONField(default=dict)
    display_order = models.IntegerField(default=0)
    # ... other fields
```

**FieldGroup Model:**
```python
class FieldGroup(models.Model):
    pipeline = models.ForeignKey(Pipeline, related_name='field_groups')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#3B82F6')
    display_order = models.IntegerField(default=0)
```

### 5. Real-time Updates

**WebSocket Integration:** `/backend/realtime/signals.py`
```python
@receiver(post_save, sender=Field)
def field_updated_handler(sender, instance, created, **kwargs):
    """Broadcast field updates via WebSocket"""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"pipeline_fields_{instance.pipeline_id}",
        {
            "type": "field_update",
            "field": FieldSerializer(instance).data
        }
    )
```

## Data Flow

### Field Group Assignment (Drag & Drop)

1. **User drags field** to new group in frontend
2. **Frontend updates local state** immediately for responsive UI
3. **Auto-save hook** schedules save after 1.5s delay
4. **API request** sent to `/api/pipelines/{id}/fields/{field_id}/`
5. **FieldSerializer validates** field_group within pipeline scope
6. **FieldOperationManager** applies changes with proper ForeignKey lookup
7. **Django signals** broadcast update via WebSocket
8. **All connected clients** receive real-time field update

### Field Creation Flow

1. **Frontend** creates new field with temporary ID
2. **API call** to create field endpoint
3. **FieldOperationManager** validates and creates field
4. **Data migration** adds field to existing records if needed
5. **Pipeline schema update** refreshes cached field definitions
6. **WebSocket broadcast** notifies all clients of new field
7. **Frontend replaces** temporary field with real field data

## Multi-Tenant Architecture

### Schema Isolation
- Each tenant has isolated database schema
- FieldGroups are scoped to specific pipelines within tenant
- No cross-tenant data access possible

### URL Structure
```
https://{tenant}.localhost:3000/pipelines/{pipeline_id}/fields
↓
http://{tenant}.localhost:8000/api/pipelines/{pipeline_id}/fields/
```

### Permission System
- Pipeline-level permissions control field access
- Field operations respect user role hierarchy
- Admin/Manager/User/Viewer permission levels

## Error Handling & Debugging

### Common Issues & Solutions

**1. "Cannot assign '9': Field.field_group must be a FieldGroup instance"**
- **Cause:** Direct integer assignment to ForeignKey field
- **Fix:** Implemented special handling in `_apply_field_changes()`
- **Code:** Look up FieldGroup instance before assignment

**2. Field group not found in queryset**
- **Cause:** FieldSerializer using unscoped queryset
- **Fix:** Pipeline-scoped queryset in `FieldSerializer.__init__()`
- **Code:** `FieldGroup.objects.filter(pipeline_id=pipeline_id)`

**3. Auto-save not triggering**
- **Cause:** Field changes not detected or debouncing issues
- **Fix:** Check field change detection and debounce timing
- **Debug:** Console logs show auto-save scheduling

### Debug Logging

**Frontend Console:**
```javascript
🔄 assignFieldToGroup called: {fieldId: '79', groupId: 9}
⏰ Scheduled auto-save for field "personal_website" in 1500ms
🔄 Auto-updating field: Personal Website field_group: 9
✅ Auto-updated field: Personal Website
```

**Backend Logs:**
```python
🔍 FieldSerializer.__init__ called
🔍 Got pipeline_id from view.kwargs['pipeline_pk']: 23
🔍 Set field_group queryset to pipeline 23
INFO Successfully assigned field_group 9 to field Personal Website
```

## Field Types System

### Supported Field Types (24+)
- **Basic:** text, textarea, email, url, phone
- **Numeric:** number, decimal, currency
- **Selection:** select, multiselect, boolean
- **Date/Time:** date, datetime, time
- **Advanced:** user, relation, address, tags
- **Special:** ai, computed, formula, file, button

### Field Configuration
Each field type has specific configuration options:
```python
field_config = {
    # Text fields
    'placeholder': 'Enter value...',
    'max_length': 255,
    
    # Number fields  
    'min_value': 0,
    'max_value': 1000000,
    'format': 'currency',
    'currency': 'USD',
    
    # Select fields
    'options': [{'label': 'Option 1', 'value': 'opt1'}],
    'allow_multiple': False,
    
    # AI fields
    'ai_prompt': 'Analyze this contact...',
    'ai_model': 'gpt-4',
    'tools_enabled': ['web_search']
}
```

## Performance Optimizations

### Database Optimizations
- **Select for Update:** Prevents concurrent field modifications
- **Prefetch Related:** Loads field groups efficiently
- **GIN Indexes:** Fast JSONB field_config queries
- **Schema Caching:** Pipeline field schemas cached for performance

### Frontend Optimizations
- **Debounced Auto-save:** Prevents excessive API calls
- **Local State Management:** Immediate UI updates
- **WebSocket Updates:** Efficient real-time synchronization
- **Lazy Loading:** Field configurations loaded on demand

### API Optimizations
- **Nested Routing:** Efficient URL structure
- **Permission Caching:** User permissions cached per request
- **Bulk Operations:** Multiple field updates in single transaction

## Testing Strategy

### Unit Tests
```python
class FieldOperationManagerTestCase(TestCase):
    def test_field_group_assignment(self):
        # Test proper ForeignKey assignment
        result = self.manager.update_field(
            field_id=self.field.id,
            changes={'field_group': self.group.id},
            user=self.user
        )
        self.assertTrue(result.success)
        self.field.refresh_from_db()
        self.assertEqual(self.field.field_group, self.group)
```

### Integration Tests
```python
def test_drag_drop_workflow(self):
    # Test complete drag-and-drop flow
    response = self.client.patch(
        f'/api/pipelines/{self.pipeline.id}/fields/{self.field.id}/',
        {'field_group': self.target_group.id}
    )
    self.assertEqual(response.status_code, 200)
```

### Frontend Tests
```typescript
describe('Field Drag and Drop', () => {
  it('should update field group on drop', async () => {
    const { scheduleAutoSave } = useAutoSaveFields(pipelineId)
    scheduleAutoSave({ id: '79', field_group: 9 })
    
    await waitFor(() => {
      expect(mockApi.patch).toHaveBeenCalledWith(
        '/api/pipelines/23/fields/79/',
        expect.objectContaining({ field_group: 9 })
      )
    })
  })
})
```

## Monitoring & Analytics

### Metrics Tracked
- Field operation success rates
- Auto-save performance timings
- WebSocket connection stability
- Field validation error rates
- Migration execution times

### Audit Logging
All field operations are logged with:
- User who made the change
- Operation type (create/update/delete)
- Original and new values
- Migration requirements and results
- Timestamps and operation IDs

## Future Enhancements

### Planned Features
1. **Field Templates:** Reusable field configurations
2. **Bulk Field Operations:** Mass field updates
3. **Field Dependencies:** Dynamic field relationships
4. **Advanced Validation Rules:** Custom field validators
5. **Field History:** Version tracking for field changes
6. **Performance Dashboard:** Real-time field operation metrics

### Architecture Improvements
1. **Event Sourcing:** Complete operation replay capability
2. **Caching Strategy:** Enhanced field metadata caching
3. **Background Processing:** Async field migration for large datasets
4. **API Rate Limiting:** Per-tenant operation limits
5. **Health Monitoring:** Field system health checks

## Getting Started

### Development Setup
```bash
# Backend setup
cd backend
source venv/bin/activate
python manage.py migrate_schemas
python manage.py runserver

# Frontend setup  
cd frontend
npm install
npm run dev

# Test field operations
python manage.py test pipelines.tests.test_field_operations
```

### Creating a New Field Type
1. Add field type to `pipelines/field_types.py`
2. Create configuration component in `frontend/src/components/pipelines/field-configs/`
3. Add validation logic to `pipelines/validation/field_validator.py`
4. Update field renderer in `frontend/src/lib/field-system/`

---

**Last Updated:** August 17, 2025
**Contributors:** Claude Code Assistant, Josh Cowan
**Status:** Production Ready ✅