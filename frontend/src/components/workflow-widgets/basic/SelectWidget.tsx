/**
 * Select and multiselect widgets
 */

import React from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { X } from 'lucide-react';
import { WidgetProps } from '../core/types';
import { BaseWidgetWrapper } from './BaseWidget';

export const SelectWidget: React.FC<WidgetProps> = (props) => {
  const { value, onChange, uiHints = {} } = props;

  const options = uiHints.options || [];
  const placeholder = props.placeholder || uiHints.placeholder || 'Select an option';

  return (
    <BaseWidgetWrapper {...props}>
      <Select
        value={value?.toString() || ''}
        onValueChange={onChange}
        disabled={props.disabled || props.readonly}
      >
        <SelectTrigger>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {options.map((option: any) => (
            <SelectItem key={option.value} value={option.value?.toString()}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </BaseWidgetWrapper>
  );
};

/**
 * Multiselect widget
 */
export const MultiselectWidget: React.FC<WidgetProps> = (props) => {
  const { value = [], onChange, uiHints = {} } = props;

  const options = uiHints.options || [];
  const selectedValues = Array.isArray(value) ? value : [];
  const placeholder = props.placeholder || uiHints.placeholder || 'Select options';

  const handleToggle = (optionValue: any) => {
    const newValues = selectedValues.includes(optionValue)
      ? selectedValues.filter(v => v !== optionValue)
      : [...selectedValues, optionValue];
    onChange(newValues);
  };

  const handleRemove = (optionValue: any) => {
    onChange(selectedValues.filter(v => v !== optionValue));
  };

  return (
    <BaseWidgetWrapper {...props}>
      <div className="space-y-2">
        <Select
          value=""
          onValueChange={handleToggle}
          disabled={props.disabled || props.readonly}
        >
          <SelectTrigger>
            <SelectValue placeholder={placeholder} />
          </SelectTrigger>
          <SelectContent>
            {options.map((option: any) => {
              const isSelected = selectedValues.includes(option.value);
              return (
                <SelectItem
                  key={option.value}
                  value={option.value?.toString()}
                  className={isSelected ? 'bg-blue-50' : ''}
                >
                  <div className="flex items-center gap-2">
                    {isSelected && <span className="text-blue-600">✓</span>}
                    {option.label}
                  </div>
                </SelectItem>
              );
            })}
          </SelectContent>
        </Select>

        {selectedValues.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {selectedValues.map((val) => {
              const option = options.find((o: any) => o.value === val);
              return (
                <Badge
                  key={val}
                  variant="secondary"
                  className="flex items-center gap-1"
                >
                  {option?.label || val}
                  {!props.disabled && !props.readonly && (
                    <X
                      className="w-3 h-3 cursor-pointer hover:text-red-600"
                      onClick={() => handleRemove(val)}
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