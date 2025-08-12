// RecordDataService - Handles all record CRUD operations and API interactions
import { pipelinesApi, usersApi } from '@/lib/api'
import { Record, Pipeline, Filter, Sort } from '@/types/records'

export interface FetchRecordsParams {
  pipelineId: string
  page?: number
  pageSize?: number
  search?: string
  filters?: Filter[]
  sort?: Sort
  fieldTypes?: {[key: string]: string} // Map of fieldName -> fieldType
}

export interface FetchRecordsResponse {
  results: Record[]
  count: number
  next: string | null
  previous: string | null
}

export class RecordDataService {
  /**
   * Fetch records with pagination, filtering, and sorting
   */
  static async fetchRecords(params: FetchRecordsParams): Promise<FetchRecordsResponse> {
    const {
      pipelineId,
      page = 1,
      pageSize = 50,
      search,
      filters = [],
      sort
    } = params

    // Build API parameters
    const apiParams: any = {
      page,
      page_size: pageSize,
      limit: pageSize // Alternative parameter name
    }

    // Add search if provided
    if (search && search.trim()) {
      apiParams.search = search.trim()
    }

    // Add sorting if provided
    if (sort && sort.direction) {
      const orderPrefix = sort.direction === 'desc' ? '-' : ''
      apiParams.ordering = `${orderPrefix}${sort.field}`
    }

    // Add filters using Django JSONB field lookups (matching original implementation)
    if (filters.length > 0) {
      filters.forEach((filter) => {
        const fieldName = filter.field
        const fieldType = params.fieldTypes?.[fieldName] || 'text'
        const paramName = `data__${fieldName}`
        
        // Special handling for user fields (matching backup implementation)
        if (fieldType === 'user') {
          switch (filter.operator) {
            case 'contains':
            case 'equals':
              // Handle structured user+role filter values
              try {
                const parsedValue = JSON.parse(filter.value)
                if (parsedValue.user_id && parsedValue.role) {
                  // Both user and role specified
                  apiParams[`${paramName}__user_id`] = parseInt(parsedValue.user_id)
                  apiParams[`${paramName}__user_role`] = parsedValue.role
                } else if (parsedValue.user_id) {
                  // Only user specified
                  apiParams[`${paramName}__user_id`] = parseInt(parsedValue.user_id)
                } else if (parsedValue.role) {
                  // Only role specified
                  apiParams[`${paramName}__user_role`] = parsedValue.role
                }
              } catch (e) {
                // Handle legacy filter values
                if (filter.value === 'any') {
                  // Filter for any assigned user (any user_id exists)
                  apiParams[`${paramName}__user_exists`] = true
                } else if (filter.value.startsWith('role:')) {
                  // Filter by role (any user with specific role)
                  const role = filter.value.replace('role:', '')
                  apiParams[`${paramName}__user_role`] = role
                } else if (filter.value !== 'separator') {
                  // Filter by specific user ID
                  apiParams[`${paramName}__user_id`] = parseInt(filter.value)
                }
              }
              break
            case 'is_empty':
              apiParams[`${paramName}__isnull`] = true
              break
            case 'is_not_empty':
              apiParams[`${paramName}__isnull`] = false
              break
          }
        }
        // Special handling for relation fields
        else if (fieldType === 'relation' || fieldType === 'relationship' || fieldType === 'related') {
          switch (filter.operator) {
            case 'contains':
            case 'equals':
              // Relations can be stored as single IDs or arrays - use contains for arrays
              apiParams[`${paramName}__contains`] = filter.value
              break
            case 'is_empty':
              apiParams[`${paramName}__isnull`] = true
              break
            case 'is_not_empty':
              apiParams[`${paramName}__isnull`] = false
              break
          }
        }
        // Special handling for tags fields  
        else if (fieldType === 'tags') {
          switch (filter.operator) {
            case 'contains':
              // Tags use JSONB ? operator, backend expects __icontains
              apiParams[`${paramName}__icontains`] = filter.value
              break
            case 'is_empty':
              apiParams[`${paramName}__isnull`] = true
              break
            case 'is_not_empty':
              apiParams[`${paramName}__isnull`] = false
              break
          }
        }
        // Generic field handling - match backend exact parameter names
        else {
          switch (filter.operator) {
            case 'equals':
              // For boolean fields, send true/false directly
              if (fieldType === 'boolean') {
                apiParams[paramName] = filter.value
              }
              // For select/choice fields, use exact match
              else if (['select', 'multiselect', 'radio', 'checkbox'].includes(fieldType)) {
                apiParams[`${paramName}__exact`] = filter.value
              }
              // For numeric fields, send direct value (backend will cast)
              else if (['number', 'decimal', 'integer', 'float', 'currency', 'percentage'].includes(fieldType)) {
                apiParams[paramName] = filter.value
              }
              // Default: exact text match
              else {
                apiParams[`${paramName}__exact`] = filter.value
              }
              break
            case 'contains':
              // Text fields use icontains
              apiParams[`${paramName}__icontains`] = filter.value
              break
            case 'starts_with':
              // Note: backend doesn't implement istartswith, fallback to icontains
              apiParams[`${paramName}__icontains`] = filter.value
              break
            case 'ends_with':
              // Note: backend doesn't implement iendswith, fallback to icontains
              apiParams[`${paramName}__icontains`] = filter.value
              break
            case 'greater_than':
              // Numeric comparison
              if (['date', 'datetime', 'time'].includes(fieldType)) {
                apiParams[`${paramName}__gte`] = filter.value
              } else {
                apiParams[`${paramName}__gt`] = filter.value
              }
              break
            case 'less_than':
              // Numeric comparison  
              if (['date', 'datetime', 'time'].includes(fieldType)) {
                apiParams[`${paramName}__lte`] = filter.value
              } else {
                apiParams[`${paramName}__lt`] = filter.value
              }
              break
            case 'is_empty':
              apiParams[`${paramName}__isnull`] = true
              break
            case 'is_not_empty':
              apiParams[`${paramName}__isnull`] = false
              break
            default:
              apiParams[paramName] = filter.value
          }
        }
      })
    }

    const response = await pipelinesApi.getRecords(pipelineId, apiParams)
    return response.data
  }

