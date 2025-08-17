// PublicRecordListView - Token-authenticated version for shared filter access
'use client'

import React, { useState, useMemo, useEffect } from 'react'
import { AlertCircle, Info, Shield } from 'lucide-react'
import { savedFiltersApi } from '@/lib/api'

// Import types
import { 
  Record, 
  ViewMode,
  RecordField
} from '@/types/records'

// Import components  
import {
  LoadingState,
  ErrorState,
  RecordTable,
  ViewModeToggle,
} from '@/components/pipelines/record-list'

// Import services for field utils
import { FieldUtilsService } from '@/services/records'

// Import existing view components
import { KanbanView } from '@/components/pipelines/kanban-view'
import { CalendarView } from '@/components/pipelines/calendar-view'

// Import access mode utilities
import { 
  type SharedAccessMode, 
  getAccessPermissions, 
  getAccessModeDisplayName, 
  getAccessModeDescription 
} from '@/utils/shared-access-modes'

interface SharedFilterData {
  id: string
  name: string
  description: string
  pipeline: {
    id: string
    name: string
    slug: string
  }
  filter_config: any
  view_mode: 'table' | 'kanban' | 'calendar'
  visible_fields: string[]
  sort_config: any
  access_mode: SharedAccessMode
  expires_at: string
  time_remaining_seconds: number
}

export interface PublicRecordListViewProps {
  filterData: SharedFilterData
  token: string
  onEditRecord?: (record: Record, relatedPipeline?: any) => void
  onCreateRecord?: () => void
}

