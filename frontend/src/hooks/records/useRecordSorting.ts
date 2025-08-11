// useRecordSorting - Hook for managing table sorting and ordering
import { useState, useCallback } from 'react'
import { Sort, SortDirection } from '@/types/records'

export interface UseRecordSortingReturn {
  sort: Sort
  handleSort: (field: string) => void
  setSortField: (field: string) => void
  setSortDirection: (direction: SortDirection) => void
  setSort: (sort: Sort) => void
  clearSort: () => void
  isSorted: (field: string) => boolean
  getSortDirection: (field: string) => SortDirection
}

export function useRecordSorting(
  initialSort: Sort = { field: 'updated_at', direction: 'desc' }
): UseRecordSortingReturn {
  const [sort, setSort] = useState<Sort>(initialSort)

  const handleSort = useCallback((field: string) => {
    setSort(prevSort => {
      // If clicking the same field, toggle direction
      if (prevSort.field === field) {
        const newDirection: SortDirection = 
          prevSort.direction === 'asc' ? 'desc' : 
          prevSort.direction === 'desc' ? null : 'asc'
        
        return {
          field: newDirection ? field : 'updated_at', // Default field when no sort
          direction: newDirection || 'desc' // Default direction
        }
      }
      
      // If clicking a different field, start with ascending
      return {
        field,
        direction: 'asc'
      }
    })
  }, [])

  const setSortField = useCallback((field: string) => {
    setSort(prev => ({ ...prev, field }))
  }, [])

  const setSortDirection = useCallback((direction: SortDirection) => {
    setSort(prev => ({ ...prev, direction }))
  }, [])

  const clearSort = useCallback(() => {
    setSort({ field: 'updated_at', direction: 'desc' })
  }, [])

  const isSorted = useCallback((field: string) => {
    return sort.field === field && sort.direction !== null
  }, [sort])

  const getSortDirection = useCallback((field: string): SortDirection => {
    return sort.field === field ? sort.direction : null
  }, [sort])

  return {
    sort,
    handleSort,
    setSortField,
    setSortDirection,
    setSort,
    clearSort,
    isSorted,
    getSortDirection
  }
}