  /**
   * Create a new record
   */
  static async createRecord(pipelineId: string, data: Record['data']): Promise<Record> {
    const response = await pipelinesApi.createRecord(pipelineId, { data })
    return response.data
  }

  /**
   * Update a record
   */
  static async updateRecord(
    pipelineId: string, 
    recordId: string, 
    data: Partial<Record['data']>
  ): Promise<Record> {
    const response = await pipelinesApi.updateRecord(pipelineId, recordId, { data })
    return response.data
  }

  /**
   * Delete a record (soft delete)
   */
  static async deleteRecord(pipelineId: string, recordId: string): Promise<void> {
    await pipelinesApi.deleteRecord(pipelineId, recordId)
  }

  /**
   * Bulk update multiple records
   */
  static async bulkUpdateRecords(
    pipelineId: string, 
    recordIds: string[], 
    data: Record['data']
  ): Promise<void> {
    await pipelinesApi.bulkUpdateRecords(pipelineId, {
      record_ids: recordIds,
      data
    })
  }

  /**
   * Bulk delete multiple records
   */
  static async bulkDeleteRecords(pipelineId: string, recordIds: string[]): Promise<void> {
    await pipelinesApi.bulkDeleteRecords(pipelineId, {
      record_ids: recordIds
    })
  }

  /**
   * Export records in specified format
   */
  static async exportRecords(
    pipelineId: string, 
    format: 'csv' | 'json' | 'excel',
    filters?: Filter[],
    search?: string
  ): Promise<Blob> {
    const params: any = { format }
    
    if (search?.trim()) {
      params.search = search.trim()
    }

    if (filters && filters.length > 0) {
      filters.forEach((filter, index) => {
        params[`filter_${index}_field`] = filter.field
        params[`filter_${index}_operator`] = filter.operator
        params[`filter_${index}_value`] = filter.value
      })
    }

    const response = await pipelinesApi.exportRecords(pipelineId, format, params)
    return response.data
  }

  /**
   * Fetch available users for user field options
   */
  static async fetchUsers(): Promise<Array<{value: string, label: string}>> {
    const response = await usersApi.list()
    const users = response.data.results || response.data || []
    
    return users.map((user: any) => ({
      value: user.id.toString(),
      label: `${user.first_name || ''} ${user.last_name || ''}`.trim() || 
             user.email || 
             user.username || 
             `User ${user.id}`
    }))
  }

  /**
   * Extract unique tags from records for tag field options
   */
  static async fetchTagOptions(pipelineId: string, fieldName: string): Promise<Array<{value: string, label: string}>> {
    const response = await pipelinesApi.getRecords(pipelineId, { 
      limit: 500,
      page_size: 500
    })
    
    const uniqueTags = new Set<string>()
    
    if (response.data.results) {
      response.data.results.forEach((record: any) => {
        const topLevelTags = record.tags
        const fieldTags = record.data?.[fieldName]
        const tagsToProcess = fieldTags || topLevelTags
        
        if (tagsToProcess && Array.isArray(tagsToProcess)) {
          tagsToProcess.forEach((tag: string) => {
            if (tag && tag.trim()) {
              uniqueTags.add(tag.trim())
            }
          })
        }
      })
    }
    
    return Array.from(uniqueTags).sort().map(tag => ({ value: tag, label: tag }))
  }

  /**
   * Fetch relation field options from target pipeline
   */
  static async fetchRelationOptions(
    targetPipelineId: string, 
    displayFieldSlug: string
  ): Promise<Array<{value: string, label: string}>> {
    const response = await pipelinesApi.getRecords(targetPipelineId, { limit: 200 })
    
    if (!response.data.results) {
      return []
    }

    return response.data.results.map((record: any) => {
      let label: string | null = null
      
      // Use configured display field
      if (displayFieldSlug && record.data?.[displayFieldSlug]) {
        label = record.data[displayFieldSlug]
      }
      // Fallback to common field names
      else {
        label = record.data?.name || 
               record.data?.title || 
               record.data?.company_name ||
               record.data?.first_name || 
               record.data?.email ||
               record.title
      }
      
      // Use first non-empty field if still no label
      if (!label && record.data) {
        const dataValues = Object.values(record.data).filter(v => v && String(v).trim())
        if (dataValues.length > 0) {
          label = String(dataValues[0])
        }
      }
      
      // Final fallback
      if (!label) {
        label = `Record ${record.id}`
      }
      
      return {
        value: record.id.toString(),
        label
      }
    })
  }
}