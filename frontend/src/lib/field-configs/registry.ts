import { FieldConfigComponent } from './types'

// Import field configuration components
import { AIFieldConfig } from '@/components/pipelines/field-configs/AIFieldConfig'
import { RelationFieldConfig } from '@/components/pipelines/field-configs/RelationFieldConfig'
import { PhoneFieldConfig } from '@/components/pipelines/field-configs/PhoneFieldConfig'
import { UserFieldConfig } from '@/components/pipelines/field-configs/UserFieldConfig'
import { NumberFieldConfig } from '@/components/pipelines/field-configs/NumberFieldConfig'
import { SelectFieldConfig } from '@/components/pipelines/field-configs/SelectFieldConfig'
import { TextFieldConfig } from '@/components/pipelines/field-configs/TextFieldConfig'
import { BooleanFieldConfig } from '@/components/pipelines/field-configs/BooleanFieldConfig'
import { DateFieldConfig } from '@/components/pipelines/field-configs/DateFieldConfig'
import { TagsFieldConfig } from '@/components/pipelines/field-configs/TagsFieldConfig'
import { FileFieldConfig } from '@/components/pipelines/field-configs/FileFieldConfig'

// TODO: Import remaining field config components as they are created
// import { AddressFieldConfig } from '@/components/pipelines/field-configs/AddressFieldConfig'
// import { ButtonFieldConfig } from '@/components/pipelines/field-configs/ButtonFieldConfig'

/**
 * Registry mapping field types to their configuration components
 */
export const fieldConfigRegistry: Record<string, FieldConfigComponent> = {
  // Complex field types (Phase 1 - Completed)
  ai_generated: {
    component: AIFieldConfig,
    requiresAiConfig: true,
    requiresAvailableFields: true
  },
  
  ai_field: {
    component: AIFieldConfig,
    requiresAiConfig: true,
    requiresAvailableFields: true
  },
  
  ai: {
    component: AIFieldConfig,
    requiresAiConfig: true,
    requiresAvailableFields: true
  },
  
  relation: {
    component: RelationFieldConfig,
    requiresAvailableFields: false // Loads its own pipeline data
  },
  
  phone: {
    component: PhoneFieldConfig,
    requiresGlobalOptions: true
  },
  
  user: {
    component: UserFieldConfig
  },

  number: {
    component: NumberFieldConfig,
    requiresGlobalOptions: true // For currency options
  },
  
  select: {
    component: SelectFieldConfig
  },
  
  multiselect: {
    component: SelectFieldConfig
  },

  // Text field types
  text: {
    component: TextFieldConfig
  },
  
  textarea: {
    component: TextFieldConfig
  },
  
  email: {
    component: TextFieldConfig
  },
  
  url: {
    component: TextFieldConfig
  },

  // Other field types
  boolean: {
    component: BooleanFieldConfig
  },

  date: {
    component: DateFieldConfig
  },

  tags: {
    component: TagsFieldConfig
  },

  file: {
    component: FileFieldConfig
  }

  // TODO: Add remaining field types as components are created
  // address: {
  //   component: AddressFieldConfig,
  //   requiresGlobalOptions: true // For countries/regions
  // },
  // button: {
  //   component: ButtonFieldConfig
  // }
}

/**
 * Get the configuration component for a field type
 */
export function getFieldConfigComponent(fieldType: string): FieldConfigComponent | null {
  return fieldConfigRegistry[fieldType] || null
}

/**
 * Check if a field type has a dedicated configuration component
 */
export function hasFieldConfig(fieldType: string): boolean {
  return fieldType in fieldConfigRegistry
}

/**
 * Get all registered field types
 */
export function getRegisteredFieldTypes(): string[] {
  return Object.keys(fieldConfigRegistry)
}

/**
 * Get field types that require specific dependencies
 */
export function getFieldTypesRequiring(dependency: keyof FieldConfigComponent): string[] {
  return Object.entries(fieldConfigRegistry)
    .filter(([_, config]) => config[dependency])
    .map(([fieldType]) => fieldType)
}