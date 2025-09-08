# Pipeline Layout Components

## ⚠️ IMPORTANT: Component Usage Status

### ✅ ACTIVE COMPONENTS
- **`pipeline-list-sidebar.tsx`** - The main pipeline list sidebar shown on the left side of pipeline pages
  - Used in: `/app/(dashboard)/pipelines/layout.tsx` (main pipelines layout)
  - Shows: List of all pipelines with search and filtering

### ❌ UNUSED/ORPHANED COMPONENTS
- **`config-sections-sidebar.tsx`** - NOT CURRENTLY USED
  - Only imported by: `pipeline-config-wrapper.tsx` (which is also unused)
  - Was likely part of a refactoring that was never completed
  - Contains permission-aware navigation logic that is duplicated in the active layout
  
- **`pipeline-config-wrapper.tsx`** - NOT CURRENTLY USED
  - Not imported anywhere in the codebase
  - Appears to be an alternative implementation that was never integrated

## 📍 WHERE THE ACTUAL PIPELINE CONFIGURATION SIDEBAR IS

The actual working pipeline configuration sidebar is implemented directly in:
**`/app/(dashboard)/pipelines/[id]/layout.tsx`**

This is the Next.js layout file that renders:
1. The pipeline configuration navigation (Overview, Fields, Business Rules, etc.)
2. Permission-based filtering of navigation items
3. Pipeline metadata display

## 🔧 If You Need to Modify Pipeline Navigation

### To change the pipeline configuration sidebar:
Edit: `/app/(dashboard)/pipelines/[id]/layout.tsx`
- Look for the `navigationItems` array
- Permission checks are done in the component with `hasFieldPermissions`, `hasBusinessRulesPermissions`, etc.
- Items are filtered before rendering based on these permissions

### To change the main pipeline list sidebar:
Edit: `/src/components/pipelines/layout/pipeline-list-sidebar.tsx`

## 🗑️ Cleanup Recommendation

Consider removing these unused files to avoid confusion:
- `config-sections-sidebar.tsx`
- `pipeline-config-wrapper.tsx`

They contain duplicate logic that could cause confusion when developers are looking for where to make changes.

## 📝 Notes

This situation likely occurred due to:
1. An incomplete refactoring where the team started extracting the sidebar into a reusable component
2. A change in approach where they decided to keep the navigation in the layout file
3. The unused components were never cleaned up

Last verified: 2025-09-08