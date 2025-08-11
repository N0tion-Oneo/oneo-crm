'use client'
import React, { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PermissionGuard } from '@/components/permissions/PermissionGuard'
import TenantConfigModal from '@/components/ai/TenantConfigModal'
import { useWebSocket, type RealtimeMessage } from '@/contexts/websocket-context'
import { Plus, Settings, TrendingUp, Zap, FileText, Brain, Search, Users, MessageSquare, BarChart3, Play, Pause, AlertCircle, Clock, User, Database, Copy, ChevronDown, ChevronUp, Eye, AlertTriangle, CheckCircle, XCircle, Activity, RefreshCw, Trash2, PlayCircle, RotateCcw } from 'lucide-react'
import { api } from '@/lib/api'

interface AIJob {
  id: string
  job_type: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
  pipeline: { name: string } | null
  record_id?: number
  field_name: string
  ai_provider: string
  model_name: string
  prompt_template: string
  ai_config: Record<string, any>
  input_data: Record<string, any>
  output_data: Record<string, any>
  tokens_used: number
  cost_cents: number
  cost_dollars: number
  processing_time_ms: number | null
  error_message?: string
  retry_count: number
  max_retries: number
  created_by: { name: string; email: string }
  created_at: string
  updated_at: string
  completed_at?: string
}

interface UsageSummary {
  total_tokens: number
  total_cost_dollars: number
  total_requests: number
  avg_response_time_ms: number
}

interface AIPromptTemplate {
  id: string
  name: string
  slug: string
  description: string
  prompt_template: string
  system_message: string
  ai_provider: string
  model_name: string
  temperature: number
  max_tokens: number
  field_types: string[]
  pipeline_types: string[]
  required_variables: string[]
  optional_variables: string[]
  version: number
  is_active: boolean
  created_by: string
  created_at: string
  updated_at: string
}

interface TenantConfig {
  ai_enabled: boolean
  default_provider: string
  default_model: string
  usage_limits: any
  current_usage: UsageSummary
  concurrent_jobs: number
}

interface WorkerHealth {
  workers_online: number
  worker_details: Record<string, any>
  worker_stats: Record<string, any>
  queue_lengths: {
    ai_processing: number
    celery: number
    maintenance: number
    total: number
  }
  job_counts: {
    pending: number
    processing: number
    total_active: number
  }
  health_status: 'healthy' | 'no_workers' | 'jobs_not_queuing' | 'potential_stuck_jobs' | 'error'
  health_message: string
  timestamp: string
}

interface SystemDiagnostics {
  tenant_info: {
    name: string
    schema: string
    id: string
  }
  ai_config: {
    ai_enabled: boolean
    has_openai_key: boolean
    has_anthropic_key: boolean
    default_provider: string
    default_model: string
    concurrent_jobs: number
    usage_limits: any
  }
  job_stats: {
    total_jobs: number
    pending: number
    processing: number
    completed: number
    failed: number
    cancelled: number
  }
  connectivity: Record<string, string>
  recent_errors: Array<{
    job_id: number
    error_message: string
    failed_at: string
    retry_count: number
    can_retry: boolean
  }>
  overall_health: {
    status: 'healthy' | 'issues_detected'
    issues: string[]
    issues_count: number
    timestamp: string
  }
}

const JOB_TYPE_CONFIG = {
  field_generation: {
    icon: Zap,
    label: 'Field Generation',
    description: 'AI-powered field completion',
    color: 'bg-blue-500'
  },
  summarization: {
    icon: FileText,
    label: 'Summarization',
    description: 'Content summarization',
    color: 'bg-green-500'
  },
  classification: {
    icon: Brain,
    label: 'Classification',
    description: 'Content classification',
    color: 'bg-purple-500'
  },
  sentiment_analysis: {
    icon: MessageSquare,
    label: 'Sentiment Analysis',
    description: 'Emotional tone analysis',
    color: 'bg-pink-500'
  },
  embedding_generation: {
    icon: Search,
    label: 'Embedding Generation',
    description: 'Vector embeddings creation',
    color: 'bg-orange-500'
  },
  semantic_search: {
    icon: Search,
    label: 'Semantic Search',
    description: 'Intelligent content search',
    color: 'bg-teal-500'
  }
}

