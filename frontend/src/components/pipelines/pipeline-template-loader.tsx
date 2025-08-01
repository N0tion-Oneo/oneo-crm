'use client'

import { useState, useEffect } from 'react'
import { 
  Search, 
  Star, 
  Copy, 
  Eye, 
  Users, 
  Database, 
  Briefcase, 
  FileText, 
  Package, 
  Headphones,
  Settings
} from 'lucide-react'
import { pipelinesApi } from '@/lib/api'

// Template categories with icons
const TEMPLATE_CATEGORIES = {
  crm: { 
    icon: Users, 
    label: 'Customer Relationship Management',
    description: 'Manage customers, leads, and sales pipelines'
  },
  ats: { 
    icon: Briefcase, 
    label: 'Applicant Tracking System',
    description: 'Track job applications and hiring process'
  },
  cms: { 
    icon: FileText, 
    label: 'Content Management System',
    description: 'Manage content, articles, and publications'
  },
  project: { 
    icon: Database, 
    label: 'Project Management',
    description: 'Track projects, tasks, and deliverables'
  },
  inventory: { 
    icon: Package, 
    label: 'Inventory Management',
    description: 'Manage products, stock, and suppliers'
  },
  support: { 
    icon: Headphones, 
    label: 'Support Ticketing',
    description: 'Handle customer support and tickets'
  },
  custom: { 
    icon: Settings, 
    label: 'Custom Template',
    description: 'Build your own custom pipeline'
  }
}

export interface PipelineTemplate {
  id: string
  name: string
  slug: string
  description: string
  category: keyof typeof TEMPLATE_CATEGORIES
  is_system: boolean
  is_public: boolean
  usage_count: number
  preview_config: Record<string, any>
  sample_data: Record<string, any>
  template_data: {
    pipeline: Record<string, any>
    fields: Array<Record<string, any>>
  }
  created_by?: {
    first_name: string
    last_name: string
  }
  created_at: string
}

export interface PipelineTemplateLoaderProps {
  onSelectTemplate: (template: PipelineTemplate) => void
  onCancel: () => void
}

