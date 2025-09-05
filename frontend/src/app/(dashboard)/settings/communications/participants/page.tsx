'use client'

import { useState, useEffect } from 'react'
import { Loader2, AlertCircle } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/features/auth/context'
import { api } from '@/lib/api'

// Import all the extracted components
import { AutoCreationSettings } from '@/components/settings/communications/AutoCreationSettings'
import { ChannelSettings } from '@/components/settings/communications/ChannelSettings'
import { CompanyLinkingSettings } from '@/components/settings/communications/CompanyLinkingSettings'
import { BlacklistManagement } from '@/components/settings/communications/BlacklistManagement'
import { ProcessingSettings } from '@/components/settings/communications/ProcessingSettings'

interface ParticipantSettings {
  id: string
  auto_create_enabled: boolean
  min_messages_before_create: number
  check_duplicates_before_create: boolean
  duplicate_confidence_threshold: number
  creation_delay_hours: number
  default_contact_pipeline: string | null
  default_contact_pipeline_name: string | null
  name_mapping_mode?: 'single' | 'split'
  full_name_field: string
  first_name_field: string
  last_name_field: string
  name_split_strategy: 'first_space' | 'last_space' | 'smart'
  company_name_field?: string
  auto_link_by_domain: boolean
  create_company_if_missing: boolean
  min_employees_for_company: number
  default_company_pipeline: string | null
  default_company_pipeline_name: string | null
  batch_size: number
  max_creates_per_hour: number
  enable_real_time_creation: boolean
  channel_settings?: Record<string, any>
  [key: string]: any
}

interface BlacklistEntry {
  id: string
  entry_type: 'domain' | 'email' | 'email_pattern' | 'phone' | 'name_pattern'
  value: string
  reason: string
  is_active: boolean
  expires_at: string | null
  created_by_name: string
  created_at: string
}

interface Pipeline {
  id: string
  name: string
  slug: string
  pipeline_type?: string
  email_fields?: any[]
  phone_fields?: any[]
  domain_fields?: any[]
  url_fields?: any[]
}

interface PipelineField {
  id: string
  slug: string
  display_name: string
  field_type: string
  is_required: boolean
}

