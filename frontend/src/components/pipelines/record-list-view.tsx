'use client'

import { useState, useEffect, useMemo } from 'react'
import { pipelinesApi } from '@/lib/api'
import { 
  Search, 
  Filter, 
  Plus, 
  MoreHorizontal, 
  ArrowUpDown, 
  ArrowUp, 
  ArrowDown,
  Eye,
  Edit,
  Trash2,
  Download,
  Upload,
  RefreshCw,
  CheckSquare,
  Square,
  X,
  Tag,
  Calendar,
  User,
  Hash,
  Type,
  Mail,
  Phone,
  Link,
  FileText,
  Image,
  Database,
  Users,
  Bot
} from 'lucide-react'

// Field type icons
const FIELD_ICONS = {
  text: Type,
  textarea: FileText,
  number: Hash,
  decimal: Hash,
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
  file: FileText,
  image: Image,
  relation: Link,
  user: Users,
  ai_field: Bot
}

export interface RecordField {
  id: string
  name: string
  label: string
  field_type: keyof typeof FIELD_ICONS
  required: boolean
  visible: boolean
  order: number
  config: { [key: string]: any }
}

export interface Record {
  id: string
  data: { [key: string]: any }
  stage?: string
  tags?: string[]
  created_at: string
  updated_at: string
  created_by?: {
    id: string
    first_name: string
    last_name: string
    email: string
  }
}

export interface Pipeline {
  id: string
  name: string
  description: string
  fields: RecordField[]
  stages?: string[]
  record_count: number
}

export interface RecordListViewProps {
  pipeline: Pipeline
  onEditRecord: (record: Record) => void
  onCreateRecord: () => void
  onEditPipeline: () => void
}

type SortDirection = 'asc' | 'desc' | null
type FilterOperator = 'equals' | 'contains' | 'starts_with' | 'ends_with' | 'greater_than' | 'less_than' | 'is_empty' | 'is_not_empty'

interface Filter {
  field: string
  operator: FilterOperator
  value: any
}

interface Sort {
  field: string
  direction: SortDirection
}

