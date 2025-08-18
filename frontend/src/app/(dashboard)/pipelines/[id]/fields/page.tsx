'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/features/auth/context'
import { ArrowLeft, AlertCircle, ChevronRight, Settings, Database, Sparkles, Archive, RotateCcw, Check, Clock } from 'lucide-react'
import { PipelineFieldBuilder } from '@/components/pipelines/pipeline-field-builder'
import { DeletedFieldsList } from '@/components/pipelines/deleted-fields-list'
import { PipelineTitleConfiguration } from '@/components/pipelines/pipeline-title-configuration'
import { FieldConfigCacheProvider } from '@/contexts/FieldConfigCacheContext'
import { pipelinesApi } from '@/lib/api'
import { useAutoSaveFields } from '@/hooks/use-auto-save-fields'

interface PipelineField {
  id: string
  name: string                    // Field name/slug
  display_name?: string           // Display name (optional)
  description?: string            // Field description
  field_type: string              // Field type
  help_text?: string              // User help text
  
  // Display configuration (NO width, NO placeholder per requirements)
  display_order: number
  is_visible_in_list: boolean
  is_visible_in_detail: boolean
  is_visible_in_public_forms?: boolean
  is_visible_in_shared_list_and_detail_views?: boolean
  
  // Behavior
  is_searchable: boolean
  create_index: boolean
  enforce_uniqueness: boolean
  is_ai_field: boolean
  
  // Configuration objects
  field_config: Record<string, any>     // Type-specific config
  storage_constraints: Record<string, any>
  business_rules: Record<string, any>
  ai_config?: Record<string, any>       // For AI fields only
  
  // Field group assignment
  field_group?: string | null  // Field group ID
  
  // Field lifecycle management
  is_deleted?: boolean
  deleted_at?: string
  deleted_by?: string
  scheduled_for_hard_delete?: string
  hard_delete_reason?: string
  deletion_status?: {
    status: 'active' | 'soft_deleted' | 'scheduled_for_hard_delete'
    deleted_at?: string
    deleted_by?: string
    days_remaining?: number
    hard_delete_date?: string
    reason?: string
  }
  
  // Legacy support (remove these gradually)
  label?: string                  // Maps to display_name
  type?: string                   // Maps to field_type
  required?: boolean              // Moved to business_rules
  visible?: boolean               // Maps to is_visible_in_list
  order?: number                  // Maps to display_order
  config?: Record<string, any>    // Maps to field_config
}

interface Pipeline {
  id: string
  name: string
  description: string
  fields: PipelineField[]
  settings?: {
    title_field?: {
      template?: string
    }
  }
}

