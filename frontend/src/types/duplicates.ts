// Duplicates Detection Types

export interface DuplicateRule {
  id: number
  name: string
  description?: string
  pipeline: number | string // Can be ID or slug
  is_active: boolean
  action_on_duplicate: 'block' | 'warn' | 'merge_prompt' | 'auto_merge' | 'allow'
  confidence_threshold: number
  auto_merge_threshold: number
  enable_fuzzy_matching: boolean
  enable_phonetic_matching: boolean
  ignore_case: boolean
  normalize_whitespace: boolean
  field_rules?: DuplicateFieldRule[]
  created_at: string
  updated_at: string
}

export interface DuplicateFieldRule {
  id: number
  duplicate_rule: number
  field: number | string // Can be ID or slug
  match_type: 'exact' | 'case_insensitive' | 'fuzzy' | 'soundex' | 'metaphone' | 'levenshtein' | 'jaro_winkler' | 'email_domain' | 'phone_normalized' | 'partial' | 'regex' | 'cosine' | 'jaccard'
  match_threshold: number
  weight: number
  is_required: boolean
  preprocessing_rules: Record<string, any>
  custom_regex?: string
  is_active: boolean
  created_at: string
}

export interface DuplicateMatch {
  id: number
  rule: DuplicateRule
  record1: number | string
  record2: number | string
  confidence_score: number
  field_scores: Record<string, any>
  matched_fields: string[]
  detection_method: string
  detected_at: string
  reviewed_by?: number
  reviewed_at?: string
  status: 'pending' | 'confirmed' | 'false_positive' | 'merged' | 'ignored' | 'auto_resolved'
  resolution_notes?: string
  auto_resolution_reason?: string
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
  pipeline_id: number
  confidence_threshold?: number
  action_on_duplicate?: 'block' | 'warn' | 'merge_prompt' | 'auto_merge' | 'allow'
  enable_fuzzy_matching?: boolean
  enable_phonetic_matching?: boolean
  field_rules: Omit<DuplicateFieldRule, 'id' | 'duplicate_rule' | 'created_at'>[]
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