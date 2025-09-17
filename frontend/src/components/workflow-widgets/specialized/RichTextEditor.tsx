/**
 * Rich text editor widget with formatting capabilities
 */

import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Bold, Italic, Underline, List, ListOrdered,
  Link, Quote, Code, Heading1, Heading2,
  AlignLeft, AlignCenter, AlignRight, Undo, Redo
} from 'lucide-react';
import { WidgetProps } from '../core/types';
import { BaseWidgetWrapper } from '../basic/BaseWidget';
import { cn } from '@/lib/utils';

interface RichTextEditorProps extends WidgetProps {
  toolbar?: string[];
  maxLength?: number;
}

const DEFAULT_TOOLBAR = [
  'bold', 'italic', 'underline', '|',
  'heading1', 'heading2', '|',
  'alignLeft', 'alignCenter', 'alignRight', '|',
  'bulletList', 'orderedList', '|',
  'link', 'quote', 'code', '|',
  'undo', 'redo'
];

export const RichTextEditor: React.FC<RichTextEditorProps> = (props) => {
  const { value = '', onChange, uiHints = {} } = props;
  const editorRef = useRef<HTMLDivElement>(null);
  const [isLinkDialogOpen, setIsLinkDialogOpen] = useState(false);
  const [selectedText, setSelectedText] = useState('');
  const [charCount, setCharCount] = useState(0);

  const toolbar = uiHints.toolbar || DEFAULT_TOOLBAR;
  const maxLength = props.maxLength || uiHints.max_length;
  const minHeight = uiHints.min_height || '200px';
  const maxHeight = uiHints.max_height || '400px';

  useEffect(() => {
    if (editorRef.current && value !== editorRef.current.innerHTML) {
      editorRef.current.innerHTML = value;
    }
    setCharCount(editorRef.current?.innerText?.length || 0);
  }, [value]);

  const execCommand = (command: string, value?: string) => {
    document.execCommand(command, false, value);
    handleContentChange();
  };

  const handleContentChange = () => {
    if (editorRef.current) {
      const html = editorRef.current.innerHTML;
      const text = editorRef.current.innerText;

      if (maxLength && text.length > maxLength) {
        // Prevent exceeding max length
        return;
      }

      onChange(html);
      setCharCount(text.length);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Handle keyboard shortcuts
    if (e.ctrlKey || e.metaKey) {
      switch (e.key) {
        case 'b':
          e.preventDefault();
          execCommand('bold');
          break;
        case 'i':
          e.preventDefault();
          execCommand('italic');
          break;
        case 'u':
          e.preventDefault();
          execCommand('underline');
          break;
        case 'z':
          e.preventDefault();
          if (e.shiftKey) {
            execCommand('redo');
          } else {
            execCommand('undo');
          }
          break;
      }
    }
  };

  const insertLink = () => {
    const selection = window.getSelection();
    if (selection && selection.toString()) {
      setSelectedText(selection.toString());
      setIsLinkDialogOpen(true);
    } else {
      const url = prompt('Enter URL:');
      if (url) {
        execCommand('createLink', url);
      }
    }
  };

  const applyLink = (url: string) => {
    if (url) {
      execCommand('createLink', url);
    }
    setIsLinkDialogOpen(false);
    setSelectedText('');
  };

  const getToolbarButton = (tool: string) => {
    switch (tool) {
      case 'bold':
        return (
          <Button
            key={tool}
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => execCommand('bold')}
            className="p-1"
            title="Bold (Ctrl+B)"
          >
            <Bold className="w-4 h-4" />
          </Button>
        );
      case 'italic':
        return (
          <Button
            key={tool}
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => execCommand('italic')}
            className="p-1"
            title="Italic (Ctrl+I)"
          >
            <Italic className="w-4 h-4" />
          </Button>
        );
      case 'underline':
        return (
          <Button
            key={tool}
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => execCommand('underline')}
            className="p-1"
            title="Underline (Ctrl+U)"
          >
            <Underline className="w-4 h-4" />
          </Button>
        );
      case 'heading1':
        return (
          <Button
            key={tool}
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => execCommand('formatBlock', '<h1>')}
            className="p-1"
            title="Heading 1"
          >
            <Heading1 className="w-4 h-4" />
          </Button>
        );
      case 'heading2':
        return (
          <Button
            key={tool}
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => execCommand('formatBlock', '<h2>')}
            className="p-1"
            title="Heading 2"
          >
            <Heading2 className="w-4 h-4" />
          </Button>
        );
      case 'alignLeft':
        return (
          <Button
            key={tool}
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => execCommand('justifyLeft')}
            className="p-1"
            title="Align Left"
          >
            <AlignLeft className="w-4 h-4" />
          </Button>
        );
      case 'alignCenter':
        return (
          <Button
            key={tool}
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => execCommand('justifyCenter')}
            className="p-1"
            title="Align Center"
          >
            <AlignCenter className="w-4 h-4" />
          </Button>
        );
      case 'alignRight':
        return (
          <Button
            key={tool}
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => execCommand('justifyRight')}
            className="p-1"
            title="Align Right"
          >
            <AlignRight className="w-4 h-4" />
          </Button>
        );
      case 'bulletList':
        return (
          <Button
            key={tool}
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => execCommand('insertUnorderedList')}
            className="p-1"
            title="Bullet List"
          >
            <List className="w-4 h-4" />
          </Button>
        );
      case 'orderedList':
        return (
          <Button
            key={tool}
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => execCommand('insertOrderedList')}
            className="p-1"
            title="Numbered List"
          >
            <ListOrdered className="w-4 h-4" />
          </Button>
        );
      case 'link':
        return (
          <Button
            key={tool}
            type="button"
            variant="ghost"
            size="sm"
            onClick={insertLink}
            className="p-1"
            title="Insert Link"
          >
            <Link className="w-4 h-4" />
          </Button>
        );
      case 'quote':
        return (
          <Button
            key={tool}
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => execCommand('formatBlock', '<blockquote>')}
            className="p-1"
            title="Quote"
          >
            <Quote className="w-4 h-4" />
          </Button>
        );
      case 'code':
        return (
          <Button
            key={tool}
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => execCommand('formatBlock', '<pre>')}
            className="p-1"
            title="Code Block"
          >
            <Code className="w-4 h-4" />
          </Button>
        );
      case 'undo':
        return (
          <Button
            key={tool}
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => execCommand('undo')}
            className="p-1"
            title="Undo (Ctrl+Z)"
          >
            <Undo className="w-4 h-4" />
          </Button>
        );
      case 'redo':
        return (
          <Button
            key={tool}
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => execCommand('redo')}
            className="p-1"
            title="Redo (Ctrl+Shift+Z)"
          >
            <Redo className="w-4 h-4" />
          </Button>
        );
      case '|':
        return <div key={`separator-${Math.random()}`} className="w-px h-6 bg-gray-300" />;
      default:
        return null;
    }
  };

  return (
    <BaseWidgetWrapper {...props}>
      <div className="border rounded-lg overflow-hidden">
        {/* Toolbar */}
        {!props.readonly && (
          <div className="border-b bg-gray-50 p-1 flex items-center gap-1 flex-wrap">
            {toolbar.map(tool => getToolbarButton(tool))}
          </div>
        )}

        {/* Editor */}
        <div
          ref={editorRef}
          contentEditable={!props.disabled && !props.readonly}
          onInput={handleContentChange}
          onKeyDown={handleKeyDown}
          className={cn(
            "p-3 focus:outline-none prose prose-sm max-w-none",
            props.disabled && "opacity-50 cursor-not-allowed",
            props.readonly && "cursor-default"
          )}
          style={{
            minHeight,
            maxHeight,
            overflowY: 'auto'
          }}
          dangerouslySetInnerHTML={{ __html: value }}
        />

        {/* Footer */}
        {maxLength && (
          <div className="border-t px-3 py-1 text-xs text-gray-500 text-right">
            {charCount} / {maxLength} characters
          </div>
        )}
      </div>

      {/* Link Dialog (simplified) */}
      {isLinkDialogOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-4 rounded-lg shadow-lg space-y-3">
            <h3 className="text-sm font-medium">Insert Link</h3>
            <p className="text-sm text-gray-600">Text: {selectedText}</p>
            <input
              type="url"
              placeholder="Enter URL..."
              className="w-full px-2 py-1 border rounded"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  applyLink((e.target as HTMLInputElement).value);
                } else if (e.key === 'Escape') {
                  setIsLinkDialogOpen(false);
                }
              }}
              autoFocus
            />
            <div className="flex gap-2 justify-end">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setIsLinkDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  const input = document.querySelector('input[type="url"]') as HTMLInputElement;
                  applyLink(input?.value || '');
                }}
              >
                Apply
              </Button>
            </div>
          </div>
        </div>
      )}
    </BaseWidgetWrapper>
  );
};