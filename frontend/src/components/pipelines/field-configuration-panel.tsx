'use client'

import { useState, useEffect } from 'react'
import { fieldTypesApi, globalOptionsApi } from '@/lib/api'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Separator,
  Badge,
  Checkbox,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from '@/components/ui'
import { HelpCircle, AlertCircle, Info } from 'lucide-react'

// Import registry and types
import { getFieldConfigComponent, hasFieldConfig } from '@/lib/field-configs/registry'
import { FieldTypeConfig } from '@/lib/field-configs/types'
import { getCategoryColor, validateFieldConfig, mergeWithDefaults } from '@/lib/field-configs/utils'

interface FieldConfigurationPanelProps {
  fieldType: string
  config: Record<string, any>
  onChange: (config: Record<string, any>) => void
  storageConstraints?: Record<string, any>
  onStorageConstraintsChange?: (constraints: Record<string, any>) => void
  isVisible?: boolean
  availableFields?: { id: string; name: string; display_name: string; field_type: string; field_config?: Record<string, any> }[]
  // AI configuration props
  aiConfig?: Record<string, any>
  onAiConfigChange?: (aiConfig: Record<string, any>) => void
}

export function FieldConfigurationPanel({
  fieldType,
  config,
  onChange,
  storageConstraints = {},
  onStorageConstraintsChange,
  isVisible = true,
  availableFields = [],
  // AI configuration props
  aiConfig = {},
  onAiConfigChange
}: FieldConfigurationPanelProps) {
  const [fieldTypeConfig, setFieldTypeConfig] = useState<FieldTypeConfig | null>(null)
  const [globalOptions, setGlobalOptions] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [configErrors, setConfigErrors] = useState<string[]>([])

  // Load field type configuration and global options
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        
        // Load field type configuration
        const fieldResponse = await fieldTypesApi.get(fieldType)
        setFieldTypeConfig(fieldResponse.data)
        
        // Load global options if field config requires them
        const fieldConfigComponent = getFieldConfigComponent(fieldType)
        if (fieldConfigComponent?.requiresGlobalOptions) {
          try {
            const globalResponse = await globalOptionsApi.getAll()
            setGlobalOptions(globalResponse.data)
          } catch (error) {
            console.warn('Global options not available:', error)
            setGlobalOptions({})
          }
        }
        
      } catch (error) {
        console.error('Failed to load field configuration:', error)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [fieldType])

  // Validate configuration when it changes
  useEffect(() => {
    if (fieldTypeConfig) {
      const errors = validateFieldConfig(fieldType, config, aiConfig)
      setConfigErrors(errors)
    }
  }, [fieldType, config, aiConfig, fieldTypeConfig])

  // Update configuration with validation
  const updateConfig = (key: string, value: any) => {
    const newConfig = { ...config, [key]: value }
    onChange(newConfig)
  }

  // Update storage constraints
  const updateStorageConstraints = (key: string, value: any) => {
    if (onStorageConstraintsChange) {
      onStorageConstraintsChange({ ...storageConstraints, [key]: value })
    }
  }

  // Render the field-specific configuration component
  const renderFieldConfiguration = () => {
    const fieldConfigComponent = getFieldConfigComponent(fieldType)
    
    if (!fieldConfigComponent) {
      // Fall back to basic configuration for fields without dedicated components
      return (
        <div className="p-4 text-center text-muted-foreground">
          <p className="text-sm">
            Basic configuration for {fieldType} fields is not yet implemented.
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            This field type will use default settings.
          </p>
        </div>
      )
    }

    const Component = fieldConfigComponent.component

    // Prepare props based on component requirements
    const componentProps: any = {
      config,
      onChange: (newConfig: Record<string, any>) => {
        // Handle both individual key updates and complete config updates
        if (typeof newConfig === 'object' && newConfig !== null) {
          onChange(newConfig)
        } else {
          // Fallback for single key updates
          updateConfig(arguments[0], arguments[1])
        }
      }
    }

    // Add conditional props
    if (fieldConfigComponent.requiresAiConfig && onAiConfigChange) {
      componentProps.aiConfig = aiConfig
      componentProps.onAiConfigChange = onAiConfigChange
    }

    if (fieldConfigComponent.requiresAvailableFields) {
      componentProps.availableFields = availableFields
    }

    if (fieldConfigComponent.requiresGlobalOptions) {
      componentProps.globalOptions = globalOptions
    }

    // Special props for select fields
    if (fieldType === 'select' || fieldType === 'multiselect') {
      componentProps.fieldType = fieldType
    }

    // Special props for text fields (text, textarea, email, url)
    if (['text', 'textarea', 'email', 'url'].includes(fieldType)) {
      componentProps.fieldType = fieldType
    }

    return <Component {...componentProps} />
  }

  if (!isVisible) return null

  if (loading) {
    return (
      <div className="p-6 text-center">
        <div className="text-sm text-muted-foreground">Loading field configuration...</div>
      </div>
    )
  }

  if (!fieldTypeConfig) {
    return (
      <div className="p-6 text-center">
        <div className="text-sm text-destructive">Failed to load field configuration</div>
      </div>
    )
  }

  return (
    <TooltipProvider>
      <div className="space-y-6">
        {/* Field Type Information */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <CardTitle className="text-base">{fieldTypeConfig.label} Field</CardTitle>
                <Badge variant="outline" className={getCategoryColor(fieldTypeConfig.category)}>
                  {fieldTypeConfig.category}
                </Badge>
              </div>
              {fieldTypeConfig.is_computed && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Badge variant="secondary" className="text-xs">
                      Computed
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>This field value is automatically generated</p>
                  </TooltipContent>
                </Tooltip>
              )}
            </div>
            <CardDescription className="text-sm">
              {fieldTypeConfig.description}
            </CardDescription>
          </CardHeader>
        </Card>

        {/* Configuration Errors */}
        {configErrors.length > 0 && (
          <Card className="border-destructive">
            <CardHeader className="pb-3">
              <div className="flex items-center space-x-2">
                <AlertCircle className="h-4 w-4 text-destructive" />
                <CardTitle className="text-sm text-destructive">Configuration Issues</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <ul className="space-y-1 text-sm text-destructive">
                {configErrors.map((error, index) => (
                  <li key={index}>• {error}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* Field Configuration */}
        <Accordion type="single" collapsible defaultValue="field-config">
          <AccordionItem value="field-config">
            <AccordionTrigger className="text-base font-medium text-gray-900 dark:text-white">
              Field Configuration
            </AccordionTrigger>
            <AccordionContent className="pt-4 text-gray-900 dark:text-white">
              {renderFieldConfiguration()}
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        {/* Storage Constraints Section */}
        {onStorageConstraintsChange && (
          <Accordion type="single" collapsible defaultValue="storage-constraints">
            <AccordionItem value="storage-constraints">
              <AccordionTrigger className="text-base font-medium text-gray-900 dark:text-white">
                <div className="flex items-center space-x-2">
                  <span className="text-gray-900 dark:text-white">Storage Constraints</span>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <HelpCircle className="h-4 w-4 text-muted-foreground" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="max-w-xs">Database-level constraints that control how data is stored. These never block incomplete data - that's handled by business rules and forms.</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
              </AccordionTrigger>
              <AccordionContent className="pt-4 text-gray-900 dark:text-white">
                <div className="space-y-4">
                  <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
                    <div className="flex items-start space-x-2">
                      <Info className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                      <div className="text-sm text-gray-700 dark:text-gray-300">
                        <div className="font-medium text-blue-800 dark:text-blue-200 mb-1">
                          Database-Level Constraints
                        </div>
                        <div className="text-blue-700 dark:text-blue-300">
                          These settings control how data is stored in the database. They never block incomplete data - that's handled by business rules and forms.
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <Label className="text-base font-medium text-gray-900 dark:text-white">Storage Behavior</Label>
                    
                    <div className="space-y-3">
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="allow-null"
                          checked={storageConstraints.allow_null !== false}
                          onCheckedChange={(checked) => updateStorageConstraints('allow_null', checked)}
                        />
                        <Label htmlFor="allow-null" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                          Allow NULL values (recommended: always true)
                        </Label>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="enforce-uniqueness"
                          checked={storageConstraints.enforce_uniqueness || false}
                          onCheckedChange={(checked) => updateStorageConstraints('enforce_uniqueness', checked)}
                        />
                        <Label htmlFor="enforce-uniqueness" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                          Enforce database uniqueness constraint
                        </Label>
                      </div>
                    </div>

                    <Separator />

                    {/* Index Configuration */}
                    <div className="space-y-3">
                      <Label className="text-base font-medium text-gray-900 dark:text-white">Performance</Label>
                      
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="create-index"
                          checked={storageConstraints.create_index || false}
                          onCheckedChange={(checked) => updateStorageConstraints('create_index', checked)}
                        />
                        <Label htmlFor="create-index" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                          Create database index for faster queries
                        </Label>
                      </div>

                      {storageConstraints.create_index && (
                        <div className="ml-6 space-y-2">
                          <Label htmlFor="index-type" className="text-sm text-gray-700 dark:text-gray-300">Index Type</Label>
                          <Select
                            value={storageConstraints.index_type || 'btree'}
                            onValueChange={(value) => updateStorageConstraints('index_type', value)}
                          >
                            <SelectTrigger className="w-full">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="btree">B-Tree (General Purpose)</SelectItem>
                              <SelectItem value="gin">GIN (Full-text Search)</SelectItem>
                              <SelectItem value="gist">GiST (Geometric Data)</SelectItem>
                              <SelectItem value="hash">Hash (Equality Only)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        )}

        {/* Field Configuration Summary */}
        {hasFieldConfig(fieldType) && configErrors.length === 0 && (
          <Card className="bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800">
            <CardContent className="pt-6">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-sm font-medium text-green-800 dark:text-green-200">
                  Configuration Complete
                </span>
              </div>
              <p className="text-xs text-green-700 dark:text-green-300 mt-1">
                This {fieldTypeConfig.label.toLowerCase()} field is properly configured and ready to use.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </TooltipProvider>
  )
}