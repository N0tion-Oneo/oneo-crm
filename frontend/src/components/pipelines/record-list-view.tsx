// record-list-view.tsx - Updated to use refactored components
// Original 1,768-line monolithic component has been decomposed into focused, reusable pieces

// Export types for backward compatibility
export type { 
  RecordField,
  Record, 
  Pipeline,
  RecordListViewProps 
} from '@/types/records'

// Export the field conversion utility for backward compatibility
export { FieldUtilsService as convertToFieldType } from '@/services/records'

// Re-export the refactored main component
export { RecordListView } from '@/components/pipelines/record-list'

// For any components that import specific pieces, we maintain compatibility
export type { 
  Filter,
  FilterOperator,
  ViewMode,
  Sort,
  SortDirection
} from '@/types/records'