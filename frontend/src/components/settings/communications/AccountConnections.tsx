'use client'

import { useState } from 'react'
import { 
  Plus, 
  MessageSquare, 
  CheckCircle, 
  AlertCircle, 
  ExternalLink, 
  Trash2, 
  RotateCcw, 
  RefreshCw,
  Mail,
  MessageCircle,
  Settings,
  Clock
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger,
  DialogFooter
} from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useToast } from '@/hooks/use-toast'
import { communicationsApi } from '@/lib/api'
import { cn } from '@/lib/utils'

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

interface AccountConnectionsProps {
  connections: ChannelConnection[]
  onConnectionsChange: () => void
  canManage: boolean
}

const PROVIDERS = [
  { value: 'linkedin', label: 'LinkedIn', icon: MessageSquare, color: 'indigo' },
  { value: 'gmail', label: 'Gmail', icon: Mail, color: 'red' },
  { value: 'outlook', label: 'Outlook', icon: Mail, color: 'blue' },
  { value: 'mail', label: 'Email (Generic)', icon: Mail, color: 'gray' },
  { value: 'whatsapp', label: 'WhatsApp', icon: MessageCircle, color: 'green' },
]

export function AccountConnections({
  connections,
  onConnectionsChange,
  canManage
}: AccountConnectionsProps) {
  const { toast } = useToast()
  const [addAccountOpen, setAddAccountOpen] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState<string>('')
  const [connecting, setConnecting] = useState(false)
  
  // Checkpoint resolution state
  const [checkpointDialogOpen, setCheckpointDialogOpen] = useState(false)
  const [selectedConnection, setSelectedConnection] = useState<ChannelConnection | null>(null)
  const [verificationCode, setVerificationCode] = useState('')
  const [submittingCode, setSubmittingCode] = useState(false)

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
      const response = await communicationsApi.requestHostedAuth({
        providers: [selectedProvider],
        success_redirect_url: `${window.location.origin}/settings/communications/accounts?success=true`,
        failure_redirect_url: `${window.location.origin}/settings/communications/accounts?error=true`,
        name: `${selectedProvider} Account`
      })

      const data = response.data
      if (data.url) {
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
      
      toast({
        title: "Connection Removed",
        description: "The account connection has been removed successfully.",
      })
      
      onConnectionsChange()
    } catch (error) {
      console.error('Error removing connection:', error)
      toast({
        title: "Removal Failed",
        description: "Failed to remove the connection. Please try again.",
        variant: "destructive",
      })
    }
  }

  const handleReconnect = async (connection: ChannelConnection) => {
    // TODO: Implement reconnectAccount API method
    toast({
      title: "Feature Not Available",
      description: "Account reconnection is not yet implemented.",
      variant: "destructive"
    })
  }

  const submitCheckpointCode = async () => {
    // TODO: Implement submitCheckpoint API method
    toast({
      title: "Feature Not Available",
      description: "Checkpoint verification is not yet implemented.",
      variant: "destructive"
    })
    setCheckpointDialogOpen(false)
    setVerificationCode('')
    setSelectedConnection(null)
    setSubmittingCode(false)
  }

  const getConnectionStatus = (connection: ChannelConnection) => {
    const { authStatus, accountStatus, statusInfo } = connection

    if (statusInfo?.needs_action) {
      return {
        color: 'amber',
        label: statusInfo.action_type || 'Action Required',
        description: statusInfo.message
      }
    }

    if (authStatus === 'authenticated' && accountStatus === 'active') {
      return {
        color: 'green',
        label: 'Active',
        description: 'Connection is working properly'
      }
    }

    if (accountStatus === 'checkpoint_required') {
      return {
        color: 'yellow',
        label: 'Verification Required',
        description: 'Account needs verification'
      }
    }

    return {
      color: 'red',
      label: 'Disconnected',
      description: 'Connection needs to be re-established'
    }
  }

  const getChannelIcon = (channelType: string) => {
    const provider = PROVIDERS.find(p => p.value === channelType)
    return provider?.icon || Mail
  }

  const getChannelColor = (channelType: string) => {
    const provider = PROVIDERS.find(p => p.value === channelType)
    return provider?.color || 'gray'
  }

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Connected Accounts</h3>
          <p className="text-sm text-gray-500">Manage your communication channel connections</p>
        </div>
        {canManage && (
          <Dialog open={addAccountOpen} onOpenChange={setAddAccountOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Connect Account
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Connect Communication Account</DialogTitle>
                <DialogDescription>
                  Select a provider to connect your communication account
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>Provider</Label>
                  <Select value={selectedProvider} onValueChange={setSelectedProvider}>
                    <SelectTrigger>
                      <SelectValue placeholder="Choose a provider..." />
                    </SelectTrigger>
                    <SelectContent>
                      {PROVIDERS.map(provider => {
                        const Icon = provider.icon
                        return (
                          <SelectItem key={provider.value} value={provider.value}>
                            <div className="flex items-center gap-2">
                              <Icon className="h-4 w-4" />
                              <span>{provider.label}</span>
                            </div>
                          </SelectItem>
                        )
                      })}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setAddAccountOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleAddAccount} disabled={connecting || !selectedProvider}>
                  {connecting ? "Connecting..." : "Connect"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Connected Accounts List */}
      {connections.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <MessageCircle className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium mb-2">No accounts connected</h3>
            <p className="text-gray-500 mb-4">
              Connect your communication accounts to start receiving messages
            </p>
            {canManage && (
              <Button onClick={() => setAddAccountOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Connect Your First Account
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {connections.map(connection => {
            const status = getConnectionStatus(connection)
            const Icon = getChannelIcon(connection.channelType)
            const color = getChannelColor(connection.channelType)
            
            return (
              <Card key={connection.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "p-2 rounded-lg",
                        color === 'red' && "bg-red-100 dark:bg-red-900/30",
                        color === 'green' && "bg-green-100 dark:bg-green-900/30",
                        color === 'blue' && "bg-blue-100 dark:bg-blue-900/30",
                        color === 'indigo' && "bg-indigo-100 dark:bg-indigo-900/30",
                        color === 'gray' && "bg-gray-100 dark:bg-gray-900/30"
                      )}>
                        <Icon className={cn(
                          "h-5 w-5",
                          color === 'red' && "text-red-600 dark:text-red-400",
                          color === 'green' && "text-green-600 dark:text-green-400",
                          color === 'blue' && "text-blue-600 dark:text-blue-400",
                          color === 'indigo' && "text-indigo-600 dark:text-indigo-400",
                          color === 'gray' && "text-gray-600 dark:text-gray-400"
                        )} />
                      </div>
                      <div>
                        <CardTitle className="text-lg">{connection.accountName}</CardTitle>
                        <CardDescription>
                          {connection.channelType} Account
                        </CardDescription>
                      </div>
                    </div>
                    <Badge 
                      variant={
                        status.color === 'green' ? 'default' : 
                        status.color === 'amber' || status.color === 'yellow' ? 'secondary' : 
                        'destructive'
                      }
                    >
                      {status.label}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-500">Account ID</span>
                      <span className="font-mono">{connection.externalAccountId || 'Pending...'}</span>
                    </div>
                    
                    {connection.lastActiveAt && (
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-500">Last Active</span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(connection.lastActiveAt).toLocaleDateString()}
                        </span>
                      </div>
                    )}
                    
                    {status.description && (
                      <Alert className="mt-3">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>{status.description}</AlertDescription>
                      </Alert>
                    )}
                    
                    {canManage && (
                      <div className="flex gap-2 pt-3 border-t">
                        {status.color !== 'green' && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleReconnect(connection)}
                          >
                            <RotateCcw className="mr-2 h-4 w-4" />
                            Reconnect
                          </Button>
                        )}
                        {connection.accountStatus === 'checkpoint_required' && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setSelectedConnection(connection)
                              setCheckpointDialogOpen(true)
                            }}
                          >
                            Verify
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          className="ml-auto text-red-600 hover:text-red-700"
                          onClick={() => handleRemoveConnection(connection.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* Checkpoint Verification Dialog */}
      <Dialog open={checkpointDialogOpen} onOpenChange={setCheckpointDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Account Verification Required</DialogTitle>
            <DialogDescription>
              {selectedConnection?.accountName} requires verification to continue. 
              Please enter the verification code sent to your account.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Verification Code</Label>
              <Input
                placeholder="Enter code..."
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCheckpointDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={submitCheckpointCode} disabled={submittingCode || !verificationCode}>
              {submittingCode ? "Verifying..." : "Verify"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}