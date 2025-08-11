"""
Unified Record Validation System
Consolidates all record-level validation logic from Pipeline model
"""
import logging
import asyncio
from typing import Dict, Any, List, Tuple, Optional
from django.db import models, connection
from django.utils import timezone

logger = logging.getLogger(__name__)


class RecordValidationResult:
    """Standardized record validation result"""
    
    def __init__(self, is_valid: bool = True, cleaned_data: Dict[str, Any] = None, 
                 errors: Dict[str, Any] = None, warnings: List[str] = None, 
                 metadata: Dict[str, Any] = None):
        self.is_valid = is_valid
        self.cleaned_data = cleaned_data or {}
        self.errors = errors or {}
        self.warnings = warnings or []
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'is_valid': self.is_valid,
            'cleaned_data': self.cleaned_data,
            'errors': self.errors,
            'warnings': self.warnings,
            'metadata': self.metadata
        }


class RecordValidator:
    """
    Unified record validation system (moved from Pipeline model)
    Handles all record-level validation operations with optimization
    """
    
    def __init__(self, pipeline):
        """
        Initialize validator for a specific pipeline
        
        Args:
            pipeline: Pipeline model instance
        """
        self.pipeline = pipeline
        self.logger = logging.getLogger(__name__)
    
    # =============================================================================
    # MAIN VALIDATION METHODS - Moved from Pipeline model
    # =============================================================================
    
    def validate_record_data(self, data: Dict[str, Any], context: str = 'storage') -> Dict[str, Any]:
        """
        Validate record data against pipeline schema (moved from Pipeline.validate_record_data)
        
        Args:
            data: Record data to validate
            context: Validation context ('storage', 'form', 'business_rules', 'migration')
            
        Returns:
            Dict with validation results
        """
        field_definitions = []
        for field in self.pipeline.fields.all():
            field_definitions.append({
                'slug': field.slug,
                'field_type': field.field_type,
                'field_config': field.field_config,
                'storage_constraints': field.storage_constraints,
                'business_rules': field.business_rules,
                'ai_config': field.ai_config if field.is_ai_field else {},
                'pipeline_id': self.pipeline.id,  # Add pipeline context for USER field validation
            })
        
        # Import and use existing validation function
        from . import validate_record_data
        return validate_record_data(field_definitions, data, context)
    
    def validate_stage_transition(self, record_data: Dict[str, Any], target_stage: str) -> Tuple[bool, List[str]]:
        """
        Validate if record can transition to target stage (moved from Pipeline.validate_stage_transition)
        
        Args:
            record_data: Record data dictionary
            target_stage: Target stage to validate against
            
        Returns:
            Tuple of (is_valid, error_list)
        """
        errors = []
        
        for field in self.pipeline.fields.all():
            is_valid, field_errors = field.check_business_rules(record_data, target_stage)
            if not is_valid:
                errors.extend(field_errors)
        
        return len(errors) == 0, errors
    
    def validate_record_data_optimized(self, data: Dict[str, Any], context: str = 'storage', 
                                     changed_field_slug: Optional[str] = None) -> Dict[str, Any]:
        """
        Optimized validation with dependency tracking (moved from Pipeline.validate_record_data_optimized)
        
        Args:
            data: Record data to validate
            context: Validation context ('storage', 'form', 'business_rules', 'migration')
            changed_field_slug: If provided, optimize validation for this specific field change
            
        Returns:
            Dict with validation results
        """
        self.logger.info(f"VALIDATION: Starting optimized validation - context={context}, field={changed_field_slug or 'all'}")
        
        # PRIORITY-BASED VALIDATION STRATEGY
        if context == 'business_rules' and changed_field_slug:
            self.logger.info(f"VALIDATION: Priority-based validation for field '{changed_field_slug}'")
            
            # Step 1: Validate critical rules synchronously (blocking)
            critical_result = self.validate_critical_rules_sync(data, context, changed_field_slug)
            
            # Step 2: If critical validation passes, trigger async non-critical validation
            if critical_result['is_valid']:
                self.logger.info("VALIDATION: PASSED - Critical rules validation successful")
                
                # Trigger async validation in background (don't wait for it)
                try:
                    # Run async validation in background without blocking
                    asyncio.create_task(self.validate_non_critical_rules_async(data, changed_field_slug))
                    self.logger.info("VALIDATION: Background validation task started")
                except Exception as e:
                    self.logger.warning(f"VALIDATION: Background validation failed to start - {e}")
                    # Continue anyway - async validation is not critical
                
                # Return critical validation result immediately
                return critical_result
            else:
                self.logger.error("VALIDATION: FAILED - Critical rules validation failed")
                return critical_result
        
        # For all other contexts, use dependency-aware validation
        if changed_field_slug:
            self.logger.info(f"VALIDATION: Analyzing field dependencies for '{changed_field_slug}'")
            
            # Get all affected fields based on cascading dependencies
            cascade_data = self.get_all_affected_fields_with_cascades(changed_field_slug)
            affected_fields = set(cascade_data['affected_fields'])
            
            # Filter to only validate affected fields
            fields_to_validate = self.pipeline.fields.filter(slug__in=affected_fields)
            self.logger.info(f"VALIDATION: Validating {fields_to_validate.count()} affected field(s)")
        else:
            # No specific field changed - validate all fields
            fields_to_validate = self.pipeline.fields.all()
            self.logger.info(f"VALIDATION: Full validation of {fields_to_validate.count()} field(s)")
        
        # Build field definitions for the necessary fields
        field_definitions = []
        for field in fields_to_validate:
            field_definitions.append({
                'slug': field.slug,
                'field_type': field.field_type,
                'field_config': field.field_config,
                'storage_constraints': field.storage_constraints,
                'business_rules': field.business_rules,
                'ai_config': field.ai_config if field.is_ai_field else {},
            })
        
        # Use the existing validation function with the filtered field definitions
        from . import validate_record_data
        result = validate_record_data(field_definitions, data, context)
        
        # Log the validation result
        if result.get('is_valid', False):
            self.logger.info(f"VALIDATION: PASSED - {len(field_definitions)} field(s) validated successfully")
        else:
            error_count = len(result.get('field_errors', {}))
            self.logger.error(f"VALIDATION: FAILED - {error_count} field validation error(s)")
        
        return result
    
    def validate_critical_rules_sync(self, data: Dict[str, Any], context: str = 'business_rules', 
                                   changed_field_slug: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronously validate critical business rules (moved from Pipeline.validate_critical_rules_sync)
        
        This is optimized for speed and only validates rules that can block operations
        
        Args:
            data: Record data to validate
            context: Validation context
            changed_field_slug: If provided, optimize for this field change
            
        Returns:
            Dict with validation results
        """
        self.logger.info(f"VALIDATION: Starting critical rules validation for {changed_field_slug or 'all fields'}")
        
        # Get critical rules only
        rule_categories = self.categorize_business_rules_by_priority()
        critical_rules = rule_categories['critical']
        
        if changed_field_slug:
            # Use cascade analysis for critical rules
            cascade_data = self.get_all_affected_fields_with_cascades(changed_field_slug)
            affected_fields = set(cascade_data['affected_fields'])
            critical_rules = [r for r in critical_rules if r['field_slug'] in affected_fields]
            self.logger.info(f"VALIDATION: Filtering to {len(critical_rules)} critical rule(s)")
        
        # Build field definitions for critical fields only
        critical_field_slugs = [r['field_slug'] for r in critical_rules]
        fields_to_validate = self.pipeline.fields.filter(slug__in=critical_field_slugs)
        
        field_definitions = []
        for field in fields_to_validate:
            field_definitions.append({
                'slug': field.slug,
                'field_type': field.field_type,
                'field_config': field.field_config,
                'storage_constraints': field.storage_constraints,
                'business_rules': field.business_rules,
                'ai_config': field.ai_config if field.is_ai_field else {},
            })
        
        # Use existing validation function but only on critical fields
        from . import validate_record_data
        result = validate_record_data(field_definitions, data, context)
        
        # Log the critical validation result
        if result.get('is_valid', False):
            self.logger.info(f"VALIDATION: PASSED - Critical rules validation successful ({len(field_definitions)} field(s))")
        else:
            error_count = len(result.get('field_errors', {}))
            self.logger.error(f"VALIDATION: FAILED - Critical rules validation failed ({error_count} error(s))")
        
        return result
    
    async def validate_non_critical_rules_async(self, data: Dict[str, Any], 
                                              changed_field_slug: Optional[str] = None) -> Dict[str, Any]:
        """
        Asynchronously validate non-critical business rules (moved from Pipeline.validate_non_critical_rules_async)
        
        Args:
            data: Record data to validate
            changed_field_slug: If provided, only validate rules affected by this field
            
        Returns:
            Dict with validation results
        """
        self.logger.info(f"VALIDATION: Starting background validation for {changed_field_slug or 'all fields'}")
        
        # Get non-critical rules
        rule_categories = self.categorize_business_rules_by_priority()
        non_critical_rules = rule_categories['non_critical']
        
        if changed_field_slug:
            # Filter to only affected fields
            cascade_data = self.get_all_affected_fields_with_cascades(changed_field_slug)
            affected_fields = set(cascade_data['affected_fields'])
            non_critical_rules = [r for r in non_critical_rules if r['field_slug'] in affected_fields]
            self.logger.info(f"VALIDATION: Processing {len(non_critical_rules)} background rule(s)")
        
        # Process rules asynchronously with small delays to prevent blocking
        results = {'warnings': [], 'display_changes': [], 'suggestions': []}
        
        for rule_data in non_critical_rules:
            try:
                # Small delay to prevent database overload
                await asyncio.sleep(0.01)  
                
                field_slug = rule_data['field_slug']
                business_rules = rule_data['business_rules']
                
                # Process show_when/hide_when rules (display logic)
                conditional_rules = business_rules.get('conditional_rules', {})
                
                if conditional_rules.get('show_when') or conditional_rules.get('hide_when'):
                    display_result = await self._evaluate_display_rules_async(field_slug, data, conditional_rules)
                    if display_result:
                        results['display_changes'].append(display_result)
                
                # Process validation warnings (non-blocking)
                warning_rules = business_rules.get('warning_rules', [])
                for warning_rule in warning_rules:
                    warning_result = await self._evaluate_warning_rule_async(field_slug, data, warning_rule)
                    if warning_result:
                        results['warnings'].append(warning_result)
                
                # Process suggestions and recommendations
                suggestion_rules = business_rules.get('suggestion_rules', [])
                for suggestion_rule in suggestion_rules:
                    suggestion_result = await self._evaluate_suggestion_rule_async(field_slug, data, suggestion_rule)
                    if suggestion_result:
                        results['suggestions'].append(suggestion_result)
                
            except Exception as e:
                self.logger.error(f"VALIDATION: Background rule error for '{field_slug}' - {e}")
                # Continue processing other rules even if one fails
                continue
        
        total_results = len(results['warnings']) + len(results['display_changes']) + len(results['suggestions'])
        if total_results > 0:
            self.logger.info(f"VALIDATION: COMPLETED - Background validation processed {total_results} result(s)")
        else:
            self.logger.info("VALIDATION: COMPLETED - Background validation (no results)")
            
        
        return {
            'is_valid': True,  # Async validation doesn't block operations
            'async_results': results,
            'processed_rules': len(non_critical_rules)
        }
    
    # =============================================================================
    # HELPER METHODS - Supporting functionality
    # =============================================================================
    
    def categorize_business_rules_by_priority(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorize business rules by priority (critical vs non-critical)
        
        Returns:
            Dict with 'critical' and 'non_critical' rule lists
        """
        critical_rules = []
        non_critical_rules = []
        
        for field in self.pipeline.fields.all():
            if not field.business_rules:
                continue
            
            rule_data = {
                'field_slug': field.slug,
                'business_rules': field.business_rules
            }
            
            # Rules that can block operations are critical
            stage_requirements = field.business_rules.get('stage_requirements', {})
            conditional_requirements = field.business_rules.get('conditional_requirements', [])
            validation_rules = field.business_rules.get('validation_rules', [])
            
            # Critical: Required fields, stage blocking rules, validation errors
            if (stage_requirements or 
                conditional_requirements or 
                validation_rules):
                critical_rules.append(rule_data)
            
            # Non-critical: Display logic, warnings, suggestions
            conditional_rules = field.business_rules.get('conditional_rules', {})
            warning_rules = field.business_rules.get('warning_rules', [])
            suggestion_rules = field.business_rules.get('suggestion_rules', [])
            
            if (conditional_rules.get('show_when') or 
                conditional_rules.get('hide_when') or 
                warning_rules or 
                suggestion_rules):
                non_critical_rules.append(rule_data)
        
        return {
            'critical': critical_rules,
            'non_critical': non_critical_rules
        }
    
    def get_all_affected_fields_with_cascades(self, changed_field_slug: str) -> Dict[str, Any]:
        """
        Get all fields affected by a change, including cascade dependencies
        
        Args:
            changed_field_slug: Slug of the field that changed
            
        Returns:
            Dict with affected field information
        """
        affected_fields = set([changed_field_slug])  # Always include the changed field itself
        
        # Find fields that reference the changed field
        for field in self.pipeline.fields.all():
            if field.slug == changed_field_slug:
                continue
            
            # Check if this field references the changed field in business rules
            if field.business_rules:
                # Convert business rules to string for searching
                rules_str = str(field.business_rules)
                if changed_field_slug in rules_str:
                    affected_fields.add(field.slug)
            
            # Check field config references (for computed fields, AI prompts, etc.)
            if field.field_config:
                config_str = str(field.field_config)
                if changed_field_slug in config_str:
                    affected_fields.add(field.slug)
            
            # Check AI config references
            if field.ai_config:
                ai_config_str = str(field.ai_config)
                if changed_field_slug in ai_config_str:
                    affected_fields.add(field.slug)
        
        return {
            'affected_fields': list(affected_fields),
            'cascade_depth': len(affected_fields) - 1,  # Exclude the original field
            'total_fields': self.pipeline.fields.count()
        }
    
    # =============================================================================
    # ASYNC EVALUATION HELPERS
    # =============================================================================
    
    async def _evaluate_display_rules_async(self, field_slug: str, data: Dict[str, Any], 
                                           conditional_rules: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Asynchronously evaluate display logic rules
        
        Args:
            field_slug: Field to evaluate
            data: Record data
            conditional_rules: Rules to evaluate
            
        Returns:
            Display change result or None
        """
        try:
            # Implement display rule evaluation logic
            show_when = conditional_rules.get('show_when')
            hide_when = conditional_rules.get('hide_when')
            
            current_visibility = True  # Default visible
            
            if show_when:
                # Evaluate show condition
                current_visibility = self._evaluate_condition(data, show_when)
            
            if hide_when and current_visibility:
                # Evaluate hide condition
                current_visibility = not self._evaluate_condition(data, hide_when)
            
            return {
                'field_slug': field_slug,
                'should_show': current_visibility,
                'rule_type': 'display_logic',
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"VALIDATION: Display rule evaluation failed for '{field_slug}' - {e}")
            return None
    
    async def _evaluate_warning_rule_async(self, field_slug: str, data: Dict[str, Any], 
                                         warning_rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Asynchronously evaluate warning rules
        
        Args:
            field_slug: Field to evaluate
            data: Record data
            warning_rule: Warning rule to evaluate
            
        Returns:
            Warning result or None
        """
        try:
            condition = warning_rule.get('condition')
            message = warning_rule.get('message', f'Warning for field {field_slug}')
            
            if condition and self._evaluate_condition(data, condition):
                return {
                    'field_slug': field_slug,
                    'message': message,
                    'rule_type': 'warning',
                    'severity': warning_rule.get('severity', 'low'),
                    'timestamp': timezone.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"VALIDATION: Warning rule evaluation failed for '{field_slug}' - {e}")
            return None
    
    async def _evaluate_suggestion_rule_async(self, field_slug: str, data: Dict[str, Any], 
                                            suggestion_rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Asynchronously evaluate suggestion rules
        
        Args:
            field_slug: Field to evaluate
            data: Record data
            suggestion_rule: Suggestion rule to evaluate
            
        Returns:
            Suggestion result or None
        """
        try:
            condition = suggestion_rule.get('condition')
            suggestion = suggestion_rule.get('suggestion', f'Suggestion for field {field_slug}')
            
            if condition and self._evaluate_condition(data, condition):
                return {
                    'field_slug': field_slug,
                    'suggestion': suggestion,
                    'rule_type': 'suggestion',
                    'priority': suggestion_rule.get('priority', 'medium'),
                    'timestamp': timezone.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"VALIDATION: Suggestion rule evaluation failed for '{field_slug}' - {e}")
            return None
    
    def _evaluate_condition(self, data: Dict[str, Any], condition: Dict[str, Any]) -> bool:
        """
        Evaluate a condition against record data
        
        Args:
            data: Record data
            condition: Condition to evaluate
            
        Returns:
            True if condition is met
        """
        try:
            field_name = condition.get('field')
            operator = condition.get('operator', 'equals')
            expected_value = condition.get('value')
            
            if not field_name or field_name not in data:
                return False
            
            actual_value = data[field_name]
            
            if operator == 'equals':
                return actual_value == expected_value
            elif operator == 'not_equals':
                return actual_value != expected_value
            elif operator == 'contains':
                return expected_value in str(actual_value)
            elif operator == 'not_contains':
                return expected_value not in str(actual_value)
            elif operator == 'is_empty':
                return not actual_value
            elif operator == 'is_not_empty':
                return bool(actual_value)
            else:
                self.logger.warning(f"VALIDATION: Unknown condition operator '{operator}' - defaulting to false")
                return False
                
        except Exception as e:
            self.logger.error(f"VALIDATION: Condition evaluation failed - {e}")
            return False