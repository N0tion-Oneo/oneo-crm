// Filter and query-related type definitions extracted from record-list-view.tsx

export type FilterOperator = 
  | 'equals' 
  | 'contains' 
  | 'starts_with' 
  | 'ends_with' 
  | 'greater_than' 
  | 'less_than' 
  | 'is_empty' 
  | 'is_not_empty'

export interface Filter {
  field: string
  operator: FilterOperator
  value: any
}

export interface FilterGroup {
  id: string
  logic: 'AND' | 'OR'
  filters: Filter[]
}

export interface BooleanQuery {
  groups: FilterGroup[]
  groupLogic: 'AND' | 'OR'
}

export interface FieldOption {
  value: string
  label: string
}

export interface SelectFieldOption {
  value: string
  label: string
  options: any[]
}

export interface DateFieldOption {
  value: string
  label: string
  type: 'date' | 'datetime'
}