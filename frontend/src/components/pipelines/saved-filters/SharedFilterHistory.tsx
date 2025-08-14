'use client'

import { useState, useEffect } from 'react'
import { Clock, Eye, ExternalLink, Ban, Activity, Mail, Calendar, BarChart3, AlertTriangle } from 'lucide-react'
import { savedFiltersApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { toast } from '@/hooks/use-toast'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'

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
  status: 'active' | 'expired' | 'revoked'
  created_at: string
}

interface SharedFilterHistoryProps {
  filterKey?: string // Optional: if provided, only show shares for this specific saved filter
  className?: string
}

export function SharedFilterHistory({ filterKey, className = '' }: SharedFilterHistoryProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [sharedFilters, setSharedFilters] = useState<SharedFilter[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [selectedFilter, setSelectedFilter] = useState<SharedFilter | null>(null)

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

  const revokeShare = async (shareId: string) => {
    try {
      await savedFiltersApi.shared.revoke(shareId)
      toast({
        title: '🚫 Share revoked',
        description: 'The shared filter link has been deactivated.',
      })
      // Reload the data
      loadSharedFilters()
    } catch (error: any) {
      console.error('Failed to revoke share:', error)
      toast({
        title: 'Failed to revoke share',
        description: 'Could not deactivate the shared filter link.',
        variant: 'destructive',
      })
    }
  }

  const copyShareLink = async (token: string) => {
    const shareUrl = `${window.location.origin}/shared/filter/${token}`
    try {
      await navigator.clipboard.writeText(shareUrl)
      toast({
        title: '📋 Link copied',
        description: 'Share link copied to clipboard.',
      })
    } catch (error) {
      toast({
        title: 'Failed to copy',
        description: 'Could not copy link to clipboard.',
        variant: 'destructive',
      })
    }
  }

  const previewShare = (token: string) => {
    const shareUrl = `${window.location.origin}/shared/filter/${token}`
    window.open(shareUrl, '_blank')
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatTimeRemaining = (seconds: number) => {
    if (seconds <= 0) return 'Expired'
    
    const days = Math.floor(seconds / (24 * 60 * 60))
    const hours = Math.floor((seconds % (24 * 60 * 60)) / (60 * 60))
    
    if (days > 0) return `${days} day${days > 1 ? 's' : ''} remaining`
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} remaining`
    return 'Less than 1 hour remaining'
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <Activity className="w-4 h-4 text-green-600" />
      case 'expired':
        return <Clock className="w-4 h-4 text-orange-600" />
      case 'revoked':
        return <Ban className="w-4 h-4 text-red-600" />
      default:
        return <AlertTriangle className="w-4 h-4 text-gray-600" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'text-green-800 bg-green-50 dark:text-green-200 dark:bg-green-900/20'
      case 'expired':
        return 'text-orange-800 bg-orange-50 dark:text-orange-200 dark:bg-orange-900/20'
      case 'revoked':
        return 'text-red-800 bg-red-50 dark:text-red-200 dark:bg-red-900/20'
      default:
        return 'text-gray-800 bg-gray-50 dark:text-gray-200 dark:bg-gray-900/20'
    }
  }

  const handleModalOpen = () => {
    setIsOpen(true)
    loadSharedFilters()
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={className}
          onClick={handleModalOpen}
        >
          <BarChart3 className="w-4 h-4 mr-2" />
          {filterKey ? 'Share History' : 'All Shares'}
        </Button>
      </DialogTrigger>
      
      <DialogContent className="sm:max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center">
            <BarChart3 className="w-5 h-5 mr-2 text-orange-600" />
            {filterKey ? 'Share History for This Filter' : 'All Shared Filters'}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-600"></div>
              <span className="ml-3 text-gray-600 dark:text-gray-400">Loading share history...</span>
            </div>
          ) : sharedFilters.length === 0 ? (
            <div className="text-center py-8">
              <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                No shares found
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {filterKey 
                  ? 'This filter hasn\'t been shared yet.' 
                  : 'You haven\'t shared any filters yet.'}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {sharedFilters.map((share) => (
                <div
                  key={share.id}
                  className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <h4 className="font-medium text-gray-900 dark:text-white">
                          {share.saved_filter_name}
                        </h4>
                        <span className="text-sm text-gray-500 dark:text-gray-400">
                          • {share.pipeline_name}
                        </span>
                      </div>
                      <div className="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                        <div className="flex items-center space-x-1">
                          <Mail className="w-4 h-4" />
                          <span>{share.intended_recipient_email}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Eye className="w-4 h-4" />
                          <span>{share.access_mode === 'readonly' ? 'Read-only' : 'Filtered Edit'}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Activity className="w-4 h-4" />
                          <span>{share.access_count} access{share.access_count !== 1 ? 'es' : ''}</span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <div className={`px-2 py-1 rounded-full text-xs font-medium flex items-center space-x-1 ${getStatusColor(share.status)}`}>
                        {getStatusIcon(share.status)}
                        <span className="capitalize">{share.status}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
                      <div className="flex items-center space-x-1">
                        <Calendar className="w-4 h-4" />
                        <span>Shared {formatDate(share.created_at)}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <Clock className="w-4 h-4" />
                        <span>{formatTimeRemaining(share.time_remaining)}</span>
                      </div>
                      {share.last_accessed_at && (
                        <div className="flex items-center space-x-1">
                          <Eye className="w-4 h-4" />
                          <span>Last accessed {formatDate(share.last_accessed_at)}</span>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center space-x-2">
                      {share.status === 'active' && (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => copyShareLink(share.encrypted_token)}
                          >
                            📋 Copy Link
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => previewShare(share.encrypted_token)}
                          >
                            <ExternalLink className="w-4 h-4 mr-1" />
                            Preview
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => revokeShare(share.id)}
                            className="text-red-600 hover:text-red-800 hover:bg-red-50 dark:text-red-400 dark:hover:text-red-300 dark:hover:bg-red-900/20"
                          >
                            <Ban className="w-4 h-4 mr-1" />
                            Revoke
                          </Button>
                        </>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setSelectedFilter(share)}
                      >
                        View Details
                      </Button>
                    </div>
                  </div>

                  {share.shared_fields && share.shared_fields.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
                      <div className="text-sm">
                        <span className="text-gray-600 dark:text-gray-400">Shared fields:</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {share.shared_fields.map((field) => (
                            <span
                              key={field}
                              className="px-2 py-1 bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 text-xs rounded"
                            >
                              {field}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}