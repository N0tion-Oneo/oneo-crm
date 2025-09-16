import React from 'react';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Plus, Trash2 } from 'lucide-react';

interface Condition {
  field: string;
  operator: string;
  value: any;
  value_to?: any; // For between operator
}

interface ConditionBuilderProps {
  fields: any[];
  conditions: Condition[];
  onChange: (conditions: Condition[]) => void;
  allowMultiple?: boolean;
  logicalOperator?: 'AND' | 'OR';
  onLogicalOperatorChange?: (operator: 'AND' | 'OR') => void;
}

export function ConditionBuilder({
  fields,
  conditions = [],
  onChange,
  allowMultiple = true,
  logicalOperator = 'AND',
  onLogicalOperatorChange
}: ConditionBuilderProps) {

  // Get operators for a specific field type
  const getOperatorsForFieldType = (fieldType: string) => {
    switch (fieldType) {
      case 'text':
      case 'textarea':
      case 'email':
      case 'url':
      case 'phone':
        return [
          { value: 'equals', label: 'Equals' },
          { value: 'not_equals', label: 'Does not equal' },
          { value: 'contains', label: 'Contains' },
          { value: 'not_contains', label: 'Does not contain' },
          { value: 'starts_with', label: 'Starts with' },
          { value: 'ends_with', label: 'Ends with' },
          { value: 'is_empty', label: 'Is empty' },
          { value: 'is_not_empty', label: 'Is not empty' }
        ];

      case 'number':
        return [
          { value: 'equals', label: 'Equals' },
          { value: 'not_equals', label: 'Does not equal' },
          { value: 'greater_than', label: 'Greater than' },
          { value: 'greater_than_or_equal', label: 'Greater than or equal' },
          { value: 'less_than', label: 'Less than' },
          { value: 'less_than_or_equal', label: 'Less than or equal' },
          { value: 'between', label: 'Between' },
          { value: 'is_empty', label: 'Is empty' },
          { value: 'is_not_empty', label: 'Is not empty' }
        ];

      case 'boolean':
        return [
          { value: 'is_true', label: 'Is checked' },
          { value: 'is_false', label: 'Is not checked' }
        ];

      case 'date':
        return [
          { value: 'equals', label: 'Is on' },
          { value: 'before', label: 'Is before' },
          { value: 'after', label: 'Is after' },
          { value: 'between', label: 'Is between' },
          { value: 'in_last_days', label: 'In the last X days' },
          { value: 'in_next_days', label: 'In the next X days' },
          { value: 'is_today', label: 'Is today' },
          { value: 'is_past', label: 'Is in the past' },
          { value: 'is_future', label: 'Is in the future' },
          { value: 'is_empty', label: 'Is empty' },
          { value: 'is_not_empty', label: 'Is not empty' }
        ];

      case 'select':
      case 'multiselect':
      case 'tags':
        return [
          { value: 'equals', label: 'Is' },
          { value: 'not_equals', label: 'Is not' },
          { value: 'in', label: 'Is one of' },
          { value: 'not_in', label: 'Is not one of' },
          { value: 'is_empty', label: 'Is empty' },
          { value: 'is_not_empty', label: 'Is not empty' }
        ];

      case 'relation':
      case 'user':
        return [
          { value: 'equals', label: 'Is' },
          { value: 'not_equals', label: 'Is not' },
          { value: 'is_empty', label: 'Is empty' },
          { value: 'is_not_empty', label: 'Is not empty' }
        ];

      case 'file':
        return [
          { value: 'is_empty', label: 'No file attached' },
          { value: 'is_not_empty', label: 'Has file attached' }
        ];

      case 'address':
        return [
          { value: 'contains', label: 'Contains' },
          { value: 'not_contains', label: 'Does not contain' },
          { value: 'is_empty', label: 'Is empty' },
          { value: 'is_not_empty', label: 'Is not empty' }
        ];

      default:
        return [
          { value: 'equals', label: 'Equals' },
          { value: 'not_equals', label: 'Does not equal' },
          { value: 'is_empty', label: 'Is empty' },
          { value: 'is_not_empty', label: 'Is not empty' }
        ];
    }
  };

  // Get field options for select/multiselect fields
  const getFieldOptions = (field: any) => {
    if (!field) return [];
    return field.field_config?.options || [];
  };

  // Get the appropriate input component for a field and operator
  const renderValueInput = (condition: Condition, index: number) => {
    const field = fields.find(f => f.slug === condition.field);
    if (!field) return null;

    const operator = condition.operator;

    // No value input needed for these operators
    if (['is_empty', 'is_not_empty', 'is_true', 'is_false', 'is_today', 'is_past', 'is_future'].includes(operator)) {
      return null;
    }

    // Handle different field types
    switch (field.field_type) {
      case 'select':
      case 'multiselect':
      case 'tags':
        const options = getFieldOptions(field);

        if (operator === 'in' || operator === 'not_in') {
          // Multiple selection for in/not_in operators
          return (
            <div>
              <Label className="text-sm">Values (select multiple)</Label>
              <div className="space-y-2">
                {options.map((option: any) => (
                  <div key={option.value} className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={(condition.value || []).includes(option.value)}
                      onChange={(e) => {
                        const values = condition.value || [];
                        const newValues = e.target.checked
                          ? [...values, option.value]
                          : values.filter((v: string) => v !== option.value);
                        updateCondition(index, { ...condition, value: newValues });
                      }}
                      className="rounded border-gray-300"
                    />
                    <label className="text-sm">{option.label}</label>
                  </div>
                ))}
              </div>
            </div>
          );
        } else {
          // Single selection for equals/not_equals
          return (
            <div>
              <Label className="text-sm">Value</Label>
              <Select
                value={condition.value || ''}
                onValueChange={(value) => updateCondition(index, { ...condition, value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Choose value" />
                </SelectTrigger>
                <SelectContent>
                  {options.map((option: any) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          );
        }

      case 'boolean':
        // Boolean is handled by operator only (is_true/is_false)
        return null;

      case 'number':
        if (operator === 'between') {
          // Two inputs for between operator
          return (
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-sm">From</Label>
                <Input
                  type="number"
                  value={condition.value || ''}
                  onChange={(e) => updateCondition(index, { ...condition, value: e.target.value })}
                  placeholder="Min value"
                />
              </div>
              <div>
                <Label className="text-sm">To</Label>
                <Input
                  type="number"
                  value={condition.value_to || ''}
                  onChange={(e) => updateCondition(index, { ...condition, value_to: e.target.value })}
                  placeholder="Max value"
                />
              </div>
            </div>
          );
        } else {
          // Single number input
          const formatConfig = field.field_config?.format;
          return (
            <div>
              <Label className="text-sm">Value</Label>
              <Input
                type="number"
                value={condition.value || ''}
                onChange={(e) => updateCondition(index, { ...condition, value: e.target.value })}
                placeholder={formatConfig === 'currency' ? 'Amount' : 'Enter number'}
                step={formatConfig === 'decimal' || formatConfig === 'percentage' ? '0.01' : '1'}
              />
            </div>
          );
        }

      case 'date':
        if (operator === 'between') {
          // Two date inputs for between
          return (
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-sm">From</Label>
                <Input
                  type={field.field_config?.include_time ? 'datetime-local' : 'date'}
                  value={condition.value || ''}
                  onChange={(e) => updateCondition(index, { ...condition, value: e.target.value })}
                />
              </div>
              <div>
                <Label className="text-sm">To</Label>
                <Input
                  type={field.field_config?.include_time ? 'datetime-local' : 'date'}
                  value={condition.value_to || ''}
                  onChange={(e) => updateCondition(index, { ...condition, value_to: e.target.value })}
                />
              </div>
            </div>
          );
        } else if (operator === 'in_last_days' || operator === 'in_next_days') {
          // Number input for days
          return (
            <div>
              <Label className="text-sm">Number of days</Label>
              <Input
                type="number"
                min="1"
                value={condition.value || ''}
                onChange={(e) => updateCondition(index, { ...condition, value: e.target.value })}
                placeholder="Days"
              />
            </div>
          );
        } else {
          // Single date input
          return (
            <div>
              <Label className="text-sm">Date</Label>
              <Input
                type={field.field_config?.include_time ? 'datetime-local' : 'date'}
                value={condition.value || ''}
                onChange={(e) => updateCondition(index, { ...condition, value: e.target.value })}
              />
            </div>
          );
        }

      case 'relation':
      case 'user':
        // TODO: These would ideally load records/users from the API
        return (
          <div>
            <Label className="text-sm">Value</Label>
            <Input
              placeholder={field.field_type === 'user' ? 'User ID or email' : 'Record ID'}
              value={condition.value || ''}
              onChange={(e) => updateCondition(index, { ...condition, value: e.target.value })}
            />
          </div>
        );

      default:
        // Text input for everything else
        return (
          <div>
            <Label className="text-sm">Value</Label>
            <Input
              type="text"
              value={condition.value || ''}
              onChange={(e) => updateCondition(index, { ...condition, value: e.target.value })}
              placeholder={`Enter ${field.display_name || field.name}`}
            />
          </div>
        );
    }
  };

  const addCondition = () => {
    onChange([...conditions, { field: '', operator: '', value: '' }]);
  };

  const removeCondition = (index: number) => {
    onChange(conditions.filter((_, i) => i !== index));
  };

  const updateCondition = (index: number, updatedCondition: Condition) => {
    const newConditions = [...conditions];
    newConditions[index] = updatedCondition;
    onChange(newConditions);
  };

  if (conditions.length === 0) {
    return (
      <Button
        type="button"
        variant="outline"
        onClick={addCondition}
        className="w-full"
      >
        <Plus className="h-4 w-4 mr-2" />
        Add Condition
      </Button>
    );
  }

  return (
    <div className="space-y-4">
      {conditions.length > 1 && onLogicalOperatorChange && (
        <div>
          <Label>Match conditions</Label>
          <RadioGroup
            value={logicalOperator}
            onValueChange={(value) => onLogicalOperatorChange(value as 'AND' | 'OR')}
          >
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="AND" />
              <Label className="font-normal">All conditions (AND)</Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="OR" />
              <Label className="font-normal">Any condition (OR)</Label>
            </div>
          </RadioGroup>
        </div>
      )}

      {conditions.map((condition, index) => {
        const selectedField = fields.find(f => f.slug === condition.field);
        const operators = selectedField ? getOperatorsForFieldType(selectedField.field_type) : [];

        return (
          <div key={index} className="border rounded-lg p-4 space-y-3">
            <div className="flex justify-between items-start">
              <div className="text-sm font-medium">Condition {index + 1}</div>
              {(allowMultiple || conditions.length > 1) && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeCondition(index)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>

            <div>
              <Label className="text-sm">Field</Label>
              <Select
                value={condition.field || ''}
                onValueChange={(value) => {
                  // Reset operator and value when field changes
                  updateCondition(index, { field: value, operator: '', value: '' });
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Choose field" />
                </SelectTrigger>
                <SelectContent>
                  {fields.map(field => (
                    <SelectItem key={field.slug} value={field.slug}>
                      {field.display_name || field.name}
                      <span className="text-xs text-muted-foreground ml-2">
                        ({field.field_type})
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {condition.field && (
              <div>
                <Label className="text-sm">Operator</Label>
                <Select
                  value={condition.operator || ''}
                  onValueChange={(value) => {
                    // Reset value when operator changes
                    updateCondition(index, { ...condition, operator: value, value: '', value_to: undefined });
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Choose operator" />
                  </SelectTrigger>
                  <SelectContent>
                    {operators.map(op => (
                      <SelectItem key={op.value} value={op.value}>
                        {op.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {condition.field && condition.operator && renderValueInput(condition, index)}
          </div>
        );
      })}

      {allowMultiple && (
        <Button
          type="button"
          variant="outline"
          onClick={addCondition}
          className="w-full"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Another Condition
        </Button>
      )}
    </div>
  );
}