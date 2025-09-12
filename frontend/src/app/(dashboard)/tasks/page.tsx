'use client'

import React, { useState, useEffect } from 'react'
import { CheckSquare, Plus, Calendar, Clock, User, AlertCircle, Flag, Filter, Search, LayoutGrid, List } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api'
import { toast } from '@/hooks/use-toast'
import { useAuth } from '@/features/auth/context'
import { format } from 'date-fns'
import { TaskDetailDrawer } from './TaskDetailDrawer'
import { TasksKanbanView } from './TasksKanbanView'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'

interface Task {
  id: string
  title: string
  description?: string
  priority: 'low' | 'medium' | 'high' | 'urgent'
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled'
  due_date?: string
  reminder_at?: string
  completed_at?: string
  record?: {
    id: string
    data?: any
  }
  record_id?: string
  record_name?: string
  pipeline_id?: string
  pipeline_name?: string
  assigned_to?: {
    id: string
    email: string
    first_name?: string
    last_name?: string
    full_name?: string
  }
  assigned_to_name?: string
  assigned_to_email?: string
  created_by?: {
    id: string
    email: string
    first_name?: string
    last_name?: string
  }
  created_by_name?: string
  created_by_email?: string
  is_overdue?: boolean
  comments_count?: number
  attachments_count?: number
  created_at: string
  updated_at: string
}

