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
  CloudOff,
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
import { useWebSocket } from '@/hooks/use-websocket'
import { debounce } from 'lodash'

interface MeetingCaptureAutoSaveProps {
  conversationId: string
  recordId: string
  onContentAdded?: () => void
}

interface ActionItem {
  id: string
  text: string
  completed: boolean
}

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

export function MeetingCaptureAutoSave({
  conversationId,
  recordId,
  onContentAdded
}: MeetingCaptureAutoSaveProps) {
  const [notes, setNotes] = useState('')
  const [actionItems, setActionItems] = useState<ActionItem[]>([])
  const [currentActionItem, setCurrentActionItem] = useState('')
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle')
  const [isExpanded, setIsExpanded] = useState(true)
  const [showTaskCreator, setShowTaskCreator] = useState(false)
  const [createdTasksCount, setCreatedTasksCount] = useState(0)
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null)
  
  // Track if content has been modified
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // WebSocket setup for real-time sync
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/realtime/'
  const { sendMessage, isConnected } = useWebSocket(wsUrl, {
    onMessage: (message) => {
      // Handle incoming messages if needed for collaboration
      if (message.type === 'meeting_notes_updated' && message.conversation_id === conversationId) {
        // Could update UI to show other users' changes
        console.log('Meeting notes updated by another user')
      }
    },
    onOpen: () => {
      console.log('WebSocket connected for meeting notes')
      // Subscribe to conversation updates
      sendMessage({
        type: 'subscribe',
        channel: `conversation:${conversationId}`
      })
    }
  })

  // Debounced auto-save function
  const autoSave = useCallback(
    debounce(async (currentNotes: string, currentActionItems: ActionItem[]) => {
      const hasContent = currentNotes.trim() || currentActionItems.length > 0

      if (!hasContent) {
        setSaveStatus('idle')
        return
      }

      setSaveStatus('saving')
      setHasUnsavedChanges(false)

      try {
        // Format content for the conversation
        let formattedContent = ''
        
        if (currentNotes.trim()) {
          formattedContent += currentNotes.trim()
        }

        if (currentActionItems.length > 0) {
          if (formattedContent) formattedContent += '\n\n'
          formattedContent += '**Action Items:**\n'
          formattedContent += currentActionItems.map(item => 
            `${item.completed ? '✓' : '○'} ${item.text}`
          ).join('\n')
        }

        if (createdTasksCount > 0) {
          if (formattedContent) formattedContent += '\n\n'
          formattedContent += `*${createdTasksCount} task${createdTasksCount > 1 ? 's' : ''} created during this meeting*`
        }

        // Send to conversation via API
        const requestData = {
          content: formattedContent,
          note_type: 'meeting_notes',
          metadata: {
            has_notes: currentNotes.trim().length > 0,
            has_actions: currentActionItems.length > 0,
            tasks_created: createdTasksCount,
            action_items: currentActionItems,
            auto_saved: true,
            saved_at: new Date().toISOString()
          }
        }

        const endpoint = `/api/v1/communications/conversations/${conversationId}/add-note/`
        const response = await api.post(endpoint, requestData)

        if (response.data.success || response.data.id) {
          setSaveStatus('saved')
          setLastSavedAt(new Date())
          
          // Broadcast via WebSocket for real-time sync
          if (isConnected) {
            sendMessage({
              type: 'meeting_notes_saved',
              conversation_id: conversationId,
              content: formattedContent,
              metadata: requestData.metadata
            })
          }

          // Reset save status after 2 seconds
          setTimeout(() => {
            setSaveStatus('idle')
          }, 2000)
        }
      } catch (error: any) {
        console.error('Failed to auto-save meeting content:', error)
        setSaveStatus('error')
        
        // Show error toast only if it's not a network issue
        if (error.response?.status !== 0) {
          toast({
            title: 'Auto-save failed',
            description: 'Your changes will be saved when connection is restored',
            variant: 'destructive'
          })
        }
        
        // Retry after 5 seconds
        setTimeout(() => {
          autoSave(currentNotes, currentActionItems)
        }, 5000)
      }
    }, 1500), // 1.5 second debounce
    [conversationId, createdTasksCount, isConnected, sendMessage]
  )

  // Effect to trigger auto-save when content changes
  useEffect(() => {
    if (hasUnsavedChanges) {
      autoSave(notes, actionItems)
    }
  }, [notes, actionItems, hasUnsavedChanges, autoSave])

  // Track content changes
  const handleNotesChange = (value: string) => {
    setNotes(value)
    setHasUnsavedChanges(true)
  }

  const handleAddActionItem = () => {
    if (currentActionItem.trim()) {
      const newItems = [
        ...actionItems,
        {
          id: Date.now().toString(),
          text: currentActionItem.trim(),
          completed: false
        }
      ]
      setActionItems(newItems)
      setCurrentActionItem('')
      setHasUnsavedChanges(true)
    }
  }

  const handleRemoveActionItem = (id: string) => {
    const newItems = actionItems.filter(item => item.id !== id)
    setActionItems(newItems)
    setHasUnsavedChanges(true)
  }

  const handleToggleActionItem = (id: string) => {
    const newItems = actionItems.map(item => 
      item.id === id ? { ...item, completed: !item.completed } : item
    )
    setActionItems(newItems)
    setHasUnsavedChanges(true)
  }

  const handleTaskCreated = () => {
    setCreatedTasksCount(prev => prev + 1)
    setShowTaskCreator(false)
    setHasUnsavedChanges(true)
    toast({
      title: "Task created",
      description: "Task has been added to the record"
    })
  }

  // Manual save (optional - for user peace of mind)
  const handleManualSave = () => {
    autoSave.cancel() // Cancel any pending auto-save
    autoSave(notes, actionItems) // Trigger immediate save
  }

  const totalItems = (notes.trim() ? 1 : 0) + actionItems.length

  // Save status indicator
  const SaveStatusIndicator = () => {
    switch (saveStatus) {
      case 'saving':
        return (
          <div className="flex items-center gap-1 text-blue-600">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span className="text-xs">Saving...</span>
          </div>
        )
      case 'saved':
        return (
          <div className="flex items-center gap-1 text-green-600">
            <Cloud className="w-3 h-3" />
            <span className="text-xs">Saved</span>
          </div>
        )
      case 'error':
        return (
          <div className="flex items-center gap-1 text-red-600">
            <CloudOff className="w-3 h-3" />
            <span className="text-xs">Save failed</span>
          </div>
        )
      default:
        return hasUnsavedChanges ? (
          <div className="flex items-center gap-1 text-gray-500">
            <Cloud className="w-3 h-3" />
            <span className="text-xs">Auto-save enabled</span>
          </div>
        ) : null
    }
  }

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
          <SaveStatusIndicator />
          <Button
            size="sm"
            variant="outline"
            onClick={() => setShowTaskCreator(!showTaskCreator)}
          >
            <ListTodo className="w-3 h-3 mr-1" />
            Create Task
          </Button>
          {hasUnsavedChanges && (
            <Button
              size="sm"
              variant="ghost"
              onClick={handleManualSave}
              title="Save now"
            >
              <Save className="w-3 h-3" />
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
              onChange={(e) => handleNotesChange(e.target.value)}
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

          {/* Quick Summary with Auto-save Status */}
          {(totalItems > 0 || createdTasksCount > 0) && (
            <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>
                  {notes.trim() ? '✓ Notes' : ''} 
                  {actionItems.length > 0 ? ` ✓ ${actionItems.length} Actions` : ''} 
                  {createdTasksCount > 0 ? ` • ${createdTasksCount} Tasks created` : ''}
                </span>
                <span className="text-gray-400">
                  {lastSavedAt ? (
                    `Last saved ${lastSavedAt.toLocaleTimeString()}`
                  ) : (
                    'Auto-saving enabled'
                  )}
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}