export function RecordListView({ pipeline, onEditRecord, onCreateRecord, onEditPipeline }: RecordListViewProps) {
  const [records, setRecords] = useState<Record[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedRecords, setSelectedRecords] = useState<Set<string>>(new Set())
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState<Filter[]>([])
  const [sort, setSort] = useState<Sort>({ field: 'updated_at', direction: 'desc' })
  const [visibleFields, setVisibleFields] = useState<Set<string>>(new Set())
  const [currentPage, setCurrentPage] = useState(1)
  const [recordsPerPage] = useState(50)

  // Initialize visible fields
  useEffect(() => {
    const defaultVisible = pipeline.fields
      .filter(field => field.visible)
      .map(field => field.name)
    setVisibleFields(new Set(defaultVisible))
  }, [pipeline.fields])

  // Load records
  useEffect(() => {
    const loadRecords = async () => {
      try {
        setLoading(true)
        
        // Build query parameters
        const params: any = {
          page: currentPage,
          page_size: recordsPerPage,
        }
        
        // Add search query
        if (searchQuery.trim()) {
          params.search = searchQuery.trim()
        }
        
        // Add filters
        if (filters.length > 0) {
          filters.forEach((filter, index) => {
            params[`filter_${index}_field`] = filter.field
            params[`filter_${index}_operator`] = filter.operator
            params[`filter_${index}_value`] = filter.value
          })
        }
        
        // Add sorting
        if (sort.field && sort.direction) {
          params.ordering = sort.direction === 'desc' ? `-${sort.field}` : sort.field
        }
        
        const response = await pipelinesApi.getRecords(pipeline.id, params)
        setRecords(response.data.results || response.data)
      } catch (error) {
        console.error('Failed to load records:', error)
        // Fall back to empty array on error
        setRecords([])
      } finally {
        setLoading(false)
      }
    }

    loadRecords()
  }, [pipeline.id, filters, sort, searchQuery, currentPage, recordsPerPage])

  // Filter and sort records
  const filteredAndSortedRecords = useMemo(() => {
    let filtered = records

    // Apply search
    if (searchQuery) {
      filtered = filtered.filter(record => 
        Object.values(record.data).some(value =>
          String(value).toLowerCase().includes(searchQuery.toLowerCase())
        )
      )
    }

    // Apply filters
    filtered = filtered.filter(record => {
      return filters.every(filter => {
        const value = record.data[filter.field]
        
        switch (filter.operator) {
          case 'equals':
            return value === filter.value
          case 'contains':
            return String(value).toLowerCase().includes(String(filter.value).toLowerCase())
          case 'starts_with':
            return String(value).toLowerCase().startsWith(String(filter.value).toLowerCase())
          case 'ends_with':
            return String(value).toLowerCase().endsWith(String(filter.value).toLowerCase())
          case 'greater_than':
            return Number(value) > Number(filter.value)
          case 'less_than':
            return Number(value) < Number(filter.value)
          case 'is_empty':
            return !value || value === ''
          case 'is_not_empty':
            return value && value !== ''
          default:
            return true
        }
      })
    })

    // Apply sorting
    if (sort.field && sort.direction) {
      filtered.sort((a, b) => {
        const aValue = a.data[sort.field] || ''
        const bValue = b.data[sort.field] || ''
        
        if (sort.direction === 'asc') {
          return aValue > bValue ? 1 : -1
        } else {
          return aValue < bValue ? 1 : -1
        }
      })
    }

    return filtered
  }, [records, searchQuery, filters, sort])

  // Pagination
  const totalPages = Math.ceil(filteredAndSortedRecords.length / recordsPerPage)
  const paginatedRecords = filteredAndSortedRecords.slice(
    (currentPage - 1) * recordsPerPage,
    currentPage * recordsPerPage
  )

  // Handle sort
  const handleSort = (fieldName: string) => {
    setSort(prev => ({
      field: fieldName,
      direction: prev.field === fieldName 
        ? prev.direction === 'asc' ? 'desc' : 'asc'
        : 'asc'
    }))
  }

  // Handle select all
  const handleSelectAll = () => {
    if (selectedRecords.size === paginatedRecords.length) {
      setSelectedRecords(new Set())
    } else {
      setSelectedRecords(new Set(paginatedRecords.map(r => r.id)))
    }
  }

  // Handle select record
  const handleSelectRecord = (recordId: string) => {
    const newSelected = new Set(selectedRecords)
    if (newSelected.has(recordId)) {
      newSelected.delete(recordId)
    } else {
      newSelected.add(recordId)
    }
    setSelectedRecords(newSelected)
  }

  // Format field value for display
  const formatFieldValue = (field: RecordField, value: any) => {
    if (value === null || value === undefined || value === '') {
      return <span className="text-gray-400 italic">Empty</span>
    }

    switch (field.field_type) {
      case 'date':
        return new Date(value).toLocaleDateString()
      case 'datetime':
        return new Date(value).toLocaleString()
      case 'decimal':
        return typeof value === 'number' ? value.toLocaleString() : value
      case 'number':
        return typeof value === 'number' ? value.toLocaleString() : value
      case 'boolean':
        return value ? '✓' : '✗'
      case 'email':
        return <a href={`mailto:${value}`} className="text-blue-600 hover:underline">{value}</a>
      case 'phone':
        return <a href={`tel:${value}`} className="text-blue-600 hover:underline">{value}</a>
      case 'url':
        return <a href={value} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{value}</a>
      default:
        return String(value).substring(0, 100) + (String(value).length > 100 ? '...' : '')
    }
  }

  // Get visible fields for table
  const visibleFieldsList = pipeline.fields
    .filter(field => visibleFields.has(field.name))
    .sort((a, b) => a.order - b.order)

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading records...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {pipeline.name}
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              {pipeline.description}
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={onEditPipeline}
              className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <Edit className="w-4 h-4 mr-1 inline" />
              Edit Pipeline
            </button>
            <button
              onClick={onCreateRecord}
              className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
            >
              <Plus className="w-4 h-4 mr-2 inline" />
              Add Record
            </button>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search records..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white w-80"
              />
            </div>
            
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`px-3 py-2 border rounded-md flex items-center ${
                showFilters 
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              <Filter className="w-4 h-4 mr-2" />
              Filters {filters.length > 0 && `(${filters.length})`}
            </button>
          </div>

          <div className="flex items-center space-x-2">
            {selectedRecords.size > 0 && (
              <div className="flex items-center space-x-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 rounded-md">
                <span className="text-sm text-blue-700 dark:text-blue-300">
                  {selectedRecords.size} selected
                </span>
                <button className="text-blue-600 hover:text-blue-800 dark:hover:text-blue-400">
                  <Trash2 className="w-4 h-4" />
                </button>
                <button className="text-blue-600 hover:text-blue-800 dark:hover:text-blue-400">
                  <Download className="w-4 h-4" />
                </button>
              </div>
            )}
            
            <button className="p-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700">
              <Download className="w-4 h-4" />
            </button>
            <button className="p-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700">
              <Upload className="w-4 h-4" />
            </button>
            <button 
              onClick={() => window.location.reload()}
              className="p-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="p-4 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white">Filters</h3>
            <button
              onClick={() => setFilters([])}
              className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            >
              Clear all
            </button>
          </div>
          
          {/* Filter rows would go here */}
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Filter functionality coming soon...
          </p>
        </div>
      )}

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0 z-10">
            <tr>
              <th className="w-12 px-4 py-3">
                <button
                  onClick={handleSelectAll}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {selectedRecords.size === paginatedRecords.length && paginatedRecords.length > 0 ? (
                    <CheckSquare className="w-4 h-4" />
                  ) : (
                    <Square className="w-4 h-4" />
                  )}
                </button>
              </th>
              
              {visibleFieldsList.map((field) => {
                const Icon = FIELD_ICONS[field.field_type] || Type
                const isSorted = sort.field === field.name
                
                return (
                  <th
                    key={field.name}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                  >
                    <button
                      onClick={() => handleSort(field.name)}
                      className="flex items-center space-x-2 hover:text-gray-700 dark:hover:text-gray-200"
                    >
                      <Icon className="w-4 h-4" />
                      <span>{field.label}</span>
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
              
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          
          <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
            {paginatedRecords.map((record) => (
              <tr
                key={record.id}
                className="hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
                onClick={() => onEditRecord(record)}
              >
                <td className="px-4 py-3">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleSelectRecord(record.id)
                    }}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    {selectedRecords.has(record.id) ? (
                      <CheckSquare className="w-4 h-4 text-primary" />
                    ) : (
                      <Square className="w-4 h-4" />
                    )}
                  </button>
                </td>
                
                {visibleFieldsList.map((field) => (
                  <td key={field.name} className="px-4 py-3 text-sm text-gray-900 dark:text-white">
                    {formatFieldValue(field, record.data[field.name])}
                  </td>
                ))}
                
                <td className="px-4 py-3">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        onEditRecord(record)
                      }}
                      className="text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                      <MoreHorizontal className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {paginatedRecords.length === 0 && (
          <div className="text-center py-12">
            <Database className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No records found
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mb-6">
              {searchQuery || filters.length > 0
                ? 'Try adjusting your search or filters.'
                : 'Get started by adding your first record.'}
            </p>
            {!searchQuery && filters.length === 0 && (
              <button
                onClick={onCreateRecord}
                className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
              >
                <Plus className="w-4 h-4 mr-2 inline" />
                Add First Record
              </button>
            )}
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Showing {((currentPage - 1) * recordsPerPage) + 1} to {Math.min(currentPage * recordsPerPage, filteredAndSortedRecords.length)} of {filteredAndSortedRecords.length} records
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const page = i + 1
              return (
                <button
                  key={page}
                  onClick={() => setCurrentPage(page)}
                  className={`px-3 py-1 border rounded-md ${
                    currentPage === page
                      ? 'border-primary bg-primary text-white'
                      : 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  {page}
                </button>
              )
            })}
            
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}