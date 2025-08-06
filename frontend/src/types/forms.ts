// Dynamic Form Types - Pipeline-based form generation

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

