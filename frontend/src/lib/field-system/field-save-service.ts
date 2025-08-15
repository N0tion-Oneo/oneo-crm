'use client'

import { Field } from './types'
import { api } from '@/lib/api'
import { toast } from '@/hooks/use-toast'

// Save strategy function moved from deleted field-save-manager.tsx
export function getSaveStrategy(fieldType: string): 'immediate' | 'on-exit' | 'continuous' | 'on-change' | 'manual' {
  // Immediate save for choices, toggles, tags, and action buttons
  // Tags need immediate feedback for good UX when adding/removing
  if (['select', 'multiselect', 'radio', 'boolean', 'relation', 'user', 'button', 'tags'].includes(fieldType)) {
    return 'immediate'
  }
  
  // On-exit save for most input fields 
  if (['text', 'textarea', 'email', 'url', 'phone', 'address', 'number', 'integer', 'decimal', 'float', 'currency', 'percentage', 'date', 'datetime', 'time'].includes(fieldType)) {
    return 'on-exit'
  }
  
  // Continuous save for complex interactive fields (file uploads only)
  if (['file', 'image'].includes(fieldType)) {
    return 'continuous'
  }
  
  // Default to on-exit for unknown types
  return 'on-exit'
}

export interface FieldSaveParams {
  field: Field
  newValue: any
  apiEndpoint: string
  onSuccess?: (result: any) => void
  onError?: (error: any) => void
  isSharedContext?: boolean // Flag to indicate shared/public context
}

/**
 * FieldSaveService - Centralized field saving with strategy-based timing
 * 
 * Handles when and how to save field values based on field type strategies:
 * - immediate: Save instantly (select, boolean, relation, tags)
 * - on-exit: Save when user exits field (text, email, number)
 * - on-change: Debounced save (ai_generated)
 * - continuous: Save when user signals done (file uploads)
 * - manual: Save when explicitly called (file uploads)
 */
export interface SaveValidationResult {
  isValid: boolean
  errors: string[]
  warnings: string[]
  displayChanges: Array<{field: string, action: 'show' | 'hide', reason: string}>
}

export class FieldSaveService {
  private pendingChanges = new Map<string, FieldSaveParams>()
  private timers = new Map<string, NodeJS.Timeout>()
  
  // PHASE 3: REAL-TIME VALIDATION
  private validationTimers = new Map<string, NodeJS.Timeout>()
  private lastValidationResults = new Map<string, SaveValidationResult>()
  private onValidationChange?: (fieldName: string, result: SaveValidationResult) => void
  
  /**
   * Set validation change callback for real-time validation feedback
   */
  setValidationCallback(callback: (fieldName: string, result: SaveValidationResult) => void) {
    this.onValidationChange = callback
  }
  
  /**
   * PHASE 3: Real-time incremental validation as user types
   * Debounced validation that doesn't save but provides immediate feedback
   */
  private validateIncrementally(params: FieldSaveParams, debounceMs: number = 300) {
    const fieldName = params.field.name
    
    // Clear existing validation timer
    const existingTimer = this.validationTimers.get(fieldName)
    if (existingTimer) {
      clearTimeout(existingTimer)
    }
    
    // Set new debounced validation
    const timer = setTimeout(async () => {
      try {
        console.log(`🔍 PHASE 3: Incremental validation for ${fieldName}`)
        
        // Call backend validation API (without saving)
        const validationResult = await this.validateFieldValue(params)
        
        // Store result and notify callback
        this.lastValidationResults.set(fieldName, validationResult)
        
        if (this.onValidationChange) {
          this.onValidationChange(fieldName, validationResult)
        }
        
        console.log(`✅ Validation complete for ${fieldName}:`, validationResult)
        
      } catch (error) {
        console.error(`❌ Validation error for ${fieldName}:`, error)
        
        const errorResult: SaveValidationResult = {
          isValid: false,
          errors: ['Validation service unavailable'],
          warnings: [],
          displayChanges: []
        }
        
        this.lastValidationResults.set(fieldName, errorResult)
        
        if (this.onValidationChange) {
          this.onValidationChange(fieldName, errorResult)
        }
      }
    }, debounceMs)
    
    this.validationTimers.set(fieldName, timer)
  }
  
  /**
   * Call backend validation API without saving
   */
  private async validateFieldValue(params: FieldSaveParams): Promise<SaveValidationResult> {
    const { field, newValue, apiEndpoint } = params
    
    try {
      // Create validation payload (similar to save payload but with validation flag)
      const payload = {
        data: {
          [field.original_slug || field.name]: newValue
        },
        validate_only: true, // Flag to indicate validation-only request
        field_slug: field.original_slug || field.name
      }
      
      console.log(`🔍 Validation API call for ${field.name}:`, payload)
      
      // Call validation endpoint (handle trailing slash in apiEndpoint)
      const cleanEndpoint = apiEndpoint.replace(/\/$/, '')
      const response = await api.post(`${cleanEndpoint}/validate`, payload)
      
      // Parse validation response
      const result: SaveValidationResult = {
        isValid: response.data.is_valid || false,
        errors: response.data.errors || [],
        warnings: response.data.warnings || [],
        displayChanges: response.data.display_changes || []
      }
      
      return result
      
    } catch (error: any) {
      console.error(`Validation API error:`, error)
      
      // Parse error response
      if (error.response?.data?.errors) {
        return {
          isValid: false,
          errors: Object.values(error.response.data.errors).flat() as string[],
          warnings: [],
          displayChanges: []
        }
      }
      
      return {
        isValid: false,
        errors: ['Validation failed'],
        warnings: [],
        displayChanges: []
      }
    }
  }
  
