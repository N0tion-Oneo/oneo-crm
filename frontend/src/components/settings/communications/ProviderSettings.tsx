'use client'

import { useState } from 'react'
import { Settings2, Info, Zap, Bell, Clock, Shield, Globe, Mail, MessageCircle, Linkedin, Camera, Send, Hash } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import { useToast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'

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

interface ProviderSettingsProps {
  providers: Record<string, ProviderConfig>
  onUpdatePreferences: (providerType: string, preferences: any) => Promise<void>
  saving: boolean
  canEdit: boolean
}

const PROVIDER_DETAILS: Record<string, { color: string; description: string; icon: any }> = {
  gmail: { color: 'text-red-500', description: 'Google Gmail integration with full email capabilities', icon: Mail },
  outlook: { color: 'text-blue-600', description: 'Microsoft Outlook integration for enterprise email', icon: Mail },
  mail: { color: 'text-gray-600', description: 'Generic email integration for standard SMTP/IMAP', icon: Mail },
  whatsapp: { color: 'text-green-500', description: 'WhatsApp Business API for instant messaging', icon: MessageCircle },
  linkedin: { color: 'text-indigo-600', description: 'LinkedIn messaging and InMail integration', icon: Linkedin },
  instagram: { color: 'text-pink-500', description: 'Instagram Direct Messages for social engagement', icon: Camera },
  messenger: { color: 'text-blue-500', description: 'Facebook Messenger for business communication', icon: MessageCircle },
  telegram: { color: 'text-cyan-500', description: 'Telegram Bot API for secure messaging', icon: Send },
  twitter: { color: 'text-sky-500', description: 'Twitter/X Direct Messages and mentions', icon: Hash }
}

export function ProviderSettings({
  providers,
  onUpdatePreferences,
  saving,
  canEdit
}: ProviderSettingsProps) {
  const { toast } = useToast()
  const [activeProvider, setActiveProvider] = useState<string>(Object.keys(providers)[0] || '')

  const toggleProviderFeature = async (providerType: string, feature: string, enabled: boolean) => {
    const provider = providers[providerType]
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
    
    try {
      await onUpdatePreferences(providerType, updatedPreferences)
      toast({
        title: "Settings Updated",
        description: `${provider.global.name} feature settings have been updated.`,
      })
    } catch (error) {
      toast({
        title: "Update Failed",
        description: "Failed to update provider settings.",
        variant: "destructive",
      })
    }
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

  const formatRateLimit = (limit: number): string => {
    if (limit >= 1000000) return `${(limit / 1000000).toFixed(1)}M`
    if (limit >= 1000) return `${(limit / 1000).toFixed(0)}K`
    return limit.toString()
  }

  if (Object.keys(providers).length === 0) {
    return (
      <Card>
        <CardContent className="text-center py-12">
          <Settings2 className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">No Providers Configured</h3>
          <p className="text-gray-500">
            Communication providers have not been configured for this tenant.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Tabs value={activeProvider} onValueChange={setActiveProvider}>
        <TabsList className="grid w-full grid-cols-9 h-auto">
          {Object.entries(providers).map(([key, provider]) => {
            const ProviderIcon = PROVIDER_DETAILS[key]?.icon || Globe
            const providerColor = PROVIDER_DETAILS[key]?.color || 'text-gray-500'
            
            return (
              <TabsTrigger key={key} value={key} className="flex flex-col items-center justify-center gap-0.5 py-2">
                <ProviderIcon className={cn("h-5 w-5", providerColor)} />
                <span className="hidden lg:block text-[10px] leading-tight">{provider.global.name}</span>
              </TabsTrigger>
            )
          })}
        </TabsList>

        {Object.entries(providers).map(([providerType, provider]) => (
          <TabsContent key={providerType} value={providerType} className="space-y-6">
            {/* Provider Overview */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn("p-2 rounded-lg bg-gray-100 dark:bg-gray-800", PROVIDER_DETAILS[providerType]?.color)}>
                      {(() => {
                        const Icon = PROVIDER_DETAILS[providerType]?.icon || Globe
                        return <Icon className="h-6 w-6" />
                      })()}
                    </div>
                    <div>
                      <CardTitle>{provider.global.name}</CardTitle>
                      <CardDescription>
                        {PROVIDER_DETAILS[providerType]?.description || 'Communication provider integration'}
                      </CardDescription>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Badge variant={provider.is_configured ? "default" : "secondary"}>
                      {provider.is_configured ? "Configured" : "Not Configured"}
                    </Badge>
                    <Badge variant={provider.can_connect ? "default" : "destructive"}>
                      {provider.can_connect ? "Available" : "Unavailable"}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
            </Card>

            {/* Features Configuration */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  Features
                </CardTitle>
                <CardDescription>
                  Enable or disable specific features for {provider.global.name}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {Object.entries(provider.global.features).map(([feature, globallyEnabled]) => {
                    const status = getFeatureStatus(provider, feature)
                    const featureName = feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
                    
                    return (
                      <div 
                        key={feature} 
                        className={cn(
                          "p-4 border rounded-lg",
                          !globallyEnabled && "opacity-60 bg-gray-50 dark:bg-gray-900/50"
                        )}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <Label className="text-sm font-medium">
                            {featureName}
                          </Label>
                          <Switch
                            checked={status.available}
                            disabled={!globallyEnabled || saving || !canEdit}
                            onCheckedChange={(checked) => toggleProviderFeature(providerType, feature, checked)}
                          />
                        </div>
                        {!globallyEnabled && (
                          <div className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
                            <Info className="h-3 w-3" />
                            <span>Not available globally</span>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Rate Limits */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  Rate Limits
                </CardTitle>
                <CardDescription>
                  API rate limits and usage quotas for {provider.global.name}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {Object.entries(provider.global.rate_limits).map(([limitType, limit]) => {
                    const limitName = limitType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
                    const usage = Math.random() * limit // Simulated usage
                    const percentage = (usage / limit) * 100
                    
                    return (
                      <div key={limitType} className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="font-medium">{limitName}</span>
                          <span className="text-gray-500">
                            {formatRateLimit(Math.round(usage))} / {formatRateLimit(limit)}
                          </span>
                        </div>
                        <Progress value={percentage} className="h-2" />
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Quick Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings2 className="h-5 w-5" />
                  Quick Settings
                </CardTitle>
                <CardDescription>
                  Common configuration options for {provider.global.name}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <Clock className="h-5 w-5 text-gray-500" />
                      <div>
                        <Label>Auto Sync</Label>
                        <p className="text-sm text-gray-500">Automatically sync messages</p>
                      </div>
                    </div>
                    <Switch
                      checked={provider.tenant_preferences.auto_sync_enabled}
                      disabled={saving || !canEdit}
                      onCheckedChange={async (checked) => {
                        await onUpdatePreferences(providerType, {
                          ...provider.tenant_preferences,
                          auto_sync_enabled: checked
                        })
                      }}
                    />
                  </div>

                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <Bell className="h-5 w-5 text-gray-500" />
                      <div>
                        <Label>Notifications</Label>
                        <p className="text-sm text-gray-500">Receive alerts for new messages</p>
                      </div>
                    </div>
                    <Switch
                      checked={provider.tenant_preferences.notifications_enabled}
                      disabled={saving || !canEdit}
                      onCheckedChange={async (checked) => {
                        await onUpdatePreferences(providerType, {
                          ...provider.tenant_preferences,
                          notifications_enabled: checked
                        })
                      }}
                    />
                  </div>

                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <Shield className="h-5 w-5 text-gray-500" />
                      <div>
                        <Label>Auto-Create Contacts</Label>
                        <p className="text-sm text-gray-500">Create contacts from new conversations</p>
                      </div>
                    </div>
                    <Switch
                      checked={provider.tenant_preferences.auto_create_contacts}
                      disabled={saving || !canEdit}
                      onCheckedChange={async (checked) => {
                        await onUpdatePreferences(providerType, {
                          ...provider.tenant_preferences,
                          auto_create_contacts: checked
                        })
                      }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Authentication Methods */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Authentication Methods
                </CardTitle>
                <CardDescription>
                  Supported authentication methods for {provider.global.name}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {provider.global.auth_methods.map(method => (
                    <Badge key={method} variant="secondary">
                      {method.toUpperCase()}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}