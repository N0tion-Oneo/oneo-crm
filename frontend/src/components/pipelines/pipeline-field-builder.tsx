'use client'

import { useState, useEffect } from 'react'
import { fieldTypesApi } from '@/lib/api'
import { FieldConfigurationPanel } from './field-configuration-panel'
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

export function PipelineFieldBuilder({ pipelineId, fields, onFieldsChange, onSave }: Props) {
  const [availableFieldTypes, setAvailableFieldTypes] = useState<FieldType[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddField, setShowAddField] = useState(false)
  const [editingField, setEditingField] = useState<string | null>(null)
  
  // Load available field types
  useEffect(() => {
    const loadFieldTypes = async () => {
      try {
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
      } catch (error) {
        console.error('Failed to load field types:', error)
      } finally {
        setLoading(false)
      }
    }
    
    loadFieldTypes()
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
      
      // Behavior
      is_searchable: true,
      create_index: false,
      enforce_uniqueness: false,
      is_ai_field: fieldType.key === 'ai_generated',
      
      // Configuration objects - NEW ARCHITECTURE
      field_config: {},
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
      ai_config: fieldType.key === 'ai_generated' ? {} : undefined,
      
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
      <div className="w-1/2 border-r border-gray-200 dark:border-gray-700">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Fields ({fields.length})
            </h3>
            <button
              onClick={() => setShowAddField(true)}
              className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md text-white bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
            >
              <Plus className="w-4 h-4 mr-1" />
              Add Field
            </button>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto">
          {fields.length === 0 ? (
            <div className="p-8 text-center">
              <div className="text-gray-400 mb-4">
                <Type className="w-12 h-12 mx-auto" />
              </div>
              <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                No fields yet
              </h4>
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                Add your first field to get started building your pipeline.
              </p>
              <button
                onClick={() => setShowAddField(true)}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary hover:bg-primary/90"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Your First Field
              </button>
            </div>
          ) : (
            <div className="p-4 space-y-2">
              {fields.map((field, index) => {
                const Icon = FIELD_ICONS[field.field_type || field.type || 'text'] || Type
                const isEditing = editingField === field.id
                
                return (
                  <div
                    key={field.id}
                    className={`p-3 border rounded-lg cursor-pointer transition-all ${
                      isEditing 
                        ? 'border-primary bg-primary/5 ring-1 ring-primary/20' 
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                    }`}
                    onClick={() => setEditingField(field.id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <Icon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                        <div>
                          <div className="font-medium text-gray-900 dark:text-white">
                            {field.display_name || field.label || field.name}
                          </div>
                          <div className="text-sm text-gray-500 dark:text-gray-400">
                            {availableFieldTypes.find(t => t.key === (field.field_type || field.type))?.label || (field.field_type || field.type)}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-1">
                        {(field.required || field.business_rules?.stage_requirements) && (
                          <span className="px-2 py-0.5 text-xs bg-red-100 text-red-800 rounded">
                            Required
                          </span>
                        )}
                        {!(field.is_visible_in_list ?? field.visible ?? true) && (
                          <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-800 rounded">
                            Hidden
                          </span>
                        )}
                        {field.is_ai_field && (
                          <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded">
                            AI
                          </span>
                        )}
                        
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            moveField(field.id, 'up')
                          }}
                          disabled={index === 0}
                          className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
                        >
                          ↑
                        </button>
                        
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            moveField(field.id, 'down')
                          }}
                          disabled={index === fields.length - 1}
                          className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
                        >
                          ↓
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
                          className="p-1 text-gray-400 hover:text-gray-600"
                        >
                          {(field.is_visible_in_list ?? field.visible ?? true) ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                        </button>
                        
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            deleteField(field.id)
                          }}
                          className="p-1 text-gray-400 hover:text-red-600"
                        >
                          <Trash2 className="w-4 h-4" />
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
      <div className="w-1/2 flex flex-col">
        {editingField ? (
          <FieldEditor 
            field={fields.find(f => f.id === editingField)!}
            availableFieldTypes={availableFieldTypes}
            onUpdate={(updates) => updateField(editingField, updates)}
            onClose={() => setEditingField(null)}
            fields={fields}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <Settings className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                Select a field to configure
              </h4>
              <p className="text-gray-500 dark:text-gray-400">
                Click on a field from the list to edit its settings.
              </p>
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

// Field Editor Component - Uses NEW FieldConfigurationPanel
function FieldEditor({ 
  field, 
  availableFieldTypes, 
  onUpdate, 
  onClose,
  fields
}: {
  field: PipelineField
  availableFieldTypes: FieldType[]
  onUpdate: (updates: Partial<PipelineField>) => void
  onClose: () => void
  fields: PipelineField[]
}) {
  const fieldType = availableFieldTypes.find(t => t.key === (field.field_type || field.type))
  
  return (
    <>
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Configure Field
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {field.display_name || field.label || field.name} ({fieldType?.label || field.field_type || field.type})
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-1"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Basic Field Settings Section */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white">
            Basic Field Settings
          </h4>
          
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
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
              placeholder="Enter field label"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-600 dark:text-gray-400 mb-1 text-xs">
              Field Name (Auto-generated)
            </label>
            <div className="px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-600 dark:text-gray-400">
              {field.name || 'field_name'}
            </div>
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
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
            >
              {availableFieldTypes.map(type => (
                <option key={type.key} value={type.key}>
                  {type.label}
                </option>
              ))}
            </select>
            {fieldType && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
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
              placeholder="Optional field description"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
              rows={2}
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
              placeholder="Optional help text for users"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
            />
          </div>
        </div>
        
        {/* Display & Visibility Settings */}
        <div className="border-t border-gray-200 dark:border-gray-700 pt-6 space-y-4">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white">
            Display & Visibility
          </h4>
          
          <div className="space-y-3">
            {/* Visibility Checkboxes */}
            <div className="flex items-center">
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
              <label htmlFor="visible-list" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Show in record list view
              </label>
            </div>
            
            <div className="flex items-center">
              <input
                type="checkbox"
                id="visible-detail"
                checked={field.is_visible_in_detail !== false}
                onChange={(e) => onUpdate({ is_visible_in_detail: e.target.checked })}
                className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
              />
              <label htmlFor="visible-detail" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Show in record detail view
              </label>
            </div>
            
            <div className="flex items-center">
              <input
                type="checkbox"
                id="searchable"
                checked={field.is_searchable !== false}
                onChange={(e) => onUpdate({ is_searchable: e.target.checked })}
                className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
              />
              <label htmlFor="searchable" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Include in search results
              </label>
            </div>
          </div>
        </div>
        
        {/* NEW FieldConfigurationPanel Integration */}
        <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
          <FieldConfigurationPanel
            fieldType={field.field_type || field.type || ''}
            config={field.field_config || field.config || {}}
            onChange={(newConfig) => onUpdate({ 
              field_config: newConfig,
              config: newConfig // Legacy support
            })}
            storageConstraints={field.storage_constraints || {}}
            onStorageConstraintsChange={(newConstraints) => onUpdate({ storage_constraints: newConstraints })}
            businessRules={field.business_rules || {}}
            onBusinessRulesChange={(newRules) => onUpdate({ business_rules: newRules })}
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