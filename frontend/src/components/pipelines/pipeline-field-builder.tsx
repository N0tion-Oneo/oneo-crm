'use client'

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { fieldTypesApi, permissionsApi, aiApi, pipelinesApi } from '@/lib/api'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragStartEvent,
  DragOverEvent,
  DragOverlay,
  Active,
  Over,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import {
  restrictToVerticalAxis,
  restrictToWindowEdges,
} from '@dnd-kit/modifiers'
import {
  useSortable,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { FieldConfigurationPanel } from './field-configuration-panel'
import { ConditionalRulesBuilder } from './conditional-rules-builder'
import { FieldManagementPanel } from './field-management-panel'
import { FieldStatusIndicator } from './field-status-indicator'
import { RelationshipFieldIndicator, hasEnhancedRelationshipFeatures } from './relationship-field-indicator'
import { 
  Plus, 
  Trash2, 
  Settings,
  Edit,
  Eye, 
  EyeOff,
  X,
  Type,
  Hash,
  Mail,
  Phone,
  Calendar,
  CheckSquare,
  Link,
  FileText,
  Bot,
  Sliders,
  Shield,
  Layout,
  Zap,
  Copy,
  FolderPlus,
  CheckCircle,
  AlertCircle,
  Info,
  AlignLeft,
  Calculator,
  Globe,
  ChevronDown,
  List,
  ToggleLeft,
  GitBranch,
  GripVertical,
  MapPin,
  MousePointer,
  Database,
  User,
  Tag,
  Check,
  Users,
  Building,
  Heart,
  Star,
  Home,
  Briefcase,
  Target,
  TrendingUp,
  DollarSign,
  CreditCard,
  ShoppingCart,
  Package,
  Truck,
  Clock,
  Bell,
  MessageCircle,
  Users2,
  UserCheck,
  Crown,
  Award,
  Trophy,
  Lightbulb,
  BookOpen,
  GraduationCap,
  PieChart,
  BarChart3,
  Activity,
  Wifi,
  Smartphone,
  Monitor,
  Camera,
  Video,
  Music,
  Image,
  Palette,
  Brush,
  Code,
  Terminal,
  Server,
  Cloud,
  Lock,
  Key,
  Fingerprint,
  Share2,
} from 'lucide-react'

// Field group interface
interface FieldGroup {
  id: string
  name: string
  description?: string
  color: string
  icon: string
  display_order: number
  field_count: number
  created_at: string
  created_by: any
  updated_at: string
  updated_by?: any
}

// Complete field interface matching new architecture
interface PipelineField {
  id: string
  name: string                    // Field name/slug
  display_name?: string           // Display name (optional)
  description?: string            // Field description
  field_type: string              // Field type
  help_text?: string              // User help text
  
  // Display configuration
  display_order: number
  is_visible_in_list: boolean
  is_visible_in_detail: boolean
  is_visible_in_public_forms?: boolean  // Dynamic forms: public visibility
  is_visible_in_shared_list_and_detail_views?: boolean  // Shared filtered views: external visibility
  
  // Behavior
  is_searchable: boolean
  create_index: boolean
  enforce_uniqueness: boolean
  is_ai_field: boolean
  
  // Configuration objects - NEW ARCHITECTURE
  field_config: Record<string, any>     // Type-specific config
  storage_constraints: Record<string, any>
  business_rules: Record<string, any>
  ai_config?: Record<string, any>       // For AI fields only
  form_validation_rules?: Record<string, any> // Form validation rules
  
  // Field group information
  field_group?: string | null     // Field group ID
  field_group_name?: string       // Field group name (read-only)
  
  // Field lifecycle management
  is_deleted?: boolean
  deleted_at?: string
  deleted_by?: string
  scheduled_for_hard_delete?: string
  hard_delete_reason?: string
  deletion_status?: {
    status: 'active' | 'soft_deleted' | 'scheduled_for_hard_delete'
    deleted_at?: string
    deleted_by?: string
    days_remaining?: number
    hard_delete_date?: string
    reason?: string
  }
  
  // Legacy support (remove these gradually)
  label?: string                  // Maps to display_name
  type?: string                   // Maps to field_type
  required?: boolean              // Moved to business_rules
  visible?: boolean               // Maps to is_visible_in_list
  order?: number                  // Maps to display_order
  config?: Record<string, any>    // Maps to field_config
}

interface FieldType {
  key: string
  label: string
  description: string
  icon: string
  category: string
}

interface Props {
  pipelineId?: string
  fields: PipelineField[]
  onFieldsChange: (fields: PipelineField[]) => void
  onSave?: () => void
}

const FIELD_ICONS: Record<string, any> = {
  text: AlignLeft,
  textarea: FileText,
  number: Hash,
  decimal: Calculator,
  currency: Calculator,
  percentage: Calculator,
  auto_increment: Hash,
  email: Mail,
  phone: Phone,
  date: Calendar,
  boolean: ToggleLeft,
  select: ChevronDown,
  multiselect: List,
  url: Globe,
  file: FileText,
  relation: GitBranch,
  ai_generated: Bot,
  ai_field: Bot,
  ai: Bot,
  tags: Tag,
  address: MapPin,
  button: MousePointer,
  user: User,
  // Group icons
  folder: Database,
  group: List,
}

// Helper function to get field icon component
const getFieldIcon = (fieldType: string) => {
  const IconComponent = FIELD_ICONS[fieldType] || Type
  return <IconComponent className="w-5 h-5 text-gray-500" />
}

// Helper function to get group icon component
const getGroupIcon = (iconValue: string) => {
  const iconMap: Record<string, any> = {
    // General/Common
    'folder': Database,
    'tag': Tag,
    'settings': Settings,
    'star': Star,
    'heart': Heart,
    'home': Home,
    'bell': Bell,
    'clock': Clock,
    
    // People & Users
    'user': User,
    'users': Users,
    'users2': Users2,
    'usercheck': UserCheck,
    'crown': Crown,
    
    // Business & Finance
    'briefcase': Briefcase,
    'building': Building,
    'dollarsign': DollarSign,
    'creditcard': CreditCard,
    'shoppingcart': ShoppingCart,
    'package': Package,
    'truck': Truck,
    'target': Target,
    
    // Performance & Analytics
    'trendingup': TrendingUp,
    'piechart': PieChart,
    'barchart3': BarChart3,
    'activity': Activity,
    'award': Award,
    'trophy': Trophy,
    
    // Communication & Media
    'messagecircle': MessageCircle,
    'mail': Mail,
    'phone': Phone,
    'camera': Camera,
    'video': Video,
    'music': Music,
    'image': Image,
    
    // Technology & Development
    'code': Code,
    'terminal': Terminal,
    'server': Server,
    'cloud': Cloud,
    'wifi': Wifi,
    'smartphone': Smartphone,
    'monitor': Monitor,
    
    // Security & Access
    'lock': Lock,
    'key': Key,
    'fingerprint': Fingerprint,
    'shield': Shield,
    
    // Education & Knowledge
    'lightbulb': Lightbulb,
    'bookopen': BookOpen,
    'graduationcap': GraduationCap,
    
    // Creative & Design
    'palette': Palette,
    'brush': Brush,
    
    // Miscellaneous
    'filetext': FileText,
    'calendar': Calendar,
    'checksquare': CheckSquare,
    'mappin': MapPin,
    'globe': Globe,
    'link': Link,
    'bot': Bot,
    'zap': Zap
  }
  
  const IconComponent = iconMap[iconValue] || Database
  return IconComponent
}


// Sortable Group Component using dnd-kit
interface SortableGroupProps {
  group: FieldGroup
  isCollapsed: boolean
  fieldCount: number
  isEditing: boolean
  editData: {
    name: string
    description: string
    color: string
    icon: string
  } | null
  onToggleCollapse: (groupId: string) => void
  onDeleteGroup: (groupId: string) => void
  onStartEdit: (group: FieldGroup) => void
  onCancelEdit: () => void
  onSaveEdit: (groupId: string, updates: Partial<FieldGroup>) => Promise<void>
  onEditDataChange: (updates: Partial<{ name: string; description: string; color: string; icon: string }>) => void
  existingGroups: FieldGroup[]
  children: React.ReactNode
}

const SortableGroup: React.FC<SortableGroupProps> = ({
  group,
  isCollapsed,
  fieldCount,
  isEditing,
  editData,
  onToggleCollapse,
  onDeleteGroup,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  onEditDataChange,
  existingGroups,
  children,
}) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: `group-${group.id}`,
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      className="border border-gray-200 dark:border-gray-700 rounded-lg"
      role="group"
      aria-label={`Field group: ${group.name}`}
    >
      {/* Group Header */}
      {isEditing ? (
        // Edit Mode Header
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-700">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <div 
                className="w-5 h-5 rounded flex items-center justify-center"
                style={{ backgroundColor: editData?.color || group.color }}
              >
                {React.createElement(getGroupIcon((editData?.icon || group.icon) || 'folder'), {
                  className: "w-3 h-3 text-white"
                })}
              </div>
              <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
                Edit Group Settings
              </span>
            </div>
            
            <div className="flex items-center space-x-1">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  if (editData && editData.name.trim()) {
                    onSaveEdit(group.id, {
                      name: editData.name,
                      description: editData.description,
                      color: editData.color,
                      icon: editData.icon
                    })
                  }
                }}
                className={`p-1 rounded transition-colors ${
                  editData?.name.trim() 
                    ? 'text-green-600 hover:text-green-700 cursor-pointer' 
                    : 'text-gray-400 cursor-not-allowed'
                }`}
                title={editData?.name.trim() ? 'Save changes' : 'Enter a group name to save'}
                disabled={!editData?.name.trim()}
              >
                <Check className="w-4 h-4" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onCancelEdit()
                }}
                className="p-1 text-gray-500 hover:text-gray-600 rounded"
                title="Cancel editing"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          {/* Edit Form */}
          <div className="space-y-2">
            <div>
              <input
                type="text"
                value={editData?.name || ''}
                onChange={(e) => onEditDataChange({ name: e.target.value })}
                placeholder="Group name *"
                className={`w-full px-2 py-1 text-sm border rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 focus:ring-1 ${
                  !editData?.name.trim() 
                    ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500' 
                    : 'border-gray-200 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500'
                }`}
                autoFocus
                onKeyDown={(e) => {
                  e.stopPropagation()
                  if (e.key === 'Enter' && editData?.name.trim()) {
                    onSaveEdit(group.id, {
                      name: editData.name,
                      description: editData.description,
                      color: editData.color,
                      icon: editData.icon
                    })
                  }
                  if (e.key === 'Escape') {
                    onCancelEdit()
                  }
                }}
              />
              {!editData?.name.trim() && (
                <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                  Group name is required
                </p>
              )}
            </div>
            <div>
              <input
                type="text"
                value={editData?.description || ''}
                onChange={(e) => onEditDataChange({ description: e.target.value })}
                placeholder="Description (optional)"
                className="w-full px-2 py-1 text-sm border border-gray-200 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                onKeyDown={(e) => {
                  e.stopPropagation()
                  if (e.key === 'Enter' && editData?.name.trim()) {
                    onSaveEdit(group.id, {
                      name: editData.name,
                      description: editData.description,
                      color: editData.color,
                      icon: editData.icon
                    })
                  }
                  if (e.key === 'Escape') {
                    onCancelEdit()
                  }
                }}
              />
            </div>
            
            {/* Color Selection */}
            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">Color</label>
              <div className="flex items-center space-x-2">
                {[
                  '#3B82F6', // Blue
                  '#10B981', // Green  
                  '#F59E0B', // Yellow
                  '#EF4444', // Red
                  '#8B5CF6', // Purple
                  '#F97316', // Orange
                  '#06B6D4', // Cyan
                  '#84CC16', // Lime
                  '#EC4899', // Pink
                  '#6B7280'  // Gray
                ].map((color) => (
                  <button
                    key={color}
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      onEditDataChange({ color })
                    }}
                    className={`w-6 h-6 rounded border-2 hover:scale-110 transition-transform ${
                      editData?.color === color
                        ? 'border-gray-800 dark:border-white'
                        : 'border-gray-300 dark:border-gray-600'
                    }`}
                    style={{ backgroundColor: color }}
                    title={color}
                  />
                ))}
              </div>
            </div>
            
            {/* Icon Selection */}
            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">Icon</label>
              <div className="grid grid-cols-8 gap-1 max-h-32 overflow-y-auto">
                {[
                  // General/Common
                  { value: 'folder', icon: Database, label: 'Folder' },
                  { value: 'tag', icon: Tag, label: 'Tag' },
                  { value: 'settings', icon: Settings, label: 'Settings' },
                  { value: 'star', icon: Star, label: 'Star' },
                  { value: 'heart', icon: Heart, label: 'Heart' },
                  { value: 'home', icon: Home, label: 'Home' },
                  { value: 'bell', icon: Bell, label: 'Bell' },
                  { value: 'clock', icon: Clock, label: 'Clock' },
                  
                  // People & Users
                  { value: 'user', icon: User, label: 'User' },
                  { value: 'users', icon: Users, label: 'Users' },
                  { value: 'users2', icon: Users2, label: 'Team' },
                  { value: 'usercheck', icon: UserCheck, label: 'User Check' },
                  { value: 'crown', icon: Crown, label: 'Crown' },
                  
                  // Business & Finance
                  { value: 'briefcase', icon: Briefcase, label: 'Business' },
                  { value: 'building', icon: Building, label: 'Building' },
                  { value: 'dollarsign', icon: DollarSign, label: 'Money' },
                  { value: 'creditcard', icon: CreditCard, label: 'Credit Card' },
                  { value: 'shoppingcart', icon: ShoppingCart, label: 'Shopping' },
                  { value: 'package', icon: Package, label: 'Package' },
                  { value: 'truck', icon: Truck, label: 'Shipping' },
                  { value: 'target', icon: Target, label: 'Target' },
                  
                  // Performance & Analytics
                  { value: 'trendingup', icon: TrendingUp, label: 'Trending' },
                  { value: 'piechart', icon: PieChart, label: 'Pie Chart' },
                  { value: 'barchart3', icon: BarChart3, label: 'Bar Chart' },
                  { value: 'activity', icon: Activity, label: 'Activity' },
                  { value: 'award', icon: Award, label: 'Award' },
                  { value: 'trophy', icon: Trophy, label: 'Trophy' },
                  
                  // Communication & Media
                  { value: 'messagecircle', icon: MessageCircle, label: 'Message' },
                  { value: 'mail', icon: Mail, label: 'Email' },
                  { value: 'phone', icon: Phone, label: 'Phone' },
                  { value: 'camera', icon: Camera, label: 'Camera' },
                  { value: 'video', icon: Video, label: 'Video' },
                  { value: 'music', icon: Music, label: 'Music' },
                  { value: 'image', icon: Image, label: 'Image' },
                  
                  // Technology & Development
                  { value: 'code', icon: Code, label: 'Code' },
                  { value: 'terminal', icon: Terminal, label: 'Terminal' },
                  { value: 'server', icon: Server, label: 'Server' },
                  { value: 'cloud', icon: Cloud, label: 'Cloud' },
                  { value: 'wifi', icon: Wifi, label: 'WiFi' },
                  { value: 'smartphone', icon: Smartphone, label: 'Mobile' },
                  { value: 'monitor', icon: Monitor, label: 'Monitor' },
                  
                  // Security & Access
                  { value: 'lock', icon: Lock, label: 'Lock' },
                  { value: 'key', icon: Key, label: 'Key' },
                  { value: 'fingerprint', icon: Fingerprint, label: 'Security' },
                  { value: 'shield', icon: Shield, label: 'Shield' },
                  
                  // Education & Knowledge
                  { value: 'lightbulb', icon: Lightbulb, label: 'Idea' },
                  { value: 'bookopen', icon: BookOpen, label: 'Book' },
                  { value: 'graduationcap', icon: GraduationCap, label: 'Education' },
                  
                  // Creative & Design
                  { value: 'palette', icon: Palette, label: 'Palette' },
                  { value: 'brush', icon: Brush, label: 'Brush' },
                  
                  // Miscellaneous
                  { value: 'filetext', icon: FileText, label: 'Document' },
                  { value: 'calendar', icon: Calendar, label: 'Calendar' },
                  { value: 'checksquare', icon: CheckSquare, label: 'Checkbox' },
                  { value: 'mappin', icon: MapPin, label: 'Location' },
                  { value: 'globe', icon: Globe, label: 'Globe' },
                  { value: 'link', icon: Link, label: 'Link' },
                  { value: 'bot', icon: Bot, label: 'Bot' },
                  { value: 'zap', icon: Zap, label: 'Lightning' }
                ].map((iconOption) => {
                  const IconComp = iconOption.icon
                  return (
                    <button
                      key={iconOption.value}
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        onEditDataChange({ icon: iconOption.value })
                      }}
                      className={`p-1 rounded border-2 transition-all ${
                        editData?.icon === iconOption.value
                          ? 'bg-blue-100 border-blue-500 text-blue-700 dark:bg-blue-900/50 dark:border-blue-400 dark:text-blue-300 shadow-md scale-110'
                          : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-gray-400'
                      }`}
                      title={iconOption.label}
                    >
                      <IconComp className="w-3 h-3" />
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      ) : (
        // View Mode Header
        <div 
          className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700/50"
          onClick={() => onToggleCollapse(group.id)}
        >
          <div className="flex items-center space-x-2">
            {/* Drag Handle for Group */}
            <div 
              className="opacity-0 group-hover:opacity-100 cursor-grab active:cursor-grabbing touch-none mr-2"
              {...listeners}
              onClick={(e) => e.stopPropagation()}
              role="button"
              aria-label={`Drag to reorder group: ${group.name}`}
              tabIndex={0}
            >
              <GripVertical className="w-4 h-4 text-gray-400 hover:text-gray-600" />
            </div>
            <div 
              className="w-6 h-6 rounded flex items-center justify-center"
              style={{ backgroundColor: group.color }}
            >
              {React.createElement(getGroupIcon(group.icon || 'folder'), {
                className: "w-3 h-3 text-white"
              })}
            </div>
            <div className="flex flex-col">
              <span className="font-medium text-sm text-gray-900 dark:text-white">
                {group.name}
              </span>
              {group.description && (
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {group.description}
                </span>
              )}
            </div>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              ({fieldCount} fields)
            </span>
          </div>
          <div className="flex items-center space-x-1">
            <button
              onClick={(e) => {
                e.stopPropagation()
                onStartEdit(group)
              }}
              className="p-1 text-gray-400 hover:text-blue-600 rounded"
              title="Edit group settings"
            >
              <Edit className="w-3 h-3" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDeleteGroup(group.id)
              }}
              className="p-1 text-gray-400 hover:text-red-600 rounded"
              title="Delete group"
            >
              <Trash2 className="w-3 h-3" />
            </button>
            <ChevronDown 
              className={`w-4 h-4 text-gray-400 transition-transform ${
                isCollapsed ? '-rotate-90' : ''
              }`}
            />
          </div>
        </div>
      )}

      {children}
    </div>
  )
}

