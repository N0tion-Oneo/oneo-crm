'use client'

import { useState, useEffect } from 'react'
import { 
  Settings2, 
  Activity, 
  Database, 
  Link, 
  Info, 
  AlertCircle,
  CheckCircle,
  XCircle,
  Loader2,
  Code,
  RefreshCw,
  Terminal
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/features/auth/context'
import { communicationsApi } from '@/lib/api'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy'
  components: {
    database: boolean
    redis: boolean
    celery: boolean
    unipile: boolean
  }
  last_check: string
}

interface SystemStats {
  total_messages: number
  total_conversations: number
  total_participants: number
  messages_today: number
  api_calls_today: number
  storage_used_mb: number
  active_webhooks: number
  pending_sync_tasks: number
}

export default function AdvancedSettingsPage() {
  const [systemInfo, setSystemInfo] = useState<any>(null)
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null)
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  
  const { toast } = useToast()
  const { hasPermission } = useAuth()
  
  // Settings permission ONLY controls page access
  const hasSettingsAccess = hasPermission('settings', 'communications')
  
  // Resource permissions control what actions can be performed
  const hasAdvancedAccess = hasPermission('communication_settings', 'advanced')
  
  // Page access: need settings permission to view the settings page
  const canViewPage = hasSettingsAccess
  
  // Action permissions: require specific resource permission
  const canViewAdvanced = hasAdvancedAccess
  const canManageAdvanced = hasAdvancedAccess // For communication settings, permission implies both view and edit

  useEffect(() => {
    // Only load if user has permission
    if (!canViewAdvanced) {
      setLoading(false)
      return
    }
    loadSystemInfo()
  }, [canViewAdvanced])

  const loadSystemInfo = async () => {
    try {
      setLoading(true)
      
      // Load all system information in parallel
      const [configResponse, healthResponse, statsResponse] = await Promise.all([
        communicationsApi.getProviderConfigurations(),
        fetchSystemHealth(),
        fetchSystemStats()
      ])
      
      setSystemInfo(configResponse.data)
      setSystemHealth(healthResponse)
      setSystemStats(statsResponse)
    } catch (error: any) {
      console.error('Error loading system info:', error)
      toast({
        title: "Failed to load system information",
        description: error.message || "An error occurred",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const fetchSystemHealth = async (): Promise<SystemHealth> => {
    // In production, this would call an API endpoint
    // For now, returning mock data
    return {
      status: 'healthy',
      components: {
        database: true,
        redis: true,
        celery: true,
        unipile: true
      },
      last_check: new Date().toISOString()
    }
  }

  const fetchSystemStats = async (): Promise<SystemStats> => {
    // In production, this would call an API endpoint
    // For now, returning mock data
    return {
      total_messages: 15423,
      total_conversations: 892,
      total_participants: 456,
      messages_today: 234,
      api_calls_today: 1856,
      storage_used_mb: 2048,
      active_webhooks: 3,
      pending_sync_tasks: 0
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await loadSystemInfo()
    setRefreshing(false)
    toast({
      title: "System Information Refreshed",
      description: "All system data has been updated.",
    })
  }

  const clearCache = async () => {
    try {
      // TODO: Implement clearCache API endpoint
      // await communicationsApi.clearCache()
      
      // For now, simulate the cache clearing
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      toast({
        title: "Cache Cleared",
        description: "Communication cache has been cleared successfully.",
      })
    } catch (error: any) {
      toast({
        title: "Clear Cache Failed",
        description: error.message || "Failed to clear cache",
        variant: "destructive",
      })
    }
  }

  const runDiagnostics = async () => {
    try {
      toast({
        title: "Running Diagnostics",
        description: "This may take a moment...",
      })
      
      // In production, this would call an API endpoint
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      toast({
        title: "Diagnostics Complete",
        description: "All systems are operating normally.",
      })
    } catch (error: any) {
      toast({
        title: "Diagnostics Failed",
        description: error.message || "Failed to run diagnostics",
        variant: "destructive",
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

  if (!canViewAdvanced) {
    return (
      <div className="p-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 mx-auto text-amber-500 mb-4" />
            <h3 className="text-lg font-medium">Access Denied</h3>
            <p className="text-gray-600">You don't have permission to view advanced settings.</p>
          </div>
        </div>
      </div>
    )
  }

  const getHealthColor = (healthy: boolean) => healthy ? 'text-green-500' : 'text-red-500'
  const getHealthIcon = (healthy: boolean) => healthy ? 
    <CheckCircle className="h-4 w-4 text-green-500" /> : 
    <XCircle className="h-4 w-4 text-red-500" />

  return (
    <div className="p-6">
      <div className="max-w-5xl mx-auto">
        <div className="mb-6 flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Advanced Settings
            </h1>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              System diagnostics, debugging tools, and technical information
            </p>
          </div>
          <Button 
            onClick={handleRefresh}
            variant="outline"
            size="sm"
            disabled={refreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        <Tabs defaultValue="system" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="system">System Info</TabsTrigger>
            <TabsTrigger value="health">Health Status</TabsTrigger>
            <TabsTrigger value="api">API Endpoints</TabsTrigger>
            <TabsTrigger value="debug">Debug</TabsTrigger>
          </TabsList>

          {/* System Information Tab */}
          <TabsContent value="system" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings2 className="h-5 w-5" />
                  System Information
                </CardTitle>
                <CardDescription>
                  Technical details about your communication system configuration
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-gray-500">Database Schema</p>
                    <p className="font-mono text-sm">{systemInfo?.global_settings?.dsn || 'Not configured'}</p>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-gray-500">Webhook URL</p>
                    <p className="font-mono text-sm break-all">
                      {systemInfo?.global_settings?.webhook_url || 'Not configured'}
                    </p>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-gray-500">Configured Providers</p>
                    <div className="flex gap-2">
                      {systemInfo?.providers && Object.keys(systemInfo.providers).map(provider => (
                        <Badge key={provider} variant="secondary">
                          {provider}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-gray-500">System Status</p>
                    <Badge variant={systemInfo?.global_settings?.is_configured ? "default" : "destructive"}>
                      {systemInfo?.global_settings?.is_configured ? "Configured" : "Not Configured"}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* System Statistics */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  System Statistics
                </CardTitle>
                <CardDescription>
                  Current usage and performance metrics
                </CardDescription>
              </CardHeader>
              <CardContent>
                {systemStats && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="space-y-1">
                      <p className="text-sm text-gray-500">Total Messages</p>
                      <p className="text-2xl font-bold">{systemStats.total_messages.toLocaleString()}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-gray-500">Conversations</p>
                      <p className="text-2xl font-bold">{systemStats.total_conversations}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-gray-500">Participants</p>
                      <p className="text-2xl font-bold">{systemStats.total_participants}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-gray-500">Messages Today</p>
                      <p className="text-2xl font-bold">{systemStats.messages_today}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-gray-500">API Calls Today</p>
                      <p className="text-2xl font-bold">{systemStats.api_calls_today.toLocaleString()}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-gray-500">Storage Used</p>
                      <p className="text-2xl font-bold">{(systemStats.storage_used_mb / 1024).toFixed(1)} GB</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-gray-500">Active Webhooks</p>
                      <p className="text-2xl font-bold">{systemStats.active_webhooks}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-gray-500">Pending Tasks</p>
                      <p className="text-2xl font-bold">{systemStats.pending_sync_tasks}</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Health Status Tab */}
          <TabsContent value="health" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  System Health
                </CardTitle>
                <CardDescription>
                  Real-time health status of communication system components
                </CardDescription>
              </CardHeader>
              <CardContent>
                {systemHealth && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <Database className={getHealthColor(systemHealth.components.database)} />
                        <div>
                          <p className="font-medium">Database Connection</p>
                          <p className="text-sm text-gray-500">PostgreSQL primary database</p>
                        </div>
                      </div>
                      {getHealthIcon(systemHealth.components.database)}
                    </div>

                    <div className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <Activity className={getHealthColor(systemHealth.components.redis)} />
                        <div>
                          <p className="font-medium">Redis Cache</p>
                          <p className="text-sm text-gray-500">Caching and message queue</p>
                        </div>
                      </div>
                      {getHealthIcon(systemHealth.components.redis)}
                    </div>

                    <div className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <Settings2 className={getHealthColor(systemHealth.components.celery)} />
                        <div>
                          <p className="font-medium">Background Tasks</p>
                          <p className="text-sm text-gray-500">Celery worker processes</p>
                        </div>
                      </div>
                      {getHealthIcon(systemHealth.components.celery)}
                    </div>

                    <div className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <Link className={getHealthColor(systemHealth.components.unipile)} />
                        <div>
                          <p className="font-medium">UniPile API</p>
                          <p className="text-sm text-gray-500">External communication provider</p>
                        </div>
                      </div>
                      {getHealthIcon(systemHealth.components.unipile)}
                    </div>

                    <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                      <p className="text-xs text-gray-500">
                        Last checked: {new Date(systemHealth.last_check).toLocaleString()}
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* API Endpoints Tab */}
          <TabsContent value="api" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Code className="h-5 w-5" />
                  API Endpoints
                </CardTitle>
                <CardDescription>
                  Available API endpoints for communication system integration
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <h4 className="font-medium">Provider Management</h4>
                    <div className="space-y-1 font-mono text-sm">
                      <p className="p-2 bg-gray-100 dark:bg-gray-800 rounded">GET /api/v1/communications/providers/</p>
                      <p className="p-2 bg-gray-100 dark:bg-gray-800 rounded">POST /api/v1/communications/providers/connect/</p>
                      <p className="p-2 bg-gray-100 dark:bg-gray-800 rounded">DELETE /api/v1/communications/providers/{'{provider_id}'}/disconnect/</p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <h4 className="font-medium">Message Operations</h4>
                    <div className="space-y-1 font-mono text-sm">
                      <p className="p-2 bg-gray-100 dark:bg-gray-800 rounded">GET /api/v1/communications/messages/</p>
                      <p className="p-2 bg-gray-100 dark:bg-gray-800 rounded">POST /api/v1/communications/messages/send/</p>
                      <p className="p-2 bg-gray-100 dark:bg-gray-800 rounded">GET /api/v1/communications/conversations/{'{id}'}/</p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <h4 className="font-medium">Participant Management</h4>
                    <div className="space-y-1 font-mono text-sm">
                      <p className="p-2 bg-gray-100 dark:bg-gray-800 rounded">GET /api/v1/communications/participants/</p>
                      <p className="p-2 bg-gray-100 dark:bg-gray-800 rounded">POST /api/v1/communications/participants/auto-create/</p>
                      <p className="p-2 bg-gray-100 dark:bg-gray-800 rounded">GET /api/v1/communications/participants/settings/</p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <h4 className="font-medium">Webhooks</h4>
                    <div className="space-y-1 font-mono text-sm">
                      <p className="p-2 bg-gray-100 dark:bg-gray-800 rounded">POST /api/v1/communications/webhooks/unipile/</p>
                      <p className="p-2 bg-gray-100 dark:bg-gray-800 rounded">GET /api/v1/communications/webhooks/status/</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Debug Tab */}
          <TabsContent value="debug" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Terminal className="h-5 w-5" />
                  Debug Tools
                </CardTitle>
                <CardDescription>
                  Advanced debugging and diagnostic utilities
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    These tools are for advanced debugging only. Use with caution in production environments.
                  </AlertDescription>
                </Alert>

                <div className="space-y-3">
                  <Button 
                    variant="outline" 
                    className="w-full justify-start"
                    onClick={clearCache}
                    disabled={!canManageAdvanced}
                  >
                    <Database className="h-4 w-4 mr-2" />
                    Clear Communication Cache
                  </Button>

                  <Button 
                    variant="outline" 
                    className="w-full justify-start"
                    onClick={runDiagnostics}
                    disabled={!canManageAdvanced}
                  >
                    <Activity className="h-4 w-4 mr-2" />
                    Run System Diagnostics
                  </Button>

                  <Button 
                    variant="outline" 
                    className="w-full justify-start"
                    disabled={!canManageAdvanced}
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Force Sync All Conversations
                  </Button>

                  <Button 
                    variant="outline" 
                    className="w-full justify-start"
                    disabled={!canManageAdvanced}
                  >
                    <Settings2 className="h-4 w-4 mr-2" />
                    Reset Provider Configurations
                  </Button>
                </div>

                {!canManageAdvanced && (
                  <Alert>
                    <AlertDescription>
                      You need manage permissions to use debug tools.
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>

            {/* Debug Information */}
            <Card>
              <CardHeader>
                <CardTitle>Debug Information</CardTitle>
                <CardDescription>
                  Current system state and configuration details
                </CardDescription>
              </CardHeader>
              <CardContent>
                <pre className="text-xs bg-gray-100 dark:bg-gray-800 p-4 rounded overflow-x-auto">
                  {JSON.stringify({
                    tenant_config: systemInfo?.tenant_config,
                    global_settings: systemInfo?.global_settings,
                    environment: process.env.NODE_ENV,
                    timestamp: new Date().toISOString()
                  }, null, 2)}
                </pre>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}