/**
 * Core types for the centralized workflow widget system
 */

import { ReactElement } from 'react';

/**
 * Base configuration for all widgets
 */
export interface BaseWidgetConfig {
  key: string;
  label?: string;
  value: any;
  onChange: (value: any) => void;
  placeholder?: string;
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  error?: string;
  helpText?: string;
  className?: string;
}

/**
 * UI hints from backend schema
 */
export interface UIHints {
  widget?: string;
  placeholder?: string;
  help_text?: string;
  section?: string;
  rows?: number;
  options?: Array<{ label: string; value: any }>;
  min?: number;
  max?: number;
  step?: number;
  pattern?: string;
  // Dynamic select
  fetch_endpoint?: string;
  depends_on?: string;
  value_field?: string;
  label_field?: string;
  show_field_count?: boolean;
  group_by?: string;
  store_additional_fields?: string[];
  // Computed fields
  computed_from?: string;
  // Conditional display
  show_when?: Record<string, any>;
  // Additional hints
  visual?: boolean;
  supports_change_operators?: boolean;
  on_change_update?: string[];
  [key: string]: any;
}

/**
 * Widget props that include both base config and UI hints
 */
export interface WidgetProps extends BaseWidgetConfig {
  uiHints?: UIHints;
  // Context data for widgets that need it
  config?: Record<string, any>;  // Full form config for conditional logic
  field?: { key: string };  // Field metadata
  onConfigUpdate?: (config: Record<string, any>) => void;  // Update entire config object
  pipelines?: any[];
  users?: any[];
  userTypes?: any[];
  workflows?: any[];
  pipelineFields?: any[];
  availableVariables?: Array<{ nodeId: string; label: string; outputs: string[] }>;
}

/**
 * Widget definition in the registry
 */
export interface WidgetDefinition {
  name: string;
  component: React.ComponentType<WidgetProps>;
  defaultProps?: Partial<WidgetProps>;
  validator?: (value: any) => string | null;
  transformer?: {
    fromBackend?: (value: any) => any;
    toBackend?: (value: any) => any;
  };
}

/**
 * Widget renderer props
 */
export interface WidgetRendererProps {
  widget: string;  // Widget type from backend
  fieldType?: string;  // Field type as fallback
  props: WidgetProps;
}

/**
 * Registry interface
 */
export interface IWidgetRegistry {
  register(name: string, definition: WidgetDefinition): void;
  get(name: string): WidgetDefinition | undefined;
  has(name: string): boolean;
  getAll(): Map<string, WidgetDefinition>;
  render(widget: string, props: WidgetProps): ReactElement | null;
}