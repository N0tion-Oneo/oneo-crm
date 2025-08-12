// RecordListView - Refactored orchestration component using extracted hooks, services, and components
'use client'

import React, { useState, useMemo } from 'react'
import { Plus } from 'lucide-react'

// Import types
import { 
  Record, 
  Pipeline, 
  RecordListViewProps, 
  ViewMode,
  RecordField
} from '@/types/records'

// Import hooks
import {
  useRecordData,
  useRecordSelection, 
  useRecordFilters,
  useRecordSorting,
  useFieldOptions,
  useRealtimeUpdates
} from '@/hooks/records'

// Import services
import { FieldUtilsService, FilterTransformService } from '@/services/records'

// Import components
import {
  SearchBar,
  ViewModeToggle,
  RealtimeStatus, 
  LoadingState,
  ErrorState,
  RecordActions,
  RecordTable,
  FilterPanel,
  FieldColumnManager,
  Pagination
} from '@/components/pipelines/record-list'

// Import existing view components
import { KanbanView } from '@/components/pipelines/kanban-view'
import { CalendarView } from '@/components/pipelines/calendar-view'

export function RecordListView({ pipeline, onEditRecord, onCreateRecord }: RecordListViewProps) {
  // View state
  const [viewMode, setViewMode] = useState<ViewMode>('table')
  const [visibleFields, setVisibleFields] = useState<Set<string>>(new Set())
  const [kanbanField, setKanbanField] = useState<string>('')
  const [calendarField, setCalendarField] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')

  // Initialize sorting
  const { sort, handleSort } = useRecordSorting({ field: 'updated_at', direction: 'desc' })

  // Initialize filtering
  const filterHook = useRecordFilters()
  const { 
    booleanQuery,
    appliedFilters, 
    showFilters, 
    toggleFilterPanel,
    hideFilterPanel,
    hasActiveFilters,
    activeFilterCount,
    applyFilters,
    updateBooleanQuery
  } = filterHook

  // Initialize record selection
  const {
    selectedRecords,
    hasSelection,
    selectedCount,
    toggleRecord,
    toggleSelectAll,
    unselectAll,
    getSelectedRecordIds
  } = useRecordSelection()

  // Initialize record data with dependencies
  const recordData = useRecordData({
    pipeline,
    searchQuery,
    filters: appliedFilters,
    sort,
    recordsPerPage: 50,
    autoFetch: true
  })

  const {
    records,
    loading,
    error,
    pagination,
    refreshRecords,
    bulkUpdateRecords,
    bulkDeleteRecords,
    exportRecords,
    addRecord,
    updateRecordInState,
    removeRecordFromState
  } = recordData

  // Initialize field options
  const { fetchFieldOptions } = useFieldOptions(pipeline)

  // Initialize real-time updates
  const { isConnected } = useRealtimeUpdates(pipeline, {
    onRecordCreate: addRecord,
    onRecordUpdate: updateRecordInState,
    onRecordDelete: removeRecordFromState,
    onError: (error) => console.error('Real-time error:', error)
  })

  // Memoized field computations (must come before useEffects that use them)
  const visibleFieldsList = useMemo(() => {
    const visibleFieldsArray = pipeline.fields.filter(field => visibleFields.has(field.name))
    
    // If no field groups, fallback to regular sorting
    if (!pipeline.field_groups || pipeline.field_groups.length === 0) {
      return visibleFieldsArray.sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
    }

    // Group fields by field_group
    const groups = new Map<string | null, RecordField[]>()
    
    // Organize visible fields by group
    visibleFieldsArray.forEach(field => {
      // Normalize field group ID to string for consistent comparison
      const groupId = field.field_group ? String(field.field_group) : null
      if (!groups.has(groupId)) {
        groups.set(groupId, [])
      }
      groups.get(groupId)!.push(field)
    })
    
    // Sort fields within each group by display_order
    groups.forEach(groupFields => {
      groupFields.sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
    })
    
    // Sort groups by display order and flatten
    const sortedFields: RecordField[] = []
    
    // Process defined field groups first (sorted by display_order)
    const sortedFieldGroups = [...pipeline.field_groups].sort((a, b) => a.display_order - b.display_order)
    
    sortedFieldGroups.forEach(group => {
      const groupFields = groups.get(String(group.id))
      if (groupFields && groupFields.length > 0) {
        sortedFields.push(...groupFields)
      }
    })
    
    // Add ungrouped fields last
    const ungroupedFields = groups.get(null)
    if (ungroupedFields && ungroupedFields.length > 0) {
      sortedFields.push(...ungroupedFields)
    }
    
    return sortedFields
  }, [pipeline.fields, visibleFields, pipeline.field_groups])

  const selectFields = useMemo(() => 
    FieldUtilsService.getSelectFields(pipeline.fields),
    [pipeline.fields]
  )

  const dateFields = useMemo(() => 
    FieldUtilsService.getDateFields(pipeline.fields),
    [pipeline.fields]
  )

  // Initialize visible fields when pipeline changes
  React.useEffect(() => {
    const defaultVisible = FieldUtilsService.getDefaultVisibleFields(pipeline.fields)
    setVisibleFields(defaultVisible)
  }, [pipeline.fields])

  // Auto-select default fields for views
  React.useEffect(() => {
    if (!kanbanField && selectFields.length > 0) {
      // Look for common status/stage field names first
      const statusField = selectFields.find(f => 
        ['status', 'stage', 'phase', 'state', 'pipeline_stage'].includes(f.value.toLowerCase())
      )
      setKanbanField(statusField?.value || selectFields[0].value)
    }
    if (!calendarField && dateFields.length > 0) {
      // Look for common date field names first
      const dateField = dateFields.find(f => 
        ['due_date', 'start_date', 'end_date', 'created_at', 'updated_at'].includes(f.value.toLowerCase())
      )
      setCalendarField(dateField?.value || dateFields[0].value)
    }
  }, [selectFields, dateFields, kanbanField, calendarField])

  // Event handlers  
  const handleBooleanQueryChange = (newQuery: typeof booleanQuery) => {
    updateBooleanQuery(newQuery)
  }

  const handleBulkUpdate = async () => {
    const selectedIds = getSelectedRecordIds()
    if (selectedIds.length === 0) return

    // TODO: Implement bulk update UI
    console.log('Bulk update:', selectedIds)
  }

  const handleBulkDelete = async () => {
    const selectedIds = getSelectedRecordIds()
    if (selectedIds.length === 0) return

    if (!window.confirm(`Delete ${selectedIds.length} selected records?`)) return

    try {
      await bulkDeleteRecords(selectedIds)
      unselectAll()
    } catch (error) {
      console.error('Bulk delete failed:', error)
    }
  }

  const handleExport = async (format: 'csv' | 'json' | 'excel') => {
    try {
      const blob = await exportRecords(format)
      
      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${pipeline.name}-records.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export failed:', error)
    }
  }

  // Loading state
  if (loading && records.length === 0) {
    return <LoadingState />
  }

  // Error state
  if (error && records.length === 0) {
    return (
      <ErrorState 
        error={error} 
        onRetry={() => window.location.reload()} 
      />
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {pipeline.name}
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              {pipeline.description}
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={onCreateRecord}
              className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
            >
              <Plus className="w-4 h-4 mr-2 inline" />
              Add Record
            </button>
            
            <RealtimeStatus isConnected={isConnected} />
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <ViewModeToggle
              viewMode={viewMode}
              onViewModeChange={setViewMode}
              selectFields={selectFields}
              dateFields={dateFields}
            />

            <SearchBar
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              placeholder="Search records..."
            />
            
            <button
              onClick={toggleFilterPanel}
              className={`px-3 py-2 border rounded-md flex items-center ${
                showFilters 
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M3 3a1 1 0 011-1h12a1 1 0 011 1v3a1 1 0 01-.293.707L12 11.414V15a1 1 0 01-.293.707l-2 2A1 1 0 018 17v-5.586L3.293 6.707A1 1 0 013 6V3z" clipRule="evenodd" />
              </svg>
              Filters {activeFilterCount > 0 && `(${activeFilterCount})`}
            </button>

            <FieldColumnManager
              fields={pipeline.fields}
              visibleFields={visibleFields}
              onVisibleFieldsChange={setVisibleFields}
            />
          </div>

          <RecordActions
            selectedCount={selectedCount}
            onBulkUpdate={handleBulkUpdate}
            onBulkDelete={handleBulkDelete}
            onExport={handleExport}
            onRefresh={refreshRecords}
            onClearSelection={unselectAll}
          />
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <FilterPanel
          booleanQuery={booleanQuery}
          onBooleanQueryChange={handleBooleanQueryChange}
          pipeline={pipeline}
          showFilters={showFilters}
          onClose={hideFilterPanel}
          onGetFieldOptions={fetchFieldOptions}
        />
      )}

      {/* View Configuration Panel */}
      {(viewMode === 'kanban' || viewMode === 'calendar') && (
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-6">
            {viewMode === 'kanban' && selectFields.length > 0 && (
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Group by:
                </label>
                <select
                  value={kanbanField}
                  onChange={(e) => setKanbanField(e.target.value)}
                  className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-sm"
                >
                  {selectFields.map(field => (
                    <option key={field.value} value={field.value}>
                      {field.label} ({field.options.length} options)
                    </option>
                  ))}
                </select>
              </div>
            )}
            
            {viewMode === 'calendar' && dateFields.length > 0 && (
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Date field:
                </label>
                <select
                  value={calendarField}
                  onChange={(e) => setCalendarField(e.target.value)}
                  className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-sm"
                >
                  {dateFields.map(field => (
                    <option key={field.value} value={field.value}>
                      {field.label} ({field.type})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 overflow-auto">
        {viewMode === 'table' && (
          <RecordTable
            records={records}
            fields={visibleFieldsList}
            fieldGroups={pipeline.field_groups}
            sort={sort}
            onSort={handleSort}
            selectedRecords={selectedRecords}
            onSelectRecord={toggleRecord}
            onSelectAll={() => toggleSelectAll(records)}
            onEditRecord={onEditRecord}
            pipelineId={pipeline.id}
          />
        )}

        {viewMode === 'kanban' && selectFields.length > 0 && (
          <KanbanView
            records={records}
            pipeline={pipeline}
            kanbanField={kanbanField || selectFields[0]?.value || ''}
            onEditRecord={onEditRecord}
            onCreateRecord={onCreateRecord}
            onUpdateRecord={async (recordId: string, fieldName: string, value: any) => {
              // This will be handled by real-time updates
              await recordData.updateRecord(recordId, { [fieldName]: value })
            }}
          />
        )}

        {viewMode === 'calendar' && dateFields.length > 0 && (
          <CalendarView
            records={records}
            pipeline={pipeline}
            calendarField={calendarField || dateFields[0]?.value || ''}
            onEditRecord={onEditRecord}
            onCreateRecord={onCreateRecord}
          />
        )}
      </div>

      {/* Status bar with pagination */}
      {pagination.totalRecords > 0 && (
        <div className="px-6 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <Pagination
            currentPage={pagination.currentPage}
            totalPages={pagination.totalPages}
            totalRecords={pagination.totalRecords}
            recordsPerPage={pagination.recordsPerPage}
            onPageChange={recordData.setPage}
            onNextPage={recordData.nextPage}
            onPreviousPage={recordData.previousPage}
            hasNext={pagination.hasNext}
            hasPrevious={pagination.hasPrevious}
          />
        </div>
      )}
    </div>
  )
}