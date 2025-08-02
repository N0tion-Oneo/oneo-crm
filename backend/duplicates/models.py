from django.db import models
from django.contrib.auth import get_user_model
from pipelines.models import Pipeline, Field, Record
from tenants.models import Tenant

User = get_user_model()


class DuplicateRule(models.Model):
    """Tenant-configurable duplicate detection rules with comprehensive matching"""
    
    ACTION_CHOICES = [
        ('block', 'Block Creation'),
        ('warn', 'Show Warning'),
        ('merge_prompt', 'Prompt to Merge'),
        ('auto_merge', 'Auto-Merge'),
        ('allow', 'Allow with Flag'),
    ]
    
    # Multi-tenant isolation - CRITICAL for tenant data separation
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='duplicate_rules')
    name = models.CharField(max_length=255, help_text="Human-readable name for this duplicate rule")
    description = models.TextField(blank=True, help_text="Description of what this rule detects")
    pipeline = models.ForeignKey(
        Pipeline, 
        on_delete=models.CASCADE, 
        related_name='duplicate_rules',
        help_text="Pipeline this rule applies to"
    )
    is_active = models.BooleanField(default=True)
    action_on_duplicate = models.CharField(
        max_length=50, 
        choices=ACTION_CHOICES,
        default='warn',
        help_text="Action to take when duplicates are detected"
    )
    confidence_threshold = models.FloatField(
        default=0.8,
        help_text="Minimum confidence score (0.0-1.0) to consider records as duplicates"
    )
    auto_merge_threshold = models.FloatField(
        default=0.95,
        help_text="Confidence threshold for automatic merging (if enabled)"
    )
    enable_fuzzy_matching = models.BooleanField(
        default=True,
        help_text="Enable fuzzy text matching algorithms"
    )
    enable_phonetic_matching = models.BooleanField(
        default=True,
        help_text="Enable phonetic matching for names (Soundex, Metaphone)"
    )
    ignore_case = models.BooleanField(
        default=True,
        help_text="Ignore case when comparing text fields"
    )
    normalize_whitespace = models.BooleanField(
        default=True,
        help_text="Normalize whitespace and trim fields before comparison"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        # Ensure tenant isolation at database level
        unique_together = ['tenant', 'name']
        ordering = ['name']
        indexes = [
            models.Index(fields=['tenant', 'pipeline']),
            models.Index(fields=['tenant', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.tenant.name} - {self.name} ({self.pipeline.name})"


class DuplicateFieldRule(models.Model):
    """Individual field matching rules within a duplicate detection rule"""
    
    MATCH_TYPE_CHOICES = [
        ('exact', 'Exact Match'),
        ('case_insensitive', 'Case Insensitive'),
        ('fuzzy', 'Fuzzy Match'),
        ('soundex', 'Soundex Match'),
        ('metaphone', 'Metaphone Match'),
        ('levenshtein', 'Levenshtein Distance'),
        ('jaro_winkler', 'Jaro-Winkler Similarity'),
        ('email_domain', 'Email Domain Match'),
        ('phone_normalized', 'Normalized Phone Match'),
        ('partial', 'Partial Match'),
        ('regex', 'Regular Expression Match'),
        ('cosine', 'Cosine Similarity'),
        ('jaccard', 'Jaccard Similarity'),
    ]
    
    duplicate_rule = models.ForeignKey(
        DuplicateRule, 
        related_name='field_rules', 
        on_delete=models.CASCADE
    )
    field = models.ForeignKey(
        Field, 
        on_delete=models.CASCADE,
        help_text="Pipeline field to use for duplicate detection"
    )
    match_type = models.CharField(max_length=50, choices=MATCH_TYPE_CHOICES)
    match_threshold = models.FloatField(
        default=0.8,
        help_text="Threshold for fuzzy matching (0.0-1.0, higher = more strict)"
    )
    weight = models.FloatField(
        default=1.0,
        help_text="Weight of this field in overall duplicate score calculation"
    )
    is_required = models.BooleanField(
        default=False,
        help_text="Whether this field must match for records to be considered duplicates"
    )
    preprocessing_rules = models.JSONField(
        default=dict,
        help_text="Field-specific preprocessing rules (normalization, cleanup, etc.)"
    )
    custom_regex = models.TextField(
        blank=True,
        help_text="Custom regex pattern for regex match type"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-weight', 'field__name']
        unique_together = ['duplicate_rule', 'field']
        indexes = [
            models.Index(fields=['duplicate_rule', 'is_active']),
            models.Index(fields=['field', 'match_type']),
        ]
    
    def __str__(self):
        return f"{self.duplicate_rule.name} - {self.field.name} ({self.match_type})"


class DuplicateMatch(models.Model):
    """Track detected duplicate matches between records"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('confirmed', 'Confirmed Duplicate'),
        ('false_positive', 'False Positive'),
        ('merged', 'Records Merged'),
        ('ignored', 'Ignored'),
        ('auto_resolved', 'Auto-Resolved'),
    ]
    
    # Multi-tenant isolation - CRITICAL for tenant data separation
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='duplicate_matches')
    rule = models.ForeignKey(DuplicateRule, on_delete=models.CASCADE, related_name='matches')
    record1 = models.ForeignKey(
        Record, 
        related_name='duplicate_matches_1', 
        on_delete=models.CASCADE,
        help_text="First record in the duplicate pair"
    )
    record2 = models.ForeignKey(
        Record, 
        related_name='duplicate_matches_2', 
        on_delete=models.CASCADE,
        help_text="Second record in the duplicate pair"
    )
    confidence_score = models.FloatField(
        help_text="Overall confidence score (0.0-1.0) for this duplicate match"
    )
    field_scores = models.JSONField(
        help_text="Individual field match scores and details"
    )
    matched_fields = models.JSONField(
        help_text="List of fields that contributed to the match"
    )
    detection_method = models.CharField(
        max_length=100,
        help_text="Primary algorithm used for detection"
    )
    detected_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        User, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='reviewed_duplicates'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    resolution_notes = models.TextField(
        blank=True,
        help_text="Notes about how this duplicate was resolved"
    )
    auto_resolution_reason = models.TextField(
        blank=True,
        help_text="Reason for automatic resolution (if applicable)"
    )
    
    class Meta:
        ordering = ['-detected_at']
        unique_together = ['tenant', 'record1', 'record2', 'rule']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'detected_at']),
            models.Index(fields=['rule', 'confidence_score']),
            models.Index(fields=['record1', 'record2']),
        ]
    
    def __str__(self):
        return f"{self.tenant.name} - Duplicate: {self.record1.id} & {self.record2.id} ({self.confidence_score:.2f})"


class DuplicateResolution(models.Model):
    """Track resolution actions taken for duplicate matches"""
    
    ACTION_CHOICES = [
        ('merge', 'Merged Records'),
        ('keep_both', 'Keep Both Records'),
        ('delete_duplicate', 'Deleted Duplicate'),
        ('mark_false_positive', 'Marked as False Positive'),
        ('update_primary', 'Updated Primary Record'),
        ('create_relationship', 'Created Relationship'),
    ]
    
    # Multi-tenant isolation - CRITICAL for tenant data separation
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='duplicate_resolutions')
    duplicate_match = models.ForeignKey(
        DuplicateMatch, 
        on_delete=models.CASCADE, 
        related_name='resolutions'
    )
    action_taken = models.CharField(max_length=50, choices=ACTION_CHOICES)
    primary_record = models.ForeignKey(
        Record,
        on_delete=models.CASCADE,
        related_name='primary_resolutions',
        help_text="The record chosen as primary in merge operations"
    )
    merged_record = models.ForeignKey(
        Record,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='merged_resolutions',
        help_text="The record that was merged/deleted"
    )
    data_changes = models.JSONField(
        default=dict,
        help_text="Details of data changes made during resolution"
    )
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolved_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-resolved_at']
        indexes = [
            models.Index(fields=['tenant', 'resolved_at']),
            models.Index(fields=['duplicate_match', 'action_taken']),
        ]
    
    def __str__(self):
        return f"{self.tenant.name} - {self.action_taken} - {self.resolved_at.strftime('%Y-%m-%d')}"


class DuplicateAnalytics(models.Model):
    """Analytics data for duplicate detection performance"""
    
    # Multi-tenant isolation - CRITICAL for tenant data separation
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='duplicate_analytics')
    rule = models.ForeignKey(DuplicateRule, on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField()
    records_processed = models.IntegerField(default=0)
    duplicates_detected = models.IntegerField(default=0)
    false_positives = models.IntegerField(default=0)
    true_positives = models.IntegerField(default=0)
    avg_confidence_score = models.FloatField(default=0.0)
    processing_time_ms = models.IntegerField(default=0)
    field_performance = models.JSONField(
        default=dict,
        help_text="Performance metrics by field"
    )
    algorithm_performance = models.JSONField(
        default=dict,
        help_text="Performance metrics by algorithm"
    )
    
    class Meta:
        unique_together = ['tenant', 'rule', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['tenant', 'date']),
            models.Index(fields=['rule', 'date']),
        ]
    
    def __str__(self):
        return f"{self.tenant.name} - {self.rule.name} - {self.date}"


class DuplicateExclusion(models.Model):
    """Explicitly exclude certain record pairs from duplicate detection"""
    
    # Multi-tenant isolation - CRITICAL for tenant data separation
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='duplicate_exclusions')
    record1 = models.ForeignKey(Record, related_name='exclusions_1', on_delete=models.CASCADE)
    record2 = models.ForeignKey(Record, related_name='exclusions_2', on_delete=models.CASCADE)
    rule = models.ForeignKey(
        DuplicateRule, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="Specific rule to exclude, or null for all rules"
    )
    reason = models.TextField(help_text="Reason for excluding this pair")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['tenant', 'record1', 'record2', 'rule']
        indexes = [
            models.Index(fields=['tenant', 'record1']),
            models.Index(fields=['tenant', 'record2']),
        ]
    
    def __str__(self):
        return f"{self.tenant.name} - Excluded: {self.record1.id} & {self.record2.id}"