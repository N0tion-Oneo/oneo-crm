'use client'

import { useState, useEffect } from 'react'
import { Loader2, AlertCircle } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/features/auth/context'
import { communicationsApi } from '@/lib/api'
import { ProviderSettings } from '@/components/settings/communications/ProviderSettings'

interface ProviderConfigurations {
  providers: Record<string, any>
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

export default function ProviderSettingsPage() {
  const [configurations, setConfigurations] = useState<ProviderConfigurations | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  
  const { toast } = useToast()
  const { hasPermission } = useAuth()
  
  const canViewCommunicationSettings = hasPermission('communications', 'read')
  const canManageCommunicationSettings = hasPermission('communications', 'update')

  useEffect(() => {
    // Only load if user has permission
    if (!canViewCommunicationSettings) {
      setLoading(false)
      return
    }
    loadConfigurations()
  }, [canViewCommunicationSettings])

  const loadConfigurations = async () => {
    try {
      setLoading(true)
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

  if (loading) {
    return (
      <div className="p-6">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        </div>
      </div>
    )
  }

  if (!canViewCommunicationSettings) {
    return (
      <div className="p-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 mx-auto text-amber-500 mb-4" />
            <h3 className="text-lg font-medium">Access Denied</h3>
            <p className="text-gray-600">You don't have permission to view provider settings.</p>
          </div>
        </div>
      </div>
    )
  }

  if (!configurations) {
    return (
      <div className="p-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 mx-auto text-red-500 mb-4" />
            <h3 className="text-lg font-medium">Configuration Error</h3>
            <p className="text-gray-600">Unable to load provider configurations.</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="max-w-5xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Provider Settings
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Configure features, rate limits, and preferences for each communication provider
          </p>
        </div>

        <ProviderSettings
          providers={configurations.providers}
          onUpdatePreferences={updateProviderPreferences}
          saving={saving}
          canEdit={canManageCommunicationSettings}
        />
      </div>
    </div>
  )
}