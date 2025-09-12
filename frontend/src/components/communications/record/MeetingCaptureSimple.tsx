import React, { useState, useCallback, useEffect, useRef } from 'react'
import { 
  StickyNote, 
  CheckSquare, 
  ListTodo, 
  Plus, 
  X,
  Save,
  ChevronDown,
  ChevronUp,
  Cloud,
  Loader2
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api } from '@/lib/api'
import { toast } from '@/hooks/use-toast'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { TaskCreator } from './TaskCreator'

interface MeetingCaptureSimpleProps {
  conversationId: string
  recordId: string
  onContentAdded?: () => void
}

interface ActionItem {
  id: string
  text: string
  completed: boolean
}

export function MeetingCaptureSimple({
  conversationId,
  recordId,
  onContentAdded
}: MeetingCaptureSimpleProps) {
  const [notes, setNotes] = useState('')
  const [actionItems, setActionItems] = useState<ActionItem[]>([])
  const [currentActionItem, setCurrentActionItem] = useState('')
  const [isExpanded, setIsExpanded] = useState(true)
  const [showTaskCreator, setShowTaskCreator] = useState(false)
  const [createdTasksCount, setCreatedTasksCount] = useState(0)
  const [isSaving, setIsSaving] = useState(false)
  const [hasSaved, setHasSaved] = useState(false) // Track if we've saved at least once
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(true)
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null)
  
  // Track the message ID for updates instead of creating new messages
  const messageIdRef = useRef<string | null>(null)
  const saveTimerRef = useRef<NodeJS.Timeout | null>(null)

  // Smart save function - creates or updates existing message
  const handleSave = async (isAutoSave = false) => {
    const hasContent = notes.trim() || actionItems.length > 0 || createdTasksCount > 0

    if (!hasContent) {
      // For auto-save, silently skip if no content
      if (isAutoSave) return
      
      toast({
        title: "No content to save",
        description: "Add notes, action items, or create tasks before saving",
        variant: "destructive"
      })
      return
    }

    setIsSaving(true)

    try {
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

      if (createdTasksCount > 0) {
        if (formattedContent) formattedContent += '\n\n'
        formattedContent += `*${createdTasksCount} task${createdTasksCount > 1 ? 's' : ''} created during this meeting*`
      }

      let response
      
      // If we have a message ID, update the existing message
      if (messageIdRef.current) {
        // For updates, we need to send only the fields that MessageSerializer expects
        const updateData = {
          content: formattedContent,
          metadata: {
            has_notes: notes.trim().length > 0,
            has_actions: actionItems.length > 0,
            tasks_created: createdTasksCount,
            action_items: actionItems,
            auto_save: isAutoSave,
            last_updated: new Date().toISOString(),
            note_type: 'meeting_notes'
          }
        }
        const updateEndpoint = `/api/v1/communications/messages/${messageIdRef.current}/`
        response = await api.patch(updateEndpoint, updateData)
      } else {
        // First save - create a new message with note-specific fields
        const createData = {
          content: formattedContent,
          note_type: 'meeting_notes',
          metadata: {
            has_notes: notes.trim().length > 0,
            has_actions: actionItems.length > 0,
            tasks_created: createdTasksCount,
            action_items: actionItems,
            auto_save: isAutoSave,
            last_updated: new Date().toISOString()
          }
        }
        const createEndpoint = `/api/v1/communications/conversations/${conversationId}/add-note/`
        response = await api.post(createEndpoint, createData)
        
        // Store the message ID for future updates
        if (response.data.id) {
          messageIdRef.current = response.data.id
        }
      }

      if (response.data.success || response.data.id || response.data) {
        setLastSavedAt(new Date())
        
        // Only show toast for manual saves
        if (!isAutoSave) {
          toast({
            title: "Meeting notes saved",
            description: messageIdRef.current 
              ? "Your meeting notes have been updated"
              : "Your meeting notes have been added to the conversation"
          })
        }
        
        setHasSaved(true)
        
        // Only notify parent on first save
        if (!messageIdRef.current && onContentAdded) {
          onContentAdded()
        }
        
        // Don't clear form on auto-save
        if (!isAutoSave) {
          // Clear form after successful manual save
          setNotes('')
          setActionItems([])
          setCreatedTasksCount(0)
          messageIdRef.current = null // Reset for next note
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

  // Auto-save debounced function
  const triggerAutoSave = useCallback(() => {
    if (!autoSaveEnabled) return
    
    // Clear existing timer
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current)
    }
    
    // Set new timer for auto-save (2 seconds after user stops typing)
    saveTimerRef.current = setTimeout(() => {
      handleSave(true) // true = auto-save
    }, 2000)
  }, [autoSaveEnabled, notes, actionItems, createdTasksCount])
  
  // Trigger auto-save when content changes
  useEffect(() => {
    const hasContent = notes.trim() || actionItems.length > 0 || createdTasksCount > 0
    if (hasContent && autoSaveEnabled) {
      triggerAutoSave()
    }
  }, [notes, actionItems, createdTasksCount, autoSaveEnabled, triggerAutoSave])
  
  // Add keyboard shortcut for manual save
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        handleSave(false) // false = manual save
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [notes, actionItems, createdTasksCount])
  
  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current)
      }
    }
  }, [])

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

  const handleRemoveActionItem = (id: string) => {
    setActionItems(actionItems.filter(item => item.id !== id))
  }

  const handleToggleActionItem = (id: string) => {
    setActionItems(actionItems.map(item => 
      item.id === id ? { ...item, completed: !item.completed } : item
    ))
  }

  const handleTaskCreated = () => {
    setCreatedTasksCount(prev => prev + 1)
    setShowTaskCreator(false)
    toast({
      title: "Task created",
      description: "Task has been added to the record"
    })
  }

  const totalItems = (notes.trim() ? 1 : 0) + actionItems.length

  return (
    <div className="border-t border-gray-200 dark:border-gray-700">
      {/* Compact Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        <div className="flex items-center gap-3">
          <StickyNote className="w-4 h-4 text-gray-600" />
          <span className="font-medium text-sm">Meeting Notes</span>
          {(totalItems > 0 || createdTasksCount > 0) && (
            <div className="flex gap-2">
              {totalItems > 0 && (
                <Badge variant="secondary">{totalItems} item{totalItems !== 1 ? 's' : ''}</Badge>
              )}
              {createdTasksCount > 0 && (
                <Badge variant="outline" className="text-purple-600">
                  {createdTasksCount} task{createdTasksCount !== 1 ? 's' : ''}
                </Badge>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Auto-save indicator */}
          {autoSaveEnabled && hasSaved && (
            <div className="flex items-center gap-1 text-xs text-gray-500">
              {isSaving ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span>Saving...</span>
                </>
              ) : lastSavedAt ? (
                <>
                  <Cloud className="w-3 h-3" />
                  <span>Auto-saved</span>
                </>
              ) : null}
            </div>
          )}
          <Button
            size="sm"
            variant="outline"
            onClick={() => setShowTaskCreator(!showTaskCreator)}
          >
            <ListTodo className="w-3 h-3 mr-1" />
            Create Task
          </Button>
          {(totalItems > 0 || createdTasksCount > 0) && (
            <Button
              size="sm"
              variant={hasSaved ? "outline" : "default"}
              onClick={() => handleSave(false)}
              disabled={isSaving}
            >
              <Save className="w-3 h-3 mr-1" />
              {isSaving ? 'Saving...' : messageIdRef.current ? 'Save & Close' : 'Save Notes'}
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      {/* Task Creator Modal/Panel */}
      {showTaskCreator && (
        <div className="border-b border-gray-200 dark:border-gray-700 bg-blue-50 dark:bg-blue-950">
          <TaskCreator
            recordId={recordId}
            onTaskCreated={handleTaskCreated}
            onCancel={() => setShowTaskCreator(false)}
          />
        </div>
      )}

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
              rows={4}
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

          {/* Quick Summary */}
          {(totalItems > 0 || createdTasksCount > 0) && (
            <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>
                  {notes.trim() ? '✓ Notes' : ''} 
                  {actionItems.length > 0 ? ` ✓ ${actionItems.length} Actions` : ''} 
                  {createdTasksCount > 0 ? ` • ${createdTasksCount} Tasks created` : ''}
                </span>
                <span className="text-gray-400">
                  {autoSaveEnabled && messageIdRef.current 
                    ? 'Auto-saving enabled' 
                    : hasSaved 
                      ? 'Notes saved to conversation' 
                      : 'Press Ctrl+S to save'}
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}