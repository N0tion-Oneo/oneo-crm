'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { pipelinesApi } from '@/lib/api'
import { 
  AlertCircle, 
  Check, 
  Info,
  Database,
  Archive,
  Eye,
  EyeOff,
  Palette,
  Type
} from 'lucide-react'

export default function PipelineSettingsPage() {
  const params = useParams()
  const router = useRouter()
  const pipelineId = params.id as string
  const [pipeline, setPipeline] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    pipeline_type: '',
    icon: '',
    color: '',
    is_active: true
  })

  useEffect(() => {
    const loadPipeline = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await pipelinesApi.get(pipelineId)
        setPipeline(response.data)
        // Convert text icon to emoji if needed
        const iconValue = response.data.icon || 'database'
        const displayIcon = getDisplayIcon(iconValue)
        
        setFormData({
          name: response.data.name || '',
          description: response.data.description || '',
          pipeline_type: response.data.pipeline_type || 'custom',
          icon: displayIcon,
          color: response.data.color || '#3B82F6',
          is_active: response.data.is_active !== false
        })
      } catch (error: any) {
        console.error('Failed to load pipeline:', error)
        setError('Failed to load pipeline settings')
      } finally {
        setLoading(false)
      }
    }

    if (pipelineId) {
      loadPipeline()
    }
  }, [pipelineId])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await pipelinesApi.update(pipelineId, formData)
      setShowSuccess(true)
      setTimeout(() => setShowSuccess(false), 3000)
      
      // Update the pipeline data
      setPipeline({ ...pipeline, ...formData })
    } catch (error: any) {
      console.error('Failed to update pipeline:', error)
      setError(error?.response?.data?.error || 'Failed to update pipeline settings')
    } finally {
      setSaving(false)
    }
  }

  // Map old text identifiers to emojis
  const iconMap: Record<string, string> = {
    'database': '📊',
    'folder': '📁',
    'chart': '📈',
    'users': '👥',
    'settings': '⚙️',
    'star': '⭐'
  }

  const iconCategories = {
    'Popular': ['📊', '🎯', '💼', '📈', '🚀', '⭐', '🔥', '💡', '🏆', '📋'],
    'Business': ['💰', '🏢', '🏭', '🏪', '🏦', '💳', '📱', '🤝', '📞', '💸'],
    'People': ['👤', '👥', '👨‍💼', '👩‍💼', '🧑‍🤝‍🧑', '👨‍👩‍👦', '🫂', '💬', '🗣️', '👨‍💻'],
    'Tasks': ['✅', '📝', '✏️', '📌', '🔔', '⏰', '📅', '🗓️', '⏳', '✔️'],
    'Analytics': ['📉', '💹', '🎲', '🔢', '📐', '🧮', '📏', '📊', '📈', '💯'],
    'Creative': ['🎨', '✨', '💎', '🌟', '🎭', '🎪', '🎬', '📸', '🖼️', '🎵']
  }
  const [selectedIconCategory, setSelectedIconCategory] = useState('Popular')
  
  // Helper to get display icon (handles both emoji and text identifiers)
  const getDisplayIcon = (icon: string) => {
    // If it's already an emoji (has emoji character), return it
    if (icon && icon.match(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]/u)) {
      return icon
    }
    // Otherwise try to map it
    return iconMap[icon] || '📊'
  }
  
  const commonColors = [
    '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
    '#EC4899', '#14B8A6', '#F97316', '#06B6D4', '#6366F1'
  ]

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-300 dark:bg-gray-600 rounded w-1/3 mb-4"></div>
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-10 bg-gray-300 dark:bg-gray-600 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!pipeline) {
    return (
      <div className="p-8">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Pipeline not found
          </h2>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      <div className="max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            General Settings
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Configure basic pipeline settings and appearance
          </p>
        </div>

        {/* Success/Error Messages */}
        {showSuccess && (
          <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-center">
            <Check className="w-5 h-5 text-green-600 dark:text-green-400 mr-2" />
            <span className="text-green-700 dark:text-green-300">Settings saved successfully!</span>
          </div>
        )}

        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 mr-2" />
            <span className="text-red-700 dark:text-red-300">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Information */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
                <Type className="w-5 h-5 mr-2 text-gray-400" />
                Basic Information
              </h2>
            </div>
            
            <div className="p-6 space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Pipeline Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Describe the purpose of this pipeline..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Pipeline Type
                </label>
                <select
                  value={formData.pipeline_type}
                  onChange={(e) => setFormData({ ...formData, pipeline_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="custom">Custom</option>
                  <option value="crm">CRM</option>
                  <option value="ats">ATS (Applicant Tracking)</option>
                  <option value="cms">CMS (Content Management)</option>
                  <option value="contacts">Contacts</option>
                  <option value="companies">Companies</option>
                  <option value="deals">Deals</option>
                  <option value="support">Support Tickets</option>
                  <option value="projects">Projects</option>
                </select>
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label htmlFor="is_active" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                  Pipeline is active and can receive new records
                </label>
              </div>
            </div>
          </div>

          {/* Appearance */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
                <Palette className="w-5 h-5 mr-2 text-gray-400" />
                Appearance
              </h2>
            </div>
            
            <div className="p-6">
              <div className="grid grid-cols-2 gap-6">
                {/* Icon Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                    Icon
                  </label>
                  
                  {/* Icon Category Tabs */}
                  <div className="flex flex-wrap gap-1 mb-3">
                    {Object.keys(iconCategories).map(category => (
                      <button
                        key={category}
                        type="button"
                        onClick={() => setSelectedIconCategory(category)}
                        className={`px-2 py-1 text-xs rounded-md transition-all ${
                          selectedIconCategory === category
                            ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium'
                            : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                        }`}
                      >
                        {category}
                      </button>
                    ))}
                  </div>
                  
                  {/* Icon Grid */}
                  <div className="grid grid-cols-5 gap-1">
                    {iconCategories[selectedIconCategory as keyof typeof iconCategories].map((icon, index) => (
                      <button
                        key={`${selectedIconCategory}-${index}`}
                        type="button"
                        onClick={() => setFormData({ ...formData, icon })}
                        className={`p-2 text-2xl rounded-md transition-all ${
                          formData.icon === icon 
                            ? 'bg-blue-100 dark:bg-blue-900/30 ring-2 ring-blue-500' 
                            : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                        }`}
                      >
                        {icon}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Color Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                    Color Theme
                  </label>
                  <div className="grid grid-cols-5 gap-2">
                    {commonColors.map(color => (
                      <button
                        key={color}
                        type="button"
                        onClick={() => setFormData({ ...formData, color })}
                        className={`h-10 rounded-md transition-all ${
                          formData.color === color 
                            ? 'ring-2 ring-offset-2 ring-blue-500 dark:ring-offset-gray-800' 
                            : 'hover:scale-110'
                        }`}
                        style={{ backgroundColor: color }}
                      />
                    ))}
                  </div>
                  <div className="flex items-center gap-2 mt-3">
                    <input
                      type="color"
                      value={formData.color}
                      onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                      className="h-10 w-10 border border-gray-300 dark:border-gray-600 rounded-md cursor-pointer"
                    />
                    <input
                      type="text"
                      value={formData.color}
                      onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                      className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="#3B82F6"
                      pattern="^#[0-9A-Fa-f]{6}$"
                    />
                  </div>
                </div>
              </div>

              {/* Preview */}
              <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">Preview</div>
                <div className="flex items-center gap-3">
                  <div 
                    className="w-10 h-10 rounded-lg flex items-center justify-center text-2xl"
                    style={{ backgroundColor: formData.color + '20' }}
                  >
                    <span>{formData.icon || '📊'}</span>
                  </div>
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">{formData.name || 'Pipeline Name'}</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">{formData.pipeline_type || 'custom'} pipeline</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              <Info className="inline w-4 h-4 mr-1" />
              Changes will take effect immediately
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => router.push(`/pipelines/${pipelineId}`)}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}