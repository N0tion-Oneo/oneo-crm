"""
Unified duplicate detection models with standardized naming
"""
from django.db import models
from django.contrib.auth import get_user_model
from pipelines.models import Pipeline, Field, Record
from tenants.models import Tenant

User = get_user_model()


class URLExtractionRule(models.Model):
    """Configurable URL extraction patterns for duplicate detection"""
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='duplicate_url_extraction_rules')
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name='url_extraction_rules', help_text="Pipeline this URL extraction rule applies to")
    name = models.CharField(max_length=255, help_text="Human-readable name (e.g., 'LinkedIn Profile')")
    description = models.TextField(blank=True, help_text="Description of what this rule extracts")
    
    # URL pattern configuration
    domain_patterns = models.JSONField(
        default=list,
        help_text="List of domain patterns to match (e.g., ['linkedin.com', '*.linkedin.com'])"
    )
    extraction_pattern = models.CharField(
        max_length=500,
        help_text="Regex pattern to extract identifier from URL"
    )
    extraction_format = models.CharField(
        max_length=100,
        help_text="Format template for extracted value (e.g., 'linkedin:{}')"
    )
    
    # Normalization options
    case_sensitive = models.BooleanField(default=False)
    remove_protocol = models.BooleanField(default=True)
    remove_www = models.BooleanField(default=True)
    remove_query_params = models.BooleanField(default=True)
    remove_fragments = models.BooleanField(default=True)
    strip_subdomains = models.BooleanField(default=False, help_text="Strip all subdomains to keep only main domain (e.g., blog.apple.com → apple.com)")
    normalization_steps = models.JSONField(
        default=list, 
        blank=True,
        help_text="Visual normalization steps configuration"
    )
    template_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Template type used to create this rule (e.g., 'linkedin', 'domain', 'custom')"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['pipeline', 'name']
        ordering = ['name']
        indexes = [
            models.Index(fields=['tenant', 'pipeline']),
            models.Index(fields=['pipeline', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.pipeline.name} - {self.name}"


class DuplicateRule(models.Model):
    """Duplicate detection rule with AND/OR logic"""
    
    ACTION_CHOICES = [
        ('detect_only', 'Detect and Store Matches'),
        ('disabled', 'Disable Detection'),
    ]
    
    # Multi-tenant isolation
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='duplicate_rules')
    name = models.CharField(max_length=255, help_text="Human-readable name for this duplicate rule")
    description = models.TextField(blank=True, help_text="Description of what this rule detects")
    pipeline = models.ForeignKey(
        Pipeline, 
        on_delete=models.CASCADE, 
        related_name='duplicate_rules',
        help_text="Pipeline this rule applies to"
    )
    
    # Boolean logic stored as JSON
    logic = models.JSONField(
        help_text="AND/OR logic for field matching in JSON format",
        default=dict
    )
    
    # Simple action configuration
    action_on_duplicate = models.CharField(
        max_length=50, 
        choices=ACTION_CHOICES,
        default='detect_only',
        help_text="Action to take when duplicates are detected"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['tenant', 'name']
        ordering = ['name']
        indexes = [
            models.Index(fields=['tenant', 'pipeline']),
            models.Index(fields=['tenant', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.tenant.name} - {self.name} ({self.pipeline.name})"


class DuplicateRuleTest(models.Model):
    """Test cases for duplicate rules"""
    
    rule = models.ForeignKey(DuplicateRule, on_delete=models.CASCADE, related_name='duplicate_test_cases')
    name = models.CharField(max_length=255, help_text="Test case name")
    
    # Test data
    record1_data = models.JSONField(help_text="First record data for testing")
    record2_data = models.JSONField(help_text="Second record data for testing")
    expected_result = models.BooleanField(help_text="Expected duplicate detection result")
    
    # Test results
    last_test_result = models.BooleanField(null=True, blank=True)
    last_test_at = models.DateTimeField(null=True, blank=True)
    test_details = models.JSONField(default=dict, help_text="Detailed test execution results")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['rule', 'name']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.rule.name} - {self.name}"


class DuplicateDetectionResult(models.Model):
    """Results of duplicate detection process"""
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='duplicate_detection_results')
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name='duplicate_detection_results')
    record = models.ForeignKey(Record, on_delete=models.CASCADE, related_name='duplicate_detection_results')
    
    # Detection summary
    total_duplicates_found = models.IntegerField(default=0)
    detection_summary = models.JSONField(
        default=dict,
        help_text="Summary of detection results including rules triggered and matched records"
    )
    duplicate_match_ids = models.JSONField(
        default=list,
        help_text="List of DuplicateMatch IDs created from this detection"
    )
    
    # Status flags
    requires_review = models.BooleanField(default=False)
    is_processed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'pipeline']),
            models.Index(fields=['tenant', 'requires_review']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.record} - {self.total_duplicates_found} duplicates found"


