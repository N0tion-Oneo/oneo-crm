'use client'

import { useState, useEffect } from 'react'
import { 
  Loader2, 
  AlertCircle, 
  Plus, 
  Search,
  Filter,
  ChevronDown,
  ChevronRight,
  User,
  Users,
  Mail,
  MessageCircle,
  Linkedin,
  MoreVertical,
  Edit2,
  Trash2,
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle
} from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/features/auth/context'
import { communicationsApi } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'

interface ChannelConnection {
  id: string
  userId: string
  userName?: string
  userEmail?: string
  channelType: string
  accountName: string
  customName?: string // User-defined custom name
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

interface UserGroup {
  userId: string
  userName: string
  userEmail: string
  userAvatar?: string
  connections: ChannelConnection[]
  isExpanded: boolean
}

const CHANNEL_ICONS = {
  email: Mail,
  mail: Mail,
  gmail: Mail,
  outlook: Mail,
  whatsapp: MessageCircle,
  linkedin: Linkedin,
  instagram: MessageCircle,
  messenger: MessageCircle,
  telegram: MessageCircle,
  twitter: MessageCircle,
}

const CHANNEL_COLORS = {
  email: 'text-blue-500',
  mail: 'text-gray-600',
  gmail: 'text-red-500',
  outlook: 'text-blue-600',
  whatsapp: 'text-green-500',
  linkedin: 'text-indigo-600',
  instagram: 'text-pink-500',
  messenger: 'text-blue-500',
  telegram: 'text-cyan-500',
  twitter: 'text-sky-500',
}

export default function AccountConnectionsPage() {
  const [connections, setConnections] = useState<ChannelConnection[]>([])
  const [userGroups, setUserGroups] = useState<UserGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterChannel, setFilterChannel] = useState<string>('all')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [viewMode, setViewMode] = useState<'all' | 'mine'>('mine')
  const [editingConnection, setEditingConnection] = useState<ChannelConnection | null>(null)
  const [customName, setCustomName] = useState('')
  const [deletingConnection, setDeletingConnection] = useState<ChannelConnection | null>(null)
  
  const { toast } = useToast()
  const { user, hasPermission } = useAuth()
  
  // Settings permission ONLY controls page access
  const hasSettingsAccess = hasPermission('settings', 'communications')
  
  // Resource permissions control what actions can be performed
  const hasAccountsAccess = hasPermission('communication_settings', 'accounts')
  
  // Page access: need settings permission to view the settings page
  const canViewPage = hasSettingsAccess
  
  // Action permissions: require specific resource permission
  const canViewSettings = hasAccountsAccess
  const canViewAllAccounts = hasPermission('communications', 'admin') || hasPermission('system', 'admin')
  const canManageAccounts = hasAccountsAccess // For communication settings, permission implies both view and edit
  const canDeleteAccounts = hasAccountsAccess

  useEffect(() => {
    // Only load if user has permission
    if (!canViewSettings) {
      setLoading(false)
      return
    }
    loadConnections()
  }, [viewMode, canViewSettings])

  useEffect(() => {
    groupConnectionsByUser()
  }, [connections, searchQuery, filterChannel, filterStatus])

