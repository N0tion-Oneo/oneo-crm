// ViewModeToggle - Switch between table/kanban/calendar views
import React from 'react'
import { Table, Columns, CalendarDays } from 'lucide-react'
import { ViewMode, SelectFieldOption, DateFieldOption } from '@/types/records'

export interface ViewModeToggleProps {
  viewMode: ViewMode
  onViewModeChange: (mode: ViewMode) => void
  selectFields: SelectFieldOption[]
  dateFields: DateFieldOption[]
  className?: string
}

export function ViewModeToggle({
  viewMode,
  onViewModeChange,
  selectFields,
  dateFields,
  className = ""
}: ViewModeToggleProps) {
  const canShowKanban = selectFields.length > 0
  const canShowCalendar = dateFields.length > 0

  return (
    <div className={`flex items-center border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 ${className}`}>
      <button
        onClick={() => onViewModeChange('table')}
        className={`px-3 py-2 flex items-center text-sm transition-colors ${
          viewMode === 'table'
            ? 'bg-primary text-white'
            : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
        }`}
      >
        <Table className="w-4 h-4 mr-2" />
        Table
      </button>
      
      <button
        onClick={() => onViewModeChange('kanban')}
        disabled={!canShowKanban}
        className={`px-3 py-2 flex items-center text-sm transition-colors border-l border-gray-300 dark:border-gray-600 ${
          viewMode === 'kanban'
            ? 'bg-primary text-white'
            : !canShowKanban
            ? 'text-gray-400 dark:text-gray-500 cursor-not-allowed'
            : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
        }`}
        title={!canShowKanban ? 'No select fields available for Kanban view' : ''}
      >
        <Columns className="w-4 h-4 mr-2" />
        Kanban
      </button>
      
      <button
        onClick={() => onViewModeChange('calendar')}
        disabled={!canShowCalendar}
        className={`px-3 py-2 flex items-center text-sm transition-colors border-l border-gray-300 dark:border-gray-600 ${
          viewMode === 'calendar'
            ? 'bg-primary text-white'
            : !canShowCalendar
            ? 'text-gray-400 dark:text-gray-500 cursor-not-allowed'
            : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
        }`}
        title={!canShowCalendar ? 'No date fields available for Calendar view' : ''}
      >
        <CalendarDays className="w-4 h-4 mr-2" />
        Calendar
      </button>
    </div>
  )
}