// useRecordSelection - Hook for managing record selection state
import { useState, useCallback, useMemo } from 'react'
import { Record } from '@/types/records'

export interface UseRecordSelectionReturn {
  selectedRecords: Set<string>
  isAllSelected: boolean
  hasSelection: boolean
  selectedCount: number
  // Actions
  selectRecord: (recordId: string) => void
  unselectRecord: (recordId: string) => void
  toggleRecord: (recordId: string) => void
  selectAll: (records: Record[]) => void
  unselectAll: () => void
  toggleSelectAll: (records: Record[]) => void
  isRecordSelected: (recordId: string) => boolean
  // Bulk operations
  getSelectedRecords: (records: Record[]) => Record[]
  getSelectedRecordIds: () => string[]
  selectRecords: (recordIds: string[]) => void
  unselectRecords: (recordIds: string[]) => void
}

export function useRecordSelection(): UseRecordSelectionReturn {
  const [selectedRecords, setSelectedRecords] = useState<Set<string>>(new Set())

  const selectRecord = useCallback((recordId: string) => {
    setSelectedRecords(prev => new Set([...prev, recordId]))
  }, [])

  const unselectRecord = useCallback((recordId: string) => {
    setSelectedRecords(prev => {
      const newSet = new Set(prev)
      newSet.delete(recordId)
      return newSet
    })
  }, [])

  const toggleRecord = useCallback((recordId: string) => {
    setSelectedRecords(prev => {
      const newSet = new Set(prev)
      if (newSet.has(recordId)) {
        newSet.delete(recordId)
      } else {
        newSet.add(recordId)
      }
      return newSet
    })
  }, [])

  const selectAll = useCallback((records: Record[]) => {
    const recordIds = records.map(record => record.id)
    setSelectedRecords(new Set(recordIds))
  }, [])

  const unselectAll = useCallback(() => {
    setSelectedRecords(new Set())
  }, [])

  const toggleSelectAll = useCallback((records: Record[]) => {
    const allSelected = records.length > 0 && records.every(record => selectedRecords.has(record.id))
    
    if (allSelected) {
      unselectAll()
    } else {
      selectAll(records)
    }
  }, [selectedRecords, selectAll, unselectAll])

  const isRecordSelected = useCallback((recordId: string) => {
    return selectedRecords.has(recordId)
  }, [selectedRecords])

  const getSelectedRecords = useCallback((records: Record[]) => {
    return records.filter(record => selectedRecords.has(record.id))
  }, [selectedRecords])

  const getSelectedRecordIds = useCallback(() => {
    return Array.from(selectedRecords)
  }, [selectedRecords])

  const selectRecords = useCallback((recordIds: string[]) => {
    setSelectedRecords(prev => new Set([...prev, ...recordIds]))
  }, [])

  const unselectRecords = useCallback((recordIds: string[]) => {
    setSelectedRecords(prev => {
      const newSet = new Set(prev)
      recordIds.forEach(id => newSet.delete(id))
      return newSet
    })
  }, [])

  // Computed properties
  const isAllSelected = useMemo(() => (records: Record[]) => {
    return records.length > 0 && records.every(record => selectedRecords.has(record.id))
  }, [selectedRecords])

  const hasSelection = selectedRecords.size > 0
  const selectedCount = selectedRecords.size

  return {
    selectedRecords,
    isAllSelected: isAllSelected([]), // This will be called with records from component
    hasSelection,
    selectedCount,
    selectRecord,
    unselectRecord,
    toggleRecord,
    selectAll,
    unselectAll,
    toggleSelectAll,
    isRecordSelected,
    getSelectedRecords,
    getSelectedRecordIds,
    selectRecords,
    unselectRecords
  }
}