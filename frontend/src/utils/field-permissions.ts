import { User } from '@/types/auth'

export interface ConditionalRule {
  field: string
  condition: string
  value: any
}

export interface ConditionalRules {
  show_when?: ConditionalRule[]
  hide_when?: ConditionalRule[]
  require_when?: ConditionalRule[]
}

export interface UserVisibility {
  visible: boolean
  editable: boolean
  visibility_level?: 'visible' | 'hidden' | 'conditional' | 'readonly'
  required?: boolean
  default_value?: any
  conditional_rules?: ConditionalRules
}

export interface BusinessRules {
  stage_requirements?: Record<string, { 
    required: boolean
    block_transitions?: boolean
    show_warnings?: boolean
    warning_message?: string
  }>
  user_visibility?: Record<string, UserVisibility>
  conditional_rules?: ConditionalRules
}

export interface FieldWithPermissions {
  id: string
  name: string
  display_name?: string
  field_type: string
  is_required?: boolean
  is_visible_in_list?: boolean
  is_visible_in_detail?: boolean
  display_order: number
  business_rules?: BusinessRules
}

export interface FieldPermissionResult {
  visible: boolean
  editable: boolean
  required: boolean
  readonly: boolean
  conditionallyHidden: boolean
  reasonHidden?: string
}

/**
 * Evaluate a single conditional rule against record data and user context
 */
export const evaluateCondition = (
  rule: ConditionalRule, 
  recordData: Record<string, any>, 
  userTypeSlug?: string
): boolean => {
  let fieldValue: any
  
  // Special handling for user_type field
  if (rule.field === 'user_type') {
    fieldValue = userTypeSlug
  } else {
    fieldValue = recordData[rule.field]
  }
  
  switch (rule.condition) {
    case 'equals':
      return fieldValue === rule.value
    case 'not_equals':
      return fieldValue !== rule.value
    case 'contains':
      return String(fieldValue || '').includes(String(rule.value))
    case 'not_contains':
      return !String(fieldValue || '').includes(String(rule.value))
    case 'greater_than':
      return Number(fieldValue) > Number(rule.value)
    case 'less_than':
      return Number(fieldValue) < Number(rule.value)
    case 'is_empty':
      return !fieldValue || fieldValue === '' || fieldValue === null || fieldValue === undefined
    case 'is_not_empty':
      return fieldValue && fieldValue !== '' && fieldValue !== null && fieldValue !== undefined
    case 'starts_with':
      return String(fieldValue || '').startsWith(String(rule.value))
    case 'ends_with':
      return String(fieldValue || '').endsWith(String(rule.value))
    default:
      console.warn(`Unknown condition operator: ${rule.condition}`)
      return false
  }
}

/**
 * Evaluate conditional rules for field visibility
 */
export const evaluateConditionalRules = (
  conditionalRules: ConditionalRules | undefined,
  recordData: Record<string, any>,
  userTypeSlug?: string
): { visible: boolean; required: boolean; reasonHidden?: string } => {
  if (!conditionalRules) {
    return { visible: true, required: false }
  }

  // Evaluate show_when conditions (ALL must be true)
  const showWhen = conditionalRules.show_when || []
  const shouldShow = showWhen.length === 0 || showWhen.every(rule => 
    evaluateCondition(rule, recordData, userTypeSlug)
  )

  // Evaluate hide_when conditions (ANY being true hides the field)
  const hideWhen = conditionalRules.hide_when || []
  const shouldHide = hideWhen.some(rule => 
    evaluateCondition(rule, recordData, userTypeSlug)
  )

  // Evaluate require_when conditions (ANY being true makes field required)
  const requireWhen = conditionalRules.require_when || []
  const shouldRequire = requireWhen.some(rule => 
    evaluateCondition(rule, recordData, userTypeSlug)
  )

  let reasonHidden: string | undefined
  if (!shouldShow && showWhen.length > 0) {
    reasonHidden = 'Show conditions not met'
  } else if (shouldHide) {
    reasonHidden = 'Hide condition triggered'
  }

  return {
    visible: shouldShow && !shouldHide,
    required: shouldRequire,
    reasonHidden
  }
}


/**
 * Evaluate field permissions for a specific user and context
 */
