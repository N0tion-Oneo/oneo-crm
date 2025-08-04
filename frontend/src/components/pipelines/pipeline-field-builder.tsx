'use client'

import React, { useState, useEffect } from 'react'
import { fieldTypesApi, permissionsApi } from '@/lib/api'
import { FieldConfigurationPanel } from './field-configuration-panel'
import { ConditionalRulesBuilder } from './conditional-rules-builder'
import { 
  Plus, 
  Trash2, 
  Settings,
  Eye, 
  EyeOff,
  X,
  Type,
  Hash,
  Mail,
  Phone,
  Calendar,
  CheckSquare,
  Link,
  FileText,
  Bot,
  Sliders,
  Shield,
  Layout,
  Zap,
  Copy,
  CheckCircle,
  AlertCircle,
} from 'lucide-react'

// Complete field interface matching new architecture
interface PipelineField {
  id: string
  name: string                    // Field name/slug
  display_name?: string           // Display name (optional)
  description?: string            // Field description
  field_type: string              // Field type
  help_text?: string              // User help text
  
  // Display configuration
  display_order: number
  is_visible_in_list: boolean
  is_visible_in_detail: boolean
  is_visible_in_public_forms?: boolean  // Dynamic forms: public visibility
  
  // Behavior
  is_searchable: boolean
  create_index: boolean
  enforce_uniqueness: boolean
  is_ai_field: boolean
  
  // Configuration objects - NEW ARCHITECTURE
  field_config: Record<string, any>     // Type-specific config
  storage_constraints: Record<string, any>
  business_rules: Record<string, any>
  ai_config?: Record<string, any>       // For AI fields only
  form_validation_rules?: Record<string, any> // Form validation rules
  
  // Legacy support (remove these gradually)
  label?: string                  // Maps to display_name
  type?: string                   // Maps to field_type
  required?: boolean              // Moved to business_rules
  visible?: boolean               // Maps to is_visible_in_list
  order?: number                  // Maps to display_order
  config?: Record<string, any>    // Maps to field_config
}

interface FieldType {
  key: string
  label: string
  description: string
  icon: string
  category: string
}

interface Props {
  pipelineId?: string
  fields: PipelineField[]
  onFieldsChange: (fields: PipelineField[]) => void
  onSave?: () => void
}

const FIELD_ICONS: Record<string, any> = {
  text: Type,
  textarea: FileText,
  number: Hash,
  email: Mail,
  phone: Phone,
  date: Calendar,
  boolean: CheckSquare,
  select: CheckSquare,
  multiselect: CheckSquare,
  url: Link,
  file: FileText,
  ai_generated: Bot,
}

// Helper function to extract required stages from field business rules
const getRequiredStages = (field: PipelineField): string[] => {
  const stageReqs = field.business_rules?.stage_requirements || {}
  
  // Debug logging for contact_email field
  if (field.name === 'contact_email') {
    console.log('=== CONTACT EMAIL FIELD DEBUG ===')
    console.log('Field object:', field)
    console.log('field.required:', field.required)
    console.log('field.business_rules:', field.business_rules)
    console.log('stage_requirements:', stageReqs)
    console.log('Entries:', Object.entries(stageReqs))
    console.log('Filtered entries:', Object.entries(stageReqs).filter(([stage, config]: [string, any]) => config.required === true))
  }
  
  return Object.entries(stageReqs)
    .filter(([stage, config]: [string, any]) => config.required === true)
    .map(([stage]) => stage)
}