export default function TasksPage() {
  const { user: currentUser } = useAuth()
  const [tasks, setTasks] = useState<Task[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [priorityFilter, setPriorityFilter] = useState<string>('all')
  const [assigneeFilter, setAssigneeFilter] = useState<string>('all')
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [users, setUsers] = useState<any[]>([])
  const [viewMode, setViewMode] = useState<'list' | 'kanban'>('kanban')

  // Fetch all tasks
  const fetchTasks = async () => {
    setIsLoading(true)
    try {
      const response = await api.get('/api/v1/tasks/')
      const tasksList = Array.isArray(response.data) ? response.data : 
                       response.data.results || []
      setTasks(tasksList)
    } catch (error) {
      console.error('Failed to fetch tasks:', error)
      toast({
        title: 'Failed to Load Tasks',
        description: 'Could not load tasks. Please try again.',
        variant: 'destructive'
      })
      setTasks([])
    } finally {
      setIsLoading(false)
    }
  }

  // Fetch users for assignment
  const fetchUsers = async () => {
    try {
      const response = await api.get('/auth/users/')
      const usersList = response.data?.results || response.data || []
      setUsers(usersList)
    } catch (error) {
      console.error('Failed to fetch users:', error)
    }
  }

  useEffect(() => {
    fetchTasks()
    fetchUsers()
  }, [])

  // Filter tasks based on search and filters
  const filteredTasks = tasks.filter(task => {
    // Search filter
    if (searchTerm && !task.title.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !task.description?.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false
    }

    // Status filter
    if (statusFilter !== 'all' && task.status !== statusFilter) {
      return false
    }

    // Priority filter
    if (priorityFilter !== 'all' && task.priority !== priorityFilter) {
      return false
    }

    // Assignee filter
    if (assigneeFilter === 'mine' && task.assigned_to?.id !== String(currentUser?.id)) {
      return false
    } else if (assigneeFilter === 'unassigned' && task.assigned_to) {
      return false
    }

    return true
  })

  // Update task status
  const updateTaskStatus = async (taskId: string, newStatus: string) => {
    try {
      await api.patch(`/api/v1/tasks/${taskId}/`, {
        status: newStatus
      })
      
      toast({
        title: 'Task Updated',
        description: 'Task status has been updated successfully.',
      })
      
      // Refresh tasks
      fetchTasks()
    } catch (error) {
      console.error('Failed to update task:', error)
      toast({
        title: 'Update Failed',
        description: 'Could not update the task status.',
        variant: 'destructive'
      })
    }
  }

  // Get priority color and icon
  const getPriorityBadge = (priority: string) => {
    const configs = {
      urgent: { color: 'bg-red-500', icon: AlertCircle, text: 'Urgent' },
      high: { color: 'bg-orange-500', icon: Flag, text: 'High' },
      medium: { color: 'bg-yellow-500', icon: Flag, text: 'Medium' },
      low: { color: 'bg-gray-400', icon: Flag, text: 'Low' }
    }
    
    const config = configs[priority as keyof typeof configs] || configs.medium
    const Icon = config.icon
    
    return (
      <Badge className={`${config.color} text-white`}>
        <Icon className="w-3 h-3 mr-1" />
        {config.text}
      </Badge>
    )
  }

  // Get status badge
  const getStatusBadge = (status: string) => {
    const configs = {
      pending: { color: 'bg-gray-500', text: 'Pending' },
      in_progress: { color: 'bg-blue-500', text: 'In Progress' },
      completed: { color: 'bg-green-500', text: 'Completed' },
      cancelled: { color: 'bg-red-500', text: 'Cancelled' }
    }
    
    const config = configs[status as keyof typeof configs] || configs.pending
    
    return (
      <Badge className={`${config.color} text-white`}>
        {config.text}
      </Badge>
    )
  }

  // Group tasks by status
  const tasksByStatus = {
    pending: filteredTasks.filter(t => t.status === 'pending'),
    in_progress: filteredTasks.filter(t => t.status === 'in_progress'),
    completed: filteredTasks.filter(t => t.status === 'completed'),
    cancelled: filteredTasks.filter(t => t.status === 'cancelled')
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <CheckSquare className="w-8 h-8" />
              Tasks Management
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Manage and track all your tasks across records
            </p>
          </div>
          <Button className="flex items-center gap-2">
            <Plus className="w-4 h-4" />
            New Task
          </Button>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-4 items-center">
              {/* View Mode Toggle */}
              <ToggleGroup type="single" value={viewMode} onValueChange={(value) => value && setViewMode(value as 'list' | 'kanban')}>
                <ToggleGroupItem value="kanban" aria-label="Kanban view">
                  <LayoutGrid className="h-4 w-4 mr-2" />
                  Kanban
                </ToggleGroupItem>
                <ToggleGroupItem value="list" aria-label="List view">
                  <List className="h-4 w-4 mr-2" />
                  List
                </ToggleGroupItem>
              </ToggleGroup>

              <div className="h-8 w-px bg-gray-300 dark:bg-gray-600" />
              {/* Search */}
              <div className="flex-1 min-w-[200px]">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="text"
                    placeholder="Search tasks..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>

              {/* Status Filter */}
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>

              {/* Priority Filter */}
              <Select value={priorityFilter} onValueChange={setPriorityFilter}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="All Priorities" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Priorities</SelectItem>
                  <SelectItem value="urgent">Urgent</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>

              {/* Assignee Filter */}
              <Select value={assigneeFilter} onValueChange={setAssigneeFilter}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="All Assignees" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Tasks</SelectItem>
                  <SelectItem value="mine">My Tasks</SelectItem>
                  <SelectItem value="unassigned">Unassigned</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Stats */}
            <div className="flex gap-4 mt-4 text-sm text-gray-600 dark:text-gray-400">
              <span>Total: {filteredTasks.length}</span>
              <span>•</span>
              <span>Pending: {tasksByStatus.pending.length}</span>
              <span>•</span>
              <span>In Progress: {tasksByStatus.in_progress.length}</span>
              <span>•</span>
              <span>Completed: {tasksByStatus.completed.length}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tasks Display */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-500">Loading tasks...</div>
        </div>
      ) : viewMode === 'kanban' ? (
        // Kanban View
        <TasksKanbanView
          tasks={tasks}
          onTaskClick={(task) => {
            setSelectedTask(task)
            setIsModalOpen(true)
          }}
          onTaskUpdate={fetchTasks}
          searchTerm={searchTerm}
          priorityFilter={priorityFilter}
          assigneeFilter={assigneeFilter}
          currentUserId={String(currentUser?.id)}
        />
      ) : filteredTasks.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center h-64">
            <CheckSquare className="w-12 h-12 text-gray-400 mb-4" />
            <p className="text-gray-500 text-lg">No tasks found</p>
            <p className="text-gray-400 text-sm mt-1">
              {searchTerm || statusFilter !== 'all' || priorityFilter !== 'all' || assigneeFilter !== 'all'
                ? 'Try adjusting your filters'
                : 'Create your first task to get started'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {filteredTasks.map((task) => (
            <Card 
              key={task.id} 
              className="hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => {
                setSelectedTask(task)
                setIsModalOpen(true)
              }}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-start gap-3">
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg text-gray-900 dark:text-white">
                          {task.title}
                        </h3>
                        {task.description && (
                          <p className="text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                            {task.description}
                          </p>
                        )}
                        
                        <div className="flex flex-wrap items-center gap-4 mt-3 text-sm text-gray-500 dark:text-gray-400">
                          {/* Assignee */}
                          <div className="flex items-center gap-1">
                            <User className="w-4 h-4" />
                            <span>
                              {task.assigned_to ? (
                                task.assigned_to_name || task.assigned_to.email
                              ) : (
                                'Unassigned'
                              )}
                            </span>
                          </div>

                          {/* Due Date */}
                          {task.due_date && (
                            <div className="flex items-center gap-1">
                              <Calendar className="w-4 h-4" />
                              <span className={task.is_overdue ? 'text-red-500 font-medium' : ''}>
                                {format(new Date(task.due_date), 'MMM d, yyyy')}
                                {task.is_overdue && ' (Overdue)'}
                              </span>
                            </div>
                          )}

                          {/* Record */}
                          {(task.record || task.record_id) && (
                            <div className="flex items-center gap-1">
                              <span>
                                {task.record_name || `Record #${task.record_id || task.record?.id}`}
                                {task.pipeline_name && ` (${task.pipeline_name})`}
                              </span>
                            </div>
                          )}

                          {/* Comments/Attachments */}
                          {(task.comments_count || task.attachments_count) && (
                            <div className="flex items-center gap-2">
                              {task.comments_count > 0 && (
                                <span>{task.comments_count} comments</span>
                              )}
                              {task.attachments_count > 0 && (
                                <span>{task.attachments_count} files</span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex flex-col gap-2 items-end">
                        {getPriorityBadge(task.priority)}
                        {getStatusBadge(task.status)}
                      </div>
                    </div>
                  </div>

                  {/* Quick Actions */}
                  <div className="ml-4" onClick={(e) => e.stopPropagation()}>
                    <Select
                      value={task.status}
                      onValueChange={(value) => updateTaskStatus(task.id, value)}
                    >
                      <SelectTrigger className="w-[140px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="pending">Pending</SelectItem>
                        <SelectItem value="in_progress">In Progress</SelectItem>
                        <SelectItem value="completed">Completed</SelectItem>
                        <SelectItem value="cancelled">Cancelled</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Task Detail Drawer */}
      <TaskDetailDrawer
        task={selectedTask}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedTask(null)
        }}
        onUpdate={fetchTasks}
        users={users}
      />
    </div>
  )
}