  /**
   * Get last validation result for a field
   */
  getLastValidationResult(fieldName: string): SaveValidationResult | null {
    return this.lastValidationResults.get(fieldName) || null
  }
  
  /**
   * Clear validation results and timers
   */
  clearValidationState(fieldName?: string) {
    if (fieldName) {
      // Clear specific field
      const timer = this.validationTimers.get(fieldName)
      if (timer) {
        clearTimeout(timer)
        this.validationTimers.delete(fieldName)
      }
      this.lastValidationResults.delete(fieldName)
    } else {
      // Clear all
      this.validationTimers.forEach(timer => clearTimeout(timer))
      this.validationTimers.clear()
      this.lastValidationResults.clear()
    }
  }
  
  /**
   * Main entry point - called on every field change
   * Decides when to save based on field type strategy + triggers real-time validation
   */
  async onFieldChange(params: FieldSaveParams): Promise<any> {
    const strategy = getSaveStrategy(params.field.field_type)
    
    // PHASE 3: Disable incremental validation temporarily due to backend endpoint issues
    // const textBasedFields = ['text', 'textarea', 'email', 'url', 'phone', 'number', 'decimal', 'float', 'currency', 'percentage']
    // if (textBasedFields.includes(params.field.field_type)) {
    //   this.validateIncrementally(params, 300) // 300ms debounce
    // }
    
    switch (strategy) {
      case 'immediate':
        // Save right away (select, boolean, relation)
        console.log(`💾 Saving ${params.field.name} immediately`)
        return await this.saveNow(params)
        
      case 'on-exit':
        // Store locally, save when user exits field (text, email, etc.)
        this.pendingChanges.set(params.field.name, params)
        break
        
      case 'on-change':
        // Debounced save (ai_generated)
        this.debouncedSave(params, 1000)
        break
        
      case 'continuous':
        // Store locally, save when user signals done (tags)
        this.pendingChanges.set(params.field.name, params)
        break
        
      case 'manual':
        // Store locally, save when explicitly called (file uploads)
        this.pendingChanges.set(params.field.name, params)
        break
        
      default:
        console.warn(`Unknown save strategy: ${strategy}, defaulting to on-exit`)
        this.pendingChanges.set(params.field.name, params)
    }
  }
  
  /**
   * Called when user exits field (blur, enter, click away)
   * Triggers save for on-exit and continuous strategies
   */
  async onFieldExit(fieldName: string): Promise<any> {
    const pending = this.pendingChanges.get(fieldName)
    if (pending) {
      const strategy = getSaveStrategy(pending.field.field_type)
      
      console.log(`🚪 FieldSaveService.onFieldExit: ${fieldName}`, {
        strategy,
        hasPending: true
      })
      
      if (strategy === 'on-exit' || strategy === 'continuous') {
        const result = await this.saveNow(pending)
        this.pendingChanges.delete(fieldName)
        // Return both the API result and the saved value for UI updates
        return {
          apiResult: result,
          savedValue: pending.newValue,
          fieldName: fieldName
        }
      }
    } else {
      console.log(`🚪 FieldSaveService.onFieldExit: ${fieldName} - no pending changes`)
    }
  }
  
  /**
   * Called for manual saves (like file upload complete, or explicit save button)
   */
  async saveField(fieldName: string): Promise<any> {
    const pending = this.pendingChanges.get(fieldName)
    if (pending) {
      console.log(`💾 Manual save triggered for ${fieldName}`)
      const result = await this.saveNow(pending)
      this.pendingChanges.delete(fieldName)
      return result
    } else {
      console.warn(`No pending changes found for manual save: ${fieldName}`)
    }
  }
  
  /**
   * Save all pending changes (useful for form submit)
   */
  async saveAllPending(): Promise<any[]> {
    const results = []
    
    for (const [fieldName, params] of this.pendingChanges.entries()) {
      try {
        const result = await this.saveNow(params)
        results.push({ fieldName, success: true, result })
      } catch (error) {
        results.push({ fieldName, success: false, error })
      }
    }
    
    this.pendingChanges.clear()
    return results
  }
  
  /**
   * Check if there are any unsaved changes
   */
  hasUnsavedChanges(): boolean {
    return this.pendingChanges.size > 0
  }
  
  /**
   * Get list of fields with unsaved changes
   */
  getUnsavedFields(): string[] {
    return Array.from(this.pendingChanges.keys())
  }
  
