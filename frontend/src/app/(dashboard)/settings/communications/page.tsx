'use client'

import { useState, useEffect } from 'react'
import { 
  MessageCircle, 
  Users, 
  Link2, 
  Settings, 
  TrendingUp, 
  Activity, 
  AlertCircle, 
  CheckCircle2, 
  Clock, 
  Loader2, 
  ArrowRight,
  Mail,
  MessageSquare,
  Building2,
  Shield,
  Zap
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/features/auth/context'
import { useRouter } from 'next/navigation'
import { api, communicationsApi } from '@/lib/api'

interface DashboardStats {
  participants: {
    total: number
    eligible: number
    created_today: number
    created_this_week: number
  }
  accounts: {
    total: number
    active: number
    needs_reconnection: number
    by_channel: Record<string, number>
  }
  processing: {
    auto_create_enabled: boolean
    last_batch_run: string | null
    next_scheduled_run: string | null
    batch_size: number
  }
  activity: Array<{
    id: string
    type: string
    message: string
    timestamp: string
    status: 'success' | 'warning' | 'error'
  }>
}

export default function CommunicationsOverviewPage() {
  const { hasPermission } = useAuth()
  const { toast } = useToast()
  const router = useRouter()
  
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [configurations, setConfigurations] = useState<any>(null)

  const canViewSettings = hasPermission('participants', 'settings')
  const canManageAccounts = hasPermission('communications', 'update')
  const canRunBatch = hasPermission('participants', 'batch')

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      
      // Load multiple data sources in parallel
      const [settingsRes, connectionsRes, configRes] = await Promise.all([
        api.get('/api/v1/participant-settings/').catch(() => null),
        communicationsApi.getConnections().catch(() => null),
        communicationsApi.getProviderConfigurations().catch(() => null)
      ])

      // Process the data for dashboard stats
      const participantSettings = settingsRes?.data
      const connections = connectionsRes?.data?.results || []
      const providerConfig = configRes?.data

      // Create dashboard stats
      const dashboardStats: DashboardStats = {
        participants: {
          total: participantSettings?.stats?.total_participants || 0,
          eligible: participantSettings?.stats?.eligible_participants || 0,
          created_today: participantSettings?.stats?.created_today || 0,
          created_this_week: participantSettings?.stats?.created_this_week || 0
        },
        accounts: {
          total: connections.length,
          active: connections.filter((c: any) => c.accountStatus === 'active').length,
          needs_reconnection: connections.filter((c: any) => 
            c.authStatus !== 'authenticated' || c.accountStatus !== 'active'
          ).length,
          by_channel: connections.reduce((acc: any, conn: any) => {
            acc[conn.channelType] = (acc[conn.channelType] || 0) + 1
            return acc
          }, {})
        },
        processing: {
          auto_create_enabled: participantSettings?.auto_create_enabled || false,
          last_batch_run: participantSettings?.last_batch_run,
          next_scheduled_run: participantSettings?.next_scheduled_run,
          batch_size: participantSettings?.batch_size || 100
        },
        activity: participantSettings?.recent_activity || []
      }

      setStats(dashboardStats)
      setConfigurations(providerConfig)
      
    } catch (error: any) {
      console.error('Error loading dashboard data:', error)
      toast({
        title: "Failed to load dashboard",
        description: "Some statistics may be unavailable",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const runBatchProcess = async () => {
    try {
      await api.post('/api/v1/participant-settings/process_batch/', {
        batch_size: stats?.processing.batch_size,
        dry_run: false
      })
      
      toast({
        title: "Batch Processing Started",
        description: "Processing participants in the background",
      })
      
      // Reload stats
      await loadDashboardData()
    } catch (error) {
      toast({
        title: "Processing Failed",
        description: "Failed to start batch processing",
        variant: "destructive",
      })
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </div>
    )
  }

  if (!canViewSettings) {
    return (
      <div className="p-6">
        <div className="text-center py-12">
          <AlertCircle className="h-12 w-12 mx-auto text-amber-500 mb-4" />
          <h3 className="text-lg font-medium">Access Denied</h3>
          <p className="text-gray-600">You don't have permission to view communication settings.</p>
        </div>
      </div>
    )
  }

  const channelIcons: Record<string, any> = {
    email: Mail,
    gmail: Mail,
    outlook: Mail,
    whatsapp: MessageCircle,
    linkedin: MessageSquare
  }

  return (
    <div className="p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Communications Overview
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Monitor and manage your communication settings and integrations
          </p>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Users className="h-4 w-4" />
                Total Participants
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.participants.total || 0}</div>
              <p className="text-xs text-gray-500 mt-1">
                {stats?.participants.eligible || 0} eligible for creation
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Link2 className="h-4 w-4" />
                Connected Accounts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.accounts.total || 0}</div>
              <div className="flex gap-2 mt-1">
                <Badge variant="default" className="text-xs">
                  {stats?.accounts.active || 0} active
                </Badge>
                {(stats?.accounts.needs_reconnection || 0) > 0 && (
                  <Badge variant="destructive" className="text-xs">
                    {stats?.accounts.needs_reconnection} need attention
                  </Badge>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                Created Today
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.participants.created_today || 0}</div>
              <p className="text-xs text-gray-500 mt-1">
                {stats?.participants.created_this_week || 0} this week
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Zap className="h-4 w-4" />
                Auto-Creation
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Badge variant={stats?.processing.auto_create_enabled ? "default" : "secondary"}>
                  {stats?.processing.auto_create_enabled ? "Enabled" : "Disabled"}
                </Badge>
                {stats?.processing.batch_size && (
                  <span className="text-sm text-gray-500">
                    Batch: {stats.processing.batch_size}
                  </span>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Connected Accounts */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Connected Accounts</CardTitle>
                <Button 
                  size="sm" 
                  variant="ghost"
                  onClick={() => router.push('/settings/communications/accounts')}
                >
                  Manage
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
              <CardDescription>
                Your connected communication channels
              </CardDescription>
            </CardHeader>
            <CardContent>
              {stats?.accounts.total === 0 ? (
                <div className="text-center py-8">
                  <Link2 className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500">No accounts connected yet</p>
                  <Button 
                    className="mt-4"
                    onClick={() => router.push('/settings/communications/accounts')}
                  >
                    Connect Account
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {Object.entries(stats?.accounts.by_channel || {}).map(([channel, count]) => {
                    const Icon = channelIcons[channel] || MessageCircle
                    return (
                      <div key={channel} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center gap-3">
                          <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                            <Icon className="h-5 w-5" />
                          </div>
                          <div>
                            <div className="font-medium capitalize">{channel}</div>
                            <div className="text-sm text-gray-500">
                              {count} account{count !== 1 ? 's' : ''} connected
                            </div>
                          </div>
                        </div>
                        <CheckCircle2 className="h-5 w-5 text-green-500" />
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
              <CardDescription>
                Common tasks and operations
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button 
                className="w-full justify-start" 
                variant="outline"
                onClick={() => router.push('/settings/communications/participants')}
              >
                <Users className="mr-2 h-4 w-4" />
                Configure Participants
              </Button>
              <Button 
                className="w-full justify-start" 
                variant="outline"
                onClick={() => router.push('/settings/communications/accounts')}
              >
                <Link2 className="mr-2 h-4 w-4" />
                Connect New Account
              </Button>
              <Button 
                className="w-full justify-start" 
                variant="outline"
                onClick={() => router.push('/settings/communications/providers')}
              >
                <Settings className="mr-2 h-4 w-4" />
                Provider Settings
              </Button>
              {canRunBatch && stats?.processing.auto_create_enabled && (
                <Button 
                  className="w-full justify-start" 
                  variant="outline"
                  onClick={runBatchProcess}
                >
                  <Activity className="mr-2 h-4 w-4" />
                  Run Batch Process
                </Button>
              )}
            </CardContent>
          </Card>
        </div>

        {/* System Status */}
        <Card>
          <CardHeader>
            <CardTitle>System Status</CardTitle>
            <CardDescription>
              Current configuration and health status
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="space-y-1">
                <p className="text-sm text-gray-500">Auto-Creation</p>
                <Badge variant={stats?.processing.auto_create_enabled ? "default" : "secondary"}>
                  {stats?.processing.auto_create_enabled ? "Enabled" : "Disabled"}
                </Badge>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-gray-500">Provider Config</p>
                <Badge variant={configurations?.global_settings?.is_configured ? "default" : "destructive"}>
                  {configurations?.global_settings?.is_configured ? "Configured" : "Not Configured"}
                </Badge>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-gray-500">Real-time Sync</p>
                <Badge variant={configurations?.tenant_config?.enable_real_time_sync ? "default" : "secondary"}>
                  {configurations?.tenant_config?.enable_real_time_sync ? "Active" : "Inactive"}
                </Badge>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-gray-500">Last Batch Run</p>
                <p className="text-sm font-medium">
                  {stats?.processing.last_batch_run 
                    ? new Date(stats.processing.last_batch_run).toLocaleDateString()
                    : 'Never'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}