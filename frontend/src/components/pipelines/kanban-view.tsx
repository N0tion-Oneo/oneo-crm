'use client'

import React, { useState, useMemo, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, MoreHorizontal, Edit, User, Calendar } from 'lucide-react'
import { type Record, type Pipeline, type RecordField } from './record-list-view'
import { FieldResolver } from '@/lib/field-system/field-registry'
import { convertToFieldType } from './record-list-view'

interface KanbanViewProps {
  pipeline: Pipeline
  records: Record[]
  kanbanField: string
  onEditRecord: (record: Record) => void
  onCreateRecord: () => void
  onUpdateRecord: (recordId: string, fieldName: string, value: any) => Promise<void>
}

interface KanbanColumn {
  id: string
  label: string
  records: Record[]
  color: string
}

const COLUMN_COLORS = [
  'border-blue-200 bg-blue-50 dark:bg-blue-900/20',
  'border-green-200 bg-green-50 dark:bg-green-900/20', 
  'border-yellow-200 bg-yellow-50 dark:bg-yellow-900/20',
  'border-purple-200 bg-purple-50 dark:bg-purple-900/20',
  'border-red-200 bg-red-50 dark:bg-red-900/20',
  'border-indigo-200 bg-indigo-50 dark:bg-indigo-900/20',
  'border-pink-200 bg-pink-50 dark:bg-pink-900/20',
  'border-gray-200 bg-gray-50 dark:bg-gray-900/20'
]

