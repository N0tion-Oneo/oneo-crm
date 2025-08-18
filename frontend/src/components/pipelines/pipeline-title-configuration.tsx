'use client'

import { useState, useEffect, useRef } from 'react'
import { Type, Eye, ChevronDown, Plus } from 'lucide-react'
import { pipelinesApi } from '@/lib/api'

interface Field {
  id: string
  name: string
  display_name: string
  slug: string
  field_type: string
}

interface Pipeline {
  id: string
  name: string
  settings?: {
    title_field?: {
      template?: string
      primary_field?: string
      secondary_field?: string
    }
  }
  fields: Field[]
}

interface PipelineTitleConfigurationProps {
  pipeline: Pipeline
  onTemplateChange?: (template: string) => void
}

// Frontend display configuration (not stored in backend)
interface TitleDisplayConfig {
  displayFormat: 'inline' | 'chip' | 'badge' | 'stacked'
  showPipelineName: boolean
  truncateLength: number | null
  separator: string
}

const DEFAULT_DISPLAY_CONFIG: TitleDisplayConfig = {
  displayFormat: 'inline',
  showPipelineName: false,
  truncateLength: null,
  separator: ' | '
}

export function PipelineTitleConfiguration({ pipeline, onTemplateChange }: PipelineTitleConfigurationProps) {
  const [template, setTemplate] = useState<string>('')
  const [primaryField, setPrimaryField] = useState<string>('')
  const [secondaryField, setSecondaryField] = useState<string>('')
  const [displayConfig, setDisplayConfig] = useState<TitleDisplayConfig>(DEFAULT_DISPLAY_CONFIG)
  const [previewData, setPreviewData] = useState<any>(null)
  const [saving, setSaving] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const debounceRef = useRef<NodeJS.Timeout | null>(null)

  // Load current configuration from pipeline settings
  useEffect(() => {
    const titleConfig = pipeline.settings?.title_field
    const currentTemplate = titleConfig?.template || generateDefaultTemplate()
    const currentPrimary = titleConfig?.primary_field || ''
    const currentSecondary = titleConfig?.secondary_field || ''
    
    setTemplate(currentTemplate)
    setPrimaryField(currentPrimary)
    setSecondaryField(currentSecondary)
  }, [pipeline])

  // Generate a default template based on available fields
  const generateDefaultTemplate = () => {
    const fieldSlugs = pipeline.fields.map(f => f.name || f.slug)
    
    // Smart defaults based on common field names
    if (fieldSlugs.includes('first_name') && fieldSlugs.includes('last_name')) {
      return '{first_name} {last_name}'
    } else if (fieldSlugs.includes('full_name')) {
      return '{full_name}'
    } else if (fieldSlugs.includes('name')) {
      return '{name}'
    } else if (fieldSlugs.includes('company_name')) {
      return '{company_name}'
    } else if (fieldSlugs.includes('title')) {
      return '{title}'
    } else if (fieldSlugs.includes('subject')) {
      return '{subject}'
    } else if (fieldSlugs.length > 0) {
      return `{${fieldSlugs[0]}}`
    }
    
    return '{name}'
  }

  // Save template to backend
  const saveConfiguration = async (config: { template?: string, primaryField?: string, secondaryField?: string }) => {
    try {
      setSaving(true)
      console.log('🔄 Starting title configuration save:', { pipelineId: pipeline.id, config })
      
      // Update pipeline settings with current values
      const updatedSettings = {
        ...pipeline.settings,
        title_field: {
          ...pipeline.settings?.title_field,
          template: config.template ?? template,
          primary_field: config.primaryField ?? primaryField,
          secondary_field: config.secondaryField ?? secondaryField
        }
      }

      console.log('🔄 Calling pipelinesApi.update with:', { 
        id: pipeline.id, 
        payload: { settings: updatedSettings } 
      })

      const response = await pipelinesApi.update(pipeline.id, {
        settings: updatedSettings
      })
      
      console.log('✅ Title configuration saved successfully:', response)
      onTemplateChange?.(config.template ?? template)
    } catch (error) {
      console.error('❌ Failed to save title configuration:', error)
      alert('Failed to save title configuration. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  // Handle template change with debounced save
  const handleTemplateChange = (newTemplate: string) => {
    setTemplate(newTemplate)
    
    // Clear previous debounce
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }
    
    // Debounced save after 1 second
    debounceRef.current = setTimeout(() => {
      console.log('Saving template:', newTemplate)
      saveConfiguration({ template: newTemplate })
    }, 1000)
  }

  // Handle primary/secondary field changes
  const handlePrimaryFieldChange = (field: string) => {
    setPrimaryField(field)
    saveConfiguration({ primaryField: field })
  }

  const handleSecondaryFieldChange = (field: string) => {
    setSecondaryField(field)
    saveConfiguration({ secondaryField: field })
  }

  // Insert field placeholder at cursor position
  const insertField = (fieldName: string) => {
    const placeholder = `{${fieldName}}`
    setTemplate(prev => prev + (prev.endsWith(' ') ? '' : ' ') + placeholder)
  }

  // Generate preview with sample data
  const generatePreview = (templateStr: string) => {
    if (!templateStr) return ''
    
    // Sample data for preview
    const sampleData: Record<string, string> = {
      first_name: 'John',
      last_name: 'Doe', 
      full_name: 'John Doe',
      name: 'John Doe',
      company_name: 'ACME Corp',
      title: 'Account Manager',
      subject: 'Login Issue',
      email: 'john@example.com',
      phone: '+1-555-0123',
      deal_name: 'Q4 Partnership',
      amount: '50000',
      id: '1234'
    }

    // Replace placeholders with sample data
    let preview = templateStr
    for (const [field, value] of Object.entries(sampleData)) {
      const placeholder = `{${field}}`
      if (preview.includes(placeholder)) {
        preview = preview.replace(new RegExp(`\\{${field}\\}`, 'g'), value)
      }
    }

    return preview
  }

  // Render title with different display formats
  const renderTitlePreview = (titleText: string, format: TitleDisplayConfig['displayFormat']) => {
    const baseClasses = "transition-all duration-200"
    
    switch (format) {
      case 'chip':
        return (
          <span className={`${baseClasses} inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-blue-100 text-blue-800 border border-blue-200`}>
            {titleText}
          </span>
        )
      case 'badge':
        return (
          <span className={`${baseClasses} inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-800 border border-gray-300`}>
            {titleText}
          </span>
        )
      case 'stacked':
        return (
          <div className={`${baseClasses} space-y-1`}>
            <div className="text-sm font-medium text-gray-900">{titleText}</div>
            {displayConfig.showPipelineName && (
              <div className="text-xs text-gray-500">{pipeline.name}</div>
            )}
          </div>
        )
      case 'inline':
      default:
        return (
          <span className={`${baseClasses} text-sm text-gray-900 font-medium`}>
            {titleText}
            {displayConfig.showPipelineName && (
              <span className="ml-2 text-xs text-gray-500">({pipeline.name})</span>
            )}
          </span>
        )
    }
  }


  const availableFields = pipeline.fields.filter(f => f.field_type !== 'button')

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
            <Type className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Record Title Template
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Configure how record titles are displayed throughout the system
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => saveTemplate(template)}
            disabled={saving}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? 'Saving...' : 'Save Now'}
          </button>
          
          <button
            onClick={() => setShowPreview(!showPreview)}
            className="flex items-center space-x-2 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <Eye className="w-4 h-4" />
            <span>{showPreview ? 'Hide' : 'Show'} Preview</span>
            <ChevronDown className={`w-4 h-4 transition-transform ${showPreview ? 'rotate-180' : ''}`} />
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {/* Template Input */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Template
          </label>
          <div className="flex space-x-2">
            <input
              type="text"
              value={template}
              onChange={(e) => handleTemplateChange(e.target.value)}
              placeholder="e.g., {first_name} {last_name} | {company_name}"
              className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            {saving && (
              <div className="flex items-center px-3 py-2 text-sm text-blue-600 dark:text-blue-400">
                Saving...
              </div>
            )}
          </div>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Use {'{field_name}'} to insert field values. Empty fields will show as gaps.
          </p>
        </div>

        {/* Available Fields */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Available Fields
          </label>
          <div className="flex flex-wrap gap-2">
            {availableFields.map(field => (
              <button
                key={field.id}
                onClick={() => insertField(field.name || field.slug)}
                className="inline-flex items-center space-x-1 px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                <Plus className="w-3 h-3" />
                <span>{field.display_name || field.name}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Preview */}
        {showPreview && (
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Preview Examples
            </label>
            <div className="space-y-2">
              <div className="flex items-center space-x-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-md border border-green-200 dark:border-green-800">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <div>
                  <div className="text-sm font-medium text-green-800 dark:text-green-200">
                    Complete Data:
                  </div>
                  <div className="text-sm text-green-700 dark:text-green-300">
                    "{generatePreview(template)}"
                  </div>
                </div>
              </div>
              
              <div className="flex items-center space-x-3 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-md border border-amber-200 dark:border-amber-800">
                <div className="w-2 h-2 bg-amber-500 rounded-full"></div>
                <div>
                  <div className="text-sm font-medium text-amber-800 dark:text-amber-200">
                    Missing Data:
                  </div>
                  <div className="text-sm text-amber-700 dark:text-amber-300">
                    Gaps will be visible (e.g., "John | " shows missing company)
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}