export default function AIPage() {
  const [jobs, setJobs] = useState<AIJob[]>([])
  const [templates, setTemplates] = useState<AIPromptTemplate[]>([])
  const [tenantConfig, setTenantConfig] = useState<TenantConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set())
  const [configModalOpen, setConfigModalOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'overview' | 'jobs' | 'templates' | 'analytics' | 'search' | 'management'>('overview')
  const [workerHealth, setWorkerHealth] = useState<WorkerHealth | null>(null)
  const [systemDiagnostics, setSystemDiagnostics] = useState<SystemDiagnostics | null>(null)
  const [bulkOperationLoading, setBulkOperationLoading] = useState(false)

  // WebSocket integration for real-time AI job updates
  const { isConnected, connectionStatus, subscribe, unsubscribe } = useWebSocket()

  // Helper functions for detailed job cards
  const toggleJobExpanded = (jobId: string) => {
    setExpandedJobs(prev => {
      const newSet = new Set(prev)
      if (newSet.has(jobId)) {
        newSet.delete(jobId)
      } else {
        newSet.add(jobId)
      }
      return newSet
    })
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const formatDuration = (ms: number | null) => {
    if (!ms) return 'N/A'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return CheckCircle
      case 'failed': return XCircle
      case 'pending': return Clock
      case 'processing': return Play
      default: return AlertCircle
    }
  }

  // Handle real-time AI job updates
  const handleRealtimeMessage = (message: RealtimeMessage) => {
    console.log('🤖 AI Page - Received WebSocket message:', message)
    
    if ((message.type as string) === 'ai_job_update' && (message as any).data) {
      const updatedJob = (message as any).data as AIJob
      
      setJobs(prevJobs => {
        const existingIndex = prevJobs.findIndex(job => job.id === updatedJob.id)
        
        if (existingIndex >= 0) {
          // Update existing job
          const newJobs = [...prevJobs]
          newJobs[existingIndex] = { ...newJobs[existingIndex], ...updatedJob }
          console.log('🔄 Updated existing AI job:', updatedJob.id, updatedJob.status)
          return newJobs
        } else {
          // Add new job
          console.log('➕ Added new AI job:', updatedJob.id, updatedJob.status)
          return [updatedJob, ...prevJobs]
        }
      })
    }
    
    if ((message.type as string) === 'ai_template_update' && (message as any).data) {
      const updatedTemplate = (message as any).data as AIPromptTemplate
      
      setTemplates(prevTemplates => {
        const existingIndex = prevTemplates.findIndex(template => template.id === updatedTemplate.id)
        
        if (existingIndex >= 0) {
          // Update existing template
          const newTemplates = [...prevTemplates]
          newTemplates[existingIndex] = { ...newTemplates[existingIndex], ...updatedTemplate }
          return newTemplates
        } else {
          // Add new template
          return [updatedTemplate, ...prevTemplates]
        }
      })
    }
  }

  // Subscribe to AI-related channels on mount
  useEffect(() => {
    if (isConnected) {
      console.log('🔌 AI Page - WebSocket connected, subscribing to AI channels')
      
      // Subscribe to AI job updates for this tenant
      subscribe('ai_jobs', handleRealtimeMessage)
      
      // Subscribe to AI template updates
      subscribe('ai_templates', handleRealtimeMessage)
      
      // Subscribe to AI usage analytics updates
      subscribe('ai_analytics', handleRealtimeMessage)
    }

    return () => {
      // Cleanup subscriptions
      unsubscribe('ai_jobs')
      unsubscribe('ai_templates') 
      unsubscribe('ai_analytics')
    }
  }, [isConnected, subscribe, unsubscribe])

  useEffect(() => {
    loadAIData()
  }, [])

  const loadAIData = async () => {
    try {
      setLoading(true)
      
      // Load each endpoint individually to better handle errors
      let jobsData = []
      let templatesData = []
      let configData = null
      
      // Load AI jobs
      try {
        console.log('🔄 Loading AI jobs...')
        const jobsResponse = await api.get('/api/v1/ai-jobs/?ordering=-created_at&limit=10')
        jobsData = jobsResponse.data.results || []
        console.log('✅ AI jobs loaded:', jobsData.length)
      } catch (error: any) {
        console.error('❌ Failed to load AI jobs:', {
          status: error?.response?.status,
          statusText: error?.response?.statusText,
          data: error?.response?.data,
          message: error?.message
        })
      }
      
      // Load AI prompt templates
      try {
        console.log('🔄 Loading AI templates...')
        const templatesResponse = await api.get('/api/v1/ai-prompt-templates/?ordering=-created_at')
        templatesData = templatesResponse.data.results || []
        console.log('✅ AI templates loaded:', templatesData.length)
      } catch (error: any) {
        console.error('❌ Failed to load AI templates:', {
          error: error,
          status: error?.response?.status,
          statusText: error?.response?.statusText,
          data: error?.response?.data,
          message: error?.message,
          stack: error?.stack,
          config: error?.config,
          fullError: JSON.stringify(error, Object.getOwnPropertyNames(error))
        })
      }
      
      // Load tenant config
      try {
        console.log('🔄 Loading tenant config...')
        const configResponse = await api.get('/api/v1/ai-jobs/tenant_config/')
        configData = configResponse.data
        console.log('✅ Tenant config loaded:', configData)
      } catch (error: any) {
        console.error('❌ Failed to load tenant config:', {
          status: error?.response?.status,
          statusText: error?.response?.statusText,
          data: error?.response?.data,
          message: error?.message
        })
      }
      
      setJobs(jobsData)
      setTemplates(templatesData)
      setTenantConfig(configData)
    } catch (error) {
      console.error('Failed to load AI data:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadWorkerHealth = useCallback(async () => {
    try {
      const response = await api.get('/api/v1/ai-jobs/worker_health/')
      setWorkerHealth(response.data)
    } catch (error: any) {
      console.error('Failed to load worker health:', error)
      setWorkerHealth(null)
    }
  }, [])

  const loadSystemDiagnostics = useCallback(async () => {
    try {
      const response = await api.get('/api/v1/ai-jobs/diagnostics/')
      setSystemDiagnostics(response.data)
    } catch (error: any) {
      console.error('Failed to load system diagnostics:', error)
      setSystemDiagnostics(null)
    }
  }, [])

  // Load management data when switching to management tab
  useEffect(() => {
    if (activeTab === 'management') {
      loadWorkerHealth()
      loadSystemDiagnostics()
    }
  }, [activeTab, loadWorkerHealth, loadSystemDiagnostics])

  const performBulkRetry = async () => {
    setBulkOperationLoading(true)
    try {
      const response = await api.post('/api/v1/ai-jobs/bulk_retry/')
      console.log('✅ Bulk retry completed:', response.data)
      
      // Show success message and reload data
      if (response.data.retried_count > 0) {
        alert(`Successfully retried ${response.data.retried_count} failed jobs`)
        await loadAIData()
      } else {
        alert('No failed jobs to retry')
      }
    } catch (error: any) {
      console.error('❌ Bulk retry failed:', error)
      alert('Failed to retry jobs: ' + (error.response?.data?.error || error.message))
    } finally {
      setBulkOperationLoading(false)
    }
  }

  const performBulkCancel = async () => {
    setBulkOperationLoading(true)
    try {
      const response = await api.post('/api/v1/ai-jobs/bulk_cancel/')
      console.log('✅ Bulk cancel completed:', response.data)
      
      // Show success message and reload data
      if (response.data.cancelled_count > 0) {
        alert(`Successfully cancelled ${response.data.cancelled_count} pending jobs`)
        await loadAIData()
      } else {
        alert('No pending jobs to cancel')
      }
    } catch (error: any) {
      console.error('❌ Bulk cancel failed:', error)
      alert('Failed to cancel jobs: ' + (error.response?.data?.error || error.message))
    } finally {
      setBulkOperationLoading(false)
    }
  }

  const performQueuePending = async () => {
    setBulkOperationLoading(true)
    try {
      const response = await api.post('/api/v1/ai-jobs/queue_pending/')
      console.log('✅ Queue pending completed:', response.data)
      
      // Show detailed message
      const { queued_count, failed_count, total_pending } = response.data
      if (queued_count > 0) {
        let message = `Successfully queued ${queued_count} jobs for processing`
        if (failed_count > 0) {
          message += `. ${failed_count} jobs failed to queue.`
        }
        alert(message)
        await loadAIData()
        await loadWorkerHealth()
      } else {
        alert('No pending jobs to queue')
      }
    } catch (error: any) {
      console.error('❌ Queue pending failed:', error)
      alert('Failed to queue jobs: ' + (error.response?.data?.error || error.message))
    } finally {
      setBulkOperationLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800'
      case 'processing': return 'bg-blue-100 text-blue-800'
      case 'pending': return 'bg-yellow-100 text-yellow-800'
      case 'failed': return 'bg-red-100 text-red-800'
      case 'cancelled': return 'bg-gray-100 text-gray-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-48 mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <PermissionGuard category="ai_features" action="read" fallback={
      <div className="p-6">
        <div className="text-center py-12">
          <Brain className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">AI Features Not Available</h3>
          <p className="text-gray-500">You don't have permission to access AI features.</p>
        </div>
      </div>
    }>
      <div className="p-6">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">AI Dashboard</h1>
            <p className="text-gray-600">Manage AI features and view processing analytics</p>
          </div>
          <div className="flex gap-2">
            <PermissionGuard category="ai_features" action="configure">
              <Button variant="outline" onClick={() => setConfigModalOpen(true)}>
                <Settings className="h-4 w-4 mr-2" />
                Configure
              </Button>
            </PermissionGuard>
            <Button onClick={() => setActiveTab('jobs')}>
              <Plus className="h-4 w-4 mr-2" />
              View Jobs
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as any)} className="space-y-6">
          <TabsList className="grid w-full grid-cols-6">
            <TabsTrigger value="overview" className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="jobs" className="flex items-center gap-2">
              <Zap className="h-4 w-4" />
              Jobs
            </TabsTrigger>
            <TabsTrigger value="management" className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Management
            </TabsTrigger>
            <TabsTrigger value="templates" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Templates
            </TabsTrigger>
            <TabsTrigger value="search" className="flex items-center gap-2">
              <Search className="h-4 w-4" />
              Search
            </TabsTrigger>
            <TabsTrigger value="analytics" className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Analytics
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
          <div className="space-y-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
                  <Zap className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{tenantConfig?.current_usage?.total_requests || 0}</div>
                  <p className="text-xs text-muted-foreground">This month</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Tokens Used</CardTitle>
                  <Brain className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{tenantConfig?.current_usage?.total_tokens?.toLocaleString() || 0}</div>
                  <p className="text-xs text-muted-foreground">Total tokens processed</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Cost</CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">${tenantConfig?.current_usage?.total_cost_dollars?.toFixed(2) || '0.00'}</div>
                  <p className="text-xs text-muted-foreground">This month</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
                  <MessageSquare className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{Math.round(tenantConfig?.current_usage?.avg_response_time_ms || 0)}ms</div>
                  <p className="text-xs text-muted-foreground">Average processing time</p>
                </CardContent>
              </Card>
            </div>

            {/* WebSocket Connection Status */}
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                    <span className="text-sm font-medium">
                      Real-time Updates: {isConnected ? 'CONNECTED' : 'DISCONNECTED'}
                    </span>
                  </div>
                  <Badge variant={isConnected ? 'default' : 'destructive'}>
                    {connectionStatus.toUpperCase()}
                  </Badge>
                </div>
                {isConnected && (
                  <p className="text-xs text-muted-foreground mt-1">
                    AI job updates will appear automatically as they process
                  </p>
                )}
                {!isConnected && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Real-time updates unavailable - refresh page to see latest changes
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Job Types Overview */}
            <Card>
              <CardHeader>
                <CardTitle>AI Job Types</CardTitle>
                <CardDescription>Available AI processing capabilities</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {Object.entries(JOB_TYPE_CONFIG).map(([type, config]) => {
                    const Icon = config.icon
                    const jobCount = jobs.filter(job => job.job_type === type).length
                    
                    return (
                      <div key={type} className="flex items-center space-x-3 p-3 rounded-lg border hover:bg-gray-50">
                        <div className={`${config.color} p-2 rounded-lg`}>
                          <Icon className="h-5 w-5 text-white" />
                        </div>
                        <div className="flex-1">
                          <h4 className="text-sm font-medium">{config.label}</h4>
                          <p className="text-xs text-gray-500">{config.description}</p>
                          <p className="text-xs text-blue-600">{jobCount} recent jobs</p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Recent Jobs */}
            <Card>
              <CardHeader>
                <CardTitle>Recent AI Jobs</CardTitle>
                <CardDescription>Latest AI processing requests</CardDescription>
              </CardHeader>
              <CardContent>
                {jobs.length === 0 ? (
                  <div className="text-center py-8">
                    <Brain className="mx-auto h-8 w-8 text-gray-400 mb-2" />
                    <p className="text-gray-500">No AI jobs yet</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {jobs.slice(0, 5).map((job) => {
                      const config = JOB_TYPE_CONFIG[job.job_type as keyof typeof JOB_TYPE_CONFIG]
                      const Icon = config?.icon || Brain
                      const StatusIcon = getStatusIcon(job.status)
                      
                      return (
                        <div key={job.id} className="border rounded-lg p-3 hover:bg-gray-50 transition-colors">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                              <div className={`${config?.color || 'bg-gray-500'} p-2 rounded-lg`}>
                                <Icon className="h-4 w-4 text-white" />
                              </div>
                              <div className="flex-1">
                                <div className="flex items-center space-x-2">
                                  <h4 className="text-sm font-medium">{config?.label || job.job_type}</h4>
                                  <Badge className={getStatusColor(job.status)}>
                                    <StatusIcon className="h-3 w-3 mr-1" />
                                    {job.status}
                                  </Badge>
                                </div>
                                <div className="mt-1 space-y-1">
                                  <p className="text-xs text-gray-600 flex items-center">
                                    <Database className="h-3 w-3 mr-1" />
                                    {job.pipeline?.name || 'No Pipeline'} • {job.field_name || 'No Field'}
                                  </p>
                                  <p className="text-xs text-gray-500 flex items-center">
                                    <User className="h-3 w-3 mr-1" />
                                    {job.created_by?.name || 'Unknown'} • {job.model_name}
                                  </p>
                                  {job.error_message && (
                                    <p className="text-xs text-red-500 flex items-center">
                                      <AlertTriangle className="h-3 w-3 mr-1" />
                                      {job.error_message.slice(0, 50)}...
                                    </p>
                                  )}
                                </div>
                              </div>
                            </div>
                            <div className="text-right space-y-1">
                              <p className="text-sm font-medium">{job.tokens_used.toLocaleString()} tokens</p>
                              <p className="text-xs text-gray-500">${(job.cost_cents / 100).toFixed(4)}</p>
                              <p className="text-xs text-gray-400 flex items-center">
                                <Clock className="h-3 w-3 mr-1" />
                                {formatDuration(job.processing_time_ms)}
                              </p>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
          </TabsContent>

          <TabsContent value="jobs">
          <Card>
            <CardHeader>
              <CardTitle>All AI Jobs</CardTitle>
              <CardDescription>Complete list of AI processing jobs</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {jobs.map((job) => {
                  const config = JOB_TYPE_CONFIG[job.job_type as keyof typeof JOB_TYPE_CONFIG]
                  const Icon = config?.icon || Brain
                  const StatusIcon = getStatusIcon(job.status)
                  const isExpanded = expandedJobs.has(job.id)
                  
                  return (
                    <div key={job.id} className="border rounded-lg overflow-hidden">
                      {/* Main Job Header */}
                      <div className="p-4 bg-gray-50 border-b">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-4">
                            <div className={`${config?.color || 'bg-gray-500'} p-2 rounded-lg`}>
                              <Icon className="h-5 w-5 text-white" />
                            </div>
                            <div>
                              <div className="flex items-center space-x-2">
                                <h4 className="font-semibold text-lg">{config?.label || job.job_type}</h4>
                                <Badge className={getStatusColor(job.status)}>
                                  <StatusIcon className="h-3 w-3 mr-1" />
                                  {job.status}
                                </Badge>
                              </div>
                              <div className="flex items-center space-x-4 mt-1">
                                <p className="text-sm text-gray-600 flex items-center">
                                  <Database className="h-4 w-4 mr-1" />
                                  {job.pipeline?.name || 'No Pipeline'} • {job.field_name || 'No Field'}
                                </p>
                                <p className="text-sm text-gray-500 flex items-center">
                                  <User className="h-4 w-4 mr-1" />
                                  {job.created_by?.name || 'Unknown User'}
                                </p>
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center space-x-4">
                            <div className="text-right">
                              <p className="text-lg font-semibold">{job.tokens_used.toLocaleString()} tokens</p>
                              <p className="text-sm text-gray-500">${(job.cost_cents / 100).toFixed(4)}</p>
                              <p className="text-xs text-gray-400 flex items-center justify-end">
                                <Clock className="h-3 w-3 mr-1" />
                                {formatDuration(job.processing_time_ms)}
                              </p>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => toggleJobExpanded(job.id)}
                              className="ml-2"
                            >
                              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                            </Button>
                          </div>
                        </div>
                      </div>

                      {/* Detailed Information (Expandable) */}
                      {isExpanded && (
                        <div className="p-4 space-y-4">
                          {/* Model & Configuration */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <h5 className="font-medium text-gray-900">AI Configuration</h5>
                              <div className="text-sm space-y-1">
                                <p><span className="font-medium">Provider:</span> {job.ai_provider}</p>
                                <p><span className="font-medium">Model:</span> {job.model_name}</p>
                                <p><span className="font-medium">Temperature:</span> {job.ai_config?.temperature || 'N/A'}</p>
                                <p><span className="font-medium">Max Tokens:</span> {job.ai_config?.max_tokens || 'N/A'}</p>
                                <p><span className="font-medium">Retries:</span> {job.retry_count}/{job.max_retries}</p>
                              </div>
                            </div>
                            <div className="space-y-2">
                              <h5 className="font-medium text-gray-900">Timing Information</h5>
                              <div className="text-sm space-y-1">
                                <p><span className="font-medium">Created:</span> {new Date(job.created_at).toLocaleString()}</p>
                                <p><span className="font-medium">Updated:</span> {new Date(job.updated_at).toLocaleString()}</p>
                                {job.completed_at && (
                                  <p><span className="font-medium">Completed:</span> {new Date(job.completed_at).toLocaleString()}</p>
                                )}
                                <p><span className="font-medium">Duration:</span> {formatDuration(job.processing_time_ms)}</p>
                                {job.record_id && (
                                  <p><span className="font-medium">Record ID:</span> {job.record_id}</p>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Prompt Template */}
                          <div className="space-y-2">
                            <div className="flex items-center justify-between">
                              <h5 className="font-medium text-gray-900">Prompt Template</h5>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => copyToClipboard(job.prompt_template)}
                                className="h-6 px-2"
                              >
                                <Copy className="h-3 w-3" />
                              </Button>
                            </div>
                            <div className="bg-gray-100 p-3 rounded-md text-sm font-mono">
                              {job.prompt_template || 'No prompt template'}
                            </div>
                          </div>

                          {/* Error Message (if failed) */}
                          {job.status === 'failed' && job.error_message && (
                            <div className="space-y-2">
                              <h5 className="font-medium text-red-700 flex items-center">
                                <AlertTriangle className="h-4 w-4 mr-2" />
                                Error Details
                              </h5>
                              <div className="bg-red-50 border border-red-200 p-3 rounded-md text-sm text-red-700">
                                {job.error_message}
                              </div>
                            </div>
                          )}

                          {/* Generated Content (if completed) */}
                          {job.status === 'completed' && job.output_data?.content && (
                            <div className="space-y-2">
                              <div className="flex items-center justify-between">
                                <h5 className="font-medium text-green-700 flex items-center">
                                  <CheckCircle className="h-4 w-4 mr-2" />
                                  Generated Content
                                  {job.output_data?.saved_to_field && (
                                    <Badge variant="secondary" className="ml-2 bg-green-100 text-green-700 text-xs">
                                      Saved to field
                                    </Badge>
                                  )}
                                </h5>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => copyToClipboard(job.output_data.content)}
                                  className="h-6 px-2"
                                >
                                  <Copy className="h-3 w-3" />
                                </Button>
                              </div>
                              <div className="bg-green-50 border border-green-200 p-3 rounded-md text-sm max-h-40 overflow-y-auto">
                                {job.output_data.content}
                              </div>
                              
                              {/* Field Save Status */}
                              {job.field_name && (
                                <div className="text-xs text-gray-500 flex items-center">
                                  {job.output_data?.saved_to_field ? (
                                    <>
                                      <CheckCircle className="h-3 w-3 mr-1 text-green-600" />
                                      Content saved to field: <code className="ml-1 bg-gray-100 px-1 rounded">{job.field_name}</code>
                                    </>
                                  ) : (
                                    <>
                                      <XCircle className="h-3 w-3 mr-1 text-orange-600" />
                                      Field save failed: <code className="ml-1 bg-gray-100 px-1 rounded">{job.field_name}</code>
                                    </>
                                  )}
                                </div>
                              )}
                            </div>
                          )}

                          {/* Input Data Summary */}
                          {job.input_data && Object.keys(job.input_data).length > 0 && (
                            <div className="space-y-2">
                              <h5 className="font-medium text-gray-900 flex items-center">
                                <Database className="h-4 w-4 mr-2" />
                                Input Data Processing
                              </h5>
                              <div className="text-sm text-gray-600 space-y-2">
                                <div>
                                  <span className="font-medium">Fields processed:</span> {Object.keys(job.input_data).join(', ')}
                                </div>
                                
                                {/* Excluded Fields Information */}
                                {job.ai_config?.excluded_fields && job.ai_config.excluded_fields.length > 0 && (
                                  <div className="bg-orange-50 border border-orange-200 p-2 rounded">
                                    <div className="flex items-center text-orange-700 text-xs font-medium mb-1">
                                      <AlertTriangle className="h-3 w-3 mr-1" />
                                      Security: Excluded Fields
                                    </div>
                                    <div className="text-orange-600 text-xs">
                                      {job.ai_config.excluded_fields.length} field(s) excluded for privacy: {job.ai_config.excluded_fields.join(', ')}
                                    </div>
                                  </div>
                                )}
                                
                                {/* Show if no exclusions */}
                                {(!job.ai_config?.excluded_fields || job.ai_config.excluded_fields.length === 0) && (
                                  <div className="bg-green-50 border border-green-200 p-2 rounded">
                                    <div className="flex items-center text-green-700 text-xs">
                                      <CheckCircle className="h-3 w-3 mr-1" />
                                      All record fields were included in AI processing
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
          </TabsContent>

          <TabsContent value="management">
          <div className="space-y-6">
            {/* Worker Health Status */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>System Health</CardTitle>
                  <CardDescription>Celery worker status and queue monitoring</CardDescription>
                </div>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => { loadWorkerHealth(); loadSystemDiagnostics(); }}
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
              </CardHeader>
              <CardContent>
                {workerHealth ? (
                  <div className="space-y-4">
                    {/* Health Status Banner */}
                    <div className={`p-4 rounded-lg flex items-center justify-between ${
                      workerHealth.health_status === 'healthy' ? 'bg-green-50 border-green-200' :
                      workerHealth.health_status === 'no_workers' ? 'bg-red-50 border-red-200' :
                      'bg-yellow-50 border-yellow-200'
                    }`}>
                      <div className="flex items-center space-x-3">
                        <div className={`w-3 h-3 rounded-full ${
                          workerHealth.health_status === 'healthy' ? 'bg-green-500' :
                          workerHealth.health_status === 'no_workers' ? 'bg-red-500' :
                          'bg-yellow-500'
                        }`}></div>
                        <div>
                          <h4 className="font-medium capitalize">{workerHealth.health_status.replace('_', ' ')}</h4>
                          <p className="text-sm text-gray-600">{workerHealth.health_message}</p>
                        </div>
                      </div>
                      <Badge variant={workerHealth.health_status === 'healthy' ? 'default' : 'destructive'}>
                        {workerHealth.health_status.toUpperCase()}
                      </Badge>
                    </div>

                    {/* Statistics Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="bg-blue-50 p-3 rounded-lg">
                        <div className="text-2xl font-bold text-blue-600">{workerHealth.workers_online}</div>
                        <div className="text-sm text-blue-700">Workers Online</div>
                      </div>
                      <div className="bg-orange-50 p-3 rounded-lg">
                        <div className="text-2xl font-bold text-orange-600">{workerHealth.queue_lengths.total}</div>
                        <div className="text-sm text-orange-700">Queued Tasks</div>
                      </div>
                      <div className="bg-yellow-50 p-3 rounded-lg">
                        <div className="text-2xl font-bold text-yellow-600">{workerHealth.job_counts.pending}</div>
                        <div className="text-sm text-yellow-700">Pending Jobs</div>
                      </div>
                      <div className="bg-purple-50 p-3 rounded-lg">
                        <div className="text-2xl font-bold text-purple-600">{workerHealth.job_counts.processing}</div>
                        <div className="text-sm text-purple-700">Processing</div>
                      </div>
                    </div>

                    {/* Queue Details */}
                    <div className="border rounded-lg p-4">
                      <h5 className="font-medium mb-3">Queue Status</h5>
                      <div className="space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="text-sm">AI Processing Queue:</span>
                          <Badge variant="outline">{workerHealth.queue_lengths.ai_processing} tasks</Badge>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm">General Queue:</span>
                          <Badge variant="outline">{workerHealth.queue_lengths.celery} tasks</Badge>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm">Maintenance Queue:</span>
                          <Badge variant="outline">{workerHealth.queue_lengths.maintenance} tasks</Badge>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-center py-8">
                    <Button onClick={loadWorkerHealth} variant="outline">
                      <Activity className="h-4 w-4 mr-2" />
                      Check Worker Health
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Bulk Operations */}
            <Card>
              <CardHeader>
                <CardTitle>Bulk Operations</CardTitle>
                <CardDescription>Manage multiple AI jobs at once</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Button 
                    onClick={performBulkRetry} 
                    disabled={bulkOperationLoading}
                    className="flex items-center justify-center"
                    variant="outline"
                  >
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Retry All Failed
                  </Button>
                  <Button 
                    onClick={performBulkCancel} 
                    disabled={bulkOperationLoading}
                    className="flex items-center justify-center"
                    variant="outline"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Cancel All Pending
                  </Button>
                  <Button 
                    onClick={performQueuePending} 
                    disabled={bulkOperationLoading}
                    className="flex items-center justify-center"
                    variant="default"
                  >
                    <PlayCircle className="h-4 w-4 mr-2" />
                    Queue Pending Jobs
                  </Button>
                </div>
                {bulkOperationLoading && (
                  <div className="mt-4 text-center">
                    <div className="flex items-center justify-center space-x-2">
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      <span className="text-sm text-gray-600">Processing bulk operation...</span>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* System Diagnostics */}
            <Card>
              <CardHeader>
                <CardTitle>System Diagnostics</CardTitle>
                <CardDescription>Detailed system health information</CardDescription>
              </CardHeader>
              <CardContent>
                {systemDiagnostics ? (
                  <div className="space-y-6">
                    {/* Overall Health */}
                    <div className={`p-4 rounded-lg ${
                      systemDiagnostics.overall_health.status === 'healthy' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
                    }`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <h5 className="font-medium">Overall System Health</h5>
                          <p className="text-sm text-gray-600">
                            {systemDiagnostics.overall_health.status === 'healthy' ? 
                              'All systems operational' : 
                              `${systemDiagnostics.overall_health.issues_count} issues detected`}
                          </p>
                        </div>
                        <Badge variant={systemDiagnostics.overall_health.status === 'healthy' ? 'default' : 'destructive'}>
                          {systemDiagnostics.overall_health.status}
                        </Badge>
                      </div>
                      {systemDiagnostics.overall_health.issues.length > 0 && (
                        <div className="mt-3">
                          <h6 className="text-sm font-medium mb-2">Issues:</h6>
                          <ul className="text-sm space-y-1">
                            {systemDiagnostics.overall_health.issues.map((issue, index) => (
                              <li key={index} className="flex items-center">
                                <AlertTriangle className="h-3 w-3 mr-2 text-red-500" />
                                {issue}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    {/* Configuration Status */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="border rounded-lg p-4">
                        <h5 className="font-medium mb-3">AI Configuration</h5>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span>AI Enabled:</span>
                            <Badge variant={systemDiagnostics.ai_config.ai_enabled ? 'default' : 'secondary'}>
                              {systemDiagnostics.ai_config.ai_enabled ? 'Yes' : 'No'}
                            </Badge>
                          </div>
                          <div className="flex justify-between">
                            <span>OpenAI Key:</span>
                            <Badge variant={systemDiagnostics.ai_config.has_openai_key ? 'default' : 'secondary'}>
                              {systemDiagnostics.ai_config.has_openai_key ? 'Configured' : 'Missing'}
                            </Badge>
                          </div>
                          <div className="flex justify-between">
                            <span>Default Model:</span>
                            <span className="text-gray-600">{systemDiagnostics.ai_config.default_model}</span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="border rounded-lg p-4">
                        <h5 className="font-medium mb-3">Job Statistics</h5>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span>Total Jobs:</span>
                            <span className="font-medium">{systemDiagnostics.job_stats.total_jobs}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Pending:</span>
                            <Badge variant={systemDiagnostics.job_stats.pending > 0 ? 'secondary' : 'default'}>
                              {systemDiagnostics.job_stats.pending}
                            </Badge>
                          </div>
                          <div className="flex justify-between">
                            <span>Failed:</span>
                            <Badge variant={systemDiagnostics.job_stats.failed > 0 ? 'destructive' : 'default'}>
                              {systemDiagnostics.job_stats.failed}
                            </Badge>
                          </div>
                          <div className="flex justify-between">
                            <span>Completed:</span>
                            <Badge variant="default">{systemDiagnostics.job_stats.completed}</Badge>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Recent Errors */}
                    {systemDiagnostics.recent_errors.length > 0 && (
                      <div className="border rounded-lg p-4">
                        <h5 className="font-medium mb-3 flex items-center">
                          <AlertTriangle className="h-4 w-4 mr-2 text-red-500" />
                          Recent Errors
                        </h5>
                        <div className="space-y-2">
                          {systemDiagnostics.recent_errors.map((error, index) => (
                            <div key={index} className="bg-red-50 p-3 rounded text-sm">
                              <div className="flex justify-between items-start mb-1">
                                <span className="font-medium">Job {error.job_id}</span>
                                <span className="text-xs text-gray-500">{new Date(error.failed_at).toLocaleString()}</span>
                              </div>
                              <p className="text-red-700 mb-1">{error.error_message}</p>
                              <div className="flex justify-between items-center">
                                <span className="text-xs text-gray-600">Retries: {error.retry_count}</span>
                                {error.can_retry && <Badge variant="outline" className="text-xs">Can Retry</Badge>}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center justify-center py-8">
                    <Button onClick={loadSystemDiagnostics} variant="outline">
                      <Activity className="h-4 w-4 mr-2" />
                      Run System Diagnostics
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
          </TabsContent>

          <TabsContent value="templates">
          <Card>
            <CardHeader>
              <CardTitle>AI Prompt Templates</CardTitle>
              <CardDescription>Reusable AI prompt templates</CardDescription>
            </CardHeader>
            <CardContent>
              {templates.length === 0 ? (
                <div className="text-center py-8">
                  <FileText className="mx-auto h-8 w-8 text-gray-400 mb-2" />
                  <p className="text-gray-500">No prompt templates yet</p>
                  <PermissionGuard category="ai_features" action="create">
                    <Button className="mt-4" variant="outline">
                      <Plus className="h-4 w-4 mr-2" />
                      Create Template
                    </Button>
                  </PermissionGuard>
                </div>
              ) : (
                <div className="space-y-4">
                  {templates.map((template) => (
                    <div key={template.id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center space-x-4">
                        <div className="bg-purple-500 p-2 rounded-lg">
                          <FileText className="h-5 w-5 text-white" />
                        </div>
                        <div>
                          <h4 className="font-medium">{template.name}</h4>
                          <p className="text-sm text-gray-500">{template.description}</p>
                          <p className="text-xs text-gray-400">
                            {template.ai_provider} • {template.model_name} • v{template.version}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="text-right">
                          <Badge variant={template.is_active ? 'default' : 'secondary'}>
                            {template.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                          <p className="text-xs text-gray-500 mt-1">
                            {template.required_variables.length} variables
                          </p>
                        </div>
                        <PermissionGuard category="ai_features" action="update">
                          <Button variant="outline" size="sm">
                            Edit
                          </Button>
                        </PermissionGuard>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
          </TabsContent>

          <TabsContent value="search">
          <Card>
            <CardHeader>
              <CardTitle>Semantic Search</CardTitle>
              <CardDescription>Search and explore AI-generated embeddings</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex gap-4">
                  <Input 
                    placeholder="Search for content using natural language..."
                    className="flex-1"
                  />
                  <Button>
                    <Search className="h-4 w-4 mr-2" />
                    Search
                  </Button>
                </div>
                <div className="text-center py-8">
                  <Search className="mx-auto h-8 w-8 text-gray-400 mb-2" />
                  <p className="text-gray-500">Enter a search query to find related content</p>
                </div>
              </div>
            </CardContent>
          </Card>
          </TabsContent>

          <TabsContent value="analytics">
          <Card>
            <CardHeader>
              <CardTitle>AI Analytics</CardTitle>
              <CardDescription>Detailed usage analytics and insights</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <BarChart3 className="mx-auto h-8 w-8 text-gray-400 mb-2" />
                <p className="text-gray-500">Advanced analytics dashboard coming soon</p>
              </div>
            </CardContent>
          </Card>
          </TabsContent>

        </Tabs>

        {/* Configuration Modal */}
        <TenantConfigModal
          isOpen={configModalOpen}
          onClose={() => setConfigModalOpen(false)}
          onSaved={loadAIData}
        />
      </div>
    </PermissionGuard>
  )
}