export function KanbanView({
  pipeline,
  records,
  kanbanField,
  onEditRecord,
  onCreateRecord,
  onUpdateRecord
}: KanbanViewProps) {
  const [draggedRecord, setDraggedRecord] = useState<Record | null>(null)
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const columnRefs = useRef<Record<string, HTMLDivElement | null>>({})
  const kanbanBoardRef = useRef<HTMLDivElement>(null)

  // Get the field configuration for kanban grouping
  const kanbanFieldConfig = useMemo(() => {
    return pipeline.fields.find(f => f.name === kanbanField)
  }, [pipeline.fields, kanbanField])

  // Create columns based on field options
  const columns = useMemo(() => {
    if (!kanbanFieldConfig) return []

    const options = kanbanFieldConfig.field_config?.options || []
    
    // Add "No Value" column for records without the kanban field value
    const allOptions = [
      { value: '', label: 'No Value' },
      ...options.map(option => 
        typeof option === 'string' 
          ? { value: option, label: option }
          : { value: option.value || option.label, label: option.label || option.value }
      )
    ]

    return allOptions.map((option, index): KanbanColumn => {
      const columnRecords = records.filter(record => {
        const value = record.data[kanbanField]
        if (!value && option.value === '') return true
        return value === option.value
      })

      return {
        id: option.value || 'no-value',
        label: option.label || 'No Value',
        records: columnRecords,
        color: COLUMN_COLORS[index % COLUMN_COLORS.length]
      }
    })
  }, [records, kanbanField, kanbanFieldConfig])

  // Get display fields for record cards (first 3 visible fields)
  const displayFields = useMemo(() => {
    return pipeline.fields
      .filter(field => 
        field.is_visible_in_list !== false && 
        field.name !== kanbanField &&
        !['id', 'created_at', 'updated_at'].includes(field.name)
      )
      .slice(0, 3)
  }, [pipeline.fields, kanbanField])

  // Handle drag start
  const handleDragStart = (record: Record) => {
    setDraggedRecord(record)
    setIsDragging(true)
  }

  // Detect which column the drag position is over with improved bounds checking
  const getColumnFromPosition = useCallback((x: number, y: number): string | null => {
    for (const [columnId, ref] of Object.entries(columnRefs.current)) {
      if (!ref) continue
      
      const rect = ref.getBoundingClientRect()
      // Add some margin to make drop zones more forgiving
      const margin = 20
      if (x >= rect.left - margin && 
          x <= rect.right + margin && 
          y >= rect.top - margin && 
          y <= rect.bottom + margin) {
        return columnId
      }
    }
    return null
  }, [])

  // Handle drag position updates
  const handleDrag = useCallback((event: any, info: any) => {
    const { point } = info
    const columnId = getColumnFromPosition(point.x, point.y)
    setDragOverColumn(columnId)
    
    // Only allow horizontal movement between columns, not vertical reordering within columns
    if (draggedRecord && columnId && columnId !== getRecordColumn(draggedRecord)) {
      // Moving between columns - allow
    } else if (draggedRecord && columnId === getRecordColumn(draggedRecord)) {
      // Moving within same column - for now, just visual feedback
      // Future: implement card reordering within columns
    }
  }, [getColumnFromPosition, draggedRecord])

  // Helper to get which column a record belongs to
  const getRecordColumn = useCallback((record: Record) => {
    const value = record.data[kanbanField]
    if (!value) return 'no-value'
    return String(value)
  }, [kanbanField])

  // Handle drag end with improved position-based drop detection
  const handleDragEnd = useCallback(async (event: any, info: any) => {
    const { point, offset } = info
    
    // Calculate the actual drop position relative to the page
    const dropX = point.x
    const dropY = point.y
    
    const targetColumnId = getColumnFromPosition(dropX, dropY)
    
    setDragOverColumn(null)
    setIsDragging(false)

    if (!draggedRecord) {
      return
    }

    // Check if dropped in a valid column
    if (!targetColumnId) {
      // Dropped outside valid column - card will snap back
      console.log('Dropped outside valid column, snapping back')
      setDraggedRecord(null)
      return
    }

    const newValue = targetColumnId === 'no-value' ? null : targetColumnId
    const currentValue = draggedRecord.data[kanbanField]
    
    // Don't update if dropping in same column
    if (currentValue === newValue) {
      console.log('Dropped in same column, no update needed')
      setDraggedRecord(null)
      return
    }

    try {
      await onUpdateRecord(draggedRecord.id, kanbanField, newValue)
      console.log(`✅ Moved record ${draggedRecord.id} from ${currentValue || 'no-value'} to ${targetColumnId}`)
    } catch (error) {
      console.error('❌ Failed to update record:', error)
      // On error, the real-time system should revert the UI automatically
    } finally {
      setDraggedRecord(null)
    }
  }, [draggedRecord, kanbanField, onUpdateRecord, getColumnFromPosition])

  // Create stable ref callback for columns
  const setColumnRef = useCallback((columnId: string) => {
    return (el: HTMLDivElement | null) => {
      columnRefs.current[columnId] = el
    }
  }, [])

  // Render record card
  const renderRecordCard = (record: Record) => {
    // Find a title field (name, title, or first text field)
    const titleField = pipeline.fields.find(f => 
      ['name', 'title', 'subject', 'description'].includes(f.name.toLowerCase()) ||
      f.field_type === 'text'
    )
    
    const title = titleField 
      ? record.data[titleField.name] || `Record ${record.id}`
      : `Record ${record.id}`

    return (
      <motion.div
        key={record.id}
        layout={!isDragging} // Disable layout animation during any drag operation
        layoutId={`card-${record.id}`} // Unique layout ID for smoother transitions
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        drag="x" // Only allow horizontal dragging between columns
        dragMomentum={false}
        dragElastic={0.1}
        dragConstraints={kanbanBoardRef}
        dragSnapToOrigin={true} // Snap back to origin if not dropped in valid column
        whileDrag={{ 
          scale: 1.02,
          rotate: 2,
          zIndex: 50,
          boxShadow: "0 15px 30px -5px rgba(0, 0, 0, 0.2)"
        }}
        onDragStart={() => handleDragStart(record)}
        onDrag={handleDrag}
        onDragEnd={handleDragEnd}
        className={`group p-3 bg-white dark:bg-gray-800 rounded-lg shadow-sm border cursor-move hover:shadow-md ${
          draggedRecord?.id === record.id 
            ? dragOverColumn 
              ? 'opacity-80 border-green-400' // Valid drop zone
              : 'opacity-80 border-red-400'   // Invalid drop zone
            : isDragging 
            ? 'opacity-50 border-gray-200 dark:border-gray-700' 
            : 'border-gray-200 dark:border-gray-700'
        }`}
        style={{
          // Ensure proper spacing and positioning
          position: draggedRecord?.id === record.id ? 'absolute' : 'static',
          transition: draggedRecord?.id === record.id ? 'none' : 'all 0.2s ease',
          // Prevent cards from overlapping during drag
          minHeight: '120px',
          width: '100%',
          display: 'block',
          // Only apply z-index when dragging
          ...(draggedRecord?.id === record.id && { zIndex: 1000 })
        }}
        title="Double-click to edit"
        onDoubleClick={() => onEditRecord(record)}
      >
        {/* Card Title */}
        <div className="flex items-start justify-between mb-2">
          <div className="font-medium text-gray-900 dark:text-white text-sm line-clamp-2 flex-1">
            {title}
          </div>
          <Edit className="w-3 h-3 text-gray-400 ml-2 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>

        {/* Display Fields */}
        <div className="space-y-1">
          {displayFields.map(field => {
            const value = record.data[field.name]
            if (!value) return null

            const fieldType = convertToFieldType(field)
            const formattedValue = FieldResolver.formatValue(fieldType, value, 'table')

            return (
              <div key={field.name} className="flex items-center text-xs text-gray-600 dark:text-gray-400">
                <span className="font-medium mr-2 min-w-0 flex-shrink-0">
                  {field.display_name || field.name}:
                </span>
                <span className="truncate">
                  {React.isValidElement(formattedValue) ? formattedValue : String(formattedValue)}
                </span>
              </div>
            )
          }).filter(Boolean)}
        </div>

        {/* Card Footer */}
        <div className="flex items-center justify-between mt-3 pt-2 border-t border-gray-100 dark:border-gray-700">
          <div className="flex items-center text-xs text-gray-500">
            {record.created_by && (
              <div className="flex items-center">
                <User className="w-3 h-3 mr-1" />
                <span>{record.created_by.first_name} {record.created_by.last_name}</span>
              </div>
            )}
          </div>
          
          <div className="flex items-center text-xs text-gray-500">
            <Calendar className="w-3 h-3 mr-1" />
            <span>{new Date(record.updated_at).toLocaleDateString()}</span>
          </div>
        </div>
      </motion.div>
    )
  }

  if (!kanbanFieldConfig) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-500 dark:text-gray-400">
          Kanban field configuration not found
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Interaction Hint */}
      <div className="px-6 py-2 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800">
        <p className="text-sm text-blue-700 dark:text-blue-300">
          💡 <strong>Drag</strong> cards between columns to update status • <strong>Double-click</strong> cards to edit details
        </p>
      </div>

      {/* Kanban Board */}
      <div className="flex-1 overflow-x-auto">
        <div ref={kanbanBoardRef} className="flex space-x-6 p-6 min-w-max">
          {columns.map(column => (
            <div
              key={column.id}
              className="flex-shrink-0 w-80"
            >
              {/* Column Header */}
              <div className={`rounded-t-lg border-t border-l border-r p-4 ${column.color}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                      {column.label}
                    </h3>
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {column.records.length} records
                    </span>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={onCreateRecord}
                      className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded"
                      title="Add record to this column"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                    <button className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded">
                      <MoreHorizontal className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Column Content */}
              <div 
                ref={setColumnRef(column.id)}
                className={`min-h-96 border-l border-r border-b rounded-b-lg p-4 transition-all duration-200 ${
                  column.color
                } ${
                  dragOverColumn === column.id 
                    ? 'border-blue-400 bg-blue-100 dark:bg-blue-900/40 scale-[1.02]' 
                    : ''
                } ${
                  isDragging ? 'border-dashed border-2' : ''
                }`}
                style={{
                  // Ensure cards don't overlap and maintain proper organization
                  display: 'block', // Use block layout for better card stacking
                  position: 'relative',
                  // Ensure proper spacing between cards
                  paddingTop: '8px',
                  paddingBottom: '8px'
                }}>
                <div className="space-y-3">
                  <AnimatePresence mode="popLayout">
                    {column.records.map((record, index) => (
                      <motion.div 
                        key={record.id} 
                        layout={!isDragging}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.2, delay: index * 0.05 }}
                        style={{ 
                          position: 'static', // Use static positioning to prevent stacking
                          zIndex: draggedRecord?.id === record.id ? 50 : 'auto',
                          display: 'block',
                          width: '100%'
                        }}
                      >
                        {renderRecordCard(record)}
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>

                {/* Empty State */}
                {column.records.length === 0 && (
                  <div className="text-center py-8 text-gray-400 dark:text-gray-500">
                    <div className="text-sm">No records</div>
                    <button
                      onClick={onCreateRecord}
                      className="mt-2 text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                    >
                      Add first record
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}