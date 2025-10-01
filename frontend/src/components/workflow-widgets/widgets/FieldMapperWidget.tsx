'use client';

import React, { useState, useMemo, useEffect } from 'react';
import { Plus, X, ArrowRight, Variable, ChevronRight, ChevronDown, Link2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { BaseWidgetProps } from '../core/types';
import { cn } from '@/lib/utils';
import { FieldRenderer } from '@/lib/field-system/field-renderer';
import { Field } from '@/lib/field-system/types';
import { expandTargetFields, type ExpandedTargetField } from '@/app/(dashboard)/workflows/utils/relationPathExpander';
// Ensure field system is initialized
import '@/lib/field-system';

interface FieldMapping {
  targetField: string;
  sourceType: 'value' | 'variable' | 'template';
  sourceValue: string;
}

// Component for rendering a single field mapping row
// This isolates all the conditional rendering and field-specific components
const FieldMappingRow: React.FC<{
  mapping: FieldMapping;
  index: number;
  targetFields: any[];
  availableVariables: Array<{ label: string; value: string; description?: string }>;
  targetPipelineId?: string;
  onUpdate: (index: number, updates: Partial<FieldMapping>) => void;
  onRemove: (index: number) => void;
  getFieldType: (fieldName: string) => string;
  getTargetFieldAsFieldType: (fieldName: string) => Field | null;
  groupedFields: { directFields: ExpandedTargetField[]; relationFieldsMap: Record<string, ExpandedTargetField[]> };
  expandedRelations: Set<string>;
  toggleRelationExpansion: (fieldValue: string) => void;
}> = ({
  mapping,
  index,
  targetFields,
  availableVariables,
  targetPipelineId,
  onUpdate,
  onRemove,
  getFieldType,
  getTargetFieldAsFieldType,
  groupedFields,
  expandedRelations,
  toggleRelationExpansion
}) => {
  // Get the target field definition once
  const targetFieldDef = mapping.targetField ? getTargetFieldAsFieldType(mapping.targetField) : null;

  return (
    <div className="border rounded-lg bg-muted/30">
      <div className="p-3 space-y-3">
        {/* Target Field Selection */}
        <div className="space-y-1.5">
          <Label className="text-xs font-medium text-muted-foreground">Target Field</Label>
          <Select
            value={mapping.targetField}
            onValueChange={(val) => onUpdate(index, { targetField: val })}
          >
            <SelectTrigger className="h-9 w-full">
              <SelectValue placeholder="Select target field" />
            </SelectTrigger>
            <SelectContent className="max-h-[400px]">
              {groupedFields.directFields.map((field: any, idx: number) => {
                const isSystemField = field.id && String(field.id).startsWith('system_');
                const isRelationField = field.field_type === 'relation';
                const fieldValue = field.value || field.slug || field.name;
                const hasNestedFields = groupedFields.relationFieldsMap[fieldValue]?.length > 0;
                const isExpanded = expandedRelations.has(fieldValue);

                return (
                  <React.Fragment key={`${fieldValue}-${idx}`}>
                    <SelectItem value={fieldValue}>
                      <div className="flex items-center gap-2">
                        <span className="truncate">{field.label || field.display_name || field.name}</span>
                        {isSystemField && (
                          <span className="text-xs text-muted-foreground flex-shrink-0">[System]</span>
                        )}
                        {field.is_required && (
                          <span className="text-xs text-destructive flex-shrink-0">*</span>
                        )}
                        <span className="text-xs text-muted-foreground flex-shrink-0">
                          ({field.field_type})
                        </span>
                      </div>
                    </SelectItem>

                    {/* Show expand/collapse toggle for relation fields with nested fields */}
                    {isRelationField && hasNestedFields && (
                      <div
                        className="flex items-center gap-2 px-2 py-1.5 text-sm cursor-pointer hover:bg-accent/50 border-b"
                        onClick={() => toggleRelationExpansion(fieldValue)}
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-3 w-3 flex-shrink-0" />
                        ) : (
                          <ChevronRight className="h-3 w-3 flex-shrink-0" />
                        )}
                        <span className="text-xs text-muted-foreground">
                          {isExpanded ? 'Hide' : 'Show'} {field.label || field.display_name || field.name} related fields
                        </span>
                      </div>
                    )}

                    {/* Show nested fields if expanded */}
                    {isRelationField && isExpanded && hasNestedFields && (
                      <>
                        {groupedFields.relationFieldsMap[fieldValue].map((nestedField: any, nestedIdx: number) => {
                          // Check if this nested field is also a relation with its own nested fields
                          const nestedFieldValue = nestedField.value;
                          const nestedIsRelation = nestedField.field_type === 'relation';
                          const nestedHasNestedFields = groupedFields.relationFieldsMap[nestedFieldValue]?.length > 0;
                          const nestedIsExpanded = expandedRelations.has(nestedFieldValue);

                          return (
                            <React.Fragment key={`${nestedField.value}-${nestedIdx}`}>
                              <SelectItem
                                value={nestedField.value}
                                className="pl-8"
                              >
                                <div className="flex items-center">
                                  <Link2 className="h-3 w-3 mr-2 text-blue-500" />
                                  <span className="text-sm">{nestedField.label}</span>
                                  {nestedField.is_required && (
                                    <span className="text-xs text-destructive ml-1">*</span>
                                  )}
                                  <span className="text-xs text-muted-foreground ml-2">
                                    ({nestedField.field_type})
                                  </span>
                                </div>
                              </SelectItem>

                              {/* Show expand/collapse toggle for nested relation fields */}
                              {nestedIsRelation && nestedHasNestedFields && (
                                <div
                                  className="flex items-center gap-2 px-2 py-1.5 pl-10 text-sm cursor-pointer hover:bg-accent/50"
                                  onClick={() => toggleRelationExpansion(nestedFieldValue)}
                                >
                                  {nestedIsExpanded ? (
                                    <ChevronDown className="h-3 w-3 flex-shrink-0" />
                                  ) : (
                                    <ChevronRight className="h-3 w-3 flex-shrink-0" />
                                  )}
                                  <span className="text-xs text-muted-foreground">
                                    {nestedIsExpanded ? 'Hide' : 'Show'} {nestedField.label} related fields
                                  </span>
                                </div>
                              )}

                              {/* Show multi-hop nested fields if expanded */}
                              {nestedIsRelation && nestedIsExpanded && nestedHasNestedFields && (
                                <>
                                  {groupedFields.relationFieldsMap[nestedFieldValue].map((deepField: any, deepIdx: number) => (
                                    <SelectItem
                                      key={`${deepField.value}-${deepIdx}`}
                                      value={deepField.value}
                                      className="pl-16"
                                    >
                                      <div className="flex items-center">
                                        <Link2 className="h-3 w-3 mr-2 text-purple-500" />
                                        <span className="text-sm">{deepField.label}</span>
                                        {deepField.is_required && (
                                          <span className="text-xs text-destructive ml-1">*</span>
                                        )}
                                        <span className="text-xs text-muted-foreground ml-2">
                                          ({deepField.field_type})
                                        </span>
                                      </div>
                                    </SelectItem>
                                  ))}
                                </>
                              )}
                            </React.Fragment>
                          );
                        })}
                      </>
                    )}
                  </React.Fragment>
                );
              })}
            </SelectContent>
          </Select>
        </div>

        {/* Source Value */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <Label className="text-xs font-medium text-muted-foreground">
              Source Value
            </Label>
            <div className="flex items-center gap-1">
              {/* Variable insertion button - available for all types */}
              {availableVariables.length > 0 && (
                <Select
                  value=""
                  onValueChange={(val) => {
                    if (!val) return;
                    // Insert variable at cursor position or append
                    const currentValue = String(mapping.sourceValue || '');
                    const variable = `{${val}}`;
                    const newValue = mapping.sourceType === 'template' || currentValue.includes('{')
                      ? `${currentValue}${currentValue ? ' ' : ''}${variable}`
                      : variable;
                    onUpdate(index, {
                      sourceValue: newValue,
                      sourceType: newValue.includes('{') ? 'template' : mapping.sourceType
                    });
                  }}
                >
                  <SelectTrigger className="h-6 w-6 p-0" title="Insert variable">
                    <Variable className="h-3 w-3" />
                  </SelectTrigger>
                  <SelectContent>
                    <div className="px-2 py-1.5 text-sm font-semibold text-muted-foreground">
                      Insert Variable
                    </div>
                    {availableVariables.map((variable) => (
                      <SelectItem key={variable.value} value={variable.value}>
                        {variable.description ? (
                          <>
                            <div>{variable.label}</div>
                            <div className="text-xs text-muted-foreground">
                              {variable.description}
                            </div>
                          </>
                        ) : (
                          variable.label
                        )}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
          </div>

          {/* Render appropriate input based on sourceType */}
          {mapping.sourceType === 'variable' && availableVariables.length > 0 ? (
            <Select
              value={String(mapping.sourceValue || '').replace(/[{}]/g, '')}
              onValueChange={(val) => onUpdate(index, { sourceValue: `{${val}}` })}
            >
              <SelectTrigger className="h-9 w-full">
                <SelectValue placeholder="Select variable" />
              </SelectTrigger>
              <SelectContent>
                {availableVariables.map((variable) => (
                  <SelectItem key={variable.value} value={variable.value}>
                    {variable.description ? (
                      <>
                        <div>{variable.label}</div>
                        <div className="text-xs text-muted-foreground">
                          {variable.description}
                        </div>
                      </>
                    ) : (
                      variable.label
                    )}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : mapping.sourceType === 'template' || (mapping.sourceValue && String(mapping.sourceValue).includes('{')) ? (
            // Template mode - always use Input for mixed content
            <Input
              value={mapping.sourceValue}
              onChange={(e) => onUpdate(index, { sourceValue: e.target.value })}
              placeholder="Enter text and {variables}"
              className="h-9 w-full font-mono text-sm"
            />
          ) : mapping.sourceType === 'value' && targetFieldDef ? (
            // Value mode - use field-specific component
            <FieldRenderer
              field={targetFieldDef}
              value={mapping.sourceValue}
              onChange={(val) => onUpdate(index, { sourceValue: val })}
              context="form"
              pipeline_id={targetPipelineId ? parseInt(targetPipelineId, 10) : undefined}
              disabled={false}
              autoFocus={false}
            />
          ) : (
            // Fallback to basic Input
            <Input
              value={mapping.sourceValue}
              onChange={(e) => onUpdate(index, { sourceValue: e.target.value })}
              placeholder={
                mapping.targetField
                  ? `Enter ${getFieldType(mapping.targetField)} value`
                  : 'Enter value'
              }
              className="h-9 w-full"
            />
          )}
        </div>

        {/* Show field type hint */}
        {mapping.targetField && (
          <div className="text-xs text-muted-foreground">
            Field type: {getFieldType(mapping.targetField)}
          </div>
        )}
      </div>

      {/* Delete button in footer area */}
      <div className="px-3 pb-3 flex justify-end">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => onRemove(index)}
          className="h-7 text-xs text-destructive hover:text-destructive/90"
        >
          <X className="h-3 w-3 mr-1" />
          Remove
        </Button>
      </div>
    </div>
  );
};

interface FieldMapperWidgetProps extends BaseWidgetProps {
  value: Record<string, any> | FieldMapping[];
  onChange: (value: Record<string, any> | FieldMapping[]) => void;
  pipelines?: any[];
  pipelineFields?: any;
  allPipelineFields?: Record<string, any[]>; // Full map of all loaded pipeline fields
  fetchPipelineFields?: (pipelineId: string) => Promise<void>; // Function to fetch fields for a pipeline
  availableVariables?: Array<{ label: string; value: string; description?: string }>;
  config?: any;
  uiHints?: {
    target_pipeline_key?: string;
    show_required_only?: boolean;
    [key: string]: any;
  };
}

export function FieldMapperWidget({
  value = {},
  onChange,
  pipelines = [],
  pipelineFields,
  allPipelineFields,
  fetchPipelineFields,
  availableVariables = [],
  config,
  uiHints = {}
}: FieldMapperWidgetProps) {
  console.log('🔍 [FieldMapperWidget] Props:', {
    pipelines: pipelines?.length,
    pipelineFields,
    config,
    uiHints
  });

  // Get target pipeline from config
  const targetPipelineKey = uiHints.target_pipeline_key || 'pipeline_id';
  const targetPipelineId = config?.[targetPipelineKey];
  const showRequiredOnly = uiHints.show_required_only || false;

  console.log('🔍 [FieldMapperWidget] Target pipeline:', {
    targetPipelineKey,
    targetPipelineId
  });

  // Auto-fetch fields for related pipelines when target pipeline fields are loaded
  useEffect(() => {
    if (!targetPipelineId || !fetchPipelineFields || !allPipelineFields) return;

    // Get the target pipeline fields
    const fields = Array.isArray(pipelineFields)
      ? pipelineFields
      : (allPipelineFields[targetPipelineId] || []);

    // Find all relation fields
    const relationFields = fields.filter((f: any) => f.field_type === 'relation');

    console.log('🔍 [FieldMapperWidget] Auto-fetching related pipelines:', {
      targetPipelineId,
      relationFieldsCount: relationFields.length,
      relationFields: relationFields.map((f: any) => ({
        name: f.name,
        targetPipelineId: f.config?.target_pipeline_id || f.field_config?.target_pipeline_id
      }))
    });

    // Fetch fields for each related pipeline
    relationFields.forEach((field: any) => {
      const fieldConfig = field.config || field.field_config;
      const relatedPipelineId = fieldConfig?.target_pipeline_id;

      if (relatedPipelineId && !allPipelineFields[relatedPipelineId]) {
        console.log('🔍 [FieldMapperWidget] Fetching fields for related pipeline:', relatedPipelineId);
        fetchPipelineFields(String(relatedPipelineId));
      }
    });
  }, [targetPipelineId, pipelineFields, allPipelineFields, fetchPipelineFields]);

  // Track which relation fields are expanded in the dropdown
  const [expandedRelations, setExpandedRelations] = useState<Set<string>>(new Set());

  const toggleRelationExpansion = (fieldValue: string) => {
    setExpandedRelations(prev => {
      const next = new Set(prev);
      if (next.has(fieldValue)) {
        next.delete(fieldValue);
      } else {
        next.add(fieldValue);
      }
      return next;
    });
  };

  // Convert value to mappings array format for internal use
  const [mappings, setMappings] = useState<FieldMapping[]>(() => {
    if (Array.isArray(value)) {
      return value;
    }
    // Convert object format to array format
    return Object.entries(value).map(([field, val]) => ({
      targetField: field,
      sourceType: typeof val === 'string' && val.includes('{') ? 'template' : 'value',
      sourceValue: String(val)
    }));
  });

  // Get fields for the target pipeline with relation field expansion
  const targetFields = useMemo(() => {
    if (!targetPipelineId) return [];

    // Use allPipelineFields if available, otherwise fall back to pipelineFields
    const fieldsMap = allPipelineFields || pipelineFields;

    let fields = [];
    if (Array.isArray(pipelineFields)) {
      fields = pipelineFields;
    } else if (fieldsMap?.[targetPipelineId]) {
      fields = fieldsMap[targetPipelineId];
    }

    console.log('🔍 [FieldMapperWidget] Before expansion:', {
      fieldsCount: fields.length,
      fields: fields.slice(0, 3),
      allPipelineFieldsKeys: allPipelineFields ? Object.keys(allPipelineFields) : 'not provided',
      pipelineFieldsStructure: typeof pipelineFields
    });

    // Expand relation fields to include nested paths
    // Pass allPipelineFields (map of {pipelineId: fields[]}) for looking up related pipeline fields
    const expandedFields = expandTargetFields(fields, fieldsMap, 2);

    console.log('🔍 [FieldMapperWidget] After expansion:', {
      expandedCount: expandedFields.length,
      expanded: expandedFields.slice(0, 10)
    });

    // Filter to required fields if needed
    if (showRequiredOnly) {
      return expandedFields.filter((f: any) => f.is_required);
    }

    return expandedFields;
  }, [targetPipelineId, pipelineFields, allPipelineFields, showRequiredOnly]);

  // Group fields by depth and parent for hierarchical display
  const groupedFields = useMemo(() => {
    const directFields: ExpandedTargetField[] = [];
    const relationFieldsMap: Record<string, ExpandedTargetField[]> = {};

    targetFields.forEach(field => {
      if (field.depth === 0) {
        directFields.push(field);
      } else if (field.parent) {
        if (!relationFieldsMap[field.parent]) {
          relationFieldsMap[field.parent] = [];
        }
        relationFieldsMap[field.parent].push(field);
      }
    });

    return { directFields, relationFieldsMap };
  }, [targetFields]);

  // Update parent when mappings change
  useEffect(() => {
    // Always convert to object format
    const objValue: Record<string, any> = {};
    mappings.forEach(m => {
      if (m.targetField && m.sourceValue) {
        objValue[m.targetField] = m.sourceValue;
      }
    });
    // Only call onChange if the value actually changed
    const currentValue = JSON.stringify(value);
    const newValue = JSON.stringify(objValue);
    if (currentValue !== newValue) {
      onChange(objValue);
    }
  }, [mappings, value, onChange]);

  const addMapping = () => {
    setMappings([...mappings, {
      targetField: '',
      sourceType: 'value',
      sourceValue: ''
    }]);
  };

  const removeMapping = (index: number) => {
    setMappings(mappings.filter((_, i) => i !== index));
  };

  const updateMapping = (index: number, updates: Partial<FieldMapping>) => {
    setMappings(mappings.map((m, i) => i === index ? { ...m, ...updates } : m));
  };

  const getFieldType = (fieldName: string) => {
    // Handle both direct fields and nested paths (e.g., "company.name" or "email")
    const field = targetFields.find((f: any) =>
      f.value === fieldName || f.slug === fieldName || f.name === fieldName
    );
    return field?.field_type || 'text';
  };

  const getFieldLabel = (fieldName: string) => {
    // Handle both direct fields and nested paths
    const field = targetFields.find((f: any) =>
      f.value === fieldName || f.slug === fieldName || f.name === fieldName
    );
    return field?.label || field?.display_name || field?.name || fieldName;
  };

  // Convert pipeline field to Field type for FieldRenderer
  const getTargetFieldAsFieldType = (fieldName: string): Field | null => {
    // Handle both direct fields and nested paths
    const expandedField = targetFields.find((f: any) =>
      f.value === fieldName || f.slug === fieldName || f.name === fieldName
    );
    if (!expandedField) return null;

    // Use originalField for nested fields, otherwise use the field itself
    const field = expandedField.originalField || expandedField;

    // Build complete field_config including options if present
    const fieldConfig: any = {
      ...(field.field_config || field.config || {}),
    };

    // Ensure options are included for select/multiselect fields
    if (field.options) {
      fieldConfig.options = field.options;
    }
    if (field.choices) {
      // Some fields might use 'choices' instead of 'options'
      fieldConfig.options = field.choices;
    }

    return {
      id: field.id || field.name,
      name: field.name || field.slug,
      display_name: expandedField.label || field.display_name,
      field_type: expandedField.field_type || field.field_type,
      field_config: fieldConfig,
      config: fieldConfig, // Include as both for compatibility
      help_text: field.help_text,
      placeholder: field.placeholder,
      is_readonly: field.is_readonly || false,
      is_required: expandedField.is_required || field.is_required || false,
      original_slug: field.slug || field.name,
      business_rules: field.business_rules
    };
  };

  // Render appropriate content based on state
  if (!targetPipelineId) {
    return (
      <div className="text-sm text-muted-foreground p-4 border border-dashed rounded">
        Please select a target pipeline first
      </div>
    );
  }

  if (targetFields.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 border border-dashed rounded">
        No fields available for the selected pipeline
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <Label className="text-sm font-medium">Field Mappings</Label>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={addMapping}
          className="h-7"
        >
          <Plus className="h-3 w-3 mr-1" />
          Add Field
        </Button>
      </div>

      {mappings.length === 0 ? (
        <div className="text-sm text-muted-foreground p-4 border border-dashed rounded text-center">
          No field mappings configured. Click "Add Field" to start mapping.
        </div>
      ) : (
        <div className="space-y-3">
          {mappings.map((mapping, index) => (
            <FieldMappingRow
              key={`mapping-${index}-${mapping.targetField || 'empty'}-${mapping.sourceType}`}
              mapping={mapping}
              index={index}
              targetFields={targetFields}
              availableVariables={availableVariables}
              targetPipelineId={targetPipelineId}
              onUpdate={updateMapping}
              onRemove={removeMapping}
              getFieldType={getFieldType}
              getTargetFieldAsFieldType={getTargetFieldAsFieldType}
              groupedFields={groupedFields}
              expandedRelations={expandedRelations}
              toggleRelationExpansion={toggleRelationExpansion}
            />
          ))}
        </div>
      )}

      {/* Show required fields hint */}
      {showRequiredOnly && (
        <p className="text-xs text-muted-foreground">
          Showing required fields only
        </p>
      )}
    </div>
  );
}

// Widget metadata for registration
FieldMapperWidget.widgetType = 'field_mapper';
FieldMapperWidget.displayName = 'Field Mapper';
FieldMapperWidget.description = 'Map fields between pipelines or set field values';