class DuplicateMatch(models.Model):
    """Track detected duplicate matches between records"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('merged', 'Records Merged'),
        ('kept_both', 'Kept Both Records'),
        ('ignored', 'Marked as False Positive'),
        ('needs_review', 'Flagged for Team Review'),
        ('resolved', 'Resolved'),
    ]
    
    # Multi-tenant isolation - CRITICAL for tenant data separation
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='duplicate_matches')
    rule = models.ForeignKey(DuplicateRule, on_delete=models.CASCADE, related_name='duplicate_matches')
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
    resolution_notes = models.TextField(blank=True)
    auto_resolution_reason = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['tenant', 'record1', 'record2']
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'detected_at']),
            models.Index(fields=['confidence_score']),
        ]
    
    def __str__(self):
        return f"Duplicate: {self.record1.id} <-> {self.record2.id} ({self.confidence_score:.2f})"


class DuplicateResolution(models.Model):
    """Track resolutions applied to duplicate matches"""
    
    ACTION_CHOICES = [
        ('merge', 'Merge Records'),
        ('keep_both', 'Keep Both Records'),
        ('ignore', 'Mark as False Positive'),
        ('manual_review', 'Requires Manual Review'),
        ('rollback', 'Rollback Resolution'),
    ]
    
    # Multi-tenant isolation
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='duplicate_resolutions')
    duplicate_match = models.ForeignKey(
        DuplicateMatch, 
        on_delete=models.CASCADE, 
        related_name='resolutions'
    )
    action_taken = models.CharField(max_length=50, choices=ACTION_CHOICES)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolved_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    # Resolution details
    primary_record = models.ForeignKey(
        Record, 
        related_name='primary_resolutions', 
        on_delete=models.CASCADE,
        null=True, 
        blank=True
    )
    merged_record = models.ForeignKey(
        Record, 
        related_name='merged_resolutions', 
        on_delete=models.CASCADE,
        null=True, 
        blank=True
    )
    data_changes = models.JSONField(
        default=dict,
        help_text="Record of data changes made during resolution"
    )
    
    class Meta:
        ordering = ['-resolved_at']
        indexes = [
            models.Index(fields=['tenant', 'action_taken']),
            models.Index(fields=['resolved_at']),
        ]
    
    def __str__(self):
        return f"Resolution: {self.action_taken} for {self.duplicate_match}"


class DuplicateAnalytics(models.Model):
    """Analytics data for duplicate detection performance"""
    
    # Multi-tenant isolation - CRITICAL for tenant data separation
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='duplicate_analytics')
    rule = models.ForeignKey(DuplicateRule, on_delete=models.CASCADE, related_name='duplicate_analytics')
    date = models.DateField()
    records_processed = models.IntegerField(default=0)
    duplicates_detected = models.IntegerField(default=0)
    false_positives = models.IntegerField(default=0)
    true_positives = models.IntegerField(default=0)
    avg_confidence_score = models.FloatField(default=0.0)
    processing_time_ms = models.IntegerField(default=0)
    
    # Performance breakdowns
    field_performance = models.JSONField(
        default=dict,
        help_text="Performance metrics by field"
    )
    algorithm_performance = models.JSONField(
        default=dict,
        help_text="Performance metrics by matching algorithm"
    )
    
    class Meta:
        unique_together = ['tenant', 'rule', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['tenant', 'date']),
            models.Index(fields=['rule', 'date']),
        ]
    
    def __str__(self):
        return f"{self.rule.name} - {self.date} ({self.duplicates_detected} duplicates)"


class DuplicateExclusion(models.Model):
    """Track manually excluded record pairs that should never be considered duplicates"""
    
    # Multi-tenant isolation
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='duplicate_exclusions')
    record1 = models.ForeignKey(Record, related_name='exclusions_1', on_delete=models.CASCADE)
    record2 = models.ForeignKey(Record, related_name='exclusions_2', on_delete=models.CASCADE)
    reason = models.TextField(help_text="Reason for excluding this pair from duplicate detection")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['tenant', 'record1', 'record2']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'record1']),
            models.Index(fields=['tenant', 'record2']),
        ]
    
    def __str__(self):
        return f"Exclusion: {self.record1.id} <-> {self.record2.id}"