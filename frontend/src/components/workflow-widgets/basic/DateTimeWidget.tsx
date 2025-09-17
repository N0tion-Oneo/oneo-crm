/**
 * Date and time widgets
 */

import React from 'react';
import { Input } from '@/components/ui/input';
import { WidgetProps } from '../core/types';
import { BaseWidgetWrapper, getInputProps } from './BaseWidget';

export const DateWidget: React.FC<WidgetProps> = (props) => {
  const { value, onChange } = props;
  const inputProps = getInputProps(props);

  return (
    <BaseWidgetWrapper {...props}>
      <Input
        type="date"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        {...inputProps}
      />
    </BaseWidgetWrapper>
  );
};

export const TimeWidget: React.FC<WidgetProps> = (props) => {
  const { value, onChange } = props;
  const inputProps = getInputProps(props);

  return (
    <BaseWidgetWrapper {...props}>
      <Input
        type="time"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        {...inputProps}
      />
    </BaseWidgetWrapper>
  );
};

export const DateTimeWidget: React.FC<WidgetProps> = (props) => {
  const { value, onChange } = props;
  const inputProps = getInputProps(props);

  return (
    <BaseWidgetWrapper {...props}>
      <Input
        type="datetime-local"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        {...inputProps}
      />
    </BaseWidgetWrapper>
  );
};

/**
 * Time range widget for business hours
 */
export const TimeRangeWidget: React.FC<WidgetProps> = (props) => {
  const { value = {}, onChange } = props;

  const handleStartChange = (start: string) => {
    onChange({ ...value, start });
  };

  const handleEndChange = (end: string) => {
    onChange({ ...value, end });
  };

  return (
    <BaseWidgetWrapper {...props}>
      <div className="flex items-center gap-2">
        <Input
          type="time"
          value={value.start || ''}
          onChange={(e) => handleStartChange(e.target.value)}
          placeholder="Start time"
          disabled={props.disabled || props.readonly}
        />
        <span className="text-gray-500">to</span>
        <Input
          type="time"
          value={value.end || ''}
          onChange={(e) => handleEndChange(e.target.value)}
          placeholder="End time"
          disabled={props.disabled || props.readonly}
        />
      </div>
    </BaseWidgetWrapper>
  );
};