// useRecordFilters - Hook for managing advanced filtering and boolean queries
import React, { useState, useCallback, useMemo } from 'react'
import { 
  Filter, 
  FilterGroup, 
  BooleanQuery, 
  FilterOperator, 
  RecordField 
} from '@/types/records'
import { FilterTransformService } from '@/services/records'

export interface UseRecordFiltersReturn {
  // State
  booleanQuery: BooleanQuery
  appliedFilters: Filter[]
  showFilters: boolean
  // Boolean query operations
  addFilter: (groupId: string, filter: Filter) => void
  removeFilter: (groupId: string, filterIndex: number) => void
  addGroup: (logic?: 'AND' | 'OR') => void
  removeGroup: (groupId: string) => void
  updateGroupLogic: (groupId: string, logic: 'AND' | 'OR') => void
  updateQueryLogic: (logic: 'AND' | 'OR') => void
  updateBooleanQuery: (query: BooleanQuery) => void
  clearFilters: () => void
  // Applied filters
  applyFilters: () => void
  resetFilters: () => void
  // UI state
  toggleFilterPanel: () => void
  hideFilterPanel: () => void
  showFilterPanel: () => void
  // Helper functions
  getOperatorsForField: (fieldType: string) => FilterOperator[]
  validateFilter: (fieldType: string, operator: FilterOperator, value: any) => boolean
  getFilterDisplayText: (filter: Filter) => string
  hasActiveFilters: boolean
  activeFilterCount: number
}

export function useRecordFilters(): UseRecordFiltersReturn {
  const [booleanQuery, setBooleanQuery] = useState<BooleanQuery>({
    groups: [{
      id: 'group-1',
      logic: 'AND',
      filters: []
    }],
    groupLogic: 'AND'
  })

  const [appliedFilters, setAppliedFilters] = useState<Filter[]>([])
  const [showFilters, setShowFilters] = useState(false)

  // Boolean query operations
  const addFilter = useCallback((groupId: string, filter: Filter) => {
    setBooleanQuery(prev => 
      FilterTransformService.addFilterToGroup(prev, groupId, filter)
    )
  }, [])

  const removeFilter = useCallback((groupId: string, filterIndex: number) => {
    setBooleanQuery(prev => 
      FilterTransformService.removeFilterFromGroup(prev, groupId, filterIndex)
    )
  }, [])

  const addGroup = useCallback((logic: 'AND' | 'OR' = 'AND') => {
    setBooleanQuery(prev => 
      FilterTransformService.addFilterGroup(prev, logic)
    )
  }, [])

  const removeGroup = useCallback((groupId: string) => {
    setBooleanQuery(prev => 
      FilterTransformService.removeFilterGroup(prev, groupId)
    )
  }, [])

  const updateGroupLogic = useCallback((groupId: string, logic: 'AND' | 'OR') => {
    setBooleanQuery(prev => 
      FilterTransformService.updateGroupLogic(prev, groupId, logic)
    )
  }, [])

  const updateQueryLogic = useCallback((logic: 'AND' | 'OR') => {
    setBooleanQuery(prev => ({ ...prev, groupLogic: logic }))
  }, [])

  const updateBooleanQuery = useCallback((newQuery: BooleanQuery) => {
    setBooleanQuery(newQuery)
  }, [])

  const clearFilters = useCallback(() => {
    setBooleanQuery({
      groups: [{
        id: 'group-1',
        logic: 'AND',
        filters: []
      }],
      groupLogic: 'AND'
    })
    setAppliedFilters([])
  }, [])

  // // Automatically apply filters when boolean query changes (matching original behavior)
  // React.useEffect(() => {
  //   const allFilters: Filter[] = []
  //   booleanQuery.groups.forEach(group => {
  //     allFilters.push(...group.filters)
  //   })
  //   setAppliedFilters(allFilters)
  // }, [booleanQuery])

  // Applied filters management
  const applyFilters = useCallback(() => {
    const flatFilters = FilterTransformService.transformBooleanQueryToFilters(booleanQuery)
    setAppliedFilters(flatFilters)
  }, [booleanQuery])

  const resetFilters = useCallback(() => {
    clearFilters()
  }, [clearFilters])

  // UI state management
  const toggleFilterPanel = useCallback(() => {
    setShowFilters(prev => !prev)
  }, [])

  const hideFilterPanel = useCallback(() => {
    setShowFilters(false)
  }, [])

  const showFilterPanel = useCallback(() => {
    setShowFilters(true)
  }, [])

  // Helper functions
  const getOperatorsForField = useCallback((fieldType: string): FilterOperator[] => {
    return FilterTransformService.getOperatorsForFieldType(fieldType)
  }, [])

  const validateFilter = useCallback((
    fieldType: string, 
    operator: FilterOperator, 
    value: any
  ): boolean => {
    return FilterTransformService.validateFilterValue(fieldType, operator, value)
  }, [])

  const getFilterDisplayText = useCallback((filter: Filter): string => {
    return FilterTransformService.getFilterDisplayText(filter)
  }, [])

  // Computed properties
  const hasActiveFilters = useMemo(() => {
    return FilterTransformService.hasActiveFilters(booleanQuery)
  }, [booleanQuery])

  const activeFilterCount = useMemo(() => {
    return FilterTransformService.countActiveFilters(booleanQuery)
  }, [booleanQuery])

  return {
    // State
    booleanQuery,
    appliedFilters,
    showFilters,
    // Boolean query operations
    addFilter,
    removeFilter,
    addGroup,
    removeGroup,
    updateGroupLogic,
    updateQueryLogic,
    updateBooleanQuery,
    clearFilters,
    // Applied filters
    applyFilters,
    resetFilters,
    // UI state
    toggleFilterPanel,
    hideFilterPanel,
    showFilterPanel,
    // Helper functions
    getOperatorsForField,
    validateFilter,
    getFilterDisplayText,
    hasActiveFilters,
    activeFilterCount
  }
}