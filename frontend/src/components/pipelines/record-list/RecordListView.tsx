// RecordListView - Refactored orchestration component using extracted hooks, services, and components
'use client'

import React, { useState, useMemo, useEffect } from 'react'
import { Plus, Lock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/context'
import { PermissionGuard } from '@/components/permissions/PermissionGuard'

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
import { pipelinesApi } from '@/lib/api'

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

// Import saved filters types only (modals now handled in FilterPanel)
import { 
  SavedFilter 
} from '@/components/pipelines/saved-filters'

export function RecordListView({ pipeline: initialPipeline, onEditRecord, onCreateRecord }: RecordListViewProps) {
  const { hasPermission } = useAuth()
  
  // Check permissions
  const canCreateRecords = hasPermission('records', 'create')
  const canUpdateRecords = hasPermission('records', 'update')
  const canDeleteRecords = hasPermission('records', 'delete')
  const hasReadAllPermission = hasPermission('records', 'read_all')
  const hasReadPermission = hasPermission('records', 'read')
  
  // Internal pipeline state to handle minimal pipeline from parent
  const [pipeline, setPipeline] = useState(initialPipeline)
  
  // Load complete pipeline data if we received a minimal one
  useEffect(() => {
    const loadCompletePipeline = async () => {
      if (pipeline.fields.length === 0 && pipeline.id) {
        try {
          const [pipelineResponse, fieldGroupsResponse] = await Promise.all([
            pipelinesApi.get(pipeline.id),
            pipelinesApi.getFieldGroups(pipeline.id)
          ])
          
          const fieldGroups = (fieldGroupsResponse.data as any)?.results || fieldGroupsResponse.data || []
          
          const completePipeline = {
            id: pipelineResponse.data.id?.toString() || pipeline.id,
            name: pipelineResponse.data.name || 'Unknown Pipeline',
            description: pipelineResponse.data.description || '',
            record_count: pipelineResponse.data.record_count || 0,
            fields: (pipelineResponse.data.fields || []).map((field: any) => ({
              id: field.id?.toString() || `field_${Date.now()}`,
              name: field.slug || field.name?.toLowerCase().replace(/\s+/g, '_'),
              display_name: field.name || field.display_name || field.slug || 'Unknown Field',
              field_type: field.field_type || 'text',
              is_visible_in_list: field.is_visible_in_list !== false,
              is_visible_in_detail: field.is_visible_in_detail !== false,
              is_visible_in_public_forms: field.is_visible_in_public_forms || false,
              display_order: field.display_order || 0,
              field_config: field.field_config || {},
              config: field.field_config || {},
              ai_config: field.ai_config || {},
              original_slug: field.slug,
              business_rules: field.business_rules || {},
              field_group: field.field_group?.toString() || null
            })),
            field_groups: fieldGroups.map((group: any) => ({
              id: group.id?.toString() || `group_${Date.now()}`,
              name: group.name || 'Unknown Group',
              description: group.description || '',
              color: group.color || '#3B82F6',
              icon: group.icon || 'folder',
              display_order: group.display_order || 0,
              field_count: group.field_count || 0
            })),
            stages: pipelineResponse.data.stages || []
          }
          
          setPipeline(completePipeline)
        } catch (error) {
          console.error('Failed to load complete pipeline data:', error)
        }
      }
    }
    
    loadCompletePipeline()
  }, [pipeline.id, pipeline.fields.length])
  
  // View state
  const [viewMode, setViewMode] = useState<ViewMode>('table')
  const [visibleFields, setVisibleFields] = useState<Set<string>>(new Set())
  const [kanbanField, setKanbanField] = useState<string>('')
  const [calendarField, setCalendarField] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  
  // Track currently applied saved filter
  const [currentSavedFilter, setCurrentSavedFilter] = useState<any>(null)
  const [isFilterModified, setIsFilterModified] = useState(false)

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

  // Saved filters functionality moved to FilterPanel

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
    // Mark filter as modified when user manually changes filters
    if (currentSavedFilter && !isFilterModified) {
      setIsFilterModified(true)
    }
    updateBooleanQuery(newQuery)
    // Filters are now automatically applied via useEffect in useRecordFilters hook
  }

  // Wrapper for view mode changes to mark filter as modified
  const handleViewModeChange = (newViewMode: ViewMode) => {
    if (currentSavedFilter && !isFilterModified && newViewMode !== currentSavedFilter.view_mode) {
      setIsFilterModified(true)
    }
    setViewMode(newViewMode)
  }

  // Wrapper for visible fields changes to mark filter as modified
  const handleVisibleFieldsChange = (newVisibleFields: Set<string>) => {
    if (currentSavedFilter && !isFilterModified) {
      // Check if visible fields have changed from saved filter
      const savedFields = new Set(currentSavedFilter.visible_fields || [])
      const hasChanges = newVisibleFields.size !== savedFields.size || 
        [...newVisibleFields].some(field => !savedFields.has(field))
      
      if (hasChanges) {
        setIsFilterModified(true)
      }
    }
    setVisibleFields(newVisibleFields)
  }


  // Handler to clear saved filter context
  const handleClearSavedFilter = () => {
    setCurrentSavedFilter(null)
    setIsFilterModified(false)
  }

  // Saved filters handlers
  const handleFilterSelect = (filter: SavedFilter) => {
    console.log('📋 RecordListView: Applying saved filter:', filter.name)
    console.log('📋 Filter config:', filter.filter_config)
    console.log('📋 Filter view mode:', filter.view_mode)
    console.log('📋 Filter visible fields:', filter.visible_fields)
    
    // Track the currently applied saved filter and reset modified state
    setCurrentSavedFilter(filter)
    setIsFilterModified(false)
    
    // Apply the saved filter configuration
    updateBooleanQuery(filter.filter_config)
    
    // Update view mode if specified
    if (filter.view_mode && filter.view_mode !== viewMode) {
      console.log('📋 Updating view mode from', viewMode, 'to', filter.view_mode)
      setViewMode(filter.view_mode) // Direct call is OK here since we're applying a saved filter
    }
    
    // Update visible fields if specified
    if (filter.visible_fields && filter.visible_fields.length > 0) {
      console.log('📋 Updating visible fields:', filter.visible_fields)
      setVisibleFields(new Set(filter.visible_fields)) // Direct call is OK here since we're applying a saved filter
    }
    
    // FilterPanel will handle closing its own dropdown
  }

  // Save/share filter handlers moved to FilterPanel

  const handleBulkUpdate = async () => {
    // Check permission
    if (!canUpdateRecords) return
    
    const selectedIds = getSelectedRecordIds()
    if (selectedIds.length === 0) return

    // TODO: Implement bulk update UI
    console.log('Bulk update:', selectedIds)
  }

  const handleBulkDelete = async () => {
    // Check permission
    if (!canDeleteRecords) return
    
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

  const handleOpenRelatedRecord = async (targetPipelineId: string, recordId: string) => {
    console.log('🔗 Opening related record:', { targetPipelineId, recordId })
    
    try {
      // Load the target pipeline data and field groups in parallel
      console.log('🔗 Fetching target pipeline and field groups:', targetPipelineId)
      const [pipelineResponse, fieldGroupsResponse, recordResponse] = await Promise.all([
        pipelinesApi.get(targetPipelineId),
        pipelinesApi.getFieldGroups(targetPipelineId),
        pipelinesApi.getRecord(targetPipelineId, recordId)
      ])
      console.log('🔗 Pipeline response:', pipelineResponse.data)
      console.log('🔗 Field groups response:', fieldGroupsResponse.data)
      console.log('🔗 Record response:', recordResponse.data)
      
      if (pipelineResponse.data && recordResponse.data) {
        // Extract field groups from the response
        const fieldGroups = (fieldGroupsResponse.data as any)?.results || fieldGroupsResponse.data || []
        
        // Create a complete pipeline object for the related record
        const targetPipeline = {
          id: pipelineResponse.data.id?.toString() || targetPipelineId,
          name: pipelineResponse.data.name || 'Related Record',
          description: pipelineResponse.data.description || '',
          record_count: pipelineResponse.data.record_count || 0,
          fields: (pipelineResponse.data.fields || []).map((field: any) => ({
            id: field.id?.toString() || `field_${Date.now()}`,
            name: field.slug || field.name?.toLowerCase().replace(/\s+/g, '_'),
            display_name: field.name || field.display_name || field.slug || 'Unknown Field',
            field_type: field.field_type || 'text',
            is_visible_in_list: field.is_visible_in_list !== false,
            is_visible_in_detail: field.is_visible_in_detail !== false,
            is_visible_in_public_forms: field.is_visible_in_public_forms || false,
            display_order: field.display_order || 0,
            field_config: field.field_config || {},
            config: field.field_config || {},
            ai_config: field.ai_config || {},
            original_slug: field.slug,
            business_rules: field.business_rules || {},
            field_group: field.field_group?.toString() || null
          })),
          field_groups: fieldGroups.map((group: any) => ({
            id: group.id?.toString() || `group_${Date.now()}`,
            name: group.name || 'Unknown Group',
            description: group.description || '',
            color: group.color || '#3B82F6',
            icon: group.icon || 'folder',
            display_order: group.display_order || 0,
            field_count: group.field_count || 0
          })),
          stages: pipelineResponse.data.stages || []
        }
        
        console.log('🔗 Opening related record drawer with pipeline:', targetPipeline.name)
        console.log('🔗 Target pipeline field groups:', targetPipeline.field_groups)
        console.log('🔗 Target pipeline fields with groups:', targetPipeline.fields.map((f: any) => ({ name: f.name, field_group: f.field_group })))
        
        // Open the related record with its proper pipeline context
        onEditRecord(recordResponse.data, targetPipeline)
      } else {
        console.error('🔗 Missing pipeline or record data:', { 
          hasPipeline: !!pipelineResponse.data, 
          hasRecord: !!recordResponse.data 
        })
      }
    } catch (error: any) {
      console.error('🔗 Failed to open related record:', {
        targetPipelineId,
        recordId,
        error: error.message,
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data
      })
      
      // Show user-friendly error message
      const errorMessage = error.response?.status === 404 
        ? `Related record not found (Pipeline: ${targetPipelineId}, Record: ${recordId})`
        : `Failed to load related record: ${error.message}`
      
      alert(errorMessage) // TODO: Replace with proper toast notification
    }
  }

  // Only show loading state if we have no records and are actively loading (prevent spinner flash)
  if (loading && records.length === 0 && pipeline.id) {
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
            {/* Permission indicator */}
            {(hasReadPermission || hasReadAllPermission) && (
              <div className="flex items-center mt-2">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  hasReadAllPermission 
                    ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' 
                    : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                }`}>
                  {hasReadAllPermission ? (
                    <>
                      <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/>
                        <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd"/>
                      </svg>
                      Viewing: All Records
                    </>
                  ) : (
                    <>
                      <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd"/>
                      </svg>
                      Viewing: My Assigned Records
                    </>
                  )}
                </span>
                {!hasReadAllPermission && hasReadPermission && (
                  <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                    (Only records where you are assigned)
                  </span>
                )}
              </div>
            )}
          </div>
          
          <div className="flex items-center space-x-3">
            {onCreateRecord && (
              <PermissionGuard 
                category="records" 
                action="create"
                fallback={
                  <Button disabled className="opacity-50 cursor-not-allowed">
                    <Lock className="w-4 h-4 mr-2" />
                    Add Record
                  </Button>
                }
              >
                <Button onClick={onCreateRecord}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Record
                </Button>
              </PermissionGuard>
            )}
            
            <RealtimeStatus isConnected={isConnected} />
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <ViewModeToggle
              viewMode={viewMode}
              onViewModeChange={handleViewModeChange}
              selectFields={selectFields}
              dateFields={dateFields}
            />

            <SearchBar
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              placeholder="Search records..."
            />
            
            <Button
              onClick={toggleFilterPanel}
              variant={showFilters ? "default" : "outline"}
              className={showFilters ? "bg-primary/10 text-primary border-primary" : ""}
            >
              <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M3 3a1 1 0 011-1h12a1 1 0 011 1v3a1 1 0 01-.293.707L12 11.414V15a1 1 0 01-.293.707l-2 2A1 1 0 018 17v-5.586L3.293 6.707A1 1 0 013 6V3z" clipRule="evenodd" />
              </svg>
              Filters {activeFilterCount > 0 && `(${activeFilterCount})`}
            </Button>

            {/* Filters controls moved to FilterPanel - now unified */}

            <FieldColumnManager
              fields={pipeline.fields}
              visibleFields={visibleFields}
              onVisibleFieldsChange={handleVisibleFieldsChange}
            />
          </div>

          <RecordActions
            selectedCount={selectedCount}
            onBulkUpdate={canUpdateRecords ? handleBulkUpdate : undefined}
            onBulkDelete={canDeleteRecords ? handleBulkDelete : undefined}
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
          currentViewMode={viewMode}
          visibleFields={Array.from(visibleFields)}
          sortConfig={sort}
          onFilterSelect={handleFilterSelect}
          currentSavedFilter={currentSavedFilter}
          isFilterModified={isFilterModified}
          onClearSavedFilter={handleClearSavedFilter}
        />
      )}

      {/* Saved filters modals moved to FilterPanel for unified experience */}

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
            onEditRecord={onEditRecord && canUpdateRecords ? onEditRecord : undefined}
            onOpenRelatedRecord={handleOpenRelatedRecord}
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