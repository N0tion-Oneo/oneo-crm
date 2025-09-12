'use client'

import React, { useState, useEffect } from 'react'
import { 
  CheckSquare, 
  Calendar, 
  Clock, 
  User, 
  AlertCircle, 
  Flag, 
  X, 
  Edit2, 
  Trash2, 
  MessageSquare, 
  Paperclip,
  Save,
  Hash,
  FileText,
  Plus,
  Send,
  RefreshCw
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
// Using custom drawer implementation similar to record-detail-drawer
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { api } from '@/lib/api'
import { toast } from '@/hooks/use-toast'
import { format } from 'date-fns'
import { useAuth } from '@/features/auth/context'

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
  updated_at: string
  metadata?: any
}

interface TaskDetailDrawerProps {
  task: Task | null
  isOpen: boolean
  onClose: () => void
  onUpdate: () => void
  users?: any[]
}

export function TaskDetailDrawer({ 
  task, 
  isOpen, 
  onClose, 
  onUpdate,
  users = []
}: TaskDetailDrawerProps) {
  const { user: currentUser } = useAuth()
  const [isEditing, setIsEditing] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [activeTab, setActiveTab] = useState('details')
  const [newComment, setNewComment] = useState('')
  const [isAddingComment, setIsAddingComment] = useState(false)
  
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    priority: 'medium',
    status: 'pending',
    due_date: '',
    assigned_to_id: null as number | null,
  })

  // Initialize form data when task changes
  useEffect(() => {
    if (task) {
      setFormData({
        title: task.title || '',
        description: task.description || '',
        priority: task.priority || 'medium',
        status: task.status || 'pending',
        due_date: task.due_date ? task.due_date.split('T')[0] : '',
        assigned_to_id: task.assigned_to?.id ? parseInt(task.assigned_to.id) : null,
      })
      setActiveTab('details')
      setIsEditing(false)
    }
  }, [task])

  const handleSave = async () => {
    if (!task) return

    setIsSaving(true)
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
    } finally {
      setIsSaving(false)
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

  const handleAddComment = async () => {
    if (!task || !newComment.trim()) return

    setIsAddingComment(true)
    try {
      await api.post(`/api/v1/tasks/${task.id}/comments/`, {
        comment: newComment
      })
      
      toast({
        title: 'Comment Added',
        description: 'Your comment has been added.',
      })
      
      setNewComment('')
      onUpdate()
    } catch (error) {
      console.error('Failed to add comment:', error)
      toast({
        title: 'Failed to Add Comment',
        description: 'Could not add the comment.',
        variant: 'destructive'
      })
    } finally {
      setIsAddingComment(false)
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

  if (!task || !isOpen) return null

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-end z-50"
      onClick={(e) => {
        // Close drawer if clicking on the backdrop
        if (e.target === e.currentTarget) {
          onClose()
        }
      }}
    >
      <div 
        className="bg-white dark:bg-gray-800 h-full w-full max-w-4xl shadow-xl flex flex-col animate-slide-in-right"
        onClick={(e) => {
          // Stop propagation to prevent closing when clicking inside
          e.stopPropagation()
        }}
      >
        {/* Header - Match record drawer style */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            {isEditing ? (
              <Input
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="text-xl font-semibold"
                placeholder="Task title"
              />
            ) : (
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                {task.title}
              </h2>
            )}
            
            {/* Status and Priority Badges */}
            {!isEditing && (
              <div className="flex items-center space-x-2">
                {getStatusBadge(task.status)}
                {getPriorityBadge(task.priority)}
                {task.is_overdue && (
                  <Badge variant="destructive" className="text-xs">
                    Overdue
                  </Badge>
                )}
              </div>
            )}
            
            {isEditing && (
              <div className="flex items-center space-x-2">
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
              </div>
            )}
            
            {isSaving && (
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Saving...</span>
              </div>
            )}
          </div>
          
          {/* Action buttons - Match record drawer style */}
          {!isEditing ? (
            <div className="flex items-center space-x-2">
              <Button
                onClick={() => setIsEditing(true)}
                variant="outline"
                size="sm"
              >
                <Edit2 className="w-4 h-4 mr-2" />
                Edit
              </Button>
              <Button
                onClick={() => setIsDeleting(true)}
                variant="ghost"
                size="sm"
                className="text-red-600 hover:text-red-700 dark:text-red-400"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete
              </Button>
              <Button
                onClick={onClose}
                variant="ghost"
                size="icon"
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <Button
                onClick={handleSave}
                disabled={isSaving}
                size="sm"
              >
                <Save className="w-4 h-4 mr-2" />
                Save Changes
              </Button>
              <Button
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
                variant="outline"
                size="sm"
              >
                Cancel
              </Button>
            </div>
          )}
        </div>

        {/* Tabs - Match record drawer style */}
        <div className="flex border-b border-gray-200 dark:border-gray-700">
          <Button
            onClick={() => setActiveTab('details')}
            variant="ghost"
            className={`px-6 py-3 rounded-none border-b-2 transition-colors ${
              activeTab === 'details'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Details
          </Button>
          <Button
            onClick={() => setActiveTab('comments')}
            variant="ghost"
            className={`px-6 py-3 rounded-none border-b-2 transition-colors ${
              activeTab === 'comments'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Comments {task.comments_count ? `(${task.comments_count})` : ''}
          </Button>
          <Button
            onClick={() => setActiveTab('activity')}
            variant="ghost"
            className={`px-6 py-3 rounded-none border-b-2 transition-colors ${
              activeTab === 'activity'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Activity
          </Button>
        </div>

        {/* Content - Match record drawer style */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === 'details' && (
            <div className="p-6 space-y-6">
              {/* Description */}
              <div>
                <Label className="text-sm font-medium mb-2">Description</Label>
                {isEditing ? (
                  <Textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Add a description..."
                    rows={4}
                    className="mt-2"
                  />
                ) : (
                  <p className="text-gray-600 dark:text-gray-400 mt-2">
                    {task.description || 'No description provided'}
                  </p>
                )}
              </div>

              <Separator />

              {/* Task Details Grid */}
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
                      <SelectTrigger className="mt-2">
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
                    <div className="flex items-center gap-2 mt-2">
                      <User className="w-4 h-4 text-gray-500" />
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
                      className="mt-2"
                    />
                  ) : (
                    <div className="flex items-center gap-2 mt-2">
                      <Calendar className="w-4 h-4 text-gray-500" />
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
                    <div className="flex items-center gap-2 mt-2">
                      <Hash className="w-4 h-4 text-gray-500" />
                      <span>
                        {task.record_name || `Record #${task.record_id || task.record?.id}`}
                      </span>
                    </div>
                    {task.pipeline_name && (
                      <div className="text-xs text-gray-500 mt-1 ml-6">
                        Pipeline: {task.pipeline_name}
                      </div>
                    )}
                  </div>
                )}

                {/* Created By */}
                <div>
                  <Label className="text-sm font-medium mb-2">Created By</Label>
                  <div className="flex items-center gap-2 mt-2">
                    <User className="w-4 h-4 text-gray-500" />
                    <span>{task.created_by_name || task.created_by?.email || 'Unknown'}</span>
                  </div>
                </div>

                {/* Created At */}
                <div>
                  <Label className="text-sm font-medium mb-2">Created</Label>
                  <div className="flex items-center gap-2 mt-2">
                    <Clock className="w-4 h-4 text-gray-500" />
                    <span>{format(new Date(task.created_at), 'MMM d, yyyy h:mm a')}</span>
                  </div>
                </div>

                {/* Updated At */}
                <div>
                  <Label className="text-sm font-medium mb-2">Last Updated</Label>
                  <div className="flex items-center gap-2 mt-2">
                    <Clock className="w-4 h-4 text-gray-500" />
                    <span>{format(new Date(task.updated_at), 'MMM d, yyyy h:mm a')}</span>
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
            </div>
          )}

          {activeTab === 'comments' && (
            <div className="p-6 space-y-6">
              {/* Add Comment */}
              <div className="space-y-2">
                <Textarea
                  placeholder="Add a comment..."
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  rows={3}
                />
                <Button 
                  onClick={handleAddComment}
                  disabled={!newComment.trim() || isAddingComment}
                  size="sm"
                  className="w-full"
                >
                  <Send className="w-4 h-4 mr-2" />
                  {isAddingComment ? 'Adding...' : 'Add Comment'}
                </Button>
              </div>

              <Separator />

              {/* Comments List */}
              {task.comments && task.comments.length > 0 ? (
                <div className="space-y-4">
                  {task.comments.map((comment: any) => (
                    <div key={comment.id} className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <User className="w-4 h-4 text-gray-500" />
                          <span className="font-medium text-sm">
                            {comment.user_name || comment.user_email}
                          </span>
                        </div>
                        <span className="text-xs text-gray-500">
                          {format(new Date(comment.created_at), 'MMM d, h:mm a')}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {comment.comment}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-400">
                  <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No comments yet</p>
                  <p className="text-xs mt-1">Be the first to comment on this task</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'activity' && (
            <div className="p-6 space-y-6">
              <div className="text-center py-8 text-gray-400">
                <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Activity tracking coming soon</p>
                <p className="text-xs mt-1">See all changes and updates to this task</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}