/**
 * Validation helper utilities for tracking error sources
 */

export interface ValidationError {
  field: string
  message: string
  source?: string
}

export interface BackendValidationError {
  field: string
  message: string
  source: 'backend' | 'frontend'
  validator_type?: string
}

/**
 * Parse validation error to identify source
 */
export function parseValidationError(errorMessage: string): {
  message: string
  source: string
  isBackend: boolean
} {
  // Check for backend validator prefixes
  const backendPrefixes = [
    'BACKEND_VALIDATOR',
    'STORAGE_CONSTRAINT', 
    'BUSINESS_RULES',
    'NUMBER_FIELD_VALIDATOR',
    'EMAIL_FIELD_VALIDATOR',
    'SELECT_FIELD_VALIDATOR',
    'DATE_FIELD_VALIDATOR',
    'TEXT_FIELD_VALIDATOR',
    'PHONE_FIELD_VALIDATOR',
    'URL_FIELD_VALIDATOR',
    'FILE_FIELD_VALIDATOR',
    'TAGS_FIELD_VALIDATOR',
    'AI_GENERATED_FIELD_VALIDATOR',
    'RELATION_FIELD_VALIDATOR',
    'ADDRESS_FIELD_VALIDATOR',
    'BUTTON_FIELD_VALIDATOR',
    'RECORD_DATA_FIELD_VALIDATOR'
  ]

  for (const prefix of backendPrefixes) {
    if (errorMessage.startsWith(`[${prefix}]`)) {
      return {
        message: errorMessage.replace(`[${prefix}] `, ''),
        source: prefix.toLowerCase(),
        isBackend: true
      }
    }
  }

  // If no backend prefix found, assume frontend validation
  return {
    message: errorMessage,
    source: 'frontend_validator',
    isBackend: false
  }
}

/**
 * Format error message with clear source indicator for debugging
 */
export function formatErrorForDebug(errorMessage: string): string {
  const parsed = parseValidationError(errorMessage)
  
  if (parsed.isBackend) {
    return `🔧 Backend: ${parsed.message} (${parsed.source})`
  } else {
    return `🎨 Frontend: ${parsed.message}`
  }
}

/**
 * Check if error is from backend validation
 */
export function isBackendValidationError(errorMessage: string): boolean {
  return parseValidationError(errorMessage).isBackend
}

/**
 * Extract clean error message without source prefixes
 */
export function getCleanErrorMessage(errorMessage: string): string {
  return parseValidationError(errorMessage).message
}

/**
 * Console logging helper for validation debugging
 */
export function logValidationError(field: string, error: string, context?: string) {
  const parsed = parseValidationError(error)
  const prefix = parsed.isBackend ? '🔧 BACKEND' : '🎨 FRONTEND'
  const contextStr = context ? ` [${context}]` : ''
  
  console.log(`${prefix} Validation Error${contextStr}:`, {
    field,
    message: parsed.message,
    source: parsed.source,
    originalError: error
  })
}