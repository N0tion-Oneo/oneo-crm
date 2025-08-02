'use client'

import { useState, useEffect } from 'react'
import { fieldTypesApi, globalOptionsApi, pipelinesApi } from '@/lib/api'
import { 
  Plus, 
  Trash2, 
  ChevronDown,
  ChevronRight,
  AlertCircle,
  Info,
  HelpCircle
} from 'lucide-react'

interface FieldTypeConfig {
  key: string
  label: string
  description: string
  category: 'basic' | 'selection' | 'datetime' | 'advanced' | 'system'
  icon: string
  config_schema: any
  supports_validation: boolean
  is_computed: boolean
  config_class: string
}

interface Pipeline {
  id: string
  name: string
  slug: string
}

interface FieldConfigurationPanelProps {
  fieldType: string
  config: Record<string, any>
  onChange: (config: Record<string, any>) => void
  storageConstraints?: Record<string, any>
  onStorageConstraintsChange?: (constraints: Record<string, any>) => void
  isVisible?: boolean
  availableFields?: { id: string; name: string; display_name: string; field_type: string; field_config?: Record<string, any> }[]
}

export function FieldConfigurationPanel({
  fieldType,
  config,
  onChange,
  storageConstraints = {},
  onStorageConstraintsChange,
  isVisible = true,
  availableFields = []
}: FieldConfigurationPanelProps) {
  const [fieldTypeConfig, setFieldTypeConfig] = useState<FieldTypeConfig | null>(null)
  const [globalOptions, setGlobalOptions] = useState<any>(null)
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [targetPipelineFields, setTargetPipelineFields] = useState<{ id: string; name: string; display_name: string; field_type: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['field_config', 'storage_constraints']))

  // Load field type configuration and global options
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        
        // Load field type configuration
        const fieldResponse = await fieldTypesApi.get(fieldType)
        setFieldTypeConfig(fieldResponse.data)
        
        // Load global options for currencies, countries, etc.
        try {
          const globalResponse = await globalOptionsApi.getAll()
          setGlobalOptions(globalResponse.data)
        } catch (error) {
          console.warn('Global options not available:', error)
        }
        
        // Load pipelines for relation fields
        if (fieldType === 'relation') {
          try {
            const pipelinesResponse = await pipelinesApi.list()
            setPipelines(pipelinesResponse.data.results || [])
          } catch (error) {
            console.warn('Pipelines not available:', error)
          }
        }
        
      } catch (error) {
        console.error('Failed to load field configuration:', error)
      } finally {
        setLoading(false)
      }
    }

    if (fieldType) {
      loadData()
    }
  }, [fieldType])

  // Load target pipeline fields when target_pipeline_id changes
  useEffect(() => {
    const loadTargetPipelineFields = async () => {
      if (fieldType === 'relation' && config.target_pipeline_id) {
        try {
          const fieldsResponse = await pipelinesApi.getFields(config.target_pipeline_id.toString())
          
          // Handle different possible response structures
          let fieldData = fieldsResponse.data
          if (Array.isArray(fieldData.results)) {
            fieldData = fieldData.results
          } else if (Array.isArray(fieldData.fields)) {
            fieldData = fieldData.fields
          } else if (!Array.isArray(fieldData)) {
            console.warn('Unexpected field data structure:', fieldData)
            fieldData = []
          }
          
          const fields = fieldData.map((field: any) => ({
            id: field.id,
            name: field.name || field.slug,
            display_name: field.display_name || field.label || field.name,
            field_type: field.field_type || field.type || 'text'
          }))
          
          setTargetPipelineFields(fields)
          
          // If display_field is not set or doesn't exist in target fields, set it to first available field
          if (fields.length > 0 && (!config.display_field || !fields.find((f: any) => f.name === config.display_field))) {
            onChange({ ...config, display_field: fields[0].name })
          }
        } catch (error: any) {
          console.error('❌ Failed to load target pipeline fields:', error)
          console.error('❌ Error details:', {
            status: error.response?.status,
            statusText: error.response?.statusText,
            data: error.response?.data,
            url: error.config?.url
          })
          setTargetPipelineFields([])
        }
      } else {
        setTargetPipelineFields([])
      }
    }

    loadTargetPipelineFields()
  }, [fieldType, config.target_pipeline_id])


  // Toggle section expansion
  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev)
      if (newSet.has(section)) {
        newSet.delete(section)
      } else {
        newSet.add(section)
      }
      return newSet
    })
  }

  // Update configuration value
  const updateConfig = (key: string, value: any) => {
    onChange({
      ...config,
      [key]: value
    })
  }

  // Update storage constraints
  const updateStorageConstraints = (key: string, value: any) => {
    if (onStorageConstraintsChange) {
      onStorageConstraintsChange({
        ...storageConstraints,
        [key]: value
      })
    }
  }


  // Get user-friendly labels for enum values
  const getEnumLabel = (key: string, value: string) => {
    const enumLabels: Record<string, Record<string, string>> = {
      resize: {
        'none': 'No Resize',
        'both': 'Both Directions',
        'horizontal': 'Horizontal Only',
        'vertical': 'Vertical Only'
      },
      allowed_protocols: {
        'http': 'HTTP',
        'https': 'HTTPS (Secure)',
        'ftp': 'FTP',
        'mailto': 'Email Links',
        'tel': 'Phone Links'
      },
      format: {
        'integer': 'Whole Numbers',
        'decimal': 'Decimal Numbers',
        'currency': 'Currency',
        'percentage': 'Percentage',
        'auto_increment': 'Auto-Increment'
      },
      date_format: {
        'MM/DD/YYYY': 'MM/DD/YYYY (US)',
        'DD/MM/YYYY': 'DD/MM/YYYY (European)',
        'YYYY-MM-DD': 'YYYY-MM-DD (ISO)'
      },
      time_format: {
        '12h': '12 Hour (AM/PM)',
        '24h': '24 Hour'
      },
      button_style: {
        'primary': 'Primary (Blue)',
        'secondary': 'Secondary (Gray)',
        'success': 'Success (Green)',
        'warning': 'Warning (Yellow)',
        'danger': 'Danger (Red)'
      },
      button_size: {
        'small': 'Small',
        'medium': 'Medium',
        'large': 'Large'
      },
      address_format: {
        'single_line': 'Single Line',
        'multi_line': 'Multi Line',
        'structured': 'Structured Components'
      },
      display_format: {
        'full': 'Full Address',
        'compact': 'Compact',
        'custom': 'Custom Format'
      },
      output_type: {
        'text': 'Text',
        'number': 'Number',
        'tags': 'Tags',
        'url': 'URL',
        'json': 'JSON Object'
      },
      model: {
        'gpt-4.1': 'GPT-4.1 (Most Capable)',
        'gpt-4.1-mini': 'GPT-4.1 Mini (Fast & Cost-Effective)',
        'o3': 'O3 (Advanced Reasoning)',
        'o3-mini': 'O3 Mini (Fast Reasoning)',
        'gpt-4o': 'GPT-4o (Multimodal)',
        'gpt-3.5-turbo': 'GPT-3.5 Turbo (Legacy)'
      }
    }

    return enumLabels[key]?.[value] || value.charAt(0).toUpperCase() + value.slice(1)
  }

  // Render contextual field configuration based on field type
  const renderContextualFieldConfig = () => {
    if (!fieldTypeConfig) return null

    switch (fieldType) {
      case 'number':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Number Format
              </label>
              <select
                value={config.format || 'integer'}
                onChange={(e) => updateConfig('format', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
              >
                <option value="integer">Whole Numbers</option>
                <option value="decimal">Decimal Numbers</option>
                <option value="currency">Currency</option>
                <option value="percentage">Percentage</option>
                <option value="auto_increment">Auto-Increment</option>
              </select>
            </div>

            {config.format === 'currency' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Currency Restriction (Optional)
                </label>
                <select
                  value={config.currency_code || ''}
                  onChange={(e) => updateConfig('currency_code', e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                >
                  <option value="">Allow any currency</option>
                  {globalOptions?.currencies?.map((currency: any) => (
                    <option key={currency.code} value={currency.code}>
                      {currency.name} ({currency.symbol}) - Restrict to this currency only
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Leave blank to allow users to select any currency. Choose a specific currency to restrict the field to only that currency.
                </p>
              </div>
            )}

            {config.format === 'auto_increment' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Prefix (Optional)
                  </label>
                  <input
                    type="text"
                    value={config.auto_increment_prefix || ''}
                    onChange={(e) => updateConfig('auto_increment_prefix', e.target.value)}
                    placeholder="INV-, CUST-, etc."
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Starting Number
                  </label>
                  <input
                    type="number"
                    value={config.auto_increment_start || 1}
                    onChange={(e) => updateConfig('auto_increment_start', parseInt(e.target.value) || 1)}
                    min="1"
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                  />
                </div>
              </>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Decimal Places
              </label>
              <input
                type="number"
                value={config.decimal_places || 2}
                onChange={(e) => updateConfig('decimal_places', parseInt(e.target.value) || 2)}
                min="0"
                max="10"
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
              />
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="thousands-separator"
                checked={config.thousands_separator !== false}
                onChange={(e) => updateConfig('thousands_separator', e.target.checked)}
                className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
              />
              <label htmlFor="thousands-separator" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Show thousands separator (1,000)
              </label>
            </div>
          </div>
        )

      case 'date':
        return (
          <div className="space-y-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="include-time"
                checked={config.include_time || false}
                onChange={(e) => updateConfig('include_time', e.target.checked)}
                className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
              />
              <label htmlFor="include-time" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Include time picker
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Date Format
              </label>
              <select
                value={config.date_format || 'MM/DD/YYYY'}
                onChange={(e) => updateConfig('date_format', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
              >
                <option value="MM/DD/YYYY">MM/DD/YYYY (US)</option>
                <option value="DD/MM/YYYY">DD/MM/YYYY (European)</option>
                <option value="YYYY-MM-DD">YYYY-MM-DD (ISO)</option>
              </select>
            </div>

            {config.include_time && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Time Format
                </label>
                <select
                  value={config.time_format || '12h'}
                  onChange={(e) => updateConfig('time_format', e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                >
                  <option value="12h">12 Hour (AM/PM)</option>
                  <option value="24h">24 Hour</option>
                </select>
              </div>
            )}
          </div>
        )

      case 'ai_generated':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                AI Prompt Template *
              </label>
              <textarea
                value={config.prompt || ''}
                onChange={(e) => updateConfig('prompt', e.target.value)}
                placeholder="Enter your AI prompt template..."
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                rows={4}
              />
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                <p className="mb-2">Use field references in your prompt:</p>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  <div><code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">{'{*}'}</code> - Include all fields</div>
                  {availableFields.length > 0 ? (
                    availableFields.map(field => (
                      <div key={field.id}>
                        <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">{`{${field.name}}`}</code> - {field.display_name} ({field.field_type})
                      </div>
                    ))
                  ) : (
                    <div><code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">{'{field_name}'}</code> - Reference other fields by name</div>
                  )}
                </div>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                AI Model
              </label>
              <select
                value={config.model || 'gpt-4.1-mini'}
                onChange={(e) => updateConfig('model', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
              >
                <option value="gpt-4.1-mini">GPT-4.1 Mini (Fast & Cost-Effective)</option>
                <option value="gpt-4.1">GPT-4.1 (Most Capable)</option>
                <option value="o3-mini">O3 Mini (Fast Reasoning)</option>
                <option value="o3">O3 (Advanced Reasoning)</option>
                <option value="gpt-4o">GPT-4o (Multimodal)</option>
                <option value="gpt-3.5-turbo">GPT-3.5 Turbo (Legacy)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Creativity Level
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={config.temperature || 0.3}
                onChange={(e) => updateConfig('temperature', parseFloat(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>Precise (0)</span>
                <span>{config.temperature || 0.3}</span>
                <span>Creative (1)</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Output Type
              </label>
              <select
                value={config.output_type || 'text'}
                onChange={(e) => updateConfig('output_type', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
              >
                <option value="text">Text</option>
                <option value="number">Number</option>
                <option value="tags">Tags</option>
                <option value="url">URL</option>
                <option value="json">JSON Object</option>
              </select>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="enable-tools"
                checked={config.enable_tools || false}
                onChange={(e) => updateConfig('enable_tools', e.target.checked)}
                className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
              />
              <label htmlFor="enable-tools" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Enable AI tools (web search, code interpreter, etc.)
              </label>
            </div>

            {config.enable_tools && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Allowed Tools
                </label>
                <div className="space-y-2">
                  {[
                    { key: 'web_search', label: 'Web Search' },
                    { key: 'code_interpreter', label: 'Code Interpreter' },
                    { key: 'file_reader', label: 'File Reader' },
                    { key: 'dalle', label: 'DALL-E Image Generation' }
                  ].map((tool) => (
                    <div key={tool.key} className="flex items-center">
                      <input
                        type="checkbox"
                        id={`tool-${tool.key}`}
                        checked={(config.allowed_tools || []).includes(tool.key)}
                        onChange={(e) => {
                          const currentTools = config.allowed_tools || []
                          const newTools = e.target.checked
                            ? [...currentTools, tool.key]
                            : currentTools.filter((t: string) => t !== tool.key)
                          updateConfig('allowed_tools', newTools)
                        }}
                        className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
                      />
                      <label htmlFor={`tool-${tool.key}`} className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                        {tool.label}
                      </label>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Trigger Fields (Optional)
              </label>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                AI will regenerate when these fields change. Leave empty to trigger on any field change.
              </p>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {availableFields.length > 0 ? (
                  availableFields.map((field) => (
                    <div key={field.id} className="flex items-center">
                      <input
                        type="checkbox"
                        id={`trigger-${field.id}`}
                        checked={(config.trigger_fields || []).includes(field.name)}
                        onChange={(e) => {
                          const currentFields = config.trigger_fields || []
                          const newFields = e.target.checked
                            ? [...currentFields, field.name]
                            : currentFields.filter((f: string) => f !== field.name)
                          updateConfig('trigger_fields', newFields)
                        }}
                        className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
                      />
                      <label htmlFor={`trigger-${field.id}`} className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                        {field.display_name} ({field.field_type})
                      </label>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                    Add other fields to the pipeline first to configure triggers
                  </p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Excluded Fields (Optional)
              </label>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                Hide these fields from the AI context for privacy or security.
              </p>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {availableFields.length > 0 ? (
                  availableFields.map((field) => (
                    <div key={field.id} className="flex items-center">
                      <input
                        type="checkbox"
                        id={`exclude-${field.id}`}
                        checked={(config.excluded_fields || []).includes(field.name)}
                        onChange={(e) => {
                          const currentFields = config.excluded_fields || []
                          const newFields = e.target.checked
                            ? [...currentFields, field.name]
                            : currentFields.filter((f: string) => f !== field.name)
                          updateConfig('excluded_fields', newFields)
                        }}
                        className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
                      />
                      <label htmlFor={`exclude-${field.id}`} className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                        {field.display_name} ({field.field_type})
                      </label>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                    Add other fields to the pipeline first to configure exclusions
                  </p>
                )}
              </div>
            </div>
          </div>
        )

      case 'select':
      case 'multiselect':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Options *
              </label>
              <div className="space-y-2">
                {(config.options || []).map((option: any, index: number) => (
                  <div key={index} className="flex items-center space-x-2">
                    <input
                      type="text"
                      placeholder="Value"
                      value={option.value || ''}
                      onChange={(e) => {
                        const newOptions = [...(config.options || [])]
                        newOptions[index] = { ...option, value: e.target.value }
                        updateConfig('options', newOptions)
                      }}
                      className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                    />
                    <input
                      type="text"
                      placeholder="Label"
                      value={option.label || ''}
                      onChange={(e) => {
                        const newOptions = [...(config.options || [])]
                        newOptions[index] = { ...option, label: e.target.value }
                        updateConfig('options', newOptions)
                      }}
                      className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                    />
                    <button
                      onClick={() => {
                        const newOptions = (config.options || []).filter((_: any, i: number) => i !== index)
                        updateConfig('options', newOptions)
                      }}
                      className="p-2 text-red-600 hover:text-red-800"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <button
                  onClick={() => {
                    const newOptions = [...(config.options || []), { value: '', label: '' }]
                    updateConfig('options', newOptions)
                  }}
                  className="w-full px-3 py-2 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-md text-gray-500 hover:border-primary hover:text-primary transition-colors"
                >
                  <Plus className="w-4 h-4 mx-auto" />
                </button>
              </div>
            </div>

            {fieldType === 'select' && (
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="allow-custom"
                  checked={config.allow_custom || false}
                  onChange={(e) => updateConfig('allow_custom', e.target.checked)}
                  className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
                />
                <label htmlFor="allow-custom" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                  Allow custom values
                </label>
              </div>
            )}
          </div>
        )

      case 'relation':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Target Pipeline *
              </label>
              <select
                value={config.target_pipeline_id || ''}
                onChange={(e) => {
                  const newPipelineId = parseInt(e.target.value) || null
                  // Clear display field when pipeline changes and update both at once
                  if (newPipelineId !== config.target_pipeline_id) {
                    onChange({ ...config, target_pipeline_id: newPipelineId, display_field: '' })
                  } else {
                    updateConfig('target_pipeline_id', newPipelineId)
                  }
                }}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
              >
                <option value="">Select pipeline...</option>
                {pipelines.map((pipeline) => (
                  <option key={pipeline.id} value={pipeline.id}>
                    {pipeline.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Display Field
                {/* Debug info */}
                <span className="text-xs text-gray-400 ml-2">
                  (Debug: {targetPipelineFields.length} fields available)
                </span>
              </label>
              <select
                value={config.display_field || ''}
                onChange={(e) => updateConfig('display_field', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                disabled={!config.target_pipeline_id || targetPipelineFields.length === 0}
              >
                {!config.target_pipeline_id ? (
                  <option value="">Select target pipeline first...</option>
                ) : targetPipelineFields.length === 0 ? (
                  <option value="">No fields available</option>
                ) : (
                  <>
                    <option value="">Select field to display...</option>
                    {targetPipelineFields.map((field) => (
                      <option key={field.id} value={field.name}>
                        {field.display_name} ({field.field_type})
                      </option>
                    ))}
                  </>
                )}
              </select>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Which field from the target pipeline should be displayed in this relation field
              </p>
            </div>
          </div>
        )

      case 'text':
        return (
          <div className="space-y-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="case-sensitive"
                checked={config.case_sensitive !== false}
                onChange={(e) => updateConfig('case_sensitive', e.target.checked)}
                className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
              />
              <label htmlFor="case-sensitive" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Case sensitive
              </label>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="auto-format"
                checked={config.auto_format || false}
                onChange={(e) => updateConfig('auto_format', e.target.checked)}
                className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
              />
              <label htmlFor="auto-format" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Auto-format text
              </label>
            </div>
          </div>
        )

      case 'textarea':
        return (
          <div className="space-y-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="rich-text"
                checked={config.enable_rich_text || false}
                onChange={(e) => updateConfig('enable_rich_text', e.target.checked)}
                className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
              />
              <label htmlFor="rich-text" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Enable rich text editor
              </label>
            </div>
          </div>
        )

      case 'email':
        return (
          <div className="space-y-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="auto-lowercase"
                checked={config.auto_lowercase !== false}
                onChange={(e) => updateConfig('auto_lowercase', e.target.checked)}
                className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
              />
              <label htmlFor="auto-lowercase" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Automatically convert to lowercase
              </label>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="trim-whitespace"
                checked={config.trim_whitespace !== false}
                onChange={(e) => updateConfig('trim_whitespace', e.target.checked)}
                className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
              />
              <label htmlFor="trim-whitespace" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Trim whitespace
              </label>
            </div>
          </div>
        )

      case 'phone':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Default Country (Optional)
              </label>
              <select
                value={config.default_country || ''}
                onChange={(e) => updateConfig('default_country', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
              >
                <option value="">Allow any country</option>
                {globalOptions?.countries?.map((country: any) => (
                  <option key={country.code} value={country.code}>
                    {country.name} ({country.phone_code}) - Default to this country
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Leave blank to let users select any country. Choose a specific country to pre-select it by default.
              </p>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="require-country-code"
                checked={config.require_country_code !== false}
                onChange={(e) => updateConfig('require_country_code', e.target.checked)}
                className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
              />
              <label htmlFor="require-country-code" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Require country code
              </label>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="format-display"
                checked={config.format_display !== false}
                onChange={(e) => updateConfig('format_display', e.target.checked)}
                className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
              />
              <label htmlFor="format-display" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Format display (+1 (555) 123-4567)
              </label>
            </div>
          </div>
        )

      default:
        return (
          <div className="p-4 text-center text-gray-500 dark:text-gray-400">
            <Info className="w-8 h-8 mx-auto mb-2" />
            <p className="text-sm">No specific configuration options for this field type.</p>
          </div>
        )
    }
  }

  // Render form field based on schema property (legacy fallback)
  const renderFormField = (key: string, property: any, value: any) => {
    const label = property.title || key.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())
    const description = property.description
    const isRequired = property.required || false

    // Handle different input types based on schema
    switch (property.type) {
      case 'string':
        if (property.enum && property.enum.length > 0) {
          // Enum select - improved labels for better UX
          const hasDefaultValue = value && property.enum.includes(value)
          return (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {label}
                {isRequired && <span className="text-red-500 ml-1">*</span>}
              </label>
              {description && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{description}</p>
              )}
              <select
                value={hasDefaultValue ? value : (property.enum[0] || '')}
                onChange={(e) => updateConfig(key, e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
              >
                {property.enum.map((option: string) => (
                  <option key={option} value={option}>
                    {getEnumLabel(key, option)}
                  </option>
                ))}
              </select>
              {!hasDefaultValue && value && (
                <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
                  Current value "{value}" is not in the available options. It will be reset to the first option.
                </p>
              )}
            </div>
          )
        } else if (key === 'currency_code' && globalOptions?.currencies) {
          // Currency select
          return (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {label}
              </label>
              <select
                value={value || ''}
                onChange={(e) => updateConfig(key, e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
              >
                <option value="">Select currency...</option>
                {globalOptions.currencies.map((currency: any) => (
                  <option key={currency.code} value={currency.code}>
                    {currency.name} ({currency.symbol})
                  </option>
                ))}
              </select>
            </div>
          )
        } else if (key === 'default_country' && globalOptions?.countries) {
          // Country select
          return (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {label}
              </label>
              <select
                value={value || ''}
                onChange={(e) => updateConfig(key, e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
              >
                <option value="">Select country...</option>
                {globalOptions.countries.map((country: any) => (
                  <option key={country.code} value={country.code}>
                    {country.name} ({country.phone_code})
                  </option>
                ))}
              </select>
            </div>
          )
        } else {
          // Regular text input
          return (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {label}
                {isRequired && <span className="text-red-500 ml-1">*</span>}
              </label>
              {description && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{description}</p>
              )}
              <input
                type="text"
                value={value || ''}
                onChange={(e) => updateConfig(key, e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
              />
            </div>
          )
        }

      case 'integer':
      case 'number':
        return (
          <div key={key}>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {label}
              {isRequired && <span className="text-red-500 ml-1">*</span>}
            </label>
            {description && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{description}</p>
            )}
            <input
              type="number"
              value={value !== undefined ? value : ''}
              onChange={(e) => updateConfig(key, property.type === 'integer' ? parseInt(e.target.value) || null : parseFloat(e.target.value) || null)}
              min={property.minimum}
              max={property.maximum}
              step={property.type === 'integer' ? 1 : 0.01}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
            />
          </div>
        )

      case 'boolean':
        return (
          <div key={key} className="flex items-center">
            <input
              type="checkbox"
              id={`config-${key}`}
              checked={value !== undefined ? value : false}
              onChange={(e) => updateConfig(key, e.target.checked)}
              className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
            />
            <label htmlFor={`config-${key}`} className="ml-2 text-sm text-gray-700 dark:text-gray-300">
              {label}
              {isRequired && <span className="text-red-500 ml-1">*</span>}
            </label>
            {description && (
              <div className="ml-2 group relative">
                <HelpCircle className="w-4 h-4 text-gray-400 cursor-help" />
                <div className="absolute bottom-6 left-0 hidden group-hover:block bg-gray-900 text-white text-xs rounded py-1 px-2 whitespace-nowrap z-10">
                  {description}
                </div>
              </div>
            )}
          </div>
        )

      case 'array':
        if (key === 'options' && (fieldType === 'select' || fieldType === 'multiselect')) {
          // Special handling for select options
          const options = value || []
          return (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {label}
                {isRequired && <span className="text-red-500 ml-1">*</span>}
              </label>
              {description && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{description}</p>
              )}
              <div className="space-y-2">
                {options.map((option: any, index: number) => (
                  <div key={index} className="flex items-center space-x-2">
                    <input
                      type="text"
                      placeholder="Value"
                      value={option.value || ''}
                      onChange={(e) => {
                        const newOptions = [...options]
                        newOptions[index] = { ...option, value: e.target.value }
                        updateConfig(key, newOptions)
                      }}
                      className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                    />
                    <input
                      type="text"
                      placeholder="Label"
                      value={option.label || ''}
                      onChange={(e) => {
                        const newOptions = [...options]
                        newOptions[index] = { ...option, label: e.target.value }
                        updateConfig(key, newOptions)
                      }}
                      className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                    />
                    <button
                      onClick={() => {
                        const newOptions = options.filter((_: any, i: number) => i !== index)
                        updateConfig(key, newOptions)
                      }}
                      className="p-2 text-red-600 hover:text-red-800"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <button
                  onClick={() => {
                    const newOptions = [...options, { value: '', label: '' }]
                    updateConfig(key, newOptions)
                  }}
                  className="w-full px-3 py-2 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-md text-gray-500 hover:border-primary hover:text-primary transition-colors"
                >
                  <Plus className="w-4 h-4 mx-auto" />
                </button>
              </div>
            </div>
          )
        } else if (key === 'allowed_tools' && fieldType === 'ai_generated') {
          // Multi-select for AI tools
          const selectedTools = value || []
          const availableTools = [
            { key: 'web_search', label: 'Web Search' },
            { key: 'code_interpreter', label: 'Code Interpreter' },
            { key: 'file_reader', label: 'File Reader' },
            { key: 'dalle', label: 'DALL-E Image Generation' },
            { key: 'image_generation', label: 'Image Generation' }
          ]
          
          return (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {label}
              </label>
              {description && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{description}</p>
              )}
              <div className="space-y-2">
                {availableTools.map((tool) => (
                  <div key={tool.key} className="flex items-center">
                    <input
                      type="checkbox"
                      id={`tool-${tool.key}`}
                      checked={selectedTools.includes(tool.key)}
                      onChange={(e) => {
                        const newTools = e.target.checked
                          ? [...selectedTools, tool.key]
                          : selectedTools.filter((t: string) => t !== tool.key)
                        updateConfig(key, newTools)
                      }}
                      className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
                    />
                    <label htmlFor={`tool-${tool.key}`} className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      {tool.label}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          )
        } else if (key === 'allowed_protocols' && fieldType === 'url') {
          // Multi-select for URL protocols
          const selectedProtocols = value || ['http', 'https']
          const availableProtocols = ['http', 'https', 'ftp', 'mailto', 'tel']
          
          return (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {label}
              </label>
              {description && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{description}</p>
              )}
              <div className="space-y-2">
                {availableProtocols.map((protocol) => (
                  <div key={protocol} className="flex items-center">
                    <input
                      type="checkbox"
                      id={`protocol-${protocol}`}
                      checked={selectedProtocols.includes(protocol)}
                      onChange={(e) => {
                        const newProtocols = e.target.checked
                          ? [...selectedProtocols, protocol]
                          : selectedProtocols.filter((p: string) => p !== protocol)
                        updateConfig(key, newProtocols)
                      }}
                      className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
                    />
                    <label htmlFor={`protocol-${protocol}`} className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      {getEnumLabel('allowed_protocols', protocol)}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          )
        } else if (key === 'trigger_fields' || key === 'excluded_fields') {
          // Field selection for AI fields
          const selectedFields = value || []
          // TODO: Get available fields from the current pipeline
          const availableFields = ['title', 'description', 'status', 'priority'] // Placeholder
          
          return (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {label}
              </label>
              {description && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{description}</p>
              )}
              <div className="space-y-2">
                {availableFields.map((fieldName) => (
                  <div key={fieldName} className="flex items-center">
                    <input
                      type="checkbox"
                      id={`${key}-${fieldName}`}
                      checked={selectedFields.includes(fieldName)}
                      onChange={(e) => {
                        const newFields = e.target.checked
                          ? [...selectedFields, fieldName]
                          : selectedFields.filter((f: string) => f !== fieldName)
                        updateConfig(key, newFields)
                      }}
                      className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
                    />
                    <label htmlFor={`${key}-${fieldName}`} className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      {fieldName}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          )
        } else if (key === 'allowed_domains' || key === 'blocked_domains') {
          // Simple string array editor for domains
          const domains = value || []
          return (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {label}
              </label>
              {description && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{description}</p>
              )}
              <div className="space-y-2">
                {domains.map((domain: string, index: number) => (
                  <div key={index} className="flex items-center space-x-2">
                    <input
                      type="text"
                      placeholder="example.com"
                      value={domain}
                      onChange={(e) => {
                        const newDomains = [...domains]
                        newDomains[index] = e.target.value
                        updateConfig(key, newDomains)
                      }}
                      className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                    />
                    <button
                      onClick={() => {
                        const newDomains = domains.filter((_: string, i: number) => i !== index)
                        updateConfig(key, newDomains)
                      }}
                      className="p-2 text-red-600 hover:text-red-800"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <button
                  onClick={() => {
                    const newDomains = [...domains, '']
                    updateConfig(key, newDomains)
                  }}
                  className="w-full px-3 py-2 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-md text-gray-500 hover:border-primary hover:text-primary transition-colors"
                >
                  <Plus className="w-4 h-4 mx-auto" />
                </button>
              </div>
            </div>
          )
        }
        break

      default:
        // Handle special cases
        if (key === 'target_pipeline_id' && fieldType === 'relation') {
          return (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Target Pipeline
                <span className="text-red-500 ml-1">*</span>
              </label>
              <select
                value={value || ''}
                onChange={(e) => updateConfig(key, parseInt(e.target.value))}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
              >
                <option value="">Select pipeline...</option>
                {pipelines.map((pipeline) => (
                  <option key={pipeline.id} value={pipeline.id}>
                    {pipeline.name}
                  </option>
                ))}
              </select>
            </div>
          )
        } else if (key === 'prompt' && fieldType === 'ai_generated') {
          return (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                AI Prompt Template
                <span className="text-red-500 ml-1">*</span>
              </label>
              {description && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{description}</p>
              )}
              <textarea
                value={value || ''}
                onChange={(e) => updateConfig(key, e.target.value)}
                placeholder="Enter your AI prompt template..."
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                rows={4}
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Use {'{field_name}'} to reference other fields, or {'{*}'} for all fields
              </p>
            </div>
          )
        } else if (key === 'components' && fieldType === 'address') {
          const components = value || {}
          const availableComponents = [
            { key: 'street_address', label: 'Street Address' },
            { key: 'apartment_suite', label: 'Apartment/Suite' },
            { key: 'city', label: 'City' },
            { key: 'state_province', label: 'State/Province' },
            { key: 'postal_code', label: 'Postal Code' },
            { key: 'country', label: 'Country' }
          ]
          
          return (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Address Components
              </label>
              <div className="space-y-2">
                {availableComponents.map((component) => (
                  <div key={component.key} className="flex items-center">
                    <input
                      type="checkbox"
                      id={`component-${component.key}`}
                      checked={components[component.key] ?? true}
                      onChange={(e) => {
                        updateConfig(key, {
                          ...components,
                          [component.key]: e.target.checked
                        })
                      }}
                      className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
                    />
                    <label htmlFor={`component-${component.key}`} className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      {component.label}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          )
        }
        break
    }

    return null
  }

  if (!isVisible) return null

  if (loading) {
    return (
      <div className="p-4 text-center">
        <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full mx-auto mb-2"></div>
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading configuration...</p>
      </div>
    )
  }

  if (!fieldTypeConfig) {
    return (
      <div className="p-4">
        <div className="flex items-center text-amber-600 dark:text-amber-400 mb-2">
          <Info className="w-4 h-4 mr-2" />
          <span className="text-sm font-medium">No Configuration Available</span>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          This field type configuration could not be loaded.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Field Type Info */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md">
        <div className="flex items-center mb-1">
          <div className="text-sm font-medium text-blue-900 dark:text-blue-100">
            {fieldTypeConfig.label} Field
          </div>
        </div>
        <p className="text-xs text-blue-700 dark:text-blue-300">
          {fieldTypeConfig.description}
        </p>
      </div>

      {/* Contextual Field Configuration */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-md">
        <button
          onClick={() => toggleSection('field_config')}
          className="w-full px-3 py-2 flex items-center justify-between text-left bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          <span className="text-sm font-medium text-gray-900 dark:text-white">
            Field Configuration
          </span>
          {expandedSections.has('field_config') ? (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500" />
          )}
        </button>
        
        {expandedSections.has('field_config') && (
          <div className="p-3 border-t border-gray-200 dark:border-gray-700">
            {renderContextualFieldConfig()}
          </div>
        )}
      </div>

      {/* Storage Constraints Section */}
      {onStorageConstraintsChange && (
        <div className="border border-gray-200 dark:border-gray-700 rounded-md">
          <button
            onClick={() => toggleSection('storage_constraints')}
            className="w-full px-3 py-2 flex items-center justify-between text-left bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <span className="text-sm font-medium text-gray-900 dark:text-white flex items-center">
              Storage Constraints
              <HelpCircle className="w-3 h-3 ml-1 text-gray-400" />
            </span>
            {expandedSections.has('storage_constraints') ? (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500" />
            )}
          </button>
          
          {expandedSections.has('storage_constraints') && (
            <div className="p-3 space-y-4 border-t border-gray-200 dark:border-gray-700">
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-3 bg-blue-50 dark:bg-blue-900/20 p-2 rounded">
                <div className="flex items-start space-x-2">
                  <Info className="w-3 h-3 text-blue-500 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-medium text-blue-700 dark:text-blue-300 mb-1">Database-Level Constraints</div>
                    <div>These settings control how data is stored in the database. They never block incomplete data - that's handled by business rules and forms.</div>
                  </div>
                </div>
              </div>

              {/* Storage Behavior */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Storage Behavior
                </label>
                
                <div className="space-y-2">
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="allow-null"
                      checked={storageConstraints.allow_null !== false}
                      onChange={(e) => updateStorageConstraints('allow_null', e.target.checked)}
                      className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
                    />
                    <label htmlFor="allow-null" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Allow NULL values (recommended: always true)
                    </label>
                  </div>
                  
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="enforce-uniqueness"
                      checked={storageConstraints.enforce_uniqueness || false}
                      onChange={(e) => updateStorageConstraints('enforce_uniqueness', e.target.checked)}
                      className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
                    />
                    <label htmlFor="enforce-uniqueness" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Enforce database uniqueness constraint
                    </label>
                  </div>
                  
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="create-index"
                      checked={storageConstraints.create_index || false}
                      onChange={(e) => updateStorageConstraints('create_index', e.target.checked)}
                      className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
                    />
                    <label htmlFor="create-index" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Create database index (improves query performance)
                    </label>
                  </div>
                </div>
              </div>

              {/* Storage Limits */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Storage Limits
                </label>
                
                <div className="grid grid-cols-1 gap-3">
                  <div>
                    <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                      Maximum Storage Length (characters)
                    </label>
                    <input
                      type="number"
                      value={storageConstraints.max_storage_length || ''}
                      onChange={(e) => updateStorageConstraints('max_storage_length', e.target.value ? parseInt(e.target.value) : null)}
                      placeholder="Leave empty for no limit"
                      min="1"
                      max="65535"
                      className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                    />
                  </div>

                  {fieldType === 'number' && (
                    <>
                      <div>
                        <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                          Numeric Precision (total digits)
                        </label>
                        <input
                          type="number"
                          value={storageConstraints.numeric_precision || ''}
                          onChange={(e) => updateStorageConstraints('numeric_precision', e.target.value ? parseInt(e.target.value) : null)}
                          placeholder="e.g., 10"
                          min="1"
                          max="65"
                          className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                          Numeric Scale (decimal places)
                        </label>
                        <input
                          type="number"
                          value={storageConstraints.numeric_scale || ''}
                          onChange={(e) => updateStorageConstraints('numeric_scale', e.target.value ? parseInt(e.target.value) : null)}
                          placeholder="e.g., 2"
                          min="0"
                          max="30"
                          className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                        />
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  )
}