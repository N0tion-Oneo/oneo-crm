// RecordTableHeader - Table header with sorting functionality and field groups
import React, { useMemo } from 'react'
import { 
  ArrowUp, ArrowDown, CheckSquare, Square, Type, FileText, Hash, 
  Calendar, Mail, Phone, Link, Image, Users, Bot, Tag, Clock, User,
  Database, Heart, Star, Home, Briefcase, Target, TrendingUp, DollarSign,
  CreditCard, ShoppingCart, Package, Truck, Bell, MessageCircle, Users2,
  UserCheck, Crown, Award, Trophy, Lightbulb, BookOpen, GraduationCap,
  PieChart, BarChart3, Activity, Wifi, Smartphone, Monitor, Camera,
  Video, Music, Key, Fingerprint, Palette, Brush, MapPin, Zap, List,
  ToggleLeft, GitBranch, MousePointer, HelpCircle, Code, Terminal,
  Server, Cloud, Shield, Settings, Building
} from 'lucide-react'
import { RecordField, Sort, Record, FieldGroup } from '@/types/records'
import { FieldUtilsService } from '@/services/records'

const STATIC_FIELD_ICONS: {[key: string]: React.ComponentType<{ className?: string }>} = {
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

// Helper function to get group icon component (same as in record detail drawer)
const getGroupIcon = (iconValue: string) => {
  const iconMap: {[key: string]: any} = {
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
    'lock': Bot, // Use Bot for lock since Lock is not imported
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
    'globe': Link, // Use Link for globe since Globe is not imported
    'link': Link,
    'bot': Bot,
    'zap': Zap
  }
  
  const IconComponent = iconMap[iconValue] || Database
  return IconComponent
}

export interface RecordTableHeaderProps {
  fields: RecordField[]
  fieldGroups?: FieldGroup[]
  sort: Sort
  onSort: (fieldName: string) => void
  selectedRecords: Set<string>
  records: Record[]
  onSelectAll: () => void
  className?: string
}

export function RecordTableHeader({
  fields,
  fieldGroups = [],
  sort,
  onSort,
  selectedRecords,
  records,
  onSelectAll,
  className = ""
}: RecordTableHeaderProps) {
  const allSelected = records.length > 0 && selectedRecords.size === records.length

  // Group fields by field_group and organize them
  const { groupedFields, hasGroups } = useMemo(() => {
    const groups = new Map<string | null, RecordField[]>()
    
    // Organize visible fields by group
    fields.forEach(field => {
      // Normalize field group ID to string for consistent comparison
      const groupId = field.field_group ? String(field.field_group) : null
      if (!groups.has(groupId)) {
        groups.set(groupId, [])
      }
      groups.get(groupId)!.push(field)
    })
    
    // Sort groups by display order
    const sortedGroups: { group: FieldGroup | null; fields: RecordField[] }[] = []
    
    // Process defined field groups first
    if (fieldGroups.length > 0) {
      const sortedFieldGroups = [...fieldGroups].sort((a, b) => a.display_order - b.display_order)
      
      sortedFieldGroups.forEach(group => {
        // Use string version of group ID for lookup
        const groupFields = groups.get(String(group.id))
        if (groupFields && groupFields.length > 0) {
          sortedGroups.push({ group, fields: groupFields })
        }
      })
    }
    
    // Add ungrouped fields last
    const ungroupedFields = groups.get(null)
    if (ungroupedFields && ungroupedFields.length > 0) {
      sortedGroups.push({ group: null, fields: ungroupedFields })
    }
    
    return {
      groupedFields: sortedGroups,
      hasGroups: fieldGroups.length > 0 && sortedGroups.some(g => g.group !== null)
    }
  }, [fields, fieldGroups])

  return (
    <thead className={`bg-gray-50 dark:bg-gray-800 sticky top-0 z-10 ${className}`}>
      {/* Field groups row (only if there are groups) */}
      {hasGroups && (
        <tr className="border-b border-gray-200 dark:border-gray-600">
          {/* Selection column */}
          <th className="w-12 px-4 py-2"></th>
          
          {/* Field group headers */}
          {groupedFields.map(({ group, fields: groupFields }) => {
            const groupColspan = groupFields.length
            
            if (group) {
              const GroupIcon = getGroupIcon(group.icon)
              return (
                <th
                  key={`group-${group.id}`}
                  colSpan={groupColspan}
                  className="px-4 py-2 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-r border-gray-200 dark:border-gray-600"
                  style={{ backgroundColor: group.color + '10' }}
                >
                  <div className="flex items-center space-x-2">
                    <div 
                      className="w-4 h-4 rounded flex items-center justify-center"
                      style={{ backgroundColor: group.color }}
                    >
                      <GroupIcon className="w-3 h-3 text-white" />
                    </div>
                    <span className="truncate">{group.name}</span>
                  </div>
                </th>
              )
            } else {
              return (
                <th
                  key="group-ungrouped"
                  colSpan={groupColspan}
                  className="px-4 py-2 text-left text-sm font-semibold text-gray-500 dark:text-gray-400 border-r border-gray-200 dark:border-gray-600"
                >
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 rounded bg-gray-400 flex items-center justify-center">
                      <List className="w-3 h-3 text-white" />
                    </div>
                    <span>Other Fields</span>
                  </div>
                </th>
              )
            }
          })}
          
          {/* System columns grouped header */}
          <th colSpan={4} className="px-4 py-2 text-left text-sm font-semibold text-gray-500 dark:text-gray-400">
            <div className="flex items-center space-x-2">
              <Clock className="w-4 h-4" />
              <span>System</span>
            </div>
          </th>
        </tr>
      )}

      {/* Individual field columns row */}
      <tr className={hasGroups ? 'border-b border-gray-300 dark:border-gray-600' : ''}>
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