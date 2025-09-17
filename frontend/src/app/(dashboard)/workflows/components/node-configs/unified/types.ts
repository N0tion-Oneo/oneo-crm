import { WorkflowNodeType } from '../../../types';
import { ReactElement } from 'react';

/**
 * Unified configuration structure for all workflow nodes.
 * Each node has ONE configuration that defines everything it needs.
 */

export interface UnifiedNodeConfig {
  // Basic metadata
  type: WorkflowNodeType;
  label: string;
  description?: string;
  icon?: React.ComponentType<any>;
  category: 'trigger' | 'action' | 'control' | 'data' | 'communication' | 'integration';
  
  // Configuration sections
  sections: ConfigSection[];
  
  // Optional custom UI component for complex interactions
  // If not provided, will use auto-generated form from sections
  customComponent?: React.ComponentType<NodeConfigComponentProps>;
  
  // Validation
  validate?: (config: any) => Record<string, string>; // Returns errors
  
  // Default configuration
  defaults?: Record<string, any>;
  
  // Dependencies (e.g., needs pipeline selection)
  dependencies?: {
    pipelines?: boolean;
    workflows?: boolean;
    users?: boolean;
    fields?: boolean;
  };
  
  // Feature flags
  features?: {
    supportsExpressions?: boolean;
    supportsVariables?: boolean;
    supportsTesting?: boolean;
    supportsTemplates?: boolean;
  };
}

export interface ConfigSection {
  id: string;
  label: string;
  description?: string;
  icon?: React.ComponentType<any>;
  collapsed?: boolean; // Start collapsed
  advanced?: boolean; // Mark as advanced section
  showWhen?: (config: any) => boolean; // Conditional visibility
  fields: ConfigField[];
}

export interface ConfigField {
  key: string;
  label: string;
  type: FieldType;
  description?: string;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  readonly?: boolean;

  // Conditional display
  showWhen?: (config: any) => boolean;

  // Validation
  validation?: (value: any, config: any) => string | null;

  // Type-specific options
  options?: SelectOption[]; // For select, multiselect, radio
  min?: number; // For number, slider
  max?: number; // For number, slider
  step?: number; // For number, slider
  rows?: number; // For textarea
  accept?: string; // For file input
  multiple?: boolean; // For file, select

  // Dynamic options configuration
  optionsSource?: 'pipelines' | 'users' | 'userTypes' | 'unipileAccounts' | 'workflows' | 'pipelineFields';
  optionsFilter?: (item: any) => boolean;
  optionsMap?: (item: any) => SelectOption;

  // For field-value type: which field to get options from
  fieldSource?: string; // The config key that contains the selected field

  // For field-select type: filter fields
  fieldFilter?: (field: any) => boolean;

  // Expression support
  allowExpressions?: boolean;
  expressionPlaceholder?: string;

  // Rich field options
  richField?: {
    type: 'code' | 'json' | 'html' | 'markdown';
    language?: string; // For code
    height?: string;
  };

  // Default value
  defaultValue?: any;

  // Help text
  helpText?: string;

  // UI hints for custom widgets
  uiHints?: {
    widget?: string; // Custom widget identifier
    visual?: boolean; // Use visual mode for JSON builder
    [key: string]: any; // Other widget-specific hints
  };

  // Custom widget type override
  widget?: string;

  // For tag input
  suggestions?: string[];
  tagValidation?: (tag: string) => string | null;
  maxTags?: number;
  allowDuplicates?: boolean;

  // For JSON builder
  templates?: Array<{
    label: string;
    value: any;
    description?: string;
  }>;

  // Custom onChange handler
  onChange?: (value: any, config: any, context: any) => any;

  // Custom render (for very special cases)
  customRender?: (props: FieldRenderProps) => ReactElement;

  // For dynamic_select widget
  fetchEndpoint?: string; // API endpoint to fetch options from
  dependsOn?: string; // Field key that this field depends on
  valueField?: string; // Field to use as value in fetched data
  labelField?: string; // Field to use as label in fetched data
  showFieldCount?: boolean; // Show field count in options
  groupBy?: string; // Group options by this field

  // For readonly computed fields
  computedFrom?: string; // Path to value in config (e.g., 'form_metadata.url')
}

export type FieldType =
  | 'text'
  | 'textarea'
  | 'number'
  | 'select'
  | 'multiselect'
  | 'boolean'
  | 'radio'
  | 'checkbox'
  | 'date'
  | 'time'
  | 'datetime'
  | 'file'
  | 'color'
  | 'slider'
  | 'array' // For managing arrays of items
  | 'tags' // Enhanced tag input
  | 'keyvalue' // For key-value pairs
  | 'json' // JSON editor
  | 'code' // Code editor
  | 'html' // HTML editor
  | 'markdown' // Markdown editor
  | 'expression' // Expression builder
  | 'pipeline' // Pipeline selector
  | 'field' // Field selector
  | 'field-value' // Field value selector (shows options from selected field)
  | 'user' // User selector
  | 'team' // Team selector
  | 'workflow' // Workflow selector
  | 'conditions' // Condition builder for complex logic
  | 'custom'; // Custom component

export interface SelectOption {
  label: string;
  value: string | number | boolean;
  description?: string;
  icon?: React.ComponentType<any>;
  disabled?: boolean;
}

export interface NodeConfigComponentProps {
  config: any;
  onChange: (config: any) => void;
  availableVariables?: Array<{ nodeId: string; label: string; outputs: string[] }>;
  pipelines?: any[];
  workflows?: any[];
  users?: any[];
  userTypes?: any[];
  unipileAccounts?: any[];
  pipelineFields?: any[];
  errors?: Record<string, string>;
}

export interface FieldRenderProps {
  field: ConfigField;
  value: any;
  onChange: (value: any) => void;
  error?: string;
  config: any; // Full config for conditional logic
  availableVariables?: Array<{ nodeId: string; label: string; outputs: string[] }>;
  pipelines?: any[];
  pipelineFields?: any[];
  users?: any[];
  userTypes?: any[];
  unipileAccounts?: any[];
  workflows?: any[];
}

// Helper type for node configuration registry
export type NodeConfigRegistry = {
  [K in WorkflowNodeType]: UnifiedNodeConfig;
};