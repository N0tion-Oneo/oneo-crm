/**
 * Base widget component with common functionality
 */

import React from 'react';
import { WidgetProps } from '../core/types';
import { cn } from '@/lib/utils';

export interface BaseWidgetComponentProps extends WidgetProps {
  children?: React.ReactNode;
  wrapperClassName?: string;
}

export const BaseWidgetWrapper: React.FC<BaseWidgetComponentProps> = ({
  children,
  label,
  helpText,
  error,
  required,
  wrapperClassName,
  className
}) => {
  return (
    <div className={cn("space-y-2", wrapperClassName)}>
      {label && (
        <label className="block text-sm font-medium text-gray-700">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}

      <div className={className}>
        {children}
      </div>

      {helpText && !error && (
        <p className="text-sm text-gray-500">{helpText}</p>
      )}

      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}
    </div>
  );
};

/**
 * Common props transformer for standard HTML input attributes
 */
export const getInputProps = (props: WidgetProps) => {
  const {
    placeholder,
    disabled,
    readonly,
    required,
    uiHints = {}
  } = props;

  return {
    placeholder: placeholder || uiHints.placeholder,
    disabled: disabled,
    readOnly: readonly,
    required: required,
    ...extractHtmlAttributes(uiHints)
  };
};

/**
 * Extract standard HTML attributes from UI hints
 */
const extractHtmlAttributes = (uiHints: any) => {
  const attrs: any = {};

  if (uiHints.min !== undefined) attrs.min = uiHints.min;
  if (uiHints.max !== undefined) attrs.max = uiHints.max;
  if (uiHints.step !== undefined) attrs.step = uiHints.step;
  if (uiHints.pattern !== undefined) attrs.pattern = uiHints.pattern;
  if (uiHints.rows !== undefined) attrs.rows = uiHints.rows;
  if (uiHints.cols !== undefined) attrs.cols = uiHints.cols;
  if (uiHints.maxLength !== undefined) attrs.maxLength = uiHints.maxLength;
  if (uiHints.minLength !== undefined) attrs.minLength = uiHints.minLength;

  return attrs;
};