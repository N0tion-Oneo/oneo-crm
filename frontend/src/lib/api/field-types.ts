import { api } from '../api'

export interface FieldTypeConfig {
  key: string
  label: string
  description: string
  category: 'basic' | 'selection' | 'datetime' | 'advanced' | 'system'
  icon: string
  config_schema: any
  supports_validation: boolean
  is_computed: boolean
  config_class: string
}

export interface FieldTypesResponse {
  basic: FieldTypeConfig[]
  selection: FieldTypeConfig[]
  datetime: FieldTypeConfig[]
  advanced: FieldTypeConfig[]
  system: FieldTypeConfig[]
}

export interface Currency {
  code: string
  name: string
  symbol: string
}

export interface Country {
  code: string
  name: string
  phone_code: string
}

export interface OpenAIModel {
  key: string
  name: string
  description: string
  cost_tier: 'budget' | 'standard' | 'premium'
  capabilities: string[]
  recommended_for: string[]
}

export interface RecordDataOption {
  key: string
  label: string
  description: string
}

export interface RecordDataOptions {
  timestamp: RecordDataOption[]
  user: RecordDataOption[]
  count: RecordDataOption[]
  duration: RecordDataOption[]
  status: RecordDataOption[]
}

export interface GlobalOptions {
  currencies: Currency[]
  countries: Country[]  
  openai_models: OpenAIModel[]
  record_data_options: RecordDataOptions
}

export const fieldTypesApi = {
  // Get all field types grouped by category
  getAll: () => api.get<FieldTypesResponse>('/api/field-types/'),
  
  // Get specific field type details
  get: (fieldType: string) => api.get<FieldTypeConfig>(`/api/field-types/${fieldType}/`),
  
  // Get configuration schema for field type
  getConfigSchema: (fieldType: string) => api.get(`/api/field-types/${fieldType}/config_schema/`),
  
  // Get field type categories
  getCategories: () => api.get('/api/field-types/categories/'),
}

export const globalOptionsApi = {
  // Get all global options
  getAll: () => api.get<GlobalOptions>('/api/global-options/'),
  
  // Get currencies
  getCurrencies: () => api.get<Currency[]>('/api/global-options/currencies/'),
  
  // Get countries  
  getCountries: () => api.get<Country[]>('/api/global-options/countries/'),
  
  // Get OpenAI models
  getOpenAIModels: () => api.get<OpenAIModel[]>('/api/global-options/openai_models/'),
  
  // Get record data options
  getRecordDataOptions: () => api.get<RecordDataOptions>('/api/global-options/record_data_options/'),
}