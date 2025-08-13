// Duplicates Detection Types

export interface DuplicateRule {
  id: number
  name: string
  description?: string
  pipeline: number | string // Can be ID or slug
  logic: any // JSON field for AND/OR logic structure
  action_on_duplicate: 'detect_only' | 'disabled'
  is_active: boolean
  created_at: string
  updated_at: string
  created_by?: number
  tenant?: number
}

export interface DuplicateFieldRule {
  id: number
  duplicate_rule: number
  field: number | string // Can be ID or slug
  match_type: 'exact' | 'case_insensitive' | 'fuzzy' | 'soundex' | 'metaphone' | 'levenshtein' | 'jaro_winkler' | 'email_domain' | 'phone_normalized' | 'partial' | 'regex' | 'cosine' | 'jaccard' | 'url_normalized'
  match_threshold: number
  weight: number
  is_required: boolean
  preprocessing_rules: Record<string, any>
  custom_regex?: string
  url_extraction_rules?: 'all' | number[] // Field-specific URL extraction rules
  is_active: boolean
  created_at: string
}

export interface DuplicateMatch {
  id: number
  rule: DuplicateRule | number // Can be full object or just ID
  record1: number | string
  record2: number | string
  confidence_score: number
  field_scores: Record<string, any> // JSON field for detailed match info
  matched_fields: string[]
  detection_method: string
  detected_at: string
  reviewed_by?: number
  reviewed_at?: string
  status: 'pending' | 'merged' | 'kept_both' | 'ignored' | 'needs_review' | 'resolved'
  resolution_notes?: string
  auto_resolution_reason?: string
  tenant?: number
}

export interface DuplicateResolution {
  id: number
  duplicate_match: DuplicateMatch
  action_taken: 'merge' | 'keep_both' | 'delete_duplicate' | 'mark_false_positive' | 'update_primary' | 'create_relationship'
  primary_record: number | string
  merged_record?: number | string
  data_changes: Record<string, any>
  resolved_by?: number
  resolved_at: string
  notes?: string
}

export interface DuplicateAnalytics {
  id: number
  rule: DuplicateRule
  date: string
  records_processed: number
  duplicates_detected: number
  false_positives: number
  true_positives: number
  avg_confidence_score: number
  processing_time_ms: number
  detection_rate: number
  precision: number
  field_performance: Record<string, any>
  algorithm_performance: Record<string, any>
}

export interface DuplicateExclusion {
  id: number
  record1: number | string
  record2: number | string
  rule?: DuplicateRule
  reason: string
  created_by?: number
  created_at: string
}

// Request/Response types
export interface DuplicateDetectionRequest {
  record_data: Record<string, any>
  pipeline_id: number
  exclude_record_id?: string
  rule_id?: number
  confidence_threshold?: number
}

export interface DuplicateComparisonRequest {
  record1_id: string
  record2_id: string
  rule_id?: number
}

export interface DuplicateBulkResolutionRequest {
  match_ids: number[]
  action: 'merge' | 'keep_both' | 'delete_duplicate' | 'mark_false_positive' | 'update_primary' | 'create_relationship'
  notes?: string
}

export interface DuplicateRuleBuilderRequest {
  name: string
  description?: string
  pipeline: number
  logic: any // JSON field for AND/OR logic structure
  action_on_duplicate?: 'detect_only' | 'disabled'
  is_active?: boolean
}

export interface DuplicateMatchResult {
  record_id: string
  record_data: Record<string, any>
  overall_score: number
  field_matches: any[]
  confidence_breakdown: Record<string, any>
}

export interface DuplicateStatistics {
  total_rules: number
  active_rules: number
  total_matches: number
  pending_matches: number
  resolved_matches: number
  false_positives: number
  avg_confidence_score: number
  processing_time_stats: Record<string, any>
  top_performing_rules: any[]
  field_performance: Record<string, any>
}

export interface MergeDecision {
  source: 'left' | 'right' | 'custom'
  value?: any
}

export interface MergeRequest {
  match_id: number
  primary_record_id: number
  field_decisions: Record<string, MergeDecision>
  notes?: string
}

export interface DuplicateCountResponse {
  record_id: string
  duplicate_count: number
  has_duplicates: boolean
}