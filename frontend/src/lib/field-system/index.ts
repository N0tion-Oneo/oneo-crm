// Central field system initialization and exports
import { registerFieldComponent } from './field-registry'

// Import all field components
import { TextFieldComponent } from './components/text-field'
import { TextareaFieldComponent } from './components/textarea-field'
import { NumberFieldComponent } from './components/number-field'
import { SelectFieldComponent, MultiselectFieldComponent } from './components/select-field'
import { DateFieldComponent, DateTimeFieldComponent, TimeFieldComponent } from './components/date-field'
import { BooleanFieldComponent } from './components/boolean-field'
import { EmailFieldComponent, UrlFieldComponent } from './components/email-field'
import { PhoneFieldComponent } from './components/phone-field'
import { RelationFieldComponent } from './components/relation-field'
import { FileFieldComponent } from './components/file-field'
import { AddressFieldComponent } from './components/address-field'
import { TagsFieldComponent } from './components/tags-field'
import { AIFieldComponent } from './components/ai-field'
import { ButtonFieldComponent } from './components/button-field'
import { UserFieldComponent } from './components/user-field'

/**
 * Initialize the field registry with all available field components
 */
export function initializeFieldSystem() {
  // Basic text fields
  registerFieldComponent('text', TextFieldComponent)
  registerFieldComponent('textarea', TextareaFieldComponent)
  
  // Numeric fields
  registerFieldComponent('number', NumberFieldComponent)
  registerFieldComponent('integer', NumberFieldComponent)
  registerFieldComponent('decimal', NumberFieldComponent)
  registerFieldComponent('float', NumberFieldComponent)
  registerFieldComponent('currency', NumberFieldComponent)
  registerFieldComponent('percentage', NumberFieldComponent)
  
  // Selection fields
  registerFieldComponent('select', SelectFieldComponent)
  registerFieldComponent('multiselect', MultiselectFieldComponent)
  registerFieldComponent('radio', SelectFieldComponent) // Radio uses select component with single selection
  registerFieldComponent('checkbox', MultiselectFieldComponent) // Checkbox group uses multiselect
  
  // Date/time fields
  registerFieldComponent('date', DateFieldComponent)
  registerFieldComponent('datetime', DateTimeFieldComponent)
  registerFieldComponent('time', TimeFieldComponent)
  
  // Boolean field
  registerFieldComponent('boolean', BooleanFieldComponent)
  
  // Contact fields
  registerFieldComponent('email', EmailFieldComponent)
  registerFieldComponent('phone', PhoneFieldComponent)
  registerFieldComponent('url', UrlFieldComponent)
  
  // Relation fields
  registerFieldComponent('relation', RelationFieldComponent)
  
  // Advanced fields
  registerFieldComponent('file', FileFieldComponent)
  registerFieldComponent('address', AddressFieldComponent)
  registerFieldComponent('tags', TagsFieldComponent)
  registerFieldComponent('ai', AIFieldComponent)
  registerFieldComponent('ai_generated', AIFieldComponent)
  registerFieldComponent('button', ButtonFieldComponent)
  registerFieldComponent('user', UserFieldComponent)
  
  // Legacy aliases
  registerFieldComponent('image', FileFieldComponent) // Images are handled by file component
  
  // Future fields (to be implemented)
  // registerFieldComponent('computed', ComputedFieldComponent)
  // registerFieldComponent('formula', FormulaFieldComponent)
  
  console.log('🔧 Field system initialized with', getRegisteredFieldTypes().length, 'field types')
  console.log('🔧 Registered field types:', getRegisteredFieldTypes())
}

// Re-export everything from the field system
export * from './types'
export * from './field-registry'
export * from './field-renderer'
export * from './field-save-service'

// Export key utilities for easy access
export { 
  normalizeFieldValue, 
  normalizeRecordData, 
  validateFieldValue, 
  getFieldDefaultValue, 
  isFieldEmpty 
} from './field-renderer'

export {
  getSaveStrategy,
  FieldSaveService
} from './field-save-service'

// Import getRegisteredFieldTypes for the console.log above
import { getRegisteredFieldTypes } from './field-registry'

/**
 * Field system utilities for easy access
 */
export const FieldSystem = {
  initialize: initializeFieldSystem,
  // Add other utility functions as needed
}

// Auto-initialize when module is imported (can be disabled if needed)
if (typeof window !== 'undefined') {
  // Only initialize in browser environment
  initializeFieldSystem()
}