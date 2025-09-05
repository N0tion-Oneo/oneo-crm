'use client'

import { useState, useEffect } from 'react'
import { Settings, Save, Loader2, AlertCircle, Plus, Trash2, Search, Shield } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/context'
import { PermissionGuard } from '@/components/permissions/PermissionGuard'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useToast } from '@/hooks/use-toast'
import { api } from '@/lib/api'
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'

interface ParticipantSettings {
  id: string
  auto_create_enabled: boolean
  min_messages_before_create: number
  require_email: boolean
  require_phone: boolean
  check_duplicates_before_create: boolean
  duplicate_confidence_threshold: number
  creation_delay_hours: number
  default_contact_pipeline: string | null
  default_contact_pipeline_name: string | null
  // Name field configuration
  name_mapping_mode?: 'single' | 'split'
  full_name_field: string
  first_name_field: string
  last_name_field: string
  name_split_strategy: 'first_space' | 'last_space' | 'smart'
  // Company settings
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
  // Channel-specific settings (flattened from channel_settings)
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
}

interface PipelineField {
  id: string
  slug: string
  display_name: string
  field_type: string
  is_required: boolean
}

export function ParticipantAutoCreateSettings() {
  const { hasPermission } = useAuth()
  const { toast } = useToast()
  
  // Check permissions
  const canViewSettings = hasPermission('participants', 'settings')
  const canEditSettings = hasPermission('participants', 'settings')
  const canRunBatch = hasPermission('participants', 'batch')
  
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
  const [activeTab, setActiveTab] = useState('general')
  
  // Blacklist dialog state
  const [showBlacklistDialog, setShowBlacklistDialog] = useState(false)
  const [newBlacklistEntry, setNewBlacklistEntry] = useState({
    entry_type: 'email',
    value: '',
    reason: ''
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      
      // Load settings
      const settingsResponse = await api.get('/api/v1/participant-settings/')
      // Flatten channel settings into main settings object
      const settingsData = settingsResponse.data
      console.log('Settings from API:', settingsData)
      if (settingsData.channel_settings) {
        Object.assign(settingsData, settingsData.channel_settings)
        console.log('Settings after flattening channel_settings:', settingsData)
      }
      setSettings(settingsData)
      
      // Load blacklist
      const blacklistResponse = await api.get('/api/v1/participant-blacklist/')
      setBlacklist(blacklistResponse.data.results || blacklistResponse.data)
      
      // Load all pipelines
      const pipelinesResponse = await api.get('/api/v1/pipelines/')
      setPipelines(pipelinesResponse.data.results || pipelinesResponse.data)
      
      // Load compatible pipelines (with email/phone fields)
      const compatibleResponse = await api.get('/api/v1/participant-settings/compatible_pipelines/')
      console.log('Compatible pipelines from API:', compatibleResponse.data)
      setCompatiblePipelines(compatibleResponse.data)
      
      // Load company pipelines (with domain/URL fields)
      const companyResponse = await api.get('/api/v1/participant-settings/company_pipelines/')
      console.log('Company pipelines from API:', companyResponse.data)
      setCompanyPipelines(companyResponse.data)
      
    } catch (error: any) {
      console.error('Error loading data:', error)
      toast({
        title: "Failed to load settings",
        description: error.response?.data?.error || "An error occurred",
        variant: "destructive",
      })
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

  // Load fields when pipeline changes
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
    
    // Merge updates with current settings for optimistic UI update
    const updatedSettings = { ...settings, ...updates }
    setSettings(updatedSettings)
    
    setSaving(true)
    try {
      const response = await api.patch(`/api/v1/participant-settings/${settings.id}/`, updates)
      // Update with server response, but preserve channel settings if they exist
      const responseData = response.data
      if (responseData.channel_settings) {
        Object.assign(responseData, responseData.channel_settings)
      }
      setSettings(responseData)
      
      toast({
        title: "Settings Updated",
        description: "Participant auto-creation settings have been saved.",
      })
    } catch (error: any) {
      console.error('Error updating settings:', error)
      // Revert on error
      setSettings(settings)
      toast({
        title: "Update Failed",
        description: error.response?.data?.error || "Failed to update settings",
        variant: "destructive",
      })
    } finally {
      setSaving(false)
    }
  }

  const addBlacklistEntry = async () => {
    if (!newBlacklistEntry.value) {
      toast({
        title: "Validation Error",
        description: "Please provide a value for the blacklist entry",
        variant: "destructive",
      })
      return
    }
    
    try {
      const response = await api.post('/api/v1/participant-blacklist/', newBlacklistEntry)
      setBlacklist([response.data, ...blacklist])
      setShowBlacklistDialog(false)
      setNewBlacklistEntry({ entry_type: 'email', value: '', reason: '' })
      
      toast({
        title: "Blacklist Entry Added",
        description: "The blacklist entry has been added successfully.",
      })
    } catch (error: any) {
      toast({
        title: "Failed to add entry",
        description: error.response?.data?.error || "An error occurred",
        variant: "destructive",
      })
    }
  }

  const removeBlacklistEntry = async (id: string) => {
    try {
      await api.delete(`/api/v1/participant-blacklist/${id}/`)
      setBlacklist(blacklist.filter(entry => entry.id !== id))
      
      toast({
        title: "Entry Removed",
        description: "The blacklist entry has been removed.",
      })
    } catch (error: any) {
      toast({
        title: "Failed to remove entry",
        description: error.response?.data?.error || "An error occurred",
        variant: "destructive",
      })
    }
  }

  const processBatch = async (dryRun: boolean = false) => {
    try {
      const response = await api.post('/api/v1/participant-settings/process_batch/', {
        batch_size: settings?.batch_size,
        dry_run: dryRun
      })
      
      if (dryRun) {
        console.log('Dry run response:', response.data)
        let description = `${response.data.eligible_count} eligible out of ${response.data.total_checked} checked`
        if (response.data.total_unlinked) {
          description += ` (${response.data.total_unlinked} total unlinked)`
        }
        
        // Add detailed breakdown if available
        if (response.data.contacts_would_create || response.data.companies_would_create || response.data.companies_would_link) {
          const details = []
          if (response.data.contacts_would_create) {
            details.push(`${response.data.contacts_would_create} contact${response.data.contacts_would_create !== 1 ? 's' : ''}`)
          }
          if (response.data.companies_would_create) {
            details.push(`${response.data.companies_would_create} new compan${response.data.companies_would_create !== 1 ? 'ies' : 'y'}`)
          }
          if (response.data.companies_would_link) {
            details.push(`${response.data.companies_would_link} existing compan${response.data.companies_would_link !== 1 ? 'ies' : 'y'} linked`)
          }
          
          if (details.length > 0) {
            description += `\nWould create: ${details.join(', ')}`
          }
        }
        
        // Add rejection reasons if available
        if (response.data.rejection_reasons && Object.keys(response.data.rejection_reasons).length > 0) {
          const topReasons = Object.entries(response.data.rejection_reasons)
            .sort((a: any, b: any) => b[1] - a[1])
            .slice(0, 3)
            .map(([reason, count]: any) => `${reason}: ${count}`)
            .join(', ')
          description += `\nTop reasons for skipping: ${topReasons}`
        }
        
        toast({
          title: "Dry Run Complete",
          description,
        })
      } else {
        let description = `Created: ${response.data.created} total`
        
        // Add detailed breakdown if available
        if (response.data.contacts_created !== undefined || response.data.companies_created !== undefined) {
          const details = []
          if (response.data.contacts_created) {
            details.push(`${response.data.contacts_created} contact${response.data.contacts_created !== 1 ? 's' : ''}`)
          }
          if (response.data.companies_created) {
            details.push(`${response.data.companies_created} compan${response.data.companies_created !== 1 ? 'ies' : 'y'}`)
          }
          if (response.data.companies_linked) {
            details.push(`${response.data.companies_linked} linked to existing compan${response.data.companies_linked !== 1 ? 'ies' : 'y'}`)
          }
          
          if (details.length > 0) {
            description = `Created: ${details.join(', ')}`
          }
        }
        
        if (response.data.skipped > 0) {
          description += `\nSkipped: ${response.data.skipped}`
        }
        if (response.data.errors > 0) {
          description += `\nErrors: ${response.data.errors}`
        }
        
        toast({
          title: "Batch Processed",
          description,
        })
      }
    } catch (error: any) {
      toast({
        title: "Batch Processing Failed",
        description: error.response?.data?.error || "An error occurred",
        variant: "destructive",
      })
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!settings) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 mx-auto text-red-500 mb-4" />
        <h3 className="text-lg font-medium">Settings Error</h3>
        <p className="text-gray-600">Unable to load participant settings.</p>
        <Button onClick={loadData} className="mt-4">
          Try Again
        </Button>
      </div>
    )
  }

  // Check if user has permission to view settings
  if (!canViewSettings) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Access Denied
          </CardTitle>
          <CardDescription>
            You don't have permission to view participant settings.
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="channels">Channels</TabsTrigger>
          <TabsTrigger value="company">Company Linking</TabsTrigger>
          <TabsTrigger value="blacklist">Blacklist</TabsTrigger>
          <TabsTrigger value="processing">Processing</TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Auto-Creation Settings</CardTitle>
              <CardDescription>
                Configure when and how participants are automatically converted to contacts
                {!canEditSettings && (
                  <span className="block mt-2 text-yellow-600 dark:text-yellow-500">
                    <Shield className="h-4 w-4 inline mr-1" />
                    View-only mode. You don't have permission to edit settings.
                  </span>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <Label>Enable Auto-Creation</Label>
                  <p className="text-sm text-gray-500">
                    Automatically create contact records from participants
                  </p>
                </div>
                <Switch
                  checked={settings.auto_create_enabled}
                  disabled={saving || !canEditSettings}
                  onCheckedChange={(checked) => updateSettings({ auto_create_enabled: checked })}
                />
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label>Minimum Messages</Label>
                  <Input
                    type="number"
                    min="0"
                    value={settings.min_messages_before_create}
                    disabled={saving}
                    onChange={(e) => updateSettings({ 
                      min_messages_before_create: parseInt(e.target.value) 
                    })}
                  />
                  <p className="text-xs text-gray-500">
                    Number of messages before creating a contact
                  </p>
                </div>

                <div className="space-y-2">
                  <Label>Creation Delay (Hours)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={settings.creation_delay_hours}
                    disabled={saving}
                    onChange={(e) => updateSettings({ 
                      creation_delay_hours: parseInt(e.target.value) 
                    })}
                  />
                  <p className="text-xs text-gray-500">
                    Wait period before auto-creating
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div className="flex items-center justify-between">
                  <Label>Require Email</Label>
                  <Switch
                    checked={settings.require_email}
                    disabled={saving}
                    onCheckedChange={(checked) => updateSettings({ require_email: checked })}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <Label>Require Phone</Label>
                  <Switch
                    checked={settings.require_phone}
                    disabled={saving}
                    onCheckedChange={(checked) => updateSettings({ require_phone: checked })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Default Contact Pipeline</Label>
                <Select
                  value={settings.default_contact_pipeline || 'none'}
                  onValueChange={(value) => updateSettings({ 
                    default_contact_pipeline: value === 'none' ? null : value 
                  })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a pipeline" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    {compatiblePipelines.length > 0 ? (
                      compatiblePipelines.map((pipeline: any) => (
                        <SelectItem key={pipeline.id} value={pipeline.id}>
                          <span>
                            {pipeline.name}
                            {pipeline.pipeline_type && (
                              <span className="ml-2 text-xs text-gray-500">
                                ({pipeline.pipeline_type})
                              </span>
                            )}
                            {(pipeline.email_fields?.length > 0 || pipeline.phone_fields?.length > 0) && (
                              <span className="ml-2 text-xs text-gray-400">
                                {pipeline.email_fields?.length > 0 && `📧 ${pipeline.email_fields.length}`}
                                {pipeline.phone_fields?.length > 0 && ` 📱 ${pipeline.phone_fields.length}`}
                              </span>
                            )}
                          </span>
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="none" disabled>
                        No compatible pipelines (need email or phone fields)
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </div>

              {/* Name Field Configuration */}
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                        <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                      </div>
                      <div>
                        <CardTitle className="text-base">Name Field Mapping</CardTitle>
                        <CardDescription className="text-xs mt-0.5">
                          Configure how participant names map to record fields
                        </CardDescription>
                      </div>
                    </div>
                    {settings.default_contact_pipeline && (
                      <Badge variant="secondary">
                        {pipelineFields.length} fields available
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                
                <CardContent className="space-y-4">
                  {!settings.default_contact_pipeline ? (
                    <div className="flex items-center gap-3 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                      <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0" />
                      <p className="text-sm text-amber-800 dark:text-amber-200">
                        Please select a <strong>Default Contact Pipeline</strong> above to configure name field mapping
                      </p>
                    </div>
                  ) : loadingFields ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-blue-600 dark:text-blue-400" />
                      <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">Loading pipeline fields...</span>
                    </div>
                  ) : (
                    <>
                      {/* Mapping Strategy Toggle */}
                      <div className="p-4 bg-gray-50 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 rounded-lg">
                        <Label className="text-sm font-medium mb-3 block">Choose Mapping Strategy</Label>
                        <div className="grid grid-cols-2 gap-3">
                          <label className="flex items-center gap-2.5 p-3 border border-gray-200 dark:border-gray-700 rounded-lg cursor-pointer hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors group">
                            <input
                              type="radio"
                              name="nameStrategy"
                              value="single"
                              checked={settings.name_mapping_mode === 'single'}
                              onChange={() => {
                                updateSettings({
                                  name_mapping_mode: 'single',
                                  first_name_field: '',
                                  last_name_field: ''
                                })
                              }}
                              className="flex-shrink-0"
                            />
                            <div className="flex-1">
                              <div className="font-medium text-sm group-hover:text-blue-600 dark:group-hover:text-blue-400">Single Name Field</div>
                              <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                                Use one field for full name
                              </div>
                            </div>
                          </label>
                          
                          <label className="flex items-center gap-2.5 p-3 border border-gray-200 dark:border-gray-700 rounded-lg cursor-pointer hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors group">
                            <input
                              type="radio"
                              name="nameStrategy"
                              value="split"
                              checked={settings.name_mapping_mode === 'split'}
                              onChange={() => {
                                updateSettings({
                                  name_mapping_mode: 'split',
                                  full_name_field: ''
                                })
                              }}
                              className="flex-shrink-0"
                            />
                            <div className="flex-1">
                              <div className="font-medium text-sm group-hover:text-blue-600 dark:group-hover:text-blue-400">Split Name Fields</div>
                              <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                                Separate first and last name
                              </div>
                            </div>
                          </label>
                        </div>
                      </div>
                      
                      {/* Field Selection - Only show selected option */}
                      <div className="space-y-3">
                        {/* Single Name Field Option - Show only when selected */}
                        {settings.name_mapping_mode === 'single' && (
                          <div className="p-4 bg-gray-50 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 rounded-lg">
                            <Label htmlFor="full-name" className="text-sm font-medium mb-2 block flex items-center gap-2">
                              <span className="w-2 h-2 bg-blue-500 dark:bg-blue-400 rounded-full"></span>
                              Full Name Field
                            </Label>
                            <Select
                              value={settings.full_name_field || 'none'}
                              onValueChange={(value) => updateSettings({ 
                                full_name_field: value === 'none' ? '' : value 
                              })}
                            >
                              <SelectTrigger id="full-name" className="w-full">
                                <SelectValue placeholder="Select field for full name" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="none">
                                  <span className="text-gray-500">No field selected</span>
                                </SelectItem>
                                {pipelineFields
                                  .filter(field => ['text', 'single_line_text', 'name'].includes(field.field_type))
                                  .map(field => (
                                    <SelectItem key={field.id} value={field.slug}>
                                      <div className="flex items-center gap-2">
                                        <span className="font-medium">{field.display_name}</span>
                                        <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">
                                          {field.slug}
                                        </code>
                                      </div>
                                    </SelectItem>
                                  ))
                                }
                              </SelectContent>
                            </Select>
                            <p className="text-xs text-gray-500 mt-1.5">
                              Stores the complete name in a single field
                            </p>
                          </div>
                        )}
                        
                        {/* Split Name Fields Option - Show only when selected */}
                        {settings.name_mapping_mode === 'split' && (
                          <div className="p-4 bg-gray-50 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 rounded-lg space-y-3">
                            <div className="grid grid-cols-3 gap-3">
                              <div>
                                <Label htmlFor="first-name" className="text-sm font-medium mb-1.5 block">
                                  First Name Field
                                </Label>
                                <Select
                                  value={settings.first_name_field || 'none'}
                                  onValueChange={(value) => updateSettings({ 
                                    first_name_field: value === 'none' ? '' : value 
                                  })}
                                >
                                  <SelectTrigger id="first-name" className="h-9">
                                    <SelectValue placeholder="Select field" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="none">
                                      <span className="text-gray-500">None</span>
                                    </SelectItem>
                                    {pipelineFields
                                      .filter(field => ['text', 'single_line_text', 'name'].includes(field.field_type))
                                      .map(field => (
                                        <SelectItem key={field.id} value={field.slug}>
                                          <div className="flex items-center gap-2">
                                            <span className="text-sm">{field.display_name}</span>
                                          </div>
                                        </SelectItem>
                                      ))
                                    }
                                  </SelectContent>
                                </Select>
                              </div>
                              
                              <div>
                                <Label htmlFor="last-name" className="text-sm font-medium mb-1.5 block">
                                  Last Name Field
                                </Label>
                                <Select
                                  value={settings.last_name_field || 'none'}
                                  onValueChange={(value) => updateSettings({ 
                                    last_name_field: value === 'none' ? '' : value 
                                  })}
                                >
                                  <SelectTrigger id="last-name" className="h-9">
                                    <SelectValue placeholder="Select field" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="none">
                                      <span className="text-gray-500">None</span>
                                    </SelectItem>
                                    {pipelineFields
                                      .filter(field => ['text', 'single_line_text', 'name'].includes(field.field_type))
                                      .map(field => (
                                        <SelectItem key={field.id} value={field.slug}>
                                          <div className="flex items-center gap-2">
                                            <span className="text-sm">{field.display_name}</span>
                                          </div>
                                        </SelectItem>
                                      ))
                                    }
                                  </SelectContent>
                                </Select>
                              </div>
                              
                              <div>
                                <Label htmlFor="name-split" className="text-sm font-medium mb-1.5 block">
                                  Split Strategy
                                </Label>
                                <Select
                                  value={settings.name_split_strategy || 'smart'}
                                  onValueChange={(value: 'first_space' | 'last_space' | 'smart') => 
                                    updateSettings({ name_split_strategy: value })
                                  }
                                >
                                  <SelectTrigger id="name-split" className="h-9">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="smart">Smart Detection</SelectItem>
                                    <SelectItem value="first_space">First Space</SelectItem>
                                    <SelectItem value="last_space">Last Space</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                            </div>
                            <p className="text-xs text-gray-500">
                              Participant names will be split using the selected strategy and mapped to your first and last name fields
                            </p>
                          </div>
                        )}
                        
                        {/* Prompt to select an option if none selected */}
                        {!settings.name_mapping_mode && (
                          <div className="p-4 bg-gray-50 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 rounded-lg text-center">
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                              Please select a mapping strategy above to configure fields
                            </p>
                          </div>
                        )}
                      </div>
                      
                      {/* Info Box */}
                      <div className="flex items-start gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                        <AlertCircle className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                        <div className="text-xs text-blue-800 dark:text-blue-200 space-y-1">
                          <p>
                            <strong>Note:</strong> Name fields are mapped separately since duplicate detection only identifies email and phone fields. This mapping tells the system where to store participant names.
                          </p>
                          <p>
                            Example: "John Michael Doe" → 
                            {settings.name_split_strategy === 'smart' && " First: John, Last: Doe"}
                            {settings.name_split_strategy === 'first_space' && " First: John, Last: Michael Doe"}
                            {settings.name_split_strategy === 'last_space' && " First: John Michael, Last: Doe"}
                          </p>
                        </div>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>

              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <Label>Check for Duplicates</Label>
                  <p className="text-sm text-gray-500">
                    Check for existing contacts before creating new ones
                  </p>
                </div>
                <Switch
                  checked={settings.check_duplicates_before_create}
                  disabled={saving}
                  onCheckedChange={(checked) => updateSettings({ 
                    check_duplicates_before_create: checked 
                  })}
                />
              </div>

              {settings.check_duplicates_before_create && (
                <div className="space-y-2">
                  <Label>Duplicate Confidence Threshold</Label>
                  <Input
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    value={settings.duplicate_confidence_threshold}
                    disabled={saving}
                    onChange={(e) => updateSettings({ 
                      duplicate_confidence_threshold: parseFloat(e.target.value) 
                    })}
                  />
                  <p className="text-xs text-gray-500">
                    Minimum confidence score to consider a match (0-1)
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="channels" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Channel-Specific Settings</CardTitle>
              <CardDescription>
                Configure auto-creation rules for each communication channel
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {['email', 'whatsapp', 'linkedin'].map((channel) => {
                const isEnabled = settings[`${channel}_enabled`] ?? true
                const minMessages = settings[`${channel}_min_messages`] ?? 1
                const requireTwoWay = settings[`${channel}_require_two_way`] ?? false
                
                return (
                <div key={channel} className="border rounded-lg p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium capitalize">{channel}</h4>
                      <p className="text-sm text-gray-500">
                        Settings for {channel} channel participants
                      </p>
                    </div>
                    <Switch
                      checked={isEnabled}
                      disabled={saving}
                      onCheckedChange={(checked) => updateSettings({ 
                        [`${channel}_enabled`]: checked 
                      })}
                    />
                  </div>
                  
                  {isEnabled && (
                    <div className="pl-4 space-y-4 border-l-2 border-gray-200">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label>Minimum Messages</Label>
                          <Input
                            type="number"
                            min="1"
                            value={minMessages}
                            disabled={saving}
                            onChange={(e) => updateSettings({ 
                              [`${channel}_min_messages`]: parseInt(e.target.value) 
                            })}
                          />
                        </div>
                        
                        <div className="flex items-center space-x-2">
                          <Switch
                            checked={requireTwoWay}
                            disabled={saving}
                            onCheckedChange={(checked) => updateSettings({ 
                              [`${channel}_require_two_way`]: checked 
                            })}
                          />
                          <Label>Require Two-Way Conversation</Label>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
                )
              })}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="company" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Company Linking Settings</CardTitle>
              <CardDescription>
                Configure how participants are linked to companies based on email domains
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <Label>Auto-Link by Domain</Label>
                  <p className="text-sm text-gray-500">
                    Automatically link participants to companies by email domain
                  </p>
                </div>
                <Switch
                  checked={settings.auto_link_by_domain}
                  disabled={saving}
                  onCheckedChange={(checked) => updateSettings({ auto_link_by_domain: checked })}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <Label>Create Company if Missing</Label>
                  <p className="text-sm text-gray-500">
                    Create a new company record if one doesn't exist
                  </p>
                </div>
                <Switch
                  checked={settings.create_company_if_missing}
                  disabled={saving}
                  onCheckedChange={(checked) => updateSettings({ 
                    create_company_if_missing: checked 
                  })}
                />
              </div>

              {settings.create_company_if_missing && (
                <>
                  <div className="space-y-2">
                    <Label>Minimum Employees for Company</Label>
                    <Input
                      type="number"
                      min="1"
                      value={settings.min_employees_for_company}
                      disabled={saving}
                      onChange={(e) => updateSettings({ 
                        min_employees_for_company: parseInt(e.target.value) 
                      })}
                    />
                    <p className="text-xs text-gray-500">
                      Minimum number of participants from same domain to create company
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label>Default Company Pipeline</Label>
                    <Select
                      value={settings.default_company_pipeline || 'none'}
                      onValueChange={(value) => {
                        updateSettings({ 
                          default_company_pipeline: value === 'none' ? null : value 
                        })
                        // Load fields for the selected pipeline
                        if (value !== 'none') {
                          loadPipelineFields(value, 'company')
                        }
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select a pipeline" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">None</SelectItem>
                        {companyPipelines.length > 0 ? (
                          companyPipelines.map((pipeline: any) => (
                            <SelectItem key={pipeline.id} value={pipeline.id}>
                              <span>
                                {pipeline.name}
                                {pipeline.pipeline_type && (
                                  <span className="ml-2 text-xs text-gray-500">
                                    ({pipeline.pipeline_type})
                                  </span>
                                )}
                                {(pipeline.domain_fields?.length > 0 || pipeline.url_fields?.length > 0) && (
                                  <span className="ml-2 text-xs text-gray-400">
                                    {pipeline.domain_fields?.length > 0 && `🌐 ${pipeline.domain_fields.length} domain`}
                                    {pipeline.url_fields?.length > 0 && ` 🔗 ${pipeline.url_fields.length} url`}
                                  </span>
                                )}
                              </span>
                            </SelectItem>
                          ))
                        ) : (
                          <SelectItem value="none" disabled>
                            No pipelines with domain/URL duplicate rules
                          </SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                    {companyPipelines.length === 0 && (
                      <p className="text-xs text-amber-600">
                        Configure duplicate detection rules with domain or URL fields to enable company linking
                      </p>
                    )}
                  </div>
                  
                  {/* Company Name Field Mapping */}
                  {settings.default_company_pipeline && (
                    <div className="space-y-2 pt-4 border-t">
                      <Label>Company Name Field</Label>
                      <Select
                        value={settings.company_name_field || 'none'}
                        onValueChange={(value) => updateSettings({ 
                          company_name_field: value === 'none' ? '' : value 
                        })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select field for company name" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">
                            <span className="text-gray-500">No field selected</span>
                          </SelectItem>
                          {companyPipelineFields
                            .filter(field => ['text', 'single_line_text', 'name'].includes(field.field_type))
                            .map(field => (
                              <SelectItem key={field.id} value={field.slug}>
                                <div className="flex items-center gap-2">
                                  <span className="text-sm">{field.display_name}</span>
                                  <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">
                                    {field.slug}
                                  </code>
                                </div>
                              </SelectItem>
                            ))
                          }
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-gray-500">
                        Company name will be derived from email domain (e.g., "acme.com" → "Acme")
                      </p>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="blacklist" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Blacklist Management</CardTitle>
                  <CardDescription>
                    Prevent specific participants from being auto-created
                  </CardDescription>
                </div>
                <Dialog open={showBlacklistDialog} onOpenChange={setShowBlacklistDialog}>
                  <DialogTrigger asChild>
                    <Button size="sm">
                      <Plus className="h-4 w-4 mr-2" />
                      Add Entry
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Add Blacklist Entry</DialogTitle>
                      <DialogDescription>
                        Add a pattern to prevent auto-creation
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label>Entry Type</Label>
                        <Select
                          value={newBlacklistEntry.entry_type}
                          onValueChange={(value) => setNewBlacklistEntry({
                            ...newBlacklistEntry,
                            entry_type: value as any
                          })}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="email">Email Address</SelectItem>
                            <SelectItem value="domain">Email Domain</SelectItem>
                            <SelectItem value="email_pattern">Email Pattern</SelectItem>
                            <SelectItem value="phone">Phone Number</SelectItem>
                            <SelectItem value="name_pattern">Name Pattern</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label>Value</Label>
                        <Input
                          placeholder={
                            newBlacklistEntry.entry_type === 'domain' ? 'example.com' :
                            newBlacklistEntry.entry_type === 'email' ? 'user@example.com' :
                            newBlacklistEntry.entry_type === 'phone' ? '+1234567890' :
                            'Pattern with * wildcards'
                          }
                          value={newBlacklistEntry.value}
                          onChange={(e) => setNewBlacklistEntry({
                            ...newBlacklistEntry,
                            value: e.target.value
                          })}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label>Reason (Optional)</Label>
                        <Textarea
                          placeholder="Why is this being blacklisted?"
                          value={newBlacklistEntry.reason}
                          onChange={(e) => setNewBlacklistEntry({
                            ...newBlacklistEntry,
                            reason: e.target.value
                          })}
                        />
                      </div>

                      <div className="flex justify-end space-x-2">
                        <Button
                          variant="outline"
                          onClick={() => setShowBlacklistDialog(false)}
                        >
                          Cancel
                        </Button>
                        <Button onClick={addBlacklistEntry}>
                          Add Entry
                        </Button>
                      </div>
                    </div>
                  </DialogContent>
                </Dialog>
              </div>
            </CardHeader>
            <CardContent>
              {blacklist.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No blacklist entries. Add entries to prevent specific participants from being auto-created.
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Type</TableHead>
                      <TableHead>Value</TableHead>
                      <TableHead>Reason</TableHead>
                      <TableHead>Created By</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {blacklist.map(entry => (
                      <TableRow key={entry.id}>
                        <TableCell>
                          <Badge variant="outline">
                            {entry.entry_type}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {entry.value}
                        </TableCell>
                        <TableCell className="text-sm text-gray-600">
                          {entry.reason || '-'}
                        </TableCell>
                        <TableCell className="text-sm">
                          {entry.created_by_name}
                        </TableCell>
                        <TableCell>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => removeBlacklistEntry(entry.id)}
                          >
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="processing" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Batch Processing Settings</CardTitle>
              <CardDescription>
                Configure batch processing and performance settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label>Batch Size</Label>
                <Input
                  type="number"
                  min="1"
                  max="1000"
                  value={settings.batch_size}
                  disabled={saving}
                  onChange={(e) => updateSettings({ 
                    batch_size: parseInt(e.target.value) 
                  })}
                />
                <p className="text-xs text-gray-500">
                  Number of participants to process in each batch
                </p>
              </div>

              <div className="border-t pt-6">
                <h4 className="font-medium mb-4">Manual Processing</h4>
                <div className="flex space-x-4">
                  <Button
                    variant="outline"
                    onClick={() => processBatch(true)}
                    disabled={!canRunBatch}
                    title={!canRunBatch ? "You don't have permission to run batch processing" : "Run a test to see what would be created"}
                  >
                    <Search className="h-4 w-4 mr-2" />
                    Dry Run
                  </Button>
                  <Button
                    onClick={() => processBatch(false)}
                    disabled={!canRunBatch}
                    title={!canRunBatch ? "You don't have permission to run batch processing" : "Process participants and create contacts"}
                  >
                    <Settings className="h-4 w-4 mr-2" />
                    Process Batch Now
                  </Button>
                </div>
                <p className="text-sm text-gray-500 mt-2">
                  Dry run shows what would be created without making changes
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}