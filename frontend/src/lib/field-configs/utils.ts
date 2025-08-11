import { FieldTypeConfig } from './types'

/**
 * Format enum values for display (capitalize and handle special cases)
 */
export function formatEnumLabel(key: string, value: string): string {
  const enumLabels: Record<string, Record<string, string>> = {
    format: {
      'integer': 'Whole Numbers',
      'decimal': 'Decimal Numbers', 
      'currency': 'Currency',
      'percentage': 'Percentage',
      'auto_increment': 'Auto-Increment'
    },
    data_type: {
      'timestamp': 'Date & Time',
      'date': 'Date Only',
      'time': 'Time Only'
    },
    model: {
      'gpt-4.1': 'GPT-4.1 (Most Capable)',
      'gpt-4.1-mini': 'GPT-4.1 Mini (Fast & Cost-Effective)',
      'o3': 'O3 (Advanced Reasoning)',
      'o3-mini': 'O3 Mini (Fast Reasoning)',
      'gpt-4o': 'GPT-4o (Multimodal)',
      'gpt-3.5-turbo': 'GPT-3.5 Turbo (Legacy)'
    }
  }

  return enumLabels[key]?.[value] || value.charAt(0).toUpperCase() + value.slice(1)
}

/**
 * Check if a field type supports validation rules
 */
export function supportsValidation(fieldTypeConfig: FieldTypeConfig): boolean {
  return fieldTypeConfig.supports_validation
}

/**
 * Check if a field type is computed (AI, formula, etc.)
 */
export function isComputedField(fieldTypeConfig: FieldTypeConfig): boolean {
  return fieldTypeConfig.is_computed
}

/**
 * Get field type category color for UI display
 */
export function getCategoryColor(category: string): string {
  const colors: Record<string, string> = {
    basic: 'bg-blue-50 text-blue-700 border-blue-200',
    selection: 'bg-green-50 text-green-700 border-green-200',
    datetime: 'bg-purple-50 text-purple-700 border-purple-200',
    advanced: 'bg-orange-50 text-orange-700 border-orange-200',
    system: 'bg-gray-50 text-gray-700 border-gray-200'
  }
  
  return colors[category] || colors.basic
}

// Memoization cache for validation results
const validationCache = new Map<string, string[]>()

/**
 * Create a cache key for validation memoization
 */
function createValidationCacheKey(fieldType: string, config: Record<string, any>, aiConfig?: Record<string, any>): string {
  const configStr = JSON.stringify(config, Object.keys(config).sort())
  const aiConfigStr = aiConfig ? JSON.stringify(aiConfig, Object.keys(aiConfig).sort()) : ''
  return `${fieldType}:${configStr}:${aiConfigStr}`
}

/**
 * Validate configuration values based on field type (memoized for performance)
 */
export function validateFieldConfig(fieldType: string, config: Record<string, any>, aiConfig?: Record<string, any>): string[] {
  // Check cache first
  const cacheKey = createValidationCacheKey(fieldType, config, aiConfig)
  if (validationCache.has(cacheKey)) {
    return validationCache.get(cacheKey)!
  }

  const errors: string[] = []

  switch (fieldType) {
    case 'relation':
      if (!config.target_pipeline_id) {
        errors.push('Target pipeline is required for relation fields')
      }
      if (!config.display_field) {
        errors.push('Display field is required for relation fields')
      }
      break

    case 'ai_generated':
    case 'ai_field':
    case 'ai':
      // Check for prompt in both config and aiConfig locations
      const prompt = config.prompt || aiConfig?.prompt || ''
      if (!prompt || prompt.trim().length === 0) {
        errors.push('AI prompt is required for AI generated fields')
      }
      if (prompt && prompt.trim().length < 10) {
        errors.push('AI prompt must be at least 10 characters long')
      }
      break

    case 'user':
      if (config.max_users && config.max_users < 1) {
        errors.push('Maximum users must be at least 1 if specified')
      }
      if (config.allowed_roles && config.allowed_roles.length === 0) {
        errors.push('At least one role must be allowed')
      }
      break

    case 'number':
      if (config.min_value !== undefined && config.max_value !== undefined) {
        if (config.min_value >= config.max_value) {
          errors.push('Minimum value must be less than maximum value')
        }
      }
      break

    case 'select':
    case 'multiselect':
      if (!config.options || config.options.length === 0) {
        errors.push('At least one option is required for select fields')
      }
      break
  }

  // Cache the result (limit cache size to prevent memory leaks)
  if (validationCache.size > 100) {
    const firstKey = validationCache.keys().next().value
    if (firstKey) {
      validationCache.delete(firstKey)
    }
  }
  validationCache.set(cacheKey, errors)

  return errors
}

/**
 * Get default configuration for a field type
 */
export function getDefaultFieldConfig(fieldType: string): Record<string, any> {
  const defaults: Record<string, Record<string, any>> = {
    text: {
      case_sensitive: true,
      auto_format: false
    },
    
    number: {
      format: 'integer',
      allow_negative: true
    },
    
    user: {
      allow_multiple: true,
      default_role: 'assigned',
      allowed_roles: ['assigned', 'owner', 'collaborator', 'reviewer'],
      show_role_selector: true,
      require_role_selection: false,
      show_user_avatars: true
    },
    
    phone: {
      require_country_code: true,
      format_display: true,
      auto_format_input: true,
      display_format: 'international'
    },
    
    ai_generated: {
      model: '',
      temperature: 0.3,
      output_type: 'text',
      enable_tools: false,
      allowed_tools: []
    },
    
    boolean: {
      default_value: false,
      display_as: 'checkbox'
    }
  }

  return defaults[fieldType] || {}
}

/**
 * Merge configuration with defaults, preserving existing values
 */
export function mergeWithDefaults(fieldType: string, config: Record<string, any>): Record<string, any> {
  const defaults = getDefaultFieldConfig(fieldType)
  return { ...defaults, ...config }
}