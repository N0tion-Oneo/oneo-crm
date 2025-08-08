// Dynamic Form Types - Pipeline-based form generation

// Dynamic form generation types
export interface DynamicFormField {
  name: string
  label: string
  field_type: string
  // is_required removed - now handled by conditional rules
  is_visible_in_detail: boolean
  configuration: any
  help_text?: string
  business_rules?: any // For conditional rules evaluation
}

export interface DynamicFormSchema {
  pipeline_id: number
  pipeline_name: string
  mode: string
  stage?: string
  fields: DynamicFormField[]
  generated_at: string
}

