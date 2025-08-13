'use client'

import React, { useState, useEffect } from 'react'
import { 
  AlertTriangle, 
  CheckCircle, 
  X, 
  Eye,
  Link,
  Trash2,
  ArrowRight,
  Clock,
  User,
  Filter,
  MoreVertical,
  ExternalLink,
  GitMerge,
  ShieldCheck,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  RefreshCw
} from 'lucide-react'
import { duplicatesApi, pipelinesApi } from '@/lib/api'
import { MergeRecordsModal } from './merge-records-modal'
import { FieldResolver } from '@/lib/field-system/field-registry'

interface DuplicateMatch {
  id: string
  rule: {
    id: string
    name: string
  }
  record1: {
    id: string
    data: { [key: string]: any }
  }
  record2: {
    id: string
    data: { [key: string]: any }
  }
  confidence_score: number
  matched_fields: string[]
  detection_method: string
  status: 'pending' | 'confirmed' | 'false_positive' | 'merged' | 'ignored' | 'auto_resolved' | 'resolved'
  detected_at: string
  reviewed_by?: {
    id: string
    name: string
    email: string
  }
  reviewed_at?: string
  resolution_notes?: string
  field_scores?: any
  latest_resolution?: {
    id: number
    action_taken: string
    resolved_by: string
    resolved_at: string
    notes: string
  }
}

interface DuplicateMatchesViewProps {
  pipelineId: string
}

