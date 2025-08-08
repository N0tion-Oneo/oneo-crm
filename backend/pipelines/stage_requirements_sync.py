"""
2-way synchronization between Stage Requirements UI and Conditional Engine
"""
from typing import Dict, Any, List, Optional


def stage_requirements_to_conditional_rules(
    stage_requirements: Dict[str, Dict[str, Any]], 
    stage_field_slug: str
) -> Dict[str, Any]:
    """
    Convert stage_requirements format to conditional_rules format
    
    Input format:
    {
        "qualified": {"required": True, "block_transitions": True, "warning_message": "Custom message"},
        "proposal": {"required": True}
    }
    
    Output format:
    {
        "logic": "OR",
        "rules": [
            {"field": "sales_stage", "condition": "equals", "value": "qualified"},
            {"field": "sales_stage", "condition": "equals", "value": "proposal"}
        ]
    }
    """
    if not stage_requirements:
        return {"logic": "OR", "rules": []}
    
    rules = []
    for stage_name, requirements in stage_requirements.items():
        if requirements.get('required', False):
            rule = {
                "field": stage_field_slug,
                "condition": "equals", 
                "value": stage_name
            }
            
            # Add description with additional metadata
            description_parts = [f"Required in {stage_name} stage"]
            if requirements.get('warning_message'):
                description_parts.append(f"Warning: {requirements['warning_message']}")
            if requirements.get('block_transitions', True):
                description_parts.append("blocks transitions")
            
            rule["description"] = " - ".join(description_parts)
            rules.append(rule)
    
    return {
        "logic": "OR",
        "rules": rules
    }


def conditional_rules_to_stage_requirements(
    conditional_rules: Dict[str, Any], 
    stage_field_slug: str
) -> Dict[str, Dict[str, Any]]:
    """
    Convert conditional_rules format back to stage_requirements format for UI
    
    Input format:
    {
        "logic": "OR",
        "rules": [
            {"field": "sales_stage", "condition": "equals", "value": "qualified", "description": "Required in qualified stage - Warning: Custom message - blocks transitions"},
            {"field": "sales_stage", "condition": "equals", "value": "proposal"}
        ]
    }
    
    Output format:
    {
        "qualified": {"required": True, "block_transitions": True, "warning_message": "Custom message"},
        "proposal": {"required": True}
    }
    """
    stage_requirements = {}
    
    if not conditional_rules or not isinstance(conditional_rules, dict):
        return stage_requirements
    
    rules = conditional_rules.get('rules', [])
    
    for rule in rules:
        if (isinstance(rule, dict) and 
            rule.get('field') == stage_field_slug and 
            rule.get('condition') == 'equals' and 
            rule.get('value')):
            
            stage_name = rule['value']
            stage_req = {"required": True}
            
            # Parse description for additional metadata
            description = rule.get('description', '')
            if description:
                if 'Warning:' in description:
                    # Extract warning message
                    parts = description.split('Warning:')
                    if len(parts) > 1:
                        warning_part = parts[1].split(' - ')[0].strip()
                        stage_req['warning_message'] = warning_part
                
                if 'blocks transitions' in description:
                    stage_req['block_transitions'] = True
                else:
                    stage_req['block_transitions'] = False
                
                if 'show warnings' not in description:
                    stage_req['show_warnings'] = True
            
            stage_requirements[stage_name] = stage_req
    
    return stage_requirements


def sync_stage_requirements_to_conditional(field_business_rules: Dict[str, Any], stage_field_slug: str) -> Dict[str, Any]:
    """
    Sync stage_requirements to conditional_rules in field business_rules
    
    This maintains the stage_requirements for UI compatibility while ensuring
    conditional_rules is always up to date for the validation engine.
    """
    if not field_business_rules:
        field_business_rules = {}
    
    stage_requirements = field_business_rules.get('stage_requirements', {})
    
    if stage_requirements:
        # Convert stage requirements to conditional rules
        conditional_rules = field_business_rules.get('conditional_rules', {})
        
        # Update require_when with converted stage requirements
        conditional_rules['require_when'] = stage_requirements_to_conditional_rules(
            stage_requirements, stage_field_slug
        )
        
        field_business_rules['conditional_rules'] = conditional_rules
    
    return field_business_rules


def sync_conditional_to_stage_requirements(field_business_rules: Dict[str, Any], stage_field_slug: str) -> Dict[str, Any]:
    """
    Sync conditional_rules back to stage_requirements for UI display
    
    This ensures the UI shows the current state from the conditional engine.
    """
    if not field_business_rules:
        return {}
    
    conditional_rules = field_business_rules.get('conditional_rules', {})
    require_when = conditional_rules.get('require_when', {})
    
    if require_when:
        # Convert conditional rules back to stage requirements
        stage_requirements = conditional_rules_to_stage_requirements(
            require_when, stage_field_slug
        )
        
        field_business_rules['stage_requirements'] = stage_requirements
    
    return field_business_rules


def find_stage_field_from_pipeline(pipeline_fields: List[Dict[str, Any]]) -> Optional[str]:
    """
    Auto-detect the most likely stage field from pipeline fields
    
    Looks for select fields that might represent stages based on naming and options
    """
    stage_field_candidates = []
    
    for field in pipeline_fields:
        if field.get('field_type') == 'select':
            field_slug = field.get('slug', field.get('name', ''))
            field_config = field.get('field_config', {})
            options = field_config.get('options', [])
            
            # Score this field as a potential stage field
            score = 0
            
            # Name-based scoring
            stage_keywords = ['stage', 'status', 'phase', 'step', 'pipeline', 'funnel']
            field_name_lower = field_slug.lower()
            for keyword in stage_keywords:
                if keyword in field_name_lower:
                    score += 10
            
            # Options-based scoring (common stage names)
            common_stages = [
                'lead', 'prospect', 'qualified', 'proposal', 'negotiation', 'closed',
                'discovery', 'demo', 'trial', 'contract', 'onboarding',
                'new', 'open', 'in_progress', 'completed', 'won', 'lost'
            ]
            
            if options:
                for option in options:
                    option_value = None
                    if isinstance(option, dict):
                        option_value = (option.get('value') or option.get('label', '')).lower()
                    elif isinstance(option, str):
                        option_value = option.lower()
                    
                    if option_value:
                        for stage in common_stages:
                            if stage in option_value or option_value in stage:
                                score += 5
            
            # Prefer fields with more options (stages usually have multiple values)
            if len(options) >= 3:
                score += 3
            elif len(options) >= 2:
                score += 1
            
            stage_field_candidates.append({
                'field_slug': field_slug,
                'score': score,
                'options_count': len(options)
            })
    
    # Return the highest scoring field
    if stage_field_candidates:
        best_candidate = max(stage_field_candidates, key=lambda x: x['score'])
        if best_candidate['score'] > 0:
            return best_candidate['field_slug']
    
    return None


def ensure_bidirectional_sync(field_business_rules: Dict[str, Any], stage_field_slug: str) -> Dict[str, Any]:
    """
    Ensure both stage_requirements and conditional_rules are in sync
    
    Priority: conditional_rules is the source of truth, but stage_requirements 
    provides UI-friendly format. This function ensures they stay synchronized.
    """
    if not field_business_rules:
        field_business_rules = {}
    
    # First, sync any existing stage_requirements TO conditional_rules
    field_business_rules = sync_stage_requirements_to_conditional(field_business_rules, stage_field_slug)
    
    # Then, sync conditional_rules back TO stage_requirements for UI display
    field_business_rules = sync_conditional_to_stage_requirements(field_business_rules, stage_field_slug)
    
    return field_business_rules