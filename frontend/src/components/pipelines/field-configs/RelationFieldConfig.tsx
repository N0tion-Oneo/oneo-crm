'use client'

import React, { useState, useEffect } from 'react'
import { usePipelines, useRelationshipTypes, usePipelineFields } from '@/contexts/FieldConfigCacheContext'
import {
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
  Checkbox,
  Input,
  Separator,
  Badge
} from '@/components/ui'
import { HelpCircle, AlertCircle, Info } from 'lucide-react'

interface Pipeline {
  id: string
  name: string
  slug: string
}

interface PipelineField {
  id: string
  name: string
  slug: string
  display_name: string
  field_type: string
}

interface RelationshipType {
  id: number
  name: string
  slug: string
  description: string
  cardinality: 'one_to_one' | 'one_to_many' | 'many_to_many' | 'many_to_one' | 'one_to_one_bidirectional' | 'one_to_many_bidirectional' | 'many_to_many_bidirectional'
  is_bidirectional: boolean
  forward_label: string
  reverse_label: string
}

interface RelationFieldConfigProps {
  config: Record<string, any>
  onChange: (config: Record<string, any>) => void
}

export const RelationFieldConfig = React.memo(function RelationFieldConfig({
  config,
  onChange
}: RelationFieldConfigProps) {
  // Use cached data from context with error handling
  const { pipelines, loading: pipelinesLoading, error: pipelinesError } = usePipelines()
  const { relationshipTypes, loading: relationshipTypesLoading, error: relationshipTypesError } = useRelationshipTypes()
  const { fields: targetPipelineFields, loading: loadingFields, error: fieldsError } = usePipelineFields(
    config.target_pipeline_id?.toString() || ''
  )

  // Debug logging for component state
  React.useEffect(() => {
    console.log('[RelationFieldConfig] Component state:', {
      config,
      pipelinesCount: pipelines?.length || 0,
      pipelinesLoading,
      pipelinesError,
      relationshipTypesCount: relationshipTypes?.length || 0,
      relationshipTypesLoading,
      relationshipTypesError,
      targetFieldsCount: targetPipelineFields?.length || 0,
      loadingFields,
      fieldsError
    })
  }, [config, pipelines, pipelinesLoading, pipelinesError, relationshipTypes, relationshipTypesLoading, relationshipTypesError, targetPipelineFields, loadingFields, fieldsError])


  const handlePipelineChange = (value: string) => {
    try {
      console.log('[RelationFieldConfig] handlePipelineChange called with:', value)
      // Ensure value is always a string for consistent comparison
      const newPipelineIdStr = value ? value.toString() : null
      const currentPipelineIdStr = config.target_pipeline_id?.toString() || null
      
      // Clear display field when pipeline changes and update both at once
      // Convert to integer for backend compatibility
      const pipelineIdForBackend = newPipelineIdStr ? parseInt(newPipelineIdStr) : null
      if (newPipelineIdStr !== currentPipelineIdStr) {
        const newConfig = { 
          ...config, 
          target_pipeline_id: pipelineIdForBackend, 
          display_field: '' 
        }
        console.log('[RelationFieldConfig] Pipeline changed, updating config:', newConfig)
        onChange(newConfig)
      }
    } catch (error) {
      console.error('[RelationFieldConfig] Error in handlePipelineChange:', error)
    }
  }

  const handleDisplayFieldChange = (value: string) => {
    try {
      console.log('[RelationFieldConfig] handleDisplayFieldChange called with:', value)
      const newConfig = { ...config, display_field: value }
      console.log('[RelationFieldConfig] Display field changed, updating config:', newConfig)
      onChange(newConfig)
    } catch (error) {
      console.error('[RelationFieldConfig] Error in handleDisplayFieldChange:', error)
    }
  }

  return (
    <TooltipProvider>
      <div className="space-y-6">
        {/* Target Pipeline Selection */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Label htmlFor="target-pipeline" className="text-sm font-medium text-gray-900 dark:text-white">
              Target Pipeline *
            </Label>
            <Tooltip>
              <TooltipTrigger asChild>
                <HelpCircle className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent>
                <p className="max-w-xs">Select which pipeline this relation field should reference. Records from the selected pipeline will be available for selection.</p>
              </TooltipContent>
            </Tooltip>
          </div>
          
          {pipelinesLoading ? (
            <div className="p-3 text-sm border rounded-md bg-muted text-gray-700 dark:text-gray-300">
              Loading available pipelines...
            </div>
          ) : (
            <Select
              value={config.target_pipeline_id?.toString() || ''}
              onValueChange={handlePipelineChange}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select pipeline..." />
              </SelectTrigger>
              <SelectContent>
                {pipelines.length === 0 ? (
                  <SelectItem value="none" disabled>
                    No pipelines available
                  </SelectItem>
                ) : (
                  pipelines.map((pipeline) => (
                    <SelectItem key={pipeline.id} value={pipeline.id.toString()}>
                      {pipeline.name}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          )}
          
          {!pipelinesLoading && pipelines.length === 0 && (
            <div className="flex items-center gap-2 p-3 text-sm bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md">
              <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
              <span className="text-yellow-800 dark:text-yellow-200">
                No other pipelines available. Create additional pipelines to enable relationships.
              </span>
            </div>
          )}
        </div>

        {/* Display Field Selection */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Label htmlFor="display-field" className="text-sm font-medium text-gray-900 dark:text-white">
              Display Field
            </Label>
            <Tooltip>
              <TooltipTrigger asChild>
                <HelpCircle className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent>
                <p className="max-w-xs">Choose which field from the target pipeline should be shown when displaying related records. This is typically a name or title field.</p>
              </TooltipContent>
            </Tooltip>
            {Array.isArray(targetPipelineFields) && targetPipelineFields.length > 0 && (
              <span className="text-xs text-muted-foreground">
                ({targetPipelineFields.length} fields available)
              </span>
            )}
          </div>

          {!config.target_pipeline_id ? (
            <Select disabled>
              <SelectTrigger>
                <SelectValue placeholder="Select target pipeline first..." />
              </SelectTrigger>
            </Select>
          ) : loadingFields ? (
            <div className="p-3 text-sm border rounded-md bg-muted text-gray-700 dark:text-gray-300">
              Loading pipeline fields...
            </div>
          ) : (
            <Select
              value={config.display_field || ''}
              onValueChange={handleDisplayFieldChange}
              disabled={!Array.isArray(targetPipelineFields) || targetPipelineFields.length === 0}
            >
              <SelectTrigger>
                <SelectValue placeholder={
                  !Array.isArray(targetPipelineFields) || targetPipelineFields.length === 0 
                    ? "No fields available" 
                    : "Select field to display..."
                } />
              </SelectTrigger>
              <SelectContent>
                {Array.isArray(targetPipelineFields) && targetPipelineFields.length > 0 ? (
                  targetPipelineFields.map((field) => (
                    <SelectItem key={field.id} value={field.slug}>
                      {field.display_name || field.name} ({field.field_type})
                    </SelectItem>
                  ))
                ) : (
                  <SelectItem value="none" disabled>
                    No fields available
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
          )}

          <p className="text-xs text-muted-foreground">
            Which field from the target pipeline should be displayed in this relation field
          </p>

          {config.target_pipeline_id && !loadingFields && (!Array.isArray(targetPipelineFields) || targetPipelineFields.length === 0) && (
            <div className="flex items-center gap-2 p-3 text-sm bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md">
              <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
              <span className="text-yellow-800 dark:text-yellow-200">
                The selected pipeline has no fields yet. Add fields to the target pipeline to configure display options.
              </span>
            </div>
          )}
        </div>

        {/* Enhanced Configuration Options */}
        <Separator />

        {/* Multiple Relationships Section */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Label className="text-base font-medium text-gray-900 dark:text-white">
              Multiple Relationships
            </Label>
            <Tooltip>
              <TooltipTrigger asChild>
                <HelpCircle className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent>
                <p className="max-w-xs">Allow this field to store multiple relationships to different records instead of just one.</p>
              </TooltipContent>
            </Tooltip>
          </div>
          
          <div className="flex items-center space-x-2">
            <Checkbox
              id="allow-multiple"
              checked={config.allow_multiple || false}
              onCheckedChange={(checked) => {
                try {
                  console.log('[RelationFieldConfig] allow_multiple checkbox changed:', checked)
                  const newConfig = {...config, allow_multiple: checked}
                  console.log('[RelationFieldConfig] Updating config with allow_multiple:', newConfig)
                  onChange(newConfig)
                } catch (error) {
                  console.error('[RelationFieldConfig] Error in allow_multiple checkbox:', error)
                }
              }}
            />
            <Label htmlFor="allow-multiple" className="text-sm font-normal text-gray-700 dark:text-gray-300">
              Allow Multiple Relationships
            </Label>
          </div>

          {config.allow_multiple && (
            <div className="space-y-2 ml-6">
              <Label htmlFor="max-relationships" className="text-sm text-gray-700 dark:text-gray-300">
                Maximum Relationships (optional)
              </Label>
              <Input
                id="max-relationships"
                type="number"
                min="1"
                placeholder="No limit"
                value={config.max_relationships || ''}
                onChange={(e) => {
                  try {
                    console.log('[RelationFieldConfig] max_relationships input changed:', e.target.value)
                    const newConfig = {
                      ...config, 
                      max_relationships: e.target.value ? parseInt(e.target.value) : null
                    }
                    console.log('[RelationFieldConfig] Updating config with max_relationships:', newConfig)
                    onChange(newConfig)
                  } catch (error) {
                    console.error('[RelationFieldConfig] Error in max_relationships input:', error)
                  }
                }}
                className="w-32"
              />
              <p className="text-xs text-muted-foreground">
                Leave empty for unlimited relationships
              </p>
            </div>
          )}
        </div>

        <Separator />

        {/* Relationship Type Section */}
        <div className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Label className="text-base font-medium text-gray-900 dark:text-white">
                Relationship Type
              </Label>
              <Tooltip>
                <TooltipTrigger asChild>
                  <HelpCircle className="h-4 w-4 text-muted-foreground" />
                </TooltipTrigger>
                <TooltipContent>
                  <p className="max-w-xs">Configure what type of relationship this field represents (e.g., "works at", "applied to", "related to").</p>
                </TooltipContent>
              </Tooltip>
            </div>

            <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-md">
              <div className="text-sm text-gray-700 dark:text-gray-300">
                <p className="font-medium mb-2">How Relationship Types Work:</p>
                <ul className="space-y-1 text-xs">
                  <li>• <strong>Works At</strong>: Employee → Company (many employees work at one company)</li>
                  <li>• <strong>Applied To</strong>: Candidate → Job (candidates can apply to multiple jobs)</li>
                  <li>• <strong>Related To</strong>: Any → Any (generic relationships between records)</li>
                  <li>• <strong>Parent Of</strong>: Company → Subsidiary (hierarchical relationships)</li>
                </ul>
                <p className="text-xs text-muted-foreground mt-2">
                  <strong>Bidirectional (↔)</strong>: Creates reverse relationships automatically<br/>
                  <strong>Cardinality</strong>: Controls how many relationships are allowed
                </p>
              </div>
            </div>
          </div>

          {/* Default Relationship Type Selection - ALWAYS shown to admins */}
          <div className="space-y-3">
            <div className="space-y-2">
              <Label className="text-sm text-gray-700 dark:text-gray-300">
                Default Relationship Type *
              </Label>
              {relationshipTypesLoading ? (
                <div className="p-3 text-sm border rounded-md bg-muted text-gray-700 dark:text-gray-300">
                  Loading relationship types...
                </div>
              ) : relationshipTypes.length === 0 ? (
                <div className="space-y-3">
                  <div className="p-3 text-sm border border-yellow-200 dark:border-yellow-800 rounded-md bg-yellow-50 dark:bg-yellow-900/20">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
                      <span className="text-yellow-800 dark:text-yellow-200">
                        No relationship types found. Using default "related_to" type.
                      </span>
                    </div>
                  </div>
                  <Select disabled>
                    <SelectTrigger>
                      <SelectValue placeholder="related_to (default)" />
                    </SelectTrigger>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Check browser console for API errors, or contact admin to setup relationship types.
                  </p>
                </div>
              ) : (
                <Select
                  value={config.default_relationship_type || 'related_to'}
                  onValueChange={(value) => onChange({...config, default_relationship_type: value})}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select relationship type..." />
                  </SelectTrigger>
                  <SelectContent>
                    {Array.isArray(relationshipTypes) && relationshipTypes.length > 0 ? relationshipTypes.map((type) => (
                      <SelectItem key={type.slug} value={type.slug}>
                        <div className="flex items-center gap-2">
                          <span>{type.name}</span>
                          <Badge variant="outline" className="text-xs">
                            {type.cardinality.replace('_', '-')}
                          </Badge>
                          {type.is_bidirectional && (
                            <Badge variant="secondary" className="text-xs">↔</Badge>
                          )}
                        </div>
                      </SelectItem>
                    )) : (
                      <SelectItem value="related_to" key="default">
                        Related To (default)
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              )}
              <p className="text-xs text-muted-foreground">
                This relationship type will be used for all records in this field
              </p>
            </div>

            {config.default_relationship_type && Array.isArray(relationshipTypes) && relationshipTypes.length > 0 && (
              <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-md">
                {(() => {
                  const selectedType = relationshipTypes.find(t => t.slug === config.default_relationship_type)
                  if (!selectedType) return null
                  return (
                    <div className="text-sm text-gray-700 dark:text-gray-300">
                      <p className="font-medium">{selectedType.name}</p>
                      <p className="text-xs mt-1">{selectedType.description}</p>
                      <div className="flex gap-2 mt-2">
                        <Badge variant="outline">{selectedType.cardinality.replace('_', '-')}</Badge>
                        {selectedType.is_bidirectional && (
                          <>
                            <Badge variant="secondary">Bidirectional</Badge>
                            <span className="text-xs text-muted-foreground">
                              "{selectedType.forward_label}" ↔ "{selectedType.reverse_label}"
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  )
                })()}
              </div>
            )}
          </div>

          {/* User Override Toggle */}
          <div className="flex items-center space-x-2">
            <Checkbox
              id="allow-relationship-type-selection"
              checked={config.allow_relationship_type_selection || false}
              onCheckedChange={(checked) => onChange({...config, allow_relationship_type_selection: checked})}
            />
            <Label htmlFor="allow-relationship-type-selection" className="text-sm font-normal text-gray-700 dark:text-gray-300">
              Allow users to change relationship type when creating records
            </Label>
          </div>
          <p className="text-xs text-muted-foreground ml-6">
            When enabled, users can select a different relationship type for each record. When disabled, all records use the default type above.
          </p>

          {config.allow_relationship_type_selection && (
            <div className="space-y-3 ml-6">
              <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
                <div className="text-sm text-blue-700 dark:text-blue-300">
                  <p className="font-medium text-blue-800 dark:text-blue-200 mb-1">User Override Enabled</p>
                  <p>Users will be able to select from all available relationship types when creating records, using "{config.default_relationship_type || 'related_to'}" as the default.</p>
                </div>
              </div>
            </div>
          )}
        </div>

        <Separator />

        {/* Advanced Options Section */}
        <div className="space-y-4">
          <Label className="text-base font-medium text-gray-900 dark:text-white">
            Advanced Options
          </Label>

          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="create-reverse-relationships"
                checked={config.create_reverse_relationships !== false}
                onCheckedChange={(checked) => onChange({...config, create_reverse_relationships: checked})}
              />
              <Label htmlFor="create-reverse-relationships" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Create Reverse Relationships
              </Label>
            </div>

            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="allow-self-reference"
                  checked={config.allow_self_reference || false}
                  onCheckedChange={(checked) => onChange({...config, allow_self_reference: checked})}
                />
                <div className="flex items-center gap-2">
                  <Label htmlFor="allow-self-reference" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Allow Self-Reference
                  </Label>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <HelpCircle className="h-4 w-4 text-muted-foreground" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="max-w-xs">Allow records in the same pipeline to relate to other records in the same pipeline (e.g., Employee → Manager, Company → Parent Company).</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
              </div>
              <p className="text-xs text-muted-foreground ml-6">
                Examples: Employee → Manager, Project → Related Project, Person → Family Member
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="enforce-cardinality"
                checked={config.enforce_cardinality !== false}
                onCheckedChange={(checked) => onChange({...config, enforce_cardinality: checked})}
              />
              <Label htmlFor="enforce-cardinality" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Enforce Relationship Cardinality
              </Label>
            </div>
          </div>
        </div>

        {/* Relationship Configuration Summary */}
        {config.target_pipeline_id && config.display_field && (
          <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
            <div className="flex items-start gap-2">
              <Info className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-gray-700 dark:text-gray-300">
                <p className="font-medium text-blue-800 dark:text-blue-200">Relationship Configuration Summary</p>
                <div className="text-blue-700 dark:text-blue-300 mt-1 space-y-1">
                  <div>• Target: "{pipelines.find(p => p.id === config.target_pipeline_id?.toString())?.name}" pipeline</div>
                  <div>• Display: "{config.display_field}" field</div>
                  <div>• Type: {config.default_relationship_type || 'related_to'} {config.allow_relationship_type_selection ? '(user can override)' : '(fixed)'}</div>
                  <div>• Multiple: {config.allow_multiple ? `Yes (max: ${config.max_relationships || 'unlimited'})` : 'No'}</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </TooltipProvider>
  )
})