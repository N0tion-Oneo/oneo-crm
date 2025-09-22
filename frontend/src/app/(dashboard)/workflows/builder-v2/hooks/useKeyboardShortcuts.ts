/**
 * useKeyboardShortcuts Hook
 * Handles keyboard shortcuts for workflow canvas
 */

import { useEffect, useCallback } from 'react';

interface ShortcutHandlers {
  onToggleMiniMap?: () => void;
  onToggleGrid?: () => void;
  onToggleBackground?: () => void;
  onToggleSettings?: () => void;
  onDelete?: () => void;
  onSelectAll?: () => void;
  onCopy?: () => void;
  onPaste?: () => void;
  onUndo?: () => void;
  onRedo?: () => void;
  onSave?: () => void;
}

export function useKeyboardShortcuts(handlers: ShortcutHandlers) {
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    // Don't trigger shortcuts when typing in input fields
    if (
      event.target instanceof HTMLInputElement ||
      event.target instanceof HTMLTextAreaElement ||
      event.target instanceof HTMLSelectElement
    ) {
      return;
    }

    const { key, metaKey, ctrlKey, shiftKey } = event;
    const isCtrlOrCmd = metaKey || ctrlKey;

    // Single key shortcuts
    if (!isCtrlOrCmd && !shiftKey) {
      switch (key.toLowerCase()) {
        case 'm':
          event.preventDefault();
          handlers.onToggleMiniMap?.();
          break;
        case 'g':
          event.preventDefault();
          handlers.onToggleGrid?.();
          break;
        case 'b':
          event.preventDefault();
          handlers.onToggleBackground?.();
          break;
        case '/':
          event.preventDefault();
          handlers.onToggleSettings?.();
          break;
        case 'delete':
        case 'backspace':
          // React Flow handles delete by default, but we can override if needed
          if (handlers.onDelete) {
            event.preventDefault();
            handlers.onDelete();
          }
          break;
      }
    }

    // Ctrl/Cmd shortcuts
    if (isCtrlOrCmd && !shiftKey) {
      switch (key.toLowerCase()) {
        case 'a':
          event.preventDefault();
          handlers.onSelectAll?.();
          break;
        case 'c':
          event.preventDefault();
          handlers.onCopy?.();
          break;
        case 'v':
          event.preventDefault();
          handlers.onPaste?.();
          break;
        case 'z':
          event.preventDefault();
          handlers.onUndo?.();
          break;
        case 's':
          event.preventDefault();
          handlers.onSave?.();
          break;
      }
    }

    // Ctrl/Cmd + Shift shortcuts
    if (isCtrlOrCmd && shiftKey) {
      switch (key.toLowerCase()) {
        case 'z':
          event.preventDefault();
          handlers.onRedo?.();
          break;
      }
    }
  }, [handlers]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);
}

// Helper hook for single key shortcuts
export function useKeyPress(targetKey: string, handler: () => void) {
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    // Don't trigger shortcuts when typing in input fields
    if (
      event.target instanceof HTMLInputElement ||
      event.target instanceof HTMLTextAreaElement ||
      event.target instanceof HTMLSelectElement
    ) {
      return;
    }

    if (event.key.toLowerCase() === targetKey.toLowerCase()) {
      event.preventDefault();
      handler();
    }
  }, [targetKey, handler]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);
}