export function PipelineFieldBuilder({ pipelineId, fields, onFieldsChange, onSave }: Props) {
  const [availableFieldTypes, setAvailableFieldTypes] = useState<FieldType[]>([])
  const [userTypes, setUserTypes] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddField, setShowAddField] = useState(false)
  const [editingField, setEditingField] = useState<string | null>(null)
  
  // Load available field types and user types
  useEffect(() => {
    const loadData = async () => {
      try {
        // Load field types
        const response = await fieldTypesApi.getAll()
        const allTypes: FieldType[] = []
        
        // Flatten the categorized field types
        Object.entries(response.data).forEach(([category, types]) => {
          (types as any[]).forEach((type: any) => {
            allTypes.push({
              key: type.key,
              label: type.label,
              description: type.description,
              icon: type.icon,
              category
            })
          })
        })
        
        setAvailableFieldTypes(allTypes)

        // Load user types for conditional rules
        try {
          const userTypesResponse = await permissionsApi.getUserTypes()
          const userTypesData = userTypesResponse.data.results || userTypesResponse.data || []
          setUserTypes(userTypesData)
        } catch (userTypeError) {
          console.error('Failed to load user types:', userTypeError)
          // Set fallback user types if API fails
          setUserTypes([
            { id: '1', name: 'Admin', slug: 'admin', description: 'System Administrator' },
            { id: '2', name: 'Manager', slug: 'manager', description: 'Manager' },
            { id: '3', name: 'User', slug: 'user', description: 'Regular User' },
            { id: '4', name: 'Viewer', slug: 'viewer', description: 'Read-only Access' }
          ])
        }
      } catch (error) {
        console.error('Failed to load field types:', error)
      } finally {
        setLoading(false)
      }
    }
    
    loadData()
  }, [])
  
  // Add new field with new architecture
  const addField = (fieldType: FieldType) => {
    const fieldName = `${fieldType.key}_${fields.length + 1}`
    const newField: PipelineField = {
      id: `field_${Date.now()}`,
      name: fieldName,                      // Field slug
      display_name: `${fieldType.label} ${fields.length + 1}`, // Display name
      description: '',                      // Field description
      field_type: fieldType.key,            // Field type
      help_text: '',                        // User help text
      
      // Display configuration
      display_order: fields.length,
      is_visible_in_list: true,
      is_visible_in_detail: true,
      is_visible_in_public_forms: false,  // Default to private
      
      // Behavior
      is_searchable: true,
      create_index: false,
      enforce_uniqueness: false,
      is_ai_field: fieldType.key === 'ai_generated',
      
      // Configuration objects - NEW ARCHITECTURE
      field_config: fieldType.key === 'select' ? { allow_multiple: false } : 
                   fieldType.key === 'multiselect' ? { allow_multiple: true } : {},
      storage_constraints: {
        allow_null: true,  // Always true for modern architecture
        max_storage_length: null,
        enforce_uniqueness: false,
        create_index: false
      },
      business_rules: {
        stage_requirements: {},
        conditional_requirements: [],
        block_transitions: true,
        show_warnings: true
      },
      ai_config: fieldType.key === 'ai_generated' ? {
        prompt: 'Analyze this record: {*}', // Default prompt to prevent validation error
        model: 'gpt-4.1-mini',
        temperature: 0.3,
        output_type: 'text',
        enable_tools: false,
        allowed_tools: [],
        trigger_fields: [],
        cache_duration: 3600,
        fallback_value: 'Analysis unavailable'
      } : undefined,
      
      // Legacy support
      label: `${fieldType.label} ${fields.length + 1}`,
      type: fieldType.key,
      required: false,
      visible: true,
      order: fields.length,
      config: {}
    }
    
    onFieldsChange([...fields, newField])
    setShowAddField(false)
    setEditingField(newField.id)
  }
  
  // Quick add field function
  const addQuickField = (fieldTypeKey: string) => {
    const fieldType = availableFieldTypes.find(t => t.key === fieldTypeKey)
    if (fieldType) {
      addField(fieldType)
    }
  }
  
  // Clone field function
  const cloneField = (fieldId: string) => {
    const originalField = fields.find(f => f.id === fieldId)
    if (!originalField) return
    
    const clonedField: PipelineField = {
      ...originalField,
      id: `field_${Date.now()}`,
      name: `${originalField.name}_copy`,
      display_name: `${originalField.display_name || originalField.label || originalField.name} (Copy)`,
      display_order: fields.length,
      order: fields.length, // Legacy support
    }
    
    onFieldsChange([...fields, clonedField])
    setEditingField(clonedField.id)
  }
  
  // Update field
  const updateField = (fieldId: string, updates: Partial<PipelineField>) => {
    onFieldsChange(fields.map(field => 
      field.id === fieldId ? { ...field, ...updates } : field
    ))
  }
  
  // Delete field
  const deleteField = (fieldId: string) => {
    onFieldsChange(fields.filter(field => field.id !== fieldId))
    if (editingField === fieldId) {
      setEditingField(null)
    }
  }
  
  // Reorder fields
  const moveField = (fieldId: string, direction: 'up' | 'down') => {
    const currentIndex = fields.findIndex(f => f.id === fieldId)
    if (currentIndex === -1) return
    
    const newIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1
    if (newIndex < 0 || newIndex >= fields.length) return
    
    const newFields = [...fields]
    const [movedField] = newFields.splice(currentIndex, 1)
    newFields.splice(newIndex, 0, movedField)
    
    // Update order numbers
    newFields.forEach((field, index) => {
      field.display_order = index
      field.order = index // Legacy support
    })
    
    onFieldsChange(newFields)
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading field types...</div>
      </div>
    )
  }
  
  return (
    <div className="h-full flex">
      {/* Fields List */}
      <div className="w-80 flex-shrink-0 border-r border-gray-200 dark:border-gray-700 flex flex-col">
        <div className="flex-shrink-0 p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Fields
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {fields.length} field{fields.length !== 1 ? 's' : ''} configured
              </p>
            </div>
          </div>
          
          {/* Quick Add Toolbar */}
          <div className="mb-3">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Quick Add</p>
            <div className="grid grid-cols-3 gap-1">
              <button
                onClick={() => addQuickField('text')}
                className="p-2 text-xs bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors flex items-center justify-center space-x-1"
                title="Add Text Field"
              >
                <Type className="w-3 h-3" />
                <span>Text</span>
              </button>
              <button
                onClick={() => addQuickField('number')}
                className="p-2 text-xs bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors flex items-center justify-center space-x-1"
                title="Add Number Field"
              >
                <Hash className="w-3 h-3" />
                <span>Number</span>
              </button>
              <button
                onClick={() => addQuickField('email')}
                className="p-2 text-xs bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors flex items-center justify-center space-x-1"
                title="Add Email Field"
              >
                <Mail className="w-3 h-3" />
                <span>Email</span>
              </button>
              <button
                onClick={() => addQuickField('select')}
                className="p-2 text-xs bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors flex items-center justify-center space-x-1"
                title="Add Select Field"
              >
                <CheckSquare className="w-3 h-3" />
                <span>Select</span>
              </button>
              <button
                onClick={() => addQuickField('date')}
                className="p-2 text-xs bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors flex items-center justify-center space-x-1"
                title="Add Date Field"
              >
                <Calendar className="w-3 h-3" />
                <span>Date</span>
              </button>
              <button
                onClick={() => addQuickField('ai_generated')}
                className="p-2 text-xs bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border border-blue-200 dark:border-blue-800 rounded-lg hover:from-blue-100 hover:to-purple-100 dark:hover:from-blue-900/30 dark:hover:to-purple-900/30 transition-colors flex items-center justify-center space-x-1"
                title="Add AI Field"
              >
                <Bot className="w-3 h-3 text-blue-600" />
                <span className="text-blue-600 dark:text-blue-400">AI</span>
              </button>
            </div>
          </div>
          
          <button
            onClick={() => setShowAddField(true)}
            className="w-full inline-flex items-center justify-center px-4 py-2.5 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-lg text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary transition-all"
          >
            <Plus className="w-4 h-4 mr-2" />
            More Field Types
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto min-h-0">
          {fields.length === 0 ? (
            <div className="p-8 text-center">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Type className="w-10 h-10 text-blue-500" />
              </div>
              <h4 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">
                Start Building Your Pipeline
              </h4>
              <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-sm mx-auto">
                Fields are the building blocks of your pipeline. Add your first field to define what data you want to collect.
              </p>
              <button
                onClick={() => setShowAddField(true)}
                className="inline-flex items-center px-6 py-3 border border-transparent text-sm font-semibold rounded-xl text-white bg-primary hover:bg-primary/90 shadow-lg hover:shadow-xl transition-all transform hover:-translate-y-0.5"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Your First Field
              </button>
              
              <div className="mt-8 grid grid-cols-3 gap-4 max-w-xs mx-auto">
                <div className="text-center">
                  <div className="w-8 h-8 bg-green-100 dark:bg-green-900/20 rounded-lg flex items-center justify-center mx-auto mb-2">
                    <Type className="w-4 h-4 text-green-600" />
                  </div>
                  <p className="text-xs text-gray-500">Text Fields</p>
                </div>
                <div className="text-center">
                  <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/20 rounded-lg flex items-center justify-center mx-auto mb-2">
                    <CheckSquare className="w-4 h-4 text-blue-600" />
                  </div>
                  <p className="text-xs text-gray-500">Selections</p>
                </div>
                <div className="text-center">
                  <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/20 rounded-lg flex items-center justify-center mx-auto mb-2">
                    <Bot className="w-4 h-4 text-purple-600" />
                  </div>
                  <p className="text-xs text-gray-500">AI Fields</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-3 space-y-3">
              {fields.map((field, index) => {
                const Icon = FIELD_ICONS[field.field_type || field.type || 'text'] || Type
                const isEditing = editingField === field.id
                const fieldTypeInfo = availableFieldTypes.find(t => t.key === (field.field_type || field.type))
                
                return (
                  <div
                    key={field.id}
                    className={`group relative p-4 border rounded-xl cursor-pointer transition-all duration-200 ${
                      isEditing 
                        ? 'border-primary bg-primary/5 ring-2 ring-primary/20 shadow-md' 
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-sm bg-white dark:bg-gray-800'
                    }`}
                    onClick={() => setEditingField(field.id)}
                  >
                    {/* Field Header */}
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center space-x-3 min-w-0 flex-1">
                        <div className={`p-2 rounded-lg ${isEditing ? 'bg-primary text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'}`}>
                          <Icon className="w-4 h-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="font-semibold text-gray-900 dark:text-white truncate">
                            {field.display_name || field.label || field.name}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                            {fieldTypeInfo?.label || (field.field_type || field.type)}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Field Status Badges */}
                    <div className="flex flex-wrap gap-1 mb-3">
                      
                      {/* Legacy required field support - REMOVED: Use stage-specific badges only */}
                      
                      {/* Stage-specific required badges */}
                      {getRequiredStages(field).map((stage) => (
                        <span key={stage} className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300 rounded-full">
                          Required: {stage.charAt(0).toUpperCase() + stage.slice(1)}
                        </span>
                      ))}
                      {!(field.is_visible_in_list ?? field.visible ?? true) && (
                        <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300 rounded-full">
                          Hidden
                        </span>
                      )}
                      {field.is_ai_field && (
                        <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300 rounded-full">
                          <Bot className="w-3 h-3 mr-1" />
                          AI
                        </span>
                      )}
                    </div>

                    {/* Field Actions */}
                    <div className="flex items-center justify-between">
                      <div className="text-xs text-gray-400 dark:text-gray-500">
                        Position {index + 1}
                      </div>
                      
                      <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            moveField(field.id, 'up')
                          }}
                          disabled={index === 0}
                          className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                          title="Move up"
                        >
                          ↑
                        </button>
                        
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            moveField(field.id, 'down')
                          }}
                          disabled={index === fields.length - 1}
                          className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                          title="Move down"
                        >
                          ↓
                        </button>
                        
                        <div className="w-px h-4 bg-gray-300 dark:bg-gray-600" />
                        
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            cloneField(field.id)
                          }}
                          className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-md transition-colors"
                          title="Clone field"
                        >
                          <Copy className="w-3 h-3" />
                        </button>
                        
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            const currentVisible = field.is_visible_in_list ?? field.visible ?? true
                            updateField(field.id, { 
                              is_visible_in_list: !currentVisible,
                              visible: !currentVisible // Legacy support
                            })
                          }}
                          className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                          title={`${(field.is_visible_in_list ?? field.visible ?? true) ? 'Hide' : 'Show'} field`}
                        >
                          {(field.is_visible_in_list ?? field.visible ?? true) ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                        </button>
                        
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            deleteField(field.id)
                          }}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors"
                          title="Delete field"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
      
      {/* Field Configuration */}
      <div className="flex-1 flex flex-col min-w-0">
        {editingField ? (
          <FieldEditor 
            field={fields.find(f => f.id === editingField)!}
            availableFieldTypes={availableFieldTypes}
            userTypes={userTypes}
            onUpdate={(updates) => updateField(editingField, updates)}
            onClose={() => setEditingField(null)}
            fields={fields}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center bg-gray-50 dark:bg-gray-800/50">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Settings className="w-8 h-8 text-gray-500 dark:text-gray-400" />
              </div>
              <h4 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">
                Configure Your Fields
              </h4>
              <p className="text-gray-500 dark:text-gray-400 mb-6">
                Select a field from the list to customize its properties, validation rules, and display settings.
              </p>
              <div className="flex items-center justify-center space-x-4 text-sm text-gray-400">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                  <span>Basic Settings</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  <span>Validation</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
                  <span>Display</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Add Field Modal */}
      {showAddField && (
        <AddFieldModal
          availableFieldTypes={availableFieldTypes}
          onAddField={addField}
          onClose={() => setShowAddField(false)}
        />
      )}
    </div>
  )
}