export function PublicRecordListView({ 
  filterData, 
  token,
  onEditRecord, 
  onCreateRecord 
}: PublicRecordListViewProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [records, setRecords] = useState<Record[]>([])
  const [pipeline, setPipeline] = useState<any>(null)
  
  // Calculate permissions based on access mode
  const permissions = getAccessPermissions(filterData.access_mode)
  const [pagination, setPagination] = useState({
    currentPage: 1,
    totalPages: 1,
    totalRecords: 0,
    recordsPerPage: 50,
    hasNext: false,
    hasPrevious: false
  })

  // View mode state - starts with the filter's default view mode
  const [viewMode, setViewMode] = useState<ViewMode>(filterData.view_mode)
  const [kanbanField, setKanbanField] = useState<string>('')
  const [calendarField, setCalendarField] = useState<string>('')

  // Load pipeline and records using token-based endpoints
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        setError(null)
        
        console.log('🔗 Loading pipeline data with token:', token)
        
        // Load pipeline details first
        const pipelineResponse = await savedFiltersApi.public.getPipeline(token)
        console.log('📄 Pipeline data:', pipelineResponse.data)
        
        // Transform pipeline data to match expected format
        // Backend already filters fields based on shared visibility, so don't filter again here
        const visibleFields = (pipelineResponse.data.fields || [])
          .map((field: any) => ({
            ...field,
            config: field.field_config || {},
            field_group: field.field_group || null // Keep field group if available
          }))

        // Create field groups based on visible fields (for shared view organization)
        const fieldGroupMap = new Map()
        const fieldGroups: any[] = []
        
        visibleFields.forEach((field: any) => {
          if (field.field_group && !fieldGroupMap.has(field.field_group)) {
            // Create a basic field group structure for organization
            const fieldGroup = {
              id: field.field_group,
              name: field.field_group_name || `Group ${field.field_group}`,
              description: field.field_group_description || '',
              color: field.field_group_color || '#3B82F6',
              icon: field.field_group_icon || 'folder',
              display_order: field.field_group_display_order || 0,
              field_count: visibleFields.filter((f: any) => f.field_group === field.field_group).length
            }
            fieldGroups.push(fieldGroup)
            fieldGroupMap.set(field.field_group, fieldGroup)
          }
        })

        const pipelineData = {
          ...pipelineResponse.data,
          fields: visibleFields,
          field_groups: fieldGroups.sort((a, b) => a.display_order - b.display_order)
        }
        setPipeline(pipelineData)
        
        // Load records
        const recordsResponse = await savedFiltersApi.public.getRecords(token, {
          page: 1,
          page_size: 50
        })
        console.log('📄 Records data:', recordsResponse.data)
        
        setRecords(recordsResponse.data.results || [])
        setPagination({
          currentPage: recordsResponse.data.page || 1,
          totalPages: recordsResponse.data.total_pages || 1,
          totalRecords: recordsResponse.data.count || 0,
          recordsPerPage: recordsResponse.data.page_size || 50,
          hasNext: recordsResponse.data.has_next || false,
          hasPrevious: recordsResponse.data.has_previous || false
        })
        
      } catch (err: any) {
        console.error('❌ Error loading public data:', err)
        setError(err.response?.data?.error || err.message || 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }
    
    if (token) {
      loadData()
    }
  }, [token])

  // Create pipeline structure for display if not loaded from API
  const displayPipeline = useMemo(() => {
    if (pipeline) {
      return pipeline
    }
    
    // Fallback to filter data
    return {
      id: filterData.pipeline.id,
      name: filterData.pipeline.name,
      description: `Shared filter: ${filterData.name}`,
      record_count: 0,
      fields: filterData.visible_fields.map((fieldName, index) => ({
        id: `field_${index}`,
        name: fieldName,
        display_name: fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        field_type: 'text',
        is_visible_in_list: true,
        is_visible_in_detail: true,
        is_visible_in_public_forms: false,
        display_order: index,
        field_config: {},
        config: {},
        ai_config: {},
        original_slug: fieldName,
        business_rules: {},
        field_group: null
      })) as RecordField[],
      field_groups: [],
      stages: []
    }
  }, [pipeline, filterData])

  // Use actual pipeline fields or fallback to filter data
  const visibleFields = useMemo(() => {
    if (pipeline && pipeline.fields) {
      return new Set(pipeline.fields.map((f: any) => f.name))
    }
    return new Set(filterData.visible_fields)
  }, [pipeline, filterData.visible_fields])

  const visibleFieldsList = useMemo(() => {
    return displayPipeline.fields.filter((field: RecordField) => visibleFields.has(field.name))
      .sort((a: RecordField, b: RecordField) => (a.display_order || 0) - (b.display_order || 0))
  }, [displayPipeline.fields, visibleFields])

  // Compute field options for view mode selectors
  const selectFields = useMemo(() => 
    FieldUtilsService.getSelectFields(displayPipeline.fields),
    [displayPipeline.fields]
  )

  const dateFields = useMemo(() => 
    FieldUtilsService.getDateFields(displayPipeline.fields),
    [displayPipeline.fields]
  )

  // Auto-select default fields for views
  useEffect(() => {
    if (!kanbanField && selectFields.length > 0) {
      // Look for common status/stage field names first
      const statusField = selectFields.find(f => 
        ['status', 'stage', 'phase', 'state', 'stages'].includes(f.value.toLowerCase())
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

  // Handle related record navigation for shared views  
  const handleOpenRelatedRecord = async (targetPipelineId: string, recordId: string) => {
    console.log('🔗 Public: Opening related record:', { targetPipelineId, recordId })
    
    try {
      // Use the new cross-pipeline shared access endpoints
      const [targetPipelineResponse, relatedRecordResponse] = await Promise.all([
        savedFiltersApi.public.getRelatedPipeline(token, targetPipelineId),
        savedFiltersApi.public.getRelatedRecord(token, targetPipelineId, recordId)
      ])
      
      console.log('🔗 Public: Target pipeline response:', targetPipelineResponse.data)
      console.log('🔗 Public: Related record response:', relatedRecordResponse.data)
      
      if (targetPipelineResponse.data && relatedRecordResponse.data && onEditRecord) {
        // Transform target pipeline to match expected structure
        const targetPipeline = {
          id: targetPipelineResponse.data.id,
          name: targetPipelineResponse.data.name,
          description: targetPipelineResponse.data.description || '',
          record_count: targetPipelineResponse.data.record_count || 0,
          fields: (targetPipelineResponse.data.fields || []).map((field: any) => ({
            id: field.id?.toString() || `field_${Date.now()}`,
            name: field.name || field.original_slug || field.slug,
            display_name: field.display_name || field.name,
            field_type: field.field_type || 'text',
            is_visible_in_list: field.is_visible_in_list !== false,
            is_visible_in_detail: field.is_visible_in_detail !== false,
            is_visible_in_public_forms: field.is_visible_in_public_forms || false,
            is_visible_in_shared_list_and_detail_views: field.is_visible_in_shared_list_and_detail_views || false,
            display_order: field.display_order || 0,
            field_config: field.field_config || {},
            config: field.field_config || {},
            ai_config: field.ai_config || {},
            original_slug: field.original_slug || field.name,
            business_rules: field.business_rules || {},
            field_group: field.field_group?.toString() || null
          })),
          field_groups: targetPipelineResponse.data.field_groups || [],
          stages: targetPipelineResponse.data.stages || []
        }
        
        console.log('🔗 Public: Opening related record drawer with target pipeline:', targetPipeline.name)
        onEditRecord(relatedRecordResponse.data, targetPipeline)
      } else {
        console.error('🔗 Public: Missing pipeline or record data')
        alert('Unable to load related record data.')
      }
      
    } catch (error: any) {
      console.error('🔗 Public: Failed to access related record:', error)
      
      let errorMessage = 'Unable to access related record from shared view.'
      
      if (error.response?.status === 404) {
        errorMessage = 'Related record not found or not accessible in shared view.'
      } else if (error.response?.status === 403) {
        errorMessage = 'Access to related record is restricted. The target pipeline may not allow shared access or the related fields are not visible in shared views.'
      } else if (error.response?.data?.error) {
        errorMessage = error.response.data.error
      }
      
      alert(errorMessage)
    }
  }

  // Loading state
  if (loading) {
    return <LoadingState />
  }

  // Error state
  if (error) {
    return (
      <ErrorState 
        error={error} 
        onRetry={() => window.location.reload()} 
      />
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Public Access Notice */}
      <div className="px-6 py-4 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800">
        <div className="flex items-center space-x-3">
          <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <div>
            <h3 className="text-sm font-medium text-blue-900 dark:text-blue-100">
              Shared Filter Access
            </h3>
            <p className="text-sm text-blue-700 dark:text-blue-300">
              You're viewing a shared filter with {getAccessModeDisplayName(filterData.access_mode).toLowerCase()} access. 
              Some features may be limited.
            </p>
          </div>
        </div>
      </div>

      {/* Filter Info */}
      <div className="px-6 py-3 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
          <div className="flex items-center space-x-4">
            <span><strong>Filter:</strong> {filterData.name}</span>
            <span><strong>View:</strong> {filterData.view_mode}</span>
            <span><strong>Fields:</strong> {filterData.visible_fields.length} visible</span>
          </div>
          <div className="flex items-center space-x-4">
            <span><strong>Records:</strong> {pagination.totalRecords}</span>
            <span><strong>Access:</strong> {filterData.access_mode}</span>
          </div>
        </div>
      </div>

      {/* Header */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {displayPipeline.name}
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              {displayPipeline.description}
            </p>
          </div>
        </div>

        {/* View Controls */}
        <div className="flex items-center space-x-4">
          <ViewModeToggle
            viewMode={viewMode}
            onViewModeChange={setViewMode}
            selectFields={selectFields}
            dateFields={dateFields}
          />
          
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {pagination.totalRecords} records • {getAccessModeDisplayName(filterData.access_mode)} access
          </div>
        </div>
      </div>

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
        {records.length === 0 ? (
          <div className="p-6">
            <div className="text-center py-12">
              <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                No Records Found
              </h3>
              <p className="text-gray-500 dark:text-gray-400">
                This shared filter doesn't contain any records to display.
              </p>
            </div>
          </div>
        ) : (
          <>
            {viewMode === 'table' && (
              <RecordTable
                records={records}
                fields={visibleFieldsList}
                fieldGroups={displayPipeline.field_groups || []}
                sort={{ field: 'id', direction: 'desc' }}
                onSort={() => {}} // Disable sorting for public views
                selectedRecords={new Set()}
                onSelectRecord={() => {}} // Disable selection for public views
                onSelectAll={() => {}} // Disable selection for public views
                sharedToken={token}
                onEditRecord={(record) => {
                  // Always allow viewing records in the drawer
                  if (onEditRecord) {
                    onEditRecord(record)
                  }
                }}
                onOpenRelatedRecord={handleOpenRelatedRecord}
                pipelineId={displayPipeline.id}
              />
            )}

            {viewMode === 'kanban' && selectFields.length > 0 && (
              <KanbanView
                records={records}
                pipeline={displayPipeline}
                kanbanField={kanbanField || selectFields[0]?.value || ''}
                onEditRecord={(record) => {
                  // Always allow viewing records in the drawer
                  if (onEditRecord) {
                    onEditRecord(record)
                  }
                }}
                onCreateRecord={permissions.canCreate && onCreateRecord ? onCreateRecord : () => {}}
                onUpdateRecord={permissions.canEdit ? async (recordId: string, fieldName: string, value: any) => {
                  // For shared filters, we would need to implement public record updates
                  console.log('Public record update:', { recordId, fieldName, value })
                } : async () => {}}
              />
            )}

            {viewMode === 'kanban' && selectFields.length === 0 && (
              <div className="p-6">
                <div className="text-center py-12">
                  <Info className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    No Select Fields Available
                  </h3>
                  <p className="text-gray-500 dark:text-gray-400">
                    Kanban view requires at least one select field to group records. This pipeline doesn't have any select fields available in the shared view.
                  </p>
                </div>
              </div>
            )}

            {viewMode === 'calendar' && dateFields.length > 0 && (
              <CalendarView
                records={records}
                pipeline={displayPipeline}
                calendarField={calendarField || dateFields[0]?.value || ''}
                onEditRecord={(record) => {
                  // Always allow viewing records in the drawer
                  if (onEditRecord) {
                    onEditRecord(record)
                  }
                }}
                onCreateRecord={permissions.canCreate && onCreateRecord ? onCreateRecord : () => {}}
              />
            )}

            {viewMode === 'calendar' && dateFields.length === 0 && (
              <div className="p-6">
                <div className="text-center py-12">
                  <Info className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    No Date Fields Available
                  </h3>
                  <p className="text-gray-500 dark:text-gray-400">
                    Calendar view requires at least one date field to display records. This pipeline doesn't have any date fields available in the shared view.
                  </p>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Pagination */}
      {pagination.totalRecords > 0 && (
        <div className="px-6 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
            <div>
              Showing {((pagination.currentPage - 1) * pagination.recordsPerPage) + 1} to{' '}
              {Math.min(pagination.currentPage * pagination.recordsPerPage, pagination.totalRecords)} of{' '}
              {pagination.totalRecords} records
            </div>
            <div>
              Page {pagination.currentPage} of {pagination.totalPages}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}