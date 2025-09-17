/**
 * Checkbox and radio widgets
 */

import React from 'react';
import { Checkbox } from '@/components/ui/checkbox';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { WidgetProps } from '../core/types';
import { BaseWidgetWrapper } from './BaseWidget';

export const CheckboxWidget: React.FC<WidgetProps> = (props) => {
  const { value, onChange, uiHints = {}, name } = props;

  const checkboxLabel = uiHints.checkbox_label || props.label;
  const fieldId = name || 'checkbox';

  return (
    <BaseWidgetWrapper {...props} label={undefined}>
      <div className="flex items-center space-x-2">
        <Checkbox
          id={fieldId}
          checked={!!value}
          onCheckedChange={(checked) => onChange(!!checked)}
          disabled={props.disabled || props.readonly}
        />
        <Label
          htmlFor={fieldId}
          className="text-sm font-normal cursor-pointer select-none"
        >
          {checkboxLabel}
          {props.required && <span className="text-red-500 ml-1">*</span>}
        </Label>
      </div>
    </BaseWidgetWrapper>
  );
};

/**
 * Radio widget
 */
export const RadioWidget: React.FC<WidgetProps> = (props) => {
  const { value, onChange, uiHints = {}, name } = props;

  const options = uiHints.options || [];
  const fieldId = name || 'radio';

  return (
    <BaseWidgetWrapper {...props}>
      <RadioGroup
        value={value?.toString() || ''}
        onValueChange={onChange}
        disabled={props.disabled || props.readonly}
      >
        {options.map((option: any) => (
          <div key={option.value} className="flex items-center space-x-2">
            <RadioGroupItem value={option.value?.toString()} id={`${fieldId}-${option.value}`} />
            <Label
              htmlFor={`${fieldId}-${option.value}`}
              className="text-sm font-normal cursor-pointer select-none"
            >
              {option.label}
            </Label>
          </div>
        ))}
      </RadioGroup>
    </BaseWidgetWrapper>
  );
};