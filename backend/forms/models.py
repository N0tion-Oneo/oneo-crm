from django.db import models
from django.contrib.auth import get_user_model
from django_tenants.models import TenantMixin
from pipelines.models import Pipeline, Field, Record
from tenants.models import Tenant

User = get_user_model()


class ValidationRule(models.Model):
    """Simple validation rule definition for basic field validation"""
    
    RULE_TYPE_CHOICES = [
        ('required', 'Required Field'),
        ('min_length', 'Minimum Length'),
        ('max_length', 'Maximum Length'),
        ('min_value', 'Minimum Value'),
        ('max_value', 'Maximum Value'),
        ('regex', 'Regular Expression'),
        ('email', 'Email Format'),
        ('phone', 'Phone Format'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='validation_rules')
    name = models.CharField(max_length=255, help_text="Human-readable name for this validation rule")
    description = models.TextField(blank=True, help_text="Description of what this rule validates")
    rule_type = models.CharField(max_length=50, choices=RULE_TYPE_CHOICES)
    configuration = models.JSONField(
        default=dict,
        help_text="Rule-specific configuration (e.g., regex pattern, min/max values, etc.)"
    )
    error_message = models.TextField(help_text="Error message to show when validation fails")
    warning_message = models.TextField(
        blank=True,
        help_text="Optional warning message for non-blocking validation"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['tenant', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.rule_type})"


class FormTemplate(models.Model):
    """Simple form template that connects to pipelines"""
    
    FORM_TYPE_CHOICES = [
        ('dynamic', 'Dynamic Form'),
        ('custom', 'Custom Form'),
    ]
    
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='form_templates')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name='form_templates')
    form_type = models.CharField(max_length=50, choices=FORM_TYPE_CHOICES, default='full')
    # Dynamic form configuration
    dynamic_mode = models.CharField(
        max_length=20,
        choices=[
            ('all', 'All Fields'),
            ('stage', 'Stage-Specific Fields'),
            ('visible', 'Visible Fields Only'),
        ],
        blank=True,
        null=True,
        help_text="For dynamic forms, which generation mode to use"
    )
    target_stage = models.CharField(
        max_length=100, 
        blank=True,
        help_text="For stage-specific dynamic forms, which stage to target"
    )
    success_message = models.TextField(
        blank=True,
        help_text="Message to show after successful form submission"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['tenant', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.pipeline.name})"


class FormFieldConfiguration(models.Model):
    """Enhanced field configuration within a form with validation support"""
    
    form_template = models.ForeignKey(
        FormTemplate, 
        related_name='field_configs', 
        on_delete=models.CASCADE
    )
    pipeline_field = models.ForeignKey(Field, on_delete=models.CASCADE)
    display_order = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    is_readonly = models.BooleanField(default=False)
    custom_label = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Override the default field label"
    )
    custom_placeholder = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Custom placeholder text for input fields"
    )
    custom_help_text = models.TextField(
        blank=True,
        help_text="Custom help text to display with the field"
    )
    conditional_logic = models.JSONField(
        default=dict,
        help_text="Show/hide conditions based on other field values"
    )
    default_value = models.JSONField(
        null=True,
        blank=True,
        help_text="Default value for this field in the form"
    )
    field_width = models.CharField(
        max_length=20,
        choices=[
            ('full', 'Full Width'),
            ('half', 'Half Width'),
            ('third', 'One Third'),
            ('quarter', 'One Quarter'),
        ],
        default='full',
        help_text="Field width in the form layout"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order']
        unique_together = ['form_template', 'pipeline_field']
    
    def __str__(self):
        return f"{self.form_template.name} - {self.pipeline_field.name}"


class FormFieldValidation(models.Model):
    """Links validation rules to form fields with execution order"""
    
    form_field_config = models.ForeignKey(
        FormFieldConfiguration, 
        related_name='validations',
        on_delete=models.CASCADE
    )
    validation_rule = models.ForeignKey(ValidationRule, on_delete=models.CASCADE)
    execution_order = models.IntegerField(
        default=0,
        help_text="Order in which to execute this validation rule"
    )
    is_active = models.BooleanField(default=True)
    conditional_logic = models.JSONField(
        default=dict,
        help_text="Conditions under which to apply this validation rule"
    )
    override_message = models.TextField(
        blank=True,
        help_text="Override the default validation rule message for this field"
    )
    is_blocking = models.BooleanField(
        default=True,
        help_text="Whether this validation failure should block form submission"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['execution_order']
        unique_together = ['form_field_config', 'validation_rule']
    
    def __str__(self):
        return f"{self.form_field_config.pipeline_field.name} - {self.validation_rule.name}"


class FormSubmission(models.Model):
    """Track form submissions for analytics and auditing"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Validation'),
        ('valid', 'Valid Submission'),
        ('invalid', 'Invalid Submission'),
        ('duplicate', 'Duplicate Detected'),
        ('merged', 'Merged with Existing'),
    ]
    
    form_template = models.ForeignKey(FormTemplate, on_delete=models.CASCADE)
    record = models.ForeignKey(
        Record, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="The record created/updated by this submission"
    )
    submitted_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="User who submitted the form (null for anonymous submissions)"
    )
    submission_data = models.JSONField(help_text="The actual form data submitted")
    validation_results = models.JSONField(
        default=dict,
        help_text="Results of validation checks"
    )
    duplicate_matches = models.JSONField(
        default=list,
        help_text="Any duplicate matches found during validation"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referrer = models.URLField(blank=True)
    session_id = models.CharField(max_length=255, blank=True)
    submission_time_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Time taken to submit form in milliseconds"
    )
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.form_template.name} - {self.submitted_at.strftime('%Y-%m-%d %H:%M')}"


class FormAnalytics(models.Model):
    """Analytics data for form performance tracking"""
    
    form_template = models.ForeignKey(FormTemplate, on_delete=models.CASCADE)
    date = models.DateField()
    views = models.IntegerField(default=0)
    submissions = models.IntegerField(default=0)
    valid_submissions = models.IntegerField(default=0)
    invalid_submissions = models.IntegerField(default=0)
    duplicate_submissions = models.IntegerField(default=0)
    abandonment_rate = models.FloatField(default=0.0)
    avg_completion_time_ms = models.IntegerField(default=0)
    field_errors = models.JSONField(
        default=dict,
        help_text="Count of validation errors by field"
    )
    
    class Meta:
        unique_together = ['form_template', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.form_template.name} - {self.date}"