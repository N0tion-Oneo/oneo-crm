'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { 
  Database, 
  FileText, 
  Users, 
  Clock,
  TrendingUp,
  Settings,
  Download,
  Copy,
  Archive,
  Activity,
  ChevronRight,
  AlertCircle,
  Lock
} from 'lucide-react'
import { pipelinesApi } from '@/lib/api'
import Link from 'next/link'
import { useAuth } from '@/features/auth/context'
import { PermissionGuard } from '@/components/permissions/PermissionGuard'

interface PipelineStats {
  fieldCount: number
  recordCount: number
  businessRules: number
  activeUsers: number
  lastModified: string
  createdAt: string
  weeklyGrowth: number
  totalViews: number
}

interface ActivityItem {
  id: string
  action: string
  user: string
  timestamp: string
  details?: string
}

export default function PipelineOverviewPage() {
  const params = useParams()
  const router = useRouter()
  const { hasPermission } = useAuth()
  const pipelineId = params.id as string
  const [pipeline, setPipeline] = useState<any>(null)
  const [stats, setStats] = useState<PipelineStats | null>(null)
  const [recentActivity, setRecentActivity] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(true)
  
  // Check permissions
  const canReadPipeline = hasPermission('pipelines', 'read')
  const canUpdatePipeline = hasPermission('pipelines', 'update')
  const canDeletePipeline = hasPermission('pipelines', 'delete')

  useEffect(() => {
    const loadPipelineData = async () => {
      try {
        setLoading(true)
        
        // Load pipeline details
        const response = await pipelinesApi.get(pipelineId)
        setPipeline(response.data)
        
        // Load field count
        const fieldsResponse = await pipelinesApi.getFields(pipelineId)
        const fieldCount = fieldsResponse.data?.length || 0
        
        // Set stats (mock data for now - will be replaced with real API calls)
        setStats({
          fieldCount,
          recordCount: response.data.record_count || 0,
          businessRules: 5, // Mock
          activeUsers: 3, // Mock
          lastModified: response.data.updated_at || new Date().toISOString(),
          createdAt: response.data.created_at || new Date().toISOString(),
          weeklyGrowth: 12.5, // Mock
          totalViews: 1234 // Mock
        })
        
        // Set mock recent activity
        setRecentActivity([
          {
            id: '1',
            action: 'Field Added',
            user: 'John Doe',
            timestamp: '2 hours ago',
            details: 'Added field "Deal Value"'
          },
          {
            id: '2',
            action: 'Business Rule Updated',
            user: 'Sarah Smith',
            timestamp: '5 hours ago',
            details: 'Modified stage requirements'
          },
          {
            id: '3',
            action: 'Records Imported',
            user: 'Mike Johnson',
            timestamp: '1 day ago',
            details: '50 new records imported'
          },
          {
            id: '4',
            action: 'Field Deleted',
            user: 'Emily Brown',
            timestamp: '2 days ago',
            details: 'Removed field "Legacy Code"'
          }
        ])
      } catch (error) {
        console.error('Failed to load pipeline data:', error)
      } finally {
        setLoading(false)
      }
    }

    if (pipelineId) {
      loadPipelineData()
    }
  }, [pipelineId])

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const handleQuickAction = (action: string) => {
    switch (action) {
      case 'export':
        router.push(`/pipelines/${pipelineId}/import-export`)
        break
      case 'clone':
        // TODO: Implement clone functionality
        console.log('Clone pipeline')
        break
      case 'archive':
        // TODO: Implement archive functionality
        console.log('Archive pipeline')
        break
    }
  }

  // Check if user can read pipelines before loading
  if (!canReadPipeline) {
    return (
      <div className="p-8">
        <div className="text-center">
          <Lock className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Access Denied
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            You don't have permission to view this pipeline.
          </p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-300 dark:bg-gray-600 rounded w-1/3 mb-4"></div>
          <div className="grid grid-cols-4 gap-4 mb-8">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-24 bg-gray-300 dark:bg-gray-600 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!pipeline) {
    return (
      <div className="p-8">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Pipeline not found
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            The pipeline you're looking for doesn't exist or you don't have access to it.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              {pipeline.name}
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              {pipeline.description || 'No description provided'}
            </p>
            <div className="flex items-center gap-4 mt-3 text-sm text-gray-500 dark:text-gray-400">
              <span className="capitalize bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                {pipeline.pipeline_type || 'Custom'}
              </span>
              <span>Created {formatDate(stats?.createdAt || '')}</span>
              <span>Modified {formatDate(stats?.lastModified || '')}</span>
            </div>
          </div>
          
          {/* Quick Actions */}
          <div className="flex gap-2">
            <PermissionGuard 
              category="pipelines" 
              action="read"
              fallback={
                <button
                  disabled
                  className="px-3 py-2 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md flex items-center text-sm opacity-50 cursor-not-allowed"
                  title="You don't have permission to export pipelines"
                >
                  <Lock className="w-4 h-4 mr-1" />
                  Export
                </button>
              }
            >
              <button
                onClick={() => handleQuickAction('export')}
                className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center text-sm"
              >
                <Download className="w-4 h-4 mr-1" />
                Export
              </button>
            </PermissionGuard>
            
            <PermissionGuard 
              category="pipelines" 
              action="create"
              fallback={
                <button
                  disabled
                  className="px-3 py-2 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md flex items-center text-sm opacity-50 cursor-not-allowed"
                  title="You don't have permission to clone pipelines"
                >
                  <Lock className="w-4 h-4 mr-1" />
                  Clone
                </button>
              }
            >
              <button
                onClick={() => handleQuickAction('clone')}
                className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center text-sm"
              >
                <Copy className="w-4 h-4 mr-1" />
                Clone
              </button>
            </PermissionGuard>
            
            <PermissionGuard 
              category="pipelines" 
              action="delete"
              fallback={
                <button
                  disabled
                  className="px-3 py-2 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md flex items-center text-sm opacity-50 cursor-not-allowed"
                  title="You don't have permission to archive pipelines"
                >
                  <Lock className="w-4 h-4 mr-1" />
                  Archive
                </button>
              }
            >
              <button
                onClick={() => handleQuickAction('archive')}
                className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center text-sm"
              >
                <Archive className="w-4 h-4 mr-1" />
                Archive
              </button>
            </PermissionGuard>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={<Database className="w-5 h-5" />}
          label="Fields"
          value={stats?.fieldCount || 0}
          trend={null}
          color="blue"
        />
        <StatCard
          icon={<FileText className="w-5 h-5" />}
          label="Records"
          value={stats?.recordCount || 0}
          trend={stats?.weeklyGrowth}
          color="green"
        />
        <StatCard
          icon={<Settings className="w-5 h-5" />}
          label="Business Rules"
          value={stats?.businessRules || 0}
          trend={null}
          color="purple"
        />
        <StatCard
          icon={<Users className="w-5 h-5" />}
          label="Active Users"
          value={stats?.activeUsers || 0}
          trend={null}
          color="orange"
        />
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Recent Activity
              </h2>
              <Link
                href={`/pipelines/${pipelineId}/activity`}
                className="text-sm text-blue-600 dark:text-blue-400 hover:underline flex items-center"
              >
                View all
                <ChevronRight className="w-4 h-4 ml-1" />
              </Link>
            </div>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {recentActivity.map(item => (
                <div key={item.id} className="flex items-start">
                  <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {item.action}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      {item.details}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                      {item.user} • {item.timestamp}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Quick Links */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Configuration Areas
            </h2>
          </div>
          <div className="p-6">
            <div className="space-y-3">
              <QuickLink
                href={`/pipelines/${pipelineId}/fields`}
                icon={<Database className="w-5 h-5" />}
                title="Field Configuration"
                description="Manage pipeline fields and data structure"
              />
              <QuickLink
                href={`/pipelines/${pipelineId}/business-rules`}
                icon={<FileText className="w-5 h-5" />}
                title="Business Rules"
                description="Configure validation and automation"
              />
              <QuickLink
                href={`/pipelines/${pipelineId}/duplicates`}
                icon={<Copy className="w-5 h-5" />}
                title="Duplicate Management"
                description="Set up duplicate detection"
              />
              <QuickLink
                href={`/pipelines/${pipelineId}/analytics`}
                icon={<TrendingUp className="w-5 h-5" />}
                title="Analytics"
                description="View performance metrics"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

interface StatCardProps {
  icon: React.ReactNode
  label: string
  value: number | string
  trend?: number | null
  color: 'blue' | 'green' | 'purple' | 'orange'
}

function StatCard({ icon, label, value, trend, color }: StatCardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400',
    green: 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400',
    purple: 'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400',
    orange: 'bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400'
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center justify-between mb-2">
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
        {trend !== null && trend !== undefined && (
          <span className={`text-sm font-medium ${
            trend > 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {trend > 0 ? '+' : ''}{trend}%
          </span>
        )}
      </div>
      <div className="text-2xl font-bold text-gray-900 dark:text-white">
        {value}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        {label}
      </div>
    </div>
  )
}

interface QuickLinkProps {
  href: string
  icon: React.ReactNode
  title: string
  description: string
}

function QuickLink({ href, icon, title, description }: QuickLinkProps) {
  return (
    <Link
      href={href}
      className="flex items-start p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
    >
      <div className="text-gray-400 mr-3 mt-0.5">
        {icon}
      </div>
      <div className="flex-1">
        <div className="font-medium text-gray-900 dark:text-white">
          {title}
        </div>
        <div className="text-sm text-gray-600 dark:text-gray-400">
          {description}
        </div>
      </div>
      <ChevronRight className="w-5 h-5 text-gray-400 mt-0.5" />
    </Link>
  )
}