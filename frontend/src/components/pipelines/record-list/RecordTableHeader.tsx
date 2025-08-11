// RecordTableHeader - Table header with sorting functionality
import React from 'react'
import { 
  ArrowUp, ArrowDown, CheckSquare, Square, Type, FileText, Hash, 
  Calendar, Mail, Phone, Link, Image, Users, Bot, Tag, Clock, User
} from 'lucide-react'
import { RecordField, Sort, Record } from '@/types/records'
import { FieldUtilsService } from '@/services/records'

const STATIC_FIELD_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  text: Type,
  textarea: FileText,
  number: Hash,
  decimal: Hash,
  integer: Hash,
  float: Hash,
  currency: Hash,
  percentage: Hash,
  boolean: CheckSquare,
  date: Calendar,
  datetime: Calendar,
  time: Calendar,
  select: CheckSquare,
  multiselect: CheckSquare,
  radio: CheckSquare,
  checkbox: CheckSquare,
  email: Mail,
  phone: Phone,
  url: Link,
  address: Hash,
  file: FileText,
  image: Image,
  relation: Link,
  user: Users,
  ai: Bot,
  ai_field: Bot,
  button: Bot,
  tags: Tag
}

export interface RecordTableHeaderProps {
  fields: RecordField[]
  sort: Sort
  onSort: (fieldName: string) => void
  selectedRecords: Set<string>
  records: Record[]
  onSelectAll: () => void
  className?: string
}

export function RecordTableHeader({
  fields,
  sort,
  onSort,
  selectedRecords,
  records,
  onSelectAll,
  className = ""
}: RecordTableHeaderProps) {
  const allSelected = records.length > 0 && selectedRecords.size === records.length

  return (
    <thead className={`bg-gray-50 dark:bg-gray-800 sticky top-0 z-10 ${className}`}>
      <tr>
        {/* Selection column */}
        <th className="w-12 px-4 py-3">
          <button
            onClick={onSelectAll}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            {allSelected ? (
              <CheckSquare className="w-4 h-4" />
            ) : (
              <Square className="w-4 h-4" />
            )}
          </button>
        </th>
        
        {/* Field columns */}
        {fields.map((field) => {
          const Icon = STATIC_FIELD_ICONS[field.field_type] || Type
          const isSorted = sort.field === field.name
          const columnWidth = FieldUtilsService.getColumnWidth(field)
          
          return (
            <th
              key={field.name}
              className={`${columnWidth} px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider`}
            >
              <button
                onClick={() => onSort(field.name)}
                className="flex items-center space-x-2 hover:text-gray-700 dark:hover:text-gray-200"
              >
                <Icon className="w-4 h-4" />
                <span className="truncate">{field.display_name || field.name}</span>
                {isSorted && (
                  sort.direction === 'asc' ? (
                    <ArrowUp className="w-3 h-3" />
                  ) : (
                    <ArrowDown className="w-3 h-3" />
                  )
                )}
              </button>
            </th>
          )
        })}
        
        {/* System metadata columns */}
        <th className="w-32 px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          <div className="flex items-center space-x-2">
            <Clock className="w-4 h-4" />
            <span>Created</span>
          </div>
        </th>
        
        <th className="w-32 px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          <div className="flex items-center space-x-2">
            <Clock className="w-4 h-4" />
            <span>Updated</span>
          </div>
        </th>
        
        <th className="w-32 px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          <div className="flex items-center space-x-2">
            <User className="w-4 h-4" />
            <span>Created By</span>
          </div>
        </th>
        
        {/* Actions column */}
        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          Actions
        </th>
      </tr>
    </thead>
  )
}