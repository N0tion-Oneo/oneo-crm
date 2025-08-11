// useRecordData - Hook for managing record data fetching, pagination, and CRUD operations
import { useState, useEffect, useCallback } from 'react'
import { Record, Pipeline, Filter, Sort } from '@/types/records'
import { RecordDataService, FetchRecordsResponse } from '@/services/records'

export interface UseRecordDataReturn {
  records: Record[]
  loading: boolean
  error: string | null
  pagination: {
    currentPage: number
    recordsPerPage: number
    totalRecords: number
    totalPages: number
    hasNext: boolean
    hasPrevious: boolean
  }
  // Actions
  fetchRecords: () => Promise<void>
  refreshRecords: () => Promise<void>
  createRecord: (data: Record['data']) => Promise<Record>
  updateRecord: (recordId: string, data: Partial<Record['data']>) => Promise<Record>
  deleteRecord: (recordId: string) => Promise<void>
  bulkUpdateRecords: (recordIds: string[], data: Record['data']) => Promise<void>
  bulkDeleteRecords: (recordIds: string[]) => Promise<void>
  exportRecords: (format: 'csv' | 'json' | 'excel') => Promise<Blob>
  // Pagination
  setPage: (page: number) => void
  nextPage: () => void
  previousPage: () => void
  // Direct state updates (for real-time updates)
  addRecord: (record: Record) => void
  updateRecordInState: (record: Record) => void
  removeRecordFromState: (recordId: string) => void
  setRecords: (records: Record[]) => void
}

export interface UseRecordDataOptions {
  pipeline: Pipeline
  searchQuery?: string
  filters?: Filter[]
  sort?: Sort
  recordsPerPage?: number
  autoFetch?: boolean
}

export function useRecordData(options: UseRecordDataOptions): UseRecordDataReturn {
  const {
    pipeline,
    searchQuery = '',
    filters = [],
    sort,
    recordsPerPage = 50,
    autoFetch = true
  } = options

  const [records, setRecords] = useState<Record[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalRecords, setTotalRecords] = useState(0)
  const [totalPages, setTotalPages] = useState(0)

  const fetchRecords = useCallback(async () => {
    if (!pipeline?.id) return

    setLoading(true)
    setError(null)

    try {
      // Create field types map for proper filter handling
      const fieldTypes: Record<string, string> = {}
      pipeline.fields.forEach(field => {
        fieldTypes[field.name] = field.field_type
      })

      const response: FetchRecordsResponse = await RecordDataService.fetchRecords({
        pipelineId: pipeline.id,
        page: currentPage,
        pageSize: recordsPerPage,
        search: searchQuery.trim() || undefined,
        filters: filters.length > 0 ? filters : undefined,
        sort,
        fieldTypes
      })

      setRecords(response.results)
      setTotalRecords(response.count)
      setTotalPages(Math.ceil(response.count / recordsPerPage))
    } catch (err: any) {
      console.error('Failed to fetch records:', err)
      setError(err?.message || 'Failed to load records')
    } finally {
      setLoading(false)
    }
  }, [pipeline.id, pipeline.fields, currentPage, recordsPerPage, searchQuery, filters, sort])

  const refreshRecords = useCallback(async () => {
    await fetchRecords()
  }, [fetchRecords])

  const createRecord = useCallback(async (data: Record['data']): Promise<Record> => {
    const newRecord = await RecordDataService.createRecord(pipeline.id, data)
    // Don't add to state here - let real-time updates handle it
    return newRecord
  }, [pipeline.id])

  const updateRecord = useCallback(async (
    recordId: string, 
    data: Partial<Record['data']>
  ): Promise<Record> => {
    const updatedRecord = await RecordDataService.updateRecord(pipeline.id, recordId, data)
    // Don't update state here - let real-time updates handle it
    return updatedRecord
  }, [pipeline.id])

  const deleteRecord = useCallback(async (recordId: string): Promise<void> => {
    await RecordDataService.deleteRecord(pipeline.id, recordId)
    // Don't remove from state here - let real-time updates handle it
  }, [pipeline.id])

  const bulkUpdateRecords = useCallback(async (
    recordIds: string[], 
    data: Record['data']
  ): Promise<void> => {
    await RecordDataService.bulkUpdateRecords(pipeline.id, recordIds, data)
    // Refresh records after bulk operation
    await fetchRecords()
  }, [pipeline.id, fetchRecords])

  const bulkDeleteRecords = useCallback(async (recordIds: string[]): Promise<void> => {
    await RecordDataService.bulkDeleteRecords(pipeline.id, recordIds)
    // Refresh records after bulk operation
    await fetchRecords()
  }, [pipeline.id, fetchRecords])

  const exportRecords = useCallback(async (
    format: 'csv' | 'json' | 'excel'
  ): Promise<Blob> => {
    return RecordDataService.exportRecords(
      pipeline.id, 
      format, 
      filters.length > 0 ? filters : undefined,
      searchQuery.trim() || undefined
    )
  }, [pipeline.id, filters, searchQuery])

  // Pagination controls
  const setPage = useCallback((page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page)
    }
  }, [totalPages])

  const nextPage = useCallback(() => {
    if (currentPage < totalPages) {
      setCurrentPage(prev => prev + 1)
    }
  }, [currentPage, totalPages])

  const previousPage = useCallback(() => {
    if (currentPage > 1) {
      setCurrentPage(prev => prev - 1)
    }
  }, [currentPage])

  // Direct state updates for real-time updates
  const addRecord = useCallback((record: Record) => {
    setRecords(prev => [record, ...prev])
    setTotalRecords(prev => prev + 1)
  }, [])

  const updateRecordInState = useCallback((updatedRecord: Record) => {
    setRecords(prev => 
      prev.map(record => 
        String(record.id) === String(updatedRecord.id)
          ? { ...record, ...updatedRecord, data: { ...record.data, ...updatedRecord.data } }
          : record
      )
    )
  }, [])

  const removeRecordFromState = useCallback((recordId: string) => {
    setRecords(prev => prev.filter(record => String(record.id) !== String(recordId)))
    setTotalRecords(prev => Math.max(0, prev - 1))
  }, [])

  // Auto-fetch when dependencies change
  useEffect(() => {
    if (autoFetch && pipeline?.id) {
      fetchRecords()
    }
  }, [fetchRecords, autoFetch, pipeline?.id])

  // Reset page when search/filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [searchQuery, filters, sort])

  const pagination = {
    currentPage,
    recordsPerPage,
    totalRecords,
    totalPages,
    hasNext: currentPage < totalPages,
    hasPrevious: currentPage > 1
  }

  return {
    records,
    loading,
    error,
    pagination,
    fetchRecords,
    refreshRecords,
    createRecord,
    updateRecord,
    deleteRecord,
    bulkUpdateRecords,
    bulkDeleteRecords,
    exportRecords,
    setPage,
    nextPage,
    previousPage,
    addRecord,
    updateRecordInState,
    removeRecordFromState,
    setRecords
  }
}