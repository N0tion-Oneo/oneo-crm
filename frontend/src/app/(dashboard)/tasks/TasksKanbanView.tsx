'use client'

import React, { useState, useMemo } from 'react'
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragOverEvent,
  DragEndEvent,
  UniqueIdentifier,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { CheckSquare, Calendar, User, AlertCircle, Flag, Plus } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { format } from 'date-fns'
import { api } from '@/lib/api'
import { toast } from '@/hooks/use-toast'

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
  updated_at: string}

interface TasksKanbanViewProps {
  tasks: Task[]
  onTaskClick: (task: Task) => void
  onTaskUpdate: () => void
  searchTerm: string
  priorityFilter: string
  assigneeFilter: string
  currentUserId?: string
}

interface KanbanColumn {
  id: 'pending' | 'in_progress' | 'completed' | 'cancelled'
  title: string
  color: string
  tasks: Task[]
}

// Sortable Task Card Component
function SortableTaskCard({ 
  task, 
  onClick,
  isDragging = false 
}: { 
  task: Task
  onClick: () => void
  isDragging?: boolean
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: task.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'urgent': return <AlertCircle className="w-3 h-3 text-red-500" />
      case 'high': return <Flag className="w-3 h-3 text-orange-500" />
      case 'medium': return <Flag className="w-3 h-3 text-yellow-500" />
      case 'low': return <Flag className="w-3 h-3 text-gray-400" />
      default: return <Flag className="w-3 h-3" />
    }
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`cursor-move ${isDragging ? 'z-50' : ''}`}
    >
      <Card 
        className="mb-3 hover:shadow-md transition-shadow cursor-pointer"
        onClick={(e) => {
          e.stopPropagation()
          onClick()
        }}
      >
        <CardContent className="p-3">
          <div className="flex items-start justify-between mb-2">
            <h4 className="font-medium text-sm line-clamp-2 flex-1">
              {task.title}
            </h4>
            <div className="ml-2">
              {getPriorityIcon(task.priority)}
            </div>
          </div>
          
          {task.description && (
            <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2 mb-2">
              {task.description}
            </p>
          )}

          {/* Record info */}
          {task.record_name && (
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-2 truncate">
              {task.record_name}
              {task.pipeline_name && (
                <span className="ml-1 text-gray-400">• {task.pipeline_name}</span>
              )}
            </div>
          )}

          <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
            <div className="flex items-center gap-3">
              {task.assigned_to && (
                <div className="flex items-center gap-1">
                  <User className="w-3 h-3" />
                  <span className="truncate max-w-[100px]">
                    {task.assigned_to_name || task.assigned_to.first_name || task.assigned_to.email.split('@')[0]}
                  </span>
                </div>
              )}
              
              {task.due_date && (
                <div className={`flex items-center gap-1 ${task.is_overdue ? 'text-red-500' : ''}`}>
                  <Calendar className="w-3 h-3" />
                  <span>{format(new Date(task.due_date), 'MMM d')}</span>
                </div>
              )}
            </div>

            {((task.comments_count && task.comments_count > 0) || (task.attachments_count && task.attachments_count > 0)) && (
              <div className="flex items-center gap-2">
                {task.comments_count && task.comments_count > 0 && (
                  <span className="text-xs">{task.comments_count} 💬</span>
                )}
                {task.attachments_count && task.attachments_count > 0 && (
                  <span className="text-xs">{task.attachments_count} 📎</span>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// Task Card for DragOverlay
function TaskCardOverlay({ task }: { task: Task }) {
  return (
    <Card className="shadow-xl opacity-90">
      <CardContent className="p-3">
        <h4 className="font-medium text-sm">{task.title}</h4>
      </CardContent>
    </Card>
  )
}

// Droppable Column Component
function DroppableColumn({ 
  column,
  onTaskClick 
}: { 
  column: KanbanColumn
  onTaskClick: (task: Task) => void
}) {
  const {
    setNodeRef,
    isOver,
  } = useSortable({
    id: column.id,
    data: {
      type: 'column',
      column,
    },
  })

  return (
    <div className="flex-shrink-0 w-80">
      <div 
        className={`bg-gray-50 dark:bg-gray-900 rounded-lg p-4 h-full transition-colors ${
          isOver ? 'bg-blue-50 dark:bg-blue-900/20' : ''
        }`}
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-sm">{column.title}</h3>
            <Badge variant="secondary" className="text-xs">
              {column.tasks.length}
            </Badge>
          </div>
        </div>

        <ScrollArea className="h-[calc(100vh-280px)]">
          <div
            ref={setNodeRef}
            className="min-h-[100px]"
          >
            <SortableContext
              items={column.tasks.map(t => t.id)}
              strategy={verticalListSortingStrategy}
            >
              {column.tasks.map((task) => (
                <SortableTaskCard
                  key={task.id}
                  task={task}
                  onClick={() => onTaskClick(task)}
                />
              ))}
            </SortableContext>
            
            {column.tasks.length === 0 && (
              <div className="text-center py-8 text-gray-400">
                <CheckSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No tasks</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  )
}

export function TasksKanbanView({
  tasks,
  onTaskClick,
  onTaskUpdate,
  searchTerm,
  priorityFilter,
  assigneeFilter,
  currentUserId
}: TasksKanbanViewProps) {
  const [activeId, setActiveId] = useState<UniqueIdentifier | null>(null)
  const [overId, setOverId] = useState<UniqueIdentifier | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // Filter tasks
  const filteredTasks = useMemo(() => {
    return tasks.filter(task => {
      // Search filter
      if (searchTerm && !task.title.toLowerCase().includes(searchTerm.toLowerCase()) &&
          !task.description?.toLowerCase().includes(searchTerm.toLowerCase())) {
        return false
      }

      // Priority filter
      if (priorityFilter !== 'all' && task.priority !== priorityFilter) {
        return false
      }

      // Assignee filter
      if (assigneeFilter === 'mine' && task.assigned_to?.id !== currentUserId) {
        return false
      } else if (assigneeFilter === 'unassigned' && task.assigned_to) {
        return false
      }

      return true
    })
  }, [tasks, searchTerm, priorityFilter, assigneeFilter, currentUserId])

  // Organize tasks into columns
  const columns: KanbanColumn[] = useMemo(() => {
    return [
      {
        id: 'pending',
        title: 'To Do',
        color: 'border-gray-200',
        tasks: filteredTasks.filter(t => t.status === 'pending')
      },
      {
        id: 'in_progress',
        title: 'In Progress',
        color: 'border-blue-200',
        tasks: filteredTasks.filter(t => t.status === 'in_progress')
      },
      {
        id: 'completed',
        title: 'Done',
        color: 'border-green-200',
        tasks: filteredTasks.filter(t => t.status === 'completed')
      },
      {
        id: 'cancelled',
        title: 'Cancelled',
        color: 'border-red-200',
        tasks: filteredTasks.filter(t => t.status === 'cancelled')
      }
    ]
  }, [filteredTasks])

  const activeTask = useMemo(
    () => tasks.find((t) => t.id === activeId),
    [activeId, tasks]
  )

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id)
  }

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event
    
    if (!over) {
      setOverId(null)
      return
    }

    setOverId(over.id)
  }

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event
    
    if (!over) {
      setActiveId(null)
      setOverId(null)
      return
    }

    const activeTask = tasks.find(t => t.id === active.id)
    if (!activeTask) {
      setActiveId(null)
      setOverId(null)
      return
    }

    // Find which column the task was dropped into
    let targetStatus: string | null = null
    
    // Check if dropped on a column
    if (over.data.current?.type === 'column') {
      targetStatus = over.data.current.column.id
    } else {
      // Dropped on a task - find its column
      const overTask = tasks.find(t => t.id === over.id)
      if (overTask) {
        targetStatus = overTask.status
      }
    }

    if (targetStatus && targetStatus !== activeTask.status) {
      try {
        await api.patch(`/api/v1/tasks/${activeTask.id}/`, {
          status: targetStatus
        })
        
        toast({
          title: 'Task Updated',
          description: `Task moved to ${targetStatus.replace('_', ' ')}`,
        })
        
        onTaskUpdate()
      } catch (error) {
        console.error('Failed to update task status:', error)
        toast({
          title: 'Update Failed',
          description: 'Could not move the task',
          variant: 'destructive'
        })
      }
    }

    setActiveId(null)
    setOverId(null)
  }

  const handleDragCancel = () => {
    setActiveId(null)
    setOverId(null)
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <div className="flex gap-4 overflow-x-auto pb-4">
        {columns.map((column) => (
          <DroppableColumn
            key={column.id}
            column={column}
            onTaskClick={onTaskClick}
          />
        ))}
      </div>

      <DragOverlay>
        {activeTask ? <TaskCardOverlay task={activeTask} /> : null}
      </DragOverlay>
    </DndContext>
  )
}