'use client'

import { useState, useEffect } from 'react'
import { aiApi } from '@/lib/api'
import {
  Checkbox,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Slider,
  Textarea,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
  Button
} from '@/components/ui'
import { ChevronDown, HelpCircle } from 'lucide-react'

interface AIFieldConfigProps {
  config: Record<string, any>
  aiConfig: Record<string, any>
  onConfigChange: (config: Record<string, any>) => void
  onAiConfigChange: (aiConfig: Record<string, any>) => void
  availableFields: { id: string; name: string; display_name: string; field_type: string }[]
}

export function AIFieldConfig({
  config,
  aiConfig,
  onConfigChange,
  onAiConfigChange,
  availableFields
}: AIFieldConfigProps) {
  const [tenantAiConfig, setTenantAiConfig] = useState<any>(null)
  const [loadingAiConfig, setLoadingAiConfig] = useState(false)
  const [aiConfigError, setAiConfigError] = useState<string | null>(null)
  const [showAdvancedTools, setShowAdvancedTools] = useState(false)

  // Load tenant AI configuration
  useEffect(() => {
    const loadTenantAiConfig = async () => {
      try {
        setLoadingAiConfig(true)
        setAiConfigError(null)
        const response = await aiApi.jobs.tenantConfig()
        setTenantAiConfig(response.data)
      } catch (error: any) {
        console.error('Failed to load tenant AI configuration:', error)
        setAiConfigError(error.response?.data?.detail || 'Failed to load AI configuration')
      } finally {
        setLoadingAiConfig(false)
      }
    }

    loadTenantAiConfig()
  }, [])

  const updateAiConfig = (key: string, value: any) => {
    onAiConfigChange({ ...aiConfig, [key]: value })
  }

  const availableTools = [
    { key: 'web_search', label: 'Web Search', description: 'Allow AI to search the internet for current information' },
    { key: 'code_interpreter', label: 'Code Interpreter', description: 'Enable code execution and data analysis capabilities' },
    { key: 'file_reader', label: 'File Reader', description: 'Allow reading and analyzing attached files' },
    { key: 'dalle', label: 'DALL-E Image Generation', description: 'Generate images based on prompts' }
  ]

  const outputTypes = [
    { value: 'text', label: 'Text' },
    { value: 'number', label: 'Number' },
    { value: 'tags', label: 'Tags' },
    { value: 'url', label: 'URL' },
    { value: 'json', label: 'JSON Object' }
  ]

  return (
    <TooltipProvider>
      <div className="space-y-6">
        {/* AI Prompt Template */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Label htmlFor="ai-prompt" className="text-sm font-medium text-gray-900 dark:text-white">
              AI Prompt Template *
            </Label>
            <Tooltip>
              <TooltipTrigger asChild>
                <HelpCircle className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent>
                <p className="max-w-xs">Write a prompt that describes what you want the AI to generate. Use field references to include data from other fields.</p>
              </TooltipContent>
            </Tooltip>
          </div>
          <Textarea
            id="ai-prompt"
            value={aiConfig.prompt || ''}
            onChange={(e) => updateAiConfig('prompt', e.target.value)}
            placeholder="Enter your AI prompt template..."
            rows={4}
            className="resize-none"
          />
          
          {/* Field Reference Help */}
          <div className="text-xs text-muted-foreground p-3 bg-muted/50 rounded-md">
            <p className="font-medium mb-2">Use field references in your prompt:</p>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              <div><code className="bg-background px-1 rounded">{'{*}'}</code> - Include all fields</div>
              {availableFields.length > 0 ? (
                availableFields.map(field => (
                  <div key={field.id}>
                    <code className="bg-background px-1 rounded">{`{${field.name}}`}</code> - {field.display_name} ({field.field_type})
                  </div>
                ))
              ) : (
                <div><code className="bg-background px-1 rounded">{'{field_name}'}</code> - Reference other fields by name</div>
              )}
            </div>
          </div>
        </div>

        {/* AI Model Selection */}
        <div className="space-y-2">
          <Label htmlFor="ai-model">AI Model</Label>
          {loadingAiConfig ? (
            <div className="p-3 text-sm border rounded-md bg-muted text-gray-700 dark:text-gray-300">
              Loading tenant AI configuration...
            </div>
          ) : aiConfigError ? (
            <div className="p-3 text-sm border border-destructive rounded-md bg-destructive/10 text-destructive">
              {aiConfigError}
            </div>
          ) : (
            <>
              <Select
                value={aiConfig.model || ''}
                onValueChange={(value) => updateAiConfig('model', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select AI model..." />
                </SelectTrigger>
                <SelectContent>
                  {tenantAiConfig?.available_models?.map((model: string) => (
                    <SelectItem key={model} value={model}>
                      {model === tenantAiConfig.default_model ? `${model} (Recommended)` : model}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {tenantAiConfig && (
                <p className="text-xs text-muted-foreground">
                  Select the AI model that best fits your use case. Recommended: {tenantAiConfig.default_model}
                </p>
              )}
            </>
          )}
        </div>

        {/* Creativity Level */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Label>Creativity Level</Label>
            <Tooltip>
              <TooltipTrigger asChild>
                <HelpCircle className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent>
                <p>Lower values make the AI more focused and deterministic. Higher values increase creativity and variation.</p>
              </TooltipContent>
            </Tooltip>
          </div>
          <div className="space-y-2">
            <Slider
              value={[aiConfig.temperature || 0.3]}
              onValueChange={(value) => updateAiConfig('temperature', value[0])}
              min={0}
              max={1}
              step={0.1}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Precise (0)</span>
              <span className="font-medium">{aiConfig.temperature || 0.3}</span>
              <span>Creative (1)</span>
            </div>
          </div>
        </div>

        {/* Output Type */}
        <div className="space-y-2">
          <Label htmlFor="output-type">Output Type</Label>
          <Select
            value={aiConfig.output_type || 'text'}
            onValueChange={(value) => updateAiConfig('output_type', value)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {outputTypes.map((type) => (
                <SelectItem key={type.value} value={type.value}>
                  {type.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Enable AI Tools */}
        <div className="flex items-center space-x-2">
          <Checkbox
            id="enable-tools"
            checked={aiConfig.enable_tools || false}
            onCheckedChange={(checked) => updateAiConfig('enable_tools', checked)}
          />
          <Label htmlFor="enable-tools" className="text-sm text-gray-700 dark:text-gray-300">
            Enable AI tools (web search, code interpreter, etc.)
          </Label>
        </div>

        {/* AI Tools Configuration */}
        {aiConfig.enable_tools && (
          <div className="space-y-3">
            <Label className="text-sm font-medium text-gray-900 dark:text-white">Allowed Tools</Label>
            <div className="space-y-3">
              {availableTools.map((tool) => (
                <div key={tool.key} className="flex items-start space-x-3">
                  <Checkbox
                    id={`tool-${tool.key}`}
                    checked={(aiConfig.allowed_tools || []).includes(tool.key)}
                    onCheckedChange={(checked) => {
                      const currentTools = aiConfig.allowed_tools || []
                      const newTools = checked
                        ? [...currentTools, tool.key]
                        : currentTools.filter((t: string) => t !== tool.key)
                      updateAiConfig('allowed_tools', newTools)
                    }}
                  />
                  <div className="space-y-1">
                    <Label htmlFor={`tool-${tool.key}`} className="text-sm font-normal text-gray-700 dark:text-gray-300">
                      {tool.label}
                    </Label>
                    <p className="text-xs text-muted-foreground">{tool.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Advanced Configuration */}
        <Collapsible>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-2 p-0 h-auto font-normal">
              <ChevronDown className="h-4 w-4" />
              Advanced Configuration
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="space-y-4 mt-4">
            {/* Trigger Fields */}
            <div className="space-y-3">
              <div>
                <Label className="text-sm font-medium text-gray-900 dark:text-white">Trigger Fields (Optional)</Label>
                <p className="text-xs text-muted-foreground mt-1">
                  AI will regenerate when these fields change. Leave empty to trigger on any field change.
                </p>
              </div>
              <div className="space-y-2 max-h-32 overflow-y-auto border rounded-md p-3">
                {availableFields.length > 0 ? (
                  availableFields.map((field) => (
                    <div key={field.id} className="flex items-center space-x-2">
                      <Checkbox
                        id={`trigger-${field.id}`}
                        checked={(aiConfig.trigger_fields || []).includes(field.name)}
                        onCheckedChange={(checked) => {
                          const currentFields = aiConfig.trigger_fields || []
                          const newFields = checked
                            ? [...currentFields, field.name]
                            : currentFields.filter((f: string) => f !== field.name)
                          updateAiConfig('trigger_fields', newFields)
                        }}
                      />
                      <Label htmlFor={`trigger-${field.id}`} className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        {field.display_name} ({field.field_type})
                      </Label>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground italic">
                    Add other fields to the pipeline first to configure triggers
                  </p>
                )}
              </div>
            </div>

            {/* Excluded Fields */}
            <div className="space-y-3">
              <div>
                <Label className="text-sm font-medium text-gray-900 dark:text-white">Excluded Fields (Optional)</Label>
                <p className="text-xs text-muted-foreground mt-1">
                  Hide these fields from the AI context for privacy or security.
                </p>
              </div>
              <div className="space-y-2 max-h-32 overflow-y-auto border rounded-md p-3">
                {availableFields.length > 0 ? (
                  availableFields.map((field) => (
                    <div key={field.id} className="flex items-center space-x-2">
                      <Checkbox
                        id={`exclude-${field.id}`}
                        checked={(aiConfig.excluded_fields || []).includes(field.name)}
                        onCheckedChange={(checked) => {
                          const currentFields = aiConfig.excluded_fields || []
                          const newFields = checked
                            ? [...currentFields, field.name]
                            : currentFields.filter((f: string) => f !== field.name)
                          updateAiConfig('excluded_fields', newFields)
                        }}
                      />
                      <Label htmlFor={`exclude-${field.id}`} className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        {field.display_name} ({field.field_type})
                      </Label>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground italic">
                    Add other fields to the pipeline first to configure exclusions
                  </p>
                )}
              </div>
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </TooltipProvider>
  )
}