// Field Editor Component - Uses NEW FieldConfigurationPanel with Tabs
function FieldEditor({ 
  field, 
  availableFieldTypes, 
  userTypes,
  onUpdate, 
  onClose,
  fields
}: {
  field: PipelineField
  availableFieldTypes: FieldType[]
  userTypes: any[]
  onUpdate: (updates: Partial<PipelineField>) => void
  onClose: () => void
  fields: PipelineField[]
}) {
  const fieldType = availableFieldTypes.find(t => t.key === (field.field_type || field.type))
  const [activeTab, setActiveTab] = useState('basic')

  const tabs = [
    {
      id: 'basic',
      label: 'Basic',
      icon: Sliders,
      description: 'Field name, type, and basic settings'
    },
    {
      id: 'display',
      label: 'Display',
      icon: Layout,
      description: 'Visibility and display options'
    },
    {
      id: 'validation',
      label: 'Validation',
      icon: CheckCircle,
      description: 'Form validation rules and requirements'
    },
    {
      id: 'advanced',
      label: 'Advanced',
      icon: Zap,
      description: 'Type-specific configuration and AI settings'
    }
  ]
  
  return (
    <>
      <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        {/* Field Header */}
        <div className="p-6 pb-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-primary/10 rounded-xl">
                {React.createElement(FIELD_ICONS[field.field_type || field.type || 'text'] || Type, {
                  className: "w-6 h-6 text-primary"
                })}
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                  {field.display_name || field.label || field.name}
                </h3>
                <div className="flex items-center space-x-2 mt-1">
                  <span className="inline-flex items-center px-2.5 py-0.5 text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300 rounded-full">
                    {fieldType?.label || field.field_type || field.type}
                  </span>
                  {field.is_ai_field && (
                    <span className="inline-flex items-center px-2.5 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300 rounded-full">
                      <Bot className="w-3 h-3 mr-1" />
                      AI Enhanced
                    </span>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="px-6 pt-4">
          <nav className="flex space-x-1" role="tablist">
            {tabs.map((tab) => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`group relative px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                    isActive
                      ? 'bg-primary text-white shadow-lg'
                      : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                  role="tab"
                  aria-selected={isActive}
                  title={tab.description}
                >
                  <div className="flex items-center space-x-2">
                    <Icon className="w-4 h-4" />
                    <span>{tab.label}</span>
                  </div>
                  {isActive && (
                    <div className="absolute -bottom-px left-0 right-0 h-0.5 bg-primary rounded-full" />
                  )}
                </button>
              )
            })}
          </nav>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'basic' && (
            <BasicFieldSettings 
              field={field} 
              fieldType={fieldType}
              availableFieldTypes={availableFieldTypes}
              onUpdate={onUpdate} 
            />
          )}
          
          
          {activeTab === 'display' && (
            <DisplaySettings 
              field={field} 
              fields={fields}
              userTypes={userTypes}
              onUpdate={onUpdate} 
            />
          )}
          
          {activeTab === 'validation' && (
            <ValidationSettings 
              field={field} 
              onUpdate={onUpdate} 
            />
          )}
          
          {activeTab === 'advanced' && (
            <AdvancedSettings 
              field={field} 
              fields={fields}
              onUpdate={onUpdate} 
            />
          )}
        </div>
      </div>
    </>
  )
}

// Add Field Modal Component
function AddFieldModal({ 
  availableFieldTypes, 
  onAddField, 
  onClose 
}: {
  availableFieldTypes: FieldType[]
  onAddField: (fieldType: FieldType) => void
  onClose: () => void
}) {
  // Group field types by category
  const groupedTypes = availableFieldTypes.reduce((acc, type) => {
    if (!acc[type.category]) {
      acc[type.category] = []
    }
    acc[type.category].push(type)
    return acc
  }, {} as Record<string, FieldType[]>)
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Add New Field
            </h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
        
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          {Object.entries(groupedTypes).map(([category, types]) => (
            <div key={category} className="mb-6">
              <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3 capitalize">
                {category} Fields
              </h4>
              <div className="grid grid-cols-2 gap-3">
                {types.map(type => {
                  const Icon = FIELD_ICONS[type.key] || Type
                  return (
                    <button
                      key={type.key}
                      onClick={() => onAddField(type)}
                      className="p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-primary hover:bg-primary/5 transition-colors text-left"
                    >
                      <div className="flex items-center space-x-3">
                        <Icon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                        <div>
                          <div className="font-medium text-gray-900 dark:text-white">
                            {type.label}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {type.description}
                          </div>
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// Basic Field Settings Tab Component
function BasicFieldSettings({ 
  field, 
  fieldType, 
  availableFieldTypes, 
  onUpdate 
}: {
  field: PipelineField
  fieldType?: FieldType
  availableFieldTypes: FieldType[]
  onUpdate: (updates: Partial<PipelineField>) => void
}) {
  return (
    <div className="space-y-6">
      <div>
        <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Basic Information
        </h4>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Field Label *
            </label>
            <input
              type="text"
              value={field.display_name || field.label || ''}
              onChange={(e) => {
                const label = e.target.value
                const slug = label.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'field'
                onUpdate({ 
                  display_name: label,
                  name: slug,
                  label: label // Legacy support
                })
              }}
              className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white transition-colors"
              placeholder="Enter field label"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
              Field Name (Auto-generated)
            </label>
            <div className="px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-600 dark:text-gray-400">
              {field.name || 'field_name'}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Used for API access and database storage
            </p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Field Type *
            </label>
            <select
              value={field.field_type || field.type || ''}
              onChange={(e) => onUpdate({ 
                field_type: e.target.value,
                type: e.target.value, // Legacy support
                is_ai_field: e.target.value === 'ai_generated'
              })}
              className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white transition-colors"
            >
              {availableFieldTypes.map(type => (
                <option key={type.key} value={type.key}>
                  {type.label}
                </option>
              ))}
            </select>
            {fieldType && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                {fieldType.description}
              </p>
            )}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Description
            </label>
            <textarea
              value={field.description || ''}
              onChange={(e) => onUpdate({ description: e.target.value })}
              placeholder="Optional field description for documentation"
              className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white transition-colors"
              rows={3}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Help Text
            </label>
            <input
              type="text"
              value={field.help_text || ''}
              onChange={(e) => onUpdate({ help_text: e.target.value })}
              placeholder="Help text shown to users when filling out this field"
              className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white transition-colors"
            />
          </div>
        </div>
      </div>
    </div>
  )
}


// Display Settings Tab Component
function DisplaySettings({ 
  field, 
  fields,
  userTypes,
  onUpdate 
}: {
  field: PipelineField
  fields: PipelineField[]
  userTypes: any[]
  onUpdate: (updates: Partial<PipelineField>) => void
}) {
  return (
    <div className="space-y-6">
      <div>
        <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Display Options
        </h4>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Visibility Settings
            </label>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center space-x-3">
                  <Layout className="w-5 h-5 text-gray-500" />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">Show in List View</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Display this field in record lists and tables</div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  id="visible-list"
                  checked={field.is_visible_in_list !== false}
                  onChange={(e) => onUpdate({ 
                    is_visible_in_list: e.target.checked,
                    visible: e.target.checked // Legacy support
                  })}
                  className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
                />
              </div>
              
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center space-x-3">
                  <Eye className="w-5 h-5 text-gray-500" />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">Show in Detail View</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Display this field when viewing individual records</div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  id="visible-detail"
                  checked={field.is_visible_in_detail !== false}
                  onChange={(e) => onUpdate({ is_visible_in_detail: e.target.checked })}
                  className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
                />
              </div>
              
              <div className="flex items-center justify-between p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <div className="flex items-center space-x-3">
                  <Settings className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">Public Forms Visible</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Show this field in public forms (external users)</div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  id="visible-public-forms"
                  checked={field.is_visible_in_public_forms || false}
                  onChange={(e) => onUpdate({ is_visible_in_public_forms: e.target.checked })}
                  className="w-4 h-4 text-blue-600 bg-white border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
                />
              </div>
              
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center space-x-3">
                  <Settings className="w-5 h-5 text-gray-500" />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">Searchable</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Include this field in search operations</div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  id="searchable"
                  checked={field.is_searchable !== false}
                  onChange={(e) => onUpdate({ is_searchable: e.target.checked })}
                  className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Conditional Display Rules Section */}
      <div>
        <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Conditional Display Rules
        </h4>
        <ConditionalRulesBuilder
          field={field}
          availableFields={fields.map(f => ({
            id: f.id,
            name: f.name,
            display_name: f.display_name || f.name,
            field_type: f.field_type
          }))}
          userTypes={userTypes}
          onChange={(conditionalRules) => {
            onUpdate({
              business_rules: {
                ...field.business_rules,
                conditional_rules: conditionalRules
              }
            })
          }}
        />
      </div>
    </div>
  )
}

// Advanced Settings Tab Component
function AdvancedSettings({ 
  field, 
  fields, 
  onUpdate 
}: {
  field: PipelineField
  fields: PipelineField[]
  onUpdate: (updates: Partial<PipelineField>) => void
}) {
  return (
    <div className="space-y-6">
      <div>
        <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Advanced Configuration
        </h4>
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
          <div className="flex items-start space-x-3">
            <Zap className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5" />
            <div>
              <h5 className="font-medium text-blue-800 dark:text-blue-200">
                Type-Specific Settings
              </h5>
              <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                Configure field-specific options, validation rules, and behavior based on the selected field type.
              </p>
            </div>
          </div>
        </div>
        
        <FieldConfigurationPanel
          fieldType={field.field_type || field.type || ''}
          config={field.field_config || field.config || {}}
          onChange={(newConfig) => onUpdate({ 
            field_config: newConfig,
            config: newConfig // Legacy support
          })}
          storageConstraints={field.storage_constraints || {}}
          onStorageConstraintsChange={(newConstraints) => onUpdate({ 
            storage_constraints: newConstraints,
            // Sync legacy properties for backward compatibility
            enforce_uniqueness: newConstraints.enforce_uniqueness || false,
            create_index: newConstraints.create_index || false
          })}
          // AI configuration props
          aiConfig={field.ai_config || {}}
          onAiConfigChange={(newAiConfig) => onUpdate({
            ai_config: newAiConfig
          })}
          isVisible={true}
          availableFields={fields.filter(f => f.id !== field.id).map(f => ({
            id: f.id,
            name: f.name,
            display_name: f.display_name || f.label || f.name,
            field_type: f.field_type || f.type || 'text',
            field_config: f.field_config || f.config || {}
          }))}
        />
      </div>
    </div>
  )
}

// Validation Settings Tab Component
function ValidationSettings({ 
  field, 
  onUpdate 
}: {
  field: PipelineField
  onUpdate: (updates: Partial<PipelineField>) => void
}) {
  const validationRules = field.form_validation_rules || {}

  const updateValidationRule = (key: string, value: any) => {
    const newRules = { ...validationRules, [key]: value }
    // Remove empty/false values to keep the object clean
    if (value === '' || value === false || value === null || value === undefined) {
      delete newRules[key]
    }
    onUpdate({ form_validation_rules: newRules })
  }

  const fieldType = field.field_type || field.type || 'text'

  return (
    <div className="space-y-6">
      <div>
        <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Form Validation Rules
        </h4>
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-6">
          <div className="flex items-start space-x-3">
            <CheckCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5" />
            <div>
              <h5 className="font-medium text-yellow-800 dark:text-yellow-200">
                Validation Applied at Form Level
              </h5>
              <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                These rules are applied when users submit forms, not when data is stored directly in the database.
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {/* Basic Required Field */}
          <div className="flex items-center justify-between p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
            <div className="flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
              <div>
                <div className="font-medium text-gray-900 dark:text-white">Required Field</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">User must fill this field in forms</div>
              </div>
            </div>
            <input
              type="checkbox"
              checked={validationRules.required || false}
              onChange={(e) => updateValidationRule('required', e.target.checked)}
              className="w-4 h-4 text-red-600 bg-white border-gray-300 rounded focus:ring-red-500 focus:ring-2"
            />
          </div>

          {/* Text Length Validation (for text fields) */}
          {(fieldType === 'text' || fieldType === 'textarea' || fieldType === 'email' || fieldType === 'url') && (
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <h5 className="font-medium text-gray-900 dark:text-white mb-4">Text Length Validation</h5>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Minimum Length
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={validationRules.minLength || ''}
                    onChange={(e) => updateValidationRule('minLength', e.target.value ? parseInt(e.target.value) : '')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Maximum Length
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={validationRules.maxLength || ''}
                    onChange={(e) => updateValidationRule('maxLength', e.target.value ? parseInt(e.target.value) : '')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="No limit"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Number Range Validation (for number fields) */}
          {(fieldType === 'number' || fieldType === 'decimal') && (
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <h5 className="font-medium text-gray-900 dark:text-white mb-4">Number Range Validation</h5>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Minimum Value
                  </label>
                  <input
                    type="number"
                    step={fieldType === 'decimal' ? '0.01' : '1'}
                    value={validationRules.min || ''}
                    onChange={(e) => updateValidationRule('min', e.target.value ? parseFloat(e.target.value) : '')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="No minimum"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Maximum Value
                  </label>
                  <input
                    type="number"
                    step={fieldType === 'decimal' ? '0.01' : '1'}
                    value={validationRules.max || ''}
                    onChange={(e) => updateValidationRule('max', e.target.value ? parseFloat(e.target.value) : '')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="No maximum"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Email Validation (automatic for email fields) */}
          {fieldType === 'email' && (
            <div className="border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
              <div className="flex items-center space-x-3">
                <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                <div>
                  <div className="font-medium text-gray-900 dark:text-white">Email Format Validation</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">Automatically validates email format</div>
                </div>
              </div>
            </div>
          )}

          {/* URL Validation (automatic for url fields) */}
          {fieldType === 'url' && (
            <div className="border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
              <div className="flex items-center space-x-3">
                <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                <div>
                  <div className="font-medium text-gray-900 dark:text-white">URL Format Validation</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">Automatically validates URL format</div>
                </div>
              </div>
            </div>
          )}

          {/* Pattern/Regex Validation */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h5 className="font-medium text-gray-900 dark:text-white mb-4">Custom Pattern Validation</h5>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Regular Expression Pattern
                </label>
                <input
                  type="text"
                  value={validationRules.pattern || ''}
                  onChange={(e) => updateValidationRule('pattern', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white font-mono text-sm"
                  placeholder="^[A-Z0-9-]+$ (example: uppercase letters, numbers, hyphens)"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  JavaScript regular expression for custom validation
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Custom Error Message
                </label>
                <input
                  type="text"
                  value={validationRules.customMessage || ''}
                  onChange={(e) => updateValidationRule('customMessage', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                  placeholder="Please enter a valid value (optional custom message)"
                />
              </div>
            </div>
          </div>

          {/* Show current validation rules summary */}
          {Object.keys(validationRules).length > 0 && (
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <h5 className="font-medium text-blue-800 dark:text-blue-200 mb-2">Active Validation Rules</h5>
              <div className="text-sm text-blue-700 dark:text-blue-300">
                <pre className="font-mono bg-white dark:bg-gray-800 p-2 rounded border">
                  {JSON.stringify(validationRules, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}