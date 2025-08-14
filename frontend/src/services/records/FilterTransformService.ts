// FilterTransformService - Handles filter transformation and boolean query processing
import { Filter, FilterGroup, BooleanQuery, FilterOperator } from '@/types/records'

export class FilterTransformService {
  /**
   * Transform boolean query to flat filter array for API consumption
   */
  static transformBooleanQueryToFilters(booleanQuery: BooleanQuery): Filter[] {
    const allFilters: Filter[] = []
    
    if (booleanQuery && booleanQuery.groups) {
      booleanQuery.groups.forEach(group => {
        allFilters.push(...group.filters)
      })
    }
    
    return allFilters
  }

  /**
   * Transform flat filter array back to boolean query structure
   */
  static transformFiltersToBooleanQuery(filters: Filter[]): BooleanQuery {
    if (filters.length === 0) {
      return {
        groups: [{
          id: 'group-1',
          logic: 'AND',
          filters: []
        }],
        groupLogic: 'AND'
      }
    }

    return {
      groups: [{
        id: 'group-1',
        logic: 'AND',
        filters: [...filters]
      }],
      groupLogic: 'AND'
    }
  }

  /**
   * Add filter to specific group in boolean query
   */
  static addFilterToGroup(
    booleanQuery: BooleanQuery, 
    groupId: string, 
    filter: Filter
  ): BooleanQuery {
    if (!booleanQuery) {
      return {
        groups: [{ id: groupId, logic: 'AND', filters: [filter] }],
        groupLogic: 'AND'
      }
    }
    return {
      ...booleanQuery,
      groups: (booleanQuery.groups || []).map(group => 
        group.id === groupId 
          ? { ...group, filters: [...group.filters, filter] }
          : group
      )
    }
  }

  /**
   * Remove filter from group
   */
  static removeFilterFromGroup(
    booleanQuery: BooleanQuery, 
    groupId: string, 
    filterIndex: number
  ): BooleanQuery {
    if (!booleanQuery) return { groups: [], groupLogic: 'AND' }
    return {
      ...booleanQuery,
      groups: (booleanQuery.groups || []).map(group => 
        group.id === groupId 
          ? { 
              ...group, 
              filters: group.filters.filter((_, index) => index !== filterIndex) 
            }
          : group
      )
    }
  }

  /**
   * Add new filter group
   */
  static addFilterGroup(booleanQuery: BooleanQuery, logic: 'AND' | 'OR' = 'AND'): BooleanQuery {
    const newGroupId = `group-${Date.now()}`
    
    if (!booleanQuery) {
      return {
        groups: [{ id: newGroupId, logic, filters: [] }],
        groupLogic: 'AND'
      }
    }
    
    return {
      ...booleanQuery,
      groups: [
        ...(booleanQuery.groups || []),
        {
          id: newGroupId,
          logic,
          filters: []
        }
      ]
    }
  }

  /**
   * Remove filter group
   */
  static removeFilterGroup(booleanQuery: BooleanQuery, groupId: string): BooleanQuery {
    if (!booleanQuery) return { groups: [], groupLogic: 'AND' }
    return {
      ...booleanQuery,
      groups: (booleanQuery.groups || []).filter(group => group.id !== groupId)
    }
  }

  /**
   * Update group logic (AND/OR)
   */
  static updateGroupLogic(
    booleanQuery: BooleanQuery, 
    groupId: string, 
    logic: 'AND' | 'OR'
  ): BooleanQuery {
    if (!booleanQuery) return { groups: [], groupLogic: 'AND' }
    return {
      ...booleanQuery,
      groups: (booleanQuery.groups || []).map(group => 
        group.id === groupId 
          ? { ...group, logic }
          : group
      )
    }
  }

  /**
   * Get available filter operators for field type (matching original implementation)
   */
  static getOperatorsForFieldType(fieldType: string): FilterOperator[] {
    // For user, tag, and relationship fields, only show contains and empty/not empty
    if (fieldType === 'user' || fieldType === 'tags' || fieldType === 'relation' || fieldType === 'relationship' || fieldType === 'related') {
      return ['contains', 'is_empty', 'is_not_empty']
    }
    
    // For number fields, show numeric operators
    if (fieldType === 'number') {
      return ['equals', 'greater_than', 'less_than', 'is_empty', 'is_not_empty']
    }
    
    // For text fields, show text operators
    if (fieldType === 'text' || fieldType === 'textarea' || fieldType === 'email') {
      return ['equals', 'contains', 'starts_with', 'ends_with', 'is_empty', 'is_not_empty']
    }
    
    // Default: show all operators
    return ['equals', 'contains', 'starts_with', 'ends_with', 'greater_than', 'less_than', 'is_empty', 'is_not_empty']
  }

  /**
   * Validate filter value for field type
   */
  static validateFilterValue(fieldType: string, operator: FilterOperator, value: any): boolean {
    // Empty checks don't need values
    if (operator === 'is_empty' || operator === 'is_not_empty') {
      return true
    }

    // Check if value is provided
    if (value === null || value === undefined || value === '') {
      return false
    }

    // Type-specific validation
    switch (fieldType) {
      case 'number':
      case 'decimal':
      case 'integer':
      case 'float':
      case 'currency':
      case 'percentage':
        return !isNaN(Number(value))
      
      case 'date':
      case 'datetime':
        return !isNaN(Date.parse(value))
      
      case 'boolean':
        return typeof value === 'boolean' || value === 'true' || value === 'false'
      
      default:
        return true // Text-based fields accept any string
    }
  }

  /**
   * Get filter display text for UI
   */
  static getFilterDisplayText(filter: Filter): string {
    const { field, operator, value } = filter
    
    switch (operator) {
      case 'equals':
        return `${field} equals "${value}"`
      case 'contains':
        return `${field} contains "${value}"`
      case 'starts_with':
        return `${field} starts with "${value}"`
      case 'ends_with':
        return `${field} ends with "${value}"`
      case 'greater_than':
        return `${field} > ${value}`
      case 'less_than':
        return `${field} < ${value}`
      case 'is_empty':
        return `${field} is empty`
      case 'is_not_empty':
        return `${field} is not empty`
      default:
        return `${field} ${operator} ${value}`
    }
  }

  /**
   * Count total active filters across all groups
   */
  static countActiveFilters(booleanQuery: BooleanQuery): number {
    if (!booleanQuery || !booleanQuery.groups) return 0
    return booleanQuery.groups.reduce((total, group) => total + group.filters.length, 0)
  }

  /**
   * Check if boolean query has any filters
   */
  static hasActiveFilters(booleanQuery: BooleanQuery): boolean {
    if (!booleanQuery) return false
    return this.countActiveFilters(booleanQuery) > 0
  }
}