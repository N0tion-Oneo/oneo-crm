'use client'

import { useState } from 'react'
import { 
  X, Database, Users, Building, Handshake, Package, HeadphonesIcon,
  Briefcase, Folder, FileText, Star, Heart, Tag, Settings, Zap, 
  Target, TrendingUp, Calendar, Clock
} from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  Button,
  Input,
  Textarea,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Card,
  CardContent
} from '@/components/ui'

// Pipeline type options with icons
const PIPELINE_TYPES = [
  { value: 'contacts', label: 'Contacts & People', icon: Users, description: 'Manage individuals and personal contacts' },
  { value: 'companies', label: 'Companies & Organizations', icon: Building, description: 'Track businesses and organizations' },
  { value: 'deals', label: 'Deals & Opportunities', icon: Handshake, description: 'Manage sales opportunities and deals' },
  { value: 'inventory', label: 'Inventory & Assets', icon: Package, description: 'Track items, products, and assets' },
  { value: 'support', label: 'Support & Tickets', icon: HeadphonesIcon, description: 'Handle support requests and tickets' },
  { value: 'custom', label: 'Custom', icon: Database, description: 'Create your own custom pipeline' },
]

// Icon options for pipelines
const ICON_OPTIONS = [
  { name: 'users', component: Users },
  { name: 'building', component: Building },
  { name: 'handshake', component: Handshake },
  { name: 'package', component: Package },
  { name: 'headphones', component: HeadphonesIcon },
  { name: 'database', component: Database },
  { name: 'briefcase', component: Briefcase },
  { name: 'folder', component: Folder },
  { name: 'file-text', component: FileText },
  { name: 'star', component: Star },
  { name: 'heart', component: Heart },
  { name: 'tag', component: Tag },
  { name: 'settings', component: Settings },
  { name: 'zap', component: Zap },
  { name: 'target', component: Target },
  { name: 'trending-up', component: TrendingUp },
  { name: 'calendar', component: Calendar },
  { name: 'clock', component: Clock },
]

// Color options for pipelines
const COLOR_OPTIONS = [
  // Primary blues
  '#3B82F6', // blue
  '#1E40AF', // blue-800
  '#0EA5E9', // sky
  '#0284C7', // sky-600
  
  // Greens
  '#10B981', // emerald
  '#059669', // emerald-600
  '#16A34A', // green
  '#15803D', // green-600
  '#84CC16', // lime
  '#65A30D', // lime-600
  
  // Reds and oranges
  '#EF4444', // red
  '#DC2626', // red-600
  '#F97316', // orange
  '#EA580C', // orange-600
  '#F59E0B', // amber
  '#D97706', // amber-600
  
  // Purples and pinks
  '#8B5CF6', // violet
  '#7C3AED', // violet-600
  '#A855F7', // purple
  '#9333EA', // purple-600
  '#EC4899', // pink
  '#DB2777', // pink-600
  '#F43F5E', // rose
  '#E11D48', // rose-600
  
  // Cyans and teals
  '#06B6D4', // cyan
  '#0891B2', // cyan-600
  '#14B8A6', // teal
  '#0D9488', // teal-600
  
  // Neutrals
  '#6B7280', // gray
  '#4B5563', // gray-600
  '#374151', // gray-700
  '#1F2937', // gray-800
]

export interface PipelineCreationData {
  name: string
  description: string
  pipeline_type: string
  custom_category?: string  // For when pipeline_type is 'custom'
  icon: string
  color: string
}

interface PipelineCreationWizardProps {
  onCreatePipeline: (data: PipelineCreationData) => void
  onCancel: () => void
  loading?: boolean
}