export const evaluateFieldPermissions = (
  field: FieldWithPermissions,
  user: User | null,
  recordData: Record<string, any> = {},
  context: 'list' | 'detail' | 'form' = 'detail'
): FieldPermissionResult => {
  // Default result if no user
  if (!user) {
    return {
      visible: false,
      editable: false,
      required: false,
      readonly: true,
      conditionallyHidden: false,
      reasonHidden: 'No user logged in'
    }
  }

  const userTypeSlug = user.userType?.slug
  if (!userTypeSlug) {
    return {
      visible: false,
      editable: false,
      required: false,
      readonly: true,
      conditionallyHidden: false,
      reasonHidden: 'No user type assigned'
    }
  }

  // Get user-specific visibility rules
  const userVisibility = field.business_rules?.user_visibility?.[userTypeSlug]
  const baseVisible = userVisibility?.visible ?? true
  const baseEditable = userVisibility?.editable ?? true

  // Check basic visibility first
  if (!baseVisible) {
    return {
      visible: false,
      editable: false,
      required: false,
      readonly: true,
      conditionallyHidden: false,
      reasonHidden: `Hidden for ${user.userType.name} users`
    }
  }

  // Check context-specific visibility
  let contextVisible = true
  switch (context) {
    case 'list':
      contextVisible = field.is_visible_in_list !== false
      break
    case 'detail':
      contextVisible = field.is_visible_in_detail !== false
      break
    case 'form':
      // For forms, use detail visibility as default
      contextVisible = field.is_visible_in_detail !== false
      break
  }

  if (!contextVisible) {
    return {
      visible: false,
      editable: false,
      required: false,
      readonly: true,
      conditionallyHidden: false,
      reasonHidden: `Hidden in ${context} view`
    }
  }

  // Evaluate conditional rules (field-level)
  const fieldConditionalResult = evaluateConditionalRules(
    field.business_rules?.conditional_rules,
    recordData,
    userTypeSlug
  )

  // Evaluate user-specific conditional rules (deprecated but support legacy)
  const userConditionalResult = evaluateConditionalRules(
    userVisibility?.conditional_rules,
    recordData,
    userTypeSlug
  )

  // Combine conditional results (field-level and user-level)
  const conditionalVisible = fieldConditionalResult.visible && userConditionalResult.visible
  const conditionalRequired = fieldConditionalResult.required || userConditionalResult.required
  const conditionallyHidden = !conditionalVisible
  
  let reasonHidden: string | undefined
  if (!conditionalVisible) {
    reasonHidden = fieldConditionalResult.reasonHidden || userConditionalResult.reasonHidden
  }

  // Final visibility
  const finalVisible = baseVisible && contextVisible && conditionalVisible

  // Determine if field is readonly
  const readonly = !baseEditable || userVisibility?.visibility_level === 'readonly'

  // Determine if field is required
  const baseRequired = field.is_required || false
  const userRequired = userVisibility?.required || false
  const finalRequired = baseRequired || userRequired || conditionalRequired

  return {
    visible: finalVisible,
    editable: baseEditable && finalVisible,
    required: finalRequired && finalVisible,
    readonly: readonly || !finalVisible,
    conditionallyHidden,
    reasonHidden: finalVisible ? undefined : reasonHidden
  }
}

/**
 * Filter fields based on permissions for a specific context
 */
export const filterFieldsByPermissions = (
  fields: FieldWithPermissions[],
  user: User | null,
  recordData: Record<string, any> = {},
  context: 'list' | 'detail' | 'form' = 'detail'
): FieldWithPermissions[] => {
  return fields.filter(field => {
    const permissions = evaluateFieldPermissions(field, user, recordData, context)
    return permissions.visible
  })
}

/**
 * Get field permissions map for all fields
 */
export const getFieldPermissionsMap = (
  fields: FieldWithPermissions[],
  user: User | null,
  recordData: Record<string, any> = {},
  context: 'list' | 'detail' | 'form' = 'detail'
): Record<string, FieldPermissionResult> => {
  const permissionsMap: Record<string, FieldPermissionResult> = {}
  
  fields.forEach(field => {
    permissionsMap[field.name] = evaluateFieldPermissions(field, user, recordData, context)
  })
  
  return permissionsMap
}

/**
 * Sort fields by display order, respecting permissions
 */
export const sortFieldsByDisplayOrder = (
  fields: FieldWithPermissions[],
  user: User | null,
  recordData: Record<string, any> = {},
  context: 'list' | 'detail' | 'form' = 'detail'
): FieldWithPermissions[] => {
  const visibleFields = filterFieldsByPermissions(fields, user, recordData, context)
  return visibleFields.sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
}