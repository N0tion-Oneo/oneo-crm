'use client'

import { useState, useEffect } from 'react'
import { Loader2, AlertCircle } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/features/auth/context'
import { communicationsApi } from '@/lib/api'
import { GeneralSettings } from '@/components/settings/communications/GeneralSettings'

interface TenantConfig {
  is_active: boolean
  auto_create_contacts: boolean
  sync_historical_days: number
  enable_real_time_sync: boolean
  max_api_calls_per_hour: number
  sync_frequency: string
  webhook_enabled: boolean
  data_retention_days: number
  enable_message_threading: boolean
  enable_attachment_sync: boolean
  max_attachment_size_mb: number
}

export default function GeneralSettingsPage() {
  const [config, setConfig] = useState<TenantConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  
  const { toast } = useToast()
  const { hasPermission } = useAuth()
  
  // Check page-based permission - having permission means both view and edit
  const hasPageAccess = hasPermission('communication_settings', 'general')
  const canViewSettings = hasPageAccess
  const canEditSettings = hasPageAccess

  useEffect(() => {
    // Only load if user has permission
    if (!canViewSettings) {
      setLoading(false)
      return
    }
    loadConfig()
  }, [canViewSettings])

  const loadConfig = async () => {
    try {
      setLoading(true)
      const response = await communicationsApi.getProviderConfigurations()
      
      // Extract tenant config and add default values for missing fields
      const tenantConfig = response.data.tenant_config || {}
      const fullConfig: TenantConfig = {
        is_active: tenantConfig.is_active ?? false,
        auto_create_contacts: tenantConfig.auto_create_contacts ?? false,
        sync_historical_days: tenantConfig.sync_historical_days ?? 30,
        enable_real_time_sync: tenantConfig.enable_real_time_sync ?? false,
        max_api_calls_per_hour: tenantConfig.max_api_calls_per_hour ?? 1000,
        sync_frequency: tenantConfig.sync_frequency ?? '15min',
        webhook_enabled: tenantConfig.webhook_enabled ?? false,
        data_retention_days: tenantConfig.data_retention_days ?? 365,
        enable_message_threading: tenantConfig.enable_message_threading ?? true,
        enable_attachment_sync: tenantConfig.enable_attachment_sync ?? true,
        max_attachment_size_mb: tenantConfig.max_attachment_size_mb ?? 10
      }
      
      setConfig(fullConfig)
    } catch (error: any) {
      console.error('Error loading configuration:', error)
      toast({
        title: "Failed to load configuration",
        description: error.response?.data?.error || "An error occurred",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const updateConfig = async (updates: Partial<TenantConfig>) => {
    if (!config) return
    
    // Optimistic update
    const updatedConfig = { ...config, ...updates }
    setConfig(updatedConfig)
    
    setSaving(true)
    try {
      await communicationsApi.updateTenantConfig(updates)
      
      toast({
        title: "Configuration Updated",
        description: "General settings have been saved successfully.",
      })
    } catch (error: any) {
      console.error('Error updating configuration:', error)
      // Revert on error
      setConfig(config)
      toast({
        title: "Update Failed",
        description: error.response?.data?.error || "Failed to update configuration",
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

  if (!canViewSettings) {
    return (
      <div className="p-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 mx-auto text-amber-500 mb-4" />
            <h3 className="text-lg font-medium">Access Denied</h3>
            <p className="text-gray-600">You don't have permission to view general settings.</p>
          </div>
        </div>
      </div>
    )
  }

  if (!config) {
    return (
      <div className="p-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 mx-auto text-red-500 mb-4" />
            <h3 className="text-lg font-medium">Configuration Error</h3>
            <p className="text-gray-600">Unable to load general settings.</p>
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
            General Settings
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Configure synchronization, API limits, and system-wide communication preferences
          </p>
        </div>

        <GeneralSettings
          config={config}
          onUpdateConfig={updateConfig}
          saving={saving}
          canEdit={canEditSettings}
        />
      </div>
    </div>
  )
}