export function PipelineCreationWizard({ onCreatePipeline, onCancel, loading = false }: PipelineCreationWizardProps) {
  const [formData, setFormData] = useState<PipelineCreationData>({
    name: '',
    description: '',
    pipeline_type: 'contacts',
    custom_category: '',
    icon: 'users',
    color: '#3B82F6'
  })

  const [errors, setErrors] = useState<Record<string, string>>({})

  const validateForm = () => {
    const newErrors: Record<string, string> = {}
    
    if (!formData.name.trim()) {
      newErrors.name = 'Pipeline name is required'
    } else if (formData.name.trim().length < 2) {
      newErrors.name = 'Pipeline name must be at least 2 characters'
    }

    if (formData.pipeline_type === 'custom' && !formData.custom_category?.trim()) {
      newErrors.custom_category = 'Custom category name is required'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validateForm()) {
      const submitData: PipelineCreationData = {
        ...formData,
        name: formData.name.trim(),
        description: formData.description.trim()
      }
      
      // Only include custom_category if pipeline_type is custom
      if (formData.pipeline_type === 'custom' && formData.custom_category?.trim()) {
        submitData.custom_category = formData.custom_category.trim()
      }
      
      onCreatePipeline(submitData)
    }
  }

  const selectedType = PIPELINE_TYPES.find(type => type.value === formData.pipeline_type)

  return (
    <Dialog open={true} onOpenChange={() => !loading && onCancel()}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto overflow-x-hidden">
        <DialogHeader>
          <DialogTitle>Create New Pipeline</DialogTitle>
        </DialogHeader>

        <div className="max-w-full overflow-x-hidden">
          <form onSubmit={handleSubmit} className="space-y-6">
          {/* Pipeline Name */}
          <div className="space-y-2">
            <Label htmlFor="name">Pipeline Name *</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              placeholder="Enter pipeline name"
              disabled={loading}
              className={errors.name ? 'border-red-500' : ''}
            />
            {errors.name && (
              <p className="text-sm text-red-500">{errors.name}</p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              rows={3}
              placeholder="Describe what this pipeline will be used for..."
              disabled={loading}
            />
          </div>

          {/* Pipeline Type */}
          <div className="space-y-2">
            <Label htmlFor="pipeline_type">Pipeline Type *</Label>
            <Select
              value={formData.pipeline_type}
              onValueChange={(value) => setFormData(prev => ({ 
                ...prev, 
                pipeline_type: value,
                custom_category: value !== 'custom' ? '' : prev.custom_category
              }))}
              disabled={loading}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a pipeline type" />
              </SelectTrigger>
              <SelectContent>
                {PIPELINE_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedType && (
              <p className="text-sm text-gray-500">
                {selectedType.description}
              </p>
            )}
          </div>

          {/* Custom Category Name (only shown when Custom is selected) */}
          {formData.pipeline_type === 'custom' && (
            <div className="space-y-2">
              <Label htmlFor="custom_category">Custom Category Name *</Label>
              <Input
                id="custom_category"
                value={formData.custom_category || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, custom_category: e.target.value }))}
                placeholder="e.g., Projects, Events, Tasks..."
                disabled={loading}
                className={errors.custom_category ? 'border-red-500' : ''}
              />
              {errors.custom_category && (
                <p className="text-sm text-red-500">{errors.custom_category}</p>
              )}
            </div>
          )}

          {/* Icon Selection */}
          <div className="space-y-2">
            <Label>Icon</Label>
            <div className="relative">
              <div 
                className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100"
                style={{ maxWidth: '100%' }}
              >
                {ICON_OPTIONS.map((iconOption) => {
                  const IconComponent = iconOption.component
                  return (
                    <Button
                      key={iconOption.name}
                      type="button"
                      variant={formData.icon === iconOption.name ? "default" : "outline"}
                      size="sm"
                      onClick={() => setFormData(prev => ({ ...prev, icon: iconOption.name }))}
                      disabled={loading}
                      className="h-12 w-12 p-0 flex-shrink-0 min-w-12"
                    >
                      <IconComponent className="w-5 h-5" />
                    </Button>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Color Selection */}
          <div className="space-y-2">
            <Label>Color</Label>
            <div className="relative">
              <div 
                className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100"
                style={{ maxWidth: '100%' }}
              >
                {COLOR_OPTIONS.map((color) => (
                  <Button
                    key={color}
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setFormData(prev => ({ ...prev, color }))}
                    className={`h-12 w-12 p-0 border-2 transition-all flex-shrink-0 min-w-12 ${
                      formData.color === color
                        ? 'border-primary scale-110'
                        : 'hover:scale-105'
                    }`}
                    style={{ backgroundColor: color }}
                    disabled={loading}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Preview */}
          <Card>
            <CardContent className="p-4">
              <Label className="text-sm font-medium mb-2 block">Preview</Label>
              <div className="flex items-center space-x-3">
                <div 
                  className="w-10 h-10 rounded-lg flex items-center justify-center text-white"
                  style={{ backgroundColor: formData.color }}
                >
                  {(() => {
                    const selectedIcon = ICON_OPTIONS.find(icon => icon.name === formData.icon)
                    const IconComponent = selectedIcon?.component || Database
                    return <IconComponent className="w-5 h-5" />
                  })()}
                </div>
                <div>
                  <div className="font-medium">
                    {formData.name || 'Pipeline Name'}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {formData.pipeline_type === 'custom' && formData.custom_category?.trim() 
                      ? formData.custom_category 
                      : selectedType?.label
                    } • {formData.description || 'No description'}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex justify-end space-x-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={
                loading || 
                !formData.name.trim() || 
                (formData.pipeline_type === 'custom' && !formData.custom_category?.trim())
              }
            >
              {loading ? 'Creating...' : 'Create Pipeline'}
            </Button>
          </div>
          </form>
        </div>
      </DialogContent>
    </Dialog>
  )
}