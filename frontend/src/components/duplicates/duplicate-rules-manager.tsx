'use client'

import { useState, useEffect } from 'react'
import { 
  Plus, 
  Search, 
  Filter, 
  Settings, 
  Play, 
  Pause, 
  Copy, 
  Trash2, 
  Edit,
  AlertTriangle,
  CheckCircle,
  Clock,
  MoreVertical,
  Eye,
  TestTube
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

interface DuplicateRulesManagerProps {
  pipelineId: string
  pipeline: any
  onPipelineChange?: (pipeline: any) => void
}

export function DuplicateRulesManager({ 
  pipelineId, 
  pipeline, 
  onPipelineChange 
}: DuplicateRulesManagerProps) {
  const [rules, setRules] = useState<DuplicateRule[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [showNewRuleModal, setShowNewRuleModal] = useState(false)
  const [selectedRule, setSelectedRule] = useState<DuplicateRule | null>(null)
  const [editingRule, setEditingRule] = useState<DuplicateRule | null>(null)
  const [testingRule, setTestingRule] = useState<DuplicateRule | null>(null)

  // Load duplicate rules from API
  useEffect(() => {
    const loadDuplicateRules = async () => {
      try {
        setLoading(true)
        const response = await duplicatesApi.getDuplicateRules()
        
        // Transform API response to match our interface
        const transformedRules: DuplicateRule[] = (response.data.results || []).map((rule: any) => ({
          id: rule.id?.toString() || '',
          name: rule.name || '',
          description: rule.description || '',
          pipeline: rule.pipeline || pipelineId,
          logic: rule.logic || {},
          action_on_duplicate: rule.action_on_duplicate || 'warn',
          is_active: rule.is_active || false,
          created_at: rule.created_at || new Date().toISOString(),
          created_by: rule.created_by || { id: '', name: 'Unknown', email: '' },
          test_cases_count: rule.test_cases?.length || 0,
          matches_count: rule.matches_count || 0,
          last_run: rule.last_run || null
        }))
        
        setRules(transformedRules)
      } catch (error: any) {
        console.error('Failed to load duplicate rules:', error)
        
        // Show error notification
        const errorNotification = document.createElement('div')
        errorNotification.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-md shadow-lg z-50 max-w-md'
        errorNotification.innerHTML = `
          <div class="font-semibold">Failed to load duplicate rules</div>
          <div class="text-sm mt-1">${error?.response?.data?.detail || error?.message || 'Network error'}</div>
        `
        document.body.appendChild(errorNotification)
        
        setTimeout(() => {
          if (document.body.contains(errorNotification)) {
            document.body.removeChild(errorNotification)
          }
        }, 5000)
        
        // Set empty rules on error
        setRules([])
      } finally {
        setLoading(false)
      }
    }

    if (pipelineId) {
      loadDuplicateRules()
    }
  }, [pipelineId])

  // Handle rule save from builder
  const handleRuleSave = (savedRule: any) => {
    if (editingRule) {
      // Update existing rule
      setRules(rules.map(r => r.id === editingRule.id ? {
        ...r,
        ...savedRule,
        id: savedRule.id?.toString() || r.id
      } : r))
    } else {
      // Add new rule
      const newRule: DuplicateRule = {
        id: savedRule.id?.toString() || '',
        name: savedRule.name || '',
        description: savedRule.description || '',
        pipeline: savedRule.pipeline || pipelineId,
        logic: savedRule.logic || {},
        action_on_duplicate: savedRule.action_on_duplicate || 'warn',
        is_active: savedRule.is_active || false,
        created_at: savedRule.created_at || new Date().toISOString(),
        created_by: savedRule.created_by || { id: '', name: 'Unknown', email: '' },
        test_cases_count: 0,
        matches_count: 0,
        last_run: undefined
      }
      setRules([newRule, ...rules])
    }
  }

  // Handle builder close
  const handleBuilderClose = () => {
    setShowNewRuleModal(false)
    setEditingRule(null)
  }

  const filteredRules = rules.filter(rule =>
    rule.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    rule.description.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const getActionBadge = (action: string) => {
    const styles = {
      warn: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400',
      prevent: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400',
      merge: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400',
      flag: 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400'
    }
    
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[action as keyof typeof styles]}`}>
        {action.charAt(0).toUpperCase() + action.slice(1)}
      </span>
    )
  }

  const getStatusBadge = (isActive: boolean) => {
    return isActive ? (
      <span className="flex items-center text-green-600 dark:text-green-400">
        <CheckCircle className="w-4 h-4 mr-1" />
        Active
      </span>
    ) : (
      <span className="flex items-center text-gray-500">
        <Pause className="w-4 h-4 mr-1" />
        Inactive
      </span>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading duplicate rules...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Duplicate Detection Rules
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Configure rules to automatically detect and handle duplicate records
          </p>
        </div>
        
        <button
          onClick={() => setShowNewRuleModal(true)}
          className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 flex items-center space-x-2 transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>New Rule</span>
        </button>
      </div>

      {/* Search and Filters */}
      <div className="flex items-center space-x-4">
        <div className="flex-1 relative">
          <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search rules..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          />
        </div>
        <button className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center space-x-2">
          <Filter className="w-4 h-4" />
          <span>Filter</span>
        </button>
      </div>

      {/* Rules List */}
      <div className="space-y-4">
        {filteredRules.length === 0 ? (
          <div className="text-center py-12">
            <Copy className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              No duplicate rules yet
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Create your first duplicate detection rule to start identifying duplicate records
            </p>
            <button
              onClick={() => setShowNewRuleModal(true)}
              className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 flex items-center space-x-2 mx-auto"
            >
              <Plus className="w-4 h-4" />
              <span>Create First Rule</span>
            </button>
          </div>
        ) : (
          filteredRules.map((rule) => (
            <div
              key={rule.id}
              className="bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {rule.name}
                    </h3>
                    {getStatusBadge(rule.is_active)}
                    {getActionBadge(rule.action_on_duplicate)}
                  </div>
                  
                  <p className="text-gray-600 dark:text-gray-400 mb-4">
                    {rule.description}
                  </p>
                  
                  <div className="flex items-center space-x-6 text-sm text-gray-500 dark:text-gray-400">
                    <div className="flex items-center space-x-1">
                      <TestTube className="w-4 h-4" />
                      <span>{rule.test_cases_count} test cases</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <AlertTriangle className="w-4 h-4" />
                      <span>{rule.matches_count} matches found</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Clock className="w-4 h-4" />
                      <span>
                        Last run: {rule.last_run ? new Date(rule.last_run).toLocaleDateString() : 'Never'}
                      </span>
                    </div>
                  </div>
                </div>
                
                {/* Actions */}
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setSelectedRule(rule)}
                    className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600"
                    title="View details"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setTestingRule(rule)}
                    className="p-2 text-purple-500 hover:text-purple-600 dark:hover:text-purple-400 rounded-lg hover:bg-purple-50 dark:hover:bg-purple-900/20"
                    title="Test rule"
                  >
                    <TestTube className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setEditingRule(rule)}
                    className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600"
                    title="Edit rule"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={async () => {
                      try {
                        const updatedRule = await duplicatesApi.updateDuplicateRule(rule.id, {
                          is_active: !rule.is_active
                        })
                        
                        // Update local state
                        setRules(rules.map(r => 
                          r.id === rule.id 
                            ? { ...r, is_active: !r.is_active }
                            : r
                        ))
                      } catch (error: any) {
                        console.error('Failed to toggle rule state:', error)
                        // Show error notification
                        const errorNotification = document.createElement('div')
                        errorNotification.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-md shadow-lg z-50 max-w-md'
                        errorNotification.innerHTML = `
                          <div class="font-semibold">Failed to update rule</div>
                          <div class="text-sm mt-1">${error?.response?.data?.detail || error?.message || 'Network error'}</div>
                        `
                        document.body.appendChild(errorNotification)
                        
                        setTimeout(() => {
                          if (document.body.contains(errorNotification)) {
                            document.body.removeChild(errorNotification)
                          }
                        }, 5000)
                      }
                    }}
                    className={`p-2 rounded-lg ${
                      rule.is_active
                        ? 'text-orange-500 hover:text-orange-600 hover:bg-orange-50 dark:hover:bg-orange-900/20'
                        : 'text-green-500 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20'
                    }`}
                    title={rule.is_active ? 'Deactivate rule' : 'Activate rule'}
                  >
                    {rule.is_active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  </button>
                  <div className="relative">
                    <button className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600">
                      <MoreVertical className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Duplicate Rule Builder */}
      <DuplicateRuleBuilder
        isOpen={showNewRuleModal || editingRule !== null}
        onClose={handleBuilderClose}
        onSave={handleRuleSave}
        pipelineId={pipelineId}
        editingRule={editingRule}
      />

      {/* Rule Test Modal */}
      {testingRule && (
        <RuleTestModal
          isOpen={testingRule !== null}
          onClose={() => setTestingRule(null)}
          rule={testingRule}
          pipelineFields={pipeline?.fields || []}
        />
      )}
    </div>
  )
}