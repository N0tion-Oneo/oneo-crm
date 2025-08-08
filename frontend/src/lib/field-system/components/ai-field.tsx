import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Brain, Zap, Loader2, AlertCircle, CheckCircle } from 'lucide-react'
import { aiApi } from '@/lib/api'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'

interface AIFieldConfig {
  // Core AI Settings - Models loaded dynamically from tenant configuration
  model?: string
  prompt?: string
  temperature?: number
  
  // OpenAI Tools Integration
  enable_tools?: boolean
  allowed_tools?: string[]
  
  // Context & Triggers
  trigger_fields?: string[]
  include_all_fields?: boolean
  excluded_fields?: string[]
  
  // Output Configuration
  output_type?: 'text' | 'number' | 'tags' | 'url' | 'json'
  is_editable?: boolean
  auto_regenerate?: boolean
  cache_duration?: number
  
  // Advanced Settings
  max_tokens?: number
  timeout?: number
  fallback_value?: any
}

interface AIJob {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  output_data?: any
  error_message?: string
  tokens_used?: number
  cost_cents?: number
  processing_time_ms?: number
}

function AIFieldInput({ 
  field, 
  value, 
  onChange, 
  onBlur,
  onKeyDown,
  error, 
  disabled, 
  autoFocus,
  className,
  context
}: FieldRenderProps) {
  const [isProcessing, setIsProcessing] = useState(false)
  const [lastJob, setLastJob] = useState<AIJob | null>(null)
  const [manualInput, setManualInput] = useState('')
  const [isManualMode, setIsManualMode] = useState(false)
  const [tenantAiConfig, setTenantAiConfig] = useState<any>(null)

  // Load tenant AI configuration on mount
  useEffect(() => {
    const loadTenantConfig = async () => {
      try {
        const response = await aiApi.jobs.tenantConfig()
        setTenantAiConfig(response.data)
      } catch (error) {
        console.error('Failed to load tenant AI config:', error)
        // Use fallback config
        setTenantAiConfig({
          default_model: 'gpt-4.1-mini',
          available_models: ['gpt-4.1-mini', 'gpt-4.1', 'o3', 'o3-mini', 'gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo']
        })
      }
    }
    loadTenantConfig()
  }, [])

  // Get AI config from field.field_config or field.config (fallback)
  const aiConfig: AIFieldConfig = field.field_config || field.config || getFieldConfig(field, 'ai_config', {})
  const {
    prompt,
    model,
    temperature = 0.3,
    max_tokens = 2000,
    auto_regenerate = true,
    trigger_fields = [],
    output_type = 'text',
    enable_tools = false,
    is_editable = true
  } = aiConfig

  // Note: recordData would come from context in real implementation
  // For now, simplified version without auto-trigger
  // useEffect(() => {
  //   if (auto_regenerate && trigger_fields.length > 0 && recordData) {
  //     const hasAllTriggerData = trigger_fields.every(fieldName => 
  //       recordData[fieldName] && recordData[fieldName].toString().trim()
  //     )
      
  //     if (hasAllTriggerData && !value && !isProcessing) {
  //       handleAIProcess()
  //     }
  //   }
  // }, [recordData, auto_trigger, trigger_fields])

  const handleAIProcess = async () => {
    if (isProcessing) return

    // Validate that a model is selected
    if (!model) {
      alert('Please select an AI model in the field configuration before processing.')
      return
    }

    setIsProcessing(true)
    setLastJob(null)

    try {
      // Use prompt-based AI processing
      const inputData = { 
        content: manualInput,
        field_name: field.name,
        field_type: field.field_type,
        prompt: prompt,
        model: model,
        temperature: temperature,
        max_tokens: max_tokens,
        output_type: output_type
      }

      // Call AI analysis endpoint
      const response = await aiApi.jobs.analyze({
        job_type: 'field_generation',
        ...inputData
      })

      setLastJob(response.data)

      // Poll for job completion
      pollJobStatus(response.data.id)

    } catch (error) {
      console.error('AI processing failed:', error)
      setIsProcessing(false)
      setLastJob({
        id: 'error',
        status: 'failed',
        error_message: error instanceof Error ? error.message : 'AI processing failed'
      })
    }
  }

  const pollJobStatus = async (jobId: string) => {
    const maxAttempts = 30 // 30 seconds max
    let attempts = 0

    const poll = async () => {
      try {
        const response = await aiApi.jobs.get(jobId)
        const job = response.data
        setLastJob(job)

        if (job.status === 'completed') {
          // Extract result and update field value
          const result = extractResultFromJob(job)
          onChange(result)
          setIsProcessing(false)
        } else if (job.status === 'failed') {
          setIsProcessing(false)
        } else if (attempts < maxAttempts) {
          attempts++
          setTimeout(poll, 1000) // Poll every second
        } else {
          setIsProcessing(false)
          setLastJob(prev => prev ? { ...prev, status: 'failed', error_message: 'Timeout' } : null)
        }
      } catch (error) {
        setIsProcessing(false)
        console.error('Failed to poll job status:', error)
      }
    }

    poll()
  }

  const extractResultFromJob = (job: AIJob): string => {
    if (!job.output_data) return ''

    const result = job.output_data.result || job.output_data

    // Handle AI field results based on output type
    if (typeof result === 'string') {
      return result
    }
    
    // Handle different result formats
    return result.content || result.text || result.value || JSON.stringify(result)
  }

  const getStatusIcon = () => {
    if (isProcessing) return <Loader2 className="h-4 w-4 animate-spin" />
    if (lastJob?.status === 'completed') return <CheckCircle className="h-4 w-4 text-green-600" />
    if (lastJob?.status === 'failed') return <AlertCircle className="h-4 w-4 text-red-600" />
    return <Brain className="h-4 w-4" />
  }

  const getStatusColor = () => {
    if (isProcessing) return 'bg-blue-100 text-blue-800'
    if (lastJob?.status === 'completed') return 'bg-green-100 text-green-800'
    if (lastJob?.status === 'failed') return 'bg-red-100 text-red-800'
    return 'bg-gray-100 text-gray-800'
  }

  return (
    <div className="space-y-4">
      {/* Model Configuration Warning */}
      {!model && (
        <div className="bg-amber-50 border border-amber-200 rounded-md p-3">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 text-amber-600" />
            <span className="text-sm text-amber-800">
              AI model not configured. Please select a model in field configuration.
            </span>
          </div>
        </div>
      )}
      
      {/* AI Field Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Brain className="h-5 w-5 text-purple-600" />
          <span className="font-medium">{field.display_name || field.name}</span>
          <Badge variant="outline" className="text-xs">
            AI Field {model ? `(${model})` : '(No Model)'}
          </Badge>
        </div>
        
        {lastJob && (
          <div className="flex items-center space-x-2">
            <Badge className={getStatusColor()}>
              {getStatusIcon()}
              <span className="ml-1">{lastJob.status}</span>
            </Badge>
            {lastJob.cost_cents && (
              <span className="text-xs text-gray-500">
                ${(lastJob.cost_cents / 100).toFixed(4)}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Current Value Display */}
      {value && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">AI Generated Result</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm bg-gray-50 p-3 rounded border">
              {value}
            </div>
            {lastJob?.tokens_used && (
              <div className="mt-2 text-xs text-gray-500">
                {lastJob.tokens_used} tokens • {lastJob.processing_time_ms}ms
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Manual Input for AI processing */}
      {!auto_regenerate && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Content to Analyze
          </label>
          <Textarea
            value={manualInput}
            onChange={(e) => setManualInput(e.target.value)}
            placeholder="Enter content for AI analysis..."
            rows={4}
            disabled={disabled || isProcessing}
          />
        </div>
      )}

      {/* AI Processing Controls */}
      <div className="flex items-center space-x-2">
                  <Button
            onClick={handleAIProcess}
            disabled={disabled || isProcessing || !model || !manualInput}
            size="sm"
            className="flex items-center space-x-2"
        >
          {getStatusIcon()}
          <span>
            {isProcessing ? 'Processing...' : 'Generate with AI'}
          </span>
        </Button>

        {!isManualMode && (
          <Button
            onClick={() => setIsManualMode(true)}
            variant="outline"
            size="sm"
            disabled={disabled}
          >
            Manual Override
          </Button>
        )}
      </div>

      {/* Manual Override Mode */}
      {isManualMode && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Manual Value
          </label>
          <Textarea
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Enter manual value..."
            rows={3}
            disabled={disabled}
          />
          <div className="mt-2 flex space-x-2">
            <Button
              onClick={() => setIsManualMode(false)}
              variant="outline"
              size="sm"
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Error Display */}
      {(error || lastJob?.error_message) && (
        <div className="text-sm text-red-600">
          {error || lastJob?.error_message}
        </div>
      )}

      {/* Field Description */}
      {field.help_text && (
        <p className="text-sm text-gray-600">{field.help_text}</p>
      )}

      {/* AI Configuration Preview */}
      {process.env.NODE_ENV === 'development' && (
        <details className="text-xs text-gray-500">
          <summary className="cursor-pointer">AI Configuration</summary>
          <div className="mt-2 bg-gray-50 p-2 rounded">
            <div>Model: {model}</div>
            <div>Temperature: {temperature}</div>
            <div>Max Tokens: {max_tokens}</div>
            {trigger_fields.length > 0 && (
              <div>Trigger Fields: {trigger_fields.join(', ')}</div>
            )}
            {prompt && (
              <div>Custom Prompt: {prompt.substring(0, 100)}...</div>
            )}
          </div>
        </details>
      )}
    </div>
  )
}

export const AIFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => (
    <AIFieldInput {...props} />
  ),

  formatValue: (value: any, field: Field, context?: string) => {
    if (value === null || value === undefined || value === '') {
      if (context === 'table') {
        return <span className="text-gray-400 italic">No AI result</span>
      }
      return ''
    }
    
    const stringValue = String(value)
    
    if (context === 'table') {
      // Truncate for table display
      return stringValue.length > 50 ? `${stringValue.substring(0, 50)}...` : stringValue
    }
    
    return stringValue
  },

  validate: (value: any, field: Field): ValidationResult => {
    // Note: Required validation handled by permission system
    // AI fields generally should not be required due to their nature

    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    return getFieldConfig(field, 'default_value', '')
  },

  isEmpty: (value: any) => !value || String(value).trim() === ''
}