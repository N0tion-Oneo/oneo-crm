'use client'

import { useState, useEffect } from 'react'
import { Link, Users, Settings, ArrowLeftRight, Database } from 'lucide-react'
import { pipelinesApi } from '@/lib/api'

interface RelationshipFieldIndicatorProps {
  fieldConfig: Record<string, any>
  size?: 'sm' | 'md' | 'lg'
  showDetails?: boolean
}

interface Pipeline {
  id: string
  name: string
  description?: string
}

// Simple cache to avoid repeated API calls for the same pipeline
const pipelineNameCache = new Map<string, Pipeline>()
const cacheExpiry = new Map<string, number>()
const CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

export function RelationshipFieldIndicator({ 
  fieldConfig, 
  size = 'md', 
  showDetails = false 
}: RelationshipFieldIndicatorProps) {
  const [targetPipeline, setTargetPipeline] = useState<Pipeline | null>(null)
  const [loading, setLoading] = useState(false)

  // Load target pipeline info
  useEffect(() => {
    const loadTargetPipeline = async () => {
      if (!fieldConfig?.target_pipeline_id || !showDetails) return
      
      const pipelineId = fieldConfig.target_pipeline_id.toString()
      
      // Check cache first
      const cached = pipelineNameCache.get(pipelineId)
      const cacheTime = cacheExpiry.get(pipelineId)
      
      if (cached && cacheTime && Date.now() < cacheTime) {
        setTargetPipeline(cached)
        return
      }
      
      try {
        setLoading(true)
        const response = await pipelinesApi.get(pipelineId)
        const pipeline = {
          id: response.data.id?.toString() || pipelineId,
          name: response.data.name || 'Unknown Pipeline',
          description: response.data.description
        }
        
        // Cache the result
        pipelineNameCache.set(pipelineId, pipeline)
        cacheExpiry.set(pipelineId, Date.now() + CACHE_DURATION)
        
        setTargetPipeline(pipeline)
      } catch (error) {
        console.error('Failed to load target pipeline:', error)
        // Set fallback with just ID
        const fallback = {
          id: pipelineId,
          name: `Pipeline ${pipelineId}`,
        }
        setTargetPipeline(fallback)
        
        // Cache the fallback too (shorter duration)
        pipelineNameCache.set(pipelineId, fallback)
        cacheExpiry.set(pipelineId, Date.now() + (30 * 1000)) // 30 seconds for fallbacks
      } finally {
        setLoading(false)
      }
    }

    loadTargetPipeline()
  }, [fieldConfig?.target_pipeline_id, showDetails])
  if (!fieldConfig) return null

  const sizeClasses = {
    sm: {
      badge: 'px-2 py-0.5 text-xs',
      icon: 'w-3 h-3',
      text: 'text-xs'
    },
    md: {
      badge: 'px-2.5 py-1 text-sm',
      icon: 'w-4 h-4',
      text: 'text-sm'
    },
    lg: {
      badge: 'px-3 py-1.5 text-base',
      icon: 'w-5 h-5',
      text: 'text-base'
    }
  }

  const classes = sizeClasses[size]

  return (
    <div className="space-y-2">
      {/* Main relationship indicator badges */}
      <div className="flex flex-wrap gap-1">
        {/* Multiple relationships indicator */}
        {fieldConfig.allow_multiple && (
          <span className={`inline-flex items-center ${classes.badge} font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-300 rounded-full`}>
            <Link className={`${classes.icon} mr-1`} />
            Multiple
            {fieldConfig.max_relationships && ` (${fieldConfig.max_relationships})`}
          </span>
        )}

        {/* Relationship type selection */}
        {fieldConfig.allow_relationship_type_selection && (
          <span className={`inline-flex items-center ${classes.badge} font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-900/20 dark:text-indigo-300 rounded-full`}>
            <Settings className={`${classes.icon} mr-1`} />
            Type Selection
          </span>
        )}

        {/* Self-reference capability */}
        {fieldConfig.allow_self_reference && (
          <span className={`inline-flex items-center ${classes.badge} font-medium bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300 rounded-full`}>
            <Users className={`${classes.icon} mr-1`} />
            Self-Reference
          </span>
        )}

        {/* Bidirectional relationships */}
        {fieldConfig.create_reverse_relationships !== false && (
          <span className={`inline-flex items-center ${classes.badge} font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300 rounded-full`}>
            <ArrowLeftRight className={`${classes.icon} mr-1`} />
            Bidirectional
          </span>
        )}
      </div>

      {/* Detailed configuration (optional) */}
      {showDetails && (
        <div className="space-y-1">
          {fieldConfig.target_pipeline_id && (
            <div className={`${classes.text} text-gray-600 dark:text-gray-400 flex items-center gap-2`}>
              <Database className="w-3 h-3" />
              <span className="font-medium">Target:</span>
              {loading ? (
                <span className="text-xs">Loading...</span>
              ) : targetPipeline ? (
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {targetPipeline.name}
                </span>
              ) : (
                <span className="font-medium">Pipeline {fieldConfig.target_pipeline_id}</span>
              )}
            </div>
          )}
          {fieldConfig.display_field && (
            <div className={`${classes.text} text-gray-600 dark:text-gray-400`}>
              <span className="font-medium">Display:</span> {fieldConfig.display_field}
            </div>
          )}
          {fieldConfig.default_relationship_type && (
            <div className={`${classes.text} text-gray-600 dark:text-gray-400`}>
              <span className="font-medium">Type:</span> {fieldConfig.default_relationship_type.replace('_', ' ')}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// Helper function to check if a field has enhanced relationship features
export function hasEnhancedRelationshipFeatures(fieldConfig: Record<string, any>): boolean {
  if (!fieldConfig) return false
  
  return !!(
    fieldConfig.allow_multiple ||
    fieldConfig.allow_relationship_type_selection ||
    fieldConfig.allow_self_reference ||
    fieldConfig.create_reverse_relationships !== false ||
    fieldConfig.default_relationship_type ||
    fieldConfig.max_relationships
  )
}

// Helper function to get relationship summary text
export function getRelationshipSummary(fieldConfig: Record<string, any>): string {
  if (!fieldConfig) return 'Basic relationship'
  
  const features = []
  if (fieldConfig.allow_multiple) features.push('multiple')
  if (fieldConfig.allow_relationship_type_selection) features.push('typed')
  if (fieldConfig.allow_self_reference) features.push('self-ref')
  if (fieldConfig.create_reverse_relationships !== false) features.push('bidirectional')
  
  return features.length > 0 ? `Enhanced (${features.join(', ')})` : 'Basic relationship'
}