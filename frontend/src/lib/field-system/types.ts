// Field system types and interfaces

export interface Field {
  id: string
  name: string
  display_name?: string
  field_type: string
  field_config?: Record<string, any>
  config?: Record<string, any> // Legacy support
  is_required?: boolean
  is_readonly?: boolean
  help_text?: string
  placeholder?: string
  original_slug?: string // Backend slug for API calls
}

export interface FieldRenderProps {
  field: Field
  value: any
  onChange: (value: any) => void
  onBlur?: () => void
  onKeyDown?: (e: React.KeyboardEvent) => void
  disabled?: boolean
  error?: string
  className?: string
  autoFocus?: boolean
  context?: 'form' | 'drawer' | 'table' | 'display'
}

export interface FieldDisplayProps {
  field: Field
  value: any
  context?: 'table' | 'detail' | 'card'
  className?: string
}

export interface ValidationResult {
  isValid: boolean
  error?: string
}

export interface FieldComponent {
  // Render input component for editing
  renderInput: (props: FieldRenderProps) => JSX.Element
  
  // Format value for display
  formatValue: (value: any, field: Field, context?: string) => string | JSX.Element
  
  // Validate field value
  validate?: (value: any, field: Field) => ValidationResult
  
  // Get default value
  getDefaultValue?: (field: Field) => any
  
  // Check if value is empty
  isEmpty?: (value: any) => boolean
}

export interface FieldConfig {
  // Field configuration from backend
  [key: string]: any
}

export interface FieldTypeSchema {
  key: string
  label: string
  description: string
  category: string
  icon: string
  config_schema: any
  supports_validation: boolean
  is_computed: boolean
}