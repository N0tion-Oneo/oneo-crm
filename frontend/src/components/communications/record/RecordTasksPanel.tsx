'use client'

import React, { useState, useEffect } from 'react'
import { 
  CheckSquare, 
  Plus, 
  RefreshCw, 
  AlertCircle,
  Loader2,
  Clock,
  Calendar,
  Flag,
  User,
  ChevronDown,
  ChevronUp,
  Check,
  X,
  Edit2,
  ListTodo
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { TaskCreator } from './TaskCreator'
import { api } from '@/lib/api'
import { toast } from '@/hooks/use-toast'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface ChecklistItem {
  id: string
  text: string
  is_completed: boolean
  order: number
  completed_at?: string
  completed_by?: string
}

interface Task {
  id: string
  title: string
  description?: string
  priority: 'low' | 'medium' | 'high' | 'urgent'
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled'
  due_date?: string
  reminder_at?: string
  assigned_to?: string
  assigned_to_name?: string
  assigned_to_email?: string
  created_at: string
  updated_at: string
  completed_at?: string
  metadata?: any
  checklist_items?: ChecklistItem[]
  checklist_progress?: {
    completed: number
    total: number
    percentage: number
  }
  is_overdue?: boolean
  record_name?: string
  pipeline_name?: string
  created_by_name?: string
  created_by_email?: string
}

interface RecordTasksPanelProps {
  recordId: string
  pipelineId: string
}

export function RecordTasksPanel({ 
  recordId
}: RecordTasksPanelProps) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isCreatingTask, setIsCreatingTask] = useState(false)
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set())
  const [filter, setFilter] = useState<'all' | 'pending' | 'in_progress' | 'completed'>('all')
  const [sortBy, setSortBy] = useState<'priority' | 'due_date' | 'created'>('priority')
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [isEditingTask, setIsEditingTask] = useState(false)

  // Fetch tasks for this record
  const fetchTasks = async () => {
    try {
      const response = await api.get(`/api/v1/tasks/record/${recordId}/`)
      setTasks(response.data.tasks || [])
    } catch (error) {
      console.error('Failed to fetch tasks:', error)
      toast({
        title: 'Failed to Load Tasks',
        description: 'Could not load tasks for this record',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchTasks()
  }, [recordId])

  // Update task status
  const updateTaskStatus = async (taskId: string, status: Task['status']) => {
    try {
      await api.patch(`/api/v1/tasks/${taskId}/status/`, { status })
      
      // Update local state
      setTasks(prev => prev.map(task => 
        task.id === taskId 
          ? { 
              ...task, 
              status, 
              completed_at: status === 'completed' ? new Date().toISOString() : undefined 
            }
          : task
      ))

      toast({
        title: 'Task Updated',
        description: `Task marked as ${status}`,
      })
    } catch (error) {
      console.error('Failed to update task:', error)
      toast({
        title: 'Failed to Update Task',
        description: 'Could not update task status',
        variant: 'destructive'
      })
    }
  }

  // Delete task
  const deleteTask = async (taskId: string) => {
    try {
      await api.delete(`/api/v1/tasks/${taskId}/`)
      
      // Update local state
      setTasks(prev => prev.filter(task => task.id !== taskId))

      toast({
        title: 'Task Deleted',
        description: 'Task has been removed',
      })
    } catch (error) {
      console.error('Failed to delete task:', error)
      toast({
        title: 'Failed to Delete Task',
        description: 'Could not delete task',
        variant: 'destructive'
      })
    }
  }

  // Open task for editing
  const openTaskEditor = (task: Task) => {
    setSelectedTask(task)
    setIsEditingTask(true)
    setIsCreatingTask(false) // Close create mode if open
  }

  // Handle task editor close
  const handleTaskEditorClose = () => {
    setSelectedTask(null)
    setIsEditingTask(false)
    fetchTasks() // Refresh tasks after potential updates
  }

  // Toggle task expansion
  const toggleTaskExpansion = (taskId: string) => {
    setExpandedTasks(prev => {
      const newSet = new Set(prev)
      if (newSet.has(taskId)) {
        newSet.delete(taskId)
      } else {
        newSet.add(taskId)
      }
      return newSet
    })
  }

  // Get priority color and icon
  const getPriorityDisplay = (priority: Task['priority']) => {
    switch (priority) {
      case 'urgent':
        return { color: 'text-red-600 dark:text-red-400', icon: <AlertCircle className="w-4 h-4" /> }
      case 'high':
        return { color: 'text-orange-600 dark:text-orange-400', icon: <Flag className="w-4 h-4" /> }
      case 'medium':
        return { color: 'text-yellow-600 dark:text-yellow-400', icon: <Flag className="w-4 h-4" /> }
      case 'low':
        return { color: 'text-gray-600 dark:text-gray-400', icon: <Flag className="w-4 h-4" /> }
      default:
        return { color: '', icon: <Flag className="w-4 h-4" /> }
    }
  }

  // Get status color
  const getStatusColor = (status: Task['status']) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
      case 'in_progress':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'
      case 'cancelled':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300'
      default:
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300'
    }
  }

  // Filter and sort tasks
  const filteredTasks = tasks
    .filter(task => {
      if (filter === 'all') return true
      return task.status === filter
    })
    .sort((a, b) => {
      if (sortBy === 'priority') {
        const priorityOrder = { urgent: 0, high: 1, medium: 2, low: 3 }
        return priorityOrder[a.priority] - priorityOrder[b.priority]
      } else if (sortBy === 'due_date') {
        if (!a.due_date) return 1
        if (!b.due_date) return -1
        return new Date(a.due_date).getTime() - new Date(b.due_date).getTime()
      } else {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      }
    })

  // Get task counts by status
  const taskCounts = {
    all: tasks.length,
    pending: tasks.filter(t => t.status === 'pending').length,
    in_progress: tasks.filter(t => t.status === 'in_progress').length,
    completed: tasks.filter(t => t.status === 'completed').length,
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header - Compact to match other tabs */}
      <div className="flex-shrink-0 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="flex items-center justify-between p-3 gap-3">
          {/* New Task button */}
          <Button
            onClick={() => setIsCreatingTask(true)}
            size="sm"
            variant="outline"
            className="mr-2"
          >
            <Plus className="w-4 h-4 mr-1" />
            New Task
          </Button>
          
          {/* Filter tabs */}
          <div className="flex-1">
            <div className="flex gap-1 bg-gray-100 dark:bg-gray-900 rounded-lg p-1">
              {(['all', 'pending', 'in_progress', 'completed'] as const).map(status => (
                <button
                  key={status}
                  onClick={() => setFilter(status)}
                  className={`flex-1 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                    filter === status
                      ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
                      : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  {status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  <span className="ml-1.5 text-xs">
                    ({taskCounts[status]})
                  </span>
                </button>
              ))}
            </div>
          </div>
          
          {/* Sort and Refresh */}
          <div className="flex items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm">
                  <ChevronDown className="w-4 h-4 mr-1" />
                  {sortBy === 'priority' ? 'Priority' : sortBy === 'due_date' ? 'Due Date' : 'Created'}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setSortBy('priority')}>
                  Sort by Priority
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setSortBy('due_date')}>
                  Sort by Due Date
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setSortBy('created')}>
                  Sort by Created Date
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <Button
              onClick={fetchTasks}
              variant="ghost"
              size="sm"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Task List or Creator/Editor */}
      <div className="flex-1 overflow-y-auto p-4">
        {(isCreatingTask || isEditingTask) ? (
          <Card>
            <CardContent className="p-0">
              <TaskCreator
                recordId={recordId}
                task={isEditingTask ? selectedTask : null}
                onTaskCreated={() => {
                  setIsCreatingTask(false)
                  fetchTasks()
                }}
                onTaskUpdated={() => {
                  setIsEditingTask(false)
                  setSelectedTask(null)
                  fetchTasks()
                }}
                onCancel={() => {
                  setIsCreatingTask(false)
                  setIsEditingTask(false)
                  setSelectedTask(null)
                }}
              />
            </CardContent>
          </Card>
        ) : filteredTasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500">
            <CheckSquare className="w-12 h-12 mb-4 text-gray-400" />
            <p className="text-sm mb-4">
              {filter === 'all' 
                ? 'No tasks yet' 
                : `No ${filter.replace('_', ' ')} tasks`}
            </p>
            <Button
              onClick={() => setIsCreatingTask(true)}
              size="sm"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create First Task
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredTasks.map(task => {
              const priorityDisplay = getPriorityDisplay(task.priority)
              const isExpanded = expandedTasks.has(task.id)
              const isOverdue = task.due_date && new Date(task.due_date) < new Date() && task.status !== 'completed'
              
              return (
                <Card key={task.id} className={task.status === 'completed' ? 'opacity-75' : ''}>
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3 flex-1">
                        <Checkbox
                          checked={task.status === 'completed'}
                          onCheckedChange={(checked) => {
                            updateTaskStatus(task.id, checked ? 'completed' : 'pending')
                          }}
                          className="mt-1"
                        />
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className={`font-medium ${task.status === 'completed' ? 'line-through text-gray-500' : ''}`}>
                              {task.title}
                            </h3>
                            <span className={priorityDisplay.color}>
                              {priorityDisplay.icon}
                            </span>
                            <Badge className={getStatusColor(task.status)}>
                              {task.status.replace('_', ' ')}
                            </Badge>
                            {isOverdue && (
                              <Badge variant="destructive" className="text-xs">
                                Overdue
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                            {task.due_date && (
                              <span className={`flex items-center gap-1 ${isOverdue ? 'text-red-600 dark:text-red-400' : ''}`}>
                                <Calendar className="w-3 h-3" />
                                {new Date(task.due_date).toLocaleDateString()}
                              </span>
                            )}
                            {task.assigned_to_name || task.assigned_to ? (
                              <span className="flex items-center gap-1">
                                <User className="w-3 h-3" />
                                {task.assigned_to_name || task.assigned_to}
                              </span>
                            ) : null}
                            {task.checklist_progress && task.checklist_progress.total > 0 && (
                              <span className="flex items-center gap-1">
                                <ListTodo className="w-3 h-3" />
                                {task.checklist_progress.completed}/{task.checklist_progress.total} items
                              </span>
                            )}
                            {task.reminder_at && (
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                Reminder
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openTaskEditor(task)}
                          title="Edit task"
                        >
                          <Edit2 className="w-4 h-4" />
                        </Button>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              Status
                              <ChevronDown className="w-4 h-4 ml-1" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent>
                            <DropdownMenuItem onClick={() => updateTaskStatus(task.id, 'pending')}>
                              Pending
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => updateTaskStatus(task.id, 'in_progress')}>
                              In Progress
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => updateTaskStatus(task.id, 'completed')}>
                              Completed
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => updateTaskStatus(task.id, 'cancelled')}>
                              Cancelled
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleTaskExpansion(task.id)}
                        >
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => deleteTask(task.id)}
                        >
                          <X className="w-4 h-4 text-red-500" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  {isExpanded && task.description && (
                    <CardContent className="pt-0">
                      <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                        {task.description}
                      </p>
                      <div className="mt-3 text-xs text-gray-500">
                        Created: {new Date(task.created_at).toLocaleString()}
                        {task.completed_at && (
                          <span className="ml-4">
                            Completed: {new Date(task.completed_at).toLocaleString()}
                          </span>
                        )}
                      </div>
                    </CardContent>
                  )}
                </Card>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}