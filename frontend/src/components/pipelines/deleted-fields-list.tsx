'use client'

import React, { useState } from 'react'
import { 
  Archive, 
  RotateCcw, 
  Calendar, 
  User,
  CheckCircle,
  AlertCircle,
  Loader2,
  Trash2,
  Database
} from 'lucide-react'
import { pipelinesApi } from '@/lib/api'
import { BulkRestoreModal } from './bulk-restore-modal'

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
  label?: string
  type?: string
  required?: boolean
  visible?: boolean
  order?: number
  config?: Record<string, any>
}

interface DeletedFieldsListProps {
  pipelineId: string
  fields: PipelineField[]
  loading: boolean
  onRefresh: () => void
  onFieldRestored: () => void
}

export function DeletedFieldsList({ 
  pipelineId, 
  fields, 
  loading, 
  onRefresh, 
  onFieldRestored 
}: DeletedFieldsListProps) {
  const [selectedFields, setSelectedFields] = useState<Set<string>>(new Set())
  const [restoringFields, setRestoringFields] = useState<Set<string>>(new Set())
  const [showBulkRestore, setShowBulkRestore] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSelectField = (fieldId: string) => {
    const newSelected = new Set(selectedFields)
    if (newSelected.has(fieldId)) {
      newSelected.delete(fieldId)
    } else {
      newSelected.add(fieldId)
    }
    setSelectedFields(newSelected)
  }

  const handleSelectAll = () => {
    if (selectedFields.size === fields.length) {
      setSelectedFields(new Set())
    } else {
      setSelectedFields(new Set(fields.map(f => f.id)))
    }
  }

  const handleRestoreField = async (field: PipelineField) => {
    try {
      setRestoringFields(prev => new Set([...prev, field.id]))
      setError(null)

      await pipelinesApi.restoreField(pipelineId, field.id, { 
        reason: 'Individual restore from deleted fields list' 
      })
      
      onFieldRestored()
    } catch (err: any) {
      console.error('Failed to restore field:', err)
      setError(err?.response?.data?.error || 'Failed to restore field')
    } finally {
      setRestoringFields(prev => {
        const newSet = new Set(prev)
        newSet.delete(field.id)
        return newSet
      })
    }
  }

  const handleBulkRestoreSuccess = () => {
    setSelectedFields(new Set())
    setShowBulkRestore(false)
    onFieldRestored()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading deleted fields...</div>
      </div>
    )
  }

  if (fields.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <Archive className="w-12 h-12 text-gray-300 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
          No Deleted Fields
        </h3>
        <p className="text-gray-500 dark:text-gray-400">
          This pipeline has no deleted fields. Fields that are soft-deleted will appear here.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 text-red-400 mr-2" />
            <span className="text-red-800 text-sm">{error}</span>
          </div>
        </div>
      )}

      {/* Header with Bulk Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            Deleted Fields ({fields.length})
          </h3>
          
          {fields.length > 0 && (
            <label className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-300">
              <input
                type="checkbox"
                checked={selectedFields.size === fields.length && fields.length > 0}
                onChange={handleSelectAll}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span>Select all</span>
            </label>
          )}
        </div>

        <div className="flex items-center space-x-2">
          {selectedFields.size > 0 && (
            <>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {selectedFields.size} selected
              </span>
              <button
                onClick={() => setShowBulkRestore(true)}
                className="flex items-center space-x-2 px-3 py-1.5 text-sm bg-green-500 text-white rounded-md hover:bg-green-600 transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                <span>Restore Selected</span>
              </button>
            </>
          )}
          
          <button
            onClick={onRefresh}
            disabled={loading}
            className="flex items-center space-x-2 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
          >
            <RotateCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Fields Grid */}
      <div className="grid gap-4">
        {fields.map((field) => {
          const isSelected = selectedFields.has(field.id)
          const isRestoring = restoringFields.has(field.id)
          
          return (
            <div 
              key={field.id} 
              className={`border rounded-lg p-4 transition-all ${
                isSelected 
                  ? 'border-blue-300 bg-blue-50 dark:border-blue-600 dark:bg-blue-900/20'
                  : 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3 flex-1">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => handleSelectField(field.id)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        {field.display_name || field.name}
                      </h4>
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300">
                        {field.field_type}
                      </span>
                      
                      {field.is_ai_field && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300">
                          AI
                        </span>
                      )}
                    </div>
                    
                    {field.description && (
                      <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">
                        {field.description}
                      </p>
                    )}
                    
                    <div className="flex items-center space-x-4 text-xs text-gray-500 dark:text-gray-400">
                      {field.deleted_at && (
                        <div className="flex items-center space-x-1">
                          <Calendar className="w-3 h-3" />
                          <span>Deleted: {new Date(field.deleted_at).toLocaleDateString()}</span>
                        </div>
                      )}
                      {field.deleted_by && (
                        <div className="flex items-center space-x-1">
                          <User className="w-3 h-3" />
                          <span>By: {field.deleted_by}</span>
                        </div>
                      )}
                      <div className="flex items-center space-x-1">
                        <Database className="w-3 h-3" />
                        <span>ID: {field.id}</span>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleRestoreField(field)}
                    disabled={isRestoring}
                    className="flex items-center space-x-1 px-3 py-1.5 text-sm text-green-600 hover:text-green-700 border border-green-300 rounded-md hover:bg-green-50 transition-colors disabled:opacity-50"
                  >
                    {isRestoring ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <RotateCcw className="w-3 h-3" />
                    )}
                    <span>{isRestoring ? 'Restoring...' : 'Restore'}</span>
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Advanced Bulk Restore Modal */}
      <BulkRestoreModal
        isOpen={showBulkRestore}
        onClose={() => setShowBulkRestore(false)}
        pipelineId={pipelineId}
        selectedFields={fields.filter(field => selectedFields.has(field.id))}
        onSuccess={handleBulkRestoreSuccess}
      />
    </div>
  )
}