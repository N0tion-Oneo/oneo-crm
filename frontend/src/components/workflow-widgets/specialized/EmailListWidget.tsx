/**
 * Email list management widget
 */

import React, { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Plus, X, Mail, AlertCircle } from 'lucide-react';
import { WidgetProps } from '../core/types';
import { BaseWidgetWrapper } from '../basic/BaseWidget';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const EmailListWidget: React.FC<WidgetProps> = (props) => {
  const { value = [], onChange, uiHints = {} } = props;
  const [inputValue, setInputValue] = useState('');
  const [error, setError] = useState<string | null>(null);

  const maxEmails = uiHints.max_emails || 50;
  const allowDuplicates = uiHints.allow_duplicates !== false;

  const validateEmail = (email: string): string | null => {
    if (!email.trim()) {
      return 'Email cannot be empty';
    }
    if (!EMAIL_REGEX.test(email)) {
      return 'Invalid email format';
    }
    if (!allowDuplicates && value.includes(email.toLowerCase())) {
      return 'Email already exists in the list';
    }
    if (value.length >= maxEmails) {
      return `Maximum ${maxEmails} emails allowed`;
    }
    return null;
  };

  const addEmail = () => {
    const email = inputValue.trim().toLowerCase();
    const validationError = validateEmail(email);

    if (validationError) {
      setError(validationError);
      return;
    }

    onChange([...value, email]);
    setInputValue('');
    setError(null);
  };

  const addMultipleEmails = (text: string) => {
    // Split by comma, semicolon, newline, or space
    const emails = text
      .split(/[,;\n\s]+/)
      .map(e => e.trim().toLowerCase())
      .filter(e => e.length > 0);

    const validEmails: string[] = [];
    const invalidEmails: string[] = [];

    emails.forEach(email => {
      if (EMAIL_REGEX.test(email)) {
        if (allowDuplicates || !value.includes(email)) {
          validEmails.push(email);
        }
      } else {
        invalidEmails.push(email);
      }
    });

    if (validEmails.length > 0) {
      const newList = [...value, ...validEmails].slice(0, maxEmails);
      onChange(newList);
      setInputValue('');
    }

    if (invalidEmails.length > 0) {
      setError(`Invalid emails: ${invalidEmails.slice(0, 3).join(', ')}${invalidEmails.length > 3 ? '...' : ''}`);
    } else {
      setError(null);
    }
  };

  const removeEmail = (emailToRemove: string) => {
    onChange(value.filter((email: string) => email !== emailToRemove));
  };

  const clearAll = () => {
    onChange([]);
    setError(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addEmail();
    } else if (e.key === 'Backspace' && !inputValue && value.length > 0) {
      // Remove last email when backspace pressed on empty input
      removeEmail(value[value.length - 1]);
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedText = e.clipboardData.getData('text');
    if (pastedText.includes(',') || pastedText.includes(';') || pastedText.includes('\n')) {
      addMultipleEmails(pastedText);
    } else {
      setInputValue(pastedText);
    }
  };

  return (
    <BaseWidgetWrapper {...props}>
      <div className="space-y-3">
        {/* Input area */}
        <div className="flex gap-2">
          <div className="flex-1">
            <Input
              type="email"
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value);
                setError(null);
              }}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              placeholder={props.placeholder || "Enter email address..."}
              disabled={props.disabled || props.readonly}
            />
          </div>
          <Button
            type="button"
            onClick={addEmail}
            disabled={props.disabled || props.readonly || !inputValue.trim()}
            size="sm"
          >
            <Plus className="w-4 h-4" />
          </Button>
        </div>

        {/* Error message */}
        {error && (
          <div className="flex items-center gap-1 text-red-600 text-sm">
            <AlertCircle className="w-3 h-3" />
            {error}
          </div>
        )}

        {/* Email list */}
        {value.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">
                {value.length} email{value.length !== 1 ? 's' : ''}
                {maxEmails && ` (max ${maxEmails})`}
              </span>
              {!props.disabled && !props.readonly && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={clearAll}
                  className="text-red-600 hover:text-red-700"
                >
                  Clear all
                </Button>
              )}
            </div>

            <div className="flex flex-wrap gap-2 p-3 border rounded-lg bg-gray-50 max-h-48 overflow-y-auto">
              {value.map((email: string, index: number) => (
                <Badge
                  key={`${email}-${index}`}
                  variant="secondary"
                  className="flex items-center gap-1 pl-2 pr-1"
                >
                  <Mail className="w-3 h-3" />
                  <span className="max-w-[200px] truncate" title={email}>
                    {email}
                  </span>
                  {!props.disabled && !props.readonly && (
                    <button
                      type="button"
                      onClick={() => removeEmail(email)}
                      className="ml-1 p-0.5 hover:bg-gray-200 rounded"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Help text */}
        {!error && uiHints.help_text && (
          <p className="text-xs text-gray-500">{uiHints.help_text}</p>
        )}
      </div>
    </BaseWidgetWrapper>
  );
};