export default function PipelineFieldsPage() {
  const params = useParams()
  const router = useRouter()
  const { isLoading: authLoading, isAuthenticated } = useAuth()
  const pipelineId = params.id as string

  const [pipeline, setPipeline] = useState<Pipeline | null>(null)
  const [fields, setFields] = useState<PipelineField[]>([])
  const [deletedFields, setDeletedFields] = useState<PipelineField[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Tab management
  const [activeTab, setActiveTab] = useState<'active' | 'deleted' | 'settings'>('active')
  const [deletedFieldsLoading, setDeletedFieldsLoading] = useState(false)
  
  // Auto-save hook with validation
  const { scheduleAutoSave, isFieldSaving } = useAutoSaveFields(pipelineId, {
    delay: 1500, // 1.5 second delay
    allFields: fields,
    validateField: (field, allFields) => {
      // Skip validation for temporary/new fields that haven't been created yet
      if (!field.id || field.id.startsWith('field_')) {
        return null
      }
      
      // Check for duplicate field names (excluding the field being updated)
      const fieldName = field.display_name || field.name
      const duplicateField = allFields.find(f => 
        f.id !== field.id && 
        !f.id.startsWith('field_') && // Don't check against temp fields
        (f.name === fieldName || f.display_name === fieldName)
      )
      if (duplicateField) {
        return `Field name "${fieldName}" already exists`
      }
      
      // Basic validation
      if (!fieldName || fieldName.trim() === '') {
        return 'Field name is required'
      }
      
      return null // No validation errors
    },
    onSaveStart: (field) => {
      console.log('🔄 Auto-save started for:', field.name)
    },
    onSaveSuccess: (savedField) => {
      console.log('✅ Auto-save completed for:', savedField.name)
      console.log('🔄 ID mapping: temp →', savedField.name, 'real →', savedField.id)
      
      // Update the field in local state with the saved version
      // For new fields, we need to match by name since the ID changed from temp to real
      setFields(prevFields => prevFields.map(f => {
        // First try exact ID match (for existing fields)
        if (f.id === savedField.id) {
          return { ...f, ...savedField }
        }
        
        // For new fields with temp IDs, match by name and temp ID pattern
        if (f.id.toString().startsWith('field_') && 
            (f.name === savedField.name || f.display_name === savedField.name)) {
          console.log('🔄 Updating temp field ID:', f.id, '→', savedField.id)
          return { ...f, ...savedField, id: savedField.id.toString() }
        }
        
        return f
      }))
      setHasChanges(false) // Clear changes indicator
      setError(null) // Clear any previous errors
    },
    onSaveError: (error, field) => {
      console.error('❌ Auto-save failed for:', field.name, error)
      const errorMessage = error?.response?.data?.detail || 
                          error?.response?.data?.error || 
                          error?.response?.data?.message || 
                          Object.values(error?.response?.data || {}).flat().join(', ') ||
                          error?.message || 
                          'Failed to save field changes'
      setError(`Auto-save failed for "${field.name}": ${errorMessage}`)
    }
  })

  // Load pipeline data
  useEffect(() => {
    const loadPipeline = async () => {
      try {
        setLoading(true)
        setError(null)
        
        // Load pipeline metadata
        const pipelineResponse = await pipelinesApi.get(pipelineId)
        
        // Load fields separately to get field_group data
        const fieldsResponse = await pipelinesApi.getFields(pipelineId)
        console.log('🔍 Raw fields API response:', fieldsResponse)
        
        // Handle both paginated and direct array responses
        const fieldsData = (fieldsResponse.data as any)?.results || (fieldsResponse as any).results || fieldsResponse.data || fieldsResponse || []
        console.log('🔍 Fields from API with groups:', fieldsData.length, 'fields')
        console.log('🔍 Fields with field_group:', fieldsData.filter((f: any) => f.field_group != null).length, 'fields')
        
        const pipelineData: Pipeline = {
          id: pipelineResponse.data.id?.toString() || pipelineId,
          name: pipelineResponse.data.name || 'Unknown Pipeline',
          description: pipelineResponse.data.description || '',
          settings: pipelineResponse.data.settings || {},
          fields: (fieldsData || []).map((field: any, index: number) => ({
            id: field.id?.toString() || `field_${index}`,
            name: field.slug || field.name || `field_${index}`,
            display_name: field.display_name || field.name || field.slug,
            description: field.description || '',
            field_type: field.field_type || 'text',
            help_text: field.help_text || '',
            display_order: field.display_order || index,
            is_visible_in_list: field.is_visible_in_list !== false,
            is_visible_in_detail: field.is_visible_in_detail !== false,
            is_visible_in_public_forms: field.is_visible_in_public_forms || false,
            is_visible_in_shared_list_and_detail_views: field.is_visible_in_shared_list_and_detail_views || false,
            is_searchable: field.is_searchable !== false,
            create_index: field.create_index || false,
            enforce_uniqueness: field.enforce_uniqueness || false,
            is_ai_field: field.is_ai_field || false,
            field_config: field.field_config || {},
            storage_constraints: field.storage_constraints || {},
            business_rules: field.business_rules || {},
            ai_config: field.ai_config || {},
            
            // Field group assignment - CRITICAL for field groups to work
            field_group: field.field_group || null,
            
            // Field lifecycle management
            is_deleted: field.is_deleted || false,
            deleted_at: field.deleted_at,
            deleted_by: field.deleted_by,
            scheduled_for_hard_delete: field.scheduled_for_hard_delete,
            hard_delete_reason: field.hard_delete_reason,
            deletion_status: field.deletion_status,
            // Legacy support
            label: field.display_name || field.name || field.slug,
            type: field.field_type || 'text',
            required: field.business_rules?.stage_requirements && Object.keys(field.business_rules.stage_requirements).length > 0,
            visible: field.is_visible_in_list !== false,
            order: field.display_order || index,
            config: field.field_config || {}
          }))
        }
        
        setPipeline(pipelineData)
        setFields(pipelineData.fields)
        
      } catch (error) {
        console.error('Failed to load pipeline:', error)
        setError('Failed to load pipeline data')
      } finally {
        setLoading(false)
      }
    }

    if (pipelineId && isAuthenticated) {
      loadPipeline()
    }
  }, [pipelineId, isAuthenticated])

  // Load deleted fields
  const loadDeletedFields = async () => {
    try {
      setDeletedFieldsLoading(true)
      setError(null)
      
      const response = await pipelinesApi.getDeletedFields(pipelineId)
      
      const deletedFieldsData = (response.data || []).map((field: any, index: number) => ({
        id: field.id?.toString() || `deleted_field_${index}`,
        name: field.slug || field.name || `deleted_field_${index}`,
        display_name: field.display_name || field.name || field.slug,
        description: field.description || '',
        field_type: field.field_type || 'text',
        help_text: field.help_text || '',
        display_order: field.display_order || index,
        is_visible_in_list: field.is_visible_in_list !== false,
        is_visible_in_detail: field.is_visible_in_detail !== false,
        is_visible_in_public_forms: field.is_visible_in_public_forms || false,
        is_searchable: field.is_searchable !== false,
        create_index: field.create_index || false,
        enforce_uniqueness: field.enforce_uniqueness || false,
        is_ai_field: field.is_ai_field || false,
        field_config: field.field_config || {},
        storage_constraints: field.storage_constraints || {},
        business_rules: field.business_rules || {},
        ai_config: field.ai_config || {},
        
        // Field lifecycle management
        is_deleted: field.is_deleted || false,
        deleted_at: field.deleted_at,
        deleted_by: field.deleted_by,
        scheduled_for_hard_delete: field.scheduled_for_hard_delete,
        hard_delete_reason: field.hard_delete_reason,
        deletion_status: field.deletion_status,
        
        // Legacy support
        label: field.display_name || field.name || field.slug,
        type: field.field_type || 'text',
        required: field.business_rules?.stage_requirements && Object.keys(field.business_rules.stage_requirements).length > 0,
        visible: field.is_visible_in_list !== false,
        order: field.display_order || index,
        config: field.field_config || {}
      }))
      
      setDeletedFields(deletedFieldsData)
      
    } catch (error) {
      console.error('Failed to load deleted fields:', error)
      setError('Failed to load deleted fields')
    } finally {
      setDeletedFieldsLoading(false)
    }
  }

  // Handle field changes - support both direct arrays and functional updates with auto-save
  const handleFieldsChange = useCallback((newFields: PipelineField[] | ((prev: PipelineField[]) => PipelineField[]), changedField?: PipelineField) => {
    // Debug field ID handling
    if (changedField) {
      console.log('🔍 handleFieldsChange received changedField:', {
        id: changedField.id,
        name: changedField.name || changedField.display_name || changedField.label,
        idType: typeof changedField.id,
        shouldBeNumeric: !isNaN(Number(changedField.id))
      })
    }
    
    if (typeof newFields === 'function') {
      setFields(prevFields => {
        const updatedFields = newFields(prevFields)
        setHasChanges(true)
        
        // If a specific field was changed, schedule auto-save for it
        if (changedField) {
          scheduleAutoSave(changedField)
        }
        
        return updatedFields
      })
    } else {
      setFields(newFields)
      setHasChanges(true)
      
      // If a specific field was changed, schedule auto-save for it
      if (changedField) {
        scheduleAutoSave(changedField)
      }
    }
  }, [scheduleAutoSave])

  // Handle field restoration - refresh both lists
  const handleFieldRestored = async () => {
    // Refresh deleted fields list
    await loadDeletedFields()
    
    // Refresh active fields list
    if (pipelineId && isAuthenticated) {
      try {
        // Load fields separately to get field_group data
        const fieldsResponse = await pipelinesApi.getFields(pipelineId)
        const fieldsData = (fieldsResponse.data as any)?.results || (fieldsResponse as any).results || fieldsResponse.data || fieldsResponse || []
        
        const activeFieldsData = (fieldsData || []).map((field: any, index: number) => ({
          id: field.id?.toString() || `field_${index}`,
          name: field.slug || field.name || `field_${index}`,
          display_name: field.display_name || field.name || field.slug,
          description: field.description || '',
          field_type: field.field_type || 'text',
          help_text: field.help_text || '',
          display_order: field.display_order || index,
          is_visible_in_list: field.is_visible_in_list !== false,
          is_visible_in_detail: field.is_visible_in_detail !== false,
          is_visible_in_public_forms: field.is_visible_in_public_forms || false,
          is_searchable: field.is_searchable !== false,
          create_index: field.create_index || false,
          enforce_uniqueness: field.enforce_uniqueness || false,
          is_ai_field: field.is_ai_field || false,
          field_config: field.field_config || {},
          storage_constraints: field.storage_constraints || {},
          business_rules: field.business_rules || {},
          ai_config: field.ai_config || {},
          
          // Field group assignment - CRITICAL for field groups to work
          field_group: field.field_group || null,
          
          is_deleted: field.is_deleted || false,
          deleted_at: field.deleted_at,
          deleted_by: field.deleted_by,
          scheduled_for_hard_delete: field.scheduled_for_hard_delete,
          hard_delete_reason: field.hard_delete_reason,
          deletion_status: field.deletion_status,
          label: field.display_name || field.name || field.slug,
          type: field.field_type || 'text',
          required: field.business_rules?.stage_requirements && Object.keys(field.business_rules.stage_requirements).length > 0,
          visible: field.is_visible_in_list !== false,
          order: field.display_order || index,
          config: field.field_config || {}
        }))
        setFields(activeFieldsData)
      } catch (error) {
        console.error('Failed to refresh active fields:', error)
      }
    }
  }

  // Auto-save handles field saving - no manual save needed

  // Let the dashboard layout handle auth loading to prevent spinner cascade
  if (!isAuthenticated && !authLoading) {
    router.push('/login')
    return null
  }

  // Only show loading if we're past auth and actually loading pipeline data
  if (loading && !authLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading pipeline...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <AlertCircle className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <div className="mt-2 text-sm text-red-700">{error}</div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!pipeline) {
    return (
      <div className="p-6">
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900">Pipeline not found</h3>
        </div>
      </div>
    )
  }

  return (
    <FieldConfigCacheProvider>
      <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Enhanced Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="px-6 py-4">
          {/* Breadcrumbs */}
          <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400 mb-3">
            <button
              onClick={() => router.push('/pipelines')}
              className="hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
            >
              Pipelines
            </button>
            <ChevronRight className="w-4 h-4" />
            <button
              onClick={() => router.push(`/pipelines/${pipelineId}`)}
              className="hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
            >
              {pipeline.name}
            </button>
            <ChevronRight className="w-4 h-4" />
            <span className="text-gray-900 dark:text-white font-medium">Field Configuration</span>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => router.push(`/pipelines/${pipelineId}`)}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-all"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              
              {/* Pipeline Info Card */}
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg p-4 border border-blue-100 dark:border-blue-800">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-blue-500 rounded-lg">
                    <Database className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h1 className="text-xl font-bold text-gray-900 dark:text-white flex items-center">
                      {pipeline.name}
                      <Settings className="w-5 h-5 ml-2 text-gray-500" />
                    </h1>
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      {fields.length} fields • Configure data structure and validation
                    </p>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Auto-Save Status */}
            <div className="flex items-center space-x-2">
              {hasChanges ? (
                <div className="flex items-center space-x-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium border border-blue-200 dark:border-blue-800">
                  <Clock className="w-3 h-3 animate-pulse" />
                  <span>Auto-saving...</span>
                </div>
              ) : (
                <div className="flex items-center space-x-2 px-3 py-1.5 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded-full text-sm font-medium border border-green-200 dark:border-green-800">
                  <Check className="w-3 h-3" />
                  <span>All changes saved</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>


      {/* Tab Navigation */}
      <div className="px-6 pb-6">
        <div className="bg-white dark:bg-gray-800 rounded-t-xl shadow-sm border border-gray-200 dark:border-gray-700 border-b-0">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex space-x-8">
              <button
                onClick={() => setActiveTab('active')}
                className={`flex items-center space-x-2 pb-2 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'active'
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                <Database className="w-4 h-4" />
                <span>Active Fields</span>
                <div className="bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-0.5 rounded-full text-xs font-medium">
                  {fields.length}
                </div>
              </button>
              
              <button
                onClick={() => {
                  setActiveTab('deleted')
                  if (deletedFields.length === 0) {
                    loadDeletedFields()
                  }
                }}
                className={`flex items-center space-x-2 pb-2 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'deleted'
                    ? 'border-orange-500 text-orange-600 dark:text-orange-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                <Archive className="w-4 h-4" />
                <span>Deleted Fields</span>
                <div className="bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-0.5 rounded-full text-xs font-medium">
                  {deletedFields.length}
                </div>
              </button>
              
              <button
                onClick={() => setActiveTab('settings')}
                className={`flex items-center space-x-2 pb-2 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'settings'
                    ? 'border-green-500 text-green-600 dark:text-green-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                <Settings className="w-4 h-4" />
                <span>Pipeline Settings</span>
              </button>
            </div>

            {activeTab === 'deleted' && (
              <button
                onClick={loadDeletedFields}
                disabled={deletedFieldsLoading}
                className="flex items-center space-x-2 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
              >
                <RotateCcw className={`w-4 h-4 ${deletedFieldsLoading ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-hidden px-6">
        <div className="h-full bg-white dark:bg-gray-800 rounded-b-xl shadow-sm border border-gray-200 dark:border-gray-700 border-t-0">
          {activeTab === 'active' ? (
            <PipelineFieldBuilder
              pipelineId={pipelineId}
              fields={fields}
              onFieldsChange={handleFieldsChange}
            />
          ) : activeTab === 'deleted' ? (
            <div className="h-full p-6">
              <DeletedFieldsList
                pipelineId={pipelineId}
                fields={deletedFields}
                loading={deletedFieldsLoading}
                onRefresh={loadDeletedFields}
                onFieldRestored={handleFieldRestored}
              />
            </div>
          ) : activeTab === 'settings' ? (
            <div className="h-full p-6">
              <PipelineTitleConfiguration
                pipeline={pipeline}
                onTemplateChange={(template) => {
                  // Update local pipeline state
                  setPipeline(prev => prev ? {
                    ...prev,
                    settings: {
                      ...prev.settings,
                      title_field: { template }
                    }
                  } : null)
                }}
              />
            </div>
          ) : null}
        </div>
      </div>
      </div>
    </FieldConfigCacheProvider>
  )
}