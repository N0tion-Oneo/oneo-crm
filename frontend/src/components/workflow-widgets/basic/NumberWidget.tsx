/**
 * Number input widgets
 */

import React from 'react';
import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';
import { WidgetProps } from '../core/types';
import { BaseWidgetWrapper, getInputProps } from './BaseWidget';

export const NumberWidget: React.FC<WidgetProps> = (props) => {
  const { value, onChange, uiHints = {} } = props;
  const inputProps = getInputProps(props);

  return (
    <BaseWidgetWrapper {...props}>
      <Input
        type="number"
        value={value ?? ''}
        onChange={(e) => {
          const val = e.target.value;
          onChange(val === '' ? undefined : Number(val));
        }}
        {...inputProps}
      />
    </BaseWidgetWrapper>
  );
};

/**
 * Slider widget
 */
export const SliderWidget: React.FC<WidgetProps> = (props) => {
  const { value, onChange, uiHints = {} } = props;
  const min = uiHints.min ?? 0;
  const max = uiHints.max ?? 100;
  const step = uiHints.step ?? 1;

  return (
    <BaseWidgetWrapper {...props}>
      <div className="flex items-center gap-4">
        <Slider
          value={[value ?? min]}
          onValueChange={([val]) => onChange(val)}
          min={min}
          max={max}
          step={step}
          disabled={props.disabled || props.readonly}
          className="flex-1"
        />
        <div className="w-16 text-center text-sm font-medium">
          {value ?? min}
        </div>
      </div>
    </BaseWidgetWrapper>
  );
};