  /**
   * CLEANUP: Clear all timers and pending saves
   * Call this when component unmounts to prevent memory leaks
   */
  cleanup(): void {
    console.log('🧹 Cleaning up FieldSaveService', {
      pendingChanges: this.pendingChanges.size,
      activeTimers: this.timers.size,
      validationTimers: this.validationTimers.size,
      validationResults: this.lastValidationResults.size
    })
    
    // Clear all timers
    this.timers.forEach(timer => clearTimeout(timer))
    this.timers.clear()
    
    // Clear pending changes (could save them first if desired)
    this.pendingChanges.clear()
    
    // PHASE 3: Clear validation state
    this.clearValidationState()
  }
  
  /**
   * Perform the actual save to backend
   */
  private async saveNow(params: FieldSaveParams): Promise<any> {
    try {
      
      // Use backend slug if available, otherwise use field name (same logic as auto-save transform)
      const fieldKey = params.field.original_slug || params.field.name
      const payload = { 
        data: { 
          [fieldKey]: params.newValue 
        } 
      }
      
      // Debug logging for relationship fields and button fields
      if (params.field.field_type === 'relation') {
        console.log('🔍 RELATION FIELD SAVE DEBUG:', {
          fieldName: params.field.name,
          fieldKey: fieldKey,
          newValue: params.newValue,
          valueType: typeof params.newValue,
          isArray: Array.isArray(params.newValue),
          arrayLength: Array.isArray(params.newValue) ? params.newValue.length : 'N/A',
          firstElement: Array.isArray(params.newValue) ? params.newValue[0] : params.newValue,
          apiEndpoint: params.apiEndpoint,
          payload: payload,
          isSharedContext: params.isSharedContext
        })
      }
      
      // 🔍 DEBUG: Button field save debugging
      if (params.field.field_type === 'button') {
        console.log('🔍 BUTTON FIELD SAVE DEBUG:', {
          fieldName: params.field.name,
          fieldKey: fieldKey,
          newValue: params.newValue,
          valueType: typeof params.newValue,
          isObject: typeof params.newValue === 'object',
          hasLastTriggered: params.newValue && typeof params.newValue === 'object' && 'last_triggered' in params.newValue,
          hasClickCount: params.newValue && typeof params.newValue === 'object' && 'click_count' in params.newValue,
          apiEndpoint: params.apiEndpoint,
          payload: JSON.stringify(payload, null, 2),
          isSharedContext: params.isSharedContext
        })
      }
      
      // Basic validation before sending
      if (!params.field.name) {
        throw new Error('Field name is required')
      }
      
      if (!params.apiEndpoint) {
        throw new Error('API endpoint is required')
      }
      
      const response = await api.patch(params.apiEndpoint, payload)
      
      // 🎉 Toast notification on success - special message for immediate save fields
      const fieldLabel = params.field.display_name || params.field.name
      const strategy = getSaveStrategy(params.field.field_type)
      
      if (strategy === 'immediate') {
        toast({
          title: `${fieldLabel} saved`,
          description: `Selection saved automatically`,
          duration: 2000  // Shorter duration for immediate saves
        })
      } else if (strategy === 'continuous') {
        toast({
          title: `${fieldLabel} saved`,
          description: `Changes saved successfully`,
          duration: 2000  // Shorter duration for interactive saves
        })
      } else {
        toast({
          title: 'Field saved',
          description: `${fieldLabel} saved successfully`
        })
      }
      
      // Optional callback for UI updates
      params.onSuccess?.(response.data)
      
      return response.data
      
    } catch (error: any) {
      console.error(`❌ Save failed for ${params.field.name}:`, error)
      
      // Enhanced error logging for relationship fields
      if (params.field.field_type === 'relation') {
        console.error('🔍 RELATION FIELD SAVE ERROR DETAILS:', {
          errorMessage: error.message,
          errorName: error.name,
          errorCode: error.code,
          status: error.response?.status,
          statusText: error.response?.statusText,
          responseData: error.response?.data,
          responseHeaders: error.response?.headers,
          requestData: { 
            data: { 
              [params.field.original_slug || params.field.name]: params.newValue 
            } 
          },
          requestUrl: error.config?.url,
          requestMethod: error.config?.method,
          requestHeaders: error.config?.headers,
          fullError: error
        })
      }
      
      // Show error toast
      const fieldLabel = params.field.display_name || params.field.name
      
      toast({
        title: 'Save failed',
        description: `Failed to save ${fieldLabel}: ${error.response?.data?.message || error.message || 'Unknown error'}`,
        variant: 'destructive'
      })
      
      params.onError?.(error)
      throw error
    }
  }
  
  /**
   * Debounced save - waits for user to stop typing before saving
   */
  private debouncedSave(params: FieldSaveParams, delay = 1000): void {
    const fieldName = params.field.name
    
    // Clear existing timer for this field
    if (this.timers.has(fieldName)) {
      clearTimeout(this.timers.get(fieldName)!)
    }
    
    // Set new timer
    const timer = setTimeout(async () => {
      try {
        await this.saveNow(params)
      } catch (error) {
        // Error already handled in saveNow
      } finally {
        this.timers.delete(fieldName)
      }
    }, delay)
    
    this.timers.set(fieldName, timer)
  }
}