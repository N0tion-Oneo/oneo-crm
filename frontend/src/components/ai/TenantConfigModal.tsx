import React, { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { AlertTriangle, Key, Settings, TrendingUp, Eye, EyeOff, Trash2 } from 'lucide-react'
import { aiApi } from '@/lib/api'

interface TenantConfig {
  tenant_id: string
  tenant_name: string
  ai_enabled: boolean
  openai_api_key?: string
  anthropic_api_key?: string
  default_provider: 'openai' | 'anthropic'
  default_model: string
  usage_limits: {
    monthly_budget_cents?: number
    daily_request_limit?: number
    concurrent_jobs?: number
  }
  current_usage: {
    total_tokens: number
    total_cost_dollars: number
    total_requests: number
    avg_response_time_ms: number
  }
  available_models: string[]
  concurrent_jobs: number
}

interface TenantConfigModalProps {
  isOpen: boolean
  onClose: () => void
  onSaved: () => void
}

export default function TenantConfigModal({ isOpen, onClose, onSaved }: TenantConfigModalProps) {
  const [config, setConfig] = useState<TenantConfig | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [showApiKey, setShowApiKey] = useState(false)
  const [showAnthropicKey, setShowAnthropicKey] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (isOpen) {
      loadConfig()
    }
  }, [isOpen])

  const loadConfig = async () => {
    try {
      setLoading(true)
      const response = await aiApi.jobs.tenantConfig()
      setConfig(response.data)
    } catch (error: any) {
      console.error('Failed to load AI config:', error)
      
      // Handle permission errors gracefully
      if (error.response?.status === 403) {
        setErrors({ 
          general: 'You do not have permission to view AI configuration. Contact your administrator.' 
        })
      } else {
        setErrors({ 
          general: 'Failed to load AI configuration. Please try again.' 
        })
      }
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteApiKey = async (provider: 'openai' | 'anthropic') => {
    try {
      await aiApi.jobs.deleteApiKey(provider)
      
      // Clear the key from local state
      setConfig(prev => {
        if (!prev) return null
        const updated = { ...prev }
        if (provider === 'openai') {
          updated.openai_api_key = ''
        } else {
          updated.anthropic_api_key = ''
        }
        return updated
      })
      
      onSaved() // Refresh the parent
    } catch (error: any) {
      console.error(`Failed to delete ${provider} API key:`, error)
      setErrors({ [provider]: `Failed to delete ${provider} API key` })
    }
  }

  const handleSave = async () => {
    if (!config) return

    try {
      setSaving(true)
      setErrors({})

      const updateData = {
        ai_enabled: config.ai_enabled,
        default_provider: config.default_provider,
        default_model: config.default_model,
        usage_limits: config.usage_limits,
        concurrent_jobs: config.concurrent_jobs,
        // Only send API keys if they're not masked (new keys being set)
        ...(config.openai_api_key && !config.openai_api_key.includes('••••') && { openai_api_key: config.openai_api_key }),
        ...(config.anthropic_api_key && !config.anthropic_api_key.includes('••••') && { anthropic_api_key: config.anthropic_api_key })
      }

      await aiApi.jobs.updateTenantConfig(updateData)
      onSaved()
      onClose()
    } catch (error: any) {
      console.error('Failed to save AI config:', error)
      
      // Handle validation errors
      if (error.response?.data) {
        setErrors(error.response.data)
      }
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>Loading AI Configuration</DialogTitle>
          </DialogHeader>
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  if (!config) {
    // Show error state if there are errors
    if (Object.keys(errors).length > 0) {
      return (
        <Dialog open={isOpen} onOpenChange={onClose}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-red-500" />
                Configuration Error
              </DialogTitle>
            </DialogHeader>
            <div className="py-4">
              <p className="text-red-600">{errors.general}</p>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={onClose}>
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )
    }
    return null
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            AI Configuration
          </DialogTitle>
          <DialogDescription>
            Configure AI features and settings for {config.tenant_name}
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="general" className="space-y-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="general">General</TabsTrigger>
            <TabsTrigger value="providers">Providers</TabsTrigger>
            <TabsTrigger value="limits">Limits</TabsTrigger>
            <TabsTrigger value="usage">Usage</TabsTrigger>
          </TabsList>

          <TabsContent value="general" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>General Settings</CardTitle>
                <CardDescription>
                  Basic AI configuration for your tenant
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Enable AI Features</Label>
                    <p className="text-sm text-gray-500">
                      Allow AI processing across the platform
                    </p>
                  </div>
                  <Switch
                    checked={config.ai_enabled}
                    onCheckedChange={(checked) => 
                      setConfig(prev => prev ? { ...prev, ai_enabled: checked } : null)
                    }
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Default Provider</Label>
                    <Select
                      value={config.default_provider}
                      onValueChange={(value: 'openai' | 'anthropic') =>
                        setConfig(prev => prev ? { ...prev, default_provider: value } : null)
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="openai">OpenAI</SelectItem>
                        <SelectItem value="anthropic">Anthropic</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Default Model</Label>
                    <Select
                      value={config.default_model}
                      onValueChange={(value) =>
                        setConfig(prev => prev ? { ...prev, default_model: value } : null)
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {config.available_models.map(model => (
                          <SelectItem key={model} value={model}>{model}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Concurrent Jobs</Label>
                  <Input
                    type="number"
                    min="1"
                    max="20"
                    value={config.concurrent_jobs}
                    onChange={(e) =>
                      setConfig(prev => prev ? { 
                        ...prev, 
                        concurrent_jobs: Math.max(1, Math.min(20, parseInt(e.target.value) || 1))
                      } : null)
                    }
                  />
                  <p className="text-sm text-gray-500">
                    Maximum number of simultaneous AI jobs
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="providers" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Key className="h-4 w-4" />
                  API Keys
                </CardTitle>
                <CardDescription>
                  Configure API keys for AI providers
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* OpenAI Configuration */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium">OpenAI</h4>
                    <Badge variant={config.default_provider === 'openai' ? 'default' : 'secondary'}>
                      {config.default_provider === 'openai' ? 'Default' : 'Available'}
                    </Badge>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>API Key</Label>
                    {config.openai_api_key && config.openai_api_key.includes('••••') ? (
                      // Show existing masked key with delete option
                      <div className="flex gap-2">
                        <Input
                          type="text"
                          value={config.openai_api_key}
                          readOnly
                          className="flex-1 bg-gray-50"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => handleDeleteApiKey('openai')}
                          className="text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ) : (
                      // Show input for new key
                      <div className="flex gap-2">
                        <Input
                          type={showApiKey ? 'text' : 'password'}
                          placeholder="sk-..."
                          value={config.openai_api_key || ''}
                          onChange={(e) =>
                            setConfig(prev => prev ? { ...prev, openai_api_key: e.target.value } : null)
                          }
                          className="flex-1"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setShowApiKey(!showApiKey)}
                        >
                          {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </Button>
                      </div>
                    )}
                    {errors.openai_api_key && (
                      <p className="text-sm text-red-600">{errors.openai_api_key}</p>
                    )}
                  </div>
                </div>

                {/* Anthropic Configuration */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium">Anthropic (Claude)</h4>
                    <Badge variant={config.default_provider === 'anthropic' ? 'default' : 'secondary'}>
                      {config.default_provider === 'anthropic' ? 'Default' : 'Available'}
                    </Badge>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>API Key</Label>
                    {config.anthropic_api_key && config.anthropic_api_key.includes('••••') ? (
                      // Show existing masked key with delete option
                      <div className="flex gap-2">
                        <Input
                          type="text"
                          value={config.anthropic_api_key}
                          readOnly
                          className="flex-1 bg-gray-50"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => handleDeleteApiKey('anthropic')}
                          className="text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ) : (
                      // Show input for new key
                      <div className="flex gap-2">
                        <Input
                          type={showAnthropicKey ? 'text' : 'password'}
                          placeholder="sk-ant-..."
                          value={config.anthropic_api_key || ''}
                          onChange={(e) =>
                            setConfig(prev => prev ? { ...prev, anthropic_api_key: e.target.value } : null)
                          }
                          className="flex-1"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setShowAnthropicKey(!showAnthropicKey)}
                        >
                          {showAnthropicKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </Button>
                      </div>
                    )}
                    {errors.anthropic_api_key && (
                      <p className="text-sm text-red-600">{errors.anthropic_api_key}</p>
                    )}
                  </div>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-blue-600 mt-0.5" />
                    <div className="text-sm text-blue-800">
                      <p className="font-medium">Security Note</p>
                      <p>API keys are encrypted and stored securely. They are never logged or exposed in API responses.</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="limits" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Usage Limits</CardTitle>
                <CardDescription>
                  Set spending and usage limits to control AI costs
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Monthly Budget (USD)</Label>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      placeholder="100.00"
                      value={(config.usage_limits.monthly_budget_cents || 0) / 100}
                      onChange={(e) => {
                        const cents = Math.round((parseFloat(e.target.value) || 0) * 100)
                        setConfig(prev => prev ? {
                          ...prev,
                          usage_limits: { ...prev.usage_limits, monthly_budget_cents: cents }
                        } : null)
                      }}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Daily Request Limit</Label>
                    <Input
                      type="number"
                      min="1"
                      placeholder="1000"
                      value={config.usage_limits.daily_request_limit || ''}
                      onChange={(e) =>
                        setConfig(prev => prev ? {
                          ...prev,
                          usage_limits: { 
                            ...prev.usage_limits, 
                            daily_request_limit: parseInt(e.target.value) || undefined 
                          }
                        } : null)
                      }
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="usage" className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{config.current_usage.total_requests}</div>
                  <p className="text-xs text-gray-500">This month</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Tokens Used</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{config.current_usage.total_tokens.toLocaleString()}</div>
                  <p className="text-xs text-gray-500">Total processed</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">${config.current_usage.total_cost_dollars.toFixed(2)}</div>
                  <p className="text-xs text-gray-500">This month</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Avg Response</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{Math.round(config.current_usage.avg_response_time_ms)}ms</div>
                  <p className="text-xs text-gray-500">Response time</p>
                </CardContent>
              </Card>
            </div>

            {/* Budget progress */}
            {config.usage_limits.monthly_budget_cents && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Budget Usage</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Current Month</span>
                      <span>
                        ${config.current_usage.total_cost_dollars.toFixed(2)} / 
                        ${(config.usage_limits.monthly_budget_cents / 100).toFixed(2)}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full"
                        style={{
                          width: `${Math.min(100, (config.current_usage.total_cost_dollars * 100) / (config.usage_limits.monthly_budget_cents / 100))}%`
                        }}
                      ></div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save Configuration'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}