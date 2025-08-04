# API-Centric Permission Architecture Plan - Final Version

## Executive Summary

This plan standardizes our permission system by centralizing all permissions through the `/api/` layer, leveraging the existing authentication registry and matrix, and cleaning up legacy Django app code. The goal is to have **one unified permission system** that all applications use consistently.

## Current State Analysis

### ✅ Well-Structured Apps
- **Authentication**: Complete permission infrastructure (models, registry, matrix)
- **API**: Excellent permission classes with proper DRF integration
- **Relationships**: Specialized permission manager with multi-hop traversal

### ⚠️ Apps Needing Standardization
- **Forms**: Split between app ViewSets and API endpoints
- **Workflows**: No permission integration with authentication registry
- **Pipelines**: Basic permission structure but not using registry
- **Communications**: Basic auth only, no granular permissions
- **Monitoring**: Admin-only access, no permission matrix integration
- **AI**: No permission system implemented

### 🔧 Infrastructure Status
- **Permission Registry**: 15 categories defined, only 5 actively used (67% unused)
- **Dynamic Permissions**: Working for pipelines, workflows, forms
- **Frontend**: Uses `/api/` endpoints exclusively
- **Legacy URLs**: Most direct app routes are unused by frontend

## Implementation Plan

### Phase 1: Organize API Permission Structure

**Goal**: Create clean, organized permission directory in `/api/permissions/`

```bash
/api/permissions/
├── __init__.py              # Import all permission classes
├── base.py                  # Base permission classes (AdminOnly, TenantMember, ReadOnly)
├── pipelines.py             # PipelinePermission, RecordPermission
├── relationships.py         # RelationshipPermission 
├── forms.py                 # FormPermission, ValidationRulePermission
├── duplicates.py            # DuplicatePermission (separate from forms)
├── workflows.py             # NEW: WorkflowPermission, WorkflowExecutionPermission
├── communications.py        # NEW: CommunicationPermission, MessagePermission
├── monitoring.py            # NEW: MonitoringPermission, AnalyticsPermission
├── ai.py                    # NEW: AIPermission, ProcessorPermission
└── utils.py                 # Permission utility functions
```

**Tasks**:
1. Create `/api/permissions/` directory structure
2. Move existing permissions from `/api/permissions.py` to organized files
3. Update imports in `/api/permissions/__init__.py`
4. Verify no import breakage across the system

### Phase 2: Add Missing Permission Classes

**Goal**: Create permission classes for apps without proper permission integration

**New Permission Classes Needed**:

#### 2.1 Workflows (`/api/permissions/workflows.py`)
```python
class WorkflowPermission(permissions.BasePermission):
    """Workflow-specific permissions using authentication registry"""
    
class WorkflowExecutionPermission(permissions.BasePermission):
    """Workflow execution permissions"""
    
class WorkflowApprovalPermission(permissions.BasePermission):
    """Workflow approval permissions"""
```

#### 2.2 Communications (`/api/permissions/communications.py`)
```python
class CommunicationPermission(permissions.BasePermission):
    """Communication management permissions"""
    
class MessagePermission(permissions.BasePermission):
    """Message-specific permissions"""
    
class ChannelPermission(permissions.BasePermission):
    """Communication channel permissions"""
```

#### 2.3 Monitoring (`/api/permissions/monitoring.py`)
```python
class MonitoringPermission(permissions.BasePermission):
    """System monitoring permissions"""
    
class AnalyticsPermission(permissions.BasePermission):
    """Analytics and reporting permissions"""
    
class AlertPermission(permissions.BasePermission):
    """Alert management permissions"""
```

#### 2.4 AI (`/api/permissions/ai.py`)
```python
class AIPermission(permissions.BasePermission):
    """AI feature permissions"""
    
class ProcessorPermission(permissions.BasePermission):
    """AI processor permissions"""
```

### Phase 3: Connect All Permissions to Authentication Registry

**Goal**: Ensure all permission classes use the `authentication.permissions_registry`

**Registry Categories to Activate**:
- `workflows` ✅ (defined, needs connection)
- `communications` ✅ (defined, needs connection)  
- `monitoring` ✅ (defined, needs connection)
- `ai_features` ✅ (defined, needs connection)
- `business_rules` (needs implementation)
- `reports` (needs implementation)

**Implementation Steps**:
1. Update each permission class to use `SyncPermissionManager` or `AsyncPermissionManager`
2. Map ViewSet actions to registry permissions (create, read, update, delete, execute, etc.)
3. Implement object-level permissions using dynamic resource IDs
4. Add permission validation for all existing endpoints

### Phase 4: Update API ViewSets

**Goal**: Apply new permission classes to all API ViewSets

**ViewSets to Update**:
- `/api/views/workflows.py` → Use `WorkflowPermission`
- `/api/views/communications.py` → Use `CommunicationPermission`
- `/api/views/monitoring.py` → Use `MonitoringPermission`
- `/api/views/ai.py` → Use `AIPermission`

**Pattern to Follow**:
```python
from api.permissions import WorkflowPermission

class WorkflowViewSet(viewsets.ModelViewSet):
    permission_classes = [WorkflowPermission]
    # ... rest of implementation
```