export function DuplicateMatchesView({ pipelineId }: DuplicateMatchesViewProps) {
  const [matches, setMatches] = useState<DuplicateMatch[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedMatches, setSelectedMatches] = useState<string[]>([])
  const [showBulkActions, setShowBulkActions] = useState(false)
  const [filterStatus, setFilterStatus] = useState<'all' | 'pending' | 'resolved' | 'false_positive'>('all')
  const [showMergeModal, setShowMergeModal] = useState(false)
  const [selectedMatch, setSelectedMatch] = useState<DuplicateMatch | null>(null)
  const [pipelineFields, setPipelineFields] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)
  const [debugInfo, setDebugInfo] = useState<any>(null)
  const [expandedMatches, setExpandedMatches] = useState<Set<string>>(new Set())

  // Load duplicate matches
  useEffect(() => {
    if (pipelineId) {
      loadDuplicateMatches()
      loadPipelineFields()
    }
  }, [pipelineId, filterStatus])

  const loadPipelineFields = async () => {
    try {
      const response = await pipelinesApi.get(pipelineId)
      setPipelineFields(response.data.fields || [])
    } catch (error) {
      console.error('Failed to load pipeline fields:', error)
    }
  }

  const loadDuplicateMatches = async () => {
    try {
      setLoading(true)
      setError(null)
      
      console.log('🔍 Loading duplicate matches for pipeline:', pipelineId)
      const response = await duplicatesApi.getDuplicateMatches(pipelineId)
      
      // Debug logging
      console.log('🔍 Raw API response:', {
        status: response.status,
        data: response.data,
        dataType: typeof response.data,
        hasResults: 'results' in response.data,
        resultsLength: response.data.results?.length || 0,
        firstMatch: response.data.results?.[0]
      })
      
      setDebugInfo({
        apiResponse: response.data,
        responseStatus: response.status,
        dataStructure: Object.keys(response.data),
        resultsCount: response.data.results?.length || 0
      })
      
      // Transform and filter matches
      const rawMatches = response.data.results || response.data || []
      console.log('🔍 Raw matches array:', rawMatches)
      
      const transformedMatches: DuplicateMatch[] = rawMatches
        .filter((match: any) => {
          // Filter by pipeline (if we had pipeline filtering in API)
          if (filterStatus !== 'all') {
            return match.status === filterStatus
          }
          return true
        })
        .map((match: any) => {
          console.log('🔍 Transforming match:', match)
          return {
            id: match.id?.toString() || '',
            rule: match.rule || { id: '', name: 'Unknown Rule' },
            record1: match.record1 || { id: '', data: {} },
            record2: match.record2 || { id: '', data: {} },
            confidence_score: match.confidence_score || 0,
            matched_fields: match.matched_fields || [],
            detection_method: match.detection_method || '',
            status: match.status || 'pending',
            detected_at: match.detected_at || new Date().toISOString(),
            reviewed_by: match.reviewed_by,
            reviewed_at: match.reviewed_at,
            resolution_notes: match.resolution_notes,
            field_scores: match.field_scores
          }
        })
      
      console.log('🔍 Transformed matches:', transformedMatches)
      setMatches(transformedMatches)
    } catch (error: any) {
      console.error('❌ Failed to load duplicate matches:', error)
      setError(`Failed to load matches: ${error.response?.data?.detail || error.message}`)
      setDebugInfo({
        error: error.message,
        errorResponse: error.response?.data,
        errorStatus: error.response?.status
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSelectMatch = (matchId: string) => {
    setSelectedMatches(prev => {
      const newSelection = prev.includes(matchId) 
        ? prev.filter(id => id !== matchId)
        : [...prev, matchId]
      
      setShowBulkActions(newSelection.length > 0)
      return newSelection
    })
  }

  const handleSelectAll = () => {
    const pendingMatches = matches.filter(m => m.status === 'pending').map(m => m.id)
    setSelectedMatches(pendingMatches)
    setShowBulkActions(pendingMatches.length > 0)
  }

  const handleDeselectAll = () => {
    setSelectedMatches([])
    setShowBulkActions(false)
  }

  const handleBulkResolve = async (action: 'merge' | 'keep_both' | 'ignore') => {
    try {
      await duplicatesApi.bulkResolveDuplicates({
        match_ids: selectedMatches,
        action,
        notes: `Bulk ${action} action`
      }, pipelineId)
      
      // Refresh matches
      await loadDuplicateMatches()
      
      // Clear selection
      setSelectedMatches([])
      setShowBulkActions(false)
    } catch (error: any) {
      console.error('Failed to bulk resolve matches:', error)
      alert('Failed to resolve matches: ' + (error.response?.data?.error || error.message))
    }
  }

  const handleIndividualMerge = (match: DuplicateMatch) => {
    setSelectedMatch(match)
    setShowMergeModal(true)
  }

  const handleIndividualResolve = async (matchId: string, action: 'keep_both' | 'ignore') => {
    try {
      await duplicatesApi.bulkResolveDuplicates({
        match_ids: [matchId],
        action,
        notes: `Individual ${action} action`
      }, pipelineId)
      
      await loadDuplicateMatches()
    } catch (error: any) {
      console.error('Failed to resolve match:', error)
      alert('Failed to resolve match: ' + (error.response?.data?.error || error.message))
    }
  }

  const handleMergeComplete = (mergedRecordId: string) => {
    loadDuplicateMatches()
    // Optional: Show success message or redirect to merged record
  }

  const handleRollback = async (match: DuplicateMatch) => {
    try {
      // Check if we have resolution information
      if (!match.latest_resolution) {
        alert('No resolution information found for this match. Cannot rollback.')
        return
      }
      
      const resolution = match.latest_resolution
      
      const confirmed = window.confirm(
        `Are you sure you want to rollback this "${resolution.action_taken}" resolution?\n\n` +
        `This will:\n` +
        `• Restore the match to pending state\n` +
        `${resolution.action_taken === 'merge' ? '• Restore any deleted records\n' : ''}` +
        `${resolution.action_taken === 'ignore' ? '• Remove exclusion rules\n' : ''}` +
        `• Undo any data changes made during resolution\n\n` +
        `Original resolution by: ${resolution.resolved_by}\n` +
        `Date: ${new Date(resolution.resolved_at).toLocaleDateString()}`
      )
      
      if (!confirmed) return
      
      await duplicatesApi.rollbackResolution({
        resolution_id: resolution.id,
        notes: `User-initiated rollback of "${resolution.action_taken}" resolution from duplicate matches view`
      })
      
      // Refresh the matches list
      await loadDuplicateMatches()
      
      // Show success message
      console.log(`${resolution.action_taken} resolution rolled back successfully`)
      
    } catch (error: any) {
      console.error('Failed to rollback resolution:', error)
      
      // More detailed error handling
      let errorMessage = 'Failed to rollback resolution'
      if (error.response?.data?.error) {
        errorMessage += ': ' + error.response.data.error
      } else if (error.message) {
        errorMessage += ': ' + error.message
      }
      
      alert(errorMessage)
    }
  }

  const toggleMatchExpanded = (matchId: string) => {
    setExpandedMatches(prev => {
      const newExpanded = new Set(prev)
      if (newExpanded.has(matchId)) {
        newExpanded.delete(matchId)
      } else {
        newExpanded.add(matchId)
      }
      return newExpanded
    })
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return (
          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400">
            <Clock className="w-3 h-3 mr-1" />
            Pending
          </span>
        )
      case 'resolved':
        return (
          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">
            <CheckCircle className="w-3 h-3 mr-1" />
            Resolved
          </span>
        )
      case 'false_positive':
        return (
          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400">
            <X className="w-3 h-3 mr-1" />
            False Positive
          </span>
        )
      default:
        return null
    }
  }

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'text-red-600 dark:text-red-400'
    if (score >= 0.6) return 'text-orange-600 dark:text-orange-400'
    return 'text-yellow-600 dark:text-yellow-400'
  }

  const getConfidenceLabel = (score: number) => {
    if (score >= 0.9) return 'Very High Confidence'
    if (score >= 0.8) return 'High Confidence'
    if (score >= 0.6) return 'Medium Confidence'
    if (score >= 0.4) return 'Low Confidence'
    return 'Weak Confidence'
  }

  // Format field values using the field system's formatValue method
  const formatFieldValue = (value: any, fieldName: string): string => {
    if (value === null || value === undefined) {
      return '—'
    }

    // Try to find the field definition from pipeline fields
    const field = pipelineFields.find(f => f.name === fieldName || f.display_name === fieldName)
    
    if (field) {
      try {
        // Use the field system's formatValue method for proper formatting
        const formatted = FieldResolver.formatValue(field, value, 'table')
        
        // Handle JSX elements returned by formatValue - convert to string
        if (typeof formatted === 'string') {
          return formatted
        } else if (React.isValidElement(formatted)) {
          // For JSX elements, extract the text content or return a string representation
          return String(value)
        }
        // Convert other types to string
        return String(formatted)
      } catch (error) {
        console.warn('Field formatting failed for', fieldName, ':', error)
        // Fallback to basic formatting
      }
    }

    // Fallback formatting for when field definition isn't available
    if (typeof value === 'object' && value !== null) {
      // Handle currency objects
      if (value.amount !== undefined && value.currency !== undefined) {
        try {
          return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: value.currency || 'USD'
          }).format(value.amount)
        } catch {
          return `${value.currency || '$'} ${value.amount}`
        }
      }
      
      // Handle other objects
      if (Array.isArray(value)) {
        return value.join(', ')
      }
      
      // For other objects, try to find a display value
      if (value.name) return value.name
      if (value.title) return value.title
      if (value.label) return value.label
      
      return JSON.stringify(value)
    }

    return String(value)
  }

  // Render collapsed match summary
  const renderMatchSummary = (match: DuplicateMatch) => {
    const record1Data = match.record1.data || {}
    const record2Data = match.record2.data || {}
    
    // Only show the matched/duplicate fields in the preview
    const getMatchedFieldsPreview = (data: any, matchedFields: string[]) => {
      return matchedFields
        .map(fieldName => [fieldName, data[fieldName]])
        .filter(([_, value]) => value !== null && value !== undefined && value !== '')
        .slice(0, 3) // Limit to 3 fields for clean display
    }

    const record1Preview = getMatchedFieldsPreview(record1Data, match.matched_fields)
    const record2Preview = getMatchedFieldsPreview(record2Data, match.matched_fields)

    return (
      <div className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
        <div className="flex items-center justify-between">
          {/* Left side - Match info and preview */}
          <div className="flex items-center space-x-4 flex-1 min-w-0">
            {/* Expand/collapse button */}
            <button
              onClick={() => toggleMatchExpanded(match.id)}
              className="flex-shrink-0 p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
            >
              <ChevronRight className="w-4 h-4 text-gray-500" />
            </button>

            {/* Match metadata */}
            <div className="flex items-center space-x-3">
              {getStatusBadge(match.status)}
              <div className="flex flex-col">
                <span 
                  className={`text-sm font-semibold ${getConfidenceColor(match.confidence_score)}`}
                  title={`System confidence that the duplicate detection rule correctly identified these records as duplicates. Based on rule "${match.rule.name}" matching ${match.matched_fields.length} field(s): ${match.matched_fields.join(', ')}`}
                >
                  {Math.round(match.confidence_score * 100)}% Rule Confidence
                </span>
                <span className="text-xs text-gray-500">
                  How confident the rule detection is
                </span>
              </div>
              <span className="text-xs text-gray-500">
                {match.matched_fields.length} fields matched
              </span>
            </div>

            {/* Matched fields preview */}
            <div className="flex-1 min-w-0">
              {match.matched_fields.length > 0 ? (
                <div className="space-y-2">
                  <span className="text-xs text-gray-500 font-medium">Matched Fields:</span>
                  <div className="flex flex-col space-y-1">
                    {record1Preview.slice(0, 2).map(([fieldName, value1]) => {
                      const value2 = record2Data[fieldName]
                      return (
                        <div key={fieldName} className="flex items-center space-x-2 text-xs">
                          <span className="font-medium text-gray-600 dark:text-gray-400 min-w-[80px]">
                            {fieldName}:
                          </span>
                          <span className="bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-300 px-2 py-1 rounded truncate max-w-[120px]">
                            {formatFieldValue(value1, fieldName)}
                          </span>
                          <span className="text-gray-400">≈</span>
                          <span className="bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-300 px-2 py-1 rounded truncate max-w-[120px]">
                            {formatFieldValue(value2, fieldName)}
                          </span>
                        </div>
                      )
                    })}
                    {match.matched_fields.length > 2 && (
                      <span className="text-xs text-gray-500">
                        +{match.matched_fields.length - 2} more matched fields
                      </span>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-xs text-gray-500">
                  No specific field matches detected
                </div>
              )}
            </div>
          </div>

          {/* Right side - Actions */}
          <div className="flex items-center space-x-2 flex-shrink-0 ml-4">
            {match.status === 'pending' ? (
              // Unresolved match actions
              <>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleIndividualMerge(match)
                  }}
                  className="px-3 py-1.5 bg-green-500 text-white rounded-md hover:bg-green-600 text-xs font-medium flex items-center space-x-1 transition-colors"
                >
                  <GitMerge className="w-3 h-3" />
                  <span>Merge</span>
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleIndividualResolve(match.id, 'keep_both')
                  }}
                  className="px-3 py-1.5 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-xs font-medium flex items-center space-x-1 transition-colors"
                >
                  <ShieldCheck className="w-3 h-3" />
                  <span>Keep Both</span>
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleIndividualResolve(match.id, 'ignore')
                  }}
                  className="px-3 py-1.5 bg-gray-500 text-white rounded-md hover:bg-gray-600 text-xs font-medium flex items-center space-x-1 transition-colors"
                >
                  <X className="w-3 h-3" />
                  <span>Ignore</span>
                </button>
              </>
            ) : (
              // Resolved match actions - show rollback button
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleRollback(match)
                }}
                className="px-3 py-1.5 bg-orange-500 text-white rounded-md hover:bg-orange-600 text-xs font-medium flex items-center space-x-1 transition-colors"
                title={`Rollback "${match.latest_resolution?.action_taken || match.status}" resolution${match.latest_resolution?.resolved_by ? ` by ${match.latest_resolution.resolved_by}` : ''}`}
              >
                <RefreshCw className="w-3 h-3" />
                <span>Rollback {match.latest_resolution?.action_taken || match.status}</span>
              </button>
            )}
          </div>
        </div>

        {/* Quick info line */}
        <div className="mt-2 text-xs text-gray-500 flex items-center space-x-4">
          <span>Rule: {match.rule.name}</span>
          <span>•</span>
          <span>Detected: {new Date(match.detected_at).toLocaleDateString()}</span>
          <span>•</span>
          <span>IDs: {match.record1.id} & {match.record2.id}</span>
        </div>
      </div>
    )
  }

  // New split-screen record comparison component with field grouping
  const renderRecordComparison = (match: DuplicateMatch) => {
    const record1Data = match.record1.data || {}
    const record2Data = match.record2.data || {}
    
    // Get all unique field names from both records
    const allFieldNames = Array.from(new Set([
      ...Object.keys(record1Data),
      ...Object.keys(record2Data)
    ]))
    
    // Organize fields by groups using pipeline field definitions
    const groupedFields = new Map<string | null, any[]>()
    
    // First, organize fields by their groups based on pipeline field definitions
    allFieldNames.forEach(fieldName => {
      const fieldDef = pipelineFields.find(f => f.name === fieldName || f.slug === fieldName)
      const groupId = fieldDef?.field_group ? String(fieldDef.field_group) : null
      
      if (!groupedFields.has(groupId)) {
        groupedFields.set(groupId, [])
      }
      
      groupedFields.get(groupId)!.push({
        name: fieldName,
        definition: fieldDef,
        displayOrder: fieldDef?.display_order || 999,
        isMatched: match.matched_fields.includes(fieldName),
        value1: record1Data[fieldName],
        value2: record2Data[fieldName]
      })
    })
    
    // Sort fields within each group by display_order
    groupedFields.forEach(fields => {
      fields.sort((a, b) => a.displayOrder - b.displayOrder)
    })
    
    // Get group definitions for headers and sort by display_order, then by name for ties
    const fieldGroups = pipelineFields
      .map(f => f.field_group_details)
      .filter((group, index, arr) => group && arr.findIndex(g => g?.id === group.id) === index)
      .sort((a, b) => {
        const orderA = a?.display_order ?? 999
        const orderB = b?.display_order ?? 999
        
        // Primary sort: display_order
        if (orderA !== orderB) {
          return orderA - orderB
        }
        
        // Secondary sort: name (for stable sorting when display_order is the same)
        return (a?.name || '').localeCompare(b?.name || '')
      })
    
    console.log('🔍 Field Groups Debug:', {
      pipelineFieldsCount: pipelineFields.length,
      fieldsWithGroups: pipelineFields.filter(f => f.field_group_details).length,
      uniqueGroups: fieldGroups.length,
      groupDetails: fieldGroups.map(g => ({ id: g?.id, name: g?.name, color: g?.color, display_order: g?.display_order })),
      renderOrder: fieldGroups.map(g => `${g?.display_order}: ${g?.name}`),
      beforeSort: pipelineFields
        .map(f => f.field_group_details)
        .filter((group, index, arr) => group && arr.findIndex(g => g?.id === group.id) === index)
        .map(g => `${g?.display_order}: ${g?.name}`),
      afterSort: fieldGroups.map(g => `${g?.display_order}: ${g?.name}`)
    })

    return (
      <div className="overflow-hidden">
        {/* Header with confidence score and actions */}
        <div className="bg-gradient-to-r from-orange-50 to-red-50 dark:from-orange-900/20 dark:to-red-900/20 px-6 py-4 border-b border-gray-200 dark:border-gray-600">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              {/* Collapse button */}
              <button
                onClick={() => toggleMatchExpanded(match.id)}
                className="flex-shrink-0 p-1 hover:bg-orange-200 dark:hover:bg-orange-700 rounded"
              >
                <ChevronDown className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              </button>
              
              <div className="flex items-center space-x-3">
                {getStatusBadge(match.status)}
                <div className="flex flex-col">
                  <span 
                    className={`text-lg font-bold ${getConfidenceColor(match.confidence_score)}`}
                    title={`System confidence that duplicate rule "${match.rule.name}" correctly identified these records as duplicates by matching ${match.matched_fields.length} field(s)`}
                  >
                    {Math.round(match.confidence_score * 100)}% Rule Confidence
                  </span>
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {getConfidenceLabel(match.confidence_score)} • {match.matched_fields.length} fields matched by rule
                  </span>
                </div>
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">
                Rule: {match.rule.name} • {new Date(match.detected_at).toLocaleDateString()}
              </div>
            </div>
            
            {/* Actions */}
            <div className="flex items-center space-x-2">
              {match.status === 'pending' ? (
                // Unresolved match actions
                <>
                  <button
                    onClick={() => handleIndividualMerge(match)}
                    className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 text-sm font-medium flex items-center space-x-2 transition-colors"
                  >
                    <GitMerge className="w-4 h-4" />
                    <span>Merge Records</span>
                  </button>
                  <button
                    onClick={() => handleIndividualResolve(match.id, 'keep_both')}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm font-medium flex items-center space-x-2 transition-colors"
                  >
                    <ShieldCheck className="w-4 h-4" />
                    <span>Keep Both</span>
                  </button>
                  <button
                    onClick={() => handleIndividualResolve(match.id, 'ignore')}
                    className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 text-sm font-medium flex items-center space-x-2 transition-colors"
                  >
                    <X className="w-4 h-4" />
                    <span>False Positive</span>
                  </button>
                </>
              ) : (
                // Resolved match actions - show rollback button
                <button
                  onClick={() => handleRollback(match)}
                  className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 text-sm font-medium flex items-center space-x-2 transition-colors"
                  title={`Rollback "${match.latest_resolution?.action_taken || match.status}" resolution${match.latest_resolution?.resolved_by ? ` by ${match.latest_resolution.resolved_by}` : ''}`}
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Rollback {match.latest_resolution?.action_taken || 'Resolution'}</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Field comparison with grouping and horizontal alignment */}
        <div className="divide-y divide-gray-200 dark:divide-gray-600">
          {/* Header row with record info */}
          <div className="grid grid-cols-1 lg:grid-cols-3 divide-x divide-gray-200 dark:divide-gray-600">
            {/* Record A Header */}
            <div className="p-4 bg-gray-50 dark:bg-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Record A</h3>
                  <div className="text-sm text-gray-500 dark:text-gray-400">ID: {match.record1.id}</div>
                </div>
                <button
                  onClick={() => window.open(`/pipelines/${pipelineId}/records/${match.record1.id}`, '_blank')}
                  className="p-2 text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
                  title="View Record A"
                >
                  <ExternalLink className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Center Header with confidence */}
            <div className="hidden lg:flex flex-col items-center justify-center p-4 bg-gray-100 dark:bg-gray-800">
              <div className="text-center">
                <div className={`text-xl font-bold mb-1 ${getConfidenceColor(match.confidence_score)}`}>
                  {Math.round(match.confidence_score * 100)}%
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">RULE CONFIDENCE</div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {getConfidenceLabel(match.confidence_score)}
                </div>
              </div>
            </div>

            {/* Record B Header */}
            <div className="p-4 bg-gray-50 dark:bg-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Record B</h3>
                  <div className="text-sm text-gray-500 dark:text-gray-400">ID: {match.record2.id}</div>
                </div>
                <button
                  onClick={() => window.open(`/pipelines/${pipelineId}/records/${match.record2.id}`, '_blank')}
                  className="p-2 text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
                  title="View Record B"
                >
                  <ExternalLink className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Field groups - sorted by display_order */}
          {fieldGroups.map(groupDef => {
            const groupId = String(groupDef.id)
            const fields = groupedFields.get(groupId) || []
            
            if (fields.length === 0) return null
            
            return (
              <div key={groupId || 'ungrouped'} className="border-t border-gray-200 dark:border-gray-600">
                {/* Group header */}
                <div className="px-6 py-3 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-600">
                  <div className="flex items-center space-x-2">
                    {groupDef ? (
                      <>
                        {groupDef.icon && (
                          <div
                            className="w-4 h-4 rounded flex items-center justify-center"
                            style={{ backgroundColor: groupDef.color || '#6B7280' }}
                          >
                            {/* Icon would go here - simplified for now */}
                            <div className="w-2 h-2 bg-white rounded-full" />
                          </div>
                        )}
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                          {groupDef.name}
                        </h4>
                        {groupDef.description && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {groupDef.description}
                          </span>
                        )}
                      </>
                    ) : (
                      <>
                        <div className="w-4 h-4 rounded bg-gray-400 flex items-center justify-center">
                          <div className="w-2 h-2 bg-white rounded-full" />
                        </div>
                        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                          Other Fields
                        </h4>
                      </>
                    )}
                  </div>
                </div>

                {/* Fields in this group */}
                <div className="divide-y divide-gray-100 dark:divide-gray-700">
                  {fields.map(field => (
                    <div
                      key={field.name}
                      className={`grid grid-cols-1 lg:grid-cols-3 divide-x divide-gray-100 dark:divide-gray-700 ${
                        field.isMatched ? 'bg-orange-50 dark:bg-orange-900/10' : ''
                      }`}
                    >
                      {/* Record A Value */}
                      <div className="p-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 flex items-center">
                            {field.definition?.display_name || field.name}
                            {field.isMatched && (
                              <CheckCircle className="w-3 h-3 ml-1 text-orange-500" />
                            )}
                          </div>
                        </div>
                        <div className="text-sm text-gray-900 dark:text-white font-medium break-words">
                          {formatFieldValue(field.value1, field.name)}
                        </div>
                      </div>

                      {/* Match indicator (desktop only) */}
                      <div className="hidden lg:flex items-center justify-center p-2">
                        {field.isMatched ? (
                          <div className="flex items-center space-x-1 text-orange-600 dark:text-orange-400">
                            <CheckCircle className="w-4 h-4" />
                            <span className="text-xs font-medium">MATCH</span>
                          </div>
                        ) : field.value1 !== field.value2 ? (
                          <div className="flex items-center space-x-1 text-gray-400">
                            <X className="w-4 h-4" />
                            <span className="text-xs">DIFF</span>
                          </div>
                        ) : (
                          <div className="flex items-center space-x-1 text-green-500">
                            <CheckCircle className="w-4 h-4" />
                            <span className="text-xs">SAME</span>
                          </div>
                        )}
                      </div>

                      {/* Record B Value */}
                      <div className="p-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 flex items-center">
                            {field.definition?.display_name || field.name}
                            {field.isMatched && (
                              <CheckCircle className="w-3 h-3 ml-1 text-orange-500" />
                            )}
                          </div>
                        </div>
                        <div className="text-sm text-gray-900 dark:text-white font-medium break-words">
                          {formatFieldValue(field.value2, field.name)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
          
          {/* Ungrouped fields */}
          {(() => {
            const ungroupedFields = groupedFields.get(null) || []
            if (ungroupedFields.length === 0) return null
            
            return (
              <div key="ungrouped" className="border-t border-gray-200 dark:border-gray-600">
                {/* Group header for ungrouped fields */}
                <div className="px-6 py-3 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-600">
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 rounded bg-gray-400 flex items-center justify-center">
                      <div className="w-2 h-2 bg-white rounded-full" />
                    </div>
                    <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                      Other Fields
                    </h4>
                  </div>
                </div>

                {/* Fields in ungrouped section */}
                <div className="divide-y divide-gray-100 dark:divide-gray-700">
                  {ungroupedFields.map(field => (
                    <div
                      key={field.name}
                      className={`grid grid-cols-1 lg:grid-cols-3 divide-x divide-gray-100 dark:divide-gray-700 ${
                        field.isMatched ? 'bg-orange-50 dark:bg-orange-900/10' : ''
                      }`}
                    >
                      {/* Record A Value */}
                      <div className="p-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 flex items-center">
                            {field.definition?.display_name || field.name}
                            {field.isMatched && (
                              <CheckCircle className="w-3 h-3 ml-1 text-orange-500" />
                            )}
                          </div>
                        </div>
                        <div className="text-sm text-gray-900 dark:text-white font-medium break-words">
                          {formatFieldValue(field.value1, field.name)}
                        </div>
                      </div>

                      {/* Match indicator (desktop only) */}
                      <div className="hidden lg:flex items-center justify-center p-2">
                        {field.isMatched ? (
                          <div className="flex items-center space-x-1 text-orange-600 dark:text-orange-400">
                            <CheckCircle className="w-4 h-4" />
                            <span className="text-xs font-medium">MATCH</span>
                          </div>
                        ) : field.value1 !== field.value2 ? (
                          <div className="flex items-center space-x-1 text-gray-400">
                            <X className="w-4 h-4" />
                            <span className="text-xs">DIFF</span>
                          </div>
                        ) : (
                          <div className="flex items-center space-x-1 text-green-500">
                            <CheckCircle className="w-4 h-4" />
                            <span className="text-xs font-medium">SAME</span>
                          </div>
                        )}
                      </div>

                      {/* Record B Value */}
                      <div className="p-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 flex items-center">
                            {field.definition?.display_name || field.name}
                            {field.isMatched && (
                              <CheckCircle className="w-3 h-3 ml-1 text-orange-500" />
                            )}
                          </div>
                        </div>
                        <div className="text-sm text-gray-900 dark:text-white font-medium break-words">
                          {formatFieldValue(field.value2, field.name)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })()}
        </div>

        {/* Resolution Notes */}
        {match.resolution_notes && (
          <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600">
            <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Resolution Notes:
            </h5>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {match.resolution_notes}
            </p>
            {match.reviewed_by && (
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-2">
                Resolved by {match.reviewed_by.name} on {new Date(match.reviewed_at!).toLocaleDateString()}
              </p>
            )}
          </div>
        )}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading duplicate matches...</p>
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
            Duplicate Matches
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Review and resolve detected duplicate records
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex items-center space-x-3">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as any)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="resolved">Resolved</option>
            <option value="false_positive">False Positive</option>
          </select>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <div>
              <h3 className="text-red-800 dark:text-red-400 font-semibold">Error Loading Matches</h3>
              <p className="text-red-700 dark:text-red-300 text-sm mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Debug Info (Development Only) */}
      {process.env.NODE_ENV === 'development' && debugInfo && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <h3 className="text-blue-800 dark:text-blue-400 font-semibold mb-2">🔧 Debug Information</h3>
          <pre className="text-xs text-blue-700 dark:text-blue-300 overflow-auto max-h-40">
            {JSON.stringify(debugInfo, null, 2)}
          </pre>
        </div>
      )}

      {/* Bulk Actions */}
      {showBulkActions && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-5 h-5 text-blue-500" />
              <span className="text-blue-800 dark:text-blue-300 font-medium">
                {selectedMatches.length} matches selected
              </span>
            </div>
            
            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleBulkResolve('merge')}
                className="px-3 py-1 bg-green-500 text-white rounded-md hover:bg-green-600 text-sm flex items-center space-x-1"
              >
                <GitMerge className="w-3 h-3" />
                <span>Merge</span>
              </button>
              <button
                onClick={() => handleBulkResolve('keep_both')}
                className="px-3 py-1 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm flex items-center space-x-1"
              >
                <ShieldCheck className="w-3 h-3" />
                <span>Keep Both</span>
              </button>
              <button
                onClick={() => handleBulkResolve('ignore')}
                className="px-3 py-1 bg-gray-500 text-white rounded-md hover:bg-gray-600 text-sm flex items-center space-x-1"
              >
                <X className="w-3 h-3" />
                <span>Ignore</span>
              </button>
              <button
                onClick={handleDeselectAll}
                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Matches List */}
      <div className="space-y-4">
        {matches.length === 0 && !loading && !error ? (
          <div className="text-center py-12">
            <AlertTriangle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              No duplicate matches found
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              {filterStatus === 'all' 
                ? 'Your duplicate detection rules haven\'t found any matches yet.'
                : `No matches with status "${filterStatus}" found.`
              }
            </p>
            
            {/* Enhanced Empty State Information */}
            <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 max-w-md mx-auto">
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Possible reasons:
              </h4>
              <ul className="text-xs text-gray-600 dark:text-gray-400 text-left space-y-1">
                <li>• No duplicate detection rules are configured</li>
                <li>• Rules are set to "disabled" mode</li>
                <li>• Detection hasn't run yet (it runs on record creation/update)</li>
                <li>• No actual duplicates exist in your data</li>
                <li>• API endpoint may not be returning data correctly</li>
              </ul>
              
              {process.env.NODE_ENV === 'development' && debugInfo && (
                <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
                  <p className="text-xs text-blue-600 dark:text-blue-400">
                    API returned {debugInfo.resultsCount || 0} matches
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <>
            {/* Select All/None */}
            <div className="flex items-center justify-between bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={selectedMatches.length === matches.filter(m => m.status === 'pending').length}
                  onChange={(e) => e.target.checked ? handleSelectAll() : handleDeselectAll()}
                  className="w-4 h-4 text-orange-600 bg-gray-100 border-gray-300 rounded focus:ring-orange-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  Select all pending matches
                </span>
              </div>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {matches.length} total matches
              </span>
            </div>

            {matches.map((match) => (
              <div key={match.id} className="mb-6">
                {/* Selection checkbox for bulk actions */}
                {match.status === 'pending' && (
                  <div className="mb-3">
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedMatches.includes(match.id)}
                        onChange={() => handleSelectMatch(match.id)}
                        className="w-4 h-4 text-orange-600 bg-gray-100 border-gray-300 rounded focus:ring-orange-500"
                      />
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        Select for bulk actions
                      </span>
                    </label>
                  </div>
                )}
                
                {/* Collapsible match display */}
                <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg overflow-hidden shadow-sm">
                  {expandedMatches.has(match.id) ? (
                    // Expanded view - full comparison
                    renderRecordComparison(match)
                  ) : (
                    // Collapsed view - summary
                    renderMatchSummary(match)
                  )}
                </div>
              </div>
            ))}
          </>
        )}
      </div>

      {/* Merge Records Modal */}
      {showMergeModal && selectedMatch && (
        <MergeRecordsModal
          match={selectedMatch}
          pipelineFields={pipelineFields}
          onClose={() => {
            setShowMergeModal(false)
            setSelectedMatch(null)
          }}
          onMergeComplete={handleMergeComplete}
        />
      )}
    </div>
  )
}