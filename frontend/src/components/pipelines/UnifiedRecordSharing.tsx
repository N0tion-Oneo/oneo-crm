'use client'

import { useState, useEffect } from 'react'
import { format } from 'date-fns'
import { 
  Share2, 
  Copy, 
  Check, 
  ExternalLink, 
  Clock, 
  Shield, 
  Eye, 
  Edit, 
  Lock,
  History,
  Users,
  Activity,
  Ban,
  RefreshCw,
  Calendar,
  AlertTriangle,
  X,
  Plus
} from 'lucide-react'
import { recordsApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { PermissionGuard } from '@/components/permissions/PermissionGuard'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { toast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'

interface UnifiedRecordSharingProps {
  pipelineId: string
  recordId: string
  pipelineName?: string
  className?: string
  variant?: 'default' | 'outline' | 'ghost'
  size?: 'default' | 'sm' | 'lg'
  trigger?: React.ReactNode
}

interface ShareLinkData {
  share_url: string
  encrypted_token: string
  expires_at: number
  expires_datetime: string
  working_days_remaining: number
  sharing_enabled: boolean
}

interface SharedRecordItem {
  id: string
  record_title: string
  pipeline_name: string
  shared_by_name: string
  access_mode: 'readonly' | 'editable'
  expires_at: string
  created_at: string
  access_count: number
  last_accessed_at: string | null
  is_active: boolean
  revoked_at: string | null
  status: 'active' | 'expired' | 'revoked' | 'inactive'
  is_expired: boolean
  time_remaining_seconds: number
  encrypted_token?: string
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

export function UnifiedRecordSharing({
  pipelineId,
  recordId,
  pipelineName = 'Record',
  className = '',
  variant = 'outline',
  size = 'default',
  trigger
}: UnifiedRecordSharingProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('create')
  
  // Share creation state
  const [isGenerating, setIsGenerating] = useState(false)
  const [shareData, setShareData] = useState<ShareLinkData | null>(null)
  const [accessMode, setAccessMode] = useState<'editable' | 'readonly'>('editable')
  const [recipientEmail, setRecipientEmail] = useState('')
  const [copied, setCopied] = useState(false)
  
  // History state
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [sharingHistory, setSharingHistory] = useState<SharedRecordItem[]>([])
  const [selectedShare, setSelectedShare] = useState<SharedRecordItem | null>(null)
  const [accessLogs, setAccessLogs] = useState<AccessLog[]>([])
  const [isLoadingLogs, setIsLoadingLogs] = useState(false)
  const [copiedShareId, setCopiedShareId] = useState<string | null>(null)

  const generateShareLink = async (mode: 'editable' | 'readonly') => {
    setIsGenerating(true)
    
    try {
      const response = await recordsApi.generateShareLink(pipelineId, recordId, { 
        access_mode: mode,
        intended_recipient_email: recipientEmail 
      })
      const backendData = response.data
      
      // Create frontend-friendly share data with the correct URL
      const frontendShareUrl = `${window.location.origin}/shared-records/${backendData.encrypted_token}`
      
      const data: ShareLinkData = {
        ...backendData,
        share_url: frontendShareUrl
      }
      
      setShareData(data)
      
      toast({
        title: '🔗 Share link generated',
        description: `Secure share link created. Expires in ${data.working_days_remaining} working days.`,
      })
      
      // Refresh history if we're on that tab
      if (activeTab === 'history') {
        loadSharingHistory()
      }
    } catch (error: any) {
      console.error('Failed to generate share link:', error)
      
      let errorMessage = 'An error occurred while generating the share link.'
      if (error.response?.status === 403) {
        errorMessage = 'Permission denied. You may not have permission to share this record.'
      } else if (error.response?.status === 404) {
        errorMessage = 'Record not found or API endpoint unavailable.'
      } else if (error.response?.status === 401) {
        errorMessage = 'Authentication failed. Please try logging in again.'
      } else if (error.response?.data?.error) {
        errorMessage = error.response.data.error
      }
      
      toast({
        title: 'Failed to generate share link',
        description: errorMessage,
        variant: 'destructive',
      })
    } finally {
      setIsGenerating(false)
    }
  }

  const loadSharingHistory = async () => {
    setIsLoadingHistory(true)
    try {
      const response = await recordsApi.getSharingHistory(pipelineId, recordId)
      setSharingHistory(response.data.results || response.data)
    } catch (error: any) {
      console.error('Failed to load sharing history:', error)
      toast({
        title: 'Failed to load sharing history',
        description: error.response?.data?.error || 'An error occurred while loading the sharing history.',
        variant: 'destructive',
      })
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const loadAccessLogs = async (shareId: string) => {
    setIsLoadingLogs(true)
    try {
      const response = await recordsApi.getShareAccessLogs(shareId)
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
    try {
      await recordsApi.revokeShare(shareId)
      toast({
        title: '✅ Share link revoked',
        description: 'The share link has been revoked and is no longer accessible.',
      })
      // Refresh the history
      loadSharingHistory()
      if (selectedShare?.id === shareId) {
        setSelectedShare(null)
      }
    } catch (error: any) {
      console.error('Failed to revoke share:', error)
      toast({
        title: 'Failed to revoke share',
        description: error.response?.data?.error || 'An error occurred while revoking the share link.',
        variant: 'destructive',
      })
    }
  }

  const copyToClipboard = async (text: string, isShareHistory = false, shareId?: string) => {
    try {
      await navigator.clipboard.writeText(text)
      
      if (isShareHistory && shareId) {
        setCopiedShareId(shareId)
        setTimeout(() => setCopiedShareId(null), 3000)
      } else {
        setCopied(true)
        setTimeout(() => setCopied(false), 3000)
      }
      
      toast({
        title: '📋 Copied to clipboard',
        description: 'Share link has been copied to your clipboard.',
      })
    } catch (error) {
      toast({
        title: 'Failed to copy',
        description: 'Could not copy share link to clipboard.',
        variant: 'destructive',
      })
    }
  }

  const copyShareLink = async (share: SharedRecordItem) => {
    if (share.encrypted_token) {
      const shareUrl = `${window.location.origin}/shared-records/${share.encrypted_token}`
      await copyToClipboard(shareUrl, true, share.id)
    } else {
      toast({
        title: 'Share link unavailable',
        description: 'The encrypted token is not available for this share link.',
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

  const formatExpiryDate = (expiryTimestamp: number) => {
    const date = new Date(expiryTimestamp * 1000)
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
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

  const getStatusBadge = (share: SharedRecordItem) => {
    switch (share.status) {
      case 'active':
        return <Badge variant="default" className="bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">Active</Badge>
      case 'expired':
        return <Badge variant="secondary" className="bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400">Expired</Badge>
      case 'revoked':
        return <Badge variant="destructive">Revoked</Badge>
      case 'inactive':
        return <Badge variant="outline">Inactive</Badge>
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

  const previewSharedRecord = () => {
    if (shareData?.encrypted_token) {
      const frontendUrl = `${window.location.origin}/shared-records/${shareData.encrypted_token}`
      window.open(frontendUrl, '_blank')
    }
  }

  useEffect(() => {
    if (isOpen && activeTab === 'history') {
      loadSharingHistory()
    }
  }, [isOpen, activeTab, pipelineId, recordId])

  const defaultTrigger = (
    <PermissionGuard
      category="sharing"
      action="create_shared_views"
      fallback={
        <Button 
          variant={variant} 
          size={size} 
          className={`${className} opacity-50 cursor-not-allowed`}
          disabled={true}
          title="You don't have permission to share records"
        >
          <Share2 className="w-4 h-4 mr-2" />
          Share
        </Button>
      }
    >
      <Button 
        variant={variant} 
        size={size} 
        className={className}
      >
        <Share2 className="w-4 h-4 mr-2" />
        Share
      </Button>
    </PermissionGuard>
  )

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {trigger || defaultTrigger}
      </DialogTrigger>
      
      <DialogContent className="sm:max-w-4xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center">
            <Shield className="w-5 h-5 mr-2 text-blue-600" />
            Share {pipelineName}
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
                    You don't have permission to share records. Contact your administrator to request access.
                  </p>
                </div>
              }
            >
            <div className="space-y-4">
              {!shareData ? (
                // Initial state - generate link
                <div className="text-center py-8">
                  <Share2 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    Share this record securely
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
                      value={recipientEmail}
                      onChange={(e) => setRecipientEmail(e.target.value)}
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
                        onClick={() => setAccessMode('editable')}
                        className={`p-4 border rounded-lg text-left transition-all ${
                          accessMode === 'editable'
                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center space-x-2 mb-2">
                          <Edit className={`w-5 h-5 ${accessMode === 'editable' ? 'text-blue-600' : 'text-gray-400'}`} />
                          <span className={`font-medium ${accessMode === 'editable' ? 'text-blue-900 dark:text-blue-100' : 'text-gray-900 dark:text-white'}`}>
                            Editable
                          </span>
                        </div>
                        <p className={`text-sm ${accessMode === 'editable' ? 'text-blue-700 dark:text-blue-300' : 'text-gray-500 dark:text-gray-400'}`}>
                          Recipients can view and update the record data
                        </p>
                      </button>
                      
                      <button
                        onClick={() => setAccessMode('readonly')}
                        className={`p-4 border rounded-lg text-left transition-all ${
                          accessMode === 'readonly'
                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center space-x-2 mb-2">
                          <Lock className={`w-5 h-5 ${accessMode === 'readonly' ? 'text-blue-600' : 'text-gray-400'}`} />
                          <span className={`font-medium ${accessMode === 'readonly' ? 'text-blue-900 dark:text-blue-100' : 'text-gray-900 dark:text-white'}`}>
                            Read-only
                          </span>
                        </div>
                        <p className={`text-sm ${accessMode === 'readonly' ? 'text-blue-700 dark:text-blue-300' : 'text-gray-500 dark:text-gray-400'}`}>
                          Recipients can only view the record data
                        </p>
                      </button>
                    </div>
                  </div>
                  
                  <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
                    <div className="flex items-start space-x-3">
                      <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                      <div className="text-left">
                        <h4 className="text-sm font-medium text-blue-900 dark:text-blue-100">
                          Secure Sharing Features:
                        </h4>
                        <ul className="text-sm text-blue-700 dark:text-blue-300 mt-1 space-y-1">
                          <li>• End-to-end encrypted link</li>
                          <li>• Restricted to specific email address only</li>
                          <li>• Requires name and email for access</li>
                          <li>• Automatic expiry after 5 working days</li>
                          <li>• Complete access tracking and analytics</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                  
                  <Button 
                    onClick={() => generateShareLink(accessMode)} 
                    disabled={isGenerating || !recipientEmail.trim() || !recipientEmail.includes('@')}
                    className="w-full"
                  >
                    {isGenerating ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Generating secure link...
                      </>
                    ) : (
                      <>
                        <Share2 className="w-4 h-4 mr-2" />
                        Generate {accessMode === 'readonly' ? 'Read-only' : 'Editable'} Share Link
                      </>
                    )}
                  </Button>
                </div>
              ) : (
                // Share link generated - show details and actions
                <div className="space-y-4">
                  <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                    <div className="flex items-center space-x-2 mb-2">
                      <Check className="w-5 h-5 text-green-600" />
                      <span className="font-medium text-green-800 dark:text-green-200">
                        Secure share link generated!
                      </span>
                    </div>
                    <p className="text-sm text-green-700 dark:text-green-300">
                      Your encrypted share link is ready. Recipients will need to provide their name and email to access.
                    </p>
                  </div>

                  {/* Share URL Display */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Share Link:
                    </label>
                    <div className="flex items-center space-x-2">
                      <input
                        type="text"
                        readOnly
                        value={shareData.share_url}
                        className="flex-1 px-3 py-2 text-sm bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                      <Button
                        onClick={() => copyToClipboard(shareData.share_url)}
                        size="sm"
                        variant="outline"
                        className="flex-shrink-0"
                      >
                        {copied ? (
                          <Check className="w-4 h-4 text-green-600" />
                        ) : (
                          <Copy className="w-4 h-4" />
                        )}
                      </Button>
                    </div>
                  </div>

                  {/* Expiry Information */}
                  <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
                    <div className="flex items-center space-x-2">
                      <Clock className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                      <div className="text-sm">
                        <span className="font-medium text-amber-800 dark:text-amber-200">
                          Expires: {formatExpiryDate(shareData.expires_at)}
                        </span>
                        <div className="text-amber-700 dark:text-amber-300">
                          {shareData.working_days_remaining} working days remaining
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-2">
                    <Button
                      onClick={() => copyToClipboard(shareData.share_url)}
                      variant="default"
                      className="flex-1"
                      disabled={copied}
                    >
                      {copied ? (
                        <>
                          <Check className="w-4 h-4 mr-2 text-green-600" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="w-4 h-4 mr-2" />
                          Copy Link
                        </>
                      )}
                    </Button>
                    
                    <Button
                      onClick={previewSharedRecord}
                      variant="outline"
                      className="flex-1"
                    >
                      <ExternalLink className="w-4 h-4 mr-2" />
                      Preview
                    </Button>
                  </div>

                  {/* Reset option */}
                  <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                    <Button
                      onClick={() => {
                        setShareData(null)
                        setRecipientEmail('')
                      }}
                      variant="ghost"
                      size="sm"
                      className="w-full text-gray-500 hover:text-gray-700"
                    >
                      Generate New Link
                    </Button>
                  </div>
                </div>
              )}
            </div>
            </PermissionGuard>
          </TabsContent>
          
          <TabsContent value="history" className="flex-1 overflow-hidden">
            <div className="h-full overflow-hidden">
              {!selectedShare ? (
                // Main history list view
                <div className="space-y-4 h-full overflow-y-auto">
                  <div className="flex justify-between items-center">
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Track all share links created for this record and see who has accessed them
                    </p>
                    <Button
                      onClick={loadSharingHistory}
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
                      <span className="ml-3 text-gray-600 dark:text-gray-400">Loading sharing history...</span>
                    </div>
                  ) : sharingHistory.length === 0 ? (
                    <div className="text-center py-12">
                      <Share2 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                        No sharing history
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                        This record hasn't been shared yet.
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
                      {sharingHistory.map((share) => (
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
                                  {share.access_mode === 'readonly' ? 'Read-only' : 'Editable'} Share
                                </span>
                                {getStatusBadge(share)}
                              </div>
                              
                              <div className="grid grid-cols-2 gap-4 text-sm text-gray-600 dark:text-gray-400">
                                <div className="flex items-center space-x-2">
                                  <Calendar className="w-4 h-4" />
                                  <span>Created {formatDate(share.created_at)}</span>
                                </div>
                                <div className="flex items-center space-x-2">
                                  <Clock className="w-4 h-4" />
                                  <span>
                                    {share.status === 'expired' 
                                      ? `Expired ${formatDate(share.expires_at)}`
                                      : share.status === 'revoked'
                                      ? `Revoked ${formatDate(share.revoked_at || '')}`
                                      : formatTimeRemaining(share.time_remaining_seconds)
                                    }
                                  </span>
                                </div>
                                <div className="flex items-center space-x-2">
                                  <Users className="w-4 h-4" />
                                  <span>Shared by {share.shared_by_name}</span>
                                </div>
                                <div className="flex items-center space-x-2">
                                  <Activity className="w-4 h-4" />
                                  <span>{share.access_count} access{share.access_count !== 1 ? 'es' : ''}</span>
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
                                        variant="ghost"
                                        size="sm"
                                        className="text-gray-400 cursor-not-allowed opacity-50"
                                        disabled={true}
                                        title="You don't have permission to revoke shares"
                                      >
                                        <Ban className="w-4 h-4" />
                                      </Button>
                                    }
                                  >
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
                                  </PermissionGuard>
                                </>
                              )}
                              <ExternalLink className="w-4 h-4 text-gray-400" />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                // Detailed view for selected share
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
                      <span className="font-medium">{selectedShare.access_mode === 'readonly' ? 'Read-only' : 'Editable'} Share</span>
                      {getStatusBadge(selectedShare)}
                    </div>
                  </div>

                  <Separator />

                  {/* Share Details */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-3">
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Created</label>
                        <p className="text-sm text-gray-600 dark:text-gray-400">{formatDate(selectedShare.created_at)}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Shared by</label>
                        <p className="text-sm text-gray-600 dark:text-gray-400">{selectedShare.shared_by_name}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Total Accesses</label>
                        <p className="text-sm text-gray-600 dark:text-gray-400">{selectedShare.access_count}</p>
                      </div>
                    </div>
                    <div className="space-y-3">
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
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Status</label>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {selectedShare.status === 'expired' 
                            ? `Expired ${formatDate(selectedShare.expires_at)}`
                            : selectedShare.status === 'revoked'
                            ? `Revoked ${formatDate(selectedShare.revoked_at || '')}`
                            : selectedShare.status === 'active'
                            ? formatTimeRemaining(selectedShare.time_remaining_seconds)
                            : selectedShare.status
                          }
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
                          People who have accessed this shared record
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
                                variant="outline"
                                size="sm"
                                className="text-gray-400 cursor-not-allowed opacity-50"
                                disabled={true}
                                title="You don't have permission to revoke shares"
                              >
                                <Ban className="w-4 h-4 mr-2" />
                                Revoke (No permission)
                              </Button>
                            }
                          >
                            <Button
                              onClick={() => revokeShare(selectedShare.id)}
                              variant="destructive"
                              size="sm"
                            >
                              <Ban className="w-4 h-4 mr-2" />
                              Revoke
                            </Button>
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
                        <p className="text-sm text-gray-500 dark:text-gray-400">No one has accessed this shared record yet</p>
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
              )}
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}