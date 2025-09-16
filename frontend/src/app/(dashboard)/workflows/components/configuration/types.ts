import { ReactNode } from 'react';

export interface ParameterSection {
  id: string;
  label: string;
  icon?: React.ElementType;
  fields: ParameterField[];
  collapsed?: boolean;
  advanced?: boolean;
}

export interface ParameterField {
  key: string;
  label: string;
  type: 'text' | 'textarea' | 'number' | 'select' | 'boolean' | 'expression' | 'json' | 'array';
  placeholder?: string;
  required?: boolean;
  options?: Array<{ label: string; value: string }>;
  helpText?: string;
  validation?: (value: any) => string | null;
  showWhen?: (config: any) => boolean;
  allowExpressions?: boolean;
}