### Phase 5: Legacy Code Cleanup

**Goal**: Remove deprecated and unused code after permission standardization

#### 5.1 Django App URL Cleanup
**Files to Clean/Remove**:
- `/workflows/urls.py` → Move any active endpoints to `/api/urls.py`
- `/communications/urls.py` → Move any active endpoints to `/api/urls.py`
- `/monitoring/urls.py` → Move any active endpoints to `/api/urls.py`
- `/ai/urls.py` → Move any active endpoints to `/api/urls.py`

**URLs to Keep**:
- `/authentication/urls_drf.py` → Authentication endpoints
- `/relationships/urls.py` → Check if used by frontend, migrate if needed
- `/api/urls.py` → Main API routing

#### 5.2 Legacy ViewSet Cleanup
**Analyze and Clean**:
- Forms: Remove `/forms/views.py` ViewSets (duplicate of API)
- Workflows: Remove `/workflows/views.py` if not used
- Communications: Remove `/communications/views.py` if not used
- Monitoring: Remove `/monitoring/views.py` if not used

#### 5.3 Permission File Consolidation
**Remove/Consolidate**:
- Individual app permission files → Migrate logic to `/api/permissions/`
- Unused permission classes and middleware
- Duplicate permission logic across apps

### Phase 6: Frontend Integration Validation

**Goal**: Ensure frontend continues working seamlessly

**Validation Steps**:
1. Test all frontend permission guards with new permission structure
2. Verify permission matrix integration works correctly
3. Ensure dynamic permissions (pipeline_X, workflow_X) function properly
4. Test permission inheritance and user type assignments
5. Validate multi-tenant permission isolation

## Permission Architecture Overview

### Multi-Level Permission System

**Level 1: System Permissions** (Global)
- `system.full_access` → Platform administration
- Applied at tenant level, overrides all other permissions

**Level 2: Category Permissions** (Feature Areas)
- `pipelines.create`, `workflows.execute`, `communications.send`
- Broad feature access control

**Level 3: Resource Permissions** (Object-Level)  
- `pipeline_123.read`, `workflow_456.execute`, `form_789.submit`
- Specific resource access control

**Level 4: User Type Permissions** (RBAC)
- Admin → All permissions by default
- Manager → Most permissions except system/delete
- User → Standard workflow permissions
- Viewer → Read-only access

**Level 5: Field-Level Permissions** (Granular)
- Per-field visibility and modification rights
- Implemented through relationship traversal permissions

### Dynamic Permission Generation

The system automatically generates resource-specific permissions:
- **Pipeline Creation** → Generates `pipeline_{id}` permission category
- **Workflow Creation** → Generates `workflow_{id}` permission category  
- **Form Creation** → Generates `form_{id}` permission category

### Permission Inheritance

```
System > Category > Resource > User Type > Field Level
```

More restrictive permissions at lower levels override broader permissions.

## Migration Strategy

### Pre-Migration Checklist
- [ ] Backup production database
- [ ] Test permission system on staging environment
- [ ] Verify frontend functionality with new permission structure
- [ ] Prepare rollback plan

### Migration Steps
1. **Phase 1-2**: Can be done safely (just organizing and adding)
2. **Phase 3-4**: Requires testing - changes permission enforcement
3. **Phase 5-6**: Breaking changes - requires careful coordination

### Risk Mitigation
- **Feature Flags**: Use Django settings to toggle between old/new permission systems
- **Gradual Rollout**: Migrate one app at a time
- **Permission Fallbacks**: Maintain backward compatibility during transition

## Success Metrics

### Technical Metrics
- ✅ **Single Permission Source**: All apps use `/api/permissions/`
- ✅ **Registry Utilization**: 90%+ of registry categories actively used
- ✅ **Code Reduction**: 50%+ reduction in permission-related code duplication
- ✅ **API Consistency**: All endpoints use standardized permission classes

### Business Metrics  
- ✅ **Multi-Level Granularity**: 5+ permission levels working
- ✅ **Multi-Tenant Isolation**: Zero cross-tenant permission leaks
- ✅ **Performance**: <50ms permission checks
- ✅ **Scalability**: Support for 1000+ dynamic resources per tenant

## Timeline Estimate

- **Phase 1**: 1-2 days (organization)
- **Phase 2**: 3-4 days (new permission classes)
- **Phase 3**: 2-3 days (registry integration)
- **Phase 4**: 2-3 days (ViewSet updates)
- **Phase 5**: 2-3 days (cleanup)
- **Phase 6**: 1-2 days (validation)

**Total**: 11-17 days

## Post-Implementation Benefits

1. **Unified Architecture**: Single permission system across all apps
2. **Improved Maintainability**: Centralized permission logic
3. **Enhanced Security**: Consistent permission enforcement
4. **Better UX**: Predictable permission behavior in frontend
5. **Scalability**: Registry-based system scales with new features
6. **Developer Experience**: Clear permission patterns and documentation

---

This plan provides the **multi-level granular permissions** system we need while building on our existing strong foundation. The API-centric approach ensures consistency and maintainability as the platform grows.