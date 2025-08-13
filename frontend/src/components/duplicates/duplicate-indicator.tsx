'use client'

import { useState, useEffect } from 'react'
import { AlertTriangle, ExternalLink } from 'lucide-react'
import { duplicatesApi } from '@/lib/api'
import { DuplicateCountResponse } from '@/types/duplicates'

interface DuplicateIndicatorProps {
  recordId: string
  pipelineId: string
  onNavigateToDuplicates?: () => void
}

export function DuplicateIndicator({ recordId, pipelineId, onNavigateToDuplicates }: DuplicateIndicatorProps) {
  const [duplicateCount, setDuplicateCount] = useState<DuplicateCountResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadDuplicateCount = async () => {
      if (!recordId || !pipelineId) return
      
      try {
        const response = await duplicatesApi.getRecordDuplicateCount(recordId, pipelineId)
        
        // Convert the duplicate matches response to the expected format
        const matches = response.data.results || response.data || []
        const pendingMatches = matches.filter((match: any) => match.status === 'pending')
        
        setDuplicateCount({
          has_duplicates: pendingMatches.length > 0,
          pending_count: pendingMatches.length,
          total_count: matches.length
        })
      } catch (error: any) {
        // Handle 403 permission errors gracefully - just don't show duplicate indicator
        if (error.response?.status === 403) {
          console.warn('No permission to check duplicates for this record')
        } else {
          console.error('Failed to load duplicate count:', error)
        }
        setDuplicateCount(null)
      } finally {
        setLoading(false)
      }
    }

    loadDuplicateCount()
  }, [recordId, pipelineId])

  if (loading || !duplicateCount || !duplicateCount.has_duplicates) {
    return null
  }

  const handleClick = () => {
    if (onNavigateToDuplicates) {
      onNavigateToDuplicates()
    } else {
      // Default navigation to duplicates page
      window.open(`/pipelines/${pipelineId}/duplicates?tab=matches&record=${recordId}`, '_blank')
    }
  }

  return (
    <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-3 mb-4">
      <div className="flex items-start space-x-3">
        <div className="p-1 bg-orange-100 dark:bg-orange-900/40 rounded">
          <AlertTriangle className="w-4 h-4 text-orange-600 dark:text-orange-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-orange-800 dark:text-orange-300">
              Potential Duplicates Found
            </h4>
            <button
              onClick={handleClick}
              className="flex items-center space-x-1 text-xs text-orange-700 dark:text-orange-400 hover:text-orange-900 dark:hover:text-orange-300 transition-colors"
            >
              <span>Manage</span>
              <ExternalLink className="w-3 h-3" />
            </button>
          </div>
          <p className="text-sm text-orange-700 dark:text-orange-400 mt-1">
            {duplicateCount.pending_count === 1 
              ? '1 potential duplicate record' 
              : `${duplicateCount.pending_count} potential duplicate records`
            } found for this record.
          </p>
          <p className="text-xs text-orange-600 dark:text-orange-500 mt-1">
            Click "Manage" to review and resolve duplicates.
          </p>
        </div>
      </div>
    </div>
  )
}