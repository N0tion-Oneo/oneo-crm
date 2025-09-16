'use client';

import { useState, useRef, useEffect } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { Variable, ChevronRight, Code } from 'lucide-react';

interface ExpressionEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  availableVariables: Array<{
    nodeId: string;
    label: string;
    outputs: string[]
  }>;
  error?: boolean;
  className?: string;
}

export function ExpressionEditor({
  value,
  onChange,
  placeholder = 'Enter expression or click to insert variables',
  availableVariables,
  error,
  className
}: ExpressionEditorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [cursorPosition, setCursorPosition] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Track cursor position
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value);
    setCursorPosition(e.target.selectionStart || 0);
  };

  const handleTextareaClick = (e: React.MouseEvent<HTMLTextAreaElement>) => {
    setCursorPosition(e.currentTarget.selectionStart || 0);
  };

  const handleTextareaKeyUp = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    setCursorPosition(e.currentTarget.selectionStart || 0);
  };

  const insertVariable = (variable: string) => {
    const before = value.substring(0, cursorPosition);
    const after = value.substring(cursorPosition);
    const newValue = `${before}{{${variable}}}${after}`;
    const newCursorPosition = cursorPosition + variable.length + 4; // +4 for {{}}

    onChange(newValue);
    setCursorPosition(newCursorPosition);
    setIsOpen(false);

    // Focus back on textarea and set cursor position
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        textareaRef.current.setSelectionRange(newCursorPosition, newCursorPosition);
      }
    }, 0);
  };

  // Extract variables from the current value
  const usedVariables = Array.from(value.matchAll(/\{\{([^}]+)\}\}/g)).map(match => match[1]);

  return (
    <div className={cn("space-y-2", className)}>
      <div className="relative">
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={handleTextareaChange}
          onClick={handleTextareaClick}
          onKeyUp={handleTextareaKeyUp}
          placeholder={placeholder}
          className={cn(
            "font-mono text-sm pr-10",
            error && "border-destructive",
            "min-h-[80px]"
          )}
          rows={3}
        />

        <Popover open={isOpen} onOpenChange={setIsOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="absolute top-2 right-2 h-6 w-6"
              type="button"
            >
              <Variable className="h-3.5 w-3.5" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-80 p-0" align="end">
            <div className="p-3 border-b">
              <h4 className="text-sm font-medium">Insert Variable</h4>
              <p className="text-xs text-muted-foreground mt-1">
                Click to insert at cursor position
              </p>
            </div>
            <ScrollArea className="h-64">
              <div className="p-2">
                {availableVariables.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No variables available from previous nodes
                  </p>
                ) : (
                  <div className="space-y-3">
                    {availableVariables.map((node) => (
                      <div key={node.nodeId} className="space-y-1">
                        <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground px-1">
                          <Code className="h-3 w-3" />
                          {node.label}
                        </div>
                        <div className="space-y-0.5">
                          {node.outputs.map((output) => (
                            <button
                              key={`${node.nodeId}.${output}`}
                              type="button"
                              className={cn(
                                "w-full text-left px-2 py-1.5 text-sm rounded-md",
                                "hover:bg-muted transition-colors",
                                "flex items-center justify-between group"
                              )}
                              onClick={() => insertVariable(`${node.nodeId}.${output}`)}
                            >
                              <span className="font-mono text-xs">
                                {output}
                              </span>
                              <ChevronRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </ScrollArea>
            {usedVariables.length > 0 && (
              <div className="p-2 border-t">
                <p className="text-xs text-muted-foreground mb-1.5">Used in expression:</p>
                <div className="flex flex-wrap gap-1">
                  {usedVariables.map((variable, index) => (
                    <Badge key={index} variant="secondary" className="text-xs font-mono">
                      {variable}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </PopoverContent>
        </Popover>
      </div>

      <div className="flex items-start gap-1.5">
        <Code className="h-3 w-3 text-muted-foreground mt-0.5" />
        <p className="text-xs text-muted-foreground">
          Use <code className="font-mono bg-muted px-1 py-0.5 rounded">{`{{variable}}`}</code> syntax
          to reference data from previous nodes
        </p>
      </div>
    </div>
  );
}