  // Check for success/error from redirect
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('success') === 'true') {
      toast({
        title: "Account Connected",
        description: "Your communication account has been successfully connected!",
      })
      // Clean up URL
      window.history.replaceState({}, '', window.location.pathname)
      // Reload connections
      loadConnections()
    } else if (params.get('error') === 'true') {
      toast({
        title: "Connection Failed",
        description: "Failed to connect account. Please try again.",
        variant: "destructive",
      })
      // Clean up URL
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

  const loadConnections = async () => {
    try {
      setLoading(true)
      
      // Use the existing getConnections method
      // In production, we'd need to add a getAllConnections method for admins
      const response = await communicationsApi.getConnections()
      
      // Mock user data for demonstration - in reality this would come from the API
      const enrichedConnections = (response.data.results || response.data || []).map((conn: any) => ({
        ...conn,
        userId: conn.userId || user?.id || 'user1',
        userName: conn.userName || (user ? `${user.firstName} ${user.lastName}`.trim() : 'Current User'),
        userEmail: conn.userEmail || user?.email || 'user@example.com',
      }))
      
      // Filter based on viewMode if not admin
      const filteredConnections = viewMode === 'mine' || !canViewAllAccounts
        ? enrichedConnections.filter((conn: any) => conn.userId === user?.id)
        : enrichedConnections
      
      setConnections(filteredConnections)
    } catch (error: any) {
      console.error('Error loading connections:', error)
      toast({
        title: "Failed to load connections",
        description: error.response?.data?.error || "An error occurred",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const groupConnectionsByUser = () => {
    const filtered = connections.filter(conn => {
      const matchesSearch = searchQuery === '' || 
        conn.accountName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        conn.customName?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        conn.userName?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        conn.userEmail?.toLowerCase().includes(searchQuery.toLowerCase())
      
      const matchesChannel = filterChannel === 'all' || conn.channelType === filterChannel
      const matchesStatus = filterStatus === 'all' || 
        (filterStatus === 'active' && conn.canSendMessages) ||
        (filterStatus === 'error' && conn.statusInfo?.needs_action)
      
      return matchesSearch && matchesChannel && matchesStatus
    })

    const groups = filtered.reduce((acc: UserGroup[], conn) => {
      const existingGroup = acc.find(g => g.userId === conn.userId)
      if (existingGroup) {
        existingGroup.connections.push(conn)
      } else {
        acc.push({
          userId: conn.userId,
          userName: conn.userName || 'Unknown User',
          userEmail: conn.userEmail || '',
          connections: [conn],
          isExpanded: true
        })
      }
      return acc
    }, [])

    setUserGroups(groups)
  }

  const toggleGroup = (userId: string) => {
    setUserGroups(prev => prev.map(group => 
      group.userId === userId ? { ...group, isExpanded: !group.isExpanded } : group
    ))
  }

  const handleConnect = async (channelType: string) => {
    try {
      const response = await communicationsApi.requestHostedAuth({
        providers: [channelType],
        success_redirect_url: `${window.location.origin}/settings/communications/accounts?success=true`,
        failure_redirect_url: `${window.location.origin}/settings/communications/accounts?error=true`,
        name: `${user ? `${user.firstName} ${user.lastName}`.trim() : 'User'} - ${channelType}`,
      })
      
      if (response.data?.hostedAuthUrl) {
        window.location.href = response.data.hostedAuthUrl
      } else {
        toast({
          title: "Connection Error",
          description: "Could not retrieve authentication URL",
          variant: "destructive",
        })
      }
    } catch (error: any) {
      toast({
        title: "Connection Failed",
        description: error.response?.data?.error || `Failed to initiate ${channelType} connection`,
        variant: "destructive",
      })
    }
  }

  const handleEdit = (connection: ChannelConnection) => {
    setEditingConnection(connection)
    setCustomName(connection.customName || '')
  }

  const handleSaveEdit = async () => {
    if (!editingConnection) return
    
    try {
      // For now, we'll update locally since we don't have a patch method
      // In production, this would need a backend endpoint
      setConnections(prev => prev.map(conn => 
        conn.id === editingConnection.id ? { ...conn, customName } : conn
      ))
      
      toast({
        title: "Account Updated",
        description: "Account details have been saved.",
      })
      
      setEditingConnection(null)
    } catch (error) {
      toast({
        title: "Update Failed",
        description: "Failed to update account details.",
        variant: "destructive",
      })
    }
  }

  const handleDelete = async (connection: ChannelConnection) => {
    try {
      await communicationsApi.deleteConnection(connection.id)
      
      setConnections(prev => prev.filter(conn => conn.id !== connection.id))
      
      toast({
        title: "Account Disconnected",
        description: "The account has been disconnected successfully.",
      })
      
      setDeletingConnection(null)
    } catch (error) {
      toast({
        title: "Disconnection Failed",
        description: "Failed to disconnect the account.",
        variant: "destructive",
      })
    }
  }

  const handleRefresh = async (connection: ChannelConnection) => {
    try {
      // For now, just reload the connections
      // In production, we'd need a refresh endpoint
      toast({
        title: "Refreshing Connection",
        description: "Connection status is being updated...",
      })
      
      setTimeout(loadConnections, 2000)
    } catch (error) {
      toast({
        title: "Refresh Failed",
        description: "Failed to refresh connection status.",
        variant: "destructive",
      })
    }
  }

  const getStatusIcon = (connection: ChannelConnection) => {
    if (connection.canSendMessages) {
      return <CheckCircle className="h-4 w-4 text-green-500" />
    }
    if (connection.statusInfo?.needs_action) {
      return <AlertTriangle className="h-4 w-4 text-amber-500" />
    }
    return <XCircle className="h-4 w-4 text-red-500" />
  }

  const getChannelIcon = (channelType: string) => {
    const Icon = CHANNEL_ICONS[channelType as keyof typeof CHANNEL_ICONS] || Mail
    return <Icon className={`h-4 w-4 ${CHANNEL_COLORS[channelType as keyof typeof CHANNEL_COLORS] || 'text-gray-500'}`} />
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        </div>
      </div>
    )
  }

  // Check permissions before showing any content
  if (!canViewSettings) {
    return (
      <div className="p-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-12">
            <AlertCircle className="h-12 w-12 mx-auto text-amber-500 mb-4" />
            <h3 className="text-lg font-medium">Access Denied</h3>
            <p className="text-gray-600">You don't have permission to view account connections.</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6 flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Account Connections
            </h1>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Manage connected communication accounts across your organization
            </p>
          </div>
          
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Connect Account
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuItem onClick={() => handleConnect('gmail')}>
                {getChannelIcon('gmail')}
                <span className="ml-2">Gmail</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleConnect('outlook')}>
                {getChannelIcon('outlook')}
                <span className="ml-2">Outlook</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleConnect('mail')}>
                {getChannelIcon('mail')}
                <span className="ml-2">Email (Generic)</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => handleConnect('whatsapp')}>
                {getChannelIcon('whatsapp')}
                <span className="ml-2">WhatsApp</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleConnect('linkedin')}>
                {getChannelIcon('linkedin')}
                <span className="ml-2">LinkedIn</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleConnect('instagram')}>
                {getChannelIcon('instagram')}
                <span className="ml-2">Instagram</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleConnect('messenger')}>
                {getChannelIcon('messenger')}
                <span className="ml-2">Facebook Messenger</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleConnect('telegram')}>
                {getChannelIcon('telegram')}
                <span className="ml-2">Telegram</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleConnect('twitter')}>
                {getChannelIcon('twitter')}
                <span className="ml-2">Twitter/X</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* View Mode Tabs (for admins) */}
        {canViewAllAccounts && (
          <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as 'all' | 'mine')} className="mb-6">
            <TabsList>
              <TabsTrigger value="mine" className="flex items-center gap-2">
                <User className="h-4 w-4" />
                My Accounts
              </TabsTrigger>
              <TabsTrigger value="all" className="flex items-center gap-2">
                <Users className="h-4 w-4" />
                All Accounts
              </TabsTrigger>
            </TabsList>
          </Tabs>
        )}

        {/* Filters */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    placeholder="Search accounts, users, or emails..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9"
                  />
                </div>
              </div>
              
              <Select value={filterChannel} onValueChange={setFilterChannel}>
                <SelectTrigger className="w-[180px]">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue placeholder="All Channels" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Channels</SelectItem>
                  <SelectItem value="gmail">Gmail</SelectItem>
                  <SelectItem value="outlook">Outlook</SelectItem>
                  <SelectItem value="mail">Email (Generic)</SelectItem>
                  <SelectItem value="whatsapp">WhatsApp</SelectItem>
                  <SelectItem value="linkedin">LinkedIn</SelectItem>
                  <SelectItem value="instagram">Instagram</SelectItem>
                  <SelectItem value="messenger">Facebook Messenger</SelectItem>
                  <SelectItem value="telegram">Telegram</SelectItem>
                  <SelectItem value="twitter">Twitter/X</SelectItem>
                </SelectContent>
              </Select>
              
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="All Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="error">Needs Attention</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* User Groups */}
        <div className="space-y-4">
          {userGroups.map((group) => (
            <Card key={group.userId}>
              <CardHeader>
                <Collapsible open={group.isExpanded} onOpenChange={() => toggleGroup(group.userId)}>
                  <CollapsibleTrigger className="w-full" asChild>
                    <button className="w-full text-left hover:bg-gray-50 dark:hover:bg-gray-900/50 p-2 rounded-lg transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="p-1">
                            {group.isExpanded ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                          </div>
                          <Avatar className="h-8 w-8">
                            <AvatarImage src={group.userAvatar} />
                            <AvatarFallback>{group.userName.substring(0, 2).toUpperCase()}</AvatarFallback>
                          </Avatar>
                          <div className="text-left">
                            <p className="font-medium">{group.userName}</p>
                            <p className="text-sm text-gray-500">{group.userEmail}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary">
                            {group.connections.length} {group.connections.length === 1 ? 'account' : 'accounts'}
                          </Badge>
                        </div>
                      </div>
                    </button>
                  </CollapsibleTrigger>
                  
                  <CollapsibleContent>
                    <div className="mt-4 space-y-3">
                      {group.connections.map((connection) => (
                        <div
                          key={connection.id}
                          className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-900/50 transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            {getChannelIcon(connection.channelType)}
                            <div>
                              <p className="font-medium">
                                {connection.customName || connection.accountName}
                              </p>
                              {connection.customName && (
                                <p className="text-sm text-gray-500">
                                  {connection.accountName}
                                </p>
                              )}
                              <div className="flex items-center gap-2 mt-1">
                                {getStatusIcon(connection)}
                                <span className="text-xs text-gray-500">
                                  {connection.statusInfo?.display || 'Unknown status'}
                                </span>
                                {connection.lastActiveAt && (
                                  <>
                                    <span className="text-xs text-gray-400">•</span>
                                    <span className="text-xs text-gray-500">
                                      Last active {new Date(connection.lastActiveAt).toLocaleDateString()}
                                    </span>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-2">
                            {connection.messagesSentToday !== undefined && (
                              <Badge variant="outline" className="text-xs">
                                {connection.messagesSentToday} sent today
                              </Badge>
                            )}
                            
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon">
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => handleEdit(connection)}>
                                  <Edit2 className="h-4 w-4 mr-2" />
                                  Edit Details
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => handleRefresh(connection)}>
                                  <RefreshCw className="h-4 w-4 mr-2" />
                                  Refresh Status
                                </DropdownMenuItem>
                                {connection.statusInfo?.needs_action && (
                                  <DropdownMenuItem>
                                    <AlertTriangle className="h-4 w-4 mr-2" />
                                    Fix Connection
                                  </DropdownMenuItem>
                                )}
                                <DropdownMenuSeparator />
                                <DropdownMenuItem 
                                  className="text-red-600"
                                  onClick={() => setDeletingConnection(connection)}
                                  disabled={!canDeleteAccounts}
                                >
                                  <Trash2 className="h-4 w-4 mr-2" />
                                  Disconnect
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              </CardHeader>
            </Card>
          ))}
        </div>

        {userGroups.length === 0 && (
          <Card>
            <CardContent className="text-center py-12">
              <AlertCircle className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium mb-2">No Accounts Found</h3>
              <p className="text-gray-500 mb-4">
                {searchQuery || filterChannel !== 'all' || filterStatus !== 'all' 
                  ? 'No accounts match your filters. Try adjusting your search criteria.'
                  : 'Connect your first communication account to get started.'}
              </p>
            </CardContent>
          </Card>
        )}

        {/* Edit Dialog */}
        <Dialog open={!!editingConnection} onOpenChange={() => setEditingConnection(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit Account Details</DialogTitle>
              <DialogDescription>
                Customize how this account appears in your dashboard.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="custom-name">Display Name</Label>
                <Input
                  id="custom-name"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  placeholder="e.g., Sales Team Gmail"
                />
                <p className="text-xs text-gray-500">
                  Original: {editingConnection?.accountName}
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditingConnection(null)}>
                Cancel
              </Button>
              <Button onClick={handleSaveEdit}>
                Save Changes
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={!!deletingConnection} onOpenChange={() => setDeletingConnection(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Disconnect Account</DialogTitle>
              <DialogDescription>
                Are you sure you want to disconnect this account? This action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <div className="py-4">
              <p className="text-sm">
                Account: <strong>{deletingConnection?.customName || deletingConnection?.accountName}</strong>
              </p>
              <p className="text-sm">
                Type: <strong>{deletingConnection?.channelType}</strong>
              </p>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeletingConnection(null)}>
                Cancel
              </Button>
              <Button 
                variant="destructive" 
                onClick={() => deletingConnection && handleDelete(deletingConnection)}
              >
                Disconnect Account
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  )
}