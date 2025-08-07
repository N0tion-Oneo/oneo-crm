'use client'

import React, { useState } from 'react'
import { 
  AlertTriangle, 
  Archive, 
  RotateCcw, 
  Trash2, 
  Clock, 
  Shield, 
  AlertCircle,
  CheckCircle,
  Loader2,
  Calendar,
  User,
  FileText,
  Database,
  Zap,
  RefreshCw
} from 'lucide-react'
import { pipelinesApi } from '@/lib/api'
import { MigrationWizard } from './migration-wizard'

interface PipelineField {
  id: string
  name: string                    // Field name/slug
  display_name?: string           // Display name (optional)
  description?: string            // Field description
  field_type: string              // Field type
  help_text?: string              // User help text
  
  // Display configuration
  display_order: number
  is_visible_in_list: boolean
  is_visible_in_detail: boolean
  is_visible_in_public_forms?: boolean
  
  // Behavior
  is_searchable: boolean
  create_index: boolean
  enforce_uniqueness: boolean
  is_ai_field: boolean
  
  // Configuration objects
  field_config: Record<string, any>
  storage_constraints: Record<string, any>
  business_rules: Record<string, any>
  ai_config?: Record<string, any>
  
  // Field lifecycle management
  is_deleted?: boolean
  deleted_at?: string
  deleted_by?: string
  scheduled_for_hard_delete?: string
  hard_delete_reason?: string
  deletion_status?: {
    status: 'active' | 'soft_deleted' | 'scheduled_for_hard_delete'
    deleted_at?: string
    deleted_by?: string
    days_remaining?: number
    hard_delete_date?: string
    reason?: string
  }
  
  // Legacy support (for compatibility)
  label?: string
  type?: string
  required?: boolean
  visible?: boolean
  order?: number
  config?: Record<string, any>
}

interface FieldManagementPanelProps {
  field: PipelineField
  pipelineId: string
  onFieldUpdate: (field: PipelineField) => void
  onClose: () => void
}

