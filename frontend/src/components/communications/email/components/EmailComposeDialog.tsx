import React, { useEffect } from 'react'
import { Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { EmailAccount, ReplyMode } from '../utils/emailTypes'

interface EmailComposeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  replyMode: ReplyMode
  selectedAccount: EmailAccount | null
  to: string
  cc: string
  bcc: string
  subject: string
  body: string
  sending: boolean
  onToChange: (value: string) => void
  onCcChange: (value: string) => void
  onBccChange: (value: string) => void
  onSubjectChange: (value: string) => void
  onBodyChange: (value: string) => void
  onSend: () => void
  onCancel: () => void
  editorRef: React.RefObject<HTMLDivElement>
  editorKey: number
  lastOpenState: React.MutableRefObject<boolean>
  setEditorKey: (key: number) => void
}

export const EmailComposeDialog: React.FC<EmailComposeDialogProps> = ({
  open,
  onOpenChange,
  replyMode,
  selectedAccount,
  to,
  cc,
  bcc,
  subject,
  body,
  sending,
  onToChange,
  onCcChange,
  onBccChange,
  onSubjectChange,
  onBodyChange,
  onSend,
  onCancel,
  editorRef,
  editorKey,
  lastOpenState,
  setEditorKey
}) => {
  // Set editor content when dialog opens
  useEffect(() => {
    // Only run when dialog transitions from closed to open
    if (open && !lastOpenState.current) {
      // Force editor to remount with new content
      setEditorKey(editorKey + 1)
      
      // Set initial content after remount
      setTimeout(() => {
        if (editorRef.current && body) {
          editorRef.current.innerHTML = body
          
          // Place cursor at the beginning for replies/forwards
          if (replyMode && editorRef.current.firstChild) {
            const range = document.createRange()
            const sel = window.getSelection()
            range.setStart(editorRef.current.firstChild, 0)
            range.collapse(true)
            sel?.removeAllRanges()
            sel?.addRange(range)
          }
        }
      }, 0)
    }
    
    // Track the last open state
    lastOpenState.current = open
  }, [open, body, replyMode, editorRef, lastOpenState, setEditorKey])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {replyMode === 'reply' ? 'Reply to Email' : replyMode === 'forward' ? 'Forward Email' : 'New Email'}
          </DialogTitle>
          <DialogDescription>
            {selectedAccount && `Sending from ${selectedAccount.email}`}
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="to">To</Label>
            <Input
              id="to"
              placeholder="recipient@example.com, another@example.com"
              value={to}
              onChange={(e) => onToChange(e.target.value)}
              disabled={sending}
            />
          </div>
          
          <div className="grid gap-2">
            <Label htmlFor="cc">CC</Label>
            <Input
              id="cc"
              placeholder="cc@example.com"
              value={cc}
              onChange={(e) => onCcChange(e.target.value)}
              disabled={sending}
            />
          </div>
          
          <div className="grid gap-2">
            <Label htmlFor="bcc">BCC</Label>
            <Input
              id="bcc"
              placeholder="bcc@example.com"
              value={bcc}
              onChange={(e) => onBccChange(e.target.value)}
              disabled={sending}
            />
          </div>
          
          <div className="grid gap-2">
            <Label htmlFor="subject">Subject</Label>
            <Input
              id="subject"
              placeholder="Email subject"
              value={subject}
              onChange={(e) => onSubjectChange(e.target.value)}
              disabled={sending}
            />
          </div>
          
          <div className="grid gap-2">
            <Label htmlFor="body">Message</Label>
            <div className="space-y-2">
              {/* Rich text editor toolbar */}
              <div className="flex items-center gap-1 p-2 border rounded-t-md bg-gray-50 dark:bg-gray-800">
                <button
                  type="button"
                  onClick={() => document.execCommand('bold', false)}
                  className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                  title="Bold"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 4h8a4 4 0 014 4 4 4 0 01-4 4H6z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 12h10a4 4 0 014 4 4 4 0 01-4 4H6z" />
                  </svg>
                </button>
                <button
                  type="button"
                  onClick={() => document.execCommand('italic', false)}
                  className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                  title="Italic"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 4h4M14 4l-4 16m-2 0h4" />
                  </svg>
                </button>
                <button
                  type="button"
                  onClick={() => document.execCommand('underline', false)}
                  className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                  title="Underline"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 4v7a5 5 0 0010 0V4M5 21h14" />
                  </svg>
                </button>
                <div className="w-px h-6 bg-gray-300 dark:bg-gray-600 mx-1" />
                <button
                  type="button"
                  onClick={() => document.execCommand('insertUnorderedList', false)}
                  className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                  title="Bullet List"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                </button>
                <button
                  type="button"
                  onClick={() => document.execCommand('insertOrderedList', false)}
                  className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                  title="Numbered List"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                  </svg>
                </button>
                <div className="w-px h-6 bg-gray-300 dark:bg-gray-600 mx-1" />
                <button
                  type="button"
                  onClick={() => {
                    const url = prompt('Enter URL:')
                    if (url) document.execCommand('createLink', false, url)
                  }}
                  className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                  title="Insert Link"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                  </svg>
                </button>
                <button
                  type="button"
                  onClick={() => document.execCommand('removeFormat', false)}
                  className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded ml-auto"
                  title="Clear Formatting"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l9-5-9-5-9 5 9 5z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17.5l3 3m0 0l3-3m-3 3v-6" />
                  </svg>
                </button>
              </div>
              {/* Rich text editor content area */}
              <div
                key={editorKey}
                ref={editorRef}
                id="body"
                contentEditable={!sending}
                className="min-h-[300px] p-3 border rounded-b-md bg-white dark:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 overflow-y-auto"
                onInput={(e) => {
                  // Update state to keep track of content
                  onBodyChange(e.currentTarget.innerHTML)
                }}
                style={{ minHeight: '300px', maxHeight: '500px' }}
                suppressContentEditableWarning={true}
              />
            </div>
          </div>
        </div>
        
        <DialogFooter>
          <Button
            variant="outline"
            onClick={onCancel}
            disabled={sending}
          >
            Cancel
          </Button>
          <Button
            onClick={onSend}
            disabled={sending || !to.trim() || !subject.trim()}
          >
            {sending ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                Sending...
              </>
            ) : (
              <>
                <Send className="w-4 h-4 mr-2" />
                Send
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}