'use client'

import { useRouter, usePathname } from 'next/navigation'
import { 
  BarChart3,
  Settings,
  Database,
  FileText,
  Copy,
  TrendingUp,
  FileDown,
  FileUp,
  History,
  CheckCircle
} from 'lucide-react'

interface Pipeline {
  id: number
  name: string
  pipeline_type: string
  record_count?: number
  field_count?: number
}

interface ConfigSectionsSidebarProps {
  pipeline: Pipeline
  activeSection: string
}

interface ConfigSection {
  id: string
  label: string
  icon: React.ReactNode
  path: string
  description?: string
  implemented?: boolean
}

export function ConfigSectionsSidebar({ pipeline, activeSection }: ConfigSectionsSidebarProps) {
  const router = useRouter()
  const pathname = usePathname()

  const sections: ConfigSection[] = [
    {
      id: 'overview',
      label: 'Overview',
      icon: <BarChart3 className="w-4 h-4" />,
      path: `/pipelines/${pipeline.id}`,
      description: 'Pipeline statistics and quick actions',
      implemented: true
    },
    {
      id: 'settings',
      label: 'General Settings',
      icon: <Settings className="w-4 h-4" />,
      path: `/pipelines/${pipeline.id}/settings`,
      description: 'Basic configuration and display options',
      implemented: true
    },
    {
      id: 'fields',
      label: 'Field Configuration',
      icon: <Database className="w-4 h-4" />,
      path: `/pipelines/${pipeline.id}/fields`,
      description: 'Manage pipeline fields and data structure',
      implemented: true
    },
    {
      id: 'business-rules',
      label: 'Business Rules',
      icon: <FileText className="w-4 h-4" />,
      path: `/pipelines/${pipeline.id}/business-rules`,
      description: 'Configure validation and automation rules',
      implemented: true
    },
    {
      id: 'duplicates',
      label: 'Duplicate Management',
      icon: <Copy className="w-4 h-4" />,
      path: `/pipelines/${pipeline.id}/duplicates`,
      description: 'Set up duplicate detection and merging',
      implemented: true
    },
    {
      id: 'analytics',
      label: 'Analytics',
      icon: <TrendingUp className="w-4 h-4" />,
      path: `/pipelines/${pipeline.id}/analytics`,
      description: 'View pipeline performance and metrics',
      implemented: true
    },
    {
      id: 'import-export',
      label: 'Import/Export',
      icon: <FileDown className="w-4 h-4" />,
      path: `/pipelines/${pipeline.id}/import-export`,
      description: 'Import data or export configuration',
      implemented: true
    },
    {
      id: 'activity',
      label: 'Activity Log',
      icon: <History className="w-4 h-4" />,
      path: `/pipelines/${pipeline.id}/activity`,
      description: 'View pipeline change history',
      implemented: true
    }
  ]

  const handleSectionClick = (section: ConfigSection) => {
    router.push(section.path)
  }

  const isActive = (section: ConfigSection) => {
    // Check if current path matches the section path
    if (section.id === 'overview') {
      return pathname === `/pipelines/${pipeline.id}`
    }
    return pathname === section.path
  }

  return (
    <div className="w-56 bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700">
      {/* Pipeline Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="font-semibold text-gray-900 dark:text-white truncate">
          {pipeline.name}
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 capitalize">
          {pipeline.pipeline_type || 'Custom'} Pipeline
        </p>
        {(pipeline.field_count !== undefined || pipeline.record_count !== undefined) && (
          <div className="flex gap-3 mt-2 text-xs text-gray-500 dark:text-gray-400">
            {pipeline.field_count !== undefined && (
              <span>{pipeline.field_count} fields</span>
            )}
            {pipeline.record_count !== undefined && (
              <span>{pipeline.record_count} records</span>
            )}
          </div>
        )}
      </div>

      {/* Configuration Sections */}
      <nav className="p-2">
        <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider px-3 py-2">
          Configuration
        </div>
        
        {sections.map(section => (
          <button
            key={section.id}
            onClick={() => handleSectionClick(section)}
            className={`w-full text-left px-3 py-2 rounded-md mb-1 transition-colors group relative ${
              isActive(section)
                ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400'
                : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
            }`}
            title={section.description}
          >
            <div className="flex items-center">
              <span className={`mr-3 ${
                isActive(section) ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400'
              }`}>
                {section.icon}
              </span>
              <span className="text-sm font-medium flex-1">
                {section.label}
              </span>
              {section.implemented && section.id !== 'overview' && section.id !== 'settings' && (
                <CheckCircle className="w-3 h-3 text-green-500 opacity-0 group-hover:opacity-100 transition-opacity" />
              )}
            </div>
            
            {/* Active indicator */}
            {isActive(section) && (
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-blue-600 dark:bg-blue-400 rounded-r"></div>
            )}
          </button>
        ))}
      </nav>

      {/* Quick Stats */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700 mt-auto">
        <div className="text-xs text-gray-500 dark:text-gray-400">
          <div className="flex justify-between mb-1">
            <span>Status</span>
            <span className="font-medium text-green-600 dark:text-green-400">Active</span>
          </div>
          <div className="flex justify-between">
            <span>Last Modified</span>
            <span className="font-medium text-gray-700 dark:text-gray-300">2h ago</span>
          </div>
        </div>
      </div>
    </div>
  )
}