export function PipelineTemplateLoader({ onSelectTemplate, onCancel }: PipelineTemplateLoaderProps) {
  const [templates, setTemplates] = useState<PipelineTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [previewTemplate, setPreviewTemplate] = useState<PipelineTemplate | null>(null)

  // Load templates
  useEffect(() => {
    const loadTemplates = async () => {
      try {
        setLoading(true)
        
        // Try to load from API first
        try {
          const response = await pipelinesApi.getTemplates()
          const apiTemplates = response.data.results || response.data || []
          if (apiTemplates.length > 0) {
            setTemplates(apiTemplates)
            setLoading(false)
            return
          }
        } catch (error) {
          console.log('API templates not available, using mock data:', error)
        }
        
        // Fallback to mock templates
        const mockTemplates: PipelineTemplate[] = [
          {
            id: '1',
            name: 'Sales CRM',
            slug: 'sales-crm',
            description: 'Complete sales pipeline with lead tracking, opportunity management, and customer relationships',
            category: 'crm',
            is_system: true,
            is_public: true,
            usage_count: 1250,
            preview_config: {},
            sample_data: {},
            template_data: {
              pipeline: { name: 'Sales Pipeline', description: 'Track sales opportunities' },
              fields: [
                { name: 'company_name', label: 'Company Name', field_type: 'text', required: true },
                { name: 'contact_email', label: 'Contact Email', field_type: 'email', required: true },
                { name: 'deal_size', label: 'Deal Size', field_type: 'decimal', required: false },
                { name: 'stage', label: 'Sales Stage', field_type: 'select', required: true }
              ]
            },
            created_at: '2024-01-15T10:00:00Z'
          },
          {
            id: '2',
            name: 'Job Applications',
            slug: 'job-applications',
            description: 'Track job candidates through the hiring process with interview scheduling and feedback management',
            category: 'ats',
            is_system: true,
            is_public: true,
            usage_count: 890,
            preview_config: {},
            sample_data: {},
            template_data: {
              pipeline: { name: 'Hiring Pipeline', description: 'Track job applications' },
              fields: [
                { name: 'candidate_name', label: 'Candidate Name', field_type: 'text', required: true },
                { name: 'resume', label: 'Resume', field_type: 'file', required: true },
                { name: 'interview_date', label: 'Interview Date', field_type: 'datetime', required: false }
              ]
            },
            created_at: '2024-01-10T14:30:00Z'
          },
          {
            id: '3',
            name: 'Content Calendar',
            slug: 'content-calendar',
            description: 'Manage content creation, review process, and publication scheduling',
            category: 'cms',
            is_system: true,
            is_public: true,
            usage_count: 567,
            preview_config: {},
            sample_data: {},
            template_data: {
              pipeline: { name: 'Content Pipeline', description: 'Manage content creation' },
              fields: [
                { name: 'title', label: 'Title', field_type: 'text', required: true },
                { name: 'content_type', label: 'Content Type', field_type: 'select', required: true },
                { name: 'publish_date', label: 'Publish Date', field_type: 'date', required: false }
              ]
            },
            created_at: '2024-01-20T09:15:00Z'
          }
        ]
        
        setTemplates(mockTemplates)
      } catch (error) {
        console.error('Failed to load templates:', error)
      } finally {
        setLoading(false)
      }
    }

    loadTemplates()
  }, [])

  // Filter templates
  const filteredTemplates = templates.filter(template => {
    const matchesSearch = searchQuery === '' || 
      template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.description.toLowerCase().includes(searchQuery.toLowerCase())
    
    const matchesCategory = selectedCategory === 'all' || template.category === selectedCategory
    
    return matchesSearch && matchesCategory
  })

  // Get category counts
  const categoryCounts = templates.reduce((acc, template) => {
    acc[template.category] = (acc[template.category] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const formatUsageCount = (count: number) => {
    if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}k`
    }
    return count.toString()
  }

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white dark:bg-gray-800 rounded-lg max-w-6xl w-full m-4 h-[80vh]">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <div className="h-6 bg-gray-300 dark:bg-gray-600 rounded w-1/3 mb-2"></div>
            <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-1/2"></div>
          </div>
          <div className="p-6">
            <div className="animate-pulse">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="h-32 bg-gray-300 dark:bg-gray-600 rounded-lg"></div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg max-w-6xl w-full m-4 h-[80vh] flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
            Choose Pipeline Template
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Start with a pre-built template or create your own from scratch
          </p>
        </div>

        <div className="flex-1 flex">
          {/* Sidebar - Categories */}
          <div className="w-64 border-r border-gray-200 dark:border-gray-700 p-6">
            <div className="mb-4">
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search className="h-4 w-4 text-gray-400" />
                </div>
                <input
                  type="text"
                  placeholder="Search templates..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500"
                />
              </div>
            </div>

            <div className="space-y-1">
              <button
                onClick={() => setSelectedCategory('all')}
                className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                  selectedCategory === 'all'
                    ? 'bg-primary text-white'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                All Templates ({templates.length})
              </button>
              
              {Object.entries(TEMPLATE_CATEGORIES).map(([key, config]) => (
                <button
                  key={key}
                  onClick={() => setSelectedCategory(key)}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors flex items-center justify-between ${
                    selectedCategory === key
                      ? 'bg-primary text-white'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  <span>{config.label}</span>
                  <span className="text-xs opacity-75">
                    {categoryCounts[key] || 0}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1 p-6 overflow-y-auto">
            {filteredTemplates.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredTemplates.map((template) => {
                  const categoryConfig = TEMPLATE_CATEGORIES[template.category]
                  const Icon = categoryConfig.icon

                  return (
                    <div
                      key={template.id}
                      className="bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg p-4 hover:shadow-lg transition-shadow"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center space-x-2">
                          <Icon className="w-5 h-5 text-primary" />
                          {template.is_system && (
                            <Star className="w-4 h-4 text-yellow-500" />
                          )}
                        </div>
                        <div className="flex items-center space-x-1">
                          <button
                            onClick={() => setPreviewTemplate(template)}
                            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                        {template.name}
                      </h4>
                      
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
                        {template.description}
                      </p>

                      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-4">
                        <span className="bg-gray-100 dark:bg-gray-600 px-2 py-1 rounded">
                          {categoryConfig.label}
                        </span>
                        <span>{formatUsageCount(template.usage_count)} uses</span>
                      </div>

                      <button
                        onClick={() => onSelectTemplate(template)}
                        className="w-full bg-primary text-white py-2 px-4 rounded-md hover:bg-primary/90 transition-colors text-sm font-medium"
                      >
                        Use This Template
                      </button>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-center py-12">
                <Database className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  No templates found
                </h3>
                <p className="text-gray-500 dark:text-gray-400">
                  Try adjusting your search or category filter
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-between">
          <button
            onClick={() => onSelectTemplate({
              id: 'blank',
              name: 'Blank Pipeline',
              slug: 'blank',
              description: 'Start with an empty pipeline',
              category: 'custom',
              is_system: false,
              is_public: false,
              usage_count: 0,
              preview_config: {},
              sample_data: {},
              template_data: {
                pipeline: { name: 'New Pipeline', description: '' },
                fields: []
              },
              created_at: new Date().toISOString()
            })}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Start Blank
          </button>
          
          <button
            onClick={onCancel}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Cancel
          </button>
        </div>
      </div>

      {/* Template Preview Modal */}
      {previewTemplate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-60">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full m-4 max-h-[80vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Template Preview: {previewTemplate.name}
              </h3>
            </div>
            
            <div className="p-6">
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                {previewTemplate.description}
              </p>
              
              <h4 className="font-medium text-gray-900 dark:text-white mb-3">
                Included Fields:
              </h4>
              
              <div className="space-y-2">
                {previewTemplate.template_data.fields.map((field, index) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded">
                    <span className="font-medium text-gray-900 dark:text-white">
                      {field.label}
                    </span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {field.field_type}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end space-x-4">
              <button
                onClick={() => setPreviewTemplate(null)}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300"
              >
                Close
              </button>
              <button
                onClick={() => {
                  onSelectTemplate(previewTemplate)
                  setPreviewTemplate(null)
                }}
                className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
              >
                Use Template
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}