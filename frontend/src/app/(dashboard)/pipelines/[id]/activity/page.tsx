'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { 
  History,
  Filter,
  Download,
  User,
  Database,
  Settings,
  FileText,
  Plus,
  Trash2,
  Edit,
  ChevronDown
} from 'lucide-react'
import { pipelinesApi } from '@/lib/api'

interface ActivityLogItem {
  id: string
  action: string
  category: string
  user: {
    name: string
    avatar?: string
  }
  timestamp: string
  details: string
  metadata?: {
    field?: string
    oldValue?: any
    newValue?: any
  }
}

export default function ActivityLogPage() {
  const params = useParams()
  const pipelineId = params.id as string
  const [pipeline, setPipeline] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [activityFilter, setActivityFilter] = useState('all')
  const [dateFilter, setDateFilter] = useState('7days')
  const [activities, setActivities] = useState<ActivityLogItem[]>([])

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        const response = await pipelinesApi.get(pipelineId)
        setPipeline(response.data)
        
        // Mock activity data - replace with real API call
        setActivities([
          {
            id: '1',
            action: 'field_added',
            category: 'field',
            user: { name: 'John Doe' },
            timestamp: '2024-01-15T14:30:00Z',
            details: 'Added field "Revenue"',
            metadata: {
              field: 'revenue',
              newValue: { type: 'number', label: 'Revenue' }
            }
          },
          {
            id: '2',
            action: 'rule_updated',
            category: 'business_rule',
            user: { name: 'Sarah Smith' },
            timestamp: '2024-01-15T11:45:00Z',
            details: 'Updated business rule "Stage Requirements"',
            metadata: {
              oldValue: 'required: email',
              newValue: 'required: email, phone'
            }
          },
          {
            id: '3',
            action: 'records_imported',
            category: 'data',
            user: { name: 'Mike Johnson' },
            timestamp: '2024-01-14T09:20:00Z',
            details: '25 records imported',
            metadata: {
              newValue: 25
            }
          },
          {
            id: '4',
            action: 'pipeline_updated',
            category: 'settings',
            user: { name: 'Emily Brown' },
            timestamp: '2024-01-13T16:00:00Z',
            details: 'Changed pipeline name',
            metadata: {
              oldValue: 'Sales',
              newValue: 'Sales Pipeline'
            }
          },
          {
            id: '5',
            action: 'field_deleted',
            category: 'field',
            user: { name: 'John Doe' },
            timestamp: '2024-01-13T15:30:00Z',
            details: 'Deleted field "Legacy Code"',
            metadata: {
              field: 'legacy_code'
            }
          }
        ])
      } catch (error) {
        console.error('Failed to load activity log:', error)
      } finally {
        setLoading(false)
      }
    }

    if (pipelineId) {
      loadData()
    }
  }, [pipelineId, activityFilter, dateFilter])

  const getActionIcon = (action: string) => {
    if (action.includes('add') || action.includes('create')) return <Plus className="w-4 h-4" />
    if (action.includes('delete') || action.includes('remove')) return <Trash2 className="w-4 h-4" />
    if (action.includes('update') || action.includes('edit')) return <Edit className="w-4 h-4" />
    if (action.includes('import')) return <Database className="w-4 h-4" />
    return <Settings className="w-4 h-4" />
  }

  const getActionColor = (action: string) => {
    if (action.includes('add') || action.includes('create')) return 'text-green-600 bg-green-50 dark:bg-green-900/20'
    if (action.includes('delete') || action.includes('remove')) return 'text-red-600 bg-red-50 dark:bg-red-900/20'
    if (action.includes('update') || action.includes('edit')) return 'text-blue-600 bg-blue-50 dark:bg-blue-900/20'
    if (action.includes('import')) return 'text-purple-600 bg-purple-50 dark:bg-purple-900/20'
    return 'text-gray-600 bg-gray-50 dark:bg-gray-900/20'
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const hours = Math.floor(diff / (1000 * 60 * 60))
    const days = Math.floor(hours / 24)
    
    if (hours < 1) return 'Just now'
    if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`
    if (days < 7) return `${days} day${days > 1 ? 's' : ''} ago`
    
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-300 dark:bg-gray-600 rounded w-1/3 mb-8"></div>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="h-20 bg-gray-300 dark:bg-gray-600 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-6xl">
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Activity Log
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Track all changes and actions for {pipeline?.name}
          </p>
        </div>
        
        <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md flex items-center">
          <Download className="w-4 h-4 mr-2" />
          Export Log
        </button>
      </div>

      {/* Filters */}
      <div className="mb-6 flex gap-3">
        <select
          value={activityFilter}
          onChange={(e) => setActivityFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
        >
          <option value="all">All Activities</option>
          <option value="field">Field Changes</option>
          <option value="business_rule">Business Rules</option>
          <option value="data">Data Operations</option>
          <option value="settings">Settings Changes</option>
        </select>
        
        <select
          value={dateFilter}
          onChange={(e) => setDateFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
        >
          <option value="today">Today</option>
          <option value="7days">Last 7 days</option>
          <option value="30days">Last 30 days</option>
          <option value="90days">Last 90 days</option>
          <option value="all">All time</option>
        </select>
      </div>

      {/* Activity Timeline */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6">
          <div className="space-y-4">
            {activities.map((activity, index) => (
              <div key={activity.id} className="relative">
                {index < activities.length - 1 && (
                  <div className="absolute left-6 top-12 bottom-0 w-0.5 bg-gray-200 dark:bg-gray-700"></div>
                )}
                
                <div className="flex items-start">
                  <div className={`p-2 rounded-lg ${getActionColor(activity.action)} mr-4`}>
                    {getActionIcon(activity.action)}
                  </div>
                  
                  <div className="flex-1">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {activity.details}
                        </div>
                        {activity.metadata && (
                          <div className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                            {activity.metadata.oldValue && activity.metadata.newValue && (
                              <span>
                                Changed from <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">
                                  {JSON.stringify(activity.metadata.oldValue)}
                                </code> to <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">
                                  {JSON.stringify(activity.metadata.newValue)}
                                </code>
                              </span>
                            )}
                            {activity.metadata.newValue && !activity.metadata.oldValue && (
                              <span>
                                Added: <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">
                                  {JSON.stringify(activity.metadata.newValue)}
                                </code>
                              </span>
                            )}
                          </div>
                        )}
                        <div className="mt-2 flex items-center text-xs text-gray-500">
                          <User className="w-3 h-3 mr-1" />
                          <span>{activity.user.name}</span>
                          <span className="mx-2">•</span>
                          <span>{formatTimestamp(activity.timestamp)}</span>
                        </div>
                      </div>
                      
                      <button className="text-gray-400 hover:text-gray-600 p-1">
                        <ChevronDown className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          <button className="mt-6 w-full py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">
            Load More
          </button>
        </div>
      </div>
    </div>
  )
}