/**
 * Field selection widget with pipeline dependency
 */

import React, { useMemo } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { X, Loader2, Database } from 'lucide-react';
import { WidgetProps } from '../core/types';
import { BaseWidgetWrapper } from '../basic/BaseWidget';
import { usePipelineFields } from './useEntityData';

export const FieldSelector: React.FC<WidgetProps> = (props) => {
  const { value, onChange, uiHints = {}, config = {} } = props;
  const isMultiple = uiHints.widget === 'field_multiselect' || uiHints.multiple;

  // Determine which pipeline(s) to fetch fields for
  const dependsOn = uiHints.depends_on || 'pipeline_id';
  const pipelineIds = config[dependsOn] || config.pipeline_ids || [];

  // Use fields from props if available, otherwise fetch
  const shouldFetch = !props.pipelineFields || props.pipelineFields.length === 0;
  const { data: fetchedFields, isLoading } = usePipelineFields(
    shouldFetch ? pipelineIds : undefined
  );

  const fields = props.pipelineFields || fetchedFields;

  // Apply field filters if specified
  const filteredFields = useMemo(() => {
    let result = fields;

    // Filter by field type if specified
    if (uiHints.field_types) {
      const allowedTypes = Array.isArray(uiHints.field_types)
        ? uiHints.field_types
        : [uiHints.field_types];
      result = result.filter((f: any) => allowedTypes.includes(f.field_type));
    }

    // Apply custom filter if specified
    if (uiHints.field_filter && typeof uiHints.field_filter === 'function') {
      result = result.filter(uiHints.field_filter);
    }

    return result;
  }, [fields, uiHints]);

  const placeholder = props.placeholder || uiHints.placeholder || 'Select field(s)';

  if (!pipelineIds || (Array.isArray(pipelineIds) && pipelineIds.length === 0)) {
    return (
      <BaseWidgetWrapper {...props}>
        <div className="px-3 py-2 border border-gray-200 rounded-md bg-gray-50 text-gray-500 text-sm">
          Please select a pipeline first
        </div>
      </BaseWidgetWrapper>
    );
  }

  if (isMultiple) {
    return (
      <FieldMultiSelect
        {...props}
        fields={filteredFields}
        isLoading={isLoading}
      />
    );
  }

  return (
    <BaseWidgetWrapper {...props}>
      <Select
        value={value || ''}
        onValueChange={onChange}
        disabled={props.disabled || props.readonly || isLoading}
      >
        <SelectTrigger>
          {isLoading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Loading fields...</span>
            </div>
          ) : (
            <SelectValue placeholder={placeholder} />
          )}
        </SelectTrigger>
        <SelectContent>
          {filteredFields.map((field: any) => {
            const fieldKey = field.slug || field.name || field.key || field.id;
            const fieldName = field.label || field.name || fieldKey;
            const fieldType = field.field_type || field.type;

            return (
              <SelectItem key={fieldKey} value={fieldKey}>
                <div className="flex items-center gap-2">
                  <Database className="w-3 h-3 text-gray-400" />
                  <div className="flex flex-col">
                    <span>{fieldName}</span>
                    <span className="text-xs text-gray-500">
                      {fieldKey} • {fieldType}
                    </span>
                  </div>
                </div>
              </SelectItem>
            );
          })}
        </SelectContent>
      </Select>
    </BaseWidgetWrapper>
  );
};

const FieldMultiSelect: React.FC<WidgetProps & { fields: any[]; isLoading: boolean }> = ({
  value = [],
  onChange,
  fields,
  isLoading,
  ...props
}) => {
  const selectedValues = Array.isArray(value) ? value : [];
  const placeholder = props.placeholder || props.uiHints?.placeholder || 'Select fields';

  const handleToggle = (fieldKey: string) => {
    const newValues = selectedValues.includes(fieldKey)
      ? selectedValues.filter(v => v !== fieldKey)
      : [...selectedValues, fieldKey];
    onChange(newValues);
  };

  const handleRemove = (fieldKey: string) => {
    onChange(selectedValues.filter(v => v !== fieldKey));
  };

  return (
    <BaseWidgetWrapper {...props}>
      <div className="space-y-2">
        <Select
          value=""
          onValueChange={handleToggle}
          disabled={props.disabled || props.readonly || isLoading}
        >
          <SelectTrigger>
            {isLoading ? (
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Loading fields...</span>
              </div>
            ) : (
              <SelectValue placeholder={placeholder} />
            )}
          </SelectTrigger>
          <SelectContent>
            {fields.map((field: any) => {
              const fieldKey = field.slug || field.name || field.key || field.id;
              const fieldName = field.label || field.name || fieldKey;
              const isSelected = selectedValues.includes(fieldKey);

              return (
                <SelectItem
                  key={fieldKey}
                  value={fieldKey}
                  className={isSelected ? 'bg-blue-50' : ''}
                >
                  <div className="flex items-center gap-2">
                    {isSelected && <span className="text-blue-600">✓</span>}
                    <Database className="w-3 h-3 text-gray-400" />
                    {fieldName}
                  </div>
                </SelectItem>
              );
            })}
          </SelectContent>
        </Select>

        {selectedValues.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {selectedValues.map((fieldKey) => {
              const field = fields.find(f =>
                (f.slug || f.name || f.key || f.id) === fieldKey
              );
              const fieldName = field?.label || field?.name || fieldKey;

              return (
                <Badge
                  key={fieldKey}
                  variant="secondary"
                  className="flex items-center gap-1"
                >
                  <Database className="w-3 h-3 text-gray-400" />
                  {fieldName}
                  {!props.disabled && !props.readonly && (
                    <X
                      className="w-3 h-3 cursor-pointer hover:text-red-600"
                      onClick={() => handleRemove(fieldKey)}
                    />
                  )}
                </Badge>
              );
            })}
          </div>
        )}
      </div>
    </BaseWidgetWrapper>
  );
};