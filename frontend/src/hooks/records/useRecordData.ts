// useRecordData - Hook for managing record data fetching, pagination, and CRUD operations
import { useState, useEffect, useCallback, useMemo } from 'react'
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
  const [showLoading, setShowLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalRecords, setTotalRecords] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  
  // Track if we've fetched data to prevent showing loading spinner on initial render
  const [hasFetchedOnce, setHasFetchedOnce] = useState(false)

  // Create stable field types reference to prevent unnecessary re-renders
  const fieldTypes = useMemo(() => {
    const types: {[key: string]: string} = {}
    pipeline.fields.forEach(field => {
      types[field.name] = field.field_type
    })
    return types
  }, [pipeline.fields])

  // Stable filters reference to prevent re-renders when filters array reference changes
  const stableFilters = useMemo(() => {
    return filters.length > 0 ? filters : undefined
  }, [filters])

  // Stable search query to prevent re-renders
  const stableSearchQuery = useMemo(() => {
    return searchQuery.trim() || undefined
  }, [searchQuery])

  // Never show loading spinner on first load
  useEffect(() => {
    if (loading && hasFetchedOnce) {
      // Only show spinner for subsequent loads (pagination, filters, etc)
      setShowLoading(true)
    } else {
      setShowLoading(false)
    }
  }, [loading, hasFetchedOnce])

  const fetchRecords = useCallback(async () => {
    if (!pipeline?.id) return

    console.log('🔄 fetchRecords called', {
      pipelineId: pipeline.id,
      page: currentPage,
      hasFields: pipeline.fields?.length > 0,
      timestamp: new Date().toISOString()
    })

    setLoading(true)
    setError(null)

    try {
      const response: FetchRecordsResponse = await RecordDataService.fetchRecords({
        pipelineId: pipeline.id,
        page: currentPage,
        pageSize: recordsPerPage,
        search: stableSearchQuery,
        filters: stableFilters,
        sort,
        fieldTypes
      })

      setRecords(response.results)
      setTotalRecords(response.count)
      setTotalPages(Math.ceil(response.count / recordsPerPage))
      setHasFetchedOnce(true)
    } catch (err: any) {
      console.error('Failed to fetch records:', err)
      setError(err?.message || 'Failed to load records')
    } finally {
      setLoading(false)
      setHasFetchedOnce(true)
    }
  }, [pipeline.id, currentPage, recordsPerPage, stableSearchQuery, stableFilters, sort, fieldTypes])

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
    // Note: fetchRecords is intentionally omitted from dependencies to prevent loops
    // fieldTypes is also omitted as it's derived from pipeline and would cause duplicate fetches
    // We only depend on pipeline.id (not the whole pipeline object) to prevent re-fetches when fields load
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoFetch, pipeline?.id, currentPage, recordsPerPage, stableSearchQuery, stableFilters, sort])

  // Reset page when search/filters change
  useEffect(() => {
    // Only reset to page 1 if we're not already on page 1
    // This prevents unnecessary re-fetches
    if (currentPage !== 1) {
      setCurrentPage(1)
    }
    // Note: currentPage should NOT be in the dependency array to prevent infinite loop
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stableSearchQuery, stableFilters, sort])

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
    loading: showLoading,  // Only show loading on subsequent fetches, never on first load
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