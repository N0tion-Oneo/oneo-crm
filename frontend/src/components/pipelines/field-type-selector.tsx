'use client'

import React, { useState, useEffect } from 'react'
import { fieldTypesApi } from '@/lib/api'
import { 
  Type,
  Hash,
  Mail,
  Phone,
  Calendar,
  CheckSquare,
  Link,
  FileText,
  Bot,
  Search,
  X
} from 'lucide-react'

interface FieldType {
  key: string
  label: string
  description: string
  icon: string
  category: string
}

interface FieldTypeSelectorProps {
  isOpen: boolean
  onClose: () => void
  onSelect: (fieldType: string, config: any) => void
  currentFieldType: string
  title?: string
}

const getFieldIcon = (fieldType: string) => {
  const iconMap: Record<string, any> = {
    text: Type,
    textarea: FileText,
    number: Hash,
    email: Mail,
    phone: Phone,
    date: Calendar,
    datetime: Calendar,
    boolean: CheckSquare,
    select: CheckSquare,
    multiselect: CheckSquare,
    url: Link,
    ai_generated: Bot,
    // Add more as needed
  }
  
  const IconComponent = iconMap[fieldType] || Type
  return <IconComponent className="w-5 h-5" />
}

export function FieldTypeSelector({
  isOpen,
  onClose,
  onSelect,
  currentFieldType,
  title = "Select New Field Type"
}: FieldTypeSelectorProps) {
  const [fieldTypes, setFieldTypes] = useState<FieldType[]>([])
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  useEffect(() => {
    if (isOpen) {
      loadFieldTypes()
    }
  }, [isOpen])

  const loadFieldTypes = async () => {
    setLoading(true)
    try {
      const response = await fieldTypesApi.getAll()
      const allTypes: FieldType[] = []
      
      // Flatten the categorized field types
      Object.entries(response.data).forEach(([category, types]: [string, any]) => {
        if (Array.isArray(types)) {
          types.forEach((type: any) => {
            allTypes.push({
              key: type.key,
              label: type.label,
              description: type.description,
              icon: type.icon,
              category: category
            })
          })
        }
      })
      
      setFieldTypes(allTypes)
    } catch (error) {
      console.error('Failed to load field types:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSelectFieldType = (fieldType: FieldType) => {
    // Create basic config for the selected field type
    let basicConfig = {}
    
    switch (fieldType.key) {
      case 'select':
        basicConfig = { allow_multiple: false, options: [] }
        break
      case 'multiselect':
        basicConfig = { allow_multiple: true, options: [] }
        break
      case 'ai_generated':
        basicConfig = { prompt: '', model: 'gpt-3.5-turbo', tools_enabled: false }
        break
      default:
        basicConfig = {}
    }

    onSelect(fieldType.key, basicConfig)
    onClose()
  }

  const filteredFieldTypes = fieldTypes.filter(type => {
    // Don't show current field type
    if (type.key === currentFieldType) return false
    
    // Search filter
    if (searchTerm && !type.label.toLowerCase().includes(searchTerm.toLowerCase()) && 
        !type.description.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false
    }
    
    // Category filter
    if (selectedCategory !== 'all' && type.category !== selectedCategory) {
      return false
    }
    
    return true
  })

  const categories = ['all', ...new Set(fieldTypes.map(type => type.category))]

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[80vh] overflow-hidden">
        <div className="flex justify-between items-center p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              {title}
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Current: {fieldTypes.find(t => t.key === currentFieldType)?.label || currentFieldType}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Filters */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Search */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search field types..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
            
            {/* Category filter */}
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              {categories.map(category => (
                <option key={category} value={category}>
                  {category === 'all' ? 'All Categories' : category.charAt(0).toUpperCase() + category.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Field Types Grid */}
        <div className="p-6 overflow-y-auto max-h-96">
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
              <p className="text-gray-600 dark:text-gray-400 mt-2">Loading field types...</p>
            </div>
          ) : filteredFieldTypes.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500 dark:text-gray-400">No field types found matching your criteria.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredFieldTypes.map(fieldType => (
                <button
                  key={fieldType.key}
                  onClick={() => handleSelectFieldType(fieldType)}
                  className="text-left p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  <div className="flex items-center mb-2">
                    {getFieldIcon(fieldType.key)}
                    <h3 className="font-medium text-gray-900 dark:text-white ml-2">
                      {fieldType.label}
                    </h3>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {fieldType.description}
                  </p>
                  <span className="inline-block mt-2 text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-600 px-2 py-1 rounded">
                    {fieldType.category}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}