// Sortable Field Component using dnd-kit
interface SortableFieldProps {
  field: PipelineField
  index: number
  isEditing: boolean
  fieldTypeInfo?: FieldType
  availableFieldTypes: FieldType[]
  fieldGroups: FieldGroup[]
  onEditClick: (fieldId: string) => void
  onMoveField: (fieldId: string, direction: 'up' | 'down') => void
  onToggleVisibility: (fieldId: string, visible: boolean) => void
  onManageField: (field: PipelineField) => void
  onDeleteField: (fieldId: string) => void
  onAssignToGroup: (fieldId: string, groupId: string | null) => void
  isDragOverlay?: boolean
}

const SortableField: React.FC<SortableFieldProps> = ({ 
  field, 
  isDragOverlay = false, 
  ...props 
}) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: `field-${field.id}`,
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      role="listitem"
      aria-label={`Field: ${field.display_name || field.label || field.name}`}
    >
      <FieldItem
        {...props}
        field={field}
        dragHandleProps={listeners}
        isDragOverlay={isDragOverlay}
      />
    </div>
  )
}

// Memoized Field Item Component - Two-Line Compact Design with Hidden Tags on Hover
const FieldItem = React.memo(({ 
  field, 
  index, 
  isEditing, 
  fieldTypeInfo, 
  availableFieldTypes,
  fieldGroups,
  onEditClick,
  onMoveField,
  onToggleVisibility,
  onManageField,
  onDeleteField,
  onAssignToGroup,
  dragHandleProps,
  isDragOverlay
}: {
  field: PipelineField
  index: number
  isEditing: boolean
  fieldTypeInfo?: FieldType
  availableFieldTypes: FieldType[]
  fieldGroups: FieldGroup[]
  onEditClick: (fieldId: string) => void
  onMoveField: (fieldId: string, direction: 'up' | 'down') => void
  onToggleVisibility: (fieldId: string, visible: boolean) => void
  onManageField: (field: PipelineField) => void
  onDeleteField: (fieldId: string) => void
  onAssignToGroup: (fieldId: string, groupId: string | null) => void
  dragHandleProps?: any
  isDragOverlay?: boolean
}) => {
  const [showGroupDropdown, setShowGroupDropdown] = React.useState(false)
  const dropdownRef = React.useRef<HTMLDivElement>(null)
  const Icon = FIELD_ICONS[field.field_type || field.type || 'text'] || Type
  const requiredStages = getRequiredStages(field)
  const isVisible = field.is_visible_in_list ?? field.visible ?? true
  
  // Close dropdown when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowGroupDropdown(false)
      }
    }
    
    if (showGroupDropdown) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showGroupDropdown])
  
  return (
    <div
      className={`group relative p-3 border rounded-lg cursor-pointer transition-all duration-200 ${
        isEditing 
          ? 'border-primary bg-primary/5 ring-2 ring-primary/20 shadow-sm' 
          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700/50 bg-white dark:bg-gray-800'
      }`}
      onClick={() => onEditClick(field.id)}
    >
      {/* First Line: Icon + Field Name + Field Type + Drag Handle */}
      <div className="flex items-center mb-2">
        {/* Drag Handle */}
        <div 
          className="flex items-center mr-2 opacity-0 group-hover:opacity-100 cursor-grab active:cursor-grabbing touch-none"
          {...dragHandleProps}
          role="button"
          aria-label={`Drag to reorder field: ${field.display_name || field.label || field.name}`}
          tabIndex={0}
        >
          <GripVertical className="w-4 h-4 text-gray-400 hover:text-gray-600" />
        </div>
        
        {/* Position and Field Icon */}
        <div className="flex items-center mr-3 flex-shrink-0">
          <span className="text-xs text-gray-400 dark:text-gray-500 font-mono mr-2 w-4 text-right">
            {index + 1}
          </span>
          <div className={`flex items-center justify-center w-6 h-6 rounded ${
            isEditing ? 'bg-primary text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
          }`}>
            <Icon className="w-3 h-3" />
          </div>
        </div>
        
        {/* Field Info */}
        <div className="flex-1 min-w-0">
          <div className="font-medium text-gray-900 dark:text-white truncate">
            {field.display_name || field.label || field.name}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
            {fieldTypeInfo?.label || (field.field_type || field.type)}
          </div>
        </div>
      </div>
      
      {/* Relationship Field Configuration Display */}
      {(field.field_type === 'relation' || field.type === 'relation') && field.field_config && hasEnhancedRelationshipFeatures(field.field_config) && (
        <div className="mb-2 p-2 bg-gray-50 dark:bg-gray-800 rounded-lg group-hover:opacity-0 transition-opacity">
          <RelationshipFieldIndicator 
            fieldConfig={field.field_config} 
            size="sm"
            showDetails={true}
          />
        </div>
      )}

      {/* Second Line: Status Badges (hidden on hover) + Actions (shown on hover) */}
      <div className="flex items-center justify-between min-h-[24px]">
        {/* Status Badges - Hidden on hover */}
        <div className="flex flex-wrap items-center gap-1 group-hover:opacity-0 transition-opacity flex-1 pr-2">
          {/* Deletion Status Badge */}
          {field.deletion_status?.status && field.deletion_status.status !== 'active' && (
            <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-300 rounded-full whitespace-nowrap">
              {field.deletion_status.status === 'soft_deleted' ? 'Deleted' : 'Scheduled for Deletion'}
            </span>
          )}
          
          {/* Stage-specific required badges */}
          {requiredStages.map((stage) => (
            <span key={stage} className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300 rounded-full whitespace-nowrap">
              Required: {stage.charAt(0).toUpperCase() + stage.slice(1)}
            </span>
          ))}
          
          {/* Hidden Badge */}
          {!isVisible && (
            <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300 rounded-full whitespace-nowrap">
              Hidden
            </span>
          )}
          
          {/* AI Badge */}
          {field.is_ai_field && (
            <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300 rounded-full whitespace-nowrap">
              <Bot className="w-3 h-3 mr-1" />
              AI
            </span>
          )}
        </div>
        
        {/* Field Actions - Shown on hover */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
          {/* Group Assignment Dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={(e) => {
                e.stopPropagation()
                setShowGroupDropdown(!showGroupDropdown)
              }}
              className="p-1 text-gray-400 hover:text-purple-600 dark:hover:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded transition-colors"
              title="Assign to group"
            >
              <FolderPlus className="w-3 h-3" />
            </button>
            
            {showGroupDropdown && (
              <div className="absolute right-0 top-6 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-50">
                <div className="p-1">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onAssignToGroup(field.id, null)
                      setShowGroupDropdown(false)
                    }}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 rounded ${
                      !field.field_group ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300'
                    }`}
                  >
                    No Group
                  </button>
                  
                  {(Array.isArray(fieldGroups) ? fieldGroups : []).map(group => (
                    <button
                      key={group.id}
                      onClick={(e) => {
                        e.stopPropagation()
                        onAssignToGroup(field.id, group.id)
                        setShowGroupDropdown(false)
                      }}
                      className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 rounded flex items-center space-x-2 ${
                        field.field_group === group.id ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300'
                      }`}
                    >
                      <div 
                        className="w-3 h-3 rounded-full" 
                        style={{ backgroundColor: group.color }}
                      />
                      <span className="truncate">{group.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
          
          <button
            onClick={(e) => {
              e.stopPropagation()
              onToggleVisibility(field.id, !isVisible)
            }}
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600 rounded transition-colors"
            title={`${isVisible ? 'Hide' : 'Show'} field`}
          >
            {isVisible ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
          </button>
          
          <button
            onClick={(e) => {
              e.stopPropagation()
              onManageField(field)
            }}
            className="p-1 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors"
            title="Manage field lifecycle"
          >
            <Shield className="w-3 h-3" />
          </button>
          
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDeleteField(field.id)
            }}
            className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
            title="Delete field"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  )
})

// Cache for stage requirements calculation to avoid repeated processing
const stageCache = new Map<string, string[]>()

// Helper function to extract required stages from field business rules
const getRequiredStages = (field: PipelineField): string[] => {
  try {
    // Create cache key based on field ID and business rules hash
    const cacheKey = `${field.id}_${JSON.stringify(field.business_rules?.stage_requirements || {})}`
    
    if (stageCache.has(cacheKey)) {
      return stageCache.get(cacheKey)!
    }
    
    const stageReqs = field.business_rules?.stage_requirements || {}
    const result = Object.entries(stageReqs)
      .filter(([stage, config]: [string, any]) => config?.required === true)
      .map(([stage]) => stage)
    
    stageCache.set(cacheKey, result)
    return result
  } catch (error) {
    console.error('Error in getRequiredStages:', error)
    return []
  }
}

export function PipelineFieldBuilder({ pipelineId, fields, onFieldsChange, onSave }: Props) {
  const [availableFieldTypes, setAvailableFieldTypes] = useState<FieldType[]>([])
  const [userTypes, setUserTypes] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddField, setShowAddField] = useState(false)
  const [editingField, setEditingField] = useState<string | null>(null)
  const [tenantAiConfig, setTenantAiConfig] = useState<any>(null)
  const [managingField, setManagingField] = useState<PipelineField | null>(null)
  
  // Field groups state
  const [fieldGroups, setFieldGroups] = useState<FieldGroup[]>([])
  const [creatingGroup, setCreatingGroup] = useState(false)
  const [newGroupName, setNewGroupName] = useState('')
  
  // Field groups editing state (legacy - will be replaced by settings panel)
  const [editingGroup, setEditingGroup] = useState<string | null>(null)
  const [editGroupData, setEditGroupData] = useState<{
    name: string
    description: string
    color: string
    icon: string
  } | null>(null)
  
  
  // Frontend-only collapse state management
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(() => {
    if (typeof window !== 'undefined' && pipelineId) {
      const saved = localStorage.getItem(`collapsed-groups-${pipelineId}`)
      return saved ? new Set(JSON.parse(saved)) : new Set()
    }
    return new Set()
  })
  
  // Save collapse state to localStorage
  const saveCollapseState = useCallback((newCollapsedGroups: Set<string>) => {
    if (typeof window !== 'undefined' && pipelineId) {
      localStorage.setItem(`collapsed-groups-${pipelineId}`, JSON.stringify([...newCollapsedGroups]))
    }
  }, [pipelineId])
  
  // Drag and drop state
  const [activeId, setActiveId] = useState<string | null>(null)
  const [draggedField, setDraggedField] = useState<PipelineField | null>(null)
  const [draggedGroup, setDraggedGroup] = useState<FieldGroup | null>(null)
  
  // Group deletion dialog state
  const [deletionDialogGroup, setDeletionDialogGroup] = useState<FieldGroup | null>(null)
  const [isDeletingGroup, setIsDeletingGroup] = useState(false)
  
  // Load available field types and user types
  useEffect(() => {
    const loadData = async () => {
      try {
        // Load field types
        const response = await fieldTypesApi.getAll()
        const allTypes: FieldType[] = []
        
        // Flatten the categorized field types
        Object.entries(response.data).forEach(([category, types]) => {
          (types as any[]).forEach((type: any) => {
            allTypes.push({
              key: type.key,
              label: type.label,
              description: type.description,
              icon: type.icon,
              category
            })
          })
        })
        
        setAvailableFieldTypes(allTypes)

        // Load user types for conditional rules
        try {
          const userTypesResponse = await permissionsApi.getUserTypes()
          const userTypesData = userTypesResponse.data.results || userTypesResponse.data || []
          setUserTypes(userTypesData)
        } catch (userTypeError) {
          console.error('Failed to load user types:', userTypeError)
          // Set fallback user types if API fails
          setUserTypes([
            { id: '1', name: 'Admin', slug: 'admin', description: 'System Administrator' },
            { id: '2', name: 'Manager', slug: 'manager', description: 'Manager' },
            { id: '3', name: 'User', slug: 'user', description: 'Regular User' },
            { id: '4', name: 'Viewer', slug: 'viewer', description: 'Read-only Access' }
          ])
        }
      } catch (error) {
        console.error('Failed to load field types:', error)
      } finally {
        setLoading(false)
      }
    }
    
    loadData()
  }, [])

  // Load tenant AI configuration for AI field defaults
  useEffect(() => {
    const loadAiConfig = async () => {
      try {
        const aiConfigResponse = await aiApi.jobs.tenantConfig()
        setTenantAiConfig(aiConfigResponse.data)
      } catch (error) {
        console.error('Failed to load tenant AI config:', error)
        // Don't set fallback - AI field creation will fail if config is not available
        setTenantAiConfig(null)
      }
    }
    loadAiConfig()
  }, [])

  // Load field groups for this pipeline
  useEffect(() => {
    const loadFieldGroups = async () => {
      if (!pipelineId) return
      
      try {
        console.log('🔧 Loading field groups for pipeline:', pipelineId)
        const response = await pipelinesApi.getFieldGroups(pipelineId)
        console.log('🔧 Field groups API response:', response)
        
        // Handle both paginated and direct array responses
        const groupsData = response.data?.results || (response as any).results || response.data || response || []
        const validGroupsData = Array.isArray(groupsData) ? groupsData : []
        console.log('🔧 Setting field groups:', validGroupsData.length, 'groups')
        setFieldGroups(validGroupsData)
      } catch (error) {
        console.error('🔧 Failed to load field groups:', error)
        setFieldGroups([])
      }
    }
    loadFieldGroups()
  }, [pipelineId])
  
  // Add new field with new architecture
  const addField = (fieldType: FieldType) => {
    const fieldName = `${fieldType.key}_${fields.length + 1}`
    const newField: PipelineField = {
      id: `field_${Date.now()}`,
      name: fieldName,                      // Field slug
      display_name: `${fieldType.label} ${fields.length + 1}`, // Display name
      description: '',                      // Field description
      field_type: fieldType.key,            // Field type
      help_text: '',                        // User help text
      
      // Display configuration
      display_order: fields.length,
      is_visible_in_list: true,
      is_visible_in_detail: true,
      is_visible_in_public_forms: false,  // Default to private
      is_visible_in_shared_list_and_detail_views: false,  // Default to private
      
      // Behavior
      is_searchable: true,
      create_index: false,
      enforce_uniqueness: false,
      is_ai_field: fieldType.key === 'ai_generated',
      
      // Configuration objects - NEW ARCHITECTURE
      field_config: fieldType.key === 'select' ? { allow_multiple: false } : 
                   fieldType.key === 'multiselect' ? { allow_multiple: true } : {},
      storage_constraints: {
        allow_null: true,  // Always true for modern architecture
        max_storage_length: null,
        enforce_uniqueness: false,
        create_index: false
      },
      business_rules: {
        stage_requirements: {},
        conditional_requirements: [],
        block_transitions: true,
        show_warnings: true
      },
      ai_config: fieldType.key === 'ai_generated' ? {
        prompt: 'Analyze this record: {*}', // Default prompt to prevent validation error
        model: tenantAiConfig?.default_model || '', // Require explicit model selection if config not loaded
        temperature: 0.3,
        output_type: 'text',
        enable_tools: false,
        allowed_tools: [],
        trigger_fields: [],
        cache_duration: 3600,
        fallback_value: 'Analysis unavailable'
      } : undefined,
      
      // Legacy support
      label: `${fieldType.label} ${fields.length + 1}`,
      type: fieldType.key,
      required: false,
      visible: true,
      order: fields.length,
      config: {}
    }
    
    onFieldsChange([...fields, newField])
    setShowAddField(false)
    setEditingField(newField.id)
  }
  
  
  // Memoized field action handlers to prevent re-renders
  // Update field - optimized to avoid full array mapping  
  const updateField = useCallback((fieldId: string, updates: Partial<PipelineField>) => {
    const index = fields.findIndex(f => f.id === fieldId)
    if (index === -1) return
    
    const newFields = [...fields]
    newFields[index] = { ...fields[index], ...updates }
    onFieldsChange(newFields)
  }, [fields, onFieldsChange])
  
  
  // Delete field
  const deleteField = (fieldId: string) => {
    onFieldsChange(fields.filter(field => field.id !== fieldId))
    if (editingField === fieldId) {
      setEditingField(null)
    }
  }
  
  // Field Groups Management Functions
  const deleteFieldGroup = async (groupId: string) => {
    if (!pipelineId) return
    
    if (!confirm('Are you sure you want to delete this field group? Fields in this group will be moved to "Ungrouped Fields".')) {
      return
    }
    
    try {
      await pipelinesApi.deleteFieldGroup(pipelineId, groupId)
      
      // Remove group from local state
      setFieldGroups(groups => groups.filter(g => g.id !== groupId))
      
      // Update fields that were in this group to be ungrouped
      onFieldsChange(fields.map(field => 
        field.field_group === groupId 
          ? { ...field, field_group: null, field_group_name: undefined }
          : field
      ))
    } catch (error) {
      console.error('Failed to delete field group:', error)
    }
  }

  const createFieldGroup = async () => {
    if (!pipelineId || !newGroupName.trim()) return
    
    setCreatingGroup(true)
    try {
      const response = await pipelinesApi.createFieldGroup(pipelineId, {
        name: newGroupName.trim(),
        description: '',
        color: '#3B82F6',
        icon: 'folder',
        display_order: fieldGroups.length
      })
      
      setFieldGroups([...fieldGroups, response.data])
      setNewGroupName('')
    } catch (error) {
      console.error('Failed to create field group:', error)
    } finally {
      setCreatingGroup(false)
    }
  }
  
  const assignFieldToGroup = async (fieldId: string, groupId: string | null) => {
    if (!pipelineId) return
    
    console.log('🔄 assignFieldToGroup called:', { fieldId, groupId })
    console.log('🔄 Current fieldGroups state:', fieldGroups)
    
    try {
      if (groupId) {
        // Assign field to group - convert fieldId to integer
        const fieldIdInt = parseInt(fieldId, 10)
        console.log('🔄 Calling pipelinesApi.assignFieldsToGroup:', { pipelineId, groupId, fieldIds: [fieldIdInt], originalFieldId: fieldId })
        const assignResponse = await pipelinesApi.assignFieldsToGroup(pipelineId, groupId, [fieldId])
        console.log('✅ Assign response:', assignResponse.data)
      } else {
        // Find the field's current group and ungroup it
        const field = fields.find(f => f.id === fieldId)
        if (field?.field_group) {
          const fieldIdInt = parseInt(fieldId, 10)
          console.log('🔄 Calling pipelinesApi.ungroupFields:', { pipelineId, groupId: field.field_group, fieldIds: [fieldIdInt], originalFieldId: fieldId })
          await pipelinesApi.ungroupFields(pipelineId, field.field_group, [fieldId])
        }
      }
      
      // Update field locally after successful API call
      console.log('🔄 Updating field locally:', { fieldId, field_group: groupId })
      updateField(fieldId, { field_group: groupId })
      console.log('🔄 Field updated, current fieldGroups state:', fieldGroups.length, 'groups')
      
      // Reload field groups to update field counts (use setTimeout to ensure state updates complete)
      setTimeout(async () => {
        try {
          console.log('🔄 Reloading field groups...')
          const groupsResponse = await pipelinesApi.getFieldGroups(pipelineId)
          console.log('🔍 Field groups reload response:', groupsResponse)
          
          // Handle both paginated and direct array responses
          const groupsData = groupsResponse.data?.results || (groupsResponse as any).results || groupsResponse.data || groupsResponse || []
          const validGroupsData = Array.isArray(groupsData) ? groupsData : []
          console.log('🔄 Setting field groups (delayed):', validGroupsData.length, 'groups')
          setFieldGroups(validGroupsData)
        } catch (reloadError) {
          console.error('Failed to reload field groups:', reloadError)
        }
      }, 100)
      
    } catch (error) {
      console.error('Failed to update field group assignment:', error)
      // Don't revert since we haven't updated locally yet
    }
  }
  
  const toggleGroupCollapse = useCallback((groupId: string) => {
    const newCollapsedGroups = new Set(collapsedGroups)
    
    if (collapsedGroups.has(groupId)) {
      newCollapsedGroups.delete(groupId)
    } else {
      newCollapsedGroups.add(groupId)
    }
    
    setCollapsedGroups(newCollapsedGroups)
    saveCollapseState(newCollapsedGroups)
  }, [collapsedGroups, saveCollapseState])

  // Field group editing functions
  const startEditingGroup = (group: FieldGroup) => {
    setEditingGroup(group.id)
    setEditGroupData({
      name: group.name,
      description: group.description || '',
      color: group.color,
      icon: group.icon || 'folder'
    })
  }

  const cancelEditingGroup = () => {
    setEditingGroup(null)
    setEditGroupData(null)
  }

  const updateFieldGroup = async (groupId: string, updates: Partial<FieldGroup>) => {
    if (!pipelineId || !editGroupData) return
    
    // Validation
    const trimmedName = editGroupData.name.trim()
    if (!trimmedName) {
      console.error('Group name is required')
      return
    }
    
    // Check for duplicate names (excluding current group)
    const isDuplicate = fieldGroups.some(group => 
      group.id !== groupId && 
      group.name.toLowerCase() === trimmedName.toLowerCase()
    )
    
    if (isDuplicate) {
      console.error('A group with this name already exists')
      return
    }
    
    try {
      // Prepare clean updates object
      const cleanUpdates = {
        name: trimmedName,
        description: editGroupData.description.trim(),
        color: editGroupData.color,
        icon: editGroupData.icon
      }
      
      // Call API to update group
      await pipelinesApi.updateFieldGroup(pipelineId, groupId, cleanUpdates)
      
      // Update local state
      setFieldGroups(groups => groups.map(group => 
        group.id === groupId 
          ? { ...group, ...cleanUpdates }
          : group
      ))
      
      // Clear editing state
      cancelEditingGroup()
    } catch (error) {
      console.error('Failed to update field group:', error)
      // TODO: Show user-friendly error message
    }
  }

  const handleEditGroupDataChange = (updates: Partial<{ name: string; description: string; color: string; icon: string }>) => {
    if (!editGroupData) return
    setEditGroupData(prev => prev ? { ...prev, ...updates } : null)
  }

  const confirmDeleteFieldGroup = async () => {
    if (!pipelineId || !deletionDialogGroup) return
    
    setIsDeletingGroup(true)
    try {
      await pipelinesApi.deleteFieldGroup(pipelineId, deletionDialogGroup.id)
      
      // Remove group from local state
      setFieldGroups(groups => groups.filter(g => g.id !== deletionDialogGroup.id))
      
      // Update fields that were in this group to be ungrouped
      onFieldsChange(fields.map(field => 
        field.field_group === deletionDialogGroup.id 
          ? { ...field, field_group: null, field_group_name: undefined }
          : field
      ))
    } catch (error) {
      console.error('Failed to delete field group:', error)
      throw error // Re-throw to let dialog handle the error
    } finally {
      setIsDeletingGroup(false)
    }
  }

  const closeDeletionDialog = () => {
    if (!isDeletingGroup) {
      setDeletionDialogGroup(null)
    }
  }

  const handleEditClick = useCallback((fieldId: string) => {
    setEditingField(fieldId)
  }, [])

  const handleMoveField = useCallback((fieldId: string, direction: 'up' | 'down') => {
    moveField(fieldId, direction)
  }, [])


  const handleToggleVisibility = useCallback((fieldId: string, visible: boolean) => {
    updateField(fieldId, { 
      is_visible_in_list: visible,
      visible: visible // Legacy support
    })
  }, [updateField])

  const handleManageField = useCallback((field: PipelineField) => {
    setManagingField(field)
  }, [])

  const handleDeleteField = useCallback((fieldId: string) => {
    deleteField(fieldId)
  }, [])
  
  // Reorder fields
  const moveField = (fieldId: string, direction: 'up' | 'down') => {
    const currentIndex = fields.findIndex(f => f.id === fieldId)
    if (currentIndex === -1) return
    
    const newIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1
    if (newIndex < 0 || newIndex >= fields.length) return
    
    const newFields = [...fields]
    const [movedField] = newFields.splice(currentIndex, 1)
    newFields.splice(newIndex, 0, movedField)
    
    // Update order numbers
    newFields.forEach((field, index) => {
      field.display_order = index
      field.order = index // Legacy support
    })
    
    onFieldsChange(newFields)
  }
  
  // Configure drag and drop sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 8px movement before drag starts
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // Drag handlers
  const handleDragStart = useCallback((event: DragStartEvent) => {
    const { active } = event
    setActiveId(String(active.id))
    
    // Check if dragging a field or a group
    if (String(active.id).startsWith('field-')) {
      const fieldId = String(active.id).replace('field-', '')
      const field = fields.find(f => f.id === fieldId)
      setDraggedField(field || null)
      setDraggedGroup(null)
    } else if (String(active.id).startsWith('group-')) {
      const groupId = String(active.id).replace('group-', '')
      const group = fieldGroups.find(g => g.id === groupId)
      setDraggedGroup(group || null)
      setDraggedField(null)
    }
  }, [fields, fieldGroups])

  const handleDragOver = useCallback((event: DragOverEvent) => {
    // Handle drag over logic for cross-container moves
    // This will be implemented when we add field-to-group dragging
  }, [])

  const handleDragEnd = useCallback(async (event: DragEndEvent) => {
    const { active, over } = event
    
    setActiveId(null)
    setDraggedField(null)
    setDraggedGroup(null)
    
    if (!over) return
    
    const activeId = String(active.id)
    const overId = String(over.id)
    
    if (activeId === overId) return
    
    try {
      // Handle field reordering
      if (activeId.startsWith('field-') && overId.startsWith('field-')) {
        const activeFieldId = activeId.replace('field-', '')
        const overFieldId = overId.replace('field-', '')
        
        const activeField = fields.find(f => f.id === activeFieldId)
        const overField = fields.find(f => f.id === overFieldId)
        
        if (activeField && overField) {
          // Check if fields are in the same group
          if (activeField.field_group === overField.field_group) {
            // Reorder within same group or ungrouped section
            await handleFieldReorder(activeFieldId, overFieldId)
          } else {
            // Move field to different group
            await assignFieldToGroup(activeFieldId, overField.field_group || null)
          }
        }
      }
      // Handle group reordering
      else if (activeId.startsWith('group-') && overId.startsWith('group-')) {
        const activeGroupId = activeId.replace('group-', '')
        const overGroupId = overId.replace('group-', '')
        await handleGroupReorder(activeGroupId, overGroupId)
      }
      // Handle field dropped on group
      else if (activeId.startsWith('field-') && overId.startsWith('group-')) {
        const fieldId = activeId.replace('field-', '')
        const groupId = overId.replace('group-', '')
        await assignFieldToGroup(fieldId, groupId)
      }
      // Handle field dropped on ungrouped section
      else if (activeId.startsWith('field-') && overId === 'ungrouped') {
        const fieldId = activeId.replace('field-', '')
        await assignFieldToGroup(fieldId, null)
      }
    } catch (error) {
      console.error('Drag operation failed:', error)
      // TODO: Show error toast
    }
  }, [fields, fieldGroups, assignFieldToGroup])

  // Helper functions for drag operations
  const handleFieldReorder = useCallback(async (activeFieldId: string, overFieldId: string) => {
    const activeField = fields.find(f => f.id === activeFieldId)
    const overField = fields.find(f => f.id === overFieldId)
    
    if (!activeField || !overField) return
    
    // Get all fields in the same group (or ungrouped)
    const groupFields = fields.filter(f => f.field_group === activeField.field_group)
    const sortedGroupFields = groupFields.sort((a, b) => a.display_order - b.display_order)
    
    const oldIndex = sortedGroupFields.findIndex(f => f.id === activeFieldId)
    const newIndex = sortedGroupFields.findIndex(f => f.id === overFieldId)
    
    if (oldIndex !== -1 && newIndex !== -1) {
      const reorderedFields = arrayMove(sortedGroupFields, oldIndex, newIndex)
      
      // Update display orders
      reorderedFields.forEach((field, index) => {
        field.display_order = index
      })
      
      // Update the main fields array
      const updatedFields = [...fields]
      reorderedFields.forEach(reorderedField => {
        const fieldIndex = updatedFields.findIndex(f => f.id === reorderedField.id)
        if (fieldIndex !== -1) {
          updatedFields[fieldIndex] = reorderedField
        }
      })
      
      onFieldsChange(updatedFields)
    }
  }, [fields, onFieldsChange])

  const handleGroupReorder = useCallback(async (activeGroupId: string, overGroupId: string) => {
    const oldIndex = fieldGroups.findIndex(g => g.id === activeGroupId)
    const newIndex = fieldGroups.findIndex(g => g.id === overGroupId)
    
    if (oldIndex !== -1 && newIndex !== -1) {
      const reorderedGroups = arrayMove(fieldGroups, oldIndex, newIndex)
      
      // Update display orders
      reorderedGroups.forEach((group, index) => {
        group.display_order = index
      })
      
      setFieldGroups(reorderedGroups)
      
      // Call API to update group order
      const groupOrders = reorderedGroups.map((group, index) => ({
        id: group.id,
        display_order: index
      }))
      
      if (pipelineId) {
        await pipelinesApi.reorderFieldGroups(pipelineId, groupOrders)
      }
    }
  }, [fieldGroups, pipelineId])

  // Helper function to organize fields by groups - MUST be before any conditional returns
  const organizedFields = useMemo(() => {
    const ungroupedFields = fields.filter(field => !field.field_group)
    const groupedFields: Record<string, PipelineField[]> = {}
    
    console.log('🔍 Organizing fields:', fields.length, 'total fields')
    console.log('🔍 Fields data:', fields.map(f => ({ id: f.id, name: f.name, field_group: f.field_group, field_group_type: typeof f.field_group })))
    
    // Check if any fields have field_group values
    const fieldsWithGroups = fields.filter(f => f.field_group != null)
    console.log('🔍 Fields WITH groups on page load:', fieldsWithGroups.length, 'out of', fields.length, 'total')
    console.log('🔍 Fields with groups details:', fieldsWithGroups.map(f => ({ id: f.id, name: f.name, field_group: f.field_group })))
    
    // Group fields by their field_group
    fields.forEach(field => {
      if (field.field_group) {
        const groupId = String(field.field_group) // Ensure string key
        if (!groupedFields[groupId]) {
          groupedFields[groupId] = []
        }
        groupedFields[groupId].push(field)
        console.log('🔍 Added field to group:', { fieldName: field.name, fieldId: field.id, groupId, groupIdType: typeof groupId })
      }
    })
    
    console.log('🔍 Grouped fields:', groupedFields)
    console.log('🔍 Ungrouped fields:', ungroupedFields.length, 'fields')
    
    // Sort fields within each group by display_order
    Object.keys(groupedFields).forEach(groupId => {
      groupedFields[groupId].sort((a, b) => a.display_order - b.display_order)
    })
    
    return { ungroupedFields, groupedFields }
  }, [fields])
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading field types...</div>
      </div>
    )
  }

  return (
    <div className="h-full flex">
      {/* Fields List */}
      <div className="w-80 flex-shrink-0 border-r border-gray-200 dark:border-gray-700 flex flex-col">
        <div className="flex-shrink-0 p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Fields
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {fields.length} field{fields.length !== 1 ? 's' : ''} configured
              </p>
            </div>
            <button
              onClick={() => setShowAddField(true)}
              className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-lg text-white bg-primary hover:bg-primary/90 transition-colors"
            >
              <Plus className="w-3 h-3 mr-1" />
              Add Field
            </button>
          </div>
        </div>
        
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
          modifiers={[restrictToVerticalAxis, restrictToWindowEdges]}
          accessibility={{
            announcements: {
              onDragStart({active}) {
                const activeId = String(active.id)
                if (activeId.startsWith('field-')) {
                  const fieldId = activeId.replace('field-', '')
                  const field = fields.find(f => f.id === fieldId)
                  return `Started dragging field ${field?.display_name || field?.label || field?.name}`
                } else if (activeId.startsWith('group-')) {
                  const groupId = activeId.replace('group-', '')
                  const group = fieldGroups.find(g => g.id === groupId)
                  return `Started dragging field group ${group?.name}`
                }
                return 'Started dragging'
              },
              onDragOver({active, over}) {
                if (over) {
                  const overId = String(over.id)
                  if (overId.startsWith('group-')) {
                    const groupId = overId.replace('group-', '')
                    const group = fieldGroups.find(g => g.id === groupId)
                    return `Dragging over field group ${group?.name}`
                  }
                }
                return 'Dragging'
              },
              onDragEnd({active, over}) {
                const activeId = String(active.id)
                if (over) {
                  const overId = String(over.id)
                  if (activeId.startsWith('field-') && overId.startsWith('group-')) {
                    const groupId = overId.replace('group-', '')
                    const group = fieldGroups.find(g => g.id === groupId)
                    return `Field moved to group ${group?.name}`
                  } else if (activeId.startsWith('group-') && overId.startsWith('group-')) {
                    return `Field group reordered`
                  }
                  return 'Item moved'
                } else {
                  return 'Item returned to original position'
                }
              },
              onDragCancel() {
                return 'Dragging cancelled'
              },
            },
          }}
        >
          <div className="flex-1 overflow-y-auto min-h-0">
            {fields.length === 0 ? (
            <div className="p-8 text-center">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Type className="w-10 h-10 text-blue-500" />
              </div>
              <h4 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">
                Start Building Your Pipeline
              </h4>
              <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-sm mx-auto">
                Fields are the building blocks of your pipeline. Add your first field to define what data you want to collect.
              </p>
              <button
                onClick={() => setShowAddField(true)}
                className="inline-flex items-center px-6 py-3 border border-transparent text-sm font-semibold rounded-xl text-white bg-primary hover:bg-primary/90 shadow-lg hover:shadow-xl transition-all transform hover:-translate-y-0.5"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Your First Field
              </button>
              
              <div className="mt-8 grid grid-cols-3 gap-4 max-w-xs mx-auto">
                <div className="text-center">
                  <div className="w-8 h-8 bg-green-100 dark:bg-green-900/20 rounded-lg flex items-center justify-center mx-auto mb-2">
                    <Type className="w-4 h-4 text-green-600" />
                  </div>
                  <p className="text-xs text-gray-500">Text Fields</p>
                </div>
                <div className="text-center">
                  <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/20 rounded-lg flex items-center justify-center mx-auto mb-2">
                    <CheckSquare className="w-4 h-4 text-blue-600" />
                  </div>
                  <p className="text-xs text-gray-500">Selections</p>
                </div>
                <div className="text-center">
                  <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/20 rounded-lg flex items-center justify-center mx-auto mb-2">
                    <Bot className="w-4 h-4 text-purple-600" />
                  </div>
                  <p className="text-xs text-gray-500">AI Fields</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-3 space-y-4">
              {/* Inline Group Creation */}
              <div className="border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-lg p-3">
                {!creatingGroup ? (
                  <button
                    onClick={() => setCreatingGroup(true)}
                    className="w-full text-left text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors flex items-center space-x-2"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Add Field Group</span>
                  </button>
                ) : (
                  <div className="space-y-2">
                    <input
                      type="text"
                      value={newGroupName}
                      onChange={(e) => setNewGroupName(e.target.value)}
                      placeholder="Group name"
                      className="w-full px-2 py-1 text-sm border border-gray-200 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') createFieldGroup()
                        if (e.key === 'Escape') {
                          setCreatingGroup(false)
                          setNewGroupName('')
                        }
                      }}
                    />
                    <div className="flex space-x-2">
                      <button
                        onClick={createFieldGroup}
                        disabled={!newGroupName.trim()}
                        className="px-2 py-1 text-xs bg-primary text-white rounded hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Create
                      </button>
                      <button
                        onClick={() => {
                          setCreatingGroup(false)
                          setNewGroupName('')
                        }}
                        className="px-2 py-1 text-xs bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-500"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Field Groups */}
              <SortableContext
                items={(Array.isArray(fieldGroups) ? fieldGroups : []).map(group => `group-${group.id}`)}
                strategy={verticalListSortingStrategy}
              >
                {(Array.isArray(fieldGroups) ? fieldGroups : []).map(group => {
                  const groupIdStr = String(group.id) // Ensure string key for lookup
                  const fieldsInGroup = organizedFields.groupedFields[groupIdStr] || []
                  console.log('🔍 Rendering group:', { groupId: group.id, groupIdStr, groupIdType: typeof group.id, fieldsInGroup: fieldsInGroup.length, groupName: group.name })
                  console.log('🔧 Group object:', group)
                  
                  return (
                    <SortableGroup
                      key={group.id}
                      group={group}
                      isCollapsed={collapsedGroups.has(group.id)}
                      fieldCount={fieldsInGroup.length}
                      isEditing={editingGroup === group.id}
                      editData={editingGroup === group.id ? editGroupData : null}
                      onToggleCollapse={toggleGroupCollapse}
                      onDeleteGroup={deleteFieldGroup}
                      onStartEdit={startEditingGroup}
                      onCancelEdit={cancelEditingGroup}
                      onSaveEdit={updateFieldGroup}
                      onEditDataChange={handleEditGroupDataChange}
                      existingGroups={fieldGroups}
                    >
                    {/* Group Fields */}
                    {!collapsedGroups.has(group.id) && (
                    <SortableContext
                      items={fieldsInGroup.map(field => `field-${field.id}`)}
                      strategy={verticalListSortingStrategy}
                    >
                      <div 
                        className="p-2 space-y-1"
                        role="list"
                        aria-label={`Fields in ${group.name} group`}
                      >
                        {fieldsInGroup.map((field, index) => {
                        const isEditing = editingField === field.id
                        const fieldTypeInfo = availableFieldTypes.find(t => t.key === (field.field_type || field.type))
                        
                        return (
                          <SortableField
                            key={field.id}
                            field={field}
                            index={index}
                            isEditing={isEditing}
                            fieldTypeInfo={fieldTypeInfo}
                            availableFieldTypes={availableFieldTypes}
                            fieldGroups={fieldGroups}
                            onEditClick={handleEditClick}
                            onMoveField={handleMoveField}
                            onToggleVisibility={handleToggleVisibility}
                            onManageField={handleManageField}
                            onDeleteField={handleDeleteField}
                            onAssignToGroup={assignFieldToGroup}
                          />
                        )
                      })}
                      
                      {/* Empty group message */}
                      {fieldsInGroup.length === 0 && (
                        <div className="text-center py-4 text-sm text-gray-500 dark:text-gray-400">
                          No fields in this group yet
                        </div>
                      )}
                      </div>
                    </SortableContext>
                  )}
                    </SortableGroup>
                  )
                })}
              </SortableContext>

              {/* Ungrouped Fields */}
              {organizedFields.ungroupedFields.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center space-x-2 px-1">
                    <div className="w-3 h-3 bg-gray-400 rounded-full" />
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                      Ungrouped Fields ({organizedFields.ungroupedFields.length})
                    </span>
                  </div>
                  
                  <SortableContext
                    items={organizedFields.ungroupedFields.map(field => `field-${field.id}`)}
                    strategy={verticalListSortingStrategy}
                  >
                    <div role="list" aria-label="Ungrouped fields">
                      {organizedFields.ungroupedFields.map((field, index) => {
                    const isEditing = editingField === field.id
                    const fieldTypeInfo = availableFieldTypes.find(t => t.key === (field.field_type || field.type))
                    
                    return (
                      <SortableField
                        key={field.id}
                        field={field}
                        index={index}
                        isEditing={isEditing}
                        fieldTypeInfo={fieldTypeInfo}
                        availableFieldTypes={availableFieldTypes}
                        fieldGroups={fieldGroups}
                        onEditClick={handleEditClick}
                        onMoveField={handleMoveField}
                        onToggleVisibility={handleToggleVisibility}
                        onManageField={handleManageField}
                        onDeleteField={handleDeleteField}
                        onAssignToGroup={assignFieldToGroup}
                      />
                    )
                  })}
                    </div>
                  </SortableContext>
                </div>
              )}
            </div>
          )}
          </div>
          
          <DragOverlay>
            {draggedField ? (
              <div className="p-3 bg-white dark:bg-gray-800 border border-gray-300 rounded-lg shadow-lg opacity-90">
                <div className="flex items-center space-x-2">
                  <div className="w-6 h-6 bg-primary/10 rounded flex items-center justify-center">
                    {React.createElement(FIELD_ICONS[draggedField.field_type || draggedField.type || 'text'] || Type, {
                      className: "w-3 h-3 text-primary"
                    })}
                  </div>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {draggedField.display_name || draggedField.label || draggedField.name}
                  </span>
                </div>
              </div>
            ) : draggedGroup ? (
              <div className="p-3 bg-white dark:bg-gray-800 border border-gray-300 rounded-lg shadow-lg opacity-90">
                <div className="flex items-center space-x-2">
                  <div 
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: draggedGroup.color }}
                  />
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {draggedGroup.name}
                  </span>
                </div>
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </div>
      
      {/* Field Configuration */}
      <div className="flex-1 flex flex-col min-w-0">
        {editingField ? (
          <FieldEditor 
            field={fields.find(f => f.id === editingField)!}
            availableFieldTypes={availableFieldTypes}
            userTypes={userTypes}
            onUpdate={(updates) => updateField(editingField, updates)}
            onClose={() => setEditingField(null)}
            fields={fields}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center bg-gray-50 dark:bg-gray-800/50">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Settings className="w-8 h-8 text-gray-500 dark:text-gray-400" />
              </div>
              <h4 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">
                Configure Your Fields
              </h4>
              <p className="text-gray-500 dark:text-gray-400 mb-6">
                Select a field from the list to customize its properties, validation rules, and display settings.
              </p>
              <div className="flex items-center justify-center space-x-4 text-sm text-gray-400">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                  <span>Basic Settings</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  <span>Validation</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
                  <span>Display</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Add Field Modal */}
      {showAddField && (
        <AddFieldModal
          availableFieldTypes={availableFieldTypes}
          onAddField={addField}
          onClose={() => setShowAddField(false)}
        />
      )}
      
      {/* Field Management Panel */}
      {managingField && pipelineId && (
        <FieldManagementPanel
          field={managingField}
          pipelineId={pipelineId}
          onFieldUpdate={(updatedField) => {
            onFieldsChange(fields.map(f => f.id === updatedField.id ? updatedField : f))
            setManagingField(null)
          }}
          onClose={() => setManagingField(null)}
        />
      )}
    </div>
  )
}

