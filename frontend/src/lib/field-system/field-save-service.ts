'use client'

import { Field } from './types'
import { api } from '@/lib/api'
import { toast } from '@/hooks/use-toast'

// Save strategy function moved from deleted field-save-manager.tsx
export function getSaveStrategy(fieldType: string): 'immediate' | 'on-exit' | 'continuous' {
  // Immediate save for choices and toggles
  if (['select', 'multiselect', 'radio', 'boolean', 'relation'].includes(fieldType)) {
    return 'immediate'
  }
  
  // On-exit save for most input fields 
  if (['text', 'textarea', 'email', 'url', 'phone', 'address', 'number', 'integer', 'decimal', 'float', 'currency', 'percentage', 'date', 'datetime', 'time'].includes(fieldType)) {
    return 'on-exit'
  }
  
  // Continuous save for complex interactive fields
  if (['tags', 'file', 'image'].includes(fieldType)) {
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
}

/**
 * FieldSaveService - Centralized field saving with strategy-based timing
 * 
 * Handles when and how to save field values based on field type strategies:
 * - immediate: Save instantly (select, boolean, relation)
 * - on-exit: Save when user exits field (text, email, number)
 * - on-change: Debounced save (ai_generated)
 * - continuous: Save when user signals done (tags)
 * - manual: Save when explicitly called (file uploads)
 */
export class FieldSaveService {
  private pendingChanges = new Map<string, FieldSaveParams>()
  private timers = new Map<string, NodeJS.Timeout>()
  
  /**
   * Main entry point - called on every field change
   * Decides when to save based on field type strategy
   */
  async onFieldChange(params: FieldSaveParams): Promise<any> {
    const strategy = getSaveStrategy(params.field.field_type)
    
    console.log(`🎯 FieldSaveService.onFieldChange: ${params.field.name}`, {
      strategy,
      newValue: params.newValue,
      fieldType: params.field.field_type
    })
    
    switch (strategy) {
      case 'immediate':
        // Save right away (select, boolean, relation)
        return await this.saveNow(params)
        
      case 'on-exit':
        // Store locally, save when user exits field (text, email, etc.)
        this.pendingChanges.set(params.field.name, params)
        console.log(`📝 Stored pending change for ${params.field.name}`)
        break
        
      case 'on-change':
        // Debounced save (ai_generated)
        this.debouncedSave(params, 1000)
        break
        
      case 'continuous':
        // Store locally, save when user signals done (tags)
        this.pendingChanges.set(params.field.name, params)
        console.log(`🏷️ Stored continuous change for ${params.field.name}`)
        break
        
      case 'manual':
        // Store locally, save when explicitly called (file uploads)
        this.pendingChanges.set(params.field.name, params)
        console.log(`📁 Stored manual change for ${params.field.name}`)
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
      activeTimers: this.timers.size
    })
    
    // Clear all timers
    this.timers.forEach(timer => clearTimeout(timer))
    this.timers.clear()
    
    // Clear pending changes (could save them first if desired)
    this.pendingChanges.clear()
  }
  
  /**
   * Perform the actual save to backend
   */
  private async saveNow(params: FieldSaveParams): Promise<any> {
    try {
      const payload = { [params.field.name]: params.newValue }
      
      console.log(`💾 Saving ${params.field.name}:`, {
        fieldType: params.field.field_type,
        fieldName: params.field.name,
        value: params.newValue,
        valueType: typeof params.newValue,
        endpoint: params.apiEndpoint,
        payload: payload
      })
      
      // Basic validation before sending
      if (!params.field.name) {
        throw new Error('Field name is required')
      }
      
      if (!params.apiEndpoint) {
        throw new Error('API endpoint is required')
      }
      
      // Basic save logging for debugging
      console.log(`💾 Saving ${params.field.name}:`, {
        fieldType: params.field.field_type,
        fieldName: params.field.name,
        value: params.newValue,
        valueType: typeof params.newValue,
        endpoint: params.apiEndpoint,
        payload: payload
      })
      
      // Send field directly - DynamicRecordSerializer maps it to data.field_name automatically
      // This avoids overwriting the entire data object and preserves other fields
      const response = await api.patch(params.apiEndpoint, payload)
      
      // 🎉 Toast notification on success
      const fieldLabel = params.field.display_name || params.field.name
      toast({
        title: 'Field saved',
        description: `${fieldLabel} saved successfully`
      })
      
      // Optional callback for UI updates
      params.onSuccess?.(response.data)
      
      console.log(`✅ Save successful for ${params.field.name}`)
      return response.data
      
    } catch (error: any) {
      console.error(`❌ Save failed for ${params.field.name}:`, error)
      console.error(`❌ Error response data:`, error.response?.data)
      console.error(`❌ Error status:`, error.response?.status)
      console.error(`❌ Request payload was:`, {
        [params.field.name]: params.newValue
      })
      
      // Deep log the error data structure  
      if (error.response?.data) {
        console.error(`❌ Full error structure:`, JSON.stringify(error.response.data, null, 2))
        console.error(`❌ Raw error data:`, error.response.data)
        
        // Force display error details if it's an object
        if (typeof error.response.data === 'object') {
          console.error(`❌ Error object properties:`, Object.keys(error.response.data))
          for (const [key, value] of Object.entries(error.response.data)) {
            console.error(`❌ ${key}:`, value)
          }
        }
      }
      
      // 🚨 Toast notification on error  
      const fieldLabel = params.field.display_name || params.field.name
      let errorMessage = 'Unknown error'
      
      if (error.response?.data) {
        // Try to extract meaningful error message
        const errorData = error.response.data
        if (typeof errorData === 'string') {
          errorMessage = errorData
        } else if (errorData.detail) {
          errorMessage = errorData.detail
        } else if (errorData.message) {
          errorMessage = errorData.message
        } else if (errorData.error) {
          errorMessage = errorData.error
        } else if (errorData[params.field.name]) {
          // Field-specific validation error
          const fieldErrors = errorData[params.field.name]
          errorMessage = Array.isArray(fieldErrors) ? fieldErrors.join(', ') : fieldErrors
        } else {
          errorMessage = JSON.stringify(errorData)
        }
      } else {
        errorMessage = error.message || 'Network error'
      }
      
      toast({
        title: 'Save failed',
        description: `Failed to save ${fieldLabel}: ${errorMessage}`,
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
    
    console.log(`⏱️ Setting up debounced save for ${fieldName} (${delay}ms)`)
    
    // Clear existing timer for this field
    if (this.timers.has(fieldName)) {
      clearTimeout(this.timers.get(fieldName)!)
      console.log(`⏱️ Cleared existing timer for ${fieldName}`)
    }
    
    // Set new timer
    const timer = setTimeout(async () => {
      console.log(`⏰ Debounced save timer fired for ${fieldName}`)
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