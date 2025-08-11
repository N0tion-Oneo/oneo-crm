// View and display-related type definitions extracted from record-list-view.tsx

export type ViewMode = 'table' | 'kanban' | 'calendar'

export type SortDirection = 'asc' | 'desc' | null

export interface Sort {
  field: string
  direction: SortDirection
}

export interface PaginationState {
  currentPage: number
  recordsPerPage: number
  totalRecords: number
  totalPages: number
}

export interface RecordSelectionState {
  selectedRecords: Set<string>
  isAllSelected: boolean
  hasSelection: boolean
}

export interface ViewConfiguration {
  viewMode: ViewMode
  visibleFields: Set<string>
  kanbanField: string
  calendarField: string
}

export interface SearchState {
  searchQuery: string
  debouncedSearchQuery: string
}