// Field Editor Component - Uses NEW FieldConfigurationPanel with Tabs
function FieldEditor({ 
  field, 
  availableFieldTypes, 
  userTypes,
  onUpdate, 
  onClose,
  fields
}: {
  field: PipelineField
  availableFieldTypes: FieldType[]
  userTypes: any[]
  onUpdate: (updates: Partial<PipelineField>) => void
  onClose: () => void
  fields: PipelineField[]
}) {
  const fieldType = availableFieldTypes.find(t => t.key === (field.field_type || field.type))
  const [activeTab, setActiveTab] = useState('basic')

  // Memoized onChange handlers to prevent performance issues
  const handleConfigChange = useCallback((newConfig: Record<string, any>) => {
    onUpdate({ 
      field_config: newConfig,
      config: newConfig // Legacy support
    })
  }, [onUpdate])

  const handleStorageConstraintsChange = useCallback((newConstraints: Record<string, any>) => {
    onUpdate({ 
      storage_constraints: newConstraints,
      // Sync legacy properties for backward compatibility
      enforce_uniqueness: newConstraints.enforce_uniqueness || false,
      create_index: newConstraints.create_index || false
    })
  }, [onUpdate])

  const tabs = [
    {
      id: 'basic',
      label: 'Basic',
      icon: Sliders,
      description: 'Field name, type, and basic settings'
    },
    {
      id: 'display',
      label: 'Display',
      icon: Layout,
      description: 'Visibility and display options'
    },
    {
      id: 'validation',
      label: 'Validation',
      icon: CheckCircle,
      description: 'Form validation rules and requirements'
    },
    {
      id: 'advanced',
      label: 'Advanced',
      icon: Zap,
      description: 'Type-specific configuration and AI settings'
    }
  ]
  
  return (
    <>
      <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        {/* Field Header */}
        <div className="p-6 pb-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-primary/10 rounded-xl">
                {React.createElement(FIELD_ICONS[field.field_type || field.type || 'text'] || Type, {
                  className: "w-6 h-6 text-primary"
                })}
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                  {field.display_name || field.label || field.name}
                </h3>
                <div className="flex items-center space-x-2 mt-1">
                  <span className="inline-flex items-center px-2.5 py-0.5 text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300 rounded-full">
                    {fieldType?.label || field.field_type || field.type}
                  </span>
                  {field.is_ai_field && (
                    <span className="inline-flex items-center px-2.5 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300 rounded-full">
                      <Bot className="w-3 h-3 mr-1" />
                      AI Enhanced
                    </span>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="px-6 pt-4">
          <nav className="flex space-x-1" role="tablist">
            {tabs.map((tab) => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`group relative px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                    isActive
                      ? 'bg-primary text-white shadow-lg'
                      : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                  role="tab"
                  aria-selected={isActive}
                  title={tab.description}
                >
                  <div className="flex items-center space-x-2">
                    <Icon className="w-4 h-4" />
                    <span>{tab.label}</span>
                  </div>
                  {isActive && (
                    <div className="absolute -bottom-px left-0 right-0 h-0.5 bg-primary rounded-full" />
                  )}
                </button>
              )
            })}
          </nav>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'basic' && (
            <BasicFieldSettings 
              field={field} 
              fieldType={fieldType}
              availableFieldTypes={availableFieldTypes}
              onUpdate={onUpdate} 
            />
          )}
          
          
          {activeTab === 'display' && (
            <DisplaySettings 
              field={field} 
              fields={fields}
              userTypes={userTypes}
              onUpdate={onUpdate} 
            />
          )}
          
          {activeTab === 'validation' && (
            <ValidationSettings 
              field={field} 
              onUpdate={onUpdate} 
            />
          )}
          
          {activeTab === 'advanced' && (
            <AdvancedSettings 
              field={field} 
              fields={fields}
              onUpdate={onUpdate} 
            />
          )}
        </div>
      </div>
    </>
  )
}

// Add Field Modal Component
function AddFieldModal({ 
  availableFieldTypes, 
  onAddField, 
  onClose 
}: {
  availableFieldTypes: FieldType[]
  onAddField: (fieldType: FieldType) => void
  onClose: () => void
}) {
  // Group field types by category
  const groupedTypes = availableFieldTypes.reduce((acc, type) => {
    if (!acc[type.category]) {
      acc[type.category] = []
    }
    acc[type.category].push(type)
    return acc
  }, {} as Record<string, FieldType[]>)
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Add New Field
            </h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
        
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          {Object.entries(groupedTypes).map(([category, types]) => (
            <div key={category} className="mb-6">
              <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3 capitalize">
                {category} Fields
              </h4>
              <div className="grid grid-cols-2 gap-3">
                {types.map(type => {
                  const Icon = FIELD_ICONS[type.key] || Type
                  return (
                    <button
                      key={type.key}
                      onClick={() => onAddField(type)}
                      className="p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-primary hover:bg-primary/5 transition-colors text-left"
                    >
                      <div className="flex items-center space-x-3">
                        <Icon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                        <div>
                          <div className="font-medium text-gray-900 dark:text-white">
                            {type.label}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {type.description}
                          </div>
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}

// Basic Field Settings Tab Component
function BasicFieldSettings({ 
  field, 
  fieldType, 
  availableFieldTypes, 
  onUpdate 
}: {
  field: PipelineField
  fieldType?: FieldType
  availableFieldTypes: FieldType[]
  onUpdate: (updates: Partial<PipelineField>) => void
}) {
  return (
    <div className="space-y-6">
      <div>
        <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Basic Information
        </h4>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Field Label *
            </label>
            <input
              type="text"
              value={field.display_name || field.label || ''}
              onChange={(e) => {
                const label = e.target.value
                const slug = label.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'field'
                onUpdate({ 
                  display_name: label,
                  name: slug,
                  label: label // Legacy support
                })
              }}
              className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white transition-colors"
              placeholder="Enter field label"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
              Field Name (Auto-generated)
            </label>
            <div className="px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-600 dark:text-gray-400">
              {field.name || 'field_name'}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Used for API access and database storage
            </p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Field Type {!field.id && '*'}
            </label>
            
            {/* For new fields: show dropdown selector */}
            {!field.id ? (
              <>
                <select
                  value={field.field_type || field.type || ''}
                  onChange={(e) => onUpdate({ 
                    field_type: e.target.value,
                    type: e.target.value, // Legacy support
                    is_ai_field: e.target.value === 'ai_generated'
                  })}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white transition-colors"
                >
                  <option value="">Select field type...</option>
                  {availableFieldTypes.map(type => (
                    <option key={type.key} value={type.key}>
                      {type.label}
                    </option>
                  ))}
                </select>
                {fieldType && (
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                    {fieldType.description}
                  </p>
                )}
              </>
            ) : (
              /* For existing fields: display only with management hint */
              <>
                <div className="px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg flex items-center justify-between">
                  <div className="flex items-center">
                    {fieldType && getFieldIcon(field.field_type || field.type || '')}
                    <span className="ml-2 text-gray-900 dark:text-white font-medium">
                      {fieldType?.label || field.field_type || field.type}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    Use the shield icon to change type
                  </span>
                </div>
                {fieldType && (
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                    {fieldType.description}
                  </p>
                )}
              </>
            )}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Description
            </label>
            <textarea
              value={field.description || ''}
              onChange={(e) => onUpdate({ description: e.target.value })}
              placeholder="Optional field description for documentation"
              className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white transition-colors"
              rows={3}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Help Text
            </label>
            <input
              type="text"
              value={field.help_text || ''}
              onChange={(e) => onUpdate({ help_text: e.target.value })}
              placeholder="Help text shown to users when filling out this field"
              className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white transition-colors"
            />
          </div>
        </div>
      </div>
    </div>
  )
}


// Display Settings Tab Component
function DisplaySettings({ 
  field, 
  fields,
  userTypes,
  onUpdate 
}: {
  field: PipelineField
  fields: PipelineField[]
  userTypes: any[]
  onUpdate: (updates: Partial<PipelineField>) => void
}) {
  return (
    <div className="space-y-6">
      <div>
        <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Display Options
        </h4>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Visibility Settings
            </label>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center space-x-3">
                  <Layout className="w-5 h-5 text-gray-500" />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">Show in List View</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Display this field in record lists and tables</div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  id="visible-list"
                  checked={field.is_visible_in_list !== false}
                  onChange={(e) => onUpdate({ 
                    is_visible_in_list: e.target.checked,
                    visible: e.target.checked // Legacy support
                  })}
                  className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
                />
              </div>
              
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center space-x-3">
                  <Eye className="w-5 h-5 text-gray-500" />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">Show in Detail View</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Display this field when viewing individual records</div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  id="visible-detail"
                  checked={field.is_visible_in_detail !== false}
                  onChange={(e) => onUpdate({ is_visible_in_detail: e.target.checked })}
                  className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
                />
              </div>
              
              <div className="flex items-center justify-between p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <div className="flex items-center space-x-3">
                  <Settings className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">Public Forms Visible</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Show this field in public forms (external users)</div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  id="visible-public-forms"
                  checked={field.is_visible_in_public_forms || false}
                  onChange={(e) => onUpdate({ is_visible_in_public_forms: e.target.checked })}
                  className="w-4 h-4 text-blue-600 bg-white border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
                />
              </div>
              
              {/* Shared Views Visibility */}
              <div className="flex items-center justify-between p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                <div className="flex items-center space-x-3">
                  <Share2 className="w-5 h-5 text-orange-500" />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">Shared Views Visible</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Show this field in shared filtered views (external access)</div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  id="visible-shared-views"
                  checked={field.is_visible_in_shared_list_and_detail_views || false}
                  onChange={(e) => onUpdate({ is_visible_in_shared_list_and_detail_views: e.target.checked })}
                  className="w-4 h-4 text-orange-600 bg-white border-gray-300 rounded focus:ring-orange-500 focus:ring-2"
                />
              </div>
              
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center space-x-3">
                  <Settings className="w-5 h-5 text-gray-500" />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">Searchable</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Include this field in search operations</div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  id="searchable"
                  checked={field.is_searchable !== false}
                  onChange={(e) => onUpdate({ is_searchable: e.target.checked })}
                  className="w-4 h-4 text-primary bg-white border-gray-300 rounded focus:ring-primary focus:ring-2"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Conditional Display Rules Section */}
      <div>
        <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Conditional Display Rules
        </h4>
        <ConditionalRulesBuilder
          field={field}
          availableFields={fields.map(f => ({
            id: f.id,
            name: f.name,
            display_name: f.display_name || f.name,
            field_type: f.field_type
          }))}
          userTypes={userTypes}
          onChange={(conditionalRules) => {
            // Sync conditional rules back to stage_requirements for 2-way connection
            const updatedBusinessRules = {
              ...field.business_rules,
              conditional_rules: conditionalRules
            }
            
            // Extract stage requirements from require_when rules
            const requireWhen = conditionalRules?.require_when
            if (requireWhen && requireWhen.rules) {
              const stageRequirements: Record<string, any> = {}
              
              // Find select fields that could be stage fields
              const selectFields = fields.filter(f => f.field_type === 'select')
              
              for (const rule of requireWhen.rules) {
                if ('field' in rule && rule.field && rule.condition === 'equals' && rule.value) {
                  // Check if this rule references a select field (likely a stage field)
                  const referencedField = selectFields.find(f => f.name === rule.field)
                  if (referencedField) {
                    stageRequirements[rule.value] = {
                      required: true,
                      ...(rule.description && rule.description.includes('blocks transitions') ? { block_transitions: true } : {}),
                      ...(rule.description && rule.description.includes('Warning:') ? {
                        warning_message: rule.description.split('Warning:')[1]?.split(' - ')[0]?.trim()
                      } : {})
                    }
                  }
                }
              }
              
              // Only update stage_requirements if we found stage-related rules
              if (Object.keys(stageRequirements).length > 0) {
                (updatedBusinessRules as any).stage_requirements = stageRequirements
              }
            }
            
            onUpdate({
              business_rules: updatedBusinessRules
            })
          }}
        />
      </div>
    </div>
  )
}

// Advanced Settings Tab Component
function AdvancedSettings({ 
  field, 
  fields, 
  onUpdate 
}: {
  field: PipelineField
  fields: PipelineField[]
  onUpdate: (updates: Partial<PipelineField>) => void
}) {
  // Memoized onChange handlers for AdvancedSettings
  const handleConfigChange = useCallback((newConfig: Record<string, any>) => {
    const start = performance.now()
    console.log('[PERF] AdvancedSettings handleConfigChange START')
    console.log('[PERF] New config object:', newConfig)
    
    onUpdate({ 
      field_config: newConfig,
      config: newConfig // Legacy support
    })
    
    const end = performance.now()
    console.log(`[PERF] AdvancedSettings handleConfigChange TOTAL: ${end - start}ms`)
  }, [onUpdate])

  const handleStorageConstraintsChange = useCallback((newConstraints: Record<string, any>) => {
    onUpdate({ 
      storage_constraints: newConstraints,
      // Sync legacy properties for backward compatibility
      enforce_uniqueness: newConstraints.enforce_uniqueness || false,
      create_index: newConstraints.create_index || false
    })
  }, [onUpdate])
  return (
    <div className="space-y-6">
      <div>
        <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Advanced Configuration
        </h4>
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
          <div className="flex items-start space-x-3">
            <Zap className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5" />
            <div>
              <h5 className="font-medium text-blue-800 dark:text-blue-200">
                Type-Specific Settings
              </h5>
              <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                Configure field-specific options, validation rules, and behavior based on the selected field type.
              </p>
            </div>
          </div>
        </div>
        
        <FieldConfigurationPanel
          fieldType={field.field_type || field.type || ''}
          config={field.field_config || field.config || {}}
          onChange={handleConfigChange}
          storageConstraints={field.storage_constraints || {}}
          onStorageConstraintsChange={handleStorageConstraintsChange}
          // AI configuration props
          aiConfig={field.ai_config || {}}
          onAiConfigChange={(newAiConfig) => onUpdate({
            ai_config: newAiConfig
          })}
          isVisible={true}
          availableFields={fields.filter(f => f.id !== field.id).map(f => ({
            id: f.id,
            name: f.name,
            display_name: f.display_name || f.label || f.name,
            field_type: f.field_type || f.type || 'text',
            field_config: f.field_config || f.config || {}
          }))}
        />
      </div>
    </div>
  )
}

// Validation Settings Tab Component
function ValidationSettings({ 
  field, 
  onUpdate 
}: {
  field: PipelineField
  onUpdate: (updates: Partial<PipelineField>) => void
}) {
  const validationRules = field.form_validation_rules || {}

  const updateValidationRule = (key: string, value: any) => {
    const newRules = { ...validationRules, [key]: value }
    // Remove empty/false values to keep the object clean
    if (value === '' || value === false || value === null || value === undefined) {
      delete newRules[key]
    }
    onUpdate({ form_validation_rules: newRules })
  }

  const fieldType = field.field_type || field.type || 'text'

  return (
    <div className="space-y-6">
      <div>
        <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Form Validation Rules
        </h4>
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-6">
          <div className="flex items-start space-x-3">
            <CheckCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5" />
            <div>
              <h5 className="font-medium text-yellow-800 dark:text-yellow-200">
                Validation Applied at Form Level
              </h5>
              <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                These rules are applied when users submit forms, not when data is stored directly in the database.
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {/* Required Field Settings Information */}
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <div className="flex items-start space-x-3">
              <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
              <div>
                <h5 className="font-medium text-blue-800 dark:text-blue-200 mb-2">
                  Field Requirements Setup
                </h5>
                <p className="text-sm text-blue-700 dark:text-blue-300 mb-3">
                  Field requirements are now configured through the <strong>Business Rules</strong> system, which provides advanced conditional logic based on stage, user type, and other field values.
                </p>
                <button
                  onClick={() => {
                    // Navigate to business rules tab if it exists, or show info
                    const businessRulesTab = document.querySelector('[data-tab="business-rules"]') as HTMLButtonElement
                    if (businessRulesTab) {
                      businessRulesTab.click()
                    }
                  }}
                  className="inline-flex items-center text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 transition-colors"
                >
                  → Configure in Business Rules tab
                </button>
              </div>
            </div>
          </div>

          {/* Text Length Validation (for text fields) */}
          {(fieldType === 'text' || fieldType === 'textarea' || fieldType === 'email' || fieldType === 'url') && (
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <h5 className="font-medium text-gray-900 dark:text-white mb-4">Text Length Validation</h5>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Minimum Length
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={validationRules.minLength || ''}
                    onChange={(e) => updateValidationRule('minLength', e.target.value ? parseInt(e.target.value) : '')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Maximum Length
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={validationRules.maxLength || ''}
                    onChange={(e) => updateValidationRule('maxLength', e.target.value ? parseInt(e.target.value) : '')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="No limit"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Number Range Validation (for number fields) */}
          {(fieldType === 'number' || fieldType === 'decimal') && (
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <h5 className="font-medium text-gray-900 dark:text-white mb-4">Number Range Validation</h5>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Minimum Value
                  </label>
                  <input
                    type="number"
                    step={fieldType === 'decimal' ? '0.01' : '1'}
                    value={validationRules.min || ''}
                    onChange={(e) => updateValidationRule('min', e.target.value ? parseFloat(e.target.value) : '')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="No minimum"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Maximum Value
                  </label>
                  <input
                    type="number"
                    step={fieldType === 'decimal' ? '0.01' : '1'}
                    value={validationRules.max || ''}
                    onChange={(e) => updateValidationRule('max', e.target.value ? parseFloat(e.target.value) : '')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="No maximum"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Email Validation (automatic for email fields) */}
          {fieldType === 'email' && (
            <div className="border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
              <div className="flex items-center space-x-3">
                <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                <div>
                  <div className="font-medium text-gray-900 dark:text-white">Email Format Validation</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">Automatically validates email format</div>
                </div>
              </div>
            </div>
          )}

          {/* URL Validation (automatic for url fields) */}
          {fieldType === 'url' && (
            <div className="border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
              <div className="flex items-center space-x-3">
                <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                <div>
                  <div className="font-medium text-gray-900 dark:text-white">URL Format Validation</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">Automatically validates URL format</div>
                </div>
              </div>
            </div>
          )}

          {/* Pattern/Regex Validation */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h5 className="font-medium text-gray-900 dark:text-white mb-4">Custom Pattern Validation</h5>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Regular Expression Pattern
                </label>
                <input
                  type="text"
                  value={validationRules.pattern || ''}
                  onChange={(e) => updateValidationRule('pattern', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white font-mono text-sm"
                  placeholder="^[A-Z0-9-]+$ (example: uppercase letters, numbers, hyphens)"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  JavaScript regular expression for custom validation
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Custom Error Message
                </label>
                <input
                  type="text"
                  value={validationRules.customMessage || ''}
                  onChange={(e) => updateValidationRule('customMessage', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                  placeholder="Please enter a valid value (optional custom message)"
                />
              </div>
            </div>
          </div>

          {/* Show current validation rules summary */}
          {Object.keys(validationRules).length > 0 && (
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <h5 className="font-medium text-blue-800 dark:text-blue-200 mb-2">Active Validation Rules</h5>
              <div className="text-sm text-blue-700 dark:text-blue-300">
                <pre className="font-mono bg-white dark:bg-gray-800 p-2 rounded border">
                  {JSON.stringify(validationRules, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}