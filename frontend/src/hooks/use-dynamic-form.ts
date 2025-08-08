'use client'

import { useState, useCallback } from 'react'
import { api } from '@/lib/api'

interface DynamicFormSchema {
  pipeline_id: number
  pipeline_name: string
  form_mode: string
  target_stage?: string
  metadata: {
    total_fields: number
    required_fields: number
    visible_fields: number
  }
  fields: Array<{
    id: number
    slug: string
    name: string
    type: string
    display_name: string
    help_text: string
    placeholder: string
    // is_required removed - handled by conditional rules
    is_visible: boolean
    is_readonly: boolean
    display_order: number
    field_config: Record<string, any>
    form_validation_rules: Record<string, any>
    business_rules?: Record<string, any>
    default_value: any
    current_value: any
  }>
}

interface UseDynamicFormOptions {
  pipelineId?: string
  pipelineSlug?: string
  formType: 'internal_full' | 'public_filtered' | 'stage_internal' | 'stage_public' | 'shared_record'
  stage?: string
  recordId?: string
}

export function useDynamicForm({
  pipelineId,
  pipelineSlug,
  formType,
  stage,
  recordId
}: UseDynamicFormOptions) {
  const [formSchema, setFormSchema] = useState<DynamicFormSchema | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadSchema = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      
      let endpoint = ''
      
      // Build endpoint based on form type
      switch (formType) {
        case 'internal_full':
          endpoint = `/api/pipelines/${pipelineId}/forms/internal/`
          break
        case 'public_filtered':
          endpoint = `/api/public-forms/${pipelineSlug || pipelineId}/`
          break
        case 'stage_internal':
          endpoint = `/api/pipelines/${pipelineId}/forms/stage/${stage}/internal/`
          break
        case 'stage_public':
          endpoint = `/api/public-forms/${pipelineSlug || pipelineId}/stage/${stage}/`
          break
        case 'shared_record':
          endpoint = `/api/pipelines/${pipelineId}/records/${recordId}/share/`
          break
      }
      
      const response = await api.get(endpoint)
      setFormSchema(response.data)
      
    } catch (err: any) {
      console.error('Failed to load form schema:', err)
      const errorMessage = err.response?.data?.error || err.message || 'Failed to load form'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [pipelineId, pipelineSlug, formType, stage, recordId])

  const submitForm = useCallback(async (formData: Record<string, any>) => {
    try {
      const submitData = {
        form_mode: formType,
        stage,
        record_id: recordId,
        data: formData
      }
      
      let endpoint = ''
      if (formType.includes('public')) {
        endpoint = `/api/public-forms/${pipelineSlug || pipelineId}/submit/`
      } else {
        endpoint = `/api/pipelines/${pipelineId}/forms/submit/`
      }
      
      const response = await api.post(endpoint, submitData)
      return response.data
      
    } catch (err: any) {
      console.error('Form submission failed:', err)
      const errorMessage = err.response?.data?.error || err.message || 'Form submission failed'
      throw new Error(errorMessage)
    }
  }, [pipelineId, pipelineSlug, formType, stage, recordId])

  return {
    formSchema,
    loading,
    error,
    loadSchema,
    submitForm
  }
}