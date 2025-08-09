export interface FieldConfigurationProps {
  config: Record<string, any>
  onChange: (key: string, value: any) => void
  // Optional props for specific field types
  aiConfig?: Record<string, any>
  onAiConfigChange?: (aiConfig: Record<string, any>) => void
  availableFields?: { id: string; name: string; display_name: string; field_type: string }[]
  globalOptions?: Record<string, any>
}

export interface FieldConfigComponent {
  component: React.ComponentType<any>
  requiresAiConfig?: boolean
  requiresGlobalOptions?: boolean
  requiresAvailableFields?: boolean
}

export interface FieldTypeConfig {
  key: string
  label: string
  description: string
  category: 'basic' | 'selection' | 'datetime' | 'advanced' | 'system'
  icon: string
  config_schema: any
  supports_validation: boolean
  is_computed: boolean
  config_class: string
}