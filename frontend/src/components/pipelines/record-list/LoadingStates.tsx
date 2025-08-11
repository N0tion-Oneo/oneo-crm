// LoadingStates - Loading and error state components
import React from 'react'
import { RefreshCw, AlertCircle } from 'lucide-react'

export interface LoadingStateProps {
  className?: string
}

export function LoadingState({ className = "h-full" }: LoadingStateProps) {
  return (
    <div className={`${className} flex items-center justify-center`}>
      <div className="text-center">
        <RefreshCw className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
        <p className="text-gray-600 dark:text-gray-400">Loading records...</p>
      </div>
    </div>
  )
}

export interface ErrorStateProps {
  error: string
  onRetry?: () => void
  className?: string
}

export function ErrorState({ error, onRetry, className = "h-full" }: ErrorStateProps) {
  return (
    <div className={`${className} flex items-center justify-center`}>
      <div className="text-center max-w-md">
        <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
          Failed to Load Records
        </h3>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          {error}
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
          >
            <RefreshCw className="w-4 h-4 mr-2 inline" />
            Try Again
          </button>
        )}
      </div>
    </div>
  )
}