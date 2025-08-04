import React from 'react'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'

export const RecordDataFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, className } = props
    
    const dataType = getFieldConfig(field, 'data_type', 'timestamp')
    const timestampType = getFieldConfig(field, 'timestamp_type')
    const userType = getFieldConfig(field, 'user_type')
    const countType = getFieldConfig(field, 'count_type')
    const durationType = getFieldConfig(field, 'duration_type')
    const statusType = getFieldConfig(field, 'status_type')
    const format = getFieldConfig(field, 'format', 'relative')
    const includeTime = getFieldConfig(field, 'include_time', false)
    
    // Get the display label for the data type
    const getDataTypeLabel = () => {
      switch (dataType) {
        case 'timestamp':
          return timestampType ? timestampType.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) : 'Timestamp'
        case 'user':
          return userType ? userType.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) : 'User'
        case 'count':
          return countType ? countType.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) : 'Count'
        case 'duration':
          return durationType ? durationType.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) : 'Duration'
        case 'status':
          return statusType ? statusType.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) : 'Status'
        default:
          return 'Record Data'
      }
    }

    // Format the display value
    const formatDisplayValue = () => {
      if (value === null || value === undefined) {
        return 'Not available'
      }
      
      switch (dataType) {
        case 'timestamp':
          if (typeof value === 'string' || typeof value === 'number') {
            const date = new Date(value)
            if (format === 'relative') {
              return getRelativeTime(date)
            } else {
              return includeTime 
                ? date.toLocaleString()
                : date.toLocaleDateString()
            }
          }
          break
          
        case 'user':
          if (typeof value === 'object' && value.name) {
            return value.name
          } else if (typeof value === 'string') {
            return value
          }
          break
          
        case 'count':
          if (typeof value === 'number') {
            return value.toLocaleString()
          }
          break
          
        case 'duration':
          if (typeof value === 'number') {
            return formatDuration(value)
          }
          break
          
        case 'status':
          if (typeof value === 'string') {
            return value.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())
          }
          break
      }
      
      return String(value)
    }

    // Helper function for relative time
    const getRelativeTime = (date: Date) => {
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffSecs = Math.floor(diffMs / 1000)
      const diffMins = Math.floor(diffSecs / 60)
      const diffHours = Math.floor(diffMins / 60)
      const diffDays = Math.floor(diffHours / 24)
      
      if (diffSecs < 60) return 'Just now'
      if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`
      if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`
      if (diffDays < 30) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`
      
      return date.toLocaleDateString()
    }

    // Helper function for duration formatting
    const formatDuration = (seconds: number) => {
      const hours = Math.floor(seconds / 3600)
      const minutes = Math.floor((seconds % 3600) / 60)
      const secs = seconds % 60
      
      if (hours > 0) {
        return `${hours}h ${minutes}m`
      } else if (minutes > 0) {
        return `${minutes}m ${secs}s`
      } else {
        return `${secs}s`
      }
    }

    return (
      <div className={className}>
        <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center text-gray-600 dark:text-gray-400 text-sm">
              <span className="w-2 h-2 bg-gray-400 rounded-full mr-2"></span>
              <span className="font-medium">{getDataTypeLabel()}</span>
            </div>
            <span className="text-xs text-gray-500 dark:text-gray-500 bg-gray-200 dark:bg-gray-700 px-2 py-0.5 rounded">
              System Field
            </span>
          </div>
          <div className="text-gray-900 dark:text-gray-100 font-medium">
            {formatDisplayValue()}
          </div>
          {dataType === 'timestamp' && format === 'relative' && value && (
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Absolute: {new Date(value).toLocaleString()}
            </div>
          )}
        </div>
      </div>
    )
  },

  formatValue: (value: any, field: Field, context?: string) => {
    if (value === null || value === undefined) {
      if (context === 'table') {
        return <span className="text-gray-400 italic">—</span>
      }
      return ''
    }
    
    const dataType = getFieldConfig(field, 'data_type', 'timestamp')
    const format = getFieldConfig(field, 'format', 'relative')
    const includeTime = getFieldConfig(field, 'include_time', false)
    
    const getRelativeTime = (date: Date) => {
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffSecs = Math.floor(diffMs / 1000)
      const diffMins = Math.floor(diffSecs / 60)
      const diffHours = Math.floor(diffMins / 60)
      const diffDays = Math.floor(diffHours / 24)
      
      if (diffSecs < 60) return 'Just now'
      if (diffMins < 60) return `${diffMins}m ago`
      if (diffHours < 24) return `${diffHours}h ago`
      if (diffDays < 30) return `${diffDays}d ago`
      
      return date.toLocaleDateString()
    }

    const formatDuration = (seconds: number) => {
      const hours = Math.floor(seconds / 3600)
      const minutes = Math.floor((seconds % 3600) / 60)
      
      if (hours > 0) {
        return `${hours}h ${minutes}m`
      } else if (minutes > 0) {
        return `${minutes}m`
      } else {
        return `${seconds}s`
      }
    }

    switch (dataType) {
      case 'timestamp':
        if (typeof value === 'string' || typeof value === 'number') {
          const date = new Date(value)
          if (context === 'table') {
            return (
              <span className="text-gray-600 dark:text-gray-400 text-sm">
                {format === 'relative' ? getRelativeTime(date) : date.toLocaleDateString()}
              </span>
            )
          }
          return format === 'relative' ? getRelativeTime(date) : 
                 includeTime ? date.toLocaleString() : date.toLocaleDateString()
        }
        break
        
      case 'user':
        if (typeof value === 'object' && value.name) {
          if (context === 'table') {
            return (
              <span className="text-blue-600 dark:text-blue-400 font-medium">
                {value.name}
              </span>
            )
          }
          return value.name
        } else if (typeof value === 'string') {
          if (context === 'table') {
            return (
              <span className="text-blue-600 dark:text-blue-400 font-medium">
                {value}
              </span>
            )
          }
          return value
        }
        break
        
      case 'count':
        if (typeof value === 'number') {
          if (context === 'table') {
            return (
              <span className="text-green-600 dark:text-green-400 font-mono font-medium">
                {value.toLocaleString()}
              </span>
            )
          }
          return value.toLocaleString()
        }
        break
        
      case 'duration':
        if (typeof value === 'number') {
          if (context === 'table') {
            return (
              <span className="text-orange-600 dark:text-orange-400 font-mono">
                {formatDuration(value)}
              </span>
            )
          }
          return formatDuration(value)
        }
        break
        
      case 'status':
        if (typeof value === 'string') {
          const displayValue = value.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())
          if (context === 'table') {
            const statusColors = {
              active: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
              inactive: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
              pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
              error: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
            }
            const colorClass = statusColors[value.toLowerCase() as keyof typeof statusColors] || statusColors.inactive
            
            return (
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
                {displayValue}
              </span>
            )
          }
          return displayValue
        }
        break
    }
    
    return String(value)
  },

  validate: (value: any, field: Field): ValidationResult => {
    // Record data fields are system-generated and don't need validation
    // They're read-only and populated by the system
    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    // Record data fields don't have user-defined defaults
    // They're populated by the system based on record metadata
    return null
  },

  isEmpty: (value: any) => {
    // Record data fields are never considered "empty" since they're system fields
    // Even if they have no value, they represent system metadata
    return false
  }
}