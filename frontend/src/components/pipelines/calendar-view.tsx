'use client'

import React, { useState, useMemo } from 'react'
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, isSameDay, isToday, parseISO, addMonths, subMonths } from 'date-fns'
import { ChevronLeft, ChevronRight, Calendar, Plus, Eye } from 'lucide-react'
import { type Record, type Pipeline, convertToFieldType } from '@/types/records'
import { FieldResolver } from '@/lib/field-system/field-registry'

interface CalendarViewProps {
  pipeline: Pipeline
  records: Record[]
  calendarField: string
  onEditRecord: (record: Record) => void
  onCreateRecord: () => void
}

interface CalendarEvent {
  id: string
  title: string
  date: Date
  record: Record
  color: string
}

const EVENT_COLORS = [
  'bg-blue-500',
  'bg-green-500',
  'bg-purple-500',
  'bg-red-500',
  'bg-yellow-500',
  'bg-indigo-500',
  'bg-pink-500',
  'bg-gray-500'
]

export function CalendarView({
  pipeline,
  records,
  calendarField,
  onEditRecord,
  onCreateRecord
}: CalendarViewProps) {
  const [currentDate, setCurrentDate] = useState(new Date())
  const [view, setView] = useState<'month' | 'week'>('month')

  // Get the calendar field configuration
  const calendarFieldConfig = useMemo(() => {
    return pipeline.fields.find(f => f.name === calendarField)
  }, [pipeline.fields, calendarField])

  // Convert records to calendar events
  const events = useMemo((): CalendarEvent[] => {
    if (!calendarFieldConfig) return []

    return records
      .filter(record => record.data[calendarField]) // Only records with date values
      .map((record, index) => {
        let date: Date
        try {
          const dateValue = record.data[calendarField]
          date = typeof dateValue === 'string' ? parseISO(dateValue) : new Date(dateValue)
        } catch {
          return null
        }

        // Find a title field
        const titleField = pipeline.fields.find(f => 
          ['name', 'title', 'subject', 'description'].includes(f.name.toLowerCase()) ||
          f.field_type === 'text'
        )
        
        const title = titleField 
          ? record.data[titleField.name] || `Record ${record.id}`
          : `Record ${record.id}`

        return {
          id: record.id,
          title: String(title).substring(0, 30) + (String(title).length > 30 ? '...' : ''),
          date,
          record,
          color: EVENT_COLORS[index % EVENT_COLORS.length]
        }
      })
      .filter(Boolean) as CalendarEvent[]
  }, [records, calendarField, calendarFieldConfig, pipeline.fields])

  // Get calendar days for the current month
  const calendarDays = useMemo(() => {
    const start = startOfMonth(currentDate)
    const end = endOfMonth(currentDate)
    return eachDayOfInterval({ start, end })
  }, [currentDate])

  // Get events for a specific day
  const getEventsForDay = (day: Date) => {
    return events.filter(event => isSameDay(event.date, day))
  }

  // Navigation handlers
  const goToPreviousMonth = () => {
    setCurrentDate(prev => subMonths(prev, 1))
  }

  const goToNextMonth = () => {
    setCurrentDate(prev => addMonths(prev, 1))
  }

  const goToToday = () => {
    setCurrentDate(new Date())
  }

  if (!calendarFieldConfig) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-500 dark:text-gray-400">
          Calendar field configuration not found
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Calendar Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {format(currentDate, 'MMMM yyyy')}
          </h2>
          
          <div className="flex items-center space-x-1">
            <button
              onClick={goToPreviousMonth}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            
            <button
              onClick={goToNextMonth}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
          
          <button
            onClick={goToToday}
            className="px-3 py-1 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 rounded-md hover:bg-blue-50 dark:hover:bg-blue-900/20"
          >
            Today
          </button>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {events.length} events
          </span>
          
          <button
            onClick={onCreateRecord}
            className="px-3 py-1.5 text-sm bg-primary text-white rounded-md hover:bg-primary/90 flex items-center"
          >
            <Plus className="w-4 h-4 mr-1" />
            Add Event
          </button>
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="flex-1 overflow-auto">
        <div className="p-4">
          {/* Days of Week Header */}
          <div className="grid grid-cols-7 gap-px mb-2">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
              <div
                key={day}
                className="p-2 text-center text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                {day}
              </div>
            ))}
          </div>

          {/* Calendar Days */}
          <div className="grid grid-cols-7 gap-px bg-gray-200 dark:bg-gray-700 rounded-lg overflow-hidden">
            {calendarDays.map(day => {
              const dayEvents = getEventsForDay(day)
              const isCurrentMonth = isSameMonth(day, currentDate)
              const isDayToday = isToday(day)
              
              return (
                <div
                  key={day.toISOString()}
                  className={`min-h-24 p-2 bg-white dark:bg-gray-800 ${
                    !isCurrentMonth ? 'opacity-40' : ''
                  } ${
                    isDayToday ? 'ring-2 ring-blue-500 ring-inset' : ''
                  }`}
                >
                  {/* Day Number */}
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-sm font-medium ${
                      isDayToday 
                        ? 'text-blue-600 dark:text-blue-400' 
                        : isCurrentMonth 
                        ? 'text-gray-900 dark:text-white' 
                        : 'text-gray-400 dark:text-gray-500'
                    }`}>
                      {format(day, 'd')}
                    </span>
                    
                    {dayEvents.length > 3 && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        +{dayEvents.length - 3}
                      </span>
                    )}
                  </div>

                  {/* Events */}
                  <div className="space-y-1">
                    {dayEvents.slice(0, 3).map(event => (
                      <div
                        key={event.id}
                        onClick={() => onEditRecord(event.record)}
                        className={`px-2 py-1 text-xs text-white rounded cursor-pointer hover:opacity-80 transition-opacity ${event.color}`}
                        title={event.title}
                      >
                        <div className="truncate">
                          {event.title}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Events Summary */}
      {events.length > 0 && (
        <div className="border-t border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white">
              Events in {format(currentDate, 'MMMM yyyy')}
            </h3>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {events.filter(event => 
                isSameMonth(event.date, currentDate)
              ).length} this month
            </span>
          </div>
          
          <div className="max-h-32 overflow-y-auto">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {events
                .filter(event => isSameMonth(event.date, currentDate))
                .sort((a, b) => a.date.getTime() - b.date.getTime())
                .slice(0, 6)
                .map(event => (
                  <div
                    key={event.id}
                    onClick={() => onEditRecord(event.record)}
                    className="flex items-center space-x-2 p-2 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer group"
                  >
                    <div className={`w-3 h-3 rounded-full ${event.color}`}></div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {event.title}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {format(event.date, 'MMM d, yyyy')}
                        {calendarFieldConfig.field_type === 'datetime' && (
                          <span> at {format(event.date, 'h:mm a')}</span>
                        )}
                      </div>
                    </div>
                    <Eye className="w-4 h-4 text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300" />
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}