export default function ParticipantSettingsPage() {
  const { hasPermission } = useAuth()
  const { toast } = useToast()
  
  const canViewSettings = hasPermission('communications', 'read')
  const canEditSettings = hasPermission('communications', 'update')
  const canRunBatch = hasPermission('communications', 'create') // Batch operations require create permission
  
  const [settings, setSettings] = useState<ParticipantSettings | null>(null)
  const [blacklist, setBlacklist] = useState<BlacklistEntry[]>([])
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [compatiblePipelines, setCompatiblePipelines] = useState<Pipeline[]>([])
  const [companyPipelines, setCompanyPipelines] = useState<Pipeline[]>([])
  const [pipelineFields, setPipelineFields] = useState<PipelineField[]>([])
  const [companyPipelineFields, setCompanyPipelineFields] = useState<PipelineField[]>([])
  const [loadingFields, setLoadingFields] = useState(false)
  const [loadingCompanyFields, setLoadingCompanyFields] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState('auto-creation')

  useEffect(() => {
    // Only load data if user has permission to view settings
    if (canViewSettings) {
      loadData()
    } else {
      setLoading(false)
    }
  }, [canViewSettings])

  const loadData = async () => {
    try {
      setLoading(true)
      
      // Try to load participant settings
      try {
        const settingsResponse = await api.get('/api/v1/participant-settings/')
        const settingsData = settingsResponse.data
        if (settingsData.channel_settings) {
          Object.assign(settingsData, settingsData.channel_settings)
        }
        setSettings(settingsData)
      } catch (error: any) {
        if (error.response?.status === 403) {
          console.warn('Insufficient permissions for participant settings - using defaults')
          toast({
            title: "Limited Access",
            description: "You have limited permissions for participant settings. Some features may be restricted.",
            variant: "default",
          })
        } else if (error.response?.status === 404) {
          console.warn('Participant settings endpoint not found - using defaults')
        } else {
          console.error('Error loading participant settings:', error)
        }
        // Set default settings if loading fails
        setSettings({
          enabled: false,
          auto_create_contacts: false,
          require_email: false,
          require_phone: false,
          require_company: false,
          match_existing_by_email: true,
          match_existing_by_phone: false,
          match_existing_by_name: false,
          link_to_existing_company: false,
          target_pipeline_id: null,
          company_pipeline_id: null,
          blacklist_domains: [],
          channel_settings: {}
        })
      }
      
      // Load pipelines first as other endpoints may depend on them
      let loadedPipelines: any[] = []
      try {
        const pipelinesResponse = await api.get('/api/v1/pipelines/')
        loadedPipelines = pipelinesResponse.data.results || pipelinesResponse.data || []
        setPipelines(loadedPipelines)
      } catch (error: any) {
        if (error.response?.status === 403) {
          console.warn('Insufficient permissions for pipelines')
        } else {
          console.warn('Could not load pipelines:', error)
        }
        setPipelines([])
      }
      
      // Load blacklist
      try {
        const blacklistResponse = await api.get('/api/v1/participant-blacklist/')
        setBlacklist(blacklistResponse.data.results || blacklistResponse.data || [])
      } catch (error: any) {
        if (error.response?.status === 403) {
          console.warn('Insufficient permissions for blacklist')
        } else {
          console.warn('Could not load blacklist:', error)
        }
        setBlacklist([])
      }
      
      // Load compatible pipelines with fallback
      try {
        const compatibleResponse = await api.get('/api/v1/participant-settings/compatible_pipelines/')
        setCompatiblePipelines(compatibleResponse.data || [])
      } catch (error: any) {
        if (error.response?.status === 403) {
          console.warn('Insufficient permissions for compatible pipelines - using all pipelines as fallback')
          // For non-admin users, we can fallback to all pipelines
          setCompatiblePipelines(loadedPipelines)
        } else if (error.response?.status === 404) {
          console.warn('Compatible pipelines endpoint not found - using all pipelines')
          setCompatiblePipelines(loadedPipelines)
        } else {
          console.warn('Could not load compatible pipelines:', error)
          setCompatiblePipelines(loadedPipelines)
        }
      }
      
      // Load company pipelines with fallback
      try {
        const companyResponse = await api.get('/api/v1/participant-settings/company_pipelines/')
        setCompanyPipelines(companyResponse.data || [])
      } catch (error: any) {
        if (error.response?.status === 403 || error.response?.status === 404) {
          console.warn('Cannot access company pipelines endpoint - filtering from loaded pipelines')
          // For non-admin users or missing endpoint, filter pipelines by name
          const companyPipelines = loadedPipelines.filter(p => 
            p.name?.toLowerCase().includes('company') || 
            p.name?.toLowerCase().includes('organization') ||
            p.name?.toLowerCase().includes('account')
          )
          setCompanyPipelines(companyPipelines.length > 0 ? companyPipelines : loadedPipelines)
        } else {
          console.warn('Could not load company pipelines:', error)
          setCompanyPipelines([])
        }
      }
      
    } catch (error: any) {
      console.error('Unexpected error loading data:', error)
      // Only show error toast for unexpected errors, not permission issues
      if (!error.response || (error.response.status !== 403 && error.response.status !== 404)) {
        toast({
          title: "Error Loading Settings",
          description: "Some settings could not be loaded. You may have limited functionality.",
          variant: "destructive",
        })
      }
    } finally {
      setLoading(false)
    }
  }

  const loadPipelineFields = async (pipelineId: string, type: 'contact' | 'company' = 'contact') => {
    if (!pipelineId || pipelineId === 'none') {
      if (type === 'contact') {
        setPipelineFields([])
      } else {
        setCompanyPipelineFields([])
      }
      return
    }
    
    try {
      if (type === 'contact') {
        setLoadingFields(true)
      } else {
        setLoadingCompanyFields(true)
      }
      
      const response = await api.get(`/api/v1/pipelines/${pipelineId}/fields/`)
      const fields = response.data.results || response.data || []
      
      if (type === 'contact') {
        setPipelineFields(fields)
      } else {
        setCompanyPipelineFields(fields)
      }
    } catch (error) {
      console.error(`Error loading ${type} pipeline fields:`, error)
      if (type === 'contact') {
        setPipelineFields([])
      } else {
        setCompanyPipelineFields([])
      }
    } finally {
      if (type === 'contact') {
        setLoadingFields(false)
      } else {
        setLoadingCompanyFields(false)
      }
    }
  }

  useEffect(() => {
    if (settings?.default_contact_pipeline) {
      loadPipelineFields(settings.default_contact_pipeline, 'contact')
    }
  }, [settings?.default_contact_pipeline])
  
  useEffect(() => {
    if (settings?.default_company_pipeline) {
      loadPipelineFields(settings.default_company_pipeline, 'company')
    }
  }, [settings?.default_company_pipeline])

  const updateSettings = async (updates: Partial<ParticipantSettings>) => {
    if (!settings) return
    
    // Check if user has permission to edit
    if (!canEditSettings) {
      toast({
        title: "Permission Denied",
        description: "You don't have permission to update participant settings.",
        variant: "destructive",
      })
      return
    }
    
    const updatedSettings = { ...settings, ...updates }
    setSettings(updatedSettings)
    
    setSaving(true)
    try {
      let response
      // Try participant-settings endpoint first
      try {
        response = await api.patch(`/api/v1/participant-settings/${settings.id}/`, updates)
      } catch (error: any) {
        // If that fails with 403, user doesn't have permission
        if (error.response?.status === 403) {
          throw new Error("You don't have permission to update these settings")
        }
        // If 404, the endpoint doesn't exist
        if (error.response?.status === 404) {
          console.warn('Participant settings update endpoint not found')
          // For now, just keep the local state updated
          return
        }
        throw error
      }
      
      const responseData = response.data
      if (responseData.channel_settings) {
        Object.assign(responseData, responseData.channel_settings)
      }
      setSettings(responseData)
      
      toast({
        title: "Settings Updated",
        description: "Participant settings have been saved.",
      })
    } catch (error: any) {
      console.error('Error updating settings:', error)
      setSettings(settings)
      toast({
        title: "Update Failed",
        description: error.response?.data?.detail || error.response?.data?.error || "Failed to update settings",
        variant: "destructive",
      })
    } finally {
      setSaving(false)
    }
  }

  const addBlacklistEntry = async (newEntry: any) => {
    const response = await api.post('/api/v1/participant-blacklist/', newEntry)
    setBlacklist([response.data, ...blacklist])
  }

  const removeBlacklistEntry = async (id: string) => {
    await api.delete(`/api/v1/participant-blacklist/${id}/`)
    setBlacklist(blacklist.filter(entry => entry.id !== id))
  }

  const processBatch = async (dryRun: boolean = false) => {
    const response = await api.post('/api/v1/participant-settings/process_batch/', {
      batch_size: settings?.batch_size,
      dry_run: dryRun
    })
    
    if (dryRun) {
      let description = `${response.data.eligible_count} eligible out of ${response.data.total_checked} checked`
      if (response.data.total_unlinked) {
        description += ` (${response.data.total_unlinked} total unlinked)`
      }
      
      toast({
        title: "Dry Run Complete",
        description,
      })
    } else {
      let description = `Created: ${response.data.created} total`
      
      if (response.data.skipped > 0) {
        description += `\nSkipped: ${response.data.skipped}`
      }
      
      toast({
        title: "Batch Processed",
        description,
      })
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

  if (!settings) {
    return (
      <div className="p-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 mx-auto text-red-500 mb-4" />
            <h3 className="text-lg font-medium">Settings Error</h3>
            <p className="text-gray-600">Unable to load participant settings.</p>
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
            <p className="text-gray-600">You don't have permission to view participant settings.</p>
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
            Participant Settings
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Configure how participants are automatically converted to contacts
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="auto-creation">Auto-Creation</TabsTrigger>
            <TabsTrigger value="channels">Channels</TabsTrigger>
            <TabsTrigger value="company">Companies</TabsTrigger>
            <TabsTrigger value="blacklist">Blacklist</TabsTrigger>
            <TabsTrigger value="processing">Processing</TabsTrigger>
          </TabsList>

          <TabsContent value="auto-creation" className="space-y-6">
            <AutoCreationSettings
              settings={settings}
              pipelines={compatiblePipelines}
              pipelineFields={pipelineFields}
              loadingFields={loadingFields}
              onUpdateSettings={updateSettings}
              saving={saving}
              canEdit={canEditSettings}
            />
          </TabsContent>

          <TabsContent value="channels">
            <ChannelSettings
              settings={settings}
              onUpdateSettings={updateSettings}
              saving={saving}
              canEdit={canEditSettings}
            />
          </TabsContent>

          <TabsContent value="company">
            <CompanyLinkingSettings
              settings={settings}
              companyPipelines={companyPipelines}
              companyPipelineFields={companyPipelineFields}
              loadingCompanyFields={loadingCompanyFields}
              onUpdateSettings={updateSettings}
              onLoadPipelineFields={loadPipelineFields}
              saving={saving}
              canEdit={canEditSettings}
            />
          </TabsContent>

          <TabsContent value="blacklist">
            <BlacklistManagement
              blacklist={blacklist}
              onAddEntry={addBlacklistEntry}
              onRemoveEntry={removeBlacklistEntry}
              canEdit={canEditSettings}
            />
          </TabsContent>

          <TabsContent value="processing">
            <ProcessingSettings
              settings={settings}
              onUpdateSettings={updateSettings}
              onProcessBatch={processBatch}
              saving={saving}
              canEdit={canEditSettings}
              canRunBatch={canRunBatch}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}