'use client'

import React from 'react'
import { AlertTriangle } from 'lucide-react'

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
  errorInfo: any
}

interface ErrorBoundaryProps {
  children: React.ReactNode
  fallback?: React.ComponentType<{ error: Error | null; errorInfo: any; onRetry: () => void }>
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('[ErrorBoundary] Caught error:', error, errorInfo)
    this.setState({
      error,
      errorInfo
    })
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      const FallbackComponent = this.props.fallback || DefaultErrorFallback
      return (
        <FallbackComponent
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          onRetry={this.handleRetry}
        />
      )
    }

    return this.props.children
  }
}

interface DefaultErrorFallbackProps {
  error: Error | null
  errorInfo: any
  onRetry: () => void
}

function DefaultErrorFallback({ error, errorInfo, onRetry }: DefaultErrorFallbackProps) {
  return (
    <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
      <div className="flex items-start">
        <AlertTriangle className="h-5 w-5 text-red-400 mt-0.5" />
        <div className="ml-3">
          <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
            Field Configuration Error
          </h3>
          <div className="mt-2 text-sm text-red-700 dark:text-red-300">
            <p>An error occurred while rendering the field configuration.</p>
            {error && (
              <details className="mt-2">
                <summary className="cursor-pointer text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200">
                  Error Details
                </summary>
                <pre className="mt-1 text-xs bg-red-100 dark:bg-red-900/40 p-2 rounded overflow-auto">
                  {error.toString()}
                  {errorInfo?.componentStack && (
                    <>
                      {'\n\nComponent Stack:'}
                      {errorInfo.componentStack}
                    </>
                  )}
                </pre>
              </details>
            )}
          </div>
          <div className="mt-3">
            <button
              onClick={onRetry}
              className="text-sm bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-200 px-3 py-1 rounded hover:bg-red-200 dark:hover:bg-red-900/60 transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}