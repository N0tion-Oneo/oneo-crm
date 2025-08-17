'use client'

import { useState, useEffect } from 'react'
import { Settings, Save, Loader2, CheckCircle, AlertCircle, Info } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/features/auth/context'
import { communicationsApi } from '@/lib/api'

interface ProviderConfig {
  global: {
    name: string
    icon: string
    features: Record<string, boolean>
    rate_limits: Record<string, number>
    auth_methods: string[]
    supported_endpoints: string[]
  }
  tenant_preferences: {
    enabled_features: string[]
    auto_sync_enabled: boolean
    sync_frequency: string
    auto_create_contacts: boolean
    preferred_auth_method: string
    rate_limits: Record<string, number>
    notifications_enabled: boolean
  }
  is_configured: boolean
  can_connect: boolean
}

interface ProviderConfigurations {
  providers: Record<string, ProviderConfig>
  global_settings: {
    dsn: string
    is_configured: boolean
    webhook_url: string
  }
  tenant_config: {
    is_active: boolean
    auto_create_contacts: boolean
    sync_historical_days: number
    enable_real_time_sync: boolean
    max_api_calls_per_hour: number
  }
}

export default function CommunicationsSettingsPage() {
  const [configurations, setConfigurations] = useState<ProviderConfigurations | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState('providers')
  
  const { toast } = useToast()
  const { tenant, user, isAuthenticated, isLoading: authLoading } = useAuth()

  // Load provider configurations
  useEffect(() => {
    if (isAuthenticated && !authLoading && user && tenant) {
      loadConfigurations()
    } else if (!isAuthenticated && !authLoading) {
      setLoading(false)
    }
  }, [isAuthenticated, authLoading, user, tenant])

  const loadConfigurations = async () => {
    try {
      const response = await communicationsApi.getProviderConfigurations()
      setConfigurations(response.data)
    } catch (error: any) {
      console.error('Error loading configurations:', error)
      toast({
        title: "Failed to load configurations",
        description: error.response?.data?.error || "An error occurred",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const updateProviderPreferences = async (providerType: string, preferences: any) => {
    setSaving(true)
    try {
      await communicationsApi.updateProviderPreferences({
        provider_type: providerType,
        preferences
      })
      
      // Reload configurations to get updated data
      await loadConfigurations()
      
      toast({
        title: "Preferences Updated",
        description: `${providerType} preferences have been saved.`,
      })
    } catch (error: any) {
      console.error('Error updating preferences:', error)
      toast({
        title: "Update Failed",
        description: error.response?.data?.error || "Failed to update preferences",
        variant: "destructive",
      })
    } finally {
      setSaving(false)
    }
  }

  const updateTenantConfig = async (configData: any) => {
    setSaving(true)
    try {
      await communicationsApi.updateTenantConfig(configData)
      
      // Reload configurations to get updated data
      await loadConfigurations()
      
      toast({
        title: "Configuration Updated",
        description: "Tenant configuration has been saved.",
      })
    } catch (error: any) {
      console.error('Error updating tenant config:', error)
      toast({
        title: "Update Failed",
        description: error.response?.data?.error || "Failed to update configuration",
        variant: "destructive",
      })
    } finally {
      setSaving(false)
    }
  }

  const toggleProviderFeature = (providerType: string, feature: string, enabled: boolean) => {
    if (!configurations) return
    
    const provider = configurations.providers[providerType]
    const currentFeatures = provider.tenant_preferences.enabled_features || []
    
    let newFeatures: string[]
    if (enabled) {
      newFeatures = [...currentFeatures, feature]
    } else {
      newFeatures = currentFeatures.filter(f => f !== feature)
    }
    
    const updatedPreferences = {
      ...provider.tenant_preferences,
      enabled_features: newFeatures
    }
    
    updateProviderPreferences(providerType, updatedPreferences)
  }

  const getFeatureStatus = (provider: ProviderConfig, feature: string) => {
    const globallyEnabled = provider.global.features[feature] || false
    const tenantEnabled = provider.tenant_preferences.enabled_features?.includes(feature) || false
    
    return {
      globally_enabled: globallyEnabled,
      tenant_enabled: tenantEnabled,
      available: globallyEnabled && tenantEnabled
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-12">
            <Loader2 className="h-12 w-12 animate-spin mx-auto text-primary" />
            <p className="mt-4 text-gray-600">Loading communications settings...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!configurations) {
    return (
      <div className="p-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 mx-auto text-red-500 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Configuration Error</h3>
            <p className="text-gray-600">Unable to load communications settings.</p>
            <Button onClick={loadConfigurations} className="mt-4">
              Try Again
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
              <Settings className="w-6 h-6 mr-2" />
              Communications Settings
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Configure provider preferences and communication settings
            </p>
          </div>
          
          <div className="flex items-center space-x-2">
            <Badge variant={configurations.global_settings.is_configured ? "default" : "destructive"}>
              {configurations.global_settings.is_configured ? "Configured" : "Not Configured"}
            </Badge>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="providers">Provider Settings</TabsTrigger>
            <TabsTrigger value="general">General Settings</TabsTrigger>
            <TabsTrigger value="advanced">Advanced</TabsTrigger>
          </TabsList>

          <TabsContent value="providers" className="space-y-6">
            <div className="grid gap-6">
              {Object.entries(configurations.providers).map(([providerType, provider]) => (
                <Card key={providerType}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <span className="text-2xl">{provider.global.icon}</span>
                        <div>
                          <CardTitle className="text-lg">{provider.global.name}</CardTitle>
                          <CardDescription>
                            {provider.global.auth_methods.join(', ')} authentication
                          </CardDescription>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Badge variant={provider.can_connect ? "default" : "secondary"}>
                          {provider.can_connect ? "Available" : "Unavailable"}
                        </Badge>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {/* Features */}
                    <div>
                      <h4 className="font-medium mb-3">Available Features</h4>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        {Object.entries(provider.global.features).map(([feature, globallyEnabled]) => {
                          const status = getFeatureStatus(provider, feature)
                          return (
                            <div key={feature} className="flex items-center justify-between p-3 border rounded-md">
                              <div className="flex items-center space-x-2">
                                <span className="text-sm font-medium capitalize">
                                  {feature.replace('_', ' ')}
                                </span>
                                {!globallyEnabled && (
                                  <Info className="w-4 h-4 text-gray-400" title="Not available globally" />
                                )}
                              </div>
                              <Switch
                                checked={status.available}
                                disabled={!globallyEnabled || saving}
                                onCheckedChange={(checked) => toggleProviderFeature(providerType, feature, checked)}
                              />
                            </div>
                          )
                        })}
                      </div>
                    </div>

                    {/* Rate Limits */}
                    <div>
                      <h4 className="font-medium mb-3">Rate Limits (Global Limits)</h4>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {Object.entries(provider.global.rate_limits).map(([limitType, limit]) => (
                          <div key={limitType} className="p-3 bg-gray-50 dark:bg-gray-800 rounded-md">
                            <div className="text-xs text-gray-500 uppercase tracking-wide">
                              {limitType.replace('_', ' ')}
                            </div>
                            <div className="text-lg font-semibold">{limit.toLocaleString()}</div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Quick Settings */}
                    <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                      <div className="flex items-center justify-between">
                        <Label>Auto Sync</Label>
                        <Switch
                          checked={provider.tenant_preferences.auto_sync_enabled}
                          disabled={saving}
                          onCheckedChange={(checked) => updateProviderPreferences(providerType, {
                            ...provider.tenant_preferences,
                            auto_sync_enabled: checked
                          })}
                        />
                      </div>
                      <div className="flex items-center justify-between">
                        <Label>Notifications</Label>
                        <Switch
                          checked={provider.tenant_preferences.notifications_enabled}
                          disabled={saving}
                          onCheckedChange={(checked) => updateProviderPreferences(providerType, {
                            ...provider.tenant_preferences,
                            notifications_enabled: checked
                          })}
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="general" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>General Settings</CardTitle>
                <CardDescription>
                  Configure general communication preferences
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label>Auto Create Contacts</Label>
                    <Switch
                      checked={configurations.tenant_config.auto_create_contacts}
                      disabled={saving}
                      onCheckedChange={(checked) => updateTenantConfig({
                        auto_create_contacts: checked
                      })}
                    />
                    <p className="text-xs text-gray-500">
                      Automatically create contact records from messages
                    </p>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Real-time Sync</Label>
                    <Switch
                      checked={configurations.tenant_config.enable_real_time_sync}
                      disabled={saving}
                      onCheckedChange={(checked) => updateTenantConfig({
                        enable_real_time_sync: checked
                      })}
                    />
                    <p className="text-xs text-gray-500">
                      Enable real-time message sync via webhooks
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label>Historical Sync Days</Label>
                    <Input
                      type="number"
                      value={configurations.tenant_config.sync_historical_days}
                      disabled={saving}
                      onChange={(e) => updateTenantConfig({
                        sync_historical_days: parseInt(e.target.value)
                      })}
                    />
                    <p className="text-xs text-gray-500">
                      Days of historical messages to sync on initial connection
                    </p>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Max API Calls per Hour</Label>
                    <Input
                      type="number"
                      value={configurations.tenant_config.max_api_calls_per_hour}
                      disabled={saving}
                      onChange={(e) => updateTenantConfig({
                        max_api_calls_per_hour: parseInt(e.target.value)
                      })}
                    />
                    <p className="text-xs text-gray-500">
                      Maximum UniPile API calls per hour
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="advanced" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Advanced Configuration</CardTitle>
                <CardDescription>
                  View global settings and system information
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 gap-4">
                  <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-md">
                    <div className="text-sm font-medium text-gray-700 dark:text-gray-300">Global DSN</div>
                    <div className="text-xs text-gray-500 font-mono break-all">
                      {configurations.global_settings.dsn || 'Not configured'}
                    </div>
                  </div>
                  
                  <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-md">
                    <div className="text-sm font-medium text-gray-700 dark:text-gray-300">Webhook URL</div>
                    <div className="text-xs text-gray-500 font-mono break-all">
                      {configurations.global_settings.webhook_url}
                    </div>
                  </div>
                </div>

                <div className="border-t pt-6">
                  <h4 className="font-medium mb-3">System Status</h4>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Global Configuration</span>
                      <Badge variant={configurations.global_settings.is_configured ? "default" : "destructive"}>
                        {configurations.global_settings.is_configured ? "Configured" : "Missing"}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Tenant Active</span>
                      <Badge variant={configurations.tenant_config.is_active ? "default" : "secondary"}>
                        {configurations.tenant_config.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}