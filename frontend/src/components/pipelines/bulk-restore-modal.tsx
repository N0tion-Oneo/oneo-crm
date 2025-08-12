'use client'

import React, { useState } from 'react'
import { 
  RotateCcw,
  CheckCircle,
  AlertTriangle,
  AlertCircle,
  Loader2,
  Database,
  X,
  Eye,
  ArrowRight
} from 'lucide-react'
import { pipelinesApi } from '@/lib/api'

interface PipelineField {
  id: string
  name: string
  display_name?: string
  description?: string
  field_type: string
  help_text?: string
  display_order: number
  is_visible_in_list: boolean
  is_visible_in_detail: boolean
  is_visible_in_public_forms?: boolean
  is_searchable: boolean
  create_index: boolean
  enforce_uniqueness: boolean
  is_ai_field: boolean
  field_config: Record<string, any>
  storage_constraints: Record<string, any>
  business_rules: Record<string, any>
  ai_config?: Record<string, any>
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
}

interface BulkRestoreModalProps {
  isOpen: boolean
  onClose: () => void
  pipelineId: string
  selectedFields: PipelineField[]
  onSuccess: () => void
}

interface RestorePreview {
  field_id: string
  field_name: string
  can_restore: boolean
  errors: string[]
  warnings: string[]
  records_with_data?: number
}

