import React from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card } from '@/components/ui/card';

interface FieldValueMatcherProps {
  fieldName: string;
  fieldData?: any; // The field definition with type and options
  value?: {
    fromType?: string;
    from?: any;
    toType?: string;
    to?: any;
  };
  onChange: (value: any) => void;
}

export function FieldValueMatcher({
  fieldName,
  fieldData,
  value = {},
  onChange
}: FieldValueMatcherProps) {
  // Debug field data structure
  console.log('FieldValueMatcher - Field data for', fieldName, ':', {
    fieldData,
    hasFieldConfig: !!fieldData?.field_config,
    hasFieldConfigOptions: !!fieldData?.field_config?.options,
    hasOptions: !!fieldData?.options,
    fieldType: fieldData?.field_type || fieldData?.fieldType,
    optionsArray: fieldData?.field_config?.options || fieldData?.fieldConfig?.options || fieldData?.options
  });

  const updateValue = (key: string, val: any) => {
    onChange({
      ...value,
      [key]: val
    });
  };

  // Extract field options if it's a select/multiselect field
  // Handle different field data structures from API
  const fieldOptions =
    fieldData?.field_config?.options ||
    fieldData?.fieldConfig?.options ||
    fieldData?.options ||
    [];
  const hasOptions = fieldOptions.length > 0;

  // Check if this is a select/multiselect field type
  const isSelectField = fieldData?.field_type === 'select' ||
                       fieldData?.field_type === 'multiselect' ||
                       fieldData?.fieldType === 'select' ||
                       fieldData?.fieldType === 'multiselect';

  const renderValueInput = (
    type: string | undefined,
    currentValue: any,
    prefix: 'from' | 'to'
  ) => {
    const valueType = type || 'any';

    if (valueType === 'any') {
      return null;
    }

    if (valueType === 'text') {
      return (
        <Input
          value={currentValue || ''}
          onChange={(e) => updateValue(prefix, e.target.value)}
          placeholder={`Enter ${prefix === 'from' ? 'previous' : 'new'} value`}
          className="mt-1"
        />
      );
    }

    if (valueType === 'field_option' && hasOptions) {
      return (
        <Select
          value={currentValue || ''}
          onValueChange={(val) => updateValue(prefix, val)}
        >
          <SelectTrigger className="mt-1">
            <SelectValue placeholder="Select option" />
          </SelectTrigger>
          <SelectContent>
            {fieldOptions.map((opt: any) => {
              const optValue = typeof opt === 'string' ? opt : (opt.value || opt);
              const optLabel = typeof opt === 'string' ? opt : (opt.label || opt.value || opt);
              return (
                <SelectItem key={optValue} value={optValue}>
                  {optLabel}
                </SelectItem>
              );
            })}
          </SelectContent>
        </Select>
      );
    }

    if (valueType === 'expression') {
      return (
        <Input
          value={currentValue || ''}
          onChange={(e) => updateValue(prefix, e.target.value)}
          placeholder="{{variable}}"
          className="mt-1 font-mono text-sm"
        />
      );
    }

    return null;
  };

  return (
    <Card className="p-3 mb-3">
      <div className="font-medium text-sm mb-3">
        {fieldData?.label || fieldName}
      </div>

      <div className="space-y-3">
        {/* From Value */}
        <div>
          <Label className="text-xs">Changed From</Label>
          <Select
            value={value.fromType || 'any'}
            onValueChange={(val) => updateValue('fromType', val)}
          >
            <SelectTrigger className="mt-1">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="any">Any Value</SelectItem>
              <SelectItem value="text">Text Value</SelectItem>
              {isSelectField && hasOptions && <SelectItem value="field_option">Field Option</SelectItem>}
              <SelectItem value="expression">Expression</SelectItem>
            </SelectContent>
          </Select>
          {renderValueInput(value.fromType, value.from, 'from')}
        </div>

        {/* To Value */}
        <div>
          <Label className="text-xs">Changed To</Label>
          <Select
            value={value.toType || 'any'}
            onValueChange={(val) => updateValue('toType', val)}
          >
            <SelectTrigger className="mt-1">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="any">Any Value</SelectItem>
              <SelectItem value="text">Text Value</SelectItem>
              {isSelectField && hasOptions && <SelectItem value="field_option">Field Option</SelectItem>}
              <SelectItem value="expression">Expression</SelectItem>
            </SelectContent>
          </Select>
          {renderValueInput(value.toType, value.to, 'to')}
        </div>
      </div>
    </Card>
  );
}