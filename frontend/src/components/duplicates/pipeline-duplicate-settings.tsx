'use client'

import { useState, useEffect } from 'react'
import { 
  Settings, 
  Play, 
  Pause, 
  TestTube,
  AlertTriangle,
  CheckCircle,
  Save,
  RefreshCw,
  Eye,
  BarChart3
} from 'lucide-react'
import { duplicatesApi } from '@/lib/api'
import { DuplicateRuleBuilder } from './duplicate-rule-builder'
import { RuleTestModal } from './rule-test-modal'

interface DuplicateRule {
  id: string
  name: string
  description: string
  pipeline: string
  logic: any
  action_on_duplicate: 'warn' | 'prevent' | 'merge' | 'flag'
  is_active: boolean
  created_at: string
  created_by: {
    id: string
    name: string
    email: string
  }
  test_cases_count?: number
  matches_count?: number
  last_run?: string
}

interface PipelineDuplicateSettingsProps {
  pipelineId: string
  pipeline: any
  onSettingsChange?: (settings: DuplicateRule | null) => void
}

export function PipelineDuplicateSettings({ 
  pipelineId, 
  pipeline, 
  onSettingsChange 
}: PipelineDuplicateSettingsProps) {
  const [duplicateRule, setDuplicateRule] = useState<DuplicateRule | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showRuleBuilder, setShowRuleBuilder] = useState(false)
  const [showTestModal, setShowTestModal] = useState(false)
  const [stats, setStats] = useState({
    totalMatches: 0,
    pendingMatches: 0,
    resolvedMatches: 0,
    lastScan: null as string | null
  })

  useEffect(() => {
    loadDuplicateSettings()
  }, [pipelineId])

  const loadDuplicateSettings = async () => {
    try {
      setLoading(true)
      const response = await duplicatesApi.getDuplicateRules(pipelineId)
      
      // Get the first (and ideally only) duplicate rule for this pipeline
      const rules = response.data.results || response.data || []
      const rule = rules.length > 0 ? rules[0] : null
      
      if (rule) {
        const transformedRule: DuplicateRule = {
          id: rule.id?.toString() || '',
          name: rule.name || '',
          description: rule.description || '',
          pipeline: rule.pipeline?.toString() || pipelineId,
          logic: rule.logic || { operator: 'AND', fields: [] },
          action_on_duplicate: rule.action_on_duplicate || 'warn',
          is_active: rule.is_active !== undefined ? rule.is_active : true,
          created_at: rule.created_at || new Date().toISOString(),
          created_by: rule.created_by || { id: '', name: 'Unknown', email: '' },
          test_cases_count: rule.test_cases?.length || 0,
          matches_count: rule.matches_count || 0,
          last_run: rule.last_run || null
        }
        setDuplicateRule(transformedRule)
      } else {
        setDuplicateRule(null)
      }
      
      // Load duplicate statistics
      await loadStats()
      
      onSettingsChange?.(rule)
    } catch (error: any) {
      console.error('Failed to load duplicate settings:', error)
      setDuplicateRule(null)
      onSettingsChange?.(null)
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const matchesResponse = await duplicatesApi.getDuplicateMatches(pipelineId)
      const matches = matchesResponse.data.results || matchesResponse.data || []
      
      setStats({
        totalMatches: matches.length,
        pendingMatches: matches.filter((m: any) => m.status === 'pending').length,
        resolvedMatches: matches.filter((m: any) => m.status !== 'pending').length,
        lastScan: matches.length > 0 ? matches[0].detected_at : null
      })
    } catch (error) {
      console.error('Failed to load duplicate stats:', error)
    }
  }

  const handleToggleActive = async () => {
    if (!duplicateRule) return
    
    try {
      setSaving(true)
      const updatedRule = await duplicatesApi.updateDuplicateRule(duplicateRule.id, {
        is_active: !duplicateRule.is_active
      }, pipelineId)
      
      setDuplicateRule({
        ...duplicateRule,
        is_active: !duplicateRule.is_active
      })
      
      onSettingsChange?.(updatedRule.data)
    } catch (error) {
      console.error('Failed to toggle duplicate detection:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleRuleBuilderSave = (rule: any) => {
    setDuplicateRule(rule)
    setShowRuleBuilder(false)
    onSettingsChange?.(rule)
    loadStats() // Refresh stats after rule changes
  }

  const handleCreateConfiguration = () => {
    setShowRuleBuilder(true)
  }

  const handleEditConfiguration = () => {
    setShowRuleBuilder(true)
  }

  const getActionBadgeColor = (action: string) => {
    switch (action) {
      case 'warn': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'prevent': return 'bg-red-100 text-red-800 border-red-200' 
      case 'merge': return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'flag': return 'bg-purple-100 text-purple-800 border-purple-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getActionLabel = (action: string) => {
    switch (action) {
      case 'warn': return 'Show Warning'
      case 'prevent': return 'Block Creation'
      case 'merge': return 'Prompt to Merge'
      case 'flag': return 'Flag for Review'
      default: return action
    }
  }

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
          <span className="ml-2 text-gray-600 dark:text-gray-400">Loading duplicate detection settings...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Duplicate Detection
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Configure how duplicates are detected and handled for {pipeline?.name}
            </p>
          </div>
          <div className="flex items-center space-x-2">
            {duplicateRule && (
              <>
                <button
                  onClick={() => setShowTestModal(true)}
                  className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500"
                >
                  <TestTube className="h-4 w-4 mr-1" />
                  Test Rules
                </button>
                <button
                  onClick={handleToggleActive}
                  disabled={saving}
                  className={`inline-flex items-center px-3 py-2 border shadow-sm text-sm leading-4 font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 ${
                    duplicateRule.is_active
                      ? 'border-red-300 text-red-700 bg-white hover:bg-red-50'
                      : 'border-green-300 text-green-700 bg-white hover:bg-green-50'
                  }`}
                >
                  {saving ? (
                    <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                  ) : duplicateRule.is_active ? (
                    <Pause className="h-4 w-4 mr-1" />
                  ) : (
                    <Play className="h-4 w-4 mr-1" />
                  )}
                  {duplicateRule.is_active ? 'Disable' : 'Enable'}
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {duplicateRule ? (
          /* Existing Configuration */
          <div className="space-y-6">
            {/* Status and Basic Info */}
            <div className="flex items-start justify-between">
              <div className="space-y-4 flex-1">
                <div className="flex items-center space-x-3">
                  <div className={`flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    duplicateRule.is_active 
                      ? 'bg-green-100 text-green-800 border border-green-200'
                      : 'bg-gray-100 text-gray-800 border border-gray-200'
                  }`}>
                    {duplicateRule.is_active ? (
                      <>
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Active
                      </>
                    ) : (
                      <>
                        <Pause className="h-3 w-3 mr-1" />
                        Disabled
                      </>
                    )}
                  </div>
                  <div className={`px-2 py-1 rounded-full text-xs font-medium border ${getActionBadgeColor(duplicateRule.action_on_duplicate)}`}>
                    {getActionLabel(duplicateRule.action_on_duplicate)}
                  </div>
                </div>
                
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-gray-100">
                    {duplicateRule.name || 'Duplicate Detection Rule'}
                  </h4>
                  {duplicateRule.description && (
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      {duplicateRule.description}
                    </p>
                  )}
                </div>
              </div>
              
              <button
                onClick={handleEditConfiguration}
                className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500"
              >
                <Settings className="h-4 w-4 mr-1" />
                Configure
              </button>
            </div>

            {/* Statistics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {stats.totalMatches}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Total Matches</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">
                  {stats.pendingMatches}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Pending Review</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {stats.resolvedMatches}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Resolved</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {duplicateRule.logic?.fields?.length || 0}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Match Fields</div>
              </div>
            </div>

            {/* Rule Logic Preview */}
            {duplicateRule.logic && duplicateRule.logic.fields && duplicateRule.logic.fields.length > 0 && (
              <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                <h5 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
                  Matching Fields ({duplicateRule.logic.operator})
                </h5>
                <div className="space-y-2">
                  {duplicateRule.logic.fields.map((field: any, index: number) => (
                    <div key={index} className="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-700 rounded-md">
                      <div className="flex items-center space-x-3">
                        <span className="font-medium text-gray-900 dark:text-gray-100">
                          {field.field}
                        </span>
                        <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                          {field.match_type}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {stats.lastScan && (
              <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  Last scan: {new Date(stats.lastScan).toLocaleDateString()} at {new Date(stats.lastScan).toLocaleTimeString()}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* No Configuration */
          <div className="text-center py-12">
            <Settings className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              No Duplicate Detection Configured
            </h4>
            <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md mx-auto">
              Set up duplicate detection rules to automatically identify and handle potential duplicate records in {pipeline?.name}.
            </p>
            <button
              onClick={handleCreateConfiguration}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-orange-500 hover:bg-orange-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500"
            >
              <Settings className="h-4 w-4 mr-2" />
              Configure Duplicate Detection
            </button>
          </div>
        )}
      </div>

      {/* Rule Builder Modal */}
      {showRuleBuilder && (
        <DuplicateRuleBuilder
          isOpen={showRuleBuilder}
          onClose={() => setShowRuleBuilder(false)}
          onSave={handleRuleBuilderSave}
          pipelineId={pipelineId}
          pipeline={pipeline}
          editingRule={duplicateRule}
        />
      )}

      {/* Test Modal */}
      {showTestModal && duplicateRule && (
        <RuleTestModal
          isOpen={showTestModal}
          onClose={() => setShowTestModal(false)}
          rule={duplicateRule}
          pipelineFields={pipeline?.fields || []}
          pipelineId={pipelineId}
        />
      )}
    </div>
  )
}