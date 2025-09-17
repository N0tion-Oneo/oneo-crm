'use client';

import { useState, useRef, KeyboardEvent } from 'react';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { X, Plus, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

interface EnhancedTagInputProps {
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
  suggestions?: string[];
  validation?: (tag: string) => string | null; // Return error message if invalid
  helpText?: string;
  maxTags?: number;
  allowDuplicates?: boolean;
  className?: string;
}

export function EnhancedTagInput({
  value = [],
  onChange,
  placeholder = 'Type and press Enter to add...',
  disabled = false,
  suggestions = [],
  validation,
  helpText,
  maxTags,
  allowDuplicates = false,
  className
}: EnhancedTagInputProps) {
  const [inputValue, setInputValue] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const filteredSuggestions = suggestions.filter(
    s => s.toLowerCase().includes(inputValue.toLowerCase()) && !value.includes(s)
  );

  const addTag = (tag: string) => {
    const trimmedTag = tag.trim();

    if (!trimmedTag) {
      setError('Tag cannot be empty');
      return;
    }

    if (!allowDuplicates && value.includes(trimmedTag)) {
      setError('This tag already exists');
      return;
    }

    if (maxTags && value.length >= maxTags) {
      setError(`Maximum ${maxTags} tags allowed`);
      return;
    }

    if (validation) {
      const validationError = validation(trimmedTag);
      if (validationError) {
        setError(validationError);
        return;
      }
    }

    onChange([...value, trimmedTag]);
    setInputValue('');
    setError(null);
    setShowSuggestions(false);
  };

  const removeTag = (index: number) => {
    const newTags = value.filter((_, i) => i !== index);
    onChange(newTags);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addTag(inputValue);
    } else if (e.key === 'Backspace' && !inputValue && value.length > 0) {
      removeTag(value.length - 1);
    }

    // Clear error when typing
    if (error) {
      setError(null);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    addTag(suggestion);
    inputRef.current?.focus();
  };

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex flex-wrap gap-2 p-2 border rounded-lg bg-background min-h-[42px]">
        {value.map((tag, index) => (
          <Badge key={index} variant="secondary" className="gap-1">
            {tag}
            {!disabled && (
              <Button
                size="sm"
                variant="ghost"
                className="h-3 w-3 p-0 hover:bg-transparent"
                onClick={() => removeTag(index)}
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </Badge>
        ))}

        {(!maxTags || value.length < maxTags) && !disabled && (
          <div className="flex-1 min-w-[120px] relative">
            <Input
              ref={inputRef}
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value);
                setShowSuggestions(e.target.value.length > 0);
              }}
              onKeyDown={handleKeyDown}
              onFocus={() => setShowSuggestions(inputValue.length > 0)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              placeholder={value.length === 0 ? placeholder : ''}
              disabled={disabled}
              className="border-0 shadow-none px-0 h-7 focus-visible:ring-0"
            />

            {/* Suggestions dropdown */}
            {showSuggestions && filteredSuggestions.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-popover border rounded-md shadow-md">
                <div className="max-h-48 overflow-y-auto p-1">
                  {filteredSuggestions.map((suggestion, i) => (
                    <button
                      key={i}
                      className="w-full text-left px-2 py-1.5 text-sm hover:bg-muted rounded"
                      onClick={() => handleSuggestionClick(suggestion)}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}

      {/* Help text */}
      {helpText && !error && (
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Info className="h-3 w-3" />
          <span>{helpText}</span>
        </div>
      )}

      {/* Tag count */}
      {maxTags && (
        <p className="text-xs text-muted-foreground">
          {value.length} / {maxTags} tags
        </p>
      )}
    </div>
  );
}