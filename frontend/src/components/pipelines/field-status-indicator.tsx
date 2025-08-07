'use client'

import React from 'react'
import { CheckCircle, Archive, Clock, AlertTriangle, Shield } from 'lucide-react'

interface FieldStatusIndicatorProps {
  status: 'active' | 'soft_deleted' | 'scheduled_for_hard_delete'
  deletionInfo?: {
    deleted_at?: string
    deleted_by?: string
    days_remaining?: number
    hard_delete_date?: string
    reason?: string
  }
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  className?: string
}

export function FieldStatusIndicator({ 
  status, 
  deletionInfo, 
  size = 'md', 
  showLabel = true,
  className = '' 
}: FieldStatusIndicatorProps) {
  const getStatusConfig = () => {
    switch (status) {
      case 'active':
        return {
          icon: CheckCircle,
          color: 'text-green-500',
          bgColor: 'bg-green-50 border-green-200',
          textColor: 'text-green-700',
          label: 'Active',
          description: 'Field is active and in use'
        }
      case 'soft_deleted':
        return {
          icon: Archive,
          color: 'text-orange-500',
          bgColor: 'bg-orange-50 border-orange-200',
          textColor: 'text-orange-700',
          label: 'Soft Deleted',
          description: 'Field is hidden but data is preserved'
        }
      case 'scheduled_for_hard_delete':
        return {
          icon: Clock,
          color: 'text-red-500',
          bgColor: 'bg-red-50 border-red-200',
          textColor: 'text-red-700',
          label: 'Scheduled for Deletion',
          description: 'Field will be permanently deleted'
        }
      default:
        return {
          icon: AlertTriangle,
          color: 'text-gray-400',
          bgColor: 'bg-gray-50 border-gray-200',
          textColor: 'text-gray-600',
          label: 'Unknown',
          description: 'Status unknown'
        }
    }
  }

  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return {
          icon: 'w-3 h-3',
          text: 'text-xs',
          padding: 'px-2 py-0.5',
          spacing: 'space-x-1'
        }
      case 'lg':
        return {
          icon: 'w-6 h-6',
          text: 'text-sm',
          padding: 'px-3 py-1.5',
          spacing: 'space-x-2'
        }
      default: // md
        return {
          icon: 'w-4 h-4',
          text: 'text-xs',
          padding: 'px-2.5 py-0.5',
          spacing: 'space-x-1.5'
        }
    }
  }

  const config = getStatusConfig()
  const sizeClasses = getSizeClasses()
  const Icon = config.icon

  if (!showLabel) {
    return (
      <div className={`inline-flex items-center ${className}`} title={config.description}>
        <Icon className={`${config.color} ${sizeClasses.icon}`} />
      </div>
    )
  }

  return (
    <div className={`inline-flex items-center ${sizeClasses.spacing} ${className}`}>
      <span className={`inline-flex items-center ${sizeClasses.spacing} ${sizeClasses.padding} rounded-full ${sizeClasses.text} font-medium border ${config.bgColor} ${config.textColor}`}>
        <Icon className={`${config.color} ${sizeClasses.icon}`} />
        <span>{config.label}</span>
        
        {/* Additional info for scheduled deletion */}
        {status === 'scheduled_for_hard_delete' && deletionInfo?.days_remaining !== undefined && (
          <span className="ml-1 text-red-600 font-semibold">
            ({deletionInfo.days_remaining}d)
          </span>
        )}
      </span>
    </div>
  )
}

interface FieldStatusTooltipProps {
  status: 'active' | 'soft_deleted' | 'scheduled_for_hard_delete'
  deletionInfo?: {
    deleted_at?: string
    deleted_by?: string
    days_remaining?: number
    hard_delete_date?: string
    reason?: string
  }
  fieldName: string
}

export function FieldStatusTooltip({ status, deletionInfo, fieldName }: FieldStatusTooltipProps) {
  const config = getStatusConfig(status)
  
  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg p-4 w-80">
      <div className="flex items-center space-x-2 mb-3">
        <FieldStatusIndicator status={status} showLabel={false} />
        <div>
          <div className="font-semibold text-gray-900 dark:text-white">{fieldName}</div>
          <div className={`text-sm ${config.textColor}`}>{config.label}</div>
        </div>
      </div>

      <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
        <p>{config.description}</p>
        
        {deletionInfo?.deleted_at && (
          <div>
            <span className="font-medium">Deleted:</span> {new Date(deletionInfo.deleted_at).toLocaleString()}
          </div>
        )}
        
        {deletionInfo?.deleted_by && (
          <div>
            <span className="font-medium">By:</span> {deletionInfo.deleted_by}
          </div>
        )}
        
        {deletionInfo?.hard_delete_date && (
          <div className="text-red-600 dark:text-red-400">
            <span className="font-medium">Hard Delete:</span> {new Date(deletionInfo.hard_delete_date).toLocaleString()}
            {deletionInfo.days_remaining !== undefined && (
              <span className="ml-1">({deletionInfo.days_remaining} days remaining)</span>
            )}
          </div>
        )}
        
        {deletionInfo?.reason && (
          <div>
            <span className="font-medium">Reason:</span>
            <div className="mt-1 text-xs bg-gray-50 dark:bg-gray-700 p-2 rounded border">
              {deletionInfo.reason}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Helper function for status config (extracted for reuse)
function getStatusConfig(status: 'active' | 'soft_deleted' | 'scheduled_for_hard_delete') {
  switch (status) {
    case 'active':
      return {
        color: 'text-green-500',
        bgColor: 'bg-green-50 border-green-200',
        textColor: 'text-green-700',
        label: 'Active',
        description: 'Field is active and in use'
      }
    case 'soft_deleted':
      return {
        color: 'text-orange-500',
        bgColor: 'bg-orange-50 border-orange-200', 
        textColor: 'text-orange-700',
        label: 'Soft Deleted',
        description: 'Field is hidden but data is preserved'
      }
    case 'scheduled_for_hard_delete':
      return {
        color: 'text-red-500',
        bgColor: 'bg-red-50 border-red-200',
        textColor: 'text-red-700',
        label: 'Scheduled for Deletion',
        description: 'Field will be permanently deleted'
      }
    default:
      return {
        color: 'text-gray-400',
        bgColor: 'bg-gray-50 border-gray-200',
        textColor: 'text-gray-600',
        label: 'Unknown',
        description: 'Status unknown'
      }
  }
}