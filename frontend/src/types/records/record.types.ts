// Record-related type definitions extracted from record-list-view.tsx

export interface RecordField {
  id: string
  name: string
  display_name?: string
  field_type: 'text' | 'textarea' | 'number' | 'decimal' | 'integer' | 'float' | 'currency' | 'percentage' | 
              'boolean' | 'date' | 'datetime' | 'time' | 'select' | 'multiselect' | 'radio' | 'checkbox' |
              'email' | 'phone' | 'url' | 'address' | 'file' | 'image' | 'relation' | 'relationship' | 'related' |
              'user' | 'ai' | 'ai_field' | 'button' | 'tags'
  is_required?: boolean
  is_visible_in_list?: boolean
  is_visible_in_detail?: boolean
  display_order: number
  field_config?: { [key: string]: any }
  config?: { [key: string]: any } // Legacy support
  field_group?: string | null // Field group ID for organization
  business_rules?: {
    stage_requirements?: {[key: string]: { 
      required: boolean
      block_transitions?: boolean
      show_warnings?: boolean
      warning_message?: string
    }}
    user_visibility?: {[key: string]: { visible: boolean; editable: boolean }}
  }
}

export interface Record {
  id: string
  data: { [key: string]: any }
  stage?: string
  tags?: string[]
  created_at: string
  updated_at: string
  created_by?: {
    id: string
    first_name: string
    last_name: string
    email: string
  }
}

export interface FieldGroup {
  id: string
  name: string
  description?: string
  color: string
  icon: string
  display_order: number
  field_count: number
}

export interface Pipeline {
  id: string
  name: string
  description: string
  fields: RecordField[]
  field_groups?: FieldGroup[]
  stages?: string[]
  record_count: number
}

// Convert RecordField to Field type for field registry
export const convertToFieldType = (recordField: RecordField) => ({
  id: recordField.id,
  name: recordField.name,
  display_name: recordField.display_name,
  field_type: recordField.field_type as string,
  field_config: recordField.field_config,
  config: recordField.config, // Legacy support
  is_readonly: false, // List view doesn't handle readonly
  help_text: undefined,
  placeholder: undefined
})

export interface RecordListViewProps {
  pipeline: Pipeline
  onEditRecord?: (record: Record, relatedPipeline?: Pipeline) => void
  onCreateRecord?: () => void
}