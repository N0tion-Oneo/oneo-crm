'use client'

import { useState, useEffect } from 'react'
import { 
  BarChart3,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Users,
  Activity,
  Calendar,
  Target,
  Database,
  Zap
} from 'lucide-react'
import { duplicatesApi } from '@/lib/api'

interface DuplicateStats {
  total_rules: number
  active_rules: number
  total_matches: number
  pending_matches: number
  resolved_matches: number
  false_positives: number
  avg_confidence_score: number
  top_performing_rules: Array<{
    rule_id: string
    rule_name: string
    match_count: number
    avg_confidence: number
    action_on_duplicate: string
  }>
  detection_results_count: number
  url_extraction_rules: number
  date_range: {
    start_date: string
    end_date: string
  }
}

interface DuplicateAnalyticsViewProps {
  pipelineId: string
}

export function DuplicateAnalyticsView({ pipelineId }: DuplicateAnalyticsViewProps) {
  const [stats, setStats] = useState<DuplicateStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [dateRange, setDateRange] = useState('30')

  useEffect(() => {
    if (pipelineId) {
      loadAnalytics()
    }
  }, [pipelineId, dateRange])

  const loadAnalytics = async () => {
    try {
      setLoading(true)
      const response = await duplicatesApi.getDuplicateStatistics()
      setStats(response.data)
    } catch (error: any) {
      console.error('Failed to load duplicate analytics:', error)
    } finally {
      setLoading(false)
    }
  }

  const calculateSuccessRate = () => {
    if (!stats || stats.total_matches === 0) return 0
    return ((stats.resolved_matches / stats.total_matches) * 100).toFixed(1)
  }

  const calculateFalsePositiveRate = () => {
    if (!stats || stats.total_matches === 0) return 0
    return ((stats.false_positives / stats.total_matches) * 100).toFixed(1)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading analytics...</p>
        </div>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="text-center py-12">
        <Database className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          No Analytics Data
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Analytics data will appear here once duplicate detection starts running.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Duplicate Detection Analytics
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Performance metrics and insights for your duplicate detection system
          </p>
        </div>
        
        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Date Range:
          </label>
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
            <option value="365">Last year</option>
          </select>
        </div>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Rules */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Rules</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{stats.total_rules}</p>
              <p className="text-sm text-green-600 dark:text-green-400 mt-1">
                {stats.active_rules} active
              </p>
            </div>
            <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
              <Target className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
        </div>

        {/* Total Matches */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Matches</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{stats.total_matches}</p>
              <p className="text-sm text-orange-600 dark:text-orange-400 mt-1">
                {stats.pending_matches} pending
              </p>
            </div>
            <div className="p-3 bg-orange-100 dark:bg-orange-900/20 rounded-lg">
              <Users className="w-6 h-6 text-orange-600 dark:text-orange-400" />
            </div>
          </div>
        </div>

        {/* Success Rate */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Resolution Rate</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{calculateSuccessRate()}%</p>
              <p className="text-sm text-green-600 dark:text-green-400 mt-1">
                {stats.resolved_matches} resolved
              </p>
            </div>
            <div className="p-3 bg-green-100 dark:bg-green-900/20 rounded-lg">
              <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
          </div>
        </div>

        {/* Average Confidence */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Avg Confidence</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">
                {Math.round(stats.avg_confidence_score * 100)}%
              </p>
              <p className="text-sm text-purple-600 dark:text-purple-400 mt-1">
                High accuracy
              </p>
            </div>
            <div className="p-3 bg-purple-100 dark:bg-purple-900/20 rounded-lg">
              <TrendingUp className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Additional Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Performance Summary */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <BarChart3 className="w-5 h-5 mr-2 text-blue-500" />
            Performance Summary
          </h3>
          
          <div className="space-y-4">
            {/* Detection Results */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Detection Results
              </span>
              <span className="text-lg font-semibold text-gray-900 dark:text-white">
                {stats.detection_results_count}
              </span>
            </div>
            
            {/* URL Extraction Rules */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                URL Extraction Rules
              </span>
              <span className="text-lg font-semibold text-gray-900 dark:text-white">
                {stats.url_extraction_rules}
              </span>
            </div>
            
            {/* False Positive Rate */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                False Positive Rate
              </span>
              <span className="text-lg font-semibold text-red-600 dark:text-red-400">
                {calculateFalsePositiveRate()}%
              </span>
            </div>
            
            {/* Date Range */}
            <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Data from {new Date(stats.date_range.start_date).toLocaleDateString()} to{' '}
                {new Date(stats.date_range.end_date).toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>

        {/* Top Performing Rules */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <Zap className="w-5 h-5 mr-2 text-yellow-500" />
            Top Performing Rules
          </h3>
          
          <div className="space-y-3">
            {stats.top_performing_rules.length === 0 ? (
              <p className="text-sm text-gray-600 dark:text-gray-400 text-center py-4">
                No rule performance data available yet
              </p>
            ) : (
              stats.top_performing_rules.slice(0, 5).map((rule, index) => (
                <div
                  key={rule.rule_id}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <div className="flex items-center justify-center w-6 h-6 bg-orange-500 text-white rounded-full text-xs font-bold">
                      {index + 1}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {rule.rule_name}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {rule.action_on_duplicate}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-gray-900 dark:text-white">
                      {rule.match_count} matches
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {Math.round(rule.avg_confidence * 100)}% avg confidence
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Insights and Recommendations */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg p-6 border border-blue-200 dark:border-blue-800">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
          <Activity className="w-5 h-5 mr-2 text-blue-500" />
          Insights & Recommendations
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* High Performance Insight */}
          {stats.avg_confidence_score > 0.8 && (
            <div className="flex items-start space-x-3">
              <CheckCircle className="w-5 h-5 text-green-500 mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                  High Detection Accuracy
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Your rules are performing well with {Math.round(stats.avg_confidence_score * 100)}% average confidence.
                </p>
              </div>
            </div>
          )}
          
          {/* Pending Matches Alert */}
          {stats.pending_matches > 10 && (
            <div className="flex items-start space-x-3">
              <AlertTriangle className="w-5 h-5 text-orange-500 mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                  Review Pending Matches
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  You have {stats.pending_matches} matches waiting for review.
                </p>
              </div>
            </div>
          )}
          
          {/* Inactive Rules Warning */}
          {stats.total_rules - stats.active_rules > 0 && (
            <div className="flex items-start space-x-3">
              <AlertTriangle className="w-5 h-5 text-yellow-500 mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                  Inactive Rules
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {stats.total_rules - stats.active_rules} rules are currently inactive.
                </p>
              </div>
            </div>
          )}
          
          {/* No Rules Warning */}
          {stats.total_rules === 0 && (
            <div className="flex items-start space-x-3 col-span-2">
              <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                  No Detection Rules
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Create your first duplicate detection rule to start identifying duplicates automatically.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}