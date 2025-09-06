"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
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
  Info
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

interface QueueStatus {
  [key: string]: number
}

interface WorkerInfo {
  name: string
  hostname: string
  status: string
  active_tasks: number
  processed: number
  failed: number
  pool: string
  concurrency: number
  uptime: string
}

interface CeleryOverview {
  status: string
  timestamp: string
  current_tenant?: string
  summary: {
    workers_online: number
    total_queued: number
    tenant_queued?: number
    total_active: number
    tasks_24h: number
    failed_24h: number
  }
  queues: QueueStatus
  workers: WorkerInfo[]
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

export default function CelerySettingsPage() {
  const [overview, setOverview] = useState<CeleryOverview | null>(null)
  const [activeTasks, setActiveTasks] = useState<ActiveTask[]>([])
  const [selectedQueue, setSelectedQueue] = useState<string>("")
  const [queueTasks, setQueueTasks] = useState<QueueTask[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [purgeDialogOpen, setPurgeDialogOpen] = useState(false)
  const [queueToPurge, setQueueToPurge] = useState<string>("")
  const [error, setError] = useState<string | null>(null)
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
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      })
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

  const fetchQueueDetails = async (queueName: string) => {
    try {
      const response = await api.get(`/api/v1/celery/queue_details/?queue=${queueName}`)
      setQueueTasks(response.data.tasks || [])
    } catch (error) {
      console.error("Failed to fetch queue details:", error)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await Promise.all([fetchOverview(), fetchActiveTasks()])
    if (selectedQueue) {
      await fetchQueueDetails(selectedQueue)
    }
    setRefreshing(false)
    toast({
      title: "Refreshed",
      description: "Celery status updated",
    })
  }

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

  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      await Promise.all([fetchOverview(), fetchActiveTasks()])
      setLoading(false)
    }
    loadData()

    // Auto-refresh every 10 seconds
    const interval = setInterval(() => {
      fetchOverview()
      fetchActiveTasks()
    }, 10000)

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (selectedQueue) {
      fetchQueueDetails(selectedQueue)
    }
  }, [selectedQueue])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600'
      case 'degraded':
        return 'text-yellow-600'
      case 'error':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  const getQueueBadgeColor = (count: number) => {
    if (count === 0) return 'secondary'
    if (count < 10) return 'default'
    if (count < 50) return 'outline'
    return 'destructive'
  }

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
        <div className="flex gap-2">
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
            {overview.summary.total_queued} tasks queued
            {overview.summary.tenant_queued !== undefined && ` (${overview.summary.tenant_queued} for this tenant)`} • 
            {overview.summary.total_active} tasks active • 
            {overview.summary.tasks_24h} tenant tasks in last 24h
            {overview.summary.failed_24h > 0 && ` • ${overview.summary.failed_24h} failed`}
          </AlertDescription>
        </Alert>
      )}

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Workers</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview?.summary.workers_online || 0}</div>
            <p className="text-xs text-muted-foreground">
              Online and processing
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Queued Tasks</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview?.summary.total_queued || 0}</div>
            <p className="text-xs text-muted-foreground">
              Waiting to be processed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Tasks</CardTitle>
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
            <CardTitle className="text-sm font-medium">24h Stats</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview?.summary.tasks_24h || 0}</div>
            <p className="text-xs text-muted-foreground">
              {overview?.summary.failed_24h || 0} failed (tenant only)
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="queues" className="space-y-4">
        <TabsList>
          <TabsTrigger value="queues">Queues</TabsTrigger>
          <TabsTrigger value="workers">Workers</TabsTrigger>
          <TabsTrigger value="active">Active Tasks</TabsTrigger>
        </TabsList>

        {/* Queues Tab */}
        <TabsContent value="queues" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Task Queues</CardTitle>
              <CardDescription>
                Monitor and manage task queues
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {overview?.queues && Object.entries(overview.queues).map(([queueName, count]) => (
                  <div key={queueName} className="flex items-center justify-between p-4 border rounded-lg">
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
                  <h4 className="font-medium mb-2">Tasks in {selectedQueue}</h4>
                  <ScrollArea className="h-[300px]">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Task</TableHead>
                          <TableHead>ID</TableHead>
                          <TableHead>ETA</TableHead>
                          <TableHead>Retries</TableHead>
                          <TableHead>Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {queueTasks.map((task) => (
                          <TableRow key={task.id}>
                            <TableCell className="font-mono text-xs">
                              {task.task.split('.').slice(-1)[0]}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {task.id.substring(0, 8)}...
                            </TableCell>
                            <TableCell>
                              {task.eta ? new Date(task.eta).toLocaleString() : '-'}
                            </TableCell>
                            <TableCell>{task.retries}</TableCell>
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
              <CardTitle>Celery Workers</CardTitle>
              <CardDescription>
                Monitor worker status and performance
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Worker</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Active</TableHead>
                    <TableHead>Processed</TableHead>
                    <TableHead>Failed</TableHead>
                    <TableHead>Pool</TableHead>
                    <TableHead>Uptime</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {overview?.workers.map((worker) => (
                    <TableRow key={worker.hostname}>
                      <TableCell className="font-medium">{worker.name}</TableCell>
                      <TableCell>
                        <Badge variant={worker.status === 'online' ? 'default' : 'destructive'}>
                          {worker.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{worker.active_tasks}</TableCell>
                      <TableCell>{worker.processed}</TableCell>
                      <TableCell>{worker.failed}</TableCell>
                      <TableCell className="text-sm">{worker.pool}</TableCell>
                      <TableCell>{worker.uptime}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
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
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Worker</TableHead>
                      <TableHead>Task</TableHead>
                      <TableHead>ID</TableHead>
                      <TableHead>Runtime</TableHead>
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
                        <TableCell className="font-mono text-xs">
                          {task.id.substring(0, 8)}...
                        </TableCell>
                        <TableCell>{task.runtime}</TableCell>
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
              )}
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
    </div>
  )
}