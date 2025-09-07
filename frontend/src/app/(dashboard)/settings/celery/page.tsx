"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Database,
  Loader2,
  PlayCircle,
  RefreshCw,
  Server,
  Trash2,
  XCircle,
  Activity,
  Zap,
  AlertTriangle,
  Info,
  Search,
  Filter,
  History,
  MemoryStick,
  HardDrive,
  Cpu,
  Timer,
  Copy,
  ExternalLink
} from "lucide-react"
import { api } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface QueueStatus {
  [key: string]: number
}

interface WorkerInfo {
  name: string
  type: string
  description: string
  hostname: string
  status: string
  active_tasks: number
  processed: number
  failed: number
  pool: string
  concurrency: number
  uptime: string
  queues?: string[]
  pid?: number
}

interface CeleryOverview {
  status: string
  timestamp: string
  current_tenant?: string
  summary: {
    workers_online: number
    expected_workers?: number
    total_queued: number
    tenant_queued?: number
    total_active: number
    tasks_24h: number
    failed_24h: number
  }
  queues: QueueStatus
  workers: WorkerInfo[]
  worker_types?: any
  note?: string
}

interface QueueTask {
  id: string
  task: string
  eta: string | null
  retries: number
  args: string
  kwargs: string
  origin: string
}

interface ActiveTask {
  worker: string
  id: string
  name: string
  args: any[]
  kwargs: any
  time_start: string
  runtime: string
}

interface TaskHistoryItem {
  id: string
  task_type?: 'sync' | 'ai' | 'workflow'
  task_name: string
  status: string
  created_at?: string
  started_at?: string
  completed_at?: string
  duration_ms?: number
  error_message?: string
  error_details?: any
  triggered_by?: string
  celery_task_id?: string
  
  // Sync-specific fields
  record_id?: number
  record_name?: string
  pipeline_name?: string
  job_type?: string
  trigger_reason?: string
  progress_percentage?: number
  current_step?: string
  accounts_synced?: number
  total_accounts_to_sync?: number
  messages_found?: number
  conversations_found?: number
  new_links_created?: number
  
  // AI-specific fields
  model?: string
  prompt?: string
  result?: string
  usage?: any
  cost?: number
  
  // Workflow-specific fields
  workflow_name?: string
  workflow_id?: string
  trigger_type?: string
  trigger_data?: string
  nodes_executed?: number
  execution_data?: any
  error?: string
  
  // Legacy fields
  messages_synced?: number
  retry_count?: number
  traceback?: string
  date_done?: string
  sync_type?: string
}

interface RedisStats {
  redis: {
    version: string
    uptime_days: number
    connected_clients: number
    used_memory_human: string
    used_memory_peak_human: string
    total_commands_processed: number
  }
  queues: {
    [key: string]: {
      type: string
      length?: number
      count?: number
    }
  }
  celery: {
    task_results: number
    unacked: number
  }
  tenant: string
  total_messages: number
}

