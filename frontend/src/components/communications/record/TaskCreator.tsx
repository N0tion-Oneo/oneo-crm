import React, { useState, useEffect } from 'react'
import { CheckSquare, Calendar, Clock, X, AlertCircle, Flag, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { api } from '@/lib/api'
import { toast } from '@/hooks/use-toast'
import { useAuth } from '@/features/auth/context'

interface TaskCreatorProps {
  recordId: string
  onTaskCreated?: () => void
  onCancel?: () => void
}

interface UserOption {
  id: string | number
  email: string
  first_name?: string
  last_name?: string
  full_name?: string
}

export function TaskCreator({
  recordId,
  onTaskCreated,
  onCancel
}: TaskCreatorProps) {
  const { user: currentUser } = useAuth()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<'low' | 'medium' | 'high' | 'urgent'>('medium')
  const [dueDate, setDueDate] = useState('')
  const [dueTime, setDueTime] = useState('')
  const [assignedTo, setAssignedTo] = useState<string>('')
  const [reminderBefore, setReminderBefore] = useState<'none' | '15min' | '30min' | '1hour' | '1day'>('none')
  const [isCreating, setIsCreating] = useState(false)
  const [users, setUsers] = useState<UserOption[]>([])
  const [isLoadingUsers, setIsLoadingUsers] = useState(true)
  
  // Fetch users and set default to current user
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        // Use api directly to match how the users page does it
        const response = await api.get('/auth/users/')
        // Handle both paginated and non-paginated responses
        let usersList: UserOption[] = []
        if (response.data) {
          if (Array.isArray(response.data)) {
            usersList = response.data
          } else if (response.data.results && Array.isArray(response.data.results)) {
            usersList = response.data.results
          } else if (response.data.data && Array.isArray(response.data.data)) {
            usersList = response.data.data
          }
        }
        
        console.log('Fetched users response:', response.data)
        console.log('Extracted users list:', usersList)
        setUsers(usersList)
        
        // Set default assigned user to current user
        if (currentUser?.id) {
          setAssignedTo(String(currentUser.id))
        }
      } catch (error) {
        console.error('Failed to fetch users:', error)
        setUsers([])
        // Still try to set current user even if fetch fails
        if (currentUser?.id) {
          setAssignedTo(String(currentUser.id))
        }
      } finally {
        setIsLoadingUsers(false)
      }
    }
    
    fetchUsers()
  }, [currentUser])

  const handleCreate = async () => {
    // Validate required fields
    if (!title) {
      toast({
        title: 'Missing Information',
        description: 'Please enter a task title',
        variant: 'destructive'
      })
      return
    }

    setIsCreating(true)
    try {
      // Prepare due datetime if provided
      let dueDatetime = null
      if (dueDate) {
        if (dueTime) {
          dueDatetime = `${dueDate}T${dueTime}:00`
        } else {
          dueDatetime = `${dueDate}T23:59:00`
        }
      }

      // Calculate reminder time if needed
      let reminderAt = null
      if (dueDatetime && reminderBefore !== 'none') {
        const dueDateTime = new Date(dueDatetime)
        switch (reminderBefore) {
          case '15min':
            reminderAt = new Date(dueDateTime.getTime() - 15 * 60 * 1000).toISOString()
            break
          case '30min':
            reminderAt = new Date(dueDateTime.getTime() - 30 * 60 * 1000).toISOString()
            break
          case '1hour':
            reminderAt = new Date(dueDateTime.getTime() - 60 * 60 * 1000).toISOString()
            break
          case '1day':
            reminderAt = new Date(dueDateTime.getTime() - 24 * 60 * 60 * 1000).toISOString()
            break
        }
      }

      // Create task data
      const taskData = {
        title,
        description,
        priority,
        due_date: dueDatetime,
        reminder_at: reminderAt,
        assigned_to_id: assignedTo && assignedTo !== 'unassigned' ? parseInt(assignedTo) : null,
        record_id: recordId,
        status: 'pending',
        metadata: {
          created_from: 'record_communications',
          reminder_before: reminderBefore
        }
      }

      // Call the API to create the task
      const response = await api.post('/api/v1/tasks/create/', taskData)

      toast({
        title: 'Task Created',
        description: `"${title}" has been added to your tasks`,
      })

      // Clear form and notify parent
      setTitle('')
      setDescription('')
      setPriority('medium')
      setDueDate('')
      setDueTime('')
      setAssignedTo(currentUser?.id ? String(currentUser.id) : 'unassigned')
      setReminderBefore('none')
      
      if (onTaskCreated) {
        onTaskCreated()
      }
    } catch (error: any) {
      console.error('Failed to create task:', error)
      toast({
        title: 'Failed to Create Task',
        description: error.response?.data?.detail || 'Could not create the task',
        variant: 'destructive'
      })
    } finally {
      setIsCreating(false)
    }
  }

  const getPriorityIcon = () => {
    switch (priority) {
      case 'urgent': return <AlertCircle className="w-4 h-4 text-red-500" />
      case 'high': return <Flag className="w-4 h-4 text-orange-500" />
      case 'medium': return <Flag className="w-4 h-4 text-yellow-500" />
      case 'low': return <Flag className="w-4 h-4 text-gray-400" />
      default: return <Flag className="w-4 h-4" />
    }
  }

  const getPriorityColor = () => {
    switch (priority) {
      case 'urgent': return 'text-red-600 dark:text-red-400'
      case 'high': return 'text-orange-600 dark:text-orange-400'
      case 'medium': return 'text-yellow-600 dark:text-yellow-400'
      case 'low': return 'text-gray-600 dark:text-gray-400'
      default: return ''
    }
  }

  return (
    <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <CheckSquare className="w-5 h-5" />
            Create Task
          </h3>
          {onCancel && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onCancel}
            >
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>

        {/* Title */}
        <div>
          <Label htmlFor="title">Task Title *</Label>
          <Input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Follow up with client"
            required
          />
        </div>

        {/* Priority and Assigned To */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="priority">Priority</Label>
            <Select value={priority} onValueChange={(value: any) => setPriority(value)}>
              <SelectTrigger id="priority">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">
                  <div className="flex items-center gap-2">
                    <Flag className="w-4 h-4 text-gray-400" />
                    <span>Low</span>
                  </div>
                </SelectItem>
                <SelectItem value="medium">
                  <div className="flex items-center gap-2">
                    <Flag className="w-4 h-4 text-yellow-500" />
                    <span>Medium</span>
                  </div>
                </SelectItem>
                <SelectItem value="high">
                  <div className="flex items-center gap-2">
                    <Flag className="w-4 h-4 text-orange-500" />
                    <span>High</span>
                  </div>
                </SelectItem>
                <SelectItem value="urgent">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-red-500" />
                    <span>Urgent</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="assigned">Assigned To</Label>
            <Select 
              value={assignedTo} 
              onValueChange={setAssignedTo}
              disabled={isLoadingUsers}
            >
              <SelectTrigger id="assigned">
                <SelectValue placeholder={isLoadingUsers ? "Loading users..." : "Select user"}>
                  {assignedTo === 'unassigned' ? (
                    <div className="flex items-center gap-2">
                      <User className="w-4 h-4 text-gray-400" />
                      <span>Unassigned</span>
                    </div>
                  ) : assignedTo && Array.isArray(users) && users.find(u => String(u.id) === assignedTo) ? (
                    <div className="flex items-center gap-2">
                      <User className="w-4 h-4" />
                      <span>
                        {(() => {
                          const selectedUser = users.find(u => String(u.id) === assignedTo)
                          if (selectedUser?.full_name) return selectedUser.full_name
                          if (selectedUser?.first_name || selectedUser?.last_name) {
                            return `${selectedUser.first_name || ''} ${selectedUser.last_name || ''}`.trim()
                          }
                          return selectedUser?.email || ''
                        })()}
                      </span>
                    </div>
                  ) : null}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="unassigned">
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4 text-gray-400" />
                    <span>Unassigned</span>
                  </div>
                </SelectItem>
                {Array.isArray(users) && users.map((user) => {
                  const displayName = user.full_name || 
                    (user.first_name || user.last_name ? 
                      `${user.first_name || ''} ${user.last_name || ''}`.trim() : 
                      user.email)
                  
                  return (
                    <SelectItem key={user.id} value={String(user.id)}>
                      <div className="flex items-center gap-2">
                        <User className="w-4 h-4" />
                        <span>
                          {displayName}
                          {String(user.id) === String(currentUser?.id) && (
                            <span className="ml-2 text-xs text-gray-500">(Me)</span>
                          )}
                        </span>
                      </div>
                    </SelectItem>
                  )
                })}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Due Date and Time */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label htmlFor="due-date">Due Date</Label>
            <Input
              id="due-date"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              min={new Date().toISOString().split('T')[0]}
            />
          </div>
          <div>
            <Label htmlFor="due-time">Due Time</Label>
            <Input
              id="due-time"
              type="time"
              value={dueTime}
              onChange={(e) => setDueTime(e.target.value)}
              disabled={!dueDate}
            />
          </div>
          <div>
            <Label htmlFor="reminder">Reminder</Label>
            <Select 
              value={reminderBefore} 
              onValueChange={(value: any) => setReminderBefore(value)}
              disabled={!dueDate}
            >
              <SelectTrigger id="reminder">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No Reminder</SelectItem>
                <SelectItem value="15min">15 min before</SelectItem>
                <SelectItem value="30min">30 min before</SelectItem>
                <SelectItem value="1hour">1 hour before</SelectItem>
                <SelectItem value="1day">1 day before</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Description */}
        <div>
          <Label htmlFor="description">Description / Notes</Label>
          <Textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Task details, context, or instructions..."
            rows={3}
          />
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-2">
          {onCancel && (
            <Button
              variant="outline"
              onClick={onCancel}
            >
              Cancel
            </Button>
          )}
          <Button
            onClick={handleCreate}
            disabled={isCreating || !title}
          >
            {isCreating ? 'Creating...' : 'Create Task'}
          </Button>
        </div>

        {/* Task Summary */}
        {title && (
          <div className="text-sm text-gray-500 dark:text-gray-400 border-t pt-3">
            <div className="flex items-center gap-2">
              <CheckSquare className="w-4 h-4" />
              <span className="font-medium">{title}</span>
              <span className={getPriorityColor()}>
                {getPriorityIcon()}
              </span>
            </div>
            {(dueDate || assignedTo) && (
              <div className="flex items-center gap-4 mt-1">
                {dueDate && (
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    Due: {new Date(dueDate).toLocaleDateString()}
                    {dueTime && ` at ${dueTime}`}
                  </span>
                )}
                {assignedTo && (
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3" />
                    Assigned to: {(() => {
                      if (assignedTo === 'unassigned') return 'Unassigned'
                      const selectedUser = Array.isArray(users) ? users.find(u => String(u.id) === assignedTo) : null
                      if (!selectedUser) return 'Unknown'
                      if (selectedUser.full_name) return selectedUser.full_name
                      if (selectedUser.first_name || selectedUser.last_name) {
                        return `${selectedUser.first_name || ''} ${selectedUser.last_name || ''}`.trim()
                      }
                      return selectedUser.email
                    })()}
                  </span>
                )}
                {reminderBefore !== 'none' && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Reminder: {reminderBefore.replace('min', ' min').replace('hour', ' hour').replace('day', ' day')} before
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}