'use client'

import React, { useState, useMemo, useCallback, useRef, useEffect, memo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, MoreHorizontal, Edit, User, Calendar } from 'lucide-react'
import { type Record, type Pipeline, type RecordField, convertToFieldType } from '@/types/records'
import { FieldResolver } from '@/lib/field-system/field-registry'

interface KanbanViewProps {
  pipeline: Pipeline
  records: Record[]
  kanbanField: string
  onEditRecord: (record: Record) => void
  onCreateRecord: () => void
  onUpdateRecord: (recordId: string, fieldName: string, value: any) => Promise<void>
}

type ColumnSize = 'compact' | 'standard' | 'wide' | 'extra-wide'
type CardViewMode = 'minimal' | 'standard' | 'detailed'

interface CardCustomization {
  viewMode: CardViewMode
  selectedFields: string[]
  showAvatar: boolean
  showDates: boolean
  maxFields: number
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

// Column width configuration based on size selection
const getColumnWidth = (columnSize: ColumnSize, screenSize: 'mobile' | 'tablet' | 'desktop') => {
  if (screenSize === 'mobile') {
    return 'w-72' // Fixed width for mobile
  }
  
  const widthMap = {
    'compact': 'w-64',      // 256px
    'standard': 'w-80',     // 320px
    'wide': 'w-96',         // 384px
    'extra-wide': 'w-[28rem]' // 448px
  }
  
  return widthMap[columnSize]
}

const KanbanViewComponent = function KanbanView({
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
  const [screenSize, setScreenSize] = useState<'mobile' | 'tablet' | 'desktop'>('desktop')
  const [columnSize, setColumnSize] = useState<ColumnSize>('standard')
  const [showCustomization, setShowCustomization] = useState(false)
  const [cardCustomization, setCardCustomization] = useState<CardCustomization>({
    viewMode: 'standard',
    selectedFields: [],
    showAvatar: true,
    showDates: true,
    maxFields: 3
  })
  
  // Responsive screen size detection
  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth
      if (width < 768) {
        setScreenSize('mobile')
      } else if (width < 1024) {
        setScreenSize('tablet')
      } else {
        setScreenSize('desktop')
      }
    }
    
    handleResize() // Initial check
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])
  const columnRefs = useRef<{[key: string]: HTMLDivElement | null}>({})
  const kanbanBoardRef = useRef<HTMLDivElement>(null)
  
  // Cleanup refs and timeouts on unmount
  useEffect(() => {
    return () => {
      // Clear any pending drag throttle
      if (dragThrottleRef.current) {
        clearTimeout(dragThrottleRef.current)
      }
      
      // Clear column refs to prevent memory leaks
      columnRefs.current = {}
      columnRectsRef.current.clear()
    }
  }, [])

  // Get the field configuration for kanban grouping
  const kanbanFieldConfig = useMemo(() => {
    return pipeline.fields.find(f => f.name === kanbanField)
  }, [pipeline.fields, kanbanField])

  // Optimized column structure computation with stable references
  const columnStructure = useMemo(() => {
    if (!kanbanFieldConfig) return []
    
    const options = kanbanFieldConfig.field_config?.options || []
    return [
      { value: '', label: 'No Value' },
      ...options.map((option: any) => 
        typeof option === 'string' 
          ? { value: option, label: option }
          : { value: option.value || option.label, label: option.label || option.value }
      )
    ]
  }, [kanbanFieldConfig])
  
  // Separate record distribution computation for better performance
  const recordsByColumn = useMemo(() => {
    const distribution = new Map<string, Record[]>()
    
    for (const record of records) {
      const value = record.data[kanbanField]
      const columnId = (!value || value === '') ? 'no-value' : String(value)
      
      if (!distribution.has(columnId)) {
        distribution.set(columnId, [])
      }
      distribution.get(columnId)!.push(record)
    }
    
    return distribution
  }, [records, kanbanField])

  // Final columns with cached structure and dynamic records
  const columns = useMemo((): KanbanColumn[] => {
    return columnStructure.map((option, index) => {
      const columnId = option.value || 'no-value'
      const columnRecords = recordsByColumn.get(columnId) || []

      return {
        id: columnId,
        label: option.label || 'No Value',
        records: columnRecords,
        color: COLUMN_COLORS[index % COLUMN_COLORS.length]
      }
    })
  }, [columnStructure, recordsByColumn])

  // Initialize card customization with available fields
  useEffect(() => {
    if (cardCustomization.selectedFields.length === 0) {
      const availableFields = pipeline.fields
        .filter(field => 
          field.is_visible_in_list !== false && 
          field.name !== kanbanField &&
          !['id', 'created_at', 'updated_at'].includes(field.name)
        )
        .slice(0, cardCustomization.maxFields)
        .map(field => field.name)
      
      setCardCustomization(prev => ({ ...prev, selectedFields: availableFields }))
    }
  }, [pipeline.fields, kanbanField, cardCustomization.selectedFields.length, cardCustomization.maxFields])
  
  // Get fields to display based on customization
  const displayFields = useMemo(() => {
    if (cardCustomization.selectedFields.length === 0) {
      return pipeline.fields
        .filter(field => 
          field.is_visible_in_list !== false && 
          field.name !== kanbanField &&
          !['id', 'created_at', 'updated_at'].includes(field.name)
        )
        .slice(0, cardCustomization.maxFields)
    }
    
    return pipeline.fields.filter(field => 
      cardCustomization.selectedFields.includes(field.name)
    )
  }, [pipeline.fields, kanbanField, cardCustomization.selectedFields, cardCustomization.maxFields])
  
  // Available fields for customization
  const availableFields = useMemo(() => {
    return pipeline.fields.filter(field => 
      field.is_visible_in_list !== false && 
      field.name !== kanbanField &&
      !['id', 'created_at', 'updated_at'].includes(field.name)
    )
  }, [pipeline.fields, kanbanField])

  // Handle drag start
  const handleDragStart = (record: Record) => {
    setDraggedRecord(record)
    setIsDragging(true)
  }

  // Optimized column collision detection with cached rects
  const columnRectsRef = useRef<Map<string, DOMRect>>(new Map())
  const updateColumnRects = useCallback(() => {
    const rects = new Map<string, DOMRect>()
    for (const [columnId, ref] of Object.entries(columnRefs.current)) {
      if (ref) {
        rects.set(columnId, ref.getBoundingClientRect())
      }
    }
    columnRectsRef.current = rects
  }, [])
  
  const getColumnFromPosition = useCallback((x: number, y: number): string | null => {
    const rects = columnRectsRef.current
    
    for (const [columnId, rect] of rects.entries()) {
      // Generous drop zone with 30px margin for better UX
      const margin = 30
      if (x >= rect.left - margin && 
          x <= rect.right + margin && 
          y >= rect.top - margin && 
          y <= rect.bottom + margin) {
        return columnId
      }
    }
    return null
  }, [])
  
  // Update column rects when layout changes
  useEffect(() => {
    updateColumnRects()
    
    const handleResize = () => updateColumnRects()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [columns.length, updateColumnRects])

  // Throttled drag handling for better performance
  const dragThrottleRef = useRef<number>()
  const handleDrag = useCallback((event: any, info: any) => {
    // Throttle drag updates to avoid excessive re-renders
    if (dragThrottleRef.current) {
      clearTimeout(dragThrottleRef.current)
    }
    
    dragThrottleRef.current = window.setTimeout(() => {
      const { point } = info
      const columnId = getColumnFromPosition(point.x, point.y)
      
      // Only update if column actually changed
      setDragOverColumn(prevColumn => {
        if (prevColumn === columnId) return prevColumn
        return columnId
      })
    }, 16) // ~60fps throttling
  }, [getColumnFromPosition])

  // Helper to get which column a record belongs to
  const getRecordColumn = useCallback((record: Record) => {
    const value = record.data[kanbanField]
    if (!value) return 'no-value'
    return String(value)
  }, [kanbanField])
  
  // Helper to find card position within column
  const getCardPositionInColumn = useCallback((x: number, y: number, columnId: string): number => {
    const column = columns.find(col => col.id === columnId)
    if (!column) return -1
    
    const columnRef = columnRefs.current[columnId]
    if (!columnRef) return -1
    
    const columnRect = columnRef.getBoundingClientRect()
    const relativeY = y - columnRect.top
    
    // Each card is roughly 140px tall with spacing
    const cardHeight = 140
    const insertPosition = Math.max(0, Math.floor(relativeY / cardHeight))
    
    return Math.min(insertPosition, column.records.length)
  }, [columns])

  // Handle drag end with column movement and reordering
  const handleDragEnd = useCallback(async (event: any, info: any) => {
    const { point } = info
    
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
      console.log('Dropped outside valid column, snapping back')
      setDraggedRecord(null)
      return
    }

    const newValue = targetColumnId === 'no-value' ? null : targetColumnId
    const currentValue = draggedRecord.data[kanbanField]
    const currentColumn = getRecordColumn(draggedRecord)
    
    // If moving to different column, update the field value
    if (currentValue !== newValue) {
      try {
        await onUpdateRecord(draggedRecord.id, kanbanField, newValue)
        console.log(`✅ Moved record ${draggedRecord.id} from ${currentColumn} to ${targetColumnId}`)
      } catch (error) {
        console.error('❌ Failed to update record:', error)
      }
    } else {
      // Same column - handle reordering
      const newPosition = getCardPositionInColumn(dropX, dropY, targetColumnId)
      console.log(`Card reordered within ${targetColumnId} to position ${newPosition}`)
      // Note: For now we just log reordering. In a full implementation,
      // you'd want to update a separate 'order' field on the record
    }
    
    setDraggedRecord(null)
  }, [draggedRecord, kanbanField, onUpdateRecord, getColumnFromPosition, getRecordColumn, getCardPositionInColumn])

  // Optimized ref callback with cleanup
  const setColumnRef = useCallback((columnId: string) => {
    return (el: HTMLDivElement | null) => {
      if (el) {
        columnRefs.current[columnId] = el
        // Update rects when ref changes
        requestAnimationFrame(() => updateColumnRects())
      } else {
        // Clean up when component unmounts
        delete columnRefs.current[columnId]
        columnRectsRef.current.delete(columnId)
      }
    }
  }, [updateColumnRects])

  // Memoized title field computation
  const titleField = useMemo(() => {
    return pipeline.fields.find(f => 
      ['name', 'title', 'subject', 'description'].includes(f.name.toLowerCase()) ||
      f.field_type === 'text'
    )
  }, [pipeline.fields])
  
  // Optimized record card renderer with memoization
  const renderRecordCard = useCallback((record: Record) => {
    const title = titleField 
      ? record.data[titleField.name] || `Record ${record.id}`
      : `Record ${record.id}`

    return (
      <motion.div
        key={record.id}
        layout={false} // Disable all layout animations
        initial={false}
        animate={false}
        exit={false as any}
        drag // Allow full drag movement
        dragMomentum={false}
        dragElastic={0.1}
        dragConstraints={false}
        dragSnapToOrigin={true} // Snap back to origin if not dropped in valid column
        whileDrag={{ 
          scale: 1.0,
          rotate: 0,
          zIndex: 50,
          opacity: 0.8
        }}
        onDragStart={() => handleDragStart(record)}
        onDrag={handleDrag}
        onDragEnd={handleDragEnd}
        className={`group p-3 bg-white dark:bg-gray-800 rounded-lg shadow-sm border cursor-move ${
          draggedRecord?.id === record.id 
            ? dragOverColumn 
              ? 'border-green-400' // Valid drop zone
              : 'border-red-400'   // Invalid drop zone
            : isDragging 
            ? 'opacity-50 border-gray-200 dark:border-gray-700' 
            : 'border-gray-200 dark:border-gray-700'
        }`}
        style={{
          position: draggedRecord?.id === record.id ? 'absolute' : 'static',
          transition: draggedRecord?.id === record.id ? 'none' : 'all 0.2s ease',
          minHeight: cardCustomization.viewMode === 'minimal' ? '100px' : cardCustomization.viewMode === 'standard' ? '120px' : '160px',
          width: '100%',
          display: 'block',
          ...(draggedRecord?.id === record.id && { zIndex: 1000 })
        }}
        title="Double-click to edit"
        onDoubleClick={() => onEditRecord(record)}
      >
        {/* Card Title */}
        <div className="flex items-start justify-between mb-2">
          <div className={`font-medium text-gray-900 dark:text-white flex-1 ${
            cardCustomization.viewMode === 'minimal' ? 'text-sm line-clamp-1' :
            cardCustomization.viewMode === 'standard' ? 'text-sm line-clamp-2' :
            'text-base line-clamp-2'
          }`}>
            {title}
          </div>
          <Edit className="w-3 h-3 text-gray-400 ml-2 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>

        {/* Display Fields */}
        {cardCustomization.viewMode !== 'minimal' && displayFields.length > 0 && (
          <div className={`space-y-1 ${cardCustomization.viewMode === 'detailed' ? 'space-y-2' : ''}`}>
            {displayFields.map(field => {
              const value = record.data[field.name]
              if (!value) return null

              const fieldType = convertToFieldType(field)
              const formattedValue = FieldResolver.formatValue(fieldType, value, 'table')

              return (
                <div key={field.name} className={`flex items-center ${
                  cardCustomization.viewMode === 'detailed' ? 'text-sm' : 'text-xs'
                } text-gray-600 dark:text-gray-400`}>
                  <span className="font-medium mr-2 min-w-0 flex-shrink-0">
                    {cardCustomization.viewMode === 'detailed' ? (field.display_name || field.name) : (field.display_name || field.name).substring(0, 8)}:
                  </span>
                  <span className="truncate">
                    {React.isValidElement(formattedValue) ? formattedValue : String(formattedValue)}
                  </span>
                </div>
              )
            }).filter(Boolean)}
          </div>
        )}

        {/* Card Footer */}
        {(cardCustomization.showAvatar || cardCustomization.showDates) && cardCustomization.viewMode !== 'minimal' && (
          <div className="flex items-center justify-between mt-3 pt-2 border-t border-gray-100 dark:border-gray-700">
            {cardCustomization.showAvatar && record.created_by && (
              <div className="flex items-center text-xs text-gray-500">
                <User className="w-3 h-3 mr-1" />
                <span className={cardCustomization.viewMode === 'detailed' ? '' : 'truncate max-w-[80px]'}>
                  {cardCustomization.viewMode === 'detailed' 
                    ? `${record.created_by.first_name} ${record.created_by.last_name}`
                    : record.created_by.first_name
                  }
                </span>
              </div>
            )}
            
            {cardCustomization.showDates && (
              <div className="flex items-center text-xs text-gray-500">
                <Calendar className="w-3 h-3 mr-1" />
                <span>
                  {cardCustomization.viewMode === 'detailed'
                    ? new Date(record.updated_at).toLocaleDateString()
                    : new Date(record.updated_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                  }
                </span>
              </div>
            )}
          </div>
        )}
      </motion.div>
    )
  }, [titleField, displayFields, draggedRecord, dragOverColumn, isDragging, handleDragStart, handleDrag, handleDragEnd, onEditRecord, cardCustomization])

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
      {/* Controls Bar */}
      <div className="px-6 py-3 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-6">
            {/* Column Size Selector */}
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Column Size:
              </label>
              <select
                value={columnSize}
                onChange={(e) => setColumnSize(e.target.value as ColumnSize)}
                className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
              >
                <option value="compact">Compact</option>
                <option value="standard">Standard</option>
                <option value="wide">Wide</option>
                <option value="extra-wide">Extra Wide</option>
              </select>
            </div>
            
            {/* Card View Mode */}
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Card View:
              </label>
              <select
                value={cardCustomization.viewMode}
                onChange={(e) => setCardCustomization(prev => ({ ...prev, viewMode: e.target.value as CardViewMode }))}
                className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
              >
                <option value="minimal">Minimal</option>
                <option value="standard">Standard</option>
                <option value="detailed">Detailed</option>
              </select>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowCustomization(!showCustomization)}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Customize Cards
            </button>
            
            <p className="text-xs text-gray-600 dark:text-gray-400">
              💡 <strong>Drag</strong> cards between columns • <strong>Double-click</strong> to edit
            </p>
          </div>
        </div>
        
        {/* Card Customization Panel */}
        {showCustomization && (
          <div className="mt-4 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">Card Content Customization</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Field Selection */}
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">
                  Display Fields (max {cardCustomization.viewMode === 'minimal' ? 2 : cardCustomization.viewMode === 'standard' ? 3 : 5}):
                </label>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {availableFields.map(field => (
                    <label key={field.name} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={cardCustomization.selectedFields.includes(field.name)}
                        onChange={(e) => {
                          const maxFields = cardCustomization.viewMode === 'minimal' ? 2 : cardCustomization.viewMode === 'standard' ? 3 : 5
                          if (e.target.checked && cardCustomization.selectedFields.length < maxFields) {
                            setCardCustomization(prev => ({
                              ...prev,
                              selectedFields: [...prev.selectedFields, field.name]
                            }))
                          } else if (!e.target.checked) {
                            setCardCustomization(prev => ({
                              ...prev,
                              selectedFields: prev.selectedFields.filter(f => f !== field.name)
                            }))
                          }
                        }}
                        className="rounded"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        {field.display_name || field.name}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
              
              {/* Display Options */}
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">
                  Display Options:
                </label>
                <div className="space-y-2">
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={cardCustomization.showAvatar}
                      onChange={(e) => setCardCustomization(prev => ({ ...prev, showAvatar: e.target.checked }))}
                      className="rounded"
                    />
                    <span className="text-sm text-gray-700 dark:text-gray-300">Show Avatar</span>
                  </label>
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={cardCustomization.showDates}
                      onChange={(e) => setCardCustomization(prev => ({ ...prev, showDates: e.target.checked }))}
                      className="rounded"
                    />
                    <span className="text-sm text-gray-700 dark:text-gray-300">Show Dates</span>
                  </label>
                </div>
              </div>
              
              {/* Quick Actions */}
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">
                  Quick Actions:
                </label>
                <div className="space-y-1">
                  <button
                    onClick={() => setCardCustomization(prev => ({ ...prev, selectedFields: availableFields.slice(0, 3).map(f => f.name) }))}
                    className="text-sm text-blue-600 hover:text-blue-800 block"
                  >
                    Reset to Default
                  </button>
                  <button
                    onClick={() => setCardCustomization(prev => ({ ...prev, selectedFields: [] }))}
                    className="text-sm text-red-600 hover:text-red-800 block"
                  >
                    Clear All Fields
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Kanban Board */}
      <div className="flex-1 overflow-x-auto">
        <div ref={kanbanBoardRef} className={`flex ${screenSize === 'mobile' ? 'space-x-4 p-4' : 'space-x-6 p-6'} min-w-max`}>
          {columns.map(column => (
            <div
              key={column.id}
              className={`flex-shrink-0 ${getColumnWidth(columnSize, screenSize)}`}
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
                className={`min-h-96 border-l border-r border-b rounded-b-lg p-4 ${
                  column.color
                } ${
                  dragOverColumn === column.id 
                    ? 'border-blue-400 bg-blue-100 dark:bg-blue-900/40' 
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
                  <AnimatePresence mode="wait">
                    {column.records.map((record, index) => (
                      <motion.div 
                        key={record.id} 
                        layout={false}
                        initial={false}
                        animate={false}
                        exit={false as any}
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

// Export memoized component to prevent unnecessary re-renders
export const KanbanView = memo(KanbanViewComponent, (prevProps, nextProps) => {
  // Custom comparison for optimal re-rendering
  return (
    prevProps.pipeline.id === nextProps.pipeline.id &&
    prevProps.kanbanField === nextProps.kanbanField &&
    prevProps.records.length === nextProps.records.length &&
    prevProps.records === nextProps.records // Reference equality check
  )
})