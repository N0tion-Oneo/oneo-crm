'use client'

import { useState, useEffect } from 'react'
import { format } from 'date-fns'
import { 
  History,
  Clock, 
  Eye, 
  ExternalLink, 
  Ban, 
  Activity, 
  Mail, 
  Calendar, 
  BarChart3, 
  AlertTriangle,
  Shield,
  Users,
  RefreshCw,
  Share2,
  Check,
  Copy,
  Edit
} from 'lucide-react'
import { savedFiltersApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { toast } from '@/hooks/use-toast'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { cn } from '@/lib/utils'

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

interface SharedFilterHistoryProps {
  filterKey?: string // Optional: if provided, only show shares for this specific saved filter
  className?: string
  trigger?: React.ReactNode
}

export function SharedFilterHistory({ 
  filterKey, 
  className = '',
  trigger 
}: SharedFilterHistoryProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [sharedFilters, setSharedFilters] = useState<SharedFilter[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [selectedShare, setSelectedShare] = useState<SharedFilter | null>(null)
  const [accessLogs, setAccessLogs] = useState<AccessLog[]>([])
  const [isLoadingLogs, setIsLoadingLogs] = useState(false)
  const [activeTab, setActiveTab] = useState<'history' | 'details'>('history')
  const [copied, setCopied] = useState<string | null>(null)

  const loadSharedFilters = async () => {
    setIsLoading(true)
    try {
      if (filterKey) {
        // Load shares for a specific saved filter
        const response = await savedFiltersApi.shares(filterKey)
        setSharedFilters(response.data)
      } else {
        // Load all shared filters for the user
        const response = await savedFiltersApi.shared.list()
        setSharedFilters(response.data.results || response.data)
      }
    } catch (error: any) {
      console.error('Failed to load shared filters:', error)
      toast({
        title: 'Failed to load share history',
        description: 'Could not retrieve shared filter information.',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
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
      // Reload the data
      loadSharedFilters()
      if (selectedShare?.id === shareId) {
        setSelectedShare(null)
        setActiveTab('history')
      }
    } catch (error: any) {
      console.error('Failed to revoke share:', error)
      toast({
        title: 'Failed to revoke share',
        description: error.response?.data?.error || 'Could not deactivate the shared filter link.',
        variant: 'destructive',
      })
    }
  }

  const copyShareLink = async (share: SharedFilter) => {
    try {
      const shareUrl = `${window.location.origin}/shared/filter/${share.encrypted_token}`
      await navigator.clipboard.writeText(shareUrl)
      setCopied(share.id)
      toast({
        title: '📋 Share link copied',
        description: 'The share link has been copied to your clipboard.',
      })
      setTimeout(() => setCopied(null), 3000)
    } catch (error) {
      toast({
        title: 'Failed to copy',
        description: 'Could not copy share link to clipboard.',
        variant: 'destructive',
      })
    }
  }

  const previewShare = (token: string) => {
    const shareUrl = `${window.location.origin}/shared/filter/${token}`
    window.open(shareUrl, '_blank')
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

  const handleModalOpen = () => {
    setIsOpen(true)
    setActiveTab('history')
    setSelectedShare(null)
    loadSharedFilters()
  }

  const handleShareSelect = (share: SharedFilter) => {
    setSelectedShare(share)
    setActiveTab('details')
    loadAccessLogs(share.id)
  }

  useEffect(() => {
    if (isOpen) {
      loadSharedFilters()
    }
  }, [isOpen, filterKey])

  const defaultTrigger = (
    <Button
      variant="outline"
      size="sm"
      className={className}
      onClick={handleModalOpen}
    >
      <History className="w-4 h-4 mr-2" />
      {filterKey ? 'Share History' : 'All Shares'}
    </Button>
  )

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {trigger || defaultTrigger}
      </DialogTrigger>
      
      <DialogContent className="sm:max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center">
            <Shield className="w-5 h-5 mr-2 text-blue-600" />
            {filterKey ? 'Share History for This Filter' : 'Sharing History'}
          </DialogTitle>
        </DialogHeader>

        {/* Tab Navigation */}
        <div className="flex border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => {
              setActiveTab('history')
              setSelectedShare(null)
            }}
            className={cn(
              "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
              activeTab === 'history'
                ? "border-blue-500 text-blue-600 dark:text-blue-400"
                : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
            )}
          >
            <History className="w-4 h-4 inline mr-2" />
            Share History
          </button>
          {selectedShare && (
            <button
              onClick={() => setActiveTab('details')}
              className={cn(
                "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
                activeTab === 'details'
                  ? "border-blue-500 text-blue-600 dark:text-blue-400"
                  : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
              )}
            >
              <Shield className="w-4 h-4 inline mr-2" />
              Access Details
            </button>
          )}
        </div>

        <div className="flex-1 overflow-hidden">
          {activeTab === 'history' ? (
            <div className="space-y-4 overflow-y-auto max-h-[60vh]">
              <div className="flex justify-between items-center">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {filterKey 
                    ? 'Track all share links created for this filter'
                    : 'All shared filters you have created'}
                </p>
                <Button
                  onClick={loadSharedFilters}
                  variant="ghost"
                  size="sm"
                  disabled={isLoading}
                >
                  <RefreshCw className={cn("w-4 h-4", isLoading && "animate-spin")} />
                </Button>
              </div>

              {isLoading ? (
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
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {filterKey 
                      ? 'This filter hasn\'t been shared yet. Use the Share button to create your first share link.' 
                      : 'You haven\'t shared any filters yet.'}
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {sharedFilters.map((share) => (
                    <div
                      key={share.id}
                      className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer"
                      onClick={() => handleShareSelect(share)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 space-y-2">
                          <div className="flex items-center space-x-3">
                            {getAccessModeIcon(share.access_mode)}
                            <span className="font-medium text-gray-900 dark:text-white">
                              {share.saved_filter_name}
                            </span>
                            {getStatusBadge(share)}
                          </div>
                          
                          <div className="grid grid-cols-2 gap-4 text-sm text-gray-600 dark:text-gray-400">
                            <div className="flex items-center space-x-2">
                              <Mail className="w-4 h-4" />
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
                                {copied === share.id ? (
                                  <Check className="w-4 h-4 text-green-600" />
                                ) : (
                                  <Copy className="w-4 h-4" />
                                )}
                              </Button>
                              <Button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  revokeShare(share.id)
                                }}
                                variant="ghost"
                                size="sm"
                                className="text-red-600 hover:text-red-800"
                              >
                                <Ban className="w-4 h-4" />
                              </Button>
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
            // Detailed access logs view
            selectedShare && (
              <div className="space-y-4 overflow-y-auto max-h-[60vh]">
                <div className="flex items-center justify-between">
                  <Button
                    onClick={() => setActiveTab('history')}
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

                {/* Share Details */}
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
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Shared by</label>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{selectedShare.shared_by_name || `${selectedShare.shared_by.first_name} ${selectedShare.shared_by.last_name}`.trim()}</p>
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
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Expires</label>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{formatDate(selectedShare.expires_at)}</p>
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

                {/* Access Logs */}
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
                          {copied === selectedShare.id ? (
                            <Check className="w-4 h-4 mr-2 text-green-600" />
                          ) : (
                            <Copy className="w-4 h-4 mr-2" />
                          )}
                          Copy Link
                        </Button>
                        <Button
                          onClick={() => revokeShare(selectedShare.id)}
                          variant="destructive"
                          size="sm"
                        >
                          <Ban className="w-4 h-4 mr-2" />
                          Revoke
                        </Button>
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
                              {/* Primary accessor information */}
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
                              
                              {/* Access details */}
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
                              
                              {/* User agent (truncated) */}
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
            )
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}