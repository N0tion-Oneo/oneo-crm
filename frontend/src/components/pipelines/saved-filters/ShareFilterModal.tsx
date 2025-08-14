'use client'

import React, { useState, useEffect } from 'react'
import { X, Share2, Copy, Calendar, Clock, Eye, Users, AlertCircle } from 'lucide-react'
import { savedFiltersApi } from '@/lib/api'
import { SavedFilter } from './SavedFiltersList'

export interface ShareFilterModalProps {
  isOpen: boolean
  onClose: () => void
  filter: SavedFilter | null
  onShared?: (sharedFilter: any) => void
}

export function ShareFilterModal({
  isOpen,
  onClose,
  filter,
  onShared
}: ShareFilterModalProps) {
  const [formData, setFormData] = useState({
    intended_recipient_email: '',
    access_mode: 'readonly' as 'readonly' | 'filtered_edit',
    expires_at: ''
  })
  const [selectedShareFields, setSelectedShareFields] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [shares, setShares] = useState<any[]>([])
  const [sharesLoading, setSharesLoading] = useState(false)
  const [copiedLink, setCopiedLink] = useState<string | null>(null)

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen && filter) {
      // Set default expiry to 5 working days from now
      const now = new Date()
      const expiryDate = new Date(now)
      expiryDate.setDate(now.getDate() + 7) // 7 days to account for weekends
      
      setFormData({
        intended_recipient_email: '',
        access_mode: 'readonly',
        expires_at: expiryDate.toISOString().slice(0, 16) // Format for datetime-local input
      })
      
      // Initialize with all shareable fields selected by default
      const defaultShareFields = filter.shareable_fields || []
      setSelectedShareFields(defaultShareFields)
      
      setError(null)
      setCopiedLink(null)
      loadShares()
    }
  }, [isOpen, filter])

  const loadShares = async () => {
    if (!filter) return
    
    try {
      setSharesLoading(true)
      const response = await savedFiltersApi.shares(filter.id)
      setShares(response.data || [])
    } catch (err: any) {
      console.error('❌ Error loading shares:', err)
    } finally {
      setSharesLoading(false)
    }
  }

  const handleShare = async () => {
    if (!filter) return

    try {
      setLoading(true)
      setError(null)

      if (!formData.intended_recipient_email.trim()) {
        setError('Recipient email is required')
        return
      }

      if (!formData.expires_at) {
        setError('Expiry date is required')
        return
      }

      if (selectedShareFields.length === 0) {
        setError('Please select at least one field to share')
        return
      }

      const payload = {
        intended_recipient_email: formData.intended_recipient_email.trim(),
        access_mode: formData.access_mode,
        expires_at: new Date(formData.expires_at).toISOString(),
        shared_fields: selectedShareFields
      }

      console.log('📤 Sharing filter with payload:', payload)
      
      const response = await savedFiltersApi.share(filter.id, payload)
      
      console.log('✅ Filter shared successfully:', response.data)
      
      if (onShared) {
        onShared(response.data)
      }
      
      // Reset form and reload shares
      setFormData({
        intended_recipient_email: '',
        access_mode: 'readonly',
        expires_at: formData.expires_at // Keep the same expiry date
      })
      
      // Reset to default shareable fields
      const defaultShareFields = (filter.shareable_fields || []).slice() // Make a copy to avoid mutations
      setSelectedShareFields(defaultShareFields)
      
      loadShares()
    } catch (err: any) {
      console.error('❌ Error sharing filter:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to share filter')
    } finally {
      setLoading(false)
    }
  }

  const handleCopyLink = async (token: string) => {
    try {
      const baseUrl = window.location.origin
      const shareUrl = `${baseUrl}/shared/filter/${token}`
      
      await navigator.clipboard.writeText(shareUrl)
      setCopiedLink(token)
      
      // Clear the "copied" state after 2 seconds
      setTimeout(() => setCopiedLink(null), 2000)
    } catch (err) {
      console.error('❌ Error copying to clipboard:', err)
      setError('Failed to copy link to clipboard')
    }
  }

  const handleRevokeShare = async (shareId: string) => {
    if (!confirm('Are you sure you want to revoke this share? The recipient will no longer be able to access the filter.')) {
      return
    }

    try {
      await savedFiltersApi.shared.revoke(shareId)
      loadShares() // Refresh the shares list
    } catch (err: any) {
      console.error('❌ Error revoking share:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to revoke share')
    }
  }

  const handleFieldToggle = (fieldSlug: string) => {
    setSelectedShareFields(prev => 
      prev.includes(fieldSlug)
        ? prev.filter(f => f !== fieldSlug)
        : [...prev, fieldSlug]
    )
  }

  const formatTimeRemaining = (seconds: number) => {
    if (seconds <= 0) return 'Expired'
    
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    
    if (days > 0) return `${days}d ${hours}h`
    if (hours > 0) return `${hours}h`
    return 'Less than 1h'
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-600 dark:text-green-400'
      case 'expired': return 'text-yellow-600 dark:text-yellow-400'
      case 'revoked': return 'text-red-600 dark:text-red-400'
      default: return 'text-gray-600 dark:text-gray-400'
    }
  }

  if (!isOpen || !filter) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <Share2 className="w-6 h-6 text-orange-500" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Share Filter: {filter.name}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Generate secure share links for external access
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {error && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
              <div className="flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
              </div>
            </div>
          )}

          {/* Filter Info */}
          <div className="mb-6 p-4 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-md">
            <h3 className="font-medium text-gray-900 dark:text-white mb-2">Filter Information</h3>
            <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
              <p><strong>View mode:</strong> {filter.view_mode}</p>
              <p><strong>Filter fields:</strong> {(filter.visible_fields || []).length} total</p>
              <p><strong>Shareable fields:</strong> {(filter.shareable_fields || []).length} approved for external sharing</p>
              {!filter.can_share.allowed && (
                <div className="mt-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded">
                  <p className="text-yellow-600 dark:text-yellow-400">
                    ⚠️ {filter.can_share.reason}
                  </p>
                </div>
              )}
            </div>
          </div>

          {filter.can_share.allowed && (
            <>
              {/* Create New Share */}
              <div className="mb-8 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Create New Share
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Recipient Email *
                    </label>
                    <input
                      type="email"
                      value={formData.intended_recipient_email}
                      onChange={(e) => setFormData(prev => ({ ...prev, intended_recipient_email: e.target.value }))}
                      placeholder="Enter recipient's email address..."
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white"
                    />
                  </div>

                  {/* Field Selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Fields to Share ({selectedShareFields.length} of {(filter.shareable_fields || []).length} selected)
                    </label>
                    <div className="max-h-40 overflow-y-auto border border-gray-300 dark:border-gray-600 rounded-md p-3 space-y-2">
                      {(filter.shareable_fields || []).length === 0 ? (
                        <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                          No fields are approved for external sharing by the administrator.
                        </p>
                      ) : (
                        (filter.shareable_fields || []).map(fieldSlug => (
                          <label key={fieldSlug} className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={selectedShareFields.includes(fieldSlug)}
                              onChange={() => handleFieldToggle(fieldSlug)}
                              className="rounded border-gray-300 text-orange-600 focus:ring-orange-500"
                            />
                            <span className="text-sm text-gray-700 dark:text-gray-300">
                              {fieldSlug}
                            </span>
                            <span className="text-xs text-orange-600 dark:text-orange-400">
                              ✓ Approved for sharing
                            </span>
                          </label>
                        ))
                      )}
                    </div>
                    {(filter.shareable_fields || []).length > 0 && (
                      <div className="mt-2 flex space-x-2">
                        <button
                          type="button"
                          onClick={() => setSelectedShareFields([...(filter.shareable_fields || [])])}
                          className="text-xs text-orange-600 hover:text-orange-800 dark:text-orange-400 dark:hover:text-orange-300"
                        >
                          Select All
                        </button>
                        <span className="text-xs text-gray-400">•</span>
                        <button
                          type="button"
                          onClick={() => setSelectedShareFields([])}
                          className="text-xs text-orange-600 hover:text-orange-800 dark:text-orange-400 dark:hover:text-orange-300"
                        >
                          Select None
                        </button>
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Access Level
                    </label>
                    <select
                      value={formData.access_mode}
                      onChange={(e) => setFormData(prev => ({ ...prev, access_mode: e.target.value as any }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white"
                    >
                      <option value="readonly">Read-only (view only)</option>
                      <option value="filtered_edit">Filtered Edit (edit visible records)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Expires At *
                    </label>
                    <input
                      type="datetime-local"
                      value={formData.expires_at}
                      onChange={(e) => setFormData(prev => ({ ...prev, expires_at: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white"
                    />
                  </div>

                  <button
                    onClick={handleShare}
                    disabled={loading || !formData.intended_recipient_email.trim() || !formData.expires_at || selectedShareFields.length === 0}
                    className="w-full px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
                  >
                    <Share2 className="w-4 h-4" />
                    <span>{loading ? 'Creating Share...' : 'Create Share Link'}</span>
                  </button>
                </div>
              </div>
            </>
          )}

          {/* Existing Shares */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Existing Shares ({shares.length})
            </h3>
            
            {sharesLoading ? (
              <div className="animate-pulse space-y-3">
                {[1, 2].map(i => (
                  <div key={i} className="h-20 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
                ))}
              </div>
            ) : shares.length === 0 ? (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No shares created yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {shares.map(share => (
                  <div
                    key={share.id}
                    className="border border-gray-200 dark:border-gray-700 rounded-lg p-4"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-2">
                          <span className="text-sm font-medium text-gray-900 dark:text-white">
                            {share.intended_recipient_email}
                          </span>
                          <span className={`text-xs px-2 py-1 rounded-full ${getStatusColor(share.status)}`}>
                            {share.status}
                          </span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {share.access_mode}
                          </span>
                        </div>
                        
                        <div className="flex items-center space-x-4 text-xs text-gray-500 dark:text-gray-400">
                          <div className="flex items-center space-x-1">
                            <Eye className="w-3 h-3" />
                            <span>{share.access_count} views</span>
                          </div>
                          <div className="flex items-center space-x-1">
                            <Clock className="w-3 h-3" />
                            <span>{formatTimeRemaining(share.time_remaining)}</span>
                          </div>
                          <div className="flex items-center space-x-1">
                            <Calendar className="w-3 h-3" />
                            <span>Expires {new Date(share.expires_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        {share.status === 'active' && (
                          <button
                            onClick={() => handleCopyLink(share.encrypted_token)}
                            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                            title="Copy share link"
                          >
                            <Copy className={`w-4 h-4 ${copiedLink === share.encrypted_token ? 'text-green-500' : ''}`} />
                          </button>
                        )}
                        
                        {share.is_active && (
                          <button
                            onClick={() => handleRevokeShare(share.id)}
                            className="p-2 text-red-400 hover:text-red-600 dark:hover:text-red-300 transition-colors"
                            title="Revoke share"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>

                    {copiedLink === share.encrypted_token && (
                      <div className="mt-2 p-2 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded text-xs text-green-600 dark:text-green-400">
                        ✅ Share link copied to clipboard!
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}