export function FieldManagementPanel({ field, pipelineId, onFieldUpdate, onClose }: FieldManagementPanelProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionResult, setActionResult] = useState<string | null>(null)
  const [showConfirmDelete, setShowConfirmDelete] = useState(false)
  const [deleteReason, setDeleteReason] = useState('')
  const [graceDays, setGraceDays] = useState(7)
  const [showImpactAnalysis, setShowImpactAnalysis] = useState(false)
  const [impactAnalysis, setImpactAnalysis] = useState<any>(null)
  
  // Migration wizard state
  const [showMigrationWizard, setShowMigrationWizard] = useState(false)
  const [targetFieldType, setTargetFieldType] = useState('')
  const [targetFieldConfig, setTargetFieldConfig] = useState({})

  // Restore preview state
  const [showRestorePreview, setShowRestorePreview] = useState(false)
  const [restorePreview, setRestorePreview] = useState<any>(null)
  const [showConfirmRestore, setShowConfirmRestore] = useState(false)
  const [restoreReason, setRestoreReason] = useState('')

  const fieldStatus = field.deletion_status?.status || 'active'
  const isActive = fieldStatus === 'active'
  const isSoftDeleted = fieldStatus === 'soft_deleted'
  const isScheduled = fieldStatus === 'scheduled_for_hard_delete'

  const handleFieldAction = async (action: 'soft_delete' | 'restore' | 'schedule_hard_delete' | 'impact_analysis', actionData?: any) => {
    try {
      setLoading(true)
      setError(null)
      setActionResult(null)

      const response = await pipelinesApi.manageField(pipelineId, field.id, action, actionData)

      if (response.data.success) {
        setActionResult(response.data.message || 'Action completed successfully')
        
        // Update field status based on action
        const updatedField = { ...field }
        if (action === 'soft_delete') {
          updatedField.deletion_status = {
            status: 'soft_deleted',
            deleted_at: new Date().toISOString(),
            deleted_by: 'current_user' // TODO: Get from auth context
          }
        } else if (action === 'restore') {
          updatedField.deletion_status = {
            status: 'active'
          }
        } else if (action === 'schedule_hard_delete') {
          updatedField.deletion_status = {
            status: 'scheduled_for_hard_delete',
            hard_delete_date: response.data.scheduled_date,
            days_remaining: graceDays,
            reason: actionData?.reason
          }
        } else if (action === 'impact_analysis') {
          setImpactAnalysis(response.data.impact_analysis)
          setShowImpactAnalysis(true)
          return // Don't update field for analysis
        }

        // Update field for all non-analysis actions
        onFieldUpdate(updatedField)
        setShowConfirmDelete(false)
      } else {
        setError(response.data.error || 'Action failed')
      }
    } catch (err: any) {
      console.error('Field action failed:', err)
      setError(err?.response?.data?.error || err?.message || 'Action failed')
    } finally {
      setLoading(false)
    }
  }

  const handleRestorePreview = async () => {
    try {
      setLoading(true)
      setError(null)

      // Call new restore API with dry_run: true
      const response = await pipelinesApi.restoreField(pipelineId, field.id, { 
        dry_run: true,
        reason: restoreReason 
      })

      if (response.data.success) {
        setRestorePreview(response.data)
        setShowRestorePreview(true)
      } else {
        setError(response.data.error || 'Restore preview failed')
      }
    } catch (err: any) {
      console.error('Restore preview failed:', err)
      setError(err?.response?.data?.error || err?.message || 'Restore preview failed')
    } finally {
      setLoading(false)
    }
  }

  const handleRestoreField = async (force: boolean = false) => {
    try {
      setLoading(true)
      setError(null)
      setActionResult(null)

      // Call new restore API with actual restore
      const response = await pipelinesApi.restoreField(pipelineId, field.id, {
        dry_run: false,
        force: force,
        reason: restoreReason
      })

      if (response.data.success) {
        setActionResult(response.data.message || 'Field restored successfully')
        
        // Update field status
        const updatedField = { ...field }
        updatedField.deletion_status = {
          status: 'active'
        }
        
        onFieldUpdate(updatedField)
        setShowConfirmRestore(false)
        setShowRestorePreview(false)
      } else {
        setError(response.data.error || 'Restore failed')
      }
    } catch (err: any) {
      console.error('Restore failed:', err)
      setError(err?.response?.data?.error || err?.message || 'Restore failed')
    } finally {
      setLoading(false)
    }
  }

  const StatusIcon = () => {
    if (isActive) return <CheckCircle className="w-5 h-5 text-green-500" />
    if (isSoftDeleted) return <Archive className="w-5 h-5 text-orange-500" />
    if (isScheduled) return <Clock className="w-5 h-5 text-red-500" />
    return <AlertCircle className="w-5 h-5 text-gray-400" />
  }

  const StatusBadge = () => {
    const badges = {
      active: 'bg-green-50 text-green-700 border-green-200',
      soft_deleted: 'bg-orange-50 text-orange-700 border-orange-200',
      scheduled_for_hard_delete: 'bg-red-50 text-red-700 border-red-200'
    }
    
    const labels = {
      active: 'Active',
      soft_deleted: 'Soft Deleted',
      scheduled_for_hard_delete: 'Scheduled for Deletion'
    }

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${badges[fieldStatus]}`}>
        <StatusIcon />
        <span className="ml-1.5">{labels[fieldStatus]}</span>
      </span>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
                <Shield className="w-5 h-5 mr-2 text-blue-500" />
                Field Management: {field.display_name || field.name}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Manage field lifecycle and schema operations
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="p-6">
          {/* Field Info */}
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-gray-900 dark:text-white">Field Status</h3>
              <StatusBadge />
            </div>
            
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500 dark:text-gray-400">Field Type:</span>
                <div className="font-medium text-gray-900 dark:text-white capitalize">
                  {field.field_type.replace('_', ' ')}
                </div>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">Field ID:</span>
                <div className="font-mono text-xs text-gray-700 dark:text-gray-300">{field.id}</div>
              </div>
            </div>

            {field.deletion_status && fieldStatus !== 'active' && (
              <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-600">
                <div className="grid grid-cols-1 gap-2 text-sm">
                  {field.deletion_status.deleted_at && (
                    <div className="flex items-center">
                      <Calendar className="w-4 h-4 mr-2 text-gray-400" />
                      <span className="text-gray-500">Deleted:</span>
                      <span className="ml-2 text-gray-900 dark:text-white">
                        {new Date(field.deletion_status.deleted_at).toLocaleString()}
                      </span>
                    </div>
                  )}
                  {field.deletion_status.deleted_by && (
                    <div className="flex items-center">
                      <User className="w-4 h-4 mr-2 text-gray-400" />
                      <span className="text-gray-500">By:</span>
                      <span className="ml-2 text-gray-900 dark:text-white">
                        {field.deletion_status.deleted_by}
                      </span>
                    </div>
                  )}
                  {field.deletion_status.hard_delete_date && (
                    <div className="flex items-center">
                      <Clock className="w-4 h-4 mr-2 text-red-400" />
                      <span className="text-gray-500">Hard Delete Date:</span>
                      <span className="ml-2 text-red-600 font-medium">
                        {new Date(field.deletion_status.hard_delete_date).toLocaleString()}
                      </span>
                      {field.deletion_status.days_remaining !== undefined && (
                        <span className="ml-2 text-red-500 text-xs">
                          ({field.deletion_status.days_remaining} days remaining)
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Action Results */}
          {actionResult && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center">
                <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
                <span className="text-green-800 text-sm">{actionResult}</span>
              </div>
            </div>
          )}

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center">
                <AlertCircle className="w-4 h-4 text-red-500 mr-2" />
                <span className="text-red-800 text-sm">{error}</span>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white">Available Actions</h3>

            {/* Impact Analysis */}
            <div className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center">
                  <Database className="w-5 h-5 text-blue-500 mr-2" />
                  <span className="font-medium text-gray-900 dark:text-white">Impact Analysis</span>
                </div>
                <button
                  onClick={() => handleFieldAction('impact_analysis')}
                  disabled={loading}
                  className="px-3 py-1.5 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 text-sm"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Analyze'}
                </button>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Analyze the impact of schema changes on existing data
              </p>
            </div>

            {/* Change Field Type */}
            {isActive && (
              <div className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center">
                    <RefreshCw className="w-5 h-5 text-purple-500 mr-2" />
                    <span className="font-medium text-gray-900 dark:text-white">Change Field Type</span>
                  </div>
                  <button
                    onClick={() => setShowMigrationWizard(true)}
                    disabled={loading}
                    className="px-3 py-1.5 bg-purple-500 text-white rounded-md hover:bg-purple-600 disabled:opacity-50 text-sm"
                  >
                    Change Type
                  </button>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Safely migrate field to a different type with guided validation
                </p>
              </div>
            )}

            {/* Soft Delete */}
            {isActive && (
              <div className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center">
                    <Archive className="w-5 h-5 text-orange-500 mr-2" />
                    <span className="font-medium text-gray-900 dark:text-white">Soft Delete</span>
                  </div>
                  <button
                    onClick={() => setShowConfirmDelete(true)}
                    disabled={loading}
                    className="px-3 py-1.5 bg-orange-500 text-white rounded-md hover:bg-orange-600 disabled:opacity-50 text-sm"
                  >
                    Soft Delete
                  </button>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Hide field from active use but keep data (reversible)
                </p>
              </div>
            )}

            {/* Enhanced Restore with Preview */}
            {isSoftDeleted && (
              <div className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center">
                    <RotateCcw className="w-5 h-5 text-green-500 mr-2" />
                    <span className="font-medium text-gray-900 dark:text-white">Restore Field</span>
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => setShowConfirmRestore(true)}
                      disabled={loading}
                      className="px-3 py-1.5 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 text-sm"
                    >
                      Preview Restore
                    </button>
                    <button
                      onClick={() => handleRestoreField(false)}
                      disabled={loading}
                      className="px-3 py-1.5 bg-green-500 text-white rounded-md hover:bg-green-600 disabled:opacity-50 text-sm"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Restore'}
                    </button>
                  </div>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Restore field to active use with validation preview
                </p>
              </div>
            )}

            {/* Hard Delete */}
            {isSoftDeleted && (
              <div className="border border-red-200 dark:border-red-600 rounded-lg p-4 bg-red-50 dark:bg-red-900/10">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center">
                    <Trash2 className="w-5 h-5 text-red-500 mr-2" />
                    <span className="font-medium text-gray-900 dark:text-white">Schedule Hard Delete</span>
                  </div>
                  <button
                    onClick={() => setShowConfirmDelete(true)}
                    disabled={loading}
                    className="px-3 py-1.5 bg-red-500 text-white rounded-md hover:bg-red-600 disabled:opacity-50 text-sm"
                  >
                    Schedule
                  </button>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Permanently delete field and all associated data (irreversible)
                </p>
              </div>
            )}
          </div>

          {/* Confirmation Dialog */}
          {showConfirmDelete && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-60">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md">
                <div className="p-6">
                  <div className="flex items-center mb-4">
                    <AlertTriangle className="w-6 h-6 text-red-500 mr-3" />
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {isActive ? 'Confirm Soft Delete' : 'Confirm Hard Delete Schedule'}
                    </h3>
                  </div>
                  
                  <p className="text-gray-600 dark:text-gray-400 mb-4">
                    {isActive 
                      ? 'This will hide the field from active use but preserve all data. You can restore it later.'
                      : 'This will schedule the field for permanent deletion. All associated data will be destroyed and cannot be recovered.'
                    }
                  </p>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Reason for {isActive ? 'deletion' : 'hard deletion'}
                      </label>
                      <textarea
                        value={deleteReason}
                        onChange={(e) => setDeleteReason(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        rows={3}
                        placeholder="Explain why this field is being deleted..."
                      />
                    </div>

                    {!isActive && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Grace Period (days)
                        </label>
                        <select
                          value={graceDays}
                          onChange={(e) => setGraceDays(parseInt(e.target.value))}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option value={1}>1 day</option>
                          <option value={3}>3 days</option>
                          <option value={7}>7 days</option>
                          <option value={14}>14 days</option>
                          <option value={30}>30 days</option>
                        </select>
                      </div>
                    )}
                  </div>

                  <div className="flex justify-end space-x-3 mt-6">
                    <button
                      onClick={() => setShowConfirmDelete(false)}
                      className="px-4 py-2 text-gray-600 hover:text-gray-800 border border-gray-300 rounded-md hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => {
                        const action = isActive ? 'soft_delete' : 'schedule_hard_delete'
                        handleFieldAction(action, { 
                          reason: deleteReason, 
                          grace_days: graceDays 
                        })
                      }}
                      disabled={!deleteReason.trim() || loading}
                      className={`px-4 py-2 text-white rounded-md disabled:opacity-50 ${
                        isActive 
                          ? 'bg-orange-500 hover:bg-orange-600'
                          : 'bg-red-500 hover:bg-red-600'
                      }`}
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : (
                        isActive ? 'Soft Delete' : 'Schedule Hard Delete'
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Impact Analysis Results */}
          {showImpactAnalysis && impactAnalysis && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-60">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-3xl max-h-[80vh] overflow-y-auto">
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
                      <Zap className="w-5 h-5 mr-2 text-blue-500" />
                      Impact Analysis Results
                    </h3>
                    <button
                      onClick={() => setShowImpactAnalysis(false)}
                      className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                    >
                      ✕
                    </button>
                  </div>

                  <div className="space-y-6">
                    {/* Record Statistics */}
                    <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                      <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-3 flex items-center">
                        <Database className="w-4 h-4 mr-2" />
                        Record Statistics
                      </h4>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        {impactAnalysis.record_count !== undefined && (
                          <div>
                            <span className="text-blue-600 dark:text-blue-300 font-medium">Total Records:</span>
                            <div className="text-blue-900 dark:text-blue-100 font-semibold text-lg">
                              {impactAnalysis.record_count.toLocaleString()}
                            </div>
                          </div>
                        )}
                        {impactAnalysis.records_with_data !== undefined && (
                          <div>
                            <span className="text-blue-600 dark:text-blue-300 font-medium">Records with Data:</span>
                            <div className="text-blue-900 dark:text-blue-100 font-semibold text-lg">
                              {impactAnalysis.records_with_data.toLocaleString()}
                            </div>
                          </div>
                        )}
                      </div>
                      {impactAnalysis.record_count > 0 && impactAnalysis.records_with_data !== undefined && (
                        <div className="mt-3 pt-3 border-t border-blue-200 dark:border-blue-700">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-blue-600 dark:text-blue-300">Data Coverage:</span>
                            <span className="text-blue-900 dark:text-blue-100 font-semibold">
                              {((impactAnalysis.records_with_data / impactAnalysis.record_count) * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Risk Assessment */}
                    {impactAnalysis.risk_level && (
                      <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4">
                        <h4 className="text-sm font-semibold text-orange-900 dark:text-orange-100 mb-3 flex items-center">
                          <AlertTriangle className="w-4 h-4 mr-2" />
                          Risk Assessment
                        </h4>
                        <div className="flex items-center justify-between">
                          <span className="text-orange-600 dark:text-orange-300 font-medium">Risk Level:</span>
                          <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                            impactAnalysis.risk_level === 'high' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200' :
                            impactAnalysis.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200' :
                            'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200'
                          }`}>
                            {impactAnalysis.risk_level.charAt(0).toUpperCase() + impactAnalysis.risk_level.slice(1)}
                          </span>
                        </div>
                        {impactAnalysis.risk_level === 'high' && (
                          <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800">
                            <div className="flex items-start">
                              <AlertTriangle className="w-4 h-4 text-red-500 mr-2 mt-0.5 flex-shrink-0" />
                              <p className="text-red-800 dark:text-red-200 text-sm">
                                High risk deletion! This field contains significant data that may be critical to your system.
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Dependencies */}
                    {impactAnalysis.dependent_systems && impactAnalysis.dependent_systems.length > 0 && (
                      <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                        <h4 className="text-sm font-semibold text-purple-900 dark:text-purple-100 mb-3 flex items-center">
                          <Zap className="w-4 h-4 mr-2" />
                          Dependencies ({impactAnalysis.dependent_systems.length})
                        </h4>
                        <div className="space-y-3">
                          {impactAnalysis.dependent_systems.map((dependency: any, index: number) => (
                            <div key={index} className="bg-white dark:bg-purple-800/20 rounded-lg p-3 border border-purple-200 dark:border-purple-700">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-purple-700 dark:text-purple-300 font-medium capitalize">
                                  {dependency.system?.replace('_', ' ') || 'Unknown System'}
                                </span>
                                {dependency.count !== undefined && (
                                  <span className="bg-purple-100 dark:bg-purple-800 text-purple-800 dark:text-purple-200 px-2 py-1 rounded text-xs font-semibold">
                                    {dependency.count} dependencies
                                  </span>
                                )}
                              </div>
                              {dependency.details && (
                                <p className="text-purple-600 dark:text-purple-400 text-sm">
                                  {dependency.details}
                                </p>
                              )}
                              {dependency.affected_items && dependency.affected_items.length > 0 && (
                                <div className="mt-2">
                                  <span className="text-purple-600 dark:text-purple-400 text-xs font-medium">Affected items:</span>
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {dependency.affected_items.slice(0, 5).map((item: string, i: number) => (
                                      <span key={i} className="bg-purple-100 dark:bg-purple-800/50 text-purple-700 dark:text-purple-300 px-2 py-0.5 rounded text-xs">
                                        {item}
                                      </span>
                                    ))}
                                    {dependency.affected_items.length > 5 && (
                                      <span className="text-purple-600 dark:text-purple-400 text-xs">
                                        +{dependency.affected_items.length - 5} more
                                      </span>
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* No Dependencies Message */}
                    {(!impactAnalysis.dependent_systems || impactAnalysis.dependent_systems.length === 0) && (
                      <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                        <h4 className="text-sm font-semibold text-green-900 dark:text-green-100 mb-2 flex items-center">
                          <CheckCircle className="w-4 h-4 mr-2" />
                          No Dependencies Found
                        </h4>
                        <p className="text-green-700 dark:text-green-300 text-sm">
                          This field appears to have no system dependencies. It should be safe to delete.
                        </p>
                      </div>
                    )}

                    {/* Raw Data (collapsible) */}
                    <details className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
                      <summary className="text-sm font-medium text-gray-700 dark:text-gray-300 cursor-pointer hover:text-gray-900 dark:hover:text-gray-100 select-none">
                        View Raw Analysis Data
                      </summary>
                      <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                        <pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap overflow-x-auto max-h-60 overflow-y-auto">
                          {JSON.stringify(impactAnalysis, null, 2)}
                        </pre>
                      </div>
                    </details>
                  </div>

                  <div className="flex justify-end mt-4">
                    <button
                      onClick={() => setShowImpactAnalysis(false)}
                      className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
                    >
                      Close
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Restore Confirmation Dialog */}
          {showConfirmRestore && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-60">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md">
                <div className="p-6">
                  <div className="flex items-center mb-4">
                    <RotateCcw className="w-6 h-6 text-green-500 mr-3" />
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      Confirm Field Restore
                    </h3>
                  </div>
                  
                  <p className="text-gray-600 dark:text-gray-400 mb-4">
                    This will restore the field "{field.display_name || field.name}" to active use. 
                    You can preview the restore impact before proceeding.
                  </p>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Reason for restoration (optional)
                      </label>
                      <textarea
                        value={restoreReason}
                        onChange={(e) => setRestoreReason(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                        rows={2}
                        placeholder="Explain why this field is being restored..."
                      />
                    </div>
                  </div>

                  <div className="flex justify-end space-x-3 mt-6">
                    <button
                      onClick={() => setShowConfirmRestore(false)}
                      className="px-4 py-2 text-gray-600 hover:text-gray-800 border border-gray-300 rounded-md hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleRestorePreview}
                      disabled={loading}
                      className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Preview Restore'}
                    </button>
                    <button
                      onClick={() => handleRestoreField(false)}
                      disabled={loading}
                      className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 disabled:opacity-50"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Restore Now'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Restore Preview Results */}
          {showRestorePreview && restorePreview && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-60">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] overflow-y-auto">
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
                      <CheckCircle className="w-5 h-5 mr-2 text-green-500" />
                      Restore Preview Results
                    </h3>
                    <button
                      onClick={() => setShowRestorePreview(false)}
                      className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                    >
                      ✕
                    </button>
                  </div>

                  <div className="space-y-4">
                    {/* Validation Status */}
                    <div className={`rounded-lg p-4 ${
                      restorePreview.can_restore 
                        ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700'
                        : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700'
                    }`}>
                      <h4 className={`text-sm font-semibold mb-2 flex items-center ${
                        restorePreview.can_restore 
                          ? 'text-green-900 dark:text-green-100'
                          : 'text-red-900 dark:text-red-100'
                      }`}>
                        {restorePreview.can_restore ? (
                          <CheckCircle className="w-4 h-4 mr-2" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 mr-2" />
                        )}
                        {restorePreview.can_restore ? 'Safe to Restore' : 'Restore Issues Found'}
                      </h4>
                      
                      {/* Errors */}
                      {restorePreview.errors && restorePreview.errors.length > 0 && (
                        <div className="space-y-1">
                          {restorePreview.errors.map((error: string, index: number) => (
                            <div key={index} className="text-red-700 dark:text-red-300 text-sm flex items-start">
                              <AlertCircle className="w-3 h-3 mr-1 mt-0.5 flex-shrink-0" />
                              {error}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Warnings */}
                      {restorePreview.warnings && restorePreview.warnings.length > 0 && (
                        <div className="space-y-1 mt-2">
                          {restorePreview.warnings.map((warning: string, index: number) => (
                            <div key={index} className="text-orange-700 dark:text-orange-300 text-sm flex items-start">
                              <AlertTriangle className="w-3 h-3 mr-1 mt-0.5 flex-shrink-0" />
                              {warning}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Data Information */}
                    {restorePreview.records_with_data !== undefined && (
                      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                        <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2 flex items-center">
                          <Database className="w-4 h-4 mr-2" />
                          Data Recovery Information
                        </h4>
                        <div className="text-blue-700 dark:text-blue-300 text-sm">
                          <div>Records with field data: <strong>{restorePreview.records_with_data}</strong></div>
                          <div>Field name: <strong>{restorePreview.field_name}</strong></div>
                          {restorePreview.field_slug && (
                            <div>Field slug: <strong>{restorePreview.field_slug}</strong></div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex justify-end space-x-3 mt-6">
                    <button
                      onClick={() => setShowRestorePreview(false)}
                      className="px-4 py-2 text-gray-600 hover:text-gray-800 border border-gray-300 rounded-md hover:bg-gray-50"
                    >
                      Close Preview
                    </button>
                    {restorePreview.can_restore ? (
                      <button
                        onClick={() => {
                          setShowRestorePreview(false)
                          handleRestoreField(false)
                        }}
                        disabled={loading}
                        className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 disabled:opacity-50"
                      >
                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Proceed with Restore'}
                      </button>
                    ) : (
                      <button
                        onClick={() => {
                          setShowRestorePreview(false)
                          handleRestoreField(true) // Force restore despite warnings
                        }}
                        disabled={loading}
                        className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 disabled:opacity-50"
                      >
                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Force Restore'}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Migration Wizard */}
      <MigrationWizard
        isOpen={showMigrationWizard}
        onClose={() => setShowMigrationWizard(false)}
        pipelineId={pipelineId}
        field={field}
        onMigrationSuccess={() => {
          // Refresh field data after successful migration
          onFieldUpdate(field)
          setShowMigrationWizard(false)
          onClose()
        }}
      />
    </div>
  )
}