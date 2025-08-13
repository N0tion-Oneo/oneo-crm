'use client'

import { useState } from 'react'
import { Share2, Copy, Check, ExternalLink, Clock, Shield, Eye, Edit, Lock } from 'lucide-react'
import { recordsApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { toast } from '@/hooks/use-toast'

interface ShareRecordButtonProps {
  pipelineId: string
  recordId: string
  pipelineName?: string
  className?: string
  variant?: 'default' | 'outline' | 'ghost'
  size?: 'default' | 'sm' | 'lg'
}

interface ShareLinkData {
  share_url: string
  encrypted_token: string
  expires_at: number
  expires_datetime: string
  working_days_remaining: number
  sharing_enabled: boolean
}

export function ShareRecordButton({
  pipelineId,
  recordId,
  pipelineName = 'Record',
  className = '',
  variant = 'outline',
  size = 'default'
}: ShareRecordButtonProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [shareData, setShareData] = useState<ShareLinkData | null>(null)
  const [copied, setCopied] = useState(false)
  const [accessMode, setAccessMode] = useState<'editable' | 'readonly'>('editable')

  const generateShareLink = async (mode: 'editable' | 'readonly') => {
    setIsGenerating(true)
    
    // Debug logging before making the request
    console.log('=== SHARE LINK REQUEST DEBUG ===')
    console.log('Pipeline ID:', pipelineId)
    console.log('Record ID:', recordId)
    console.log('Access Mode:', mode)
    console.log('About to call recordsApi.generateShareLink...')
    
    try {
      const response = await recordsApi.generateShareLink(pipelineId, recordId, { access_mode: mode })
      console.log('Share link API call successful:', response)
      const backendData = response.data
      
      // Create frontend-friendly share data with the correct URL
      const frontendShareUrl = `${window.location.origin}/shared-records/${backendData.encrypted_token}`
      
      const data: ShareLinkData = {
        ...backendData,
        share_url: frontendShareUrl // Override with frontend URL for user-friendly sharing
      }
      
      setShareData(data)
      
      toast({
        title: '🔗 Share link generated',
        description: `Secure share link created. Expires in ${data.working_days_remaining} working days.`,
      })
    } catch (error: any) {
      console.error('Failed to generate share link:', error)
      
      // Enhanced error debugging with complete error object inspection
      console.log('=== COMPLETE ERROR DEBUGGING ===')
      console.log('Error object type:', typeof error)
      console.log('Error name:', error.name)
      console.log('Error message:', error.message)
      console.log('Error stack:', error.stack)
      
      // Response details
      if (error.response) {
        console.log('Response exists:', true)
        console.log('Response status:', error.response.status)
        console.log('Response statusText:', error.response.statusText)
        console.log('Response headers:', error.response.headers)
        console.log('Response data:', error.response.data)
        console.log('Response data type:', typeof error.response.data)
      } else {
        console.log('No response object:', error.response)
      }
      
      // Request details
      if (error.config) {
        console.log('Request URL:', error.config.url)
        console.log('Request method:', error.config.method)
        console.log('Request baseURL:', error.config.baseURL)
        console.log('Request headers:', error.config.headers)
        console.log('Full constructed URL:', error.config.baseURL + error.config.url)
      } else {
        console.log('No config object:', error.config)
      }
      
      // Network/other details
      if (error.request) {
        console.log('Request was made but no response received')
        console.log('Request details:', error.request)
      }
      
      console.log('=== END ERROR DEBUGGING ===')
      
      const errorInfo = {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        url: error.config?.url,
        method: error.config?.method,
        headers: error.config?.headers,
        fullUrl: error.config?.baseURL + error.config?.url
      }
      console.error('Detailed error info:', errorInfo)
      
      // Show detailed error based on status code
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

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      toast({
        title: '📋 Copied to clipboard',
        description: 'Share link has been copied to your clipboard.',
      })
      
      // Reset copied state after 3 seconds
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

  const previewSharedRecord = () => {
    if (shareData?.encrypted_token) {
      // Extract the encrypted token from the share URL and create frontend URL
      const frontendUrl = `${window.location.origin}/shared-records/${shareData.encrypted_token}`
      window.open(frontendUrl, '_blank')
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button 
          variant={variant} 
          size={size} 
          className={className}
          onClick={() => setIsOpen(true)}
        >
          <Share2 className="w-4 h-4 mr-2" />
          Share
        </Button>
      </DialogTrigger>
      
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center">
            <Shield className="w-5 h-5 mr-2 text-blue-600" />
            Share {pipelineName}
          </DialogTitle>
        </DialogHeader>
        
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
                      <li>• No login required for recipients</li>
                      <li>• Automatic expiry after 5 working days</li>
                      <li>• Access tracking and analytics</li>
                    </ul>
                  </div>
                </div>
              </div>
              
              <Button 
                onClick={() => generateShareLink(accessMode)} 
                disabled={isGenerating}
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
                  Your encrypted share link is ready. Recipients can access this record without logging in.
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