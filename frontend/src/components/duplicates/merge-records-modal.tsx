'use client'

import { useState, useEffect } from 'react'
import { X, ArrowRight, AlertTriangle, CheckCircle, Save, RefreshCw } from 'lucide-react'
import { duplicatesApi } from '@/lib/api'
import { MergeRequest, MergeDecision } from '@/types/duplicates'

interface Record {
  id: string
  data: { [key: string]: any }
}

interface DuplicateMatch {
  id: string
  record1: Record
  record2: Record
  confidence_score: number
  matched_fields: string[]
}

interface MergeRecordsModalProps {
  match: DuplicateMatch
  pipelineFields: any[]
  onClose: () => void
  onMergeComplete: (mergedRecordId: string) => void
}

export function MergeRecordsModal({ 
  match, 
  pipelineFields, 
  onClose, 
  onMergeComplete 
}: MergeRecordsModalProps) {
  const [primaryRecordId, setPrimaryRecordId] = useState<string>(match.record1.id)
  const [fieldDecisions, setFieldDecisions] = useState<{[key: string]: MergeDecision}>({})
  const [customValues, setCustomValues] = useState<{[key: string]: any}>({})
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)
  const [previewData, setPreviewData] = useState<{[key: string]: any}>({})

  // Initialize field decisions with smart defaults
  useEffect(() => {
    const initialDecisions: {[key: string]: MergeDecision} = {}
    const allFieldNames = new Set([
      ...Object.keys(match.record1.data),
      ...Object.keys(match.record2.data)
    ])

    allFieldNames.forEach(fieldName => {
      const value1 = match.record1.data[fieldName]
      const value2 = match.record2.data[fieldName]
      
      // Smart default logic
      if (value1 && !value2) {
        initialDecisions[fieldName] = { source: 'left' }
      } else if (value2 && !value1) {
        initialDecisions[fieldName] = { source: 'right' }
      } else if (value1 && value2) {
        // Both have values - default to primary record
        initialDecisions[fieldName] = { 
          source: primaryRecordId === match.record1.id ? 'left' : 'right' 
        }
      } else {
        // Both empty - default to left
        initialDecisions[fieldName] = { source: 'left' }
      }
    })

    setFieldDecisions(initialDecisions)
  }, [match, primaryRecordId])

  // Update preview data when decisions change
  useEffect(() => {
    const preview: {[key: string]: any} = {}
    const primaryRecord = primaryRecordId === match.record1.id ? match.record1 : match.record2
    const secondaryRecord = primaryRecordId === match.record1.id ? match.record2 : match.record1

    Object.keys(fieldDecisions).forEach(fieldName => {
      const decision = fieldDecisions[fieldName]
      
      switch (decision.source) {
        case 'left':
          preview[fieldName] = primaryRecord.data[fieldName]
          break
        case 'right':
          preview[fieldName] = secondaryRecord.data[fieldName]
          break
        case 'custom':
          preview[fieldName] = customValues[fieldName] ?? ''
          break
      }
    })

    setPreviewData(preview)
  }, [fieldDecisions, customValues, primaryRecordId, match])

  const handleFieldDecisionChange = (fieldName: string, source: 'left' | 'right' | 'custom') => {
    setFieldDecisions(prev => ({
      ...prev,
      [fieldName]: { source }
    }))
  }

  const handleCustomValueChange = (fieldName: string, value: any) => {
    setCustomValues(prev => ({
      ...prev,
      [fieldName]: value
    }))
    
    // Update the field decision to include the custom value
    setFieldDecisions(prev => ({
      ...prev,
      [fieldName]: { source: 'custom', value }
    }))
  }

  const handleMerge = async () => {
    setLoading(true)
    try {
      const mergeRequest: MergeRequest = {
        match_id: parseInt(match.id),
        primary_record_id: parseInt(primaryRecordId),
        field_decisions: fieldDecisions,
        notes
      }

      const response = await duplicatesApi.mergeRecords(mergeRequest)
      
      if (response.data.success) {
        onMergeComplete(response.data.merged_record_id)
        onClose()
      }
    } catch (error: any) {
      console.error('Failed to merge records:', error)
      alert('Failed to merge records: ' + (error.response?.data?.error || error.message))
    } finally {
      setLoading(false)
    }
  }

  const getFieldDisplayName = (fieldName: string) => {
    const field = pipelineFields.find(f => f.name === fieldName)
    return field?.display_name || fieldName
  }

  const getFieldType = (fieldName: string) => {
    const field = pipelineFields.find(f => f.name === fieldName)
    return field?.field_type || 'text'
  }

  const formatValue = (value: any, fieldType: string) => {
    if (value === null || value === undefined || value === '') {
      return <span className="text-gray-400 italic">Empty</span>
    }
    
    if (Array.isArray(value)) {
      return value.join(', ')
    }
    
    if (typeof value === 'object') {
      return JSON.stringify(value)
    }
    
    return String(value)
  }

  const primaryRecord = primaryRecordId === match.record1.id ? match.record1 : match.record2
  const secondaryRecord = primaryRecordId === match.record1.id ? match.record2 : match.record1

  // Get all unique field names
  const allFieldNames = Array.from(new Set([
    ...Object.keys(match.record1.data),
    ...Object.keys(match.record2.data)
  ])).sort()

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-green-100 dark:bg-green-900/20 rounded-lg">
              <ArrowRight className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">Merge Records</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Confidence: {(match.confidence_score * 100).toFixed(1)}% • Matched fields: {match.matched_fields.join(', ')}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            {/* Primary Record Selector */}
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Primary:</span>
              <select
                value={primaryRecordId}
                onChange={(e) => setPrimaryRecordId(e.target.value)}
                className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value={match.record1.id}>Record {match.record1.id}</option>
                <option value={match.record2.id}>Record {match.record2.id}</option>
              </select>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {/* Field Selection */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Field Selection
              </h3>

              {allFieldNames.map((fieldName) => {
                const leftValue = match.record1.data[fieldName]
                const rightValue = match.record2.data[fieldName]
                const decision = fieldDecisions[fieldName]
                const fieldType = getFieldType(fieldName)
                const isMatched = match.matched_fields.includes(fieldName)

                return (
                  <div key={fieldName} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                    <div className="flex items-center space-x-2 mb-3">
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        {getFieldDisplayName(fieldName)}
                      </h4>
                      {isMatched && (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      )}
                      <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                        {fieldType}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Left Value */}
                      <div className="space-y-2">
                        <div className="flex items-center space-x-2">
                          <input
                            type="radio"
                            id={`${fieldName}-left`}
                            name={`${fieldName}-source`}
                            checked={decision?.source === 'left'}
                            onChange={() => handleFieldDecisionChange(fieldName, 'left')}
                            className="text-blue-600"
                          />
                          <label htmlFor={`${fieldName}-left`} className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            Record {match.record1.id} {primaryRecordId === match.record1.id && '(Primary)'}
                          </label>
                        </div>
                        <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-md text-sm">
                          {formatValue(leftValue, fieldType)}
                        </div>
                      </div>

                      {/* Right Value */}
                      <div className="space-y-2">
                        <div className="flex items-center space-x-2">
                          <input
                            type="radio"
                            id={`${fieldName}-right`}
                            name={`${fieldName}-source`}
                            checked={decision?.source === 'right'}
                            onChange={() => handleFieldDecisionChange(fieldName, 'right')}
                            className="text-blue-600"
                          />
                          <label htmlFor={`${fieldName}-right`} className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            Record {match.record2.id} {primaryRecordId === match.record2.id && '(Primary)'}
                          </label>
                        </div>
                        <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-md text-sm">
                          {formatValue(rightValue, fieldType)}
                        </div>
                      </div>
                    </div>

                    {/* Custom Value Option */}
                    <div className="mt-3">
                      <div className="flex items-center space-x-2 mb-2">
                        <input
                          type="radio"
                          id={`${fieldName}-custom`}
                          name={`${fieldName}-source`}
                          checked={decision?.source === 'custom'}
                          onChange={() => handleFieldDecisionChange(fieldName, 'custom')}
                          className="text-blue-600"
                        />
                        <label htmlFor={`${fieldName}-custom`} className="text-sm font-medium text-gray-700 dark:text-gray-300">
                          Custom Value
                        </label>
                      </div>
                      {decision?.source === 'custom' && (
                        <input
                          type="text"
                          value={customValues[fieldName] || ''}
                          onChange={(e) => handleCustomValueChange(fieldName, e.target.value)}
                          className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                          placeholder="Enter custom value..."
                        />
                      )}
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Notes */}
            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Merge Notes
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                placeholder="Optional notes about this merge decision..."
              />
            </div>
          </div>

          {/* Preview */}
          <div className="w-80 border-l border-gray-200 dark:border-gray-700 p-6 bg-gray-50 dark:bg-gray-900">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Merge Preview
            </h3>
            
            <div className="space-y-3">
              {Object.keys(previewData).map((fieldName) => (
                <div key={fieldName} className="bg-white dark:bg-gray-800 rounded-lg p-3">
                  <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {getFieldDisplayName(fieldName)}
                  </div>
                  <div className="text-sm text-gray-900 dark:text-white">
                    {formatValue(previewData[fieldName], getFieldType(fieldName))}
                  </div>
                </div>
              ))}
            </div>

            {/* Action Buttons */}
            <div className="mt-6 space-y-3">
              <button
                onClick={handleMerge}
                disabled={loading}
                className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
              >
                {loading ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                <span>{loading ? 'Merging...' : 'Merge Records'}</span>
              </button>
              
              <button
                onClick={onClose}
                disabled={loading}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
              >
                Cancel
              </button>
            </div>

            {/* Warning */}
            <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg flex items-start space-x-2">
              <AlertTriangle className="w-4 h-4 text-yellow-600 dark:text-yellow-400 mt-0.5" />
              <div className="text-xs text-yellow-800 dark:text-yellow-300">
                The secondary record will be soft-deleted. This action can be reversed.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}