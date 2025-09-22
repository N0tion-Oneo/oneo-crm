/**
 * useCanvasSettings Hook
 * Manages workflow canvas settings with localStorage persistence
 */

import { useState, useEffect, useCallback } from 'react';

export type BackgroundVariant = 'dots' | 'lines' | 'cross' | 'none';
export type ConnectionMode = 'loose' | 'strict';

export interface CanvasSettings {
  // Display settings
  showMiniMap: boolean;
  showBackground: boolean;
  backgroundVariant: BackgroundVariant;
  backgroundGap: number;
  backgroundColor: string;

  // Grid & Snapping
  snapToGrid: boolean;
  gridSize: number;
  showGridLines: boolean;

  // Interaction
  panOnScroll: boolean;
  selectionOnDrag: boolean;
  connectionMode: ConnectionMode;

  // Performance
  minZoom: number;
  maxZoom: number;
  animatedEdges: boolean;
}

const DEFAULT_SETTINGS: CanvasSettings = {
  // Display
  showMiniMap: false,
  showBackground: true,
  backgroundVariant: 'dots',
  backgroundGap: 20,
  backgroundColor: '#f0f0f0',

  // Grid
  snapToGrid: false,
  gridSize: 15,
  showGridLines: false,

  // Interaction
  panOnScroll: true,
  selectionOnDrag: false,
  connectionMode: 'loose',

  // Performance
  minZoom: 0.2,
  maxZoom: 2,
  animatedEdges: false,
};

const STORAGE_KEY = 'workflowCanvasSettings';

export function useCanvasSettings() {
  const [settings, setSettings] = useState<CanvasSettings>(DEFAULT_SETTINGS);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load settings from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Merge with defaults to handle new settings added later
        setSettings({ ...DEFAULT_SETTINGS, ...parsed });
      }
    } catch (error) {
      console.error('Failed to load canvas settings:', error);
    }
    setIsLoaded(true);
  }, []);

  // Save settings to localStorage whenever they change
  useEffect(() => {
    if (isLoaded) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
      } catch (error) {
        console.error('Failed to save canvas settings:', error);
      }
    }
  }, [settings, isLoaded]);

  // Update a single setting
  const updateSetting = useCallback(<K extends keyof CanvasSettings>(
    key: K,
    value: CanvasSettings[K]
  ) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  }, []);

  // Update multiple settings at once
  const updateSettings = useCallback((updates: Partial<CanvasSettings>) => {
    setSettings(prev => ({ ...prev, ...updates }));
  }, []);

  // Reset to defaults
  const resetSettings = useCallback(() => {
    setSettings(DEFAULT_SETTINGS);
  }, []);

  // Toggle boolean settings
  const toggleSetting = useCallback((key: keyof CanvasSettings) => {
    setSettings(prev => {
      const current = prev[key];
      if (typeof current === 'boolean') {
        return { ...prev, [key]: !current };
      }
      return prev;
    });
  }, []);

  return {
    settings,
    updateSetting,
    updateSettings,
    resetSettings,
    toggleSetting,
    isLoaded
  };
}