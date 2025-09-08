// RecordActions - Bulk actions toolbar
import React from 'react'
import { Trash2, Download, Upload, RefreshCw, X } from 'lucide-react'

export interface RecordActionsProps {
  selectedCount: number
  onBulkDelete?: () => void
  onBulkUpdate?: () => void
  onExport: (format: 'csv' | 'json' | 'excel') => void
  onRefresh: () => void
  onClearSelection: () => void
  className?: string
}

export function RecordActions({
  selectedCount,
  onBulkDelete,
  onBulkUpdate,
  onExport,
  onRefresh,
  onClearSelection,
  className = ""
}: RecordActionsProps) {
  if (selectedCount === 0) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <button
          onClick={onRefresh}
          className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          title="Refresh records"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
        
        <div className="flex items-center space-x-1">
          <button
            onClick={() => onExport('csv')}
            className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
            title="Export as CSV"
          >
            CSV
          </button>
          <button
            onClick={() => onExport('excel')}
            className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
            title="Export as Excel"
          >
            Excel
          </button>
          <button
            onClick={() => onExport('json')}
            className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
            title="Export as JSON"
          >
            JSON
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={`flex items-center space-x-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 rounded-md ${className}`}>
      <span className="text-sm text-blue-700 dark:text-blue-300">
        {selectedCount} selected
      </span>
      
      <div className="flex items-center space-x-1">
        {onBulkUpdate && (
          <button
            onClick={onBulkUpdate}
            className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
            title="Bulk update selected records"
          >
            <Upload className="w-3 h-3 mr-1 inline" />
            Update
          </button>
        )}
        
        {onBulkDelete && (
          <button
            onClick={onBulkDelete}
            className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
            title="Delete selected records"
          >
            <Trash2 className="w-3 h-3 mr-1 inline" />
            Delete
          </button>
        )}
        
        <button
          onClick={onClearSelection}
          className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          title="Clear selection"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
    </div>
  )
}