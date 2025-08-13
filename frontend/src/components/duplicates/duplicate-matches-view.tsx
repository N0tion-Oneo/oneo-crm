'use client'

import { useState, useEffect } from 'react'
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
  AlertCircle
} from 'lucide-react'
import { duplicatesApi } from '@/lib/api'

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

  // Load duplicate matches
  useEffect(() => {
    if (pipelineId) {
      loadDuplicateMatches()
    }
  }, [pipelineId, filterStatus])

  const loadDuplicateMatches = async () => {
    try {
      setLoading(true)
      const response = await duplicatesApi.getDuplicateMatches(pipelineId)
      
      // Transform and filter matches
      const transformedMatches: DuplicateMatch[] = (response.data.results || [])
        .filter((match: any) => {
          // Filter by pipeline (if we had pipeline filtering in API)
          if (filterStatus !== 'all') {
            return match.status === filterStatus
          }
          return true
        })
        .map((match: any) => ({
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
        }))
      
      setMatches(transformedMatches)
    } catch (error: any) {
      console.error('Failed to load duplicate matches:', error)
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
    }
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

  const renderRecordPreview = (record: any, title: string) => {
    const displayFields = Object.entries(record.data || {}).slice(0, 3)
    
    return (
      <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
        <h5 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
          {title} (ID: {record.id})
        </h5>
        <div className="space-y-1">
          {displayFields.map(([key, value]) => (
            <div key={key} className="flex items-center text-xs">
              <span className="text-gray-500 dark:text-gray-400 w-16 truncate">
                {key}:
              </span>
              <span className="text-gray-900 dark:text-white ml-2 truncate">
                {String(value)}
              </span>
            </div>
          ))}
        </div>
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
        {matches.length === 0 ? (
          <div className="text-center py-12">
            <AlertTriangle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              No duplicate matches found
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              {filterStatus === 'all' 
                ? 'Your duplicate detection rules haven\'t found any matches yet.'
                : `No matches with status "${filterStatus}" found.`
              }
            </p>
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
              <div
                key={match.id}
                className="bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg overflow-hidden"
              >
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center space-x-3">
                      {match.status === 'pending' && (
                        <input
                          type="checkbox"
                          checked={selectedMatches.includes(match.id)}
                          onChange={() => handleSelectMatch(match.id)}
                          className="w-4 h-4 text-orange-600 bg-gray-100 border-gray-300 rounded focus:ring-orange-500"
                        />
                      )}
                      <div>
                        <div className="flex items-center space-x-2 mb-1">
                          {getStatusBadge(match.status)}
                          <span className={`text-sm font-semibold ${getConfidenceColor(match.confidence_score)}`}>
                            {Math.round(match.confidence_score * 100)}% confidence
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          Detected by rule: <span className="font-medium">{match.rule.name}</span>
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                          Found on {new Date(match.detected_at).toLocaleDateString()}
                          {match.reviewed_at && (
                            <> • Reviewed on {new Date(match.reviewed_at).toLocaleDateString()}</>
                          )}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-1">
                      <button className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600">
                        <ExternalLink className="w-4 h-4" />
                      </button>
                      <div className="relative">
                        <button className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600">
                          <MoreVertical className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Record Comparison */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    {renderRecordPreview(match.record1, 'Record A')}
                    <div className="flex items-center justify-center">
                      <ArrowRight className="w-6 h-6 text-gray-400" />
                    </div>
                    {renderRecordPreview(match.record2, 'Record B')}
                  </div>

                  {/* Matched Fields */}
                  {match.matched_fields.length > 0 && (
                    <div className="mb-4">
                      <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Matched Fields:
                      </h5>
                      <div className="flex flex-wrap gap-2">
                        {match.matched_fields.map((field, index) => (
                          <span
                            key={index}
                            className="px-2 py-1 bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400 rounded-md text-xs font-medium"
                          >
                            {field}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Resolution Notes */}
                  {match.resolution_notes && (
                    <div className="bg-gray-50 dark:bg-gray-600 rounded-lg p-3">
                      <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Resolution Notes:
                      </h5>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {match.resolution_notes}
                      </p>
                      {match.reviewed_by && (
                        <p className="text-xs text-gray-500 dark:text-gray-500 mt-2">
                          Resolved by {match.reviewed_by.name}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Individual Actions for pending matches */}
                  {match.status === 'pending' && (
                    <div className="flex items-center space-x-2 mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
                      <button
                        onClick={() => handleBulkResolve('merge')}
                        className="px-3 py-1 bg-green-500 text-white rounded-md hover:bg-green-600 text-sm flex items-center space-x-1"
                      >
                        <GitMerge className="w-3 h-3" />
                        <span>Merge Records</span>
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
                        <span>Mark as False Positive</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  )
}