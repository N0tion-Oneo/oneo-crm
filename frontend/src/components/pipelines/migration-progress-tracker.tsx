'use client'

import React, { useState, useEffect, useRef } from 'react'
import { 
  Clock,
  CheckCircle,
  AlertCircle,
  RotateCcw,
  Database,
  Zap,
  TrendingUp,
  X,
  Pause,
  Play,
  RefreshCw
} from 'lucide-react'

interface ProgressStep {
  id: string
  name: string
  description: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped'
  progress?: number
  error?: string
  started_at?: string
  completed_at?: string
  records_processed?: number
  total_records?: number
}

interface MigrationTask {
  task_id: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled'
  field_name: string
  field_type_change: string
  started_at: string
  completed_at?: string
  estimated_duration?: string
  actual_duration?: string
  steps: ProgressStep[]
  statistics: {
    total_records: number
    records_processed: number
    records_migrated: number
    records_failed: number
    success_rate: number
    performance_metrics: {
      records_per_second: number
      estimated_completion: string
    }
  }
  error?: string
}

interface MigrationProgressTrackerProps {
  isOpen: boolean
  onClose: () => void
  taskId: string
  fieldName: string
  onMigrationComplete?: (success: boolean, result: any) => void
}

export function MigrationProgressTracker({
  isOpen,
  onClose,
  taskId,
  fieldName,
  onMigrationComplete
}: MigrationProgressTrackerProps) {
  const [migrationTask, setMigrationTask] = useState<MigrationTask | null>(null)
  const [isPolling, setIsPolling] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Mock API call - replace with actual API implementation
  const fetchMigrationStatus = async (taskId: string): Promise<MigrationTask> => {
    // Simulated API response for demonstration
    const mockTask: MigrationTask = {
      task_id: taskId,
      status: 'in_progress',
      field_name: fieldName,
      field_type_change: 'text → number',
      started_at: new Date().toISOString(),
      estimated_duration: '2 minutes',
      steps: [
        {
          id: 'validation',
          name: 'Pre-migration Validation',
          description: 'Validating data compatibility and field constraints',
          status: 'completed',
          progress: 100,
          started_at: new Date(Date.now() - 30000).toISOString(),
          completed_at: new Date(Date.now() - 25000).toISOString()
        },
        {
          id: 'backup',
          name: 'Data Backup',
          description: 'Creating backup of existing field data',
          status: 'completed', 
          progress: 100,
          started_at: new Date(Date.now() - 25000).toISOString(),
          completed_at: new Date(Date.now() - 20000).toISOString()
        },
        {
          id: 'transformation',
          name: 'Data Transformation',
          description: 'Converting field values to new format',
          status: 'in_progress',
          progress: 65,
          records_processed: 650,
          total_records: 1000,
          started_at: new Date(Date.now() - 20000).toISOString()
        },
        {
          id: 'validation_post',
          name: 'Post-migration Validation',
          description: 'Verifying data integrity after transformation',
          status: 'pending',
          progress: 0
        },
        {
          id: 'cleanup',
          name: 'Cleanup & Finalization',
          description: 'Cleaning up temporary data and finalizing migration',
          status: 'pending',
          progress: 0
        }
      ],
      statistics: {
        total_records: 1000,
        records_processed: 650,
        records_migrated: 640,
        records_failed: 10,
        success_rate: 98.46,
        performance_metrics: {
          records_per_second: 32.5,
          estimated_completion: '45 seconds'
        }
      }
    }

    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 500))
    return mockTask
  }

  // Polling effect
  useEffect(() => {
    if (!isOpen || !taskId || !isPolling) return

    const pollStatus = async () => {
      try {
        const task = await fetchMigrationStatus(taskId)
        setMigrationTask(task)
        
        // Stop polling if task is completed or failed
        if (task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') {
          setIsPolling(false)
          if (onMigrationComplete) {
            onMigrationComplete(task.status === 'completed', task)
          }
        }
      } catch (err: any) {
        console.error('Error fetching migration status:', err)
        setError(err.message || 'Failed to fetch migration status')
      }
    }

    // Initial fetch
    pollStatus()

    // Set up polling interval
    if (autoRefresh) {
      pollingIntervalRef.current = setInterval(pollStatus, 2000) // Poll every 2 seconds
    }

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
      }
    }
  }, [isOpen, taskId, isPolling, autoRefresh])

  const handleTogglePolling = () => {
    setIsPolling(!isPolling)
    setAutoRefresh(!autoRefresh)
  }

  const handleRefresh = async () => {
    if (!taskId) return
    
    try {
      const task = await fetchMigrationStatus(taskId)
      setMigrationTask(task)
    } catch (err: any) {
      setError(err.message || 'Failed to refresh status')
    }
  }

  const getStepIcon = (status: string, progress?: number) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'in_progress':
        return <div className="w-5 h-5 relative">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-red-500" />
      case 'skipped':
        return <RotateCcw className="w-5 h-5 text-yellow-500" />
      default:
        return <div className="w-5 h-5 border-2 border-gray-300 rounded-full" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600'
      case 'in_progress':
        return 'text-blue-600'
      case 'failed':
        return 'text-red-600'
      case 'cancelled':
        return 'text-gray-600'
      default:
        return 'text-gray-400'
    }
  }

  const formatDuration = (startTime: string, endTime?: string) => {
    const start = new Date(startTime)
    const end = endTime ? new Date(endTime) : new Date()
    const duration = Math.floor((end.getTime() - start.getTime()) / 1000)
    
    if (duration < 60) return `${duration}s`
    if (duration < 3600) return `${Math.floor(duration / 60)}m ${duration % 60}s`
    return `${Math.floor(duration / 3600)}h ${Math.floor((duration % 3600) / 60)}m`
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Migration Progress
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {migrationTask?.field_name || fieldName} - {migrationTask?.field_type_change || 'Field Migration'}
              </p>
            </div>
            
            {migrationTask && (
              <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                migrationTask.status === 'completed' ? 'bg-green-100 text-green-800' :
                migrationTask.status === 'failed' ? 'bg-red-100 text-red-800' :
                migrationTask.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {migrationTask.status.replace('_', ' ').toUpperCase()}
              </div>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={handleRefresh}
              disabled={autoRefresh}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 disabled:opacity-50"
              title="Refresh status"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
            <button
              onClick={handleTogglePolling}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              title={autoRefresh ? "Pause auto-refresh" : "Resume auto-refresh"}
            >
              {autoRefresh ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        <div className="p-6">
          {error && (
            <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <div className="flex items-center">
                <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
                <span className="text-red-700 dark:text-red-300">{error}</span>
              </div>
            </div>
          )}

          {migrationTask && (
            <div className="space-y-6">
              {/* Overall Progress */}
              <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-gray-900 dark:text-white">Overall Progress</h3>
                  <div className="text-sm text-gray-500">
                    {migrationTask.started_at && (
                      <div className="flex items-center">
                        <Clock className="w-4 h-4 mr-1" />
                        {formatDuration(migrationTask.started_at, migrationTask.completed_at)}
                        {migrationTask.estimated_duration && migrationTask.status === 'in_progress' && (
                          <span className="ml-2 text-gray-400">/ ~{migrationTask.estimated_duration}</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
                  <div className="flex items-center">
                    <Database className="w-4 h-4 mr-2 text-blue-500" />
                    <div>
                      <div className="text-gray-500">Records</div>
                      <div className="font-medium">
                        {migrationTask.statistics.records_processed} / {migrationTask.statistics.total_records}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center">
                    <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
                    <div>
                      <div className="text-gray-500">Success Rate</div>
                      <div className="font-medium">{migrationTask.statistics.success_rate.toFixed(1)}%</div>
                    </div>
                  </div>
                  
                  <div className="flex items-center">
                    <Zap className="w-4 h-4 mr-2 text-yellow-500" />
                    <div>
                      <div className="text-gray-500">Speed</div>
                      <div className="font-medium">
                        {migrationTask.statistics.performance_metrics.records_per_second.toFixed(1)} rec/s
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center">
                    <TrendingUp className="w-4 h-4 mr-2 text-purple-500" />
                    <div>
                      <div className="text-gray-500">ETA</div>
                      <div className="font-medium">
                        {migrationTask.statistics.performance_metrics.estimated_completion}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Overall Progress Bar */}
                <div className="mt-4">
                  <div className="flex justify-between text-sm mb-1">
                    <span>Migration Progress</span>
                    <span>
                      {Math.round((migrationTask.statistics.records_processed / migrationTask.statistics.total_records) * 100)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                      style={{
                        width: `${(migrationTask.statistics.records_processed / migrationTask.statistics.total_records) * 100}%`
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* Step-by-step Progress */}
              <div className="space-y-4">
                <h3 className="font-medium text-gray-900 dark:text-white">Migration Steps</h3>
                
                {migrationTask.steps.map((step, index) => (
                  <div key={step.id} className="flex items-start space-x-4 p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                    <div className="flex-shrink-0 mt-0.5">
                      {getStepIcon(step.status, step.progress)}
                    </div>
                    
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium text-gray-900 dark:text-white">{step.name}</h4>
                        <div className="flex items-center space-x-2 text-sm text-gray-500">
                          {step.status === 'in_progress' && step.records_processed && step.total_records && (
                            <span>
                              {step.records_processed} / {step.total_records}
                            </span>
                          )}
                          <span className={getStatusColor(step.status)}>
                            {step.status.replace('_', ' ')}
                          </span>
                        </div>
                      </div>
                      
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        {step.description}
                      </p>
                      
                      {step.error && (
                        <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-sm text-red-700 dark:text-red-300">
                          {step.error}
                        </div>
                      )}
                      
                      {step.status === 'in_progress' && step.progress !== undefined && (
                        <div className="mt-2">
                          <div className="flex justify-between text-xs mb-1">
                            <span>Progress</span>
                            <span>{step.progress}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-1">
                            <div 
                              className="bg-blue-600 h-1 rounded-full transition-all duration-500"
                              style={{ width: `${step.progress}%` }}
                            />
                          </div>
                        </div>
                      )}
                      
                      {(step.started_at || step.completed_at) && (
                        <div className="mt-2 flex items-center text-xs text-gray-500">
                          <Clock className="w-3 h-3 mr-1" />
                          {step.started_at && (
                            <span>
                              {step.completed_at 
                                ? `Completed in ${formatDuration(step.started_at, step.completed_at)}`
                                : `Running for ${formatDuration(step.started_at)}`
                              }
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Action buttons */}
              <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                {migrationTask.status === 'in_progress' && (
                  <button
                    className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-red-600 border border-gray-300 rounded-lg hover:border-red-300"
                  >
                    Cancel Migration
                  </button>
                )}
                
                {(migrationTask.status === 'completed' || migrationTask.status === 'failed') && (
                  <button
                    onClick={onClose}
                    className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark"
                  >
                    {migrationTask.status === 'completed' ? 'Done' : 'Close'}
                  </button>
                )}
                
                {migrationTask.status === 'in_progress' && (
                  <button
                    onClick={() => setIsPolling(false)}
                    className="px-6 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
                  >
                    Run in Background
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}