import React, { useState, useCallback, useEffect } from 'react'
import { 
  StickyNote, 
  CheckSquare, 
  ListTodo, 
  Plus, 
  X,
  Calendar,
  AlertCircle,
  Save,
  ChevronDown,
  ChevronUp
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api } from '@/lib/api'
import { toast } from '@/hooks/use-toast'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface MeetingCaptureProps {
  conversationId: string
  recordId: string
  onContentAdded?: () => void
}

interface ActionItem {
  id: string
  text: string
  completed: boolean
}

interface Task {
  id: string
  title: string
  due_date: string
  priority: 'low' | 'medium' | 'high'
}

export function MeetingCapture({
  conversationId,
  recordId,
  onContentAdded
}: MeetingCaptureProps) {
  const [notes, setNotes] = useState('')
  const [actionItems, setActionItems] = useState<ActionItem[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [currentActionItem, setCurrentActionItem] = useState('')
  const [currentTask, setCurrentTask] = useState('')
  const [currentTaskDue, setCurrentTaskDue] = useState('')
  const [currentTaskPriority, setCurrentTaskPriority] = useState<'low' | 'medium' | 'high'>('medium')
  const [isSaving, setIsSaving] = useState(false)
  const [isExpanded, setIsExpanded] = useState(true)

  // Add keyboard shortcut for save
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        const hasContent = notes.trim() || actionItems.length > 0 || tasks.length > 0
        if (hasContent && !isSaving) {
          handleSave()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  })

  const handleAddActionItem = () => {
    if (currentActionItem.trim()) {
      setActionItems([
        ...actionItems,
        {
          id: Date.now().toString(),
          text: currentActionItem.trim(),
          completed: false
        }
      ])
      setCurrentActionItem('')
    }
  }

  const handleAddTask = () => {
    if (currentTask.trim()) {
      setTasks([
        ...tasks,
        {
          id: Date.now().toString(),
          title: currentTask.trim(),
          due_date: currentTaskDue,
          priority: currentTaskPriority
        }
      ])
      setCurrentTask('')
      setCurrentTaskDue('')
      setCurrentTaskPriority('medium')
    }
  }

  const handleRemoveActionItem = (id: string) => {
    setActionItems(actionItems.filter(item => item.id !== id))
  }

  const handleToggleActionItem = (id: string) => {
    setActionItems(actionItems.map(item => 
      item.id === id ? { ...item, completed: !item.completed } : item
    ))
  }

  const handleRemoveTask = (id: string) => {
    setTasks(tasks.filter(task => task.id !== id))
  }

  const handleSave = async () => {
    const hasContent = notes.trim() || actionItems.length > 0 || tasks.length > 0

    if (!hasContent) {
      toast({
        title: "No content to save",
        description: "Add notes, action items, or tasks before saving",
        variant: "destructive"
      })
      return
    }

    setIsSaving(true)

    try {
      // Create tasks in the task system
      const taskPromises = tasks.map(async (task) => {
        try {
          const taskData: any = {
            title: task.title,
            record_id: recordId,  // Fixed: use record_id instead of record
            status: 'pending',
            priority: task.priority,
            metadata: {
              source: 'meeting_capture',
              conversation_id: conversationId
            }
          }

          if (task.due_date) {
            taskData.due_date = task.due_date
          }

          const response = await api.post('/api/v1/tasks/', taskData)
          return response.data
        } catch (error) {
          console.error('Failed to create task:', error)
          return null
        }
      })

      const createdTasks = await Promise.all(taskPromises)
      const successfulTasks = createdTasks.filter(t => t !== null)

      // Format content for the conversation
      let formattedContent = ''
      
      if (notes.trim()) {
        formattedContent += notes.trim()
      }

      if (actionItems.length > 0) {
        if (formattedContent) formattedContent += '\n\n'
        formattedContent += '**Action Items:**\n'
        formattedContent += actionItems.map(item => 
          `${item.completed ? '✓' : '○'} ${item.text}`
        ).join('\n')
      }

      if (tasks.length > 0) {
        if (formattedContent) formattedContent += '\n\n'
        formattedContent += '**Tasks Created:**\n'
        tasks.forEach((task, index) => {
          formattedContent += `• ${task.title}`
          if (task.priority !== 'medium') {
            formattedContent += ` [${task.priority}]`
          }
          if (task.due_date) {
            const date = new Date(task.due_date)
            formattedContent += ` (Due: ${date.toLocaleDateString()})`
          }
          if (successfulTasks[index]) {
            formattedContent += ` #${successfulTasks[index].id}`
          }
          formattedContent += '\n'
        })
      }

      // Send to conversation
      const requestData = {
        content: formattedContent,
        note_type: 'meeting_capture',
        metadata: {
          has_notes: notes.trim().length > 0,
          has_actions: actionItems.length > 0,
          has_tasks: tasks.length > 0,
          action_items: actionItems,
          created_tasks: successfulTasks.map(t => t.id)
        }
      }

      const endpoint = `/api/v1/communications/conversations/${conversationId}/add-note/`
      const response = await api.post(endpoint, requestData)

      if (response.data.success || response.data.id) {
        toast({
          title: "Meeting content saved",
          description: `Added ${notes.trim() ? 'notes, ' : ''}${actionItems.length} actions, ${tasks.length} tasks`
        })

        // Clear form
        setNotes('')
        setActionItems([])
        setTasks([])

        // Notify parent
        if (onContentAdded) {
          onContentAdded()
        }
      }
    } catch (error: any) {
      console.error('Failed to save meeting content:', error)
      toast({
        title: 'Failed to save',
        description: error.response?.data?.detail || 'Could not save meeting content',
        variant: 'destructive'
      })
    } finally {
      setIsSaving(false)
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'text-red-600 bg-red-50 border-red-200'
      case 'low': return 'text-gray-600 bg-gray-50 border-gray-200'
      default: return 'text-blue-600 bg-blue-50 border-blue-200'
    }
  }

  const totalItems = (notes.trim() ? 1 : 0) + actionItems.length + tasks.length

  return (
    <div className="border-t border-gray-200 dark:border-gray-700">
      {/* Compact Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        <div className="flex items-center gap-3">
          <StickyNote className="w-4 h-4 text-gray-600" />
          <span className="font-medium text-sm">Meeting Capture</span>
          {totalItems > 0 && (
            <Badge variant="secondary">{totalItems}</Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant={totalItems > 0 ? "default" : "outline"}
            onClick={handleSave}
            disabled={isSaving || totalItems === 0}
          >
            <Save className="w-3 h-3 mr-1" />
            Save
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      {/* Streamlined Body */}
      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* Meeting Notes Section */}
          <div>
            <Label className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
              Meeting Notes
            </Label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Key points, decisions, discussions..."
              rows={3}
              className="text-sm"
            />
          </div>

          {/* Action Items Section */}
          <div>
            <Label className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
              Action Items
            </Label>
            <div className="flex gap-2">
              <Input
                value={currentActionItem}
                onChange={(e) => setCurrentActionItem(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    handleAddActionItem()
                  }
                }}
                placeholder="Type action item and press Enter..."
                className="text-sm"
              />
              <Button
                size="sm"
                variant="outline"
                onClick={handleAddActionItem}
                disabled={!currentActionItem.trim()}
              >
                <Plus className="w-3 h-3" />
              </Button>
            </div>
            
            {/* Action Items List */}
            {actionItems.length > 0 && (
              <div className="mt-2 space-y-1">
                {actionItems.map((item) => (
                  <div key={item.id} className="flex items-center gap-2 p-2 bg-blue-50 dark:bg-blue-950 rounded text-sm">
                    <Checkbox
                      checked={item.completed}
                      onCheckedChange={() => handleToggleActionItem(item.id)}
                      className="h-3 w-3"
                    />
                    <span className={`flex-1 ${item.completed ? 'line-through text-gray-500' : ''}`}>
                      {item.text}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={() => handleRemoveActionItem(item.id)}
                    >
                      <X className="w-3 h-3" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Tasks Section */}
          <div>
            <Label className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
              Tasks to Create
            </Label>
            <div className="flex gap-2">
              <Input
                value={currentTask}
                onChange={(e) => setCurrentTask(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && currentTask.trim()) {
                    e.preventDefault()
                    handleAddTask()
                  }
                }}
                placeholder="Task title..."
                className="flex-1 text-sm"
              />
              <Input
                type="date"
                value={currentTaskDue}
                onChange={(e) => setCurrentTaskDue(e.target.value)}
                min={new Date().toISOString().split('T')[0]}
                className="w-32 text-sm"
              />
              <Select 
                value={currentTaskPriority} 
                onValueChange={(v: 'low' | 'medium' | 'high') => setCurrentTaskPriority(v)}
              >
                <SelectTrigger className="w-24 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Med</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                </SelectContent>
              </Select>
              <Button
                size="sm"
                variant="outline"
                onClick={handleAddTask}
                disabled={!currentTask.trim()}
              >
                <Plus className="w-3 h-3" />
              </Button>
            </div>

            {/* Tasks List */}
            {tasks.length > 0 && (
              <div className="mt-2 space-y-1">
                {tasks.map((task) => (
                  <div key={task.id} className={`flex items-center gap-2 p-2 rounded text-sm border ${getPriorityColor(task.priority)}`}>
                    <ListTodo className="w-3 h-3" />
                    <span className="flex-1 font-medium">{task.title}</span>
                    {task.due_date && (
                      <span className="text-xs text-gray-500 flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {new Date(task.due_date).toLocaleDateString()}
                      </span>
                    )}
                    <Badge variant="outline" className="text-xs py-0 h-5">
                      {task.priority}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={() => handleRemoveTask(task.id)}
                    >
                      <X className="w-3 h-3" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quick Summary */}
          {totalItems > 0 && (
            <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>
                  Ready to save: {notes.trim() ? '✓ Notes' : ''} 
                  {actionItems.length > 0 ? ` ✓ ${actionItems.length} Actions` : ''} 
                  {tasks.length > 0 ? ` ✓ ${tasks.length} Tasks` : ''}
                </span>
                <span className="text-gray-400">
                  Press Ctrl+S to save
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}