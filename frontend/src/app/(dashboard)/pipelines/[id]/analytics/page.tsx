'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { 
  TrendingUp,
  Users,
  Calendar,
  BarChart3,
  Activity,
  Download
} from 'lucide-react'
import { pipelinesApi } from '@/lib/api'

export default function PipelineAnalyticsPage() {
  const params = useParams()
  const pipelineId = params.id as string
  const [pipeline, setPipeline] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [dateRange, setDateRange] = useState('30days')

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        const response = await pipelinesApi.get(pipelineId)
        setPipeline(response.data)
      } catch (error) {
        console.error('Failed to load analytics:', error)
      } finally {
        setLoading(false)
      }
    }

    if (pipelineId) {
      loadData()
    }
  }, [pipelineId])

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-300 dark:bg-gray-600 rounded w-1/3 mb-8"></div>
          <div className="grid grid-cols-2 gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-64 bg-gray-300 dark:bg-gray-600 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Pipeline Analytics
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Performance metrics and usage statistics for {pipeline?.name}
          </p>
        </div>
        
        <div className="flex gap-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
          >
            <option value="7days">Last 7 days</option>
            <option value="30days">Last 30 days</option>
            <option value="90days">Last 90 days</option>
            <option value="1year">Last year</option>
          </select>
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md flex items-center">
            <Download className="w-4 h-4 mr-2" />
            Export Report
          </button>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <MetricCard
          icon={<TrendingUp className="w-5 h-5" />}
          label="Record Growth"
          value="+12.5%"
          subtext="vs last period"
          color="green"
        />
        <MetricCard
          icon={<Users className="w-5 h-5" />}
          label="Active Users"
          value="23"
          subtext="This month"
          color="blue"
        />
        <MetricCard
          icon={<Activity className="w-5 h-5" />}
          label="API Calls"
          value="1.2K"
          subtext="Daily average"
          color="purple"
        />
        <MetricCard
          icon={<Calendar className="w-5 h-5" />}
          label="Peak Activity"
          value="2-4pm"
          subtext="Weekdays"
          color="orange"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartPlaceholder title="Record Growth" type="line" />
        <ChartPlaceholder title="Field Usage" type="bar" />
        <ChartPlaceholder title="User Activity Heatmap" type="heatmap" />
        <ChartPlaceholder title="API Performance" type="area" />
      </div>
    </div>
  )
}

function MetricCard({ icon, label, value, subtext, color }: any) {
  const colorClasses: any = {
    green: 'bg-green-50 dark:bg-green-900/20 text-green-600',
    blue: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600',
    purple: 'bg-purple-50 dark:bg-purple-900/20 text-purple-600',
    orange: 'bg-orange-50 dark:bg-orange-900/20 text-orange-600'
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div className={`inline-flex p-2 rounded-lg ${colorClasses[color]} mb-3`}>
        {icon}
      </div>
      <div className="text-2xl font-bold text-gray-900 dark:text-white">{value}</div>
      <div className="text-sm text-gray-600 dark:text-gray-400">{label}</div>
      <div className="text-xs text-gray-500 mt-1">{subtext}</div>
    </div>
  )
}

function ChartPlaceholder({ title, type }: any) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">{title}</h3>
      <div className="h-64 bg-gray-100 dark:bg-gray-700 rounded flex items-center justify-center">
        <div className="text-center">
          <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-500">{type} chart visualization</p>
        </div>
      </div>
    </div>
  )
}