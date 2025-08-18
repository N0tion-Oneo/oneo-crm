'use client'

import { useState, useEffect } from 'react'
import { Plus, MessageSquare, CheckCircle, AlertCircle, ExternalLink, Trash2, RotateCcw, Shield, RefreshCw, Settings, TrendingUp } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/features/auth/context'
import { useContactResolution } from '@/hooks/use-contact-resolution'
import { communicationsApi } from '@/lib/api'

interface ChannelConnection {
  id: string
  channelType: string
  accountName: string
  authStatus: string
  accountStatus: string
  externalAccountId: string
  hostedAuthUrl?: string
  lastActiveAt?: string
  createdAt: string
  statusInfo?: {
    status: string
    display: string
    can_send: boolean
    needs_action: boolean
    action_type?: string
    message: string
  }
  canSendMessages?: boolean
  lastError?: string
  checkpointData?: any
  messagesSentToday?: number
  rateLimitPerHour?: number
}

interface HostedAuthResponse {
  url: string
  account_id?: string
}

export default function CommunicationsPage() {
  const [connections, setConnections] = useState<ChannelConnection[]>([])
  const [loading, setLoading] = useState(true)
  const [addAccountOpen, setAddAccountOpen] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState<string>('')
  const [connecting, setConnecting] = useState(false)
  
  // Checkpoint resolution state
  const [checkpointDialogOpen, setCheckpointDialogOpen] = useState(false)
  const [selectedConnection, setSelectedConnection] = useState<ChannelConnection | null>(null)
  const [verificationCode, setVerificationCode] = useState('')
  const [submittingCode, setSubmittingCode] = useState(false)
  
  const { toast } = useToast()
  const { tenant, user, isAuthenticated, isLoading: authLoading } = useAuth()
  
  // Contact resolution hook for unmatched count
  const { unmatchedCount, warningsCount } = useContactResolution()

  const providers = [
    { value: 'linkedin', label: 'LinkedIn', icon: '💼' },
    { value: 'gmail', label: 'Gmail', icon: '📧' },
    { value: 'outlook', label: 'Outlook', icon: '📧' },
    { value: 'mail', label: 'Email (Generic)', icon: '📬' },
    { value: 'whatsapp', label: 'WhatsApp', icon: '💬' },
    { value: 'instagram', label: 'Instagram', icon: '📷' },
    { value: 'messenger', label: 'Facebook Messenger', icon: '💬' },
    { value: 'telegram', label: 'Telegram', icon: '✈️' },
    { value: 'twitter', label: 'Twitter/X', icon: '🐦' },
  ]

  // Load existing connections
  useEffect(() => {
    // Only load connections if user is authenticated and auth is not loading
    if (isAuthenticated && !authLoading && user && tenant) {
      loadConnections()
    } else if (!isAuthenticated && !authLoading) {
      // User is not authenticated, stop loading
      setLoading(false)
      setConnections([])
    }
  }, [isAuthenticated, authLoading, user, tenant])

  const loadConnections = async () => {
    try {
      // Debug authentication state
      const hasToken = document.cookie.includes('oneo_access_token')
      const hasTenant = document.cookie.includes('oneo_tenant')
      
      console.log('🔐 Debug - Auth state before API call:', {
        hasAccessToken: hasToken,
        hasTenantCookie: hasTenant,
        isAuthenticated: isAuthenticated,
        user: user?.email,
        tenant: tenant?.name || tenant?.schemaName
      })
      
      const response = await communicationsApi.getConnections()
      setConnections(response.data.results || response.data || [])
    } catch (error: any) {
      console.error('Error loading connections:', error)
      setConnections([])
      
      // Show user-friendly error for debugging
      const status = error.response?.status || 'Unknown'
      const statusText = error.response?.statusText || error.message || 'Connection failed'
      
      // Enhanced error logging
      console.error('🚨 API Error Details:', {
        status,
        statusText,
        response: error.response?.data,
        config: {
          url: error.config?.url,
          method: error.config?.method,
          headers: error.config?.headers
        }
      })
      
      if (status === 404) {
        console.error('API endpoint not found - check backend routing')
      } else if (status === 401) {
        console.error('Authentication failed - check JWT tokens')
      } else if (status === 500) {
        console.error('Server error - check backend logs')
      }
      
      toast({
        title: "Failed to load connections",
        description: `Error: ${status} ${statusText}`,
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleAddAccount = async () => {
    if (!selectedProvider) {
      toast({
        title: "Provider Required",
        description: "Please select a communication provider.",
        variant: "destructive",
      })
      return
    }

    setConnecting(true)
    try {
      // Request hosted authentication URL
      const response = await communicationsApi.requestHostedAuth({
        providers: [selectedProvider],
        success_redirect_url: `${window.location.origin}/communications?success=true`,
        failure_redirect_url: `${window.location.origin}/communications?error=true`,
        name: `${tenant?.name || 'User'} ${selectedProvider} Account`
      })

      const data: HostedAuthResponse = response.data
      if (data.url) {
        // Open hosted auth in new window
        window.open(data.url, '_blank', 'width=600,height=700,scrollbars=yes,resizable=yes')
        
        setAddAccountOpen(false)
        setSelectedProvider('')
        
        toast({
          title: "Authentication Started",
          description: "Complete the authentication in the new window, then refresh this page.",
        })
      } else {
        throw new Error('No authentication URL received')
      }
    } catch (error) {
      console.error('Error requesting hosted auth:', error)
      toast({
        title: "Connection Failed",
        description: error instanceof Error ? error.message : "Failed to start authentication process.",
        variant: "destructive",
      })
    } finally {
      setConnecting(false)
    }
  }

  const handleRemoveConnection = async (connectionId: string) => {
    if (!confirm('Are you sure you want to remove this connection?')) {
      return
    }

    try {
      await communicationsApi.deleteConnection(connectionId)
      
      setConnections(prev => prev.filter(conn => conn.id !== connectionId))
      toast({
        title: "Connection Removed",
        description: "The communication account has been removed.",
      })
    } catch (error) {
      console.error('Error removing connection:', error)
      toast({
        title: "Removal Failed",
        description: "Failed to remove the connection. Please try again.",
        variant: "destructive",
      })
    }
  }

  const handleCheckpointAction = (connection: ChannelConnection) => {
    setSelectedConnection(connection)
    setCheckpointDialogOpen(true)
    setVerificationCode('')
  }

  const handleSubmitCheckpoint = async () => {
    if (!selectedConnection || !verificationCode.trim()) {
      toast({
        title: "Verification Code Required",
        description: "Please enter the verification code.",
        variant: "destructive",
      })
      return
    }

    setSubmittingCode(true)
    try {
      await communicationsApi.solveCheckpoint(selectedConnection.id, {
        code: verificationCode.trim()
      })
      
      toast({
        title: "Account Verified",
        description: "Your account has been successfully verified!",
      })
      
      setCheckpointDialogOpen(false)
      setSelectedConnection(null)
      setVerificationCode('')
      loadConnections() // Refresh connections
    } catch (error) {
      console.error('Error submitting checkpoint:', error)
      toast({
        title: "Verification Failed",
        description: error instanceof Error ? error.message : "Failed to verify account. Please try again.",
        variant: "destructive",
      })
    } finally {
      setSubmittingCode(false)
    }
  }

  const handleResendCheckpoint = async () => {
    if (!selectedConnection) return

    try {
      await communicationsApi.resendCheckpoint(selectedConnection.id)
      
      toast({
        title: "Code Sent",
        description: "A new verification code has been sent.",
      })
    } catch (error) {
      console.error('Error resending checkpoint:', error)
      toast({
        title: "Resend Failed",
        description: error instanceof Error ? error.message : "Failed to resend verification code.",
        variant: "destructive",
      })
    }
  }

  const handleReconnect = async (connection: ChannelConnection) => {
    try {
      const response = await communicationsApi.requestHostedAuth({
        providers: [connection.channelType],
        account_id: connection.externalAccountId,
        success_redirect_url: `${window.location.origin}/communications?reconnect=true`,
        failure_redirect_url: `${window.location.origin}/communications?error=true`,
        name: connection.accountName
      })
      
      const data: HostedAuthResponse = response.data
      if (data.url) {
        window.open(data.url, '_blank', 'width=600,height=700,scrollbars=yes,resizable=yes')
        
        toast({
          title: "Reconnection Started",
          description: "Complete the reconnection in the new window, then refresh this page.",
        })
      } else {
        throw new Error('Failed to request reconnection')
      }
    } catch (error) {
      console.error('Error requesting reconnection:', error)
      toast({
        title: "Reconnection Failed",
        description: "Failed to start reconnection process.",
        variant: "destructive",
      })
    }
  }

  const getStatusBadge = (connection: ChannelConnection) => {
    const { authStatus, accountStatus, statusInfo } = connection
    
    // Use enhanced status info if available
    if (statusInfo) {
      if (statusInfo.can_send && authStatus === 'authenticated' && accountStatus === 'active') {
        return <Badge variant="default" className="bg-green-100 text-green-800"><CheckCircle className="w-3 h-3 mr-1" />Connected</Badge>
      } else if (statusInfo.needs_action) {
        if (statusInfo.action_type === 'checkpoint') {
          return <Badge variant="secondary" className="bg-yellow-100 text-yellow-800"><Shield className="w-3 h-3 mr-1" />Verify Account</Badge>
        } else if (statusInfo.action_type === 'reconnect') {
          return <Badge variant="destructive"><AlertCircle className="w-3 h-3 mr-1" />Reconnect Required</Badge>
        } else if (statusInfo.action_type === 'complete_auth') {
          return <Badge variant="outline" className="bg-blue-100 text-blue-800"><ExternalLink className="w-3 h-3 mr-1" />Complete Auth</Badge>
        }
      }
    }
    
    // Fallback to basic status check
    if (authStatus === 'authenticated' && accountStatus === 'active') {
      return <Badge variant="default" className="bg-green-100 text-green-800"><CheckCircle className="w-3 h-3 mr-1" />Connected</Badge>
    } else if (accountStatus === 'checkpoint_required') {
      return <Badge variant="secondary" className="bg-yellow-100 text-yellow-800"><Shield className="w-3 h-3 mr-1" />Verification Required</Badge>
    } else if (accountStatus === 'pending') {
      return <Badge variant="outline" className="bg-blue-100 text-blue-800"><RefreshCw className="w-3 h-3 mr-1" />Connecting...</Badge>
    } else {
      return <Badge variant="destructive"><AlertCircle className="w-3 h-3 mr-1" />Disconnected</Badge>
    }
  }

  const getProviderIcon = (channelType: string) => {
    const provider = providers.find(p => p.value === channelType)
    return provider?.icon || '📢'
  }

  // Check for success/error URL params
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    
    if (urlParams.get('success') === 'true') {
      toast({
        title: "Account Connected",
        description: "Your communication account has been successfully connected!",
      })
      loadConnections() // Refresh connections
      // Clean up URL
      window.history.replaceState({}, '', '/communications')
    } else if (urlParams.get('reconnect') === 'true') {
      toast({
        title: "Account Reconnected",
        description: "Your communication account has been successfully reconnected!",
      })
      loadConnections() // Refresh connections
      window.history.replaceState({}, '', '/communications')
    } else if (urlParams.get('error') === 'true') {
      toast({
        title: "Connection Failed",
        description: "There was an error connecting your account. Please try again.",
        variant: "destructive",
      })
      window.history.replaceState({}, '', '/communications')
    }
  }, [toast])

  if (loading) {
    return (
      <div className="p-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading communication accounts...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Communications</h1>
            <p className="text-gray-600 dark:text-gray-400">Manage your communication account connections</p>
          </div>
          
          <div className="flex space-x-2">
            <Link href="/communications/inbox">
              <Button variant="outline" className="relative">
                <MessageSquare className="w-4 h-4 mr-2" />
                Inbox
                {(unmatchedCount > 0 || warningsCount > 0) && (
                  <Badge 
                    variant="destructive" 
                    className="absolute -top-2 -right-2 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs"
                  >
                    {unmatchedCount + warningsCount}
                  </Badge>
                )}
              </Button>
            </Link>
            
            <Link href="/communications/analytics">
              <Button variant="outline">
                <TrendingUp className="w-4 h-4 mr-2" />
                Analytics
              </Button>
            </Link>
            
            <Link href="/communications/settings">
              <Button variant="outline">
                <Settings className="w-4 h-4 mr-2" />
                Settings
              </Button>
            </Link>
            
            <Dialog open={addAccountOpen} onOpenChange={setAddAccountOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Account
                </Button>
              </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add Communication Account</DialogTitle>
                <DialogDescription>
                  Connect a new communication account to send and receive messages.
                </DialogDescription>
              </DialogHeader>
              
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Provider</label>
                  <Select value={selectedProvider} onValueChange={setSelectedProvider}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a communication provider" />
                    </SelectTrigger>
                    <SelectContent>
                      {providers.map((provider) => (
                        <SelectItem key={provider.value} value={provider.value}>
                          <div className="flex items-center">
                            <span className="mr-2">{provider.icon}</span>
                            {provider.label}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div className="flex justify-end space-x-2">
                <Button variant="outline" onClick={() => setAddAccountOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleAddAccount} disabled={connecting || !selectedProvider}>
                  {connecting ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Connecting...
                    </>
                  ) : (
                    <>
                      <ExternalLink className="w-4 h-4 mr-2" />
                      Connect Account
                    </>
                  )}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
          </div>
        </div>

        {connections.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <MessageSquare className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No accounts connected</h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Connect your communication accounts to start sending and receiving messages.
              </p>
              <Button onClick={() => setAddAccountOpen(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Add Your First Account
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {connections.map((connection) => (
              <Card key={connection.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="text-2xl">
                        {getProviderIcon(connection.channelType)}
                      </div>
                      <div>
                        <CardTitle className="text-lg">{connection.accountName}</CardTitle>
                        <CardDescription className="capitalize">
                          {connection.channelType} Account
                        </CardDescription>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {getStatusBadge(connection)}
                      <div className="flex space-x-1">
                        {/* Checkpoint action button */}
                        {connection.statusInfo?.action_type === 'checkpoint' && (
                          <Button
                            variant="default"
                            size="sm"
                            onClick={() => handleCheckpointAction(connection)}
                            className="bg-yellow-600 hover:bg-yellow-700"
                          >
                            <Shield className="w-4 h-4" />
                          </Button>
                        )}
                        
                        {/* Reconnect button for failed/expired connections */}
                        {(connection.statusInfo?.needs_action && connection.statusInfo?.action_type === 'reconnect') ||
                         (connection.authStatus !== 'authenticated' || connection.accountStatus !== 'active') && connection.accountStatus !== 'checkpoint_required' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleReconnect(connection)}
                          >
                            <RotateCcw className="w-4 h-4" />
                          </Button>
                        )}
                        
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRemoveConnection(connection.id)}
                          className="text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="font-medium text-gray-500 dark:text-gray-400">Account ID:</span>
                        <p className="font-mono text-xs mt-1">{connection.externalAccountId || 'Pending...'}</p>
                      </div>
                      <div>
                        <span className="font-medium text-gray-500 dark:text-gray-400">Connected:</span>
                        <p className="mt-1">{new Date(connection.createdAt).toLocaleDateString()}</p>
                      </div>
                      {connection.lastActiveAt && (
                        <div className="col-span-2">
                          <span className="font-medium text-gray-500 dark:text-gray-400">Last Active:</span>
                          <p className="mt-1">{new Date(connection.lastActiveAt).toLocaleString()}</p>
                        </div>
                      )}
                    </div>
                    
                    {/* Additional status information */}
                    {connection.statusInfo?.message && (
                      <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-md">
                        <p className="text-sm text-gray-700 dark:text-gray-300">{connection.statusInfo.message}</p>
                      </div>
                    )}
                    
                    {/* Error message */}
                    {connection.lastError && (
                      <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-md">
                        <p className="text-sm text-red-700 dark:text-red-300">{connection.lastError}</p>
                      </div>
                    )}
                    
                    {/* Usage information for active connections */}
                    {connection.canSendMessages && connection.messagesSentToday !== undefined && (
                      <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
                        <span>Messages today: {connection.messagesSentToday}/{connection.rateLimitPerHour}</span>
                        <span className={connection.canSendMessages ? 'text-green-600' : 'text-red-600'}>
                          {connection.canSendMessages ? 'Can send messages' : 'Rate limited'}
                        </span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Refresh button */}
        <div className="mt-6 text-center">
          <Button variant="outline" onClick={loadConnections}>
            <RotateCcw className="w-4 h-4 mr-2" />
            Refresh Connections
          </Button>
        </div>
        
        {/* Checkpoint Resolution Dialog */}
        <Dialog open={checkpointDialogOpen} onOpenChange={setCheckpointDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Account Verification Required</DialogTitle>
              <DialogDescription>
                {selectedConnection?.accountName} requires verification to continue. Please enter the verification code sent to your account.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              {selectedConnection?.checkpointData?.message && (
                <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md">
                  <p className="text-sm text-blue-800 dark:text-blue-200">
                    {selectedConnection.checkpointData.message}
                  </p>
                </div>
              )}
              
              <div className="space-y-2">
                <Label htmlFor="verification-code">Verification Code</Label>
                <Input
                  id="verification-code"
                  type="text"
                  placeholder="Enter 6-digit code"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value)}
                  maxLength={10}
                  className="text-center text-lg tracking-wider"
                />
              </div>
            </div>
            
            <div className="flex justify-between">
              <Button
                variant="outline"
                onClick={handleResendCheckpoint}
                disabled={submittingCode}
              >
                Resend Code
              </Button>
              
              <div className="flex space-x-2">
                <Button 
                  variant="outline" 
                  onClick={() => {
                    setCheckpointDialogOpen(false)
                    setSelectedConnection(null)
                    setVerificationCode('')
                  }}
                >
                  Cancel
                </Button>
                <Button 
                  onClick={handleSubmitCheckpoint} 
                  disabled={submittingCode || !verificationCode.trim()}
                >
                  {submittingCode ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Verifying...
                    </>
                  ) : (
                    <>
                      <Shield className="w-4 h-4 mr-2" />
                      Verify Account
                    </>
                  )}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  )
}