export function BulkRestoreModal({ 
  isOpen, 
  onClose, 
  pipelineId, 
  selectedFields, 
  onSuccess 
}: BulkRestoreModalProps) {
  const [step, setStep] = useState<'confirm' | 'preview' | 'executing'>('confirm')
  const [reason, setReason] = useState('')
  const [previews, setPreviews] = useState<RestorePreview[]>([])
  const [previewLoading, setPreviewLoading] = useState(false)
  const [restoring, setRestoring] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handlePreview = async () => {
    if (selectedFields.length === 0) return

    try {
      setPreviewLoading(true)
      setError(null)

      // Get preview for each field
      const previewPromises = selectedFields.map(async (field) => {
        try {
          const response = await pipelinesApi.restoreField(pipelineId, field.id, {
            dry_run: true,
            reason: reason
          })

          return {
            field_id: field.id,
            field_name: field.display_name || field.name,
            can_restore: response.data.can_restore || false,
            errors: response.data.errors || [],
            warnings: response.data.warnings || [],
            records_with_data: response.data.records_with_data || 0
          } as RestorePreview
        } catch (err: any) {
          return {
            field_id: field.id,
            field_name: field.display_name || field.name,
            can_restore: false,
            errors: [err?.response?.data?.error || 'Preview failed'],
            warnings: [],
            records_with_data: 0
          } as RestorePreview
        }
      })

      const results = await Promise.all(previewPromises)
      setPreviews(results)
      setStep('preview')
    } catch (err: any) {
      console.error('Failed to generate preview:', err)
      setError(err?.response?.data?.error || 'Failed to generate preview')
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleRestore = async (force: boolean = false) => {
    try {
      setRestoring(true)
      setError(null)

      // Only restore fields that can be restored (or force if specified)
      const fieldsToRestore = force 
        ? selectedFields.map(f => f.id)
        : previews.filter(p => p.can_restore).map(p => p.field_id)

      if (fieldsToRestore.length === 0) {
        setError('No fields can be restored without forcing')
        return
      }

      await pipelinesApi.bulkRestoreFields(pipelineId, {
        field_ids: fieldsToRestore,
        reason: reason || 'Bulk restore operation',
        force: force
      })

      setStep('executing')
      
      // Simulate brief delay for user feedback
      setTimeout(() => {
        onSuccess()
        handleClose()
      }, 1000)

    } catch (err: any) {
      console.error('Failed to restore fields:', err)
      setError(err?.response?.data?.error || 'Failed to restore fields')
    } finally {
      setRestoring(false)
    }
  }

  const handleClose = () => {
    setStep('confirm')
    setReason('')
    setPreviews([])
    setError(null)
    onClose()
  }

  const canRestoreCount = previews.filter(p => p.can_restore).length
  const hasErrors = previews.some(p => p.errors.length > 0)
  const hasWarnings = previews.some(p => p.warnings.length > 0)

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <RotateCcw className="w-5 h-5 text-green-500" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {step === 'confirm' && 'Bulk Field Restore'}
                {step === 'preview' && 'Restore Preview Results'}
                {step === 'executing' && 'Restoring Fields...'}
              </h2>
            </div>
            <button
              onClick={handleClose}
              disabled={restoring || step === 'executing'}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="p-6 max-h-[calc(90vh-180px)] overflow-y-auto">
          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center">
                <AlertCircle className="w-5 h-5 text-red-400 mr-2" />
                <span className="text-red-800 text-sm">{error}</span>
              </div>
            </div>
          )}

          {/* Confirmation Step */}
          {step === 'confirm' && (
            <div className="space-y-6">
              <div>
                <p className="text-gray-600 dark:text-gray-400 mb-4">
                  You are about to restore <strong>{selectedFields.length}</strong> field(s). 
                  This will make them active and available for use again.
                </p>

                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 mb-6">
                  <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">
                    Fields to restore:
                  </h3>
                  <div className="space-y-1">
                    {selectedFields.map((field) => (
                      <div key={field.id} className="flex items-center space-x-2 text-sm text-blue-700 dark:text-blue-300">
                        <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                        <span className="font-medium">{field.display_name || field.name}</span>
                        <span className="text-blue-600 dark:text-blue-400">({field.field_type})</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Reason for restoration (optional)
                  </label>
                  <textarea
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                    rows={3}
                    placeholder="Explain why these fields are being restored..."
                  />
                </div>
              </div>
            </div>
          )}

          {/* Preview Step */}
          {step === 'preview' && previews.length > 0 && (
            <div className="space-y-6">
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {canRestoreCount}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Can Restore</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                      {previews.filter(p => p.warnings.length > 0).length}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">With Warnings</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                      {previews.filter(p => !p.can_restore).length}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Blocked</div>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                {previews.map((preview) => (
                  <div 
                    key={preview.field_id}
                    className={`border rounded-lg p-4 ${
                      preview.can_restore 
                        ? 'border-green-200 bg-green-50 dark:border-green-700 dark:bg-green-900/20'
                        : 'border-red-200 bg-red-50 dark:border-red-700 dark:bg-red-900/20'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center space-x-2">
                        {preview.can_restore ? (
                          <CheckCircle className="w-5 h-5 text-green-500" />
                        ) : (
                          <AlertTriangle className="w-5 h-5 text-red-500" />
                        )}
                        <h4 className="font-medium text-gray-900 dark:text-white">
                          {preview.field_name}
                        </h4>
                      </div>
                      
                      {preview.records_with_data !== undefined && preview.records_with_data > 0 && (
                        <div className="flex items-center space-x-1 text-sm text-blue-600 dark:text-blue-400">
                          <Database className="w-4 h-4" />
                          <span>{preview.records_with_data} records with data</span>
                        </div>
                      )}
                    </div>

                    {preview.errors.length > 0 && (
                      <div className="mb-2">
                        <div className="text-sm font-medium text-red-700 dark:text-red-300 mb-1">Errors:</div>
                        <div className="space-y-1">
                          {preview.errors.map((error, index) => (
                            <div key={index} className="text-sm text-red-600 dark:text-red-400 flex items-start space-x-1">
                              <AlertCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                              <span>{error}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {preview.warnings.length > 0 && (
                      <div>
                        <div className="text-sm font-medium text-orange-700 dark:text-orange-300 mb-1">Warnings:</div>
                        <div className="space-y-1">
                          {preview.warnings.map((warning, index) => (
                            <div key={index} className="text-sm text-orange-600 dark:text-orange-400 flex items-start space-x-1">
                              <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                              <span>{warning}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Executing Step */}
          {step === 'executing' && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                Restoring Fields...
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Please wait while we restore your selected fields.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
          <div className="flex justify-end space-x-3">
            {step === 'confirm' && (
              <>
                <button
                  onClick={handleClose}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleRestore()}
                  disabled={restoring || selectedFields.length === 0}
                  className="flex items-center space-x-2 px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 disabled:opacity-50 transition-colors"
                >
                  {restoring ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <RotateCcw className="w-4 h-4" />
                  )}
                  <span>Restore Now</span>
                </button>
                <button
                  onClick={handlePreview}
                  disabled={previewLoading || selectedFields.length === 0}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 transition-colors"
                >
                  {previewLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                  <span>Preview Changes</span>
                </button>
              </>
            )}

            {step === 'preview' && (
              <>
                <button
                  onClick={() => setStep('confirm')}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
                >
                  Back
                </button>
                {canRestoreCount > 0 && (
                  <button
                    onClick={() => handleRestore(false)}
                    disabled={restoring}
                    className="flex items-center space-x-2 px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 disabled:opacity-50 transition-colors"
                  >
                    {restoring ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <RotateCcw className="w-4 h-4" />
                    )}
                    <span>Restore {canRestoreCount} Field{canRestoreCount > 1 ? 's' : ''}</span>
                  </button>
                )}
                {hasErrors && (
                  <button
                    onClick={() => handleRestore(true)}
                    disabled={restoring}
                    className="flex items-center space-x-2 px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 disabled:opacity-50 transition-colors"
                  >
                    {restoring ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <AlertTriangle className="w-4 h-4" />
                    )}
                    <span>Force Restore All</span>
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}