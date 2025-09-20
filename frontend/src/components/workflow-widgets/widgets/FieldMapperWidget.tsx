'use client';

import React, { useState, useMemo, useEffect } from 'react';
import { Plus, X, ArrowRight, Variable } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { BaseWidgetProps } from '../core/types';
import { cn } from '@/lib/utils';
import { FieldRenderer } from '@/lib/field-system/field-renderer';
import { Field } from '@/lib/field-system/types';
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
  mappingMode: string;
  targetPipelineId?: string;
  onUpdate: (index: number, updates: Partial<FieldMapping>) => void;
  onRemove: (index: number) => void;
  getFieldType: (fieldName: string) => string;
  getTargetFieldAsFieldType: (fieldName: string) => Field | null;
}> = ({
  mapping,
  index,
  targetFields,
  availableVariables,
  mappingMode,
  targetPipelineId,
  onUpdate,
  onRemove,
  getFieldType,
  getTargetFieldAsFieldType
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
            <SelectContent>
              {targetFields.map((field: any) => (
                <SelectItem
                  key={field.id || field.name}
                  value={field.name}
                >
                  <div className="flex items-center gap-2">
                    <span>{field.display_name || field.name}</span>
                    {field.is_required && (
                      <span className="text-xs text-destructive">*</span>
                    )}
                    <span className="text-xs text-muted-foreground">
                      ({field.field_type})
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Source Value */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <Label className="text-xs font-medium text-muted-foreground">
              Source Value
            </Label>
            {mappingMode === 'advanced' && (
              <Select
                value={mapping.sourceType}
                onValueChange={(val) => onUpdate(index, {
                  sourceType: val as 'value' | 'variable' | 'template'
                })}
              >
                <SelectTrigger className="h-6 w-20 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="value">Value</SelectItem>
                  <SelectItem value="variable">Variable</SelectItem>
                  <SelectItem value="template">Template</SelectItem>
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Conditionally render input based on sourceType */}
          {mapping.sourceType === 'variable' && availableVariables.length > 0 ? (
            <Select
              value={mapping.sourceValue}
              onValueChange={(val) => onUpdate(index, { sourceValue: val })}
            >
              <SelectTrigger className="h-9 w-full">
                <SelectValue placeholder="Select variable" />
              </SelectTrigger>
              <SelectContent>
                {availableVariables.map((variable) => (
                  <SelectItem key={variable.value} value={variable.value}>
                    <div>
                      <div>{variable.label}</div>
                      {variable.description && (
                        <div className="text-xs text-muted-foreground">
                          {variable.description}
                        </div>
                      )}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : mapping.sourceType === 'value' && targetFieldDef ? (
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
            <Input
              value={mapping.sourceValue}
              onChange={(e) => onUpdate(index, { sourceValue: e.target.value })}
              placeholder={
                mapping.sourceType === 'template'
                  ? '{{variable}} or text'
                  : mapping.targetField
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
  availableVariables?: Array<{ label: string; value: string; description?: string }>;
  config?: any;
  uiHints?: {
    target_pipeline_key?: string;
    mapping_mode?: 'simple' | 'advanced';
    show_required_only?: boolean;
    [key: string]: any;
  };
}

export function FieldMapperWidget({
  value = {},
  onChange,
  pipelines = [],
  pipelineFields,
  availableVariables = [],
  config,
  uiHints = {}
}: FieldMapperWidgetProps) {
  // Get target pipeline from config
  const targetPipelineKey = uiHints.target_pipeline_key || 'pipeline_id';
  const targetPipelineId = config?.[targetPipelineKey];
  const mappingMode = uiHints.mapping_mode || 'simple';
  const showRequiredOnly = uiHints.show_required_only || false;

  // Convert value to mappings array format for internal use
  const [mappings, setMappings] = useState<FieldMapping[]>(() => {
    if (Array.isArray(value)) {
      return value;
    }
    // Convert object format to array format
    return Object.entries(value).map(([field, val]) => ({
      targetField: field,
      sourceType: typeof val === 'string' && val.includes('{{') ? 'template' : 'value',
      sourceValue: String(val)
    }));
  });

  // Get fields for the target pipeline
  const targetFields = useMemo(() => {
    if (!targetPipelineId || !pipelineFields) return [];

    let fields = [];
    if (Array.isArray(pipelineFields)) {
      fields = pipelineFields;
    } else if (pipelineFields[targetPipelineId]) {
      fields = pipelineFields[targetPipelineId];
    }

    // Filter to required fields if needed
    if (showRequiredOnly) {
      fields = fields.filter((f: any) => f.is_required);
    }

    return fields;
  }, [targetPipelineId, pipelineFields, showRequiredOnly]);

  // Update parent when mappings change
  useEffect(() => {
    // Convert back to object format for simple mode
    if (mappingMode === 'simple') {
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
    } else {
      // Only call onChange if the value actually changed
      const currentValue = JSON.stringify(value);
      const newValue = JSON.stringify(mappings);
      if (currentValue !== newValue) {
        onChange(mappings);
      }
    }
  }, [mappings, mappingMode, value, onChange]);

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
    const field = targetFields.find((f: any) => f.name === fieldName || f.slug === fieldName);
    return field?.field_type || 'text';
  };

  const getFieldLabel = (fieldName: string) => {
    const field = targetFields.find((f: any) => f.name === fieldName || f.slug === fieldName);
    return field?.display_name || field?.name || fieldName;
  };

  // Convert pipeline field to Field type for FieldRenderer
  const getTargetFieldAsFieldType = (fieldName: string): Field | null => {
    const field = targetFields.find((f: any) => f.name === fieldName || f.slug === fieldName);
    if (!field) return null;

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
      display_name: field.display_name,
      field_type: field.field_type,
      field_config: fieldConfig,
      config: fieldConfig, // Include as both for compatibility
      help_text: field.help_text,
      placeholder: field.placeholder,
      is_readonly: field.is_readonly || false,
      is_required: field.is_required || false,
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
              mappingMode={mappingMode}
              targetPipelineId={targetPipelineId}
              onUpdate={updateMapping}
              onRemove={removeMapping}
              getFieldType={getFieldType}
              getTargetFieldAsFieldType={getTargetFieldAsFieldType}
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