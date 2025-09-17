'use client'

import { useState, useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { Menu, X, Bell, Search, Settings, LogOut, User, Users, Database, Workflow, ChevronDown, ChevronRight, ChevronLeft, Settings2, CheckSquare, GitBranch, PanelLeftClose, PanelLeft } from 'lucide-react'
import Link from 'next/link'
import { useAuth } from '@/features/auth/context'
import { useWebSocket } from '@/contexts/websocket-context'
import { cn } from '@/lib/utils'
import { pipelinesApi } from '@/lib/api'

interface AppShellProps {
  children: React.ReactNode
}

interface NavItem {
  name: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  description?: string
  current?: boolean
}

export function AppShell({ children }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    // Load collapsed state from localStorage
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('sidebar-collapsed')
      return saved === 'true'
    }
    return false
  })
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [pipelinesExpanded, setPipelinesExpanded] = useState(false)
  const [pipelines, setPipelines] = useState<any[]>([])
  const [pipelinesLoading, setPipelinesLoading] = useState(false)
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout, tenant, hasPermission } = useAuth()
  const { subscribe, unsubscribe, isConnected } = useWebSocket()
  
  // Check if user can update pipelines (for showing settings button)
  const canUpdatePipelines = hasPermission('pipelines', 'update')

  // Toggle sidebar collapsed state
  const toggleSidebarCollapsed = () => {
    const newState = !sidebarCollapsed
    setSidebarCollapsed(newState)
    localStorage.setItem('sidebar-collapsed', newState.toString())
    // Close pipelines if collapsing
    if (newState) {
      setPipelinesExpanded(false)
    }
  }

  // Pipeline type icons mapping
  const PIPELINE_TYPE_ICONS: Record<string, string> = {
    custom: '⚙️',
    contacts: '👤',
    companies: '🏢',
    deals: '💰',
    inventory: '📦',
    support: '🎧'
  }

  // Map old text identifiers to emojis
  const iconMap: Record<string, string> = {
    'database': '📊',
    'folder': '📁',
    'chart': '📈',
    'users': '👥',
    'settings': '⚙️',
    'star': '⭐'
  }

  // Helper to get display icon (handles both emoji and text identifiers)
  const getDisplayIcon = (icon: string) => {
    if (!icon) return '📊'
    
    // Check if it's a text identifier that needs mapping
    if (iconMap[icon]) {
      return iconMap[icon]
    }
    
    // For any other value (including emojis), return as-is
    // This handles all emoji ranges without needing complex regex
    return icon
  }

  // Navigation items
  const navigation: NavItem[] = [
    {
      name: 'Dashboard',
      href: '/dashboard',
      icon: Database,
      description: 'Overview and analytics',
    },
    {
      name: 'Pipelines',
      href: '/pipelines',
      icon: Workflow,
      description: 'Data pipelines and records',
    },
    {
      name: 'Workflows',
      href: '/workflows',
      icon: GitBranch,
      description: 'Automation and workflows',
    },
    {
      name: 'Tasks',
      href: '/tasks',
      icon: CheckSquare,
      description: 'Manage all tasks',
    },
    {
      name: 'Settings',
      href: '/settings',
      icon: Settings,
      description: 'Organization, users & permissions',
    },
  ]

  // Update current state based on pathname
  const navigationWithCurrent = navigation.map(item => ({
    ...item,
    current: pathname.startsWith(item.href)
  }))

  // Function to fetch pipelines
  const fetchPipelines = async () => {
    try {
      setPipelinesLoading(true)
      const response = await pipelinesApi.list()
      const pipelinesData = response.data.results || response.data || []
      console.log('Fetched pipelines:', pipelinesData.length, 'pipelines')
      // Filter only active pipelines and limit to first 10
      const activePipelines = pipelinesData
        .filter((p: any) => !p.is_archived)
        .slice(0, 10)
      console.log('Active pipelines after filtering:', activePipelines.length)
      setPipelines(activePipelines)
    } catch (error) {
      console.error('Failed to fetch pipelines:', error)
    } finally {
      setPipelinesLoading(false)
    }
  }

  // Fetch pipelines when component mounts or pathname changes
  useEffect(() => {
    if (user) {
      fetchPipelines()
    }
  }, [user])

  // Subscribe to pipeline updates via WebSocket
  useEffect(() => {
    if (!user || !isConnected) {
      console.log('WebSocket not ready:', { user: !!user, isConnected })
      return
    }

    console.log('Setting up WebSocket subscription for pipeline updates')
    
    // Subscribe to pipeline updates
    const subscriptionId = subscribe('pipeline_updates', (message) => {
      console.log('Received pipeline WebSocket message:', message)
      
      // The backend sends with type: 'pipeline_update' and payload contains the data
      if (message.type === 'pipeline_update') {
        console.log('Pipeline update payload:', message.payload)
        // Always refresh pipelines when we receive a pipeline_update message
        console.log('Refreshing pipelines due to pipeline update')
        fetchPipelines()
      } else if (message.type === 'field_update' || message.type === 'field_delete') {
        console.log('Field update received:', message)
        // Also refresh for field updates as they affect the pipeline
        fetchPipelines()
      }
    })

    console.log('WebSocket subscription created with ID:', subscriptionId)

    // Cleanup subscription on unmount
    return () => {
      console.log('Cleaning up WebSocket subscription:', subscriptionId)
      unsubscribe(subscriptionId)
    }
  }, [user, isConnected, subscribe, unsubscribe])

  // Auto-expand pipelines if we're on a pipeline page
  useEffect(() => {
    if (pathname.startsWith('/pipelines/') && pathname !== '/pipelines/') {
      setPipelinesExpanded(true)
    }
  }, [pathname])

  // Close mobile sidebar when route changes
  useEffect(() => {
    setSidebarOpen(false)
  }, [pathname])

  // Close user menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      const target = event.target as HTMLElement
      if (!target.closest('[data-user-menu]')) {
        setUserMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleLogout = async () => {
    try {
      console.log('Starting logout process...')
      await logout()
      console.log('Logout completed successfully')
      setUserMenuOpen(false)
    } catch (error) {
      console.error('Logout failed:', error)
      // Still close the menu and clear local state even if server logout fails
      setUserMenuOpen(false)
    }
  }

  return (
    <div className="h-screen flex overflow-hidden bg-gray-100 dark:bg-gray-900">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        >
          <div className="absolute inset-0 bg-gray-600 opacity-75" />
        </div>
      )}

      {/* Sidebar */}
      <div className={cn(
        "fixed inset-y-0 left-0 z-50 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transform transition-all duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0",
        sidebarCollapsed ? "w-16" : "w-64",
        sidebarOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="flex flex-col h-full">
          {/* Sidebar header */}
          <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200 dark:border-gray-700">
            <div className={cn("flex items-center", sidebarCollapsed && "justify-center")}>
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                  <span className="text-primary-foreground font-bold text-lg">O</span>
                </div>
              </div>
              {!sidebarCollapsed && (
                <div className="ml-3">
                  <h1 className="text-sm font-semibold text-gray-900 dark:text-white">
                    Oneo CRM
                  </h1>
                  {tenant && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                      {tenant.name}
                    </p>
                  )}
                </div>
              )}
            </div>
            <button
              className={cn(
                "lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700",
                sidebarCollapsed && "hidden"
              )}
              onClick={() => setSidebarOpen(false)}
            >
              <X className="w-5 h-5" />
            </button>
            {/* Desktop collapse toggle */}
            <button
              className="hidden lg:block p-1.5 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
              onClick={toggleSidebarCollapsed}
              title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {sidebarCollapsed ? (
                <PanelLeft className="w-4 h-4" />
              ) : (
                <PanelLeftClose className="w-4 h-4" />
              )}
            </button>
          </div>

          {/* WebSocket Status (for debugging) */}
          {!sidebarCollapsed && (
            <div className="px-4 py-2 text-xs">
              <div className={`flex items-center ${isConnected ? 'text-green-500' : 'text-red-500'}`}>
                <div className={`w-2 h-2 rounded-full mr-2 ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                WebSocket: {isConnected ? 'Connected' : 'Disconnected'}
              </div>
            </div>
          )}

          {/* Navigation */}
          <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
            {navigationWithCurrent.map((item) => {
              // Special handling for Pipelines item
              if (item.name === 'Pipelines') {
                const currentPipelineId = pathname.split('/')[2]
                return (
                  <div key={item.name}>
                    {/* Main Pipelines button */}
                    <div
                      className={cn(
                        "group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors",
                        sidebarCollapsed && "justify-center",
                        item.current && !currentPipelineId
                          ? "bg-primary text-primary-foreground"
                          : "text-gray-600 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white"
                      )}
                      title={sidebarCollapsed ? item.name : undefined}
                    >
                      {sidebarCollapsed ? (
                        // In collapsed mode, clicking the icon toggles the pipelines
                        <button
                          onClick={() => setPipelinesExpanded(!pipelinesExpanded)}
                          className="flex items-center justify-center w-full"
                        >
                          <item.icon
                            className={cn(
                              "flex-shrink-0 h-5 w-5",
                              item.current && !currentPipelineId
                                ? "text-primary-foreground"
                                : "text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300"
                            )}
                          />
                          {pipelinesExpanded && (
                            <ChevronDown className="h-3 w-3 ml-0.5 -mr-1" />
                          )}
                        </button>
                      ) : (
                        // In expanded mode, show expand button and link separately
                        <>
                          <button
                            onClick={() => setPipelinesExpanded(!pipelinesExpanded)}
                            className="p-1 -ml-1 mr-1"
                          >
                            {pipelinesExpanded ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                          </button>
                          <Link
                            href={item.href}
                            className="flex items-center flex-1"
                          >
                            <item.icon
                              className={cn(
                                "flex-shrink-0 h-5 w-5 mr-3",
                                item.current && !currentPipelineId
                                  ? "text-primary-foreground"
                                  : "text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300"
                              )}
                            />
                            <div>
                              <div>{item.name}</div>
                              {item.description && (
                                <div className="text-xs opacity-75 mt-0.5">
                                  {item.description}
                                </div>
                              )}
                            </div>
                          </Link>
                        </>
                      )}
                    </div>

                    {/* Show pipelines when expanded in either mode */}
                    {pipelinesExpanded && (
                      <div className={sidebarCollapsed ? "mt-1 space-y-1" : "ml-8 mt-1 space-y-1"}>
                        {pipelinesLoading ? (
                          <div className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">
                            Loading pipelines...
                          </div>
                        ) : pipelines.length > 0 ? (
                          <>
                            {pipelines.map((pipeline) => {
                              // Use the icon from the database, converting text identifiers to emojis if needed
                              const pipelineIcon = pipeline.icon
                                ? getDisplayIcon(pipeline.icon)
                                : PIPELINE_TYPE_ICONS[pipeline.pipeline_type] || '📊'
                              const isCurrentPipeline = currentPipelineId === pipeline.id.toString()

                              // Icon-only view for collapsed sidebar
                              if (sidebarCollapsed) {
                                return (
                                  <Link
                                    key={pipeline.id}
                                    href={`/pipelines/${pipeline.id}/records`}
                                    className={cn(
                                      "flex items-center justify-center px-2 py-2 text-sm rounded-md transition-colors group",
                                      isCurrentPipeline
                                        ? "bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                                    )}
                                    title={pipeline.name}
                                  >
                                    <span className="text-lg">{pipelineIcon}</span>
                                  </Link>
                                )
                              }

                              // Full view for expanded sidebar
                              return (
                                <div
                                  key={pipeline.id}
                                  className={cn(
                                    "flex items-center text-sm rounded-md transition-colors group px-3 py-1.5",
                                    isCurrentPipeline
                                      ? "bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                                  )}
                                >
                                  <Link
                                    href={`/pipelines/${pipeline.id}/records`}
                                    className="flex items-center flex-1 min-w-0"
                                  >
                                    <span className="mr-2 text-base flex-shrink-0">{pipelineIcon}</span>
                                    <span className="truncate">{pipeline.name}</span>
                                  </Link>
                                  {canUpdatePipelines && (
                                    <button
                                      onClick={(e) => {
                                        e.preventDefault()
                                        e.stopPropagation()
                                        router.push(`/pipelines/${pipeline.id}`)
                                      }}
                                      className={cn(
                                        "ml-2 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity",
                                        isCurrentPipeline
                                          ? "hover:bg-blue-100 dark:hover:bg-blue-800/30"
                                          : "hover:bg-gray-100 dark:hover:bg-gray-600"
                                      )}
                                      title="Pipeline Settings"
                                    >
                                      <Settings2 className="w-4 h-4" />
                                    </button>
                                  )}
                                </div>
                              )
                            })}
                            {pipelines.length >= 10 && !sidebarCollapsed && (
                              <Link
                                href="/pipelines"
                                className="flex items-center px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
                              >
                                <span className="mr-2">→</span>
                                View all pipelines
                              </Link>
                            )}
                          </>
                        ) : (
                          <div className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">
                            No pipelines available
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              }

              // Regular navigation items
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors",
                    sidebarCollapsed && "justify-center",
                    item.current
                      ? "bg-primary text-primary-foreground"
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white"
                  )}
                  title={sidebarCollapsed ? item.name : undefined}
                >
                  <item.icon
                    className={cn(
                      "flex-shrink-0 h-5 w-5",
                      !sidebarCollapsed && "mr-3",
                      item.current
                        ? "text-primary-foreground"
                        : "text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300"
                    )}
                  />
                  {!sidebarCollapsed && (
                    <div>
                      <div>{item.name}</div>
                      {item.description && (
                        <div className="text-xs opacity-75 mt-0.5">
                          {item.description}
                        </div>
                      )}
                    </div>
                  )}
                </Link>
              )
            })}
          </nav>

          {/* User info */}
          {user && (
            <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 p-4">
              <div className={cn("flex items-center", sidebarCollapsed && "justify-center")}>
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-gray-300 dark:bg-gray-600 rounded-full flex items-center justify-center">
                    <User className="w-4 h-4 text-gray-600 dark:text-gray-300" />
                  </div>
                </div>
                {!sidebarCollapsed && (
                  <div className="ml-3 min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {user.firstName && user.lastName
                        ? `${user.firstName} ${user.lastName}`
                        : user.firstName
                          ? user.firstName
                          : user.email?.split('@')[0] || 'Loading...'
                      }
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                      {user.userType?.name || 'User'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main content area */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Top navigation */}
        <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between h-16 px-4">
            {/* Mobile menu button */}
            <button
              className="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="w-5 h-5" />
            </button>

            {/* Search bar */}
            <div className="flex-1 max-w-lg mx-4">
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search className="h-4 w-4 text-gray-400" />
                </div>
                <input
                  type="text"
                  placeholder="Search..."
                  className="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md leading-5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
                />
              </div>
            </div>

            {/* Right side actions */}
            <div className="flex items-center space-x-3">
              {/* Notifications */}
              <button className="p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 relative">
                <Bell className="w-5 h-5" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
              </button>

              {/* User menu */}
              {user && (
                <div className="relative" data-user-menu>
                  <button
                    className="flex items-center p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
                    onClick={() => setUserMenuOpen(!userMenuOpen)}
                  >
                    <div className="w-6 h-6 bg-gray-300 dark:bg-gray-600 rounded-full flex items-center justify-center mr-2">
                      <User className="w-3 h-3 text-gray-600 dark:text-gray-300" />
                    </div>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {user.firstName && user.lastName 
                        ? `${user.firstName} ${user.lastName}`
                        : user.firstName 
                          ? user.firstName
                          : user.email?.split('@')[0] || 'User'
                      }
                    </span>
                    <ChevronDown className="w-4 h-4 ml-1" />
                  </button>

                  {userMenuOpen && (
                    <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 z-50">
                      <div className="py-1">
                        <div className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                          {user.email || 'Loading...'}
                        </div>
                        <Link
                          href="/profile"
                          className="flex items-center px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                          onClick={() => setUserMenuOpen(false)}
                        >
                          <User className="w-4 h-4 mr-2" />
                          Profile
                        </Link>
                        <Link
                          href="/settings"
                          className="flex items-center px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                          onClick={() => setUserMenuOpen(false)}
                        >
                          <Settings className="w-4 h-4 mr-2" />
                          Settings
                        </Link>
                        <button
                          onClick={handleLogout}
                          className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                        >
                          <LogOut className="w-4 h-4 mr-2" />
                          Sign out
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  )
}