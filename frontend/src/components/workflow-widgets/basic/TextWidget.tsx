/**
 * Text input widget
 */

import React from 'react';
import { Input } from '@/components/ui/input';
import { WidgetProps } from '../core/types';
import { BaseWidgetWrapper, getInputProps } from './BaseWidget';

export const TextWidget: React.FC<WidgetProps> = (props) => {
  const { value, onChange, uiHints = {} } = props;
  const inputProps = getInputProps(props);

  // Handle readonly display
  if (props.readonly && uiHints.widget === 'readonly_text') {
    // Computed value display
    if (uiHints.computed_from) {
      const computedValue = getNestedValue(props.config, uiHints.computed_from);
      return (
        <BaseWidgetWrapper {...props}>
          <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-700">
            {computedValue || <span className="text-gray-400">Not yet computed</span>}
          </div>
        </BaseWidgetWrapper>
      );
    }

    return (
      <BaseWidgetWrapper {...props}>
        <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-700">
          {value || <span className="text-gray-400">No value</span>}
        </div>
      </BaseWidgetWrapper>
    );
  }

  return (
    <BaseWidgetWrapper {...props}>
      <Input
        type="text"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        {...inputProps}
      />
    </BaseWidgetWrapper>
  );
};

/**
 * Textarea widget
 */
export const TextareaWidget: React.FC<WidgetProps> = (props) => {
  const { value, onChange } = props;
  const inputProps = getInputProps(props);

  return (
    <BaseWidgetWrapper {...props}>
      <textarea
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
        {...inputProps}
      />
    </BaseWidgetWrapper>
  );
};

/**
 * Password widget
 */
export const PasswordWidget: React.FC<WidgetProps> = (props) => {
  const { value, onChange } = props;
  const inputProps = getInputProps(props);

  return (
    <BaseWidgetWrapper {...props}>
      <Input
        type="password"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        {...inputProps}
      />
    </BaseWidgetWrapper>
  );
};

/**
 * Helper to get nested value from object
 */
function getNestedValue(obj: any, path: string): any {
  if (!obj || !path) return undefined;

  const keys = path.split('.');
  let current = obj;

  for (const key of keys) {
    if (current && typeof current === 'object' && key in current) {
      current = current[key];
    } else {
      return undefined;
    }
  }

  return current;
}