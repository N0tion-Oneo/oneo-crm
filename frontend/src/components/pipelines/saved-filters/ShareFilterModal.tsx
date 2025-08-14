'use client'

import React, { useState, useEffect } from 'react'
import { format } from 'date-fns'
import { 
  X, 
  Share2, 
  Copy, 
  Calendar, 
  Clock, 
  Eye, 
  Users, 
  AlertCircle,
  History,
  Shield,
  Activity,
  Ban,
  RefreshCw,
  Check,
  Edit,
  Plus,
  ExternalLink
} from 'lucide-react'
import { savedFiltersApi } from '@/lib/api'
import { SavedFilter } from './SavedFiltersList'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { toast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'
import { PermissionGuard, PermissionButton } from '@/components/permissions/PermissionGuard'
import { useAuth } from '@/features/auth/context'

export interface ShareFilterModalProps {
  isOpen: boolean
  onClose: () => void
  filter: SavedFilter | null
  onShared?: (sharedFilter: any) => void
}

interface SharedFilter {
  id: string
  saved_filter: string
  saved_filter_name: string
  pipeline_name: string
  encrypted_token: string
  shared_by: {
    id: string
    email: string
    first_name: string
    last_name: string
  }
  shared_by_name: string
  intended_recipient_email: string
  access_mode: 'readonly' | 'filtered_edit'
  shared_fields: string[]
  expires_at: string
  access_count: number
  last_accessed_at: string | null
  last_accessed_ip: string | null
  is_active: boolean
  revoked_at: string | null
  revoked_by: any
  time_remaining: number
  time_remaining_seconds: number
  status: 'active' | 'expired' | 'revoked'
  created_at: string
}

interface AccessLog {
  id: string
  accessed_at: string
  accessor_name: string
  accessor_email: string
  ip_address: string
  user_agent: string
  country?: string
  city?: string
  session_duration?: number
}

export function ShareFilterModal({
  isOpen,
  onClose,
  filter,
  onShared
}: ShareFilterModalProps) {
  const { hasPermission } = useAuth()
  const [activeTab, setActiveTab] = useState('create')
  
  // Share creation state
  const [formData, setFormData] = useState({
    intended_recipient_email: '',
    access_mode: 'readonly' as 'readonly' | 'filtered_edit'
  })
  const [selectedShareFields, setSelectedShareFields] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copiedLink, setCopiedLink] = useState<string | null>(null)
  
  // History state
  const [sharedFilters, setSharedFilters] = useState<SharedFilter[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [selectedShare, setSelectedShare] = useState<SharedFilter | null>(null)
  const [accessLogs, setAccessLogs] = useState<AccessLog[]>([])
  const [isLoadingLogs, setIsLoadingLogs] = useState(false)
  const [copiedShareId, setCopiedShareId] = useState<string | null>(null)

  // Reset form and load data when modal opens
  useEffect(() => {
    if (isOpen && filter) {
      setFormData({
        intended_recipient_email: '',
        access_mode: 'readonly'
      })
      
      // Initialize with all shareable fields selected by default
      const defaultShareFields = filter.shareable_fields || []
      setSelectedShareFields(defaultShareFields)
      
      setError(null)
      setCopiedLink(null)
      setActiveTab('create')
      setSelectedShare(null)
      
      loadSharedFilters()
    }
  }, [isOpen, filter])

  const loadSharedFilters = async () => {
    if (!filter) return
    
    try {
      setIsLoadingHistory(true)
      const response = await savedFiltersApi.shares(filter.id)
      setSharedFilters(response.data || [])
    } catch (err: any) {
      console.error('❌ Error loading shares:', err)
      toast({
        title: 'Failed to load share history',
        description: 'Could not retrieve shared filter information.',
        variant: 'destructive',
      })
    } finally {
      setIsLoadingHistory(false)
    }
  }
  
  const loadAccessLogs = async (shareId: string) => {
    setIsLoadingLogs(true)
    try {
      const response = await savedFiltersApi.shared.accessLogs(shareId)
      setAccessLogs(response.data.results || response.data)
    } catch (error: any) {
      console.error('Failed to load access logs:', error)
      toast({
        title: 'Failed to load access logs',
        description: error.response?.data?.error || 'An error occurred while loading access logs.',
        variant: 'destructive',
      })
    } finally {
      setIsLoadingLogs(false)
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


      if (filter.shareable_fields && filter.shareable_fields.length > 0 && selectedShareFields.length === 0) {
        setError('Please select at least one field to share')
        return
      }

      // Calculate expiry date - 5 working days from now
      const now = new Date()
      const expiryDate = new Date(now)
      expiryDate.setDate(now.getDate() + 7) // 7 calendar days to account for weekends

      const payload = {
        intended_recipient_email: formData.intended_recipient_email.trim(),
        access_mode: formData.access_mode,
        expires_at: expiryDate.toISOString(),
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
        access_mode: 'readonly'
      })
      
      // Reset to default shareable fields
      const defaultShareFields = (filter.shareable_fields || []).slice() // Make a copy to avoid mutations
      setSelectedShareFields(defaultShareFields)
      
      loadSharedFilters()
      
      // Switch to history tab to see the new share
      setActiveTab('history')
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

  const revokeShare = async (shareId: string) => {
    if (!confirm('Are you sure you want to revoke this share? The recipient will no longer be able to access the filter.')) {
      return
    }

    try {
      await savedFiltersApi.shared.revoke(shareId)
      toast({
        title: '✅ Share link revoked',
        description: 'The share link has been revoked and is no longer accessible.',
      })
      loadSharedFilters()
      if (selectedShare?.id === shareId) {
        setSelectedShare(null)
      }
    } catch (err: any) {
      console.error('❌ Error revoking share:', err)
      toast({
        title: 'Failed to revoke share',
        description: err.response?.data?.detail || err.message || 'Failed to revoke share',
        variant: 'destructive',
      })
    }
  }
  
  const copyShareLink = async (share: SharedFilter) => {
    try {
      const shareUrl = `${window.location.origin}/shared/filter/${share.encrypted_token}`
      await navigator.clipboard.writeText(shareUrl)
      setCopiedShareId(share.id)
      toast({
        title: '📋 Share link copied',
        description: 'The share link has been copied to your clipboard.',
      })
      setTimeout(() => setCopiedShareId(null), 3000)
    } catch (error) {
      toast({
        title: 'Failed to copy',
        description: 'Could not copy share link to clipboard.',
        variant: 'destructive',
      })
    }
  }
  
  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'MMM dd, yyyy HH:mm')
    } catch {
      return dateString
    }
  }
  
  const formatTimeRemaining = (seconds: number) => {
    if (seconds <= 0) return 'Expired'
    
    const days = Math.floor(seconds / (24 * 60 * 60))
    const hours = Math.floor((seconds % (24 * 60 * 60)) / (60 * 60))
    const minutes = Math.floor((seconds % (60 * 60)) / 60)
    
    if (days > 0) return `${days}d ${hours}h remaining`
    if (hours > 0) return `${hours}h ${minutes}m remaining`
    return `${minutes}m remaining`
  }
  
  const getStatusBadge = (share: SharedFilter) => {
    switch (share.status) {
      case 'active':
        return <Badge variant="default" className="bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">Active</Badge>
      case 'expired':
        return <Badge variant="secondary" className="bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400">Expired</Badge>
      case 'revoked':
        return <Badge variant="destructive">Revoked</Badge>
      default:
        return <Badge variant="outline">{share.status}</Badge>
    }
  }
  
  const getAccessModeIcon = (mode: string) => {
    return mode === 'readonly' ? (
      <Eye className="w-4 h-4 text-blue-600" />
    ) : (
      <Edit className="w-4 h-4 text-green-600" />
    )
  }

  const handleFieldToggle = (fieldSlug: string) => {
    setSelectedShareFields(prev => 
      prev.includes(fieldSlug)
        ? prev.filter(f => f !== fieldSlug)
        : [...prev, fieldSlug]
    )
  }



  if (!isOpen || !filter) return null

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-4xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center">
            <Shield className="w-5 h-5 mr-2 text-blue-600" />
            Share Filter: {filter.name}
          </DialogTitle>
        </DialogHeader>
        
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 overflow-hidden">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="create" className="flex items-center">
              <Plus className="w-4 h-4 mr-2" />
              Create Share
            </TabsTrigger>
            <TabsTrigger value="history" className="flex items-center">
              <History className="w-4 h-4 mr-2" />
              History & Access
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="create" className="flex-1 overflow-y-auto">
            <PermissionGuard 
              category="sharing" 
              action="create_shared_views"
              fallback={
                <div className="flex flex-col items-center justify-center py-12">
                  <Shield className="w-16 h-16 text-gray-300 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    Permission Required
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 text-center max-w-md">
                    You don't have permission to create shared views. Contact your administrator to request access.
                  </p>
                </div>
              }
            >
              {error && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md mb-4">
                  <div className="flex items-center space-x-2">
                    <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
                    <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                  </div>
                </div>
              )}

              <div className="text-center py-8">
                <Share2 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  Share this filter securely
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                  Generate a secure, encrypted share link that expires automatically after 5 working days.
                </p>
                
                {/* Recipient Email Input */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Recipient email address <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="email"
                    value={formData.intended_recipient_email}
                    onChange={(e) => setFormData(prev => ({ ...prev, intended_recipient_email: e.target.value }))}
                    placeholder="Enter the email address of the person you're sharing with"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
                    required
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    🔒 This share link will only work for this specific email address
                  </p>
                </div>
                
                {/* Access Mode Selection */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                    Choose access level:
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      onClick={() => setFormData(prev => ({ ...prev, access_mode: 'filtered_edit' }))}
                      className={`p-4 border rounded-lg text-left transition-all ${
                        formData.access_mode === 'filtered_edit'
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center space-x-2 mb-2">
                        <Edit className={`w-5 h-5 ${formData.access_mode === 'filtered_edit' ? 'text-blue-600' : 'text-gray-400'}`} />
                        <span className={`font-medium ${formData.access_mode === 'filtered_edit' ? 'text-blue-900 dark:text-blue-100' : 'text-gray-900 dark:text-white'}`}>
                          Editable
                        </span>
                      </div>
                      <p className={`text-sm ${formData.access_mode === 'filtered_edit' ? 'text-blue-700 dark:text-blue-300' : 'text-gray-500 dark:text-gray-400'}`}>
                        Recipients can view and update the filtered records
                      </p>
                    </button>
                    
                    <button
                      onClick={() => setFormData(prev => ({ ...prev, access_mode: 'readonly' }))}
                      className={`p-4 border rounded-lg text-left transition-all ${
                        formData.access_mode === 'readonly'
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center space-x-2 mb-2">
                        <Eye className={`w-5 h-5 ${formData.access_mode === 'readonly' ? 'text-blue-600' : 'text-gray-400'}`} />
                        <span className={`font-medium ${formData.access_mode === 'readonly' ? 'text-blue-900 dark:text-blue-100' : 'text-gray-900 dark:text-white'}`}>
                          Read-only
                        </span>
                      </div>
                      <p className={`text-sm ${formData.access_mode === 'readonly' ? 'text-blue-700 dark:text-blue-300' : 'text-gray-500 dark:text-gray-400'}`}>
                        Recipients can only view the filtered data
                      </p>
                    </button>
                  </div>
                </div>

                {/* Field Selection - Only show if filter has shareable fields */}
                {filter.shareable_fields && filter.shareable_fields.length > 0 && (
                  <div className="mb-6 text-left">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                      Choose which fields to include:
                    </label>
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {filter.shareable_fields.map((fieldSlug) => (
                        <label key={fieldSlug} className="flex items-center space-x-3">
                          <input
                            type="checkbox"
                            checked={selectedShareFields.includes(fieldSlug)}
                            onChange={() => handleFieldToggle(fieldSlug)}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="text-sm text-gray-900 dark:text-white font-medium">
                            {fieldSlug}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
                  <div className="flex items-start space-x-3">
                    <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                    <div className="text-left">
                      <h4 className="text-sm font-medium text-blue-900 dark:text-blue-100">
                        Secure Sharing Features:
                      </h4>
                      <ul className="text-sm text-blue-700 dark:text-blue-300 mt-1 space-y-1">
                        <li>• End-to-end encrypted link</li>
                        <li>• No login required for recipients</li>
                        <li>• Automatic expiry after 5 working days</li>
                        <li>• Access tracking and analytics</li>
                      </ul>
                    </div>
                  </div>
                </div>
                
                <Button 
                  onClick={handleShare} 
                  disabled={loading || !formData.intended_recipient_email.trim() || (filter.shareable_fields && filter.shareable_fields.length > 0 && selectedShareFields.length === 0)}
                  className="w-full"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Generating secure link...
                    </>
                  ) : (
                    <>
                      <Share2 className="w-4 h-4 mr-2" />
                      Generate {formData.access_mode === 'readonly' ? 'Read-only' : 'Editable'} Share Link
                    </>
                  )}
                </Button>
              </div>
            </PermissionGuard>
          </TabsContent>
          
          <TabsContent value="history" className="flex-1 overflow-y-auto">
            <div className="h-full overflow-hidden">
              {!selectedShare ? (
                <div className="space-y-4 h-full overflow-y-auto">
                  <div className="flex justify-between items-center">
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Track all share links created for this filter
                    </p>
                    <Button
                      onClick={loadSharedFilters}
                      variant="ghost"
                      size="sm"
                      disabled={isLoadingHistory}
                    >
                      <RefreshCw className={cn("w-4 h-4", isLoadingHistory && "animate-spin")} />
                    </Button>
                  </div>

                  {isLoadingHistory ? (
                    <div className="flex items-center justify-center py-12">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                      <span className="ml-3 text-gray-600 dark:text-gray-400">Loading share history...</span>
                    </div>
                  ) : sharedFilters.length === 0 ? (
                    <div className="text-center py-12">
                      <Share2 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                        No sharing history
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                        This filter hasn't been shared yet.
                      </p>
                      <Button
                        onClick={() => setActiveTab('create')}
                        variant="outline"
                        size="sm"
                      >
                        <Plus className="w-4 h-4 mr-2" />
                        Create First Share Link
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {sharedFilters.map((share) => (
                        <div
                          key={share.id}
                          className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer"
                          onClick={() => {
                            setSelectedShare(share)
                            loadAccessLogs(share.id)
                          }}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1 space-y-2">
                              <div className="flex items-center space-x-3">
                                {getAccessModeIcon(share.access_mode)}
                                <span className="font-medium text-gray-900 dark:text-white">
                                  {share.access_mode === 'readonly' ? 'Read-only' : 'Filtered Edit'} Share
                                </span>
                                {getStatusBadge(share)}
                              </div>
                              
                              <div className="grid grid-cols-2 gap-4 text-sm text-gray-600 dark:text-gray-400">
                                <div className="flex items-center space-x-2">
                                  <Users className="w-4 h-4" />
                                  <span>{share.intended_recipient_email}</span>
                                </div>
                                <div className="flex items-center space-x-2">
                                  <Calendar className="w-4 h-4" />
                                  <span>Created {formatDate(share.created_at)}</span>
                                </div>
                                <div className="flex items-center space-x-2">
                                  <Activity className="w-4 h-4" />
                                  <span>{share.access_count} access{share.access_count !== 1 ? 'es' : ''}</span>
                                </div>
                                <div className="flex items-center space-x-2">
                                  <Clock className="w-4 h-4" />
                                  <span>
                                    {share.status === 'expired' 
                                      ? `Expired ${formatDate(share.expires_at)}`
                                      : share.status === 'revoked'
                                      ? `Revoked ${formatDate(share.revoked_at || '')}`
                                      : formatTimeRemaining(share.time_remaining_seconds || share.time_remaining)
                                    }
                                  </span>
                                </div>
                              </div>
                            </div>
                            
                            <div className="flex items-center space-x-2 ml-4">
                              {share.status === 'active' && (
                                <>
                                  <Button
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      copyShareLink(share)
                                    }}
                                    variant="ghost"
                                    size="sm"
                                  >
                                    {copiedShareId === share.id ? (
                                      <Check className="w-4 h-4 text-green-600" />
                                    ) : (
                                      <Copy className="w-4 h-4" />
                                    )}
                                  </Button>
                                  <PermissionGuard 
                                    category="sharing" 
                                    action="revoke_shared_views_forms"
                                    fallback={
                                      <Button
                                        disabled
                                        variant="ghost"
                                        size="sm"
                                        className="text-gray-400 cursor-not-allowed"
                                        title="No permission to revoke shares"
                                      >
                                        <Ban className="w-4 h-4" />
                                      </Button>
                                    }
                                  >
                                    <PermissionButton
                                      category="sharing"
                                      action="revoke_shared_views_forms"
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        revokeShare(share.id)
                                      }}
                                      variant="danger"
                                      className="text-sm px-2 py-1 bg-transparent hover:bg-red-50 text-red-600 hover:text-red-800"
                                    >
                                      <Ban className="w-4 h-4" />
                                    </PermissionButton>
                                  </PermissionGuard>
                                </>
                              )}
                              <ExternalLink className="w-4 h-4 text-gray-400" />
                            </div>
                          </div>

                          {share.shared_fields && share.shared_fields.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
                              <div className="text-sm">
                                <span className="text-gray-600 dark:text-gray-400">Shared fields:</span>
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {share.shared_fields.slice(0, 3).map((field) => (
                                    <span
                                      key={field}
                                      className="px-2 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 text-xs rounded"
                                    >
                                      {field}
                                    </span>
                                  ))}
                                  {share.shared_fields.length > 3 && (
                                    <span className="px-2 py-1 bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-xs rounded">
                                      +{share.shared_fields.length - 3} more
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-4 h-full overflow-y-auto">
                  <div className="flex items-center justify-between">
                    <Button
                      onClick={() => setSelectedShare(null)}
                      variant="ghost"
                      size="sm"
                    >
                      ← Back to History
                    </Button>
                    <div className="flex items-center space-x-2">
                      {getAccessModeIcon(selectedShare.access_mode)}
                      <span className="font-medium">{selectedShare.access_mode === 'readonly' ? 'Read-only' : 'Filtered Edit'} Share</span>
                      {getStatusBadge(selectedShare)}
                    </div>
                  </div>

                  <Separator />

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-3">
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Filter Name</label>
                        <p className="text-sm text-gray-600 dark:text-gray-400">{selectedShare.saved_filter_name}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Recipient</label>
                        <p className="text-sm text-gray-600 dark:text-gray-400">{selectedShare.intended_recipient_email}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Created</label>
                        <p className="text-sm text-gray-600 dark:text-gray-400">{formatDate(selectedShare.created_at)}</p>
                      </div>
                    </div>
                    <div className="space-y-3">
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Access Mode</label>
                        <p className="text-sm text-gray-600 dark:text-gray-400">{selectedShare.access_mode === 'readonly' ? 'Read-only' : 'Filtered Edit'}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Total Accesses</label>
                        <p className="text-sm text-gray-600 dark:text-gray-400">{selectedShare.access_count}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Last Accessed</label>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {selectedShare.last_accessed_at ? formatDate(selectedShare.last_accessed_at) : 'Never'}
                        </p>
                      </div>
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-lg font-medium">Access History</h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          People who have accessed this shared filter
                        </p>
                      </div>
                      {selectedShare.status === 'active' && (
                        <div className="flex space-x-2">
                          <Button
                            onClick={() => copyShareLink(selectedShare)}
                            variant="outline"
                            size="sm"
                          >
                            {copiedShareId === selectedShare.id ? (
                              <Check className="w-4 h-4 mr-2 text-green-600" />
                            ) : (
                              <Copy className="w-4 h-4 mr-2" />
                            )}
                            Copy Link
                          </Button>
                          <PermissionGuard 
                            category="sharing" 
                            action="revoke_shared_views_forms"
                            fallback={
                              <Button
                                disabled
                                variant="outline"
                                size="sm"
                                className="text-gray-400 cursor-not-allowed"
                                title="No permission to revoke shares"
                              >
                                <Ban className="w-4 h-4 mr-2" />
                                Revoke (No permission)
                              </Button>
                            }
                          >
                            <PermissionButton
                              category="sharing"
                              action="revoke_shared_views_forms"
                              onClick={() => revokeShare(selectedShare.id)}
                              variant="danger"
                              className="text-sm px-3 py-1"
                            >
                              <Ban className="w-4 h-4 mr-2" />
                              Revoke
                            </PermissionButton>
                          </PermissionGuard>
                        </div>
                      )}
                    </div>

                    {isLoadingLogs ? (
                      <div className="flex items-center justify-center py-8">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                        <span className="ml-3 text-gray-600 dark:text-gray-400">Loading access logs...</span>
                      </div>
                    ) : accessLogs.length === 0 ? (
                      <div className="text-center py-8">
                        <Users className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                        <p className="text-sm text-gray-500 dark:text-gray-400">No one has accessed this shared filter yet</p>
                        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Share the link to start tracking access</p>
                      </div>
                    ) : (
                      <div className="space-y-3 max-h-48 overflow-y-auto">
                        {accessLogs.map((log) => (
                          <div
                            key={log.id}
                            className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700"
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1 space-y-2">
                                <div className="flex items-center space-x-3">
                                  <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
                                    <Users className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                                  </div>
                                  <div>
                                    <p className="font-medium text-gray-900 dark:text-white">
                                      {log.accessor_name}
                                    </p>
                                    <p className="text-sm text-gray-600 dark:text-gray-400">
                                      {log.accessor_email}
                                    </p>
                                  </div>
                                </div>
                                
                                <div className="flex items-center space-x-4 text-xs text-gray-500 dark:text-gray-400">
                                  <div className="flex items-center space-x-1">
                                    <Clock className="w-3 h-3" />
                                    <span>{formatDate(log.accessed_at)}</span>
                                  </div>
                                  <Badge variant="outline" className="text-xs">
                                    {log.ip_address}
                                  </Badge>
                                  {log.country && (
                                    <span>
                                      {log.city ? `${log.city}, ${log.country}` : log.country}
                                    </span>
                                  )}
                                  {log.session_duration && (
                                    <span>
                                      {Math.round(log.session_duration / 60)}m session
                                    </span>
                                  )}
                                </div>
                                
                                {log.user_agent && (
                                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                    {log.user_agent}
                                  </p>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}