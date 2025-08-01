'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/features/auth/context'
import { ArrowLeft, Save, AlertCircle } from 'lucide-react'
import { PipelineFieldBuilder } from '@/components/pipelines/pipeline-field-builder'
import { pipelinesApi } from '@/lib/api'

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
}

export default function PipelineFieldsPage() {
  const params = useParams()
  const router = useRouter()
  const { isLoading: authLoading, isAuthenticated } = useAuth()
  const pipelineId = params.id as string

  const [pipeline, setPipeline] = useState<Pipeline | null>(null)
  const [fields, setFields] = useState<PipelineField[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load pipeline data
  useEffect(() => {
    const loadPipeline = async () => {
      try {
        setLoading(true)
        setError(null)
        
        const response = await pipelinesApi.get(pipelineId)
        
        const pipelineData: Pipeline = {
          id: response.data.id?.toString() || pipelineId,
          name: response.data.name || 'Unknown Pipeline',
          description: response.data.description || '',
          fields: (response.data.fields || []).map((field: any, index: number) => ({
            id: field.id?.toString() || `field_${index}`,
            name: field.slug || field.name || `field_${index}`,
            display_name: field.display_name || field.name || field.slug,
            description: field.description || '',
            field_type: field.field_type || 'text',
            help_text: field.help_text || '',
            display_order: field.display_order || index,
            is_visible_in_list: field.is_visible_in_list !== false,
            is_visible_in_detail: field.is_visible_in_detail !== false,
            is_searchable: field.is_searchable !== false,
            create_index: field.create_index || false,
            enforce_uniqueness: field.enforce_uniqueness || false,
            is_ai_field: field.is_ai_field || false,
            field_config: field.field_config || {},
            storage_constraints: field.storage_constraints || {},
            business_rules: field.business_rules || {},
            ai_config: field.ai_config || {},
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

  // Handle field changes
  const handleFieldsChange = (newFields: PipelineField[]) => {
    setFields(newFields)
    setHasChanges(true)
  }

  // Save fields
  const saveFields = async () => {
    if (!pipeline) return

    try {
      setSaving(true)
      setError(null)

      // Transform fields back to API format
      const apiFields = fields.map((field, index) => {
        // Create proper slug from name
        const properSlug = (field.name || field.display_name || field.label || `field_${index}`)
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, '_')
          .replace(/^_+|_+$/g, '') // Remove leading/trailing underscores
          .replace(/_{2,}/g, '_') // Replace multiple underscores with single
          || `field_${index}` // Fallback if empty
        
        return {
          id: field.id && !field.id.startsWith('field_') ? field.id : undefined,
          name: field.display_name || field.label || field.name || `Field ${index + 1}`,
          slug: properSlug,
          description: field.description || '',
          field_type: field.field_type || field.type || 'text',
          display_name: field.display_name || field.label || field.name || `Field ${index + 1}`,
          help_text: field.help_text || '',
          
          // Configuration objects
          field_config: field.field_config || field.config || {},
          storage_constraints: field.storage_constraints || {
            allow_null: true,
            max_storage_length: null,
            enforce_uniqueness: false,
            create_index: false
          },
          business_rules: field.business_rules || {
            stage_requirements: field.required ? { qualified: { required: true } } : {},
            conditional_requirements: [],
            block_transitions: true,
            show_warnings: true
          },
          
          // Field behavior
          enforce_uniqueness: field.enforce_uniqueness || false,
          create_index: field.create_index || false,
          is_searchable: field.is_searchable !== false,
          is_ai_field: field.is_ai_field || (field.field_type || field.type) === 'ai_generated',
          
          // Display configuration
          display_order: field.display_order !== undefined ? field.display_order : (field.order !== undefined ? field.order : index),
          is_visible_in_list: field.is_visible_in_list !== undefined ? field.is_visible_in_list : (field.visible !== undefined ? field.visible : true),
          is_visible_in_detail: field.is_visible_in_detail !== false,
          
          // AI configuration
          ai_config: field.ai_config || {}
        }
      })

      // Save all fields
      for (const field of apiFields) {
        if (field.id) {
          // Update existing field
          await pipelinesApi.updateField(pipelineId, field.id, field)
        } else {
          // Create new field
          await pipelinesApi.createField(pipelineId, field)
        }
      }

      setHasChanges(false)
      
    } catch (error: any) {
      console.error('Failed to save fields:', error)
      console.error('Error details:', {
        message: error?.message,
        response: error?.response?.data,
        status: error?.response?.status,
        config: {
          url: error?.config?.url,
          method: error?.config?.method,
          data: error?.config?.data
        }
      })
      
      // Show more detailed error message
      const errorMessage = error?.response?.data?.detail || 
                          error?.response?.data?.error || 
                          error?.response?.data?.message || 
                          Object.values(error?.response?.data || {}).flat().join(', ') ||
                          error?.message || 
                          'Failed to save fields. Please try again.'
      
      setError(`Save failed: ${errorMessage}`)
    } finally {
      setSaving(false)
    }
  }

  if (authLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    router.push('/login')
    return null
  }

  if (loading) {
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
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => router.push(`/pipelines/${pipelineId}`)}
              className="text-gray-400 hover:text-gray-600"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-semibold text-gray-900">
                {pipeline.name} - Fields
              </h1>
              <p className="text-sm text-gray-500">
                Configure the fields for this pipeline
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {hasChanges && (
              <span className="text-sm text-orange-600">
                You have unsaved changes
              </span>
            )}
            <button
              onClick={saveFields}
              disabled={saving || !hasChanges}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="w-4 h-4 mr-2" />
              {saving ? 'Saving...' : 'Save Fields'}
            </button>
          </div>
        </div>
      </div>

      {/* Field Builder */}
      <div className="flex-1 overflow-hidden">
        <PipelineFieldBuilder
          pipelineId={pipelineId}
          fields={fields}
          onFieldsChange={handleFieldsChange}
          onSave={saveFields}
        />
      </div>
    </div>
  )
}