export default function CelerySettingsPage() {
  const [overview, setOverview] = useState<CeleryOverview | null>(null)
  const [activeTasks, setActiveTasks] = useState<ActiveTask[]>([])
  const [taskHistory, setTaskHistory] = useState<TaskHistoryItem[]>([])
  const [redisStats, setRedisStats] = useState<RedisStats | null>(null)
  const [selectedQueue, setSelectedQueue] = useState<string>("")
  const [queueTasks, setQueueTasks] = useState<QueueTask[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [purgeDialogOpen, setPurgeDialogOpen] = useState(false)
  const [queueToPurge, setQueueToPurge] = useState<string>("")
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [taskTypeFilter, setTaskTypeFilter] = useState<string>("all")
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [taskDetailsDialog, setTaskDetailsDialog] = useState<TaskHistoryItem | null>(null)
  const { toast } = useToast()

  const fetchOverview = async () => {
    try {
      const response = await api.get("/api/v1/celery/overview/")
      setOverview(response.data)
      setError(null)
    } catch (error: any) {
      console.error("Failed to fetch Celery overview:", error)
      const errorMessage = error.response?.status === 403 
        ? "You don't have permission to view Celery management" 
        : error.response?.status === 401
        ? "Please log in to view Celery management"
        : error.response?.data?.error || "Failed to fetch Celery overview"
      setError(errorMessage)
      if (!overview) {
        toast({
          title: "Error",
          description: errorMessage,
          variant: "destructive",
        })
      }
    }
  }

  const fetchActiveTasks = async () => {
    try {
      const response = await api.get("/api/v1/celery/active_tasks/")
      setActiveTasks(response.data.tasks || [])
    } catch (error) {
      console.error("Failed to fetch active tasks:", error)
    }
  }

  const fetchTaskHistory = async () => {
    try {
      const params: any = { limit: 100 }
      if (statusFilter !== 'all') {
        params.status = statusFilter
      }
      if (taskTypeFilter !== 'all') {
        params.task_type = taskTypeFilter
      }
      const response = await api.get("/api/v1/celery/task_history/", { params })
      setTaskHistory(response.data.tasks || [])
    } catch (error) {
      console.error("Failed to fetch task history:", error)
    }
  }

  const fetchRedisStats = async () => {
    try {
      const response = await api.get("/api/v1/celery/redis_stats/")
      setRedisStats(response.data)
    } catch (error) {
      console.error("Failed to fetch Redis stats:", error)
    }
  }

  const fetchQueueDetails = async (queueName: string) => {
    try {
      // Add tenant prefix to queue name if not already present
      const currentSchema = overview?.current_tenant
      const fullQueueName = queueName.includes('_') ? queueName : `${currentSchema}_${queueName}`
      const response = await api.get(`/api/v1/celery/queue_details/?queue=${fullQueueName}&limit=20`)
      setQueueTasks(response.data.tasks || [])
    } catch (error) {
      console.error("Failed to fetch queue details:", error)
    }
  }

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    await Promise.all([
      fetchOverview(), 
      fetchActiveTasks(),
      fetchTaskHistory(),
      fetchRedisStats()
    ])
    if (selectedQueue) {
      await fetchQueueDetails(selectedQueue)
    }
    setRefreshing(false)
    toast({
      title: "Refreshed",
      description: "Celery status updated",
    })
  }, [selectedQueue, statusFilter, taskTypeFilter])

  const handlePurgeQueue = async () => {
    try {
      await api.post("/api/v1/celery/purge_queue/", {
        queue_name: queueToPurge
      })
      toast({
        title: "Success",
        description: `Queue ${queueToPurge} has been purged`,
      })
      setPurgeDialogOpen(false)
      setQueueToPurge("")
      handleRefresh()
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to purge queue",
        variant: "destructive",
      })
    }
  }

  const handleRevokeTask = async (taskId: string, terminate: boolean = false) => {
    try {
      await api.post("/api/v1/celery/revoke_task/", {
        task_id: taskId,
        terminate
      })
      toast({
        title: "Success",
        description: `Task ${taskId} has been ${terminate ? 'terminated' : 'revoked'}`,
      })
      handleRefresh()
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to revoke task",
        variant: "destructive",
      })
    }
  }

  const pingWorkers = async () => {
    try {
      const response = await api.post("/api/v1/celery/ping_workers/")
      toast({
        title: "Ping Complete",
        description: `${response.data.workers_online} workers online, ${response.data.workers_offline} offline`,
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to ping workers",
        variant: "destructive",
      })
    }
  }

  const copyTaskId = (id: string) => {
    navigator.clipboard.writeText(id)
    toast({
      title: "Copied",
      description: "Task ID copied to clipboard",
    })
  }

  const formatDuration = (ms?: number) => {
    if (!ms) return '-'
    if (ms < 1000) return `${Math.round(ms)}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}m`
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      await Promise.all([
        fetchOverview(), 
        fetchActiveTasks(),
        fetchTaskHistory(),
        fetchRedisStats()
      ])
      setLoading(false)
    }
    loadData()
  }, [])

  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      fetchOverview()
      fetchActiveTasks()
      if (redisStats) fetchRedisStats()
    }, 10000)

    return () => clearInterval(interval)
  }, [autoRefresh, redisStats])

  useEffect(() => {
    if (selectedQueue) {
      fetchQueueDetails(selectedQueue)
    }
  }, [selectedQueue])

  useEffect(() => {
    fetchTaskHistory()
  }, [statusFilter])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600'
      case 'degraded':
        return 'text-yellow-600'
      case 'error':
      case 'failed':
        return 'text-red-600'
      case 'completed':
      case 'success':
        return 'text-green-600'
      case 'pending':
        return 'text-blue-600'
      case 'processing':
        return 'text-yellow-600'
      default:
        return 'text-gray-600'
    }
  }

  const getStatusBadge = (status: string) => {
    const color = status === 'completed' || status === 'success' ? 'default' :
                  status === 'failed' || status === 'error' ? 'destructive' :
                  status === 'processing' ? 'secondary' : 'outline'
    return <Badge variant={color as any}>{status}</Badge>
  }

  const getQueueBadgeColor = (count: number) => {
    if (count === 0) return 'secondary'
    if (count < 10) return 'default'
    if (count < 50) return 'outline'
    return 'destructive'
  }

  const filteredHistory = taskHistory.filter(task => {
    if (searchTerm) {
      const search = searchTerm.toLowerCase()
      return task.task_name.toLowerCase().includes(search) ||
             task.id.toLowerCase().includes(search) ||
             (task.record_name && task.record_name.toLowerCase().includes(search)) ||
             (task.pipeline_name && task.pipeline_name.toLowerCase().includes(search)) ||
             (task.workflow_name && task.workflow_name.toLowerCase().includes(search)) ||
             (task.error_message && task.error_message.toLowerCase().includes(search))
    }
    return true
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (error && !overview) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Celery Task Management</h2>
          <p className="text-muted-foreground">
            Monitor and manage background task queues and workers
          </p>
        </div>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <div className="flex gap-2">
          <Button onClick={() => window.location.reload()} variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh Page
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Celery Task Management</h2>
          <p className="text-muted-foreground">
            Monitor and manage background task queues and workers
          </p>
        </div>
        <div className="flex items-center gap-2">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  onClick={() => setAutoRefresh(!autoRefresh)}
                  variant={autoRefresh ? "default" : "outline"}
                  size="sm"
                >
                  {autoRefresh ? (
                    <Activity className="h-4 w-4 animate-pulse" />
                  ) : (
                    <Activity className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Auto-refresh: {autoRefresh ? 'ON' : 'OFF'}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <Button onClick={pingWorkers} variant="outline" size="sm">
            <Activity className="mr-2 h-4 w-4" />
            Ping Workers
          </Button>
          <Button
            onClick={handleRefresh}
            variant="outline"
            size="sm"
            disabled={refreshing}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* System Status Alert */}
      {overview && (
        <Alert className={overview.status === 'healthy' ? 'border-green-500' : 'border-yellow-500'}>
          <Info className="h-4 w-4" />
          <AlertTitle>
            System Status: <span className={getStatusColor(overview.status)}>{overview.status.toUpperCase()}</span>
            {overview.current_tenant && <span className="text-sm font-normal ml-2">(Tenant: {overview.current_tenant})</span>}
          </AlertTitle>
          <AlertDescription>
            {overview.summary.workers_online} workers online • 
            {overview.summary.total_queued} tasks queued • 
            {overview.summary.total_active} tasks active • 
            {overview.summary.tasks_24h} tenant tasks in last 24h
            {overview.summary.failed_24h > 0 && ` • ${overview.summary.failed_24h} failed`}
          </AlertDescription>
        </Alert>
      )}

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Workers</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {overview?.summary.workers_online || 0}/{overview?.summary.expected_workers || 6}
            </div>
            <p className="text-xs text-muted-foreground">
              Specialized workers
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Queued</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview?.summary.total_queued || 0}</div>
            <p className="text-xs text-muted-foreground">
              Waiting to process
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview?.summary.total_active || 0}</div>
            <p className="text-xs text-muted-foreground">
              Currently executing
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Memory</CardTitle>
            <MemoryStick className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{redisStats?.redis.used_memory_human || '-'}</div>
            <p className="text-xs text-muted-foreground">
              Redis memory usage
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">24h Stats</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview?.summary.tasks_24h || 0}</div>
            <p className="text-xs text-muted-foreground">
              {overview?.summary.failed_24h || 0} failed
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="queues" className="space-y-4">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="queues">Queues</TabsTrigger>
          <TabsTrigger value="workers">Workers</TabsTrigger>
          <TabsTrigger value="active">Active Tasks</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
          <TabsTrigger value="redis">Redis Stats</TabsTrigger>
          <TabsTrigger value="scheduled">Scheduled</TabsTrigger>
        </TabsList>

        {/* Queues Tab */}
        <TabsContent value="queues" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Task Queues</CardTitle>
              <CardDescription>
                Monitor and manage task queues for tenant {overview?.current_tenant}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {overview?.queues && Object.entries(overview.queues).map(([queueName, count]) => (
                  <div key={queueName} className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors">
                    <div className="flex items-center gap-4">
                      <div>
                        <p className="font-medium">{queueName}</p>
                        <p className="text-sm text-muted-foreground">
                          {count} tasks queued
                        </p>
                      </div>
                      <Badge variant={getQueueBadgeColor(count) as any}>
                        {count}
                      </Badge>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedQueue(queueName)}
                      >
                        View Tasks
                      </Button>
                      {['background_sync', 'communications_maintenance', 'analytics'].includes(queueName) && count > 0 && (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => {
                            setQueueToPurge(queueName)
                            setPurgeDialogOpen(true)
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Queue Details */}
              {selectedQueue && queueTasks.length > 0 && (
                <div className="mt-6">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="font-medium">Tasks in {selectedQueue}</h4>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedQueue("")}
                    >
                      <XCircle className="h-4 w-4" />
                    </Button>
                  </div>
                  <ScrollArea className="h-[400px]">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Task</TableHead>
                          <TableHead>ID</TableHead>
                          <TableHead>ETA</TableHead>
                          <TableHead>Retries</TableHead>
                          <TableHead>Args</TableHead>
                          <TableHead>Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {queueTasks.map((task) => (
                          <TableRow key={task.id}>
                            <TableCell className="font-mono text-xs">
                              {task.task.split('.').slice(-1)[0]}
                            </TableCell>
                            <TableCell>
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => copyTaskId(task.id)}
                                    >
                                      <Copy className="h-3 w-3 mr-1" />
                                      {task.id.substring(0, 8)}...
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>{task.id}</p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </TableCell>
                            <TableCell>
                              {task.eta ? new Date(task.eta).toLocaleString() : '-'}
                            </TableCell>
                            <TableCell>{task.retries}</TableCell>
                            <TableCell className="max-w-[200px] truncate">
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <span className="text-xs">{task.args}</span>
                                  </TooltipTrigger>
                                  <TooltipContent className="max-w-[400px]">
                                    <pre className="text-xs">{JSON.stringify(JSON.parse(task.args || '[]'), null, 2)}</pre>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </TableCell>
                            <TableCell>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleRevokeTask(task.id)}
                              >
                                <XCircle className="h-4 w-4" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Workers Tab */}
        <TabsContent value="workers" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Specialized Celery Workers</CardTitle>
              <CardDescription>
                {overview?.summary.workers_online || 0} of {overview?.summary.expected_workers || 6} workers online for tenant {overview?.current_tenant}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[600px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Type</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>PID</TableHead>
                      <TableHead>Active</TableHead>
                      <TableHead>Processed</TableHead>
                      <TableHead>Failed</TableHead>
                      <TableHead>Concurrency</TableHead>
                      <TableHead>Queues</TableHead>
                      <TableHead>Uptime</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {overview?.workers.map((worker) => (
                      <TableRow key={worker.hostname}>
                        <TableCell className="font-medium">
                          <Badge variant="outline">{worker.type}</Badge>
                        </TableCell>
                        <TableCell>{worker.description}</TableCell>
                        <TableCell>
                          <Badge variant={worker.status === 'online' ? 'default' : worker.status === 'starting' ? 'secondary' : 'destructive'}>
                            {worker.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-xs">{worker.pid || '-'}</TableCell>
                        <TableCell>{worker.active_tasks}</TableCell>
                        <TableCell>{worker.processed}</TableCell>
                        <TableCell>{worker.failed}</TableCell>
                        <TableCell>{worker.concurrency}</TableCell>
                        <TableCell className="text-xs max-w-[200px]">
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className="truncate block">{worker.queues?.slice(0, 2).join(', ')}...</span>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>{worker.queues?.join(', ')}</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </TableCell>
                        <TableCell>{worker.uptime}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Active Tasks Tab */}
        <TabsContent value="active" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Active Tasks</CardTitle>
              <CardDescription>
                Currently executing tasks across all workers
              </CardDescription>
            </CardHeader>
            <CardContent>
              {activeTasks.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No active tasks at the moment
                </div>
              ) : (
                <ScrollArea className="h-[600px]">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Worker</TableHead>
                        <TableHead>Task</TableHead>
                        <TableHead>ID</TableHead>
                        <TableHead>Runtime</TableHead>
                        <TableHead>Args</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {activeTasks.map((task) => (
                        <TableRow key={task.id}>
                          <TableCell>{task.worker}</TableCell>
                          <TableCell className="font-mono text-xs">
                            {task.name.split('.').slice(-1)[0]}
                          </TableCell>
                          <TableCell>
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => copyTaskId(task.id)}
                                  >
                                    <Copy className="h-3 w-3 mr-1" />
                                    {task.id.substring(0, 8)}...
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>{task.id}</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          </TableCell>
                          <TableCell>
                            <Badge variant="secondary">
                              <Timer className="h-3 w-3 mr-1" />
                              {task.runtime}
                            </Badge>
                          </TableCell>
                          <TableCell className="max-w-[200px] truncate">
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span className="text-xs">{JSON.stringify(task.args).substring(0, 50)}...</span>
                                </TooltipTrigger>
                                <TooltipContent className="max-w-[400px]">
                                  <pre className="text-xs">{JSON.stringify(task.args, null, 2)}</pre>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => handleRevokeTask(task.id, true)}
                            >
                              Terminate
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Task History</CardTitle>
                  <CardDescription>
                    Recent task execution history
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  <div className="relative">
                    <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search tasks..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-8 w-[200px]"
                    />
                  </div>
                  <Select value={taskTypeFilter} onValueChange={setTaskTypeFilter}>
                    <SelectTrigger className="w-[150px]">
                      <SelectValue placeholder="Filter by type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Types</SelectItem>
                      <SelectItem value="sync">Sync Tasks</SelectItem>
                      <SelectItem value="ai">AI Tasks</SelectItem>
                      <SelectItem value="workflow">Workflows</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger className="w-[150px]">
                      <SelectValue placeholder="Filter by status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Status</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                      <SelectItem value="failed">Failed</SelectItem>
                      <SelectItem value="pending">Pending</SelectItem>
                      <SelectItem value="processing">Processing</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[600px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Record</TableHead>
                      <TableHead>Pipeline</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Progress</TableHead>
                      <TableHead>Results</TableHead>
                      <TableHead>Duration</TableHead>
                      <TableHead>Triggered By</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredHistory.map((task) => (
                      <TableRow key={task.id}>
                        <TableCell>
                          {task.task_type === 'sync' ? (
                            <div>
                              <div className="font-medium">
                                {task.record_name || `Record #${task.record_id}`}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                ID: {task.record_id}
                              </div>
                            </div>
                          ) : task.task_type === 'workflow' ? (
                            <div>
                              <div className="font-medium">
                                {task.workflow_name || 'Workflow'}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {task.trigger_type || 'Manual'}
                              </div>
                            </div>
                          ) : task.task_type === 'ai' ? (
                            <div>
                              <div className="font-medium">
                                {task.job_type || 'AI Processing'}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {task.model || 'AI Model'}
                              </div>
                            </div>
                          ) : (
                            <div className="text-muted-foreground">-</div>
                          )}
                        </TableCell>
                        <TableCell className="text-sm">
                          {task.pipeline_name || '-'}
                        </TableCell>
                        <TableCell>
                          <Badge 
                            variant={
                              task.task_type === 'ai' ? 'secondary' :
                              task.task_type === 'workflow' ? 'default' :
                              'outline'
                            } 
                            className="text-xs"
                          >
                            {task.task_type === 'sync' ? '🔄 Sync' :
                             task.task_type === 'ai' ? '🤖 AI' :
                             task.task_type === 'workflow' ? '⚡ Workflow' :
                             task.task_name?.split('.').slice(-1)[0] || 'Task'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {getStatusBadge(task.status)}
                        </TableCell>
                        <TableCell>
                          {task.status === 'running' && task.progress_percentage !== undefined ? (
                            <div className="space-y-1">
                              <div className="flex items-center space-x-2">
                                <Progress value={task.progress_percentage} className="w-16 h-2" />
                                <span className="text-xs">{task.progress_percentage}%</span>
                              </div>
                              {task.current_step && (
                                <p className="text-xs text-muted-foreground truncate max-w-[150px]">
                                  {task.current_step}
                                </p>
                              )}
                            </div>
                          ) : task.accounts_synced !== undefined ? (
                            <span className="text-xs">
                              {task.accounts_synced}/{task.total_accounts_to_sync} accounts
                            </span>
                          ) : '-'}
                        </TableCell>
                        <TableCell>
                          {task.task_type === 'sync' && (task.messages_found !== undefined || task.conversations_found !== undefined) ? (
                            <div className="text-xs space-y-1">
                              {task.messages_found !== undefined && (
                                <div>{task.messages_found} messages</div>
                              )}
                              {task.conversations_found !== undefined && (
                                <div>{task.conversations_found} conversations</div>
                              )}
                              {task.new_links_created !== undefined && task.new_links_created > 0 && (
                                <div className="text-green-600">{task.new_links_created} new links</div>
                              )}
                            </div>
                          ) : task.task_type === 'workflow' ? (
                            <div className="text-xs space-y-1">
                              {task.nodes_executed !== undefined && (
                                <div>{task.nodes_executed} nodes executed</div>
                              )}
                              {task.execution_data && (
                                <div className="text-muted-foreground truncate max-w-[150px]">
                                  {typeof task.execution_data === 'string' 
                                    ? task.execution_data.substring(0, 50) 
                                    : JSON.stringify(task.execution_data).substring(0, 50)}...
                                </div>
                              )}
                            </div>
                          ) : task.task_type === 'ai' ? (
                            <div className="text-xs space-y-1">
                              {task.usage?.tokens_used !== undefined && (
                                <div>{task.usage.tokens_used} tokens</div>
                              )}
                              {task.cost !== undefined && (
                                <div>${task.cost.toFixed(4)}</div>
                              )}
                              {task.result && (
                                <div className="text-muted-foreground truncate max-w-[150px]">
                                  {task.result.substring(0, 50)}...
                                </div>
                              )}
                            </div>
                          ) : '-'}
                        </TableCell>
                        <TableCell className="text-xs">
                          {formatDuration(task.duration_ms)}
                        </TableCell>
                        <TableCell>
                          <div className="text-xs">
                            <div>{task.triggered_by || 'System'}</div>
                            {task.trigger_reason && (
                              <div className="text-muted-foreground">{task.trigger_reason}</div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setTaskDetailsDialog(task)}
                          >
                            <ExternalLink className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Redis Stats Tab */}
        <TabsContent value="redis" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Redis Server Info */}
            <Card>
              <CardHeader>
                <CardTitle>Redis Server</CardTitle>
                <CardDescription>
                  Redis version {redisStats?.redis.version}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Uptime</span>
                  <span className="font-medium">{redisStats?.redis.uptime_days} days</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Connected Clients</span>
                  <span className="font-medium">{redisStats?.redis.connected_clients}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Memory Usage</span>
                  <span className="font-medium">{redisStats?.redis.used_memory_human}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Peak Memory</span>
                  <span className="font-medium">{redisStats?.redis.used_memory_peak_human}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Total Commands</span>
                  <span className="font-medium">{redisStats?.redis.total_commands_processed?.toLocaleString()}</span>
                </div>
              </CardContent>
            </Card>

            {/* Celery Stats */}
            <Card>
              <CardHeader>
                <CardTitle>Celery Stats</CardTitle>
                <CardDescription>
                  Task results and queue metrics
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Stored Task Results</span>
                  <span className="font-medium">{redisStats?.celery.task_results}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Unacked Messages</span>
                  <span className="font-medium">{redisStats?.celery.unacked}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Total Messages</span>
                  <span className="font-medium">{redisStats?.total_messages}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Current Tenant</span>
                  <span className="font-medium">{redisStats?.tenant}</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Queue Details */}
          {redisStats?.queues && Object.keys(redisStats.queues).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Redis Queue Details</CardTitle>
                <CardDescription>
                  All queues and their current state
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[400px]">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Queue Name</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Size</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {Object.entries(redisStats.queues).map(([name, info]) => (
                        <TableRow key={name}>
                          <TableCell className="font-mono text-xs">{name}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{info.type}</Badge>
                          </TableCell>
                          <TableCell>{info.length || info.count || 0}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </ScrollArea>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Scheduled Tasks Tab */}
        <TabsContent value="scheduled" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Scheduled Tasks</CardTitle>
              <CardDescription>
                Tasks scheduled for future execution
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-muted-foreground">
                <Clock className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Scheduled tasks monitoring coming soon</p>
                <p className="text-sm mt-2">Will show ETA tasks and periodic tasks</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Purge Queue Confirmation Dialog */}
      <Dialog open={purgeDialogOpen} onOpenChange={setPurgeDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Purge Queue?</DialogTitle>
            <DialogDescription>
              Are you sure you want to purge all tasks from the <strong>{queueToPurge}</strong> queue?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPurgeDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handlePurgeQueue}>
              Purge Queue
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Task Details Dialog */}
      <Dialog open={!!taskDetailsDialog} onOpenChange={() => setTaskDetailsDialog(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Task Details</DialogTitle>
            <DialogDescription>
              Full details for task {taskDetailsDialog?.id}
            </DialogDescription>
          </DialogHeader>
          {taskDetailsDialog && (
            <div className="space-y-4">
              {/* Record Information */}
              {taskDetailsDialog.record_id && (
                <div className="bg-secondary/50 p-4 rounded-lg space-y-2">
                  <h4 className="font-semibold text-sm">Record Information</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Record</p>
                      <p className="font-medium">{taskDetailsDialog.record_name || `Record #${taskDetailsDialog.record_id}`}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Pipeline</p>
                      <p className="font-medium">{taskDetailsDialog.pipeline_name || '-'}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Task Information */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Task Type</p>
                  <div className="flex items-center gap-1">
                    {taskDetailsDialog.task_type === 'sync' && (
                      <Badge variant="outline" className="text-xs">
                        🔄 Sync
                      </Badge>
                    )}
                    {taskDetailsDialog.task_type === 'ai' && (
                      <Badge variant="outline" className="text-xs">
                        🤖 AI
                      </Badge>
                    )}
                    {taskDetailsDialog.task_type === 'workflow' && (
                      <Badge variant="outline" className="text-xs">
                        ⚡ Workflow
                      </Badge>
                    )}
                    {!taskDetailsDialog.task_type && (
                      <p className="font-mono text-sm">{taskDetailsDialog.job_type || taskDetailsDialog.task_name}</p>
                    )}
                  </div>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <div>{getStatusBadge(taskDetailsDialog.status)}</div>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Triggered By</p>
                  <p className="text-sm">{taskDetailsDialog.triggered_by || 'System'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Trigger Reason</p>
                  <p className="text-sm">{taskDetailsDialog.trigger_reason || 'Manual'}</p>
                </div>
              </div>

              {/* Timing Information */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Created</p>
                  <p className="text-sm">
                    {taskDetailsDialog.created_at ? new Date(taskDetailsDialog.created_at).toLocaleString() : '-'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Started</p>
                  <p className="text-sm">
                    {taskDetailsDialog.started_at ? new Date(taskDetailsDialog.started_at).toLocaleString() : '-'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Completed</p>
                  <p className="text-sm">
                    {taskDetailsDialog.completed_at ? new Date(taskDetailsDialog.completed_at).toLocaleString() : '-'}
                  </p>
                </div>
              </div>

              {/* Progress Information */}
              {(taskDetailsDialog.progress_percentage !== undefined || taskDetailsDialog.accounts_synced !== undefined) && (
                <div className="space-y-2">
                  <h4 className="font-semibold text-sm">Progress</h4>
                  {taskDetailsDialog.progress_percentage !== undefined && (
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2">
                        <Progress value={taskDetailsDialog.progress_percentage} className="flex-1" />
                        <span className="text-sm font-medium">{taskDetailsDialog.progress_percentage}%</span>
                      </div>
                      {taskDetailsDialog.current_step && (
                        <p className="text-sm text-muted-foreground">{taskDetailsDialog.current_step}</p>
                      )}
                    </div>
                  )}
                  {taskDetailsDialog.accounts_synced !== undefined && (
                    <p className="text-sm">
                      Synced {taskDetailsDialog.accounts_synced} of {taskDetailsDialog.total_accounts_to_sync} accounts
                    </p>
                  )}
                </div>
              )}

              {/* Task-specific Results */}
              {/* Sync Results */}
              {taskDetailsDialog.task_type === 'sync' && (
                taskDetailsDialog.messages_synced !== undefined || 
                taskDetailsDialog.conversations_created !== undefined || 
                taskDetailsDialog.new_links_created !== undefined ||
                taskDetailsDialog.messages_found !== undefined ||
                taskDetailsDialog.conversations_found !== undefined) && (
                <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg space-y-2">
                  <h4 className="font-semibold text-sm">Sync Results</h4>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Messages</p>
                      <p className="font-semibold text-lg">{taskDetailsDialog.messages_synced ?? taskDetailsDialog.messages_found ?? 0}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Conversations</p>
                      <p className="font-semibold text-lg">{taskDetailsDialog.conversations_created ?? taskDetailsDialog.conversations_found ?? 0}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">New Links Created</p>
                      <p className="font-semibold text-lg text-green-600">{taskDetailsDialog.new_links_created ?? 0}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* AI Results */}
              {taskDetailsDialog.task_type === 'ai' && (
                <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg space-y-2">
                  <h4 className="font-semibold text-sm">AI Processing Results</h4>
                  {taskDetailsDialog.job_type && (
                    <div className="mb-2">
                      <p className="text-sm text-muted-foreground">Job Type</p>
                      <p className="text-sm">{taskDetailsDialog.job_type}</p>
                    </div>
                  )}
                  {taskDetailsDialog.model && (
                    <div className="mb-2">
                      <p className="text-sm text-muted-foreground">Model</p>
                      <p className="text-sm">{taskDetailsDialog.model}</p>
                    </div>
                  )}
                  {taskDetailsDialog.prompt && (
                    <div className="mb-2">
                      <p className="text-sm text-muted-foreground">Prompt</p>
                      <p className="text-sm text-muted-foreground">{taskDetailsDialog.prompt}</p>
                    </div>
                  )}
                  {(taskDetailsDialog.usage || taskDetailsDialog.cost !== undefined) && (
                    <div className="grid grid-cols-2 gap-4">
                      {taskDetailsDialog.usage?.tokens_used && (
                        <div>
                          <p className="text-sm text-muted-foreground">Tokens Used</p>
                          <p className="font-semibold">{taskDetailsDialog.usage.tokens_used}</p>
                        </div>
                      )}
                      {taskDetailsDialog.cost !== undefined && (
                        <div>
                          <p className="text-sm text-muted-foreground">Cost</p>
                          <p className="font-semibold">${taskDetailsDialog.cost.toFixed(4)}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Workflow Results */}
              {taskDetailsDialog.task_type === 'workflow' && (
                <div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg space-y-2">
                  <h4 className="font-semibold text-sm">Workflow Execution Results</h4>
                  {taskDetailsDialog.workflow_name && (
                    <div className="mb-2">
                      <p className="text-sm text-muted-foreground">Workflow</p>
                      <p className="text-sm font-medium">{taskDetailsDialog.workflow_name}</p>
                    </div>
                  )}
                  {taskDetailsDialog.nodes_executed !== undefined && (
                    <div className="mb-2">
                      <p className="text-sm text-muted-foreground">Nodes Executed</p>
                      <p className="font-semibold">{taskDetailsDialog.nodes_executed}</p>
                    </div>
                  )}
                  {taskDetailsDialog.trigger_data && (
                    <div>
                      <p className="text-sm text-muted-foreground">Trigger Data</p>
                      <pre className="text-xs bg-secondary p-2 rounded overflow-x-auto mt-1">
                        {JSON.stringify(taskDetailsDialog.trigger_data, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}

              {/* Legacy Results (for backwards compatibility) */}
              {!taskDetailsDialog.task_type && (
                taskDetailsDialog.messages_found !== undefined || 
                taskDetailsDialog.conversations_found !== undefined || 
                taskDetailsDialog.new_links_created !== undefined) && (
                <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg space-y-2">
                  <h4 className="font-semibold text-sm">Results</h4>
                  <div className="grid grid-cols-3 gap-4">
                    {taskDetailsDialog.messages_found !== undefined && (
                      <div>
                        <p className="text-sm text-muted-foreground">Messages Found</p>
                        <p className="font-semibold text-lg">{taskDetailsDialog.messages_found}</p>
                      </div>
                    )}
                    {taskDetailsDialog.conversations_found !== undefined && (
                      <div>
                        <p className="text-sm text-muted-foreground">Conversations Found</p>
                        <p className="font-semibold text-lg">{taskDetailsDialog.conversations_found}</p>
                      </div>
                    )}
                    {taskDetailsDialog.new_links_created !== undefined && (
                      <div>
                        <p className="text-sm text-muted-foreground">New Links Created</p>
                        <p className="font-semibold text-lg text-green-600">{taskDetailsDialog.new_links_created}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Performance */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Duration</p>
                  <p className="text-sm font-medium">{formatDuration(taskDetailsDialog.duration_ms)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Celery Task ID</p>
                  <p className="text-sm font-mono truncate">{taskDetailsDialog.celery_task_id || taskDetailsDialog.id}</p>
                </div>
              </div>
              
              {taskDetailsDialog.error_message && (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">Error Message</p>
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription className="font-mono text-xs">
                      {taskDetailsDialog.error_message}
                    </AlertDescription>
                  </Alert>
                </div>
              )}

              {taskDetailsDialog.result && (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">Result</p>
                  <pre className="bg-secondary p-2 rounded text-xs overflow-auto max-h-[200px]">
                    {taskDetailsDialog.result}
                  </pre>
                </div>
              )}

              {taskDetailsDialog.traceback && (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">Traceback</p>
                  <ScrollArea className="h-[200px] bg-destructive/10 p-2 rounded">
                    <pre className="text-xs text-destructive">
                      {taskDetailsDialog.traceback}
                    </pre>
                  </ScrollArea>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setTaskDetailsDialog(null)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}