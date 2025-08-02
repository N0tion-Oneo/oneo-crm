// Simplified Forms Types

export interface FormTemplate {
  id: number
  name: string
  description?: string
  pipeline: number | string // Can be ID or slug
  form_type: 'dynamic' | 'custom'
  dynamic_mode?: 'all' | 'stage' | 'visible'
  target_stage?: string
  success_message?: string
  is_active: boolean
  field_configs?: FormFieldConfiguration[]
  created_at: string
  updated_at: string
}

export interface FormFieldConfiguration {
  id: number
  form_template: number
  pipeline_field: number | string // Can be ID or slug
  display_order: number
  is_visible: boolean
  is_readonly: boolean
  custom_label?: string
  custom_placeholder?: string
  custom_help_text?: string
  conditional_logic: Record<string, any> // This will store inline validation rules
  default_value?: any
  field_width: 'full' | 'half' | 'third' | 'quarter'
  is_active: boolean
  created_at: string
  updated_at: string
}

// Inline validation structure for conditional_logic field
export interface InlineValidation {
  required?: boolean
  type?: 'email' | 'phone' | 'url' | 'number'
  minLength?: number
  maxLength?: number
  minValue?: number
  maxValue?: number
  pattern?: string // regex pattern
  customMessage?: string
}

// Dynamic form generation types
export interface DynamicFormField {
  name: string
  label: string
  field_type: string
  is_required: boolean
  is_visible_in_detail: boolean
  configuration: any
  help_text?: string
}

export interface DynamicFormSchema {
  pipeline_id: number
  pipeline_name: string
  mode: string
  stage?: string
  fields: DynamicFormField[]
  generated_at: string
}

// Form creation/editing interfaces
export interface FormData {
  name: string
  description?: string
  pipeline: string
  form_type: 'dynamic' | 'custom'
  dynamic_mode?: 'all' | 'stage' | 'visible'
  target_stage?: string
  success_message?: string
  is_active: boolean
}

export interface FieldConfig {
  id?: number
  tempId?: string
  pipeline_field: number
  pipelineField?: any // Full pipeline field object for display
  display_order: number
  is_visible: boolean
  is_readonly: boolean
  custom_label?: string
  custom_placeholder?: string
  custom_help_text?: string
  validation: InlineValidation
  default_value?: any
  field_width: 'full' | 'half' | 'third' | 'quarter'
  is_active: boolean
}