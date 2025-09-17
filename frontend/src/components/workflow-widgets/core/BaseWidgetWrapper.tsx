/**
 * BaseWidgetWrapper - Common wrapper for all workflow widgets
 * Provides consistent layout, labels, help text, and error display
 */

import React from 'react';
import { cn } from '@/lib/utils';
import { Label } from '@/components/ui/label';

interface BaseWidgetWrapperProps {
  children: React.ReactNode;
  label?: string;
  helpText?: string;
  error?: string;
  required?: boolean;
  className?: string;
}

export function BaseWidgetWrapper({
  children,
  label,
  helpText,
  error,
  required,
  className
}: BaseWidgetWrapperProps) {
  return (
    <div className={cn('space-y-2', className)}>
      {label && (
        <Label className={cn('text-sm font-medium', error && 'text-destructive')}>
          {label}
          {required && <span className="text-destructive ml-1">*</span>}
        </Label>
      )}

      {children}

      {helpText && !error && (
        <p className="text-xs text-muted-foreground">{helpText}</p>
      )}

      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
    </div>
  );
}