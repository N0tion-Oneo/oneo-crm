import React, { useState } from 'react'
import { CheckSquare, Calendar, Clock, User, AlertCircle, Flag, X, Edit2, Trash2, MessageSquare, Paperclip } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
import { format } from 'date-fns'

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
  comments?: any[]
  attachments?: any[]
  comments_count?: number
  attachments_count?: number
  created_at: string
  updated_at: string}

interface TaskDetailModalProps {
  task: Task | null
  isOpen: boolean
  onClose: () => void
  onUpdate: () => void
  users?: any[]
}

export function TaskDetailModal({ 
  task, 
  isOpen, 
  onClose, 
  onUpdate,
  users = []
}: TaskDetailModalProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    priority: 'medium',
    status: 'pending',
    due_date: '',
    assigned_to_id: null as number | null,
  })

  // Initialize form data when task changes
  React.useEffect(() => {
    if (task) {
      setFormData({
        title: task.title || '',
        description: task.description || '',
        priority: task.priority || 'medium',
        status: task.status || 'pending',
        due_date: task.due_date ? task.due_date.split('T')[0] : '',
        assigned_to_id: task.assigned_to?.id ? parseInt(task.assigned_to.id) : null,
      })
    }
  }, [task])

  const handleSave = async () => {
    if (!task) return

    try {
      await api.patch(`/api/v1/tasks/${task.id}/`, formData)
      
      toast({
        title: 'Task Updated',
        description: 'Task has been updated successfully.',
      })
      
      setIsEditing(false)
      onUpdate()
    } catch (error) {
      console.error('Failed to update task:', error)
      toast({
        title: 'Update Failed',
        description: 'Could not update the task.',
        variant: 'destructive'
      })
    }
  }

  const handleDelete = async () => {
    if (!task) return

    try {
      await api.delete(`/api/v1/tasks/${task.id}/`)
      
      toast({
        title: 'Task Deleted',
        description: 'Task has been deleted successfully.',
      })
      
      onClose()
      onUpdate()
    } catch (error) {
      console.error('Failed to delete task:', error)
      toast({
        title: 'Delete Failed',
        description: 'Could not delete the task.',
        variant: 'destructive'
      })
    } finally {
      setIsDeleting(false)
    }
  }

  if (!task) return null

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

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              {isEditing ? (
                <Input
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="text-xl font-semibold mb-2"
                  placeholder="Task title"
                />
              ) : (
                <DialogTitle className="text-xl flex items-center gap-2">
                  <CheckSquare className="w-5 h-5" />
                  {task.title}
                </DialogTitle>
              )}
              
              <div className="flex items-center gap-2 mt-2">
                {isEditing ? (
                  <>
                    <Select 
                      value={formData.priority} 
                      onValueChange={(value) => setFormData({ ...formData, priority: value as any })}
                    >
                      <SelectTrigger className="w-[120px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="low">Low</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                        <SelectItem value="urgent">Urgent</SelectItem>
                      </SelectContent>
                    </Select>
                    
                    <Select 
                      value={formData.status} 
                      onValueChange={(value) => setFormData({ ...formData, status: value as any })}
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
                  </>
                ) : (
                  <>
                    {getPriorityBadge(task.priority)}
                    {getStatusBadge(task.status)}
                  </>
                )}
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              {!isEditing ? (
                <>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setIsEditing(true)}
                  >
                    <Edit2 className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setIsDeleting(true)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleSave}
                  >
                    Save
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setIsEditing(false)
                      // Reset form data
                      setFormData({
                        title: task.title || '',
                        description: task.description || '',
                        priority: task.priority || 'medium',
                        status: task.status || 'pending',
                        due_date: task.due_date ? task.due_date.split('T')[0] : '',
                        assigned_to_id: task.assigned_to?.id ? parseInt(task.assigned_to.id) : null,
                      })
                    }}
                  >
                    Cancel
                  </Button>
                </>
              )}
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          {/* Description */}
          <div>
            <Label className="text-sm font-medium mb-2">Description</Label>
            {isEditing ? (
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Add a description..."
                rows={4}
              />
            ) : (
              <p className="text-gray-600 dark:text-gray-400">
                {task.description || 'No description provided'}
              </p>
            )}
          </div>

          {/* Details */}
          <div className="grid grid-cols-2 gap-4">
            {/* Assignee */}
            <div>
              <Label className="text-sm font-medium mb-2">Assigned To</Label>
              {isEditing ? (
                <Select 
                  value={formData.assigned_to_id?.toString() || 'unassigned'} 
                  onValueChange={(value) => setFormData({ 
                    ...formData, 
                    assigned_to_id: value === 'unassigned' ? null : parseInt(value) 
                  })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="unassigned">Unassigned</SelectItem>
                    {users.map((user) => (
                      <SelectItem key={user.id} value={user.id.toString()}>
                        {user.full_name || user.email}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4" />
                  <span>{task.assigned_to_name || task.assigned_to?.email || 'Unassigned'}</span>
                </div>
              )}
            </div>

            {/* Due Date */}
            <div>
              <Label className="text-sm font-medium mb-2">Due Date</Label>
              {isEditing ? (
                <Input
                  type="date"
                  value={formData.due_date}
                  onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                />
              ) : (
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  <span className={task.is_overdue ? 'text-red-500 font-medium' : ''}>
                    {task.due_date ? format(new Date(task.due_date), 'MMM d, yyyy') : 'No due date'}
                    {task.is_overdue && ' (Overdue)'}
                  </span>
                </div>
              )}
            </div>

            {/* Record */}
            {(task.record || task.record_id) && (
              <div>
                <Label className="text-sm font-medium mb-2">Related Record</Label>
                <div className="text-gray-600 dark:text-gray-400">
                  {task.record_name || `Record #${task.record_id || task.record?.id}`}
                  {task.pipeline_name && (
                    <div className="text-xs text-gray-500 mt-1">
                      Pipeline: {task.pipeline_name}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Created By */}
            <div>
              <Label className="text-sm font-medium mb-2">Created By</Label>
              <div className="text-gray-600 dark:text-gray-400">
                {task.created_by_name || task.created_by?.email || 'Unknown'}
              </div>
            </div>

            {/* Created At */}
            <div>
              <Label className="text-sm font-medium mb-2">Created</Label>
              <div className="text-gray-600 dark:text-gray-400">
                {format(new Date(task.created_at), 'MMM d, yyyy h:mm a')}
              </div>
            </div>

            {/* Updated At */}
            <div>
              <Label className="text-sm font-medium mb-2">Last Updated</Label>
              <div className="text-gray-600 dark:text-gray-400">
                {format(new Date(task.updated_at), 'MMM d, yyyy h:mm a')}
              </div>
            </div>
          </div>

          {/* Comments and Attachments Summary */}
          <div className="flex items-center gap-4 pt-4 border-t">
            <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
              <MessageSquare className="w-4 h-4" />
              <span>{task.comments_count || 0} comments</span>
            </div>
            <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
              <Paperclip className="w-4 h-4" />
              <span>{task.attachments_count || 0} attachments</span>
            </div>
          </div>
        </div>

        {/* Delete Confirmation */}
        {isDeleting && (
          <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
            <p className="text-sm text-red-600 dark:text-red-400 mb-3">
              Are you sure you want to delete this task? This action cannot be undone.
            </p>
            <div className="flex gap-2">
              <Button
                variant="destructive"
                size="sm"
                onClick={handleDelete}
              >
                Delete Task
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsDeleting(false)}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}