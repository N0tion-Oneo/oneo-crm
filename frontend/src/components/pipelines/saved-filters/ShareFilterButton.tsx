'use client'

import { useState } from 'react'
import { Share2, Copy, Check, ExternalLink, Clock, Shield, Eye, Edit, Lock } from 'lucide-react'
import { savedFiltersApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { toast } from '@/hooks/use-toast'
import { SavedFilter } from './SavedFiltersList'

interface ShareFilterButtonProps {
  filter: SavedFilter
  className?: string
  variant?: 'default' | 'outline' | 'ghost'
  size?: 'default' | 'sm' | 'lg'
}

interface ShareLinkData {
  share_url: string
  encrypted_token: string
  expires_at: number
  expires_datetime: string
  time_remaining: number
  sharing_enabled: boolean
}

export function ShareFilterButton({
  filter,
  className = '',
  variant = 'outline',
  size = 'default'
}: ShareFilterButtonProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [shareData, setShareData] = useState<ShareLinkData | null>(null)
  const [copied, setCopied] = useState(false)
  const [accessMode, setAccessMode] = useState<'readonly' | 'filtered_edit'>('readonly')
  const [selectedFields, setSelectedFields] = useState<string[]>([])
  const [recipientEmail, setRecipientEmail] = useState('')

  const generateShareLink = async (mode: 'readonly' | 'filtered_edit') => {
    setIsGenerating(true)
    
    // Validate email before proceeding
    const trimmedEmail = recipientEmail.trim()
    if (!trimmedEmail || !trimmedEmail.includes('@')) {
      toast({
        title: 'Email Required',
        description: 'Please enter a valid recipient email address.',
        variant: 'destructive',
      })
      setIsGenerating(false)
      return
    }
    
    console.log('=== SHARE FILTER REQUEST DEBUG ===')
    console.log('Filter ID:', filter.id)
    console.log('Access Mode:', mode)
    console.log('Selected Fields:', selectedFields)
    console.log('Recipient Email:', trimmedEmail)
    
    try {
      const payload = {
        intended_recipient_email: trimmedEmail,
        access_mode: mode,
        expires_at: new Date(Date.now() + (7 * 24 * 60 * 60 * 1000)).toISOString(), // 7 days from now
        shared_fields: selectedFields.length > 0 ? selectedFields : (filter.shareable_fields || [])
      }

      console.log('Share payload:', payload)
      
      const response = await savedFiltersApi.share(filter.id, payload)
      console.log('Share filter API call successful:', response)
      
      const backendData = response.data
      
      // Create frontend-friendly share data with the correct URL
      const frontendShareUrl = `${window.location.origin}/shared/filter/${backendData.encrypted_token}`
      
      const data: ShareLinkData = {
        ...backendData,
        share_url: frontendShareUrl // Override with frontend URL for user-friendly sharing
      }
      
      setShareData(data)
      
      toast({
        title: '🔗 Share link generated',
        description: `Secure filter share link created. Expires in 7 days.`,
      })
    } catch (error: any) {
      console.error('Failed to generate share link:', error)
      console.error('Error response:', error.response)
      console.error('Error data:', error.response?.data)
      
      let errorMessage = 'An error occurred while generating the share link.'
      if (error.response?.status === 403) {
        errorMessage = 'Permission denied. You may not have permission to share this filter.'
      } else if (error.response?.status === 404) {
        errorMessage = 'Filter not found or API endpoint unavailable.'
      } else if (error.response?.status === 401) {
        errorMessage = 'Authentication failed. Please try logging in again.'
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error.response?.data) {
        // Try to get any error message from response data
        const errorData = error.response.data
        if (typeof errorData === 'string') {
          errorMessage = errorData
        } else if (errorData.error) {
          errorMessage = errorData.error
        } else if (errorData.message) {
          errorMessage = errorData.message
        } else {
          errorMessage = JSON.stringify(errorData)
        }
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

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      toast({
        title: '📋 Copied to clipboard',
        description: 'Share link has been copied to your clipboard.',
      })
      
      setTimeout(() => setCopied(false), 3000)
    } catch (error) {
      toast({
        title: 'Failed to copy',
        description: 'Could not copy share link to clipboard.',
        variant: 'destructive',
      })
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

  const previewSharedFilter = () => {
    if (shareData?.encrypted_token) {
      const frontendUrl = `${window.location.origin}/shared/filter/${shareData.encrypted_token}`
      window.open(frontendUrl, '_blank')
    }
  }

  const handleFieldToggle = (fieldSlug: string) => {
    setSelectedFields(prev => 
      prev.includes(fieldSlug)
        ? prev.filter(f => f !== fieldSlug)
        : [...prev, fieldSlug]
    )
  }

  // Initialize selected fields when modal opens
  const handleModalOpen = () => {
    setSelectedFields((filter.shareable_fields || []).slice()) // Make a copy to avoid mutations
    setIsOpen(true)
  }

  // Don't render if filter can't be shared
  if (!filter.can_share?.allowed) {
    return null
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button 
          variant={variant} 
          size={size} 
          className={className}
          onClick={handleModalOpen}
        >
          <Share2 className="w-4 h-4 mr-2" />
          Share
        </Button>
      </DialogTrigger>
      
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center">
            <Shield className="w-5 h-5 mr-2 text-orange-600" />
            Share Filter: {filter.name}
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          {!shareData ? (
            // Initial state - generate link
            <div className="text-center py-8">
              <Share2 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                Share this filter securely
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                Generate a secure, encrypted share link that expires automatically after 7 days.
              </p>
              
              {/* Recipient Email */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Recipient Email <span className="text-red-500">*</span>
                </label>
                <input
                  type="email"
                  required
                  value={recipientEmail}
                  onChange={(e) => setRecipientEmail(e.target.value)}
                  placeholder="Enter recipient's email address..."
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  The recipient will need this email to access the shared filter
                </p>
              </div>
              
              {/* Field Selection */}
              {filter.shareable_fields && filter.shareable_fields.length > 0 && (
                <div className="mb-6 text-left">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                    Fields to include in share ({selectedFields.length} of {(filter.shareable_fields || []).length} selected):
                  </label>
                  <div className="max-h-32 overflow-y-auto border border-gray-300 dark:border-gray-600 rounded-md p-3 space-y-2">
                    {(filter.shareable_fields || []).map(fieldSlug => (
                      <label key={fieldSlug} className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={selectedFields.includes(fieldSlug)}
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
                    ))}
                  </div>
                  <div className="mt-2 flex space-x-2">
                    <button
                      type="button"
                      onClick={() => setSelectedFields([...(filter.shareable_fields || [])])}
                      className="text-xs text-orange-600 hover:text-orange-800 dark:text-orange-400 dark:hover:text-orange-300"
                    >
                      Select All
                    </button>
                    <span className="text-xs text-gray-400">•</span>
                    <button
                      type="button"
                      onClick={() => setSelectedFields([])}
                      className="text-xs text-orange-600 hover:text-orange-800 dark:text-orange-400 dark:hover:text-orange-300"
                    >
                      Select None
                    </button>
                  </div>
                </div>
              )}
              
              {/* Access Mode Selection */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Choose access level:
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => setAccessMode('readonly')}
                    className={`p-4 border rounded-lg text-left transition-all ${
                      accessMode === 'readonly'
                        ? 'border-orange-500 bg-orange-50 dark:bg-orange-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-center space-x-2 mb-2">
                      <Lock className={`w-5 h-5 ${accessMode === 'readonly' ? 'text-orange-600' : 'text-gray-400'}`} />
                      <span className={`font-medium ${accessMode === 'readonly' ? 'text-orange-900 dark:text-orange-100' : 'text-gray-900 dark:text-white'}`}>
                        Read-only
                      </span>
                    </div>
                    <p className={`text-sm ${accessMode === 'readonly' ? 'text-orange-700 dark:text-orange-300' : 'text-gray-500 dark:text-gray-400'}`}>
                      Recipients can only view the filtered records
                    </p>
                  </button>
                  
                  <button
                    onClick={() => setAccessMode('filtered_edit')}
                    className={`p-4 border rounded-lg text-left transition-all ${
                      accessMode === 'filtered_edit'
                        ? 'border-orange-500 bg-orange-50 dark:bg-orange-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-center space-x-2 mb-2">
                      <Edit className={`w-5 h-5 ${accessMode === 'filtered_edit' ? 'text-orange-600' : 'text-gray-400'}`} />
                      <span className={`font-medium ${accessMode === 'filtered_edit' ? 'text-orange-900 dark:text-orange-100' : 'text-gray-900 dark:text-white'}`}>
                        Filtered Edit
                      </span>
                    </div>
                    <p className={`text-sm ${accessMode === 'filtered_edit' ? 'text-orange-700 dark:text-orange-300' : 'text-gray-500 dark:text-gray-400'}`}>
                      Recipients can view and edit the filtered records
                    </p>
                  </button>
                </div>
              </div>
              
              <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4 mb-6">
                <div className="flex items-start space-x-3">
                  <Shield className="w-5 h-5 text-orange-600 dark:text-orange-400 mt-0.5 flex-shrink-0" />
                  <div className="text-left">
                    <h4 className="text-sm font-medium text-orange-900 dark:text-orange-100">
                      Secure Filter Sharing Features:
                    </h4>
                    <ul className="text-sm text-orange-700 dark:text-orange-300 mt-1 space-y-1">
                      <li>• End-to-end encrypted link</li>
                      <li>• No login required for recipients</li>
                      <li>• Automatic expiry after 7 days</li>
                      <li>• Field-level access control</li>
                      <li>• Access tracking and analytics</li>
                    </ul>
                  </div>
                </div>
              </div>
              
              <Button 
                onClick={() => generateShareLink(accessMode)} 
                disabled={
                  isGenerating || 
                  !recipientEmail || 
                  !recipientEmail.includes('@') ||
                  ((filter.shareable_fields || []).length > 0 && selectedFields.length === 0)
                }
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
                    Generate {accessMode === 'readonly' ? 'Read-only' : 'Filtered Edit'} Share Link
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
                    Secure filter share link generated!
                  </span>
                </div>
                <p className="text-sm text-green-700 dark:text-green-300">
                  Your encrypted share link is ready. Recipients can access this filtered view without logging in.
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
                    className="flex-1 px-3 py-2 text-sm bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
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
                      7 days remaining
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
                  onClick={previewSharedFilter}
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
                  onClick={() => setShareData(null)}
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
      </DialogContent>
    </Dialog>
  )
}