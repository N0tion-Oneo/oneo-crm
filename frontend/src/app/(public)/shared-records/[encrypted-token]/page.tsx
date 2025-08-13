'use client'

import React, { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { DynamicFormRenderer } from '@/components/forms/DynamicFormRenderer'
import { AccessorInfoGate } from '@/components/shared-records/AccessorInfoGate'
import { Shield, Clock, User, Calendar, AlertTriangle, CheckCircle, Edit, Lock } from 'lucide-react'

interface SharedRecordData {
  record: {
    id: string
    pipeline: {
      id: string
      name: string
      slug: string
    }
    data: Record<string, any>
  }
  form_schema: {
    fields: Array<{
      name: string
      label: string
      field_type: string
      slug?: string
      current_value?: any
      config?: Record<string, any>
    }>
  }
  expires_at: number
  shared_by: string
  expires_datetime: string
  time_remaining_seconds: number
  working_days_remaining: number
  access_mode: 'readonly' | 'editable'
  access_info: {
    created_at: number
    access_count: number
    is_expired: boolean
  }
}

export default function SharedRecordPage() {
  const params = useParams()
  const encryptedToken = params['encrypted-token'] as string
  
  const [sharedData, setSharedData] = useState<SharedRecordData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [accessorInfo, setAccessorInfo] = useState<{ name: string; email: string } | null>(null)
  const [gateLoading, setGateLoading] = useState(false)

  const fetchSharedRecord = async (name?: string, email?: string) => {
    if (!encryptedToken) return
    
    try {
      setLoading(true)
      
      // Use direct fetch to the API endpoint
      const baseUrl = window.location.hostname.includes('localhost') 
        ? `http://${window.location.hostname}:8000`
        : `${window.location.protocol}//${window.location.hostname}`
      
      // Build URL with query parameters if accessor info is provided
      let url = `${baseUrl}/api/v1/shared-records/${encryptedToken}/`
      if (name && email) {
        const params = new URLSearchParams({
          accessor_name: name,
          accessor_email: email
        })
        url += `?${params.toString()}`
      }

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      })

      if (!response.ok) {
        if (response.status === 400) {
          const errorData = await response.json().catch(() => ({}))
          if (errorData.required_fields) {
            // This is expected when accessor info is required
            return
          }
          setError(errorData.error || 'Invalid request. Please try again.')
        } else if (response.status === 403 || response.status === 404) {
          const errorData = await response.json().catch(() => ({}))
          setError(errorData.error || 'This share link is invalid or has expired.')
        } else {
          setError('Failed to load shared record. Please try again.')
        }
        return
      }

      const data = await response.json()
      setSharedData(data)
      
    } catch (error: any) {
      console.error('Failed to fetch shared record:', error)
      setError('Failed to load shared record. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSharedRecord()
  }, [encryptedToken])

  const handleAccessorSubmit = async (name: string, email: string) => {
    try {
      setGateLoading(true)
      setError(null)
      
      await fetchSharedRecord(name, email)
      
      // Store accessor info for display
      setAccessorInfo({ name, email })
    } catch (error: any) {
      console.error('Failed to submit accessor info:', error)
      setError('Failed to access shared record. Please try again.')
    } finally {
      setGateLoading(false)
    }
  }

  const handleFormSubmit = (data: Record<string, any>) => {
    if (sharedData?.access_mode === 'readonly') {
      // Read-only mode - should not allow submissions
      console.log('Shared record viewed (read-only):', { recordId: sharedData?.record.id, data })
      alert('Record information viewed successfully!')
    } else {
      // Editable mode - handle record updates
      console.log('Shared record updated:', { recordId: sharedData?.record.id, data })
      // TODO: Implement record update API call for shared records
      alert('Record updated successfully!')
    }
  }

  const handleFormError = (error: string) => {
    console.error('Shared record form error:', error)
  }

  const formatTimeRemaining = (seconds: number) => {
    if (seconds <= 0) return 'Expired'
    
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    
    if (hours > 24) {
      const days = Math.floor(hours / 24)
      return `${days} day${days !== 1 ? 's' : ''} remaining`
    } else if (hours > 0) {
      return `${hours}h ${minutes}m remaining`
    } else {
      return `${minutes}m remaining`
    }
  }

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const isExpiringSoon = (remainingTime: number) => {
    return remainingTime < 24 * 60 * 60 // Less than 24 hours
  }

  // Show accessor info gate if no accessor info and no data loaded yet
  if (!accessorInfo && !sharedData && !error) {
    return (
      <AccessorInfoGate
        onSubmit={handleAccessorSubmit}
        loading={gateLoading}
        error={error}
      />
    )
  }

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 dark:from-gray-900 dark:to-blue-900/20">
        <div className="container mx-auto px-4 py-16">
          <div className="max-w-2xl mx-auto">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-8 text-center">
              <div className="w-16 h-16 mx-auto mb-6 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
              
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-200 mb-4">
                Loading Shared Record...
              </h1>
              
              <p className="text-gray-600 dark:text-gray-400">
                Please wait while we fetch the shared record information.
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20">
        <div className="container mx-auto px-4 py-16">
          <div className="max-w-2xl mx-auto">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-red-200 dark:border-red-800 p-8 text-center">
              <div className="w-16 h-16 mx-auto mb-6 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-8 h-8 text-red-600 dark:text-red-400" />
              </div>
              
              <h1 className="text-2xl font-bold text-red-900 dark:text-red-200 mb-4">
                Unable to Load Shared Record
              </h1>
              
              <p className="text-red-700 dark:text-red-300 mb-6">
                {error}
              </p>
              
              <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4 border border-red-200 dark:border-red-800">
                <p className="text-sm text-red-600 dark:text-red-400">
                  If you need access to this record, please contact the person who shared it with you 
                  to request a new share link.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!sharedData) {
    return null
  }

  // Check if expired
  if (sharedData.access_info?.is_expired || sharedData.time_remaining_seconds <= 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20">
        <div className="container mx-auto px-4 py-16">
          <div className="max-w-2xl mx-auto">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-red-200 dark:border-red-800 p-8 text-center">
              <div className="w-16 h-16 mx-auto mb-6 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
                <Clock className="w-8 h-8 text-red-600 dark:text-red-400" />
              </div>
              
              <h1 className="text-2xl font-bold text-red-900 dark:text-red-200 mb-4">
                Share Link Expired
              </h1>
              
              <p className="text-red-700 dark:text-red-300 mb-6">
                This share link has expired and is no longer accessible. 
                Share links are only valid for 5 working days after creation.
              </p>
              
              <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4 border border-red-200 dark:border-red-800">
                <p className="text-sm text-red-600 dark:text-red-400">
                  If you need access to this record, please contact the person who shared it with you 
                  to request a new share link.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const { record, form_schema, shared_by } = sharedData
  const timeRemaining = formatTimeRemaining(sharedData.time_remaining_seconds)
  const expiresSoon = isExpiringSoon(sharedData.time_remaining_seconds)

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Header Section */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-4">
                <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center flex-shrink-0">
                  <Shield className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                </div>
                
                <div className="flex-1">
                  <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                    {record.pipeline.name}
                  </h1>
                  <p className="text-gray-600 dark:text-gray-400 mb-2">
                    Shared record from <strong>{shared_by}</strong>
                  </p>
                  {accessorInfo && (
                    <p className="text-sm text-blue-600 dark:text-blue-400 mb-4 flex items-center">
                      <User className="w-4 h-4 mr-2" />
                      Accessing as: <strong className="ml-1">{accessorInfo.name}</strong> ({accessorInfo.email})
                    </p>
                  )}
                  
                  <div className="flex flex-wrap items-center gap-4 text-sm">
                    <div className="flex items-center text-gray-500 dark:text-gray-400">
                      <Calendar className="w-4 h-4 mr-2" />
                      Expires: {formatDate(sharedData.expires_at)}
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Status Badge */}
              <div className="flex flex-col items-end space-y-2">
                {/* Access Mode Badge */}
                <div className={`flex items-center px-3 py-1.5 rounded-full text-sm font-medium ${
                  sharedData.access_mode === 'readonly'
                    ? 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300'
                    : 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
                }`}>
                  {sharedData.access_mode === 'readonly' ? (
                    <>
                      <Lock className="w-4 h-4 mr-1.5" />
                      Read-only
                    </>
                  ) : (
                    <>
                      <Edit className="w-4 h-4 mr-1.5" />
                      Editable
                    </>
                  )}
                </div>
                
                {/* Expiry Status Badge */}
                <div className={`flex items-center px-3 py-1.5 rounded-full text-sm font-medium ${
                  expiresSoon 
                    ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
                    : 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                }`}>
                  {expiresSoon ? (
                    <>
                      <Clock className="w-4 h-4 mr-1.5" />
                      {timeRemaining}
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4 mr-1.5" />
                      Active
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Expiry Warning */}
          {expiresSoon && (
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 mb-6">
              <div className="flex items-start">
                <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5 mr-3 flex-shrink-0" />
                <div>
                  <h3 className="font-medium text-amber-900 dark:text-amber-200 mb-1">
                    Share Link Expiring Soon
                  </h3>
                  <p className="text-sm text-amber-700 dark:text-amber-300">
                    This share link will expire in {timeRemaining}. 
                    After expiration, you will no longer be able to access this record.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Access Information */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
            <div className="flex items-start">
              <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 mr-3 flex-shrink-0" />
              <div>
                <h3 className="font-medium text-blue-900 dark:text-blue-200 mb-1">
                  Secure Shared Access
                </h3>
                <p className="text-sm text-blue-700 dark:text-blue-300">
                  This is a secure, encrypted share link with{' '}
                  <strong>{sharedData.access_mode === 'readonly' ? 'read-only' : 'editable'}</strong> access.{' '}
                  {sharedData.access_mode === 'readonly' 
                    ? 'You can view all record information but cannot make changes.'
                    : 'You can view and update the record information.'
                  }
                </p>
                <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                  {accessorInfo ? (
                    <>Access logged as <strong>{accessorInfo.name}</strong> for security purposes.</>
                  ) : (
                    <>No login is required. Access is logged for security purposes.</>
                  )}
                </p>
                {sharedData.access_info?.access_count > 1 && (
                  <p className="text-xs text-blue-600 dark:text-blue-400 mt-2">
                    This link has been accessed {sharedData.access_info.access_count} times.
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Record Content */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                    Record Information
                  </h2>
                  <p className="text-gray-600 dark:text-gray-400 mt-1">
                    {sharedData.access_mode === 'readonly' 
                      ? 'View the shared record details below. This is a read-only view.'
                      : 'View and edit the shared record details below. Your changes will be saved.'
                    }
                  </p>
                </div>
                <div className={`flex items-center px-3 py-1.5 rounded-full text-xs font-medium ${
                  sharedData.access_mode === 'readonly'
                    ? 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-300'
                    : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                }`}>
                  {sharedData.access_mode === 'readonly' ? (
                    <>
                      <Lock className="w-3 h-3 mr-1" />
                      Read-only
                    </>
                  ) : (
                    <>
                      <Edit className="w-3 h-3 mr-1" />
                      Editable
                    </>
                  )}
                </div>
              </div>
            </div>
            
            <div className="p-6">
              {sharedData ? (
                <DynamicFormRenderer
                  pipelineId={record.pipeline.id}
                  formType="shared_record"
                  recordId={record.id}
                  encryptedToken={encryptedToken}
                  onSubmit={handleFormSubmit}
                  onError={handleFormError}
                  className="space-y-4"
                  embedMode={true}
                  readOnly={sharedData.access_mode === 'readonly'}
                />
              ) : (
                <div className="text-center py-8">
                  <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center">
                    <AlertTriangle className="w-8 h-8 text-gray-400" />
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    No Fields Available
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400">
                    This shared record doesn't have any visible fields to display.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="mt-8 text-center">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Powered by{' '}
              <span className="font-medium text-blue-600 dark:text-blue-400">
                Oneo CRM
              </span>
              {' '}- Secure Record Sharing
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}