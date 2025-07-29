"""
Workflow templates for common automation scenarios - Phase 7
Provides pre-built workflows for CRM, ATS, CMS, and project management
"""
import uuid
from typing import Dict, Any, List
from django.contrib.auth import get_user_model
from .models import Workflow, WorkflowStatus, WorkflowTriggerType

User = get_user_model()


class WorkflowTemplateManager:
    """Manager for workflow templates and template instantiation"""
    
    def __init__(self):
        self.templates = {
            'crm_lead_qualification': self._crm_lead_qualification_template,
            'crm_follow_up_sequence': self._crm_follow_up_sequence_template,
            'crm_deal_progression': self._crm_deal_progression_template,
            'ats_candidate_screening': self._ats_candidate_screening_template,
            'ats_interview_scheduling': self._ats_interview_scheduling_template,
            'ats_hiring_decision': self._ats_hiring_decision_template,
            'cms_content_approval': self._cms_content_approval_template,
            'cms_seo_optimization': self._cms_seo_optimization_template,
            'project_task_automation': self._project_task_automation_template,
            'project_status_updates': self._project_status_updates_template,
            'ai_content_generation': self._ai_content_generation_template,
            'data_sync_automation': self._data_sync_automation_template,
        }
    
    def get_available_templates(self) -> List[Dict[str, Any]]:
        """Get list of available workflow templates with metadata"""
        return [
            {
                'id': 'crm_lead_qualification',
                'name': 'CRM Lead Qualification',
                'description': 'Automatically qualify and score leads using AI analysis',
                'category': 'CRM',
                'use_case': 'Analyze incoming leads, score them based on criteria, and route to appropriate sales reps',
                'estimated_setup_time': '10 minutes',
                'complexity': 'Medium'
            },
            {
                'id': 'crm_follow_up_sequence',
                'name': 'CRM Follow-up Sequence',
                'description': 'Automated follow-up sequence for leads and prospects',
                'category': 'CRM',
                'use_case': 'Send personalized follow-up messages based on lead behavior and engagement',
                'estimated_setup_time': '15 minutes',
                'complexity': 'Medium'
            },
            {
                'id': 'crm_deal_progression',
                'name': 'CRM Deal Progression',
                'description': 'Automate deal stage progression and notifications',
                'category': 'CRM',
                'use_case': 'Move deals through stages automatically based on activities and criteria',
                'estimated_setup_time': '20 minutes',
                'complexity': 'High'
            },
            {
                'id': 'ats_candidate_screening',
                'name': 'ATS Candidate Screening',
                'description': 'AI-powered candidate resume screening and ranking',
                'category': 'ATS',
                'use_case': 'Automatically screen resumes, extract key information, and rank candidates',
                'estimated_setup_time': '15 minutes',
                'complexity': 'Medium'
            },
            {
                'id': 'ats_interview_scheduling',
                'name': 'ATS Interview Scheduling',
                'description': 'Automated interview scheduling and coordination',
                'category': 'ATS',
                'use_case': 'Schedule interviews, send calendar invites, and coordinate with all parties',
                'estimated_setup_time': '25 minutes',
                'complexity': 'High'
            },
            {
                'id': 'ats_hiring_decision',
                'name': 'ATS Hiring Decision',
                'description': 'Automate hiring decision workflow with approvals',
                'category': 'ATS',
                'use_case': 'Collect feedback, make hiring recommendations, and route for approvals',
                'estimated_setup_time': '30 minutes',
                'complexity': 'High'
            },
            {
                'id': 'cms_content_approval',
                'name': 'CMS Content Approval',
                'description': 'Content review and approval workflow',
                'category': 'CMS',
                'use_case': 'Route content through review process with multiple approval stages',
                'estimated_setup_time': '20 minutes',
                'complexity': 'Medium'
            },
            {
                'id': 'cms_seo_optimization',
                'name': 'CMS SEO Optimization',
                'description': 'AI-powered SEO analysis and optimization',
                'category': 'CMS',
                'use_case': 'Analyze content for SEO, suggest improvements, and optimize automatically',
                'estimated_setup_time': '15 minutes',
                'complexity': 'Medium'
            },
            {
                'id': 'project_task_automation',
                'name': 'Project Task Automation',
                'description': 'Automate project task creation and assignments',
                'category': 'Project Management',
                'use_case': 'Create tasks automatically based on project milestones and dependencies',
                'estimated_setup_time': '20 minutes',
                'complexity': 'Medium'
            },
            {
                'id': 'project_status_updates',
                'name': 'Project Status Updates',
                'description': 'Automated project status reporting and notifications',
                'category': 'Project Management',
                'use_case': 'Generate status reports and notify stakeholders of project progress',
                'estimated_setup_time': '15 minutes',
                'complexity': 'Low'
            },
            {
                'id': 'ai_content_generation',
                'name': 'AI Content Generation',
                'description': 'AI-powered content creation and optimization',
                'category': 'AI/Automation',
                'use_case': 'Generate content using AI based on templates and data inputs',
                'estimated_setup_time': '10 minutes',
                'complexity': 'Low'
            },
            {
                'id': 'data_sync_automation',
                'name': 'Data Sync Automation',
                'description': 'Automated data synchronization between systems',
                'category': 'Integration',
                'use_case': 'Keep data synchronized between different systems and platforms',
                'estimated_setup_time': '25 minutes',
                'complexity': 'High'
            }
        ]
    
    def create_workflow_from_template(
        self, 
        template_id: str, 
        name: str,
        description: str,
        created_by: User,
        customizations: Dict[str, Any] = None
    ) -> Workflow:
        """Create a new workflow from a template"""
        
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")
        
        # Get template definition
        template_func = self.templates[template_id]
        template_definition = template_func()
        
        # Apply customizations if provided
        if customizations:
            template_definition = self._apply_customizations(template_definition, customizations)
        
        # Create workflow
        workflow = Workflow.objects.create(
            name=name,
            description=description or template_definition.get('description', ''),
            created_by=created_by,
            trigger_type=template_definition.get('trigger_type', WorkflowTriggerType.MANUAL),
            trigger_config=template_definition.get('trigger_config', {}),
            workflow_definition=template_definition.get('workflow_definition', {}),
            status=WorkflowStatus.DRAFT
        )
        
        return workflow
    
    def _apply_customizations(self, template_definition: Dict[str, Any], customizations: Dict[str, Any]) -> Dict[str, Any]:
        """Apply user customizations to template definition"""
        
        # Deep copy to avoid modifying original template
        import copy
        customized_definition = copy.deepcopy(template_definition)
        
        # Apply field mappings
        if 'field_mappings' in customizations:
            nodes = customized_definition.get('workflow_definition', {}).get('nodes', [])
            for node in nodes:
                node_data = node.get('data', {})
                if 'pipeline_id' in node_data and 'field_mappings' in customizations:
                    # Apply pipeline-specific field mappings
                    pass  # Implementation would go here
        
        # Apply user assignments
        if 'user_assignments' in customizations:
            nodes = customized_definition.get('workflow_definition', {}).get('nodes', [])
            for node in nodes:
                if node.get('type') == 'approval':
                    node_data = node.get('data', {})
                    if 'assigned_to_id' not in node_data and 'default_approver' in customizations['user_assignments']:
                        node_data['assigned_to_id'] = customizations['user_assignments']['default_approver']
        
        return customized_definition
    
    def _crm_lead_qualification_template(self) -> Dict[str, Any]:
        """CRM lead qualification workflow template"""
        return {
            'name': 'CRM Lead Qualification',
            'description': 'Automatically qualify and score leads using AI analysis',
            'trigger_type': WorkflowTriggerType.RECORD_CREATED,
            'trigger_config': {
                'pipeline_types': ['leads', 'prospects'],
                'conditions': []
            },
            'workflow_definition': {
                'nodes': [
                    {
                        'id': 'start',
                        'type': 'ai_analysis',
                        'position': {'x': 100, 'y': 100},
                        'data': {
                            'name': 'Lead Analysis',
                            'analysis_type': 'classification',
                            'data_source': 'trigger_data.record.data',
                            'categories': ['hot', 'warm', 'cold', 'unqualified'],
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.3,
                                'max_tokens': 500
                            }
                        }
                    },
                    {
                        'id': 'score_lead',
                        'type': 'ai_prompt',
                        'position': {'x': 300, 'y': 100},
                        'data': {
                            'name': 'Lead Scoring',
                            'prompt': '''Analyze this lead data and provide a lead score from 0-100 based on:
                            - Company size and industry
                            - Job title and decision-making authority
                            - Budget indicators
                            - Timeline urgency
                            - Engagement level
                            
                            Lead Data: {trigger_data.record.data}
                            Classification: {node_start}
                            
                            Return only a JSON object with: {{"score": number, "reasoning": "explanation"}}''',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.2,
                                'max_tokens': 300
                            }
                        }
                    },
                    {
                        'id': 'update_lead_record',
                        'type': 'record_update',
                        'position': {'x': 500, 'y': 100},
                        'data': {
                            'name': 'Update Lead Score',
                            'record_id_source': 'trigger_data.record.id',
                            'update_data': {
                                'lead_score': '{node_score_lead.score}',
                                'lead_classification': '{node_start}',
                                'qualification_date': '{timestamp}',
                                'scoring_reasoning': '{node_score_lead.reasoning}'
                            }
                        }
                    },
                    {
                        'id': 'route_decision',
                        'type': 'condition',
                        'position': {'x': 700, 'y': 100},
                        'data': {
                            'name': 'Routing Decision',
                            'conditions': [
                                {
                                    'left': {'context_path': 'node_score_lead.score'},
                                    'operator': '>=',
                                    'right': 80,
                                    'output': 'high_priority'
                                },
                                {
                                    'left': {'context_path': 'node_score_lead.score'},
                                    'operator': '>=',
                                    'right': 50,
                                    'output': 'medium_priority'
                                }
                            ],
                            'default_output': 'low_priority'
                        }
                    },
                    {
                        'id': 'notify_sales_rep',
                        'type': 'task_notify',
                        'position': {'x': 900, 'y': 50},
                        'data': {
                            'name': 'Notify Sales Rep',
                            'type': 'urgent',
                            'message': 'High-value lead qualified: {trigger_data.record.data.company} - Score: {node_score_lead.score}',
                            'recipients': ['sales_team']
                        }
                    }
                ],
                'edges': [
                    {'source': 'start', 'target': 'score_lead'},
                    {'source': 'score_lead', 'target': 'update_lead_record'},
                    {'source': 'update_lead_record', 'target': 'route_decision'},
                    {'source': 'route_decision', 'target': 'notify_sales_rep', 'condition': 'high_priority'}
                ]
            }
        }
    
    def _crm_follow_up_sequence_template(self) -> Dict[str, Any]:
        """CRM follow-up sequence workflow template"""
        return {
            'name': 'CRM Follow-up Sequence',
            'description': 'Automated follow-up sequence for leads and prospects',
            'trigger_type': WorkflowTriggerType.FIELD_CHANGED,
            'trigger_config': {
                'field_name': 'lead_status',
                'field_value': 'qualified',
                'pipeline_types': ['leads']
            },
            'workflow_definition': {
                'nodes': [
                    {
                        'id': 'initial_delay',
                        'type': 'wait_delay',
                        'position': {'x': 100, 'y': 100},
                        'data': {
                            'name': 'Initial Delay',
                            'delay_type': 'hours',
                            'delay_value': 2
                        }
                    },
                    {
                        'id': 'personalized_email',
                        'type': 'ai_prompt',
                        'position': {'x': 300, 'y': 100},
                        'data': {
                            'name': 'Generate Personalized Email',
                            'prompt': '''Create a personalized follow-up email for this lead:
                            
                            Lead Information:
                            - Name: {trigger_data.record.data.name}
                            - Company: {trigger_data.record.data.company}
                            - Industry: {trigger_data.record.data.industry}
                            - Pain Points: {trigger_data.record.data.pain_points}
                            
                            Email should be:
                            - Professional but friendly
                            - Address their specific pain points
                            - Include a clear call-to-action
                            - 150-200 words maximum
                            
                            Return the email content as plain text.''',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.7,
                                'max_tokens': 400
                            }
                        }
                    },
                    {
                        'id': 'send_email',
                        'type': 'webhook_out',
                        'position': {'x': 500, 'y': 100},
                        'data': {
                            'name': 'Send Follow-up Email',
                            'webhook_url': 'https://api.email-service.com/send',
                            'headers': {
                                'Authorization': 'Bearer {email_api_key}',
                                'Content-Type': 'application/json'
                            },
                            'payload': {
                                'to': '{trigger_data.record.data.email}',
                                'subject': 'Following up on your inquiry',
                                'content': '{node_personalized_email}',
                                'track_opens': True,
                                'track_clicks': True
                            }
                        }
                    },
                    {
                        'id': 'follow_up_delay',
                        'type': 'wait_delay',
                        'position': {'x': 700, 'y': 100},
                        'data': {
                            'name': 'Follow-up Delay',
                            'delay_type': 'hours',
                            'delay_value': 72
                        }
                    },
                    {
                        'id': 'check_engagement',
                        'type': 'http_request',
                        'position': {'x': 900, 'y': 100},
                        'data': {
                            'name': 'Check Email Engagement',
                            'method': 'GET',
                            'url': 'https://api.email-service.com/engagement/{trigger_data.record.data.email}',
                            'headers': {
                                'Authorization': 'Bearer {email_api_key}'
                            }
                        }
                    },
                    {
                        'id': 'engagement_decision',
                        'type': 'condition',
                        'position': {'x': 1100, 'y': 100},
                        'data': {
                            'name': 'Engagement Check',
                            'conditions': [
                                {
                                    'left': {'context_path': 'node_check_engagement.data.opened'},
                                    'operator': '==',
                                    'right': True,
                                    'output': 'engaged'
                                }
                            ],
                            'default_output': 'not_engaged'
                        }
                    }
                ],
                'edges': [
                    {'source': 'initial_delay', 'target': 'personalized_email'},
                    {'source': 'personalized_email', 'target': 'send_email'},
                    {'source': 'send_email', 'target': 'follow_up_delay'},
                    {'source': 'follow_up_delay', 'target': 'check_engagement'},
                    {'source': 'check_engagement', 'target': 'engagement_decision'}
                ]
            }
        }
    
    def _crm_deal_progression_template(self) -> Dict[str, Any]:
        """CRM deal progression workflow template"""
        return {
            'name': 'CRM Deal Progression',
            'description': 'Automate deal stage progression and notifications',
            'trigger_type': WorkflowTriggerType.FIELD_CHANGED,
            'trigger_config': {
                'field_name': 'deal_activities',
                'pipeline_types': ['deals', 'opportunities']
            },
            'workflow_definition': {
                'nodes': [
                    {
                        'id': 'analyze_activities',
                        'type': 'ai_analysis',
                        'position': {'x': 100, 'y': 100},
                        'data': {
                            'name': 'Analyze Deal Activities',
                            'analysis_type': 'summary',
                            'data_source': 'trigger_data.record.data.recent_activities',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.3
                            }
                        }
                    },
                    {
                        'id': 'progression_decision',
                        'type': 'ai_prompt',
                        'position': {'x': 300, 'y': 100},
                        'data': {
                            'name': 'Deal Progression Analysis',
                            'prompt': '''Analyze this deal and determine if it should progress to the next stage:
                            
                            Current Stage: {trigger_data.record.data.current_stage}
                            Deal Value: {trigger_data.record.data.value}
                            Recent Activities: {node_analyze_activities}
                            Days in Current Stage: {trigger_data.record.data.days_in_stage}
                            
                            Consider:
                            - Activity quality and frequency
                            - Stakeholder engagement
                            - Budget confirmation
                            - Decision timeline
                            
                            Return JSON: {{"should_progress": boolean, "recommended_stage": "stage_name", "confidence": number, "reasoning": "explanation"}}''',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.2,
                                'max_tokens': 400
                            }
                        }
                    },
                    {
                        'id': 'progression_approval',
                        'type': 'approval',
                        'position': {'x': 500, 'y': 100},
                        'data': {
                            'name': 'Stage Progression Approval',
                            'title': 'Deal Stage Progression Required',
                            'description': 'AI recommends progressing {trigger_data.record.data.company} deal to {node_progression_decision.recommended_stage}. Confidence: {node_progression_decision.confidence}%. Reasoning: {node_progression_decision.reasoning}',
                            'assigned_to_id': '{deal_owner_id}'
                        }
                    },
                    {
                        'id': 'update_deal_stage',
                        'type': 'record_update',
                        'position': {'x': 700, 'y': 100},
                        'data': {
                            'name': 'Update Deal Stage',
                            'record_id_source': 'trigger_data.record.id',
                            'update_data': {
                                'current_stage': '{node_progression_decision.recommended_stage}',
                                'stage_changed_date': '{timestamp}',
                                'progression_reason': '{node_progression_decision.reasoning}',
                                'auto_progressed': True
                            }
                        }
                    }
                ],
                'edges': [
                    {'source': 'analyze_activities', 'target': 'progression_decision'},
                    {'source': 'progression_decision', 'target': 'progression_approval'},
                    {'source': 'progression_approval', 'target': 'update_deal_stage'}
                ]
            }
        }
    
    def _ats_candidate_screening_template(self) -> Dict[str, Any]:
        """ATS candidate screening workflow template"""
        return {
            'name': 'ATS Candidate Screening',
            'description': 'AI-powered candidate resume screening and ranking',
            'trigger_type': WorkflowTriggerType.RECORD_CREATED,
            'trigger_config': {
                'pipeline_types': ['candidates', 'applications']
            },
            'workflow_definition': {
                'nodes': [
                    {
                        'id': 'extract_resume_data',
                        'type': 'ai_prompt',
                        'position': {'x': 100, 'y': 100},
                        'data': {
                            'name': 'Extract Resume Information',
                            'prompt': '''Extract key information from this resume/candidate profile:
                            
                            {trigger_data.record.data.resume_text}
                            
                            Extract and return JSON with:
                            - "experience_years": number of years of relevant experience
                            - "skills": array of key technical skills
                            - "education": highest education level
                            - "previous_roles": array of relevant job titles
                            - "industries": array of relevant industries
                            - "certifications": array of certifications
                            - "location": current location
                            - "salary_expectations": if mentioned
                            
                            Return only valid JSON.''',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.1,
                                'max_tokens': 800
                            }
                        }
                    },
                    {
                        'id': 'match_job_requirements',
                        'type': 'ai_prompt',
                        'position': {'x': 300, 'y': 100},
                        'data': {
                            'name': 'Match Job Requirements',
                            'prompt': '''Compare this candidate against job requirements and score the match:
                            
                            Job Requirements:
                            {trigger_data.job_requirements}
                            
                            Candidate Profile:
                            {node_extract_resume_data}
                            
                            Score each area from 0-100:
                            - Technical skills match
                            - Experience level match
                            - Industry experience
                            - Education requirements
                            - Cultural fit indicators
                            
                            Return JSON: {{"overall_score": number, "technical_score": number, "experience_score": number, "education_score": number, "strengths": array, "concerns": array, "recommendation": "string"}}''',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.2,
                                'max_tokens': 600
                            }
                        }
                    },
                    {
                        'id': 'update_candidate_profile',
                        'type': 'record_update',
                        'position': {'x': 500, 'y': 100},
                        'data': {
                            'name': 'Update Candidate Profile',
                            'record_id_source': 'trigger_data.record.id',
                            'update_data': {
                                'extracted_skills': '{node_extract_resume_data.skills}',
                                'experience_years': '{node_extract_resume_data.experience_years}',
                                'education_level': '{node_extract_resume_data.education}',
                                'match_score': '{node_match_job_requirements.overall_score}',
                                'technical_score': '{node_match_job_requirements.technical_score}',
                                'screening_date': '{timestamp}',
                                'ai_recommendation': '{node_match_job_requirements.recommendation}',
                                'screening_strengths': '{node_match_job_requirements.strengths}',
                                'screening_concerns': '{node_match_job_requirements.concerns}'
                            }
                        }
                    },
                    {
                        'id': 'screening_decision',
                        'type': 'condition',
                        'position': {'x': 700, 'y': 100},
                        'data': {
                            'name': 'Screening Decision',
                            'conditions': [
                                {
                                    'left': {'context_path': 'node_match_job_requirements.overall_score'},
                                    'operator': '>=',
                                    'right': 80,
                                    'output': 'strong_match'
                                },
                                {
                                    'left': {'context_path': 'node_match_job_requirements.overall_score'},
                                    'operator': '>=',
                                    'right': 60,
                                    'output': 'potential_match'
                                }
                            ],
                            'default_output': 'weak_match'
                        }
                    }
                ],
                'edges': [
                    {'source': 'extract_resume_data', 'target': 'match_job_requirements'},
                    {'source': 'match_job_requirements', 'target': 'update_candidate_profile'},
                    {'source': 'update_candidate_profile', 'target': 'screening_decision'}
                ]
            }
        }
    
    def _ats_interview_scheduling_template(self) -> Dict[str, Any]:
        """ATS interview scheduling workflow template"""
        return {
            'name': 'ATS Interview Scheduling',
            'description': 'Automated interview scheduling and coordination',
            'trigger_type': WorkflowTriggerType.FIELD_CHANGED,
            'trigger_config': {
                'field_name': 'candidate_status',
                'field_value': 'approved_for_interview'
            },
            'workflow_definition': {
                'nodes': [
                    {
                        'id': 'check_interviewer_availability',
                        'type': 'http_request',
                        'position': {'x': 100, 'y': 100},
                        'data': {
                            'name': 'Check Interviewer Availability',
                            'method': 'GET',
                            'url': 'https://calendar-api.com/availability/{interviewer_id}',
                            'headers': {'Authorization': 'Bearer {calendar_api_key}'}
                        }
                    },
                    {
                        'id': 'send_scheduling_email',
                        'type': 'ai_prompt',
                        'position': {'x': 300, 'y': 100},
                        'data': {
                            'name': 'Generate Scheduling Email',
                            'prompt': '''Create a professional interview scheduling email:
                            
                            Candidate: {trigger_data.record.data.name}
                            Position: {trigger_data.record.data.position}
                            Available Times: {node_check_interviewer_availability.data.available_slots}
                            
                            Email should:
                            - Congratulate them on moving to interview stage
                            - Provide 3-4 time slot options
                            - Include interview format (video/in-person)
                            - Ask for confirmation
                            - Be professional and welcoming
                            
                            Return email content as plain text.''',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.6,
                                'max_tokens': 400
                            }
                        }
                    }
                ],
                'edges': [
                    {'source': 'check_interviewer_availability', 'target': 'send_scheduling_email'}
                ]
            }
        }
    
    def _ats_hiring_decision_template(self) -> Dict[str, Any]:
        """ATS hiring decision workflow template"""
        return {
            'name': 'ATS Hiring Decision',
            'description': 'Automate hiring decision workflow with approvals',
            'trigger_type': WorkflowTriggerType.FIELD_CHANGED,
            'trigger_config': {
                'field_name': 'interview_status',
                'field_value': 'completed'
            },
            'workflow_definition': {
                'nodes': [
                    {
                        'id': 'collect_feedback',
                        'type': 'record_find',
                        'position': {'x': 100, 'y': 100},
                        'data': {
                            'name': 'Collect Interview Feedback',
                            'pipeline_id': '{interview_feedback_pipeline_id}',
                            'search_criteria': {
                                'candidate_id': '{trigger_data.record.id}'
                            }
                        }
                    },
                    {
                        'id': 'analyze_feedback',
                        'type': 'ai_analysis',
                        'position': {'x': 300, 'y': 100},
                        'data': {
                            'name': 'Analyze All Feedback',
                            'analysis_type': 'summary',
                            'data_source': 'node_collect_feedback.records',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.3
                            }
                        }
                    },
                    {
                        'id': 'hiring_recommendation',
                        'type': 'ai_prompt',
                        'position': {'x': 500, 'y': 100},
                        'data': {
                            'name': 'Generate Hiring Recommendation',
                            'prompt': '''Based on all interview feedback, provide a hiring recommendation:
                            
                            Candidate: {trigger_data.record.data.name}
                            Position: {trigger_data.record.data.position}
                            
                            Interview Feedback Summary:
                            {node_analyze_feedback}
                            
                            Original Screening Score: {trigger_data.record.data.match_score}
                            
                            Provide recommendation with:
                            - Clear hire/no-hire recommendation
                            - Confidence level (0-100)
                            - Key strengths
                            - Areas of concern
                            - Salary recommendation if applicable
                            
                            Return JSON: {{"recommendation": "hire/no-hire", "confidence": number, "strengths": array, "concerns": array, "reasoning": "detailed explanation"}}''',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.2,
                                'max_tokens': 600
                            }
                        }
                    },
                    {
                        'id': 'hiring_manager_approval',
                        'type': 'approval',
                        'position': {'x': 700, 'y': 100},
                        'data': {
                            'name': 'Hiring Manager Approval',
                            'title': 'Hiring Decision Required',
                            'description': 'AI Recommendation: {node_hiring_recommendation.recommendation} for {trigger_data.record.data.name}. Confidence: {node_hiring_recommendation.confidence}%. Reasoning: {node_hiring_recommendation.reasoning}',
                            'assigned_to_id': '{hiring_manager_id}'
                        }
                    }
                ],
                'edges': [
                    {'source': 'collect_feedback', 'target': 'analyze_feedback'},
                    {'source': 'analyze_feedback', 'target': 'hiring_recommendation'},
                    {'source': 'hiring_recommendation', 'target': 'hiring_manager_approval'}
                ]
            }
        }
    
    def _cms_content_approval_template(self) -> Dict[str, Any]:
        """CMS content approval workflow template"""
        return {
            'name': 'CMS Content Approval',
            'description': 'Content review and approval workflow',
            'trigger_type': WorkflowTriggerType.FIELD_CHANGED,
            'trigger_config': {
                'field_name': 'content_status',
                'field_value': 'ready_for_review'
            },
            'workflow_definition': {
                'nodes': [
                    {
                        'id': 'content_quality_check',
                        'type': 'ai_analysis',
                        'position': {'x': 100, 'y': 100},
                        'data': {
                            'name': 'Content Quality Analysis',
                            'analysis_type': 'general',
                            'data_source': 'trigger_data.record.data.content',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.3
                            }
                        }
                    },
                    {
                        'id': 'editor_review',
                        'type': 'approval',
                        'position': {'x': 300, 'y': 100},
                        'data': {
                            'name': 'Editor Review',
                            'title': 'Content Review Required',
                            'description': 'Please review content: {trigger_data.record.data.title}. AI Quality Analysis: {node_content_quality_check}',
                            'assigned_to_id': '{content_editor_id}'
                        }
                    },
                    {
                        'id': 'publish_content',
                        'type': 'record_update',
                        'position': {'x': 500, 'y': 100},
                        'data': {
                            'name': 'Publish Content',
                            'record_id_source': 'trigger_data.record.id',
                            'update_data': {
                                'content_status': 'published',
                                'published_date': '{timestamp}',
                                'published_by': '{approval_result.approved_by}'
                            }
                        }
                    }
                ],
                'edges': [
                    {'source': 'content_quality_check', 'target': 'editor_review'},
                    {'source': 'editor_review', 'target': 'publish_content'}
                ]
            }
        }
    
    def _cms_seo_optimization_template(self) -> Dict[str, Any]:
        """CMS SEO optimization workflow template"""
        return {
            'name': 'CMS SEO Optimization',
            'description': 'AI-powered SEO analysis and optimization',
            'trigger_type': WorkflowTriggerType.RECORD_CREATED,
            'trigger_config': {
                'pipeline_types': ['articles', 'blog_posts', 'pages']
            },
            'workflow_definition': {
                'nodes': [
                    {
                        'id': 'seo_analysis',
                        'type': 'ai_prompt',
                        'position': {'x': 100, 'y': 100},
                        'data': {
                            'name': 'SEO Content Analysis',
                            'prompt': '''Analyze this content for SEO optimization:
                            
                            Title: {trigger_data.record.data.title}
                            Content: {trigger_data.record.data.content}
                            Target Keywords: {trigger_data.record.data.target_keywords}
                            
                            Analyze:
                            - Keyword density and distribution
                            - Title and heading optimization
                            - Meta description effectiveness
                            - Content structure and readability
                            - Internal linking opportunities
                            
                            Return JSON: {{"seo_score": number, "title_suggestions": array, "meta_description": "string", "keyword_recommendations": array, "content_improvements": array}}''',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.3,
                                'max_tokens': 800
                            }
                        }
                    },
                    {
                        'id': 'update_seo_data',
                        'type': 'record_update',
                        'position': {'x': 300, 'y': 100},
                        'data': {
                            'name': 'Update SEO Data',
                            'record_id_source': 'trigger_data.record.id',
                            'update_data': {
                                'seo_score': '{node_seo_analysis.seo_score}',
                                'suggested_meta_description': '{node_seo_analysis.meta_description}',
                                'title_suggestions': '{node_seo_analysis.title_suggestions}',
                                'seo_recommendations': '{node_seo_analysis.content_improvements}',
                                'seo_analysis_date': '{timestamp}'
                            }
                        }
                    }
                ],
                'edges': [
                    {'source': 'seo_analysis', 'target': 'update_seo_data'}
                ]
            }
        }
    
    def _project_task_automation_template(self) -> Dict[str, Any]:
        """Project task automation workflow template"""
        return {
            'name': 'Project Task Automation',
            'description': 'Automate project task creation and assignments',
            'trigger_type': WorkflowTriggerType.FIELD_CHANGED,
            'trigger_config': {
                'field_name': 'project_phase',
                'pipeline_types': ['projects']
            },
            'workflow_definition': {
                'nodes': [
                    {
                        'id': 'generate_tasks',
                        'type': 'ai_prompt',
                        'position': {'x': 100, 'y': 100},
                        'data': {
                            'name': 'Generate Phase Tasks',
                            'prompt': '''Generate tasks for this project phase:
                            
                            Project: {trigger_data.record.data.name}
                            Phase: {trigger_data.record.data.project_phase}
                            Project Type: {trigger_data.record.data.project_type}
                            Team Size: {trigger_data.record.data.team_size}
                            Timeline: {trigger_data.record.data.timeline}
                            
                            Generate appropriate tasks for this phase including:
                            - Task descriptions
                            - Estimated hours
                            - Dependencies
                            - Skill requirements
                            - Priority levels
                            
                            Return JSON array of tasks: [{{"title": "string", "description": "string", "estimated_hours": number, "priority": "high/medium/low", "skills_required": array, "depends_on": array}}]''',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.4,
                                'max_tokens': 1000
                            }
                        }
                    },
                    {
                        'id': 'create_tasks',
                        'type': 'for_each',
                        'position': {'x': 300, 'y': 100},
                        'data': {
                            'name': 'Create Individual Tasks',
                            'items_path': 'node_generate_tasks',
                            'max_concurrency': 3,
                            'sub_workflow_id': '{task_creation_workflow_id}'
                        }
                    }
                ],
                'edges': [
                    {'source': 'generate_tasks', 'target': 'create_tasks'}
                ]
            }
        }
    
    def _project_status_updates_template(self) -> Dict[str, Any]:
        """Project status updates workflow template"""
        return {
            'name': 'Project Status Updates',
            'description': 'Automated project status reporting and notifications',
            'trigger_type': WorkflowTriggerType.SCHEDULED,
            'trigger_config': {
                'cron_expression': '0 9 * * 1',  # Every Monday at 9 AM
                'timezone': 'UTC'
            },
            'workflow_definition': {
                'nodes': [
                    {
                        'id': 'collect_project_data',
                        'type': 'record_find',
                        'position': {'x': 100, 'y': 100},
                        'data': {
                            'name': 'Collect Active Projects',
                            'pipeline_id': '{projects_pipeline_id}',
                            'search_criteria': {
                                'status': 'active'
                            },
                            'limit': 50
                        }
                    },
                    {
                        'id': 'generate_status_report',
                        'type': 'ai_prompt',
                        'position': {'x': 300, 'y': 100},
                        'data': {
                            'name': 'Generate Weekly Status Report',
                            'prompt': '''Create a weekly project status report:
                            
                            Active Projects Data:
                            {node_collect_project_data.records}
                            
                            Include:
                            - Overall portfolio health
                            - Projects at risk
                            - Completed milestones
                            - Upcoming deadlines
                            - Resource utilization
                            - Key achievements
                            
                            Format as a professional executive summary.''',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.3,
                                'max_tokens': 1200
                            }
                        }
                    },
                    {
                        'id': 'send_status_report',
                        'type': 'task_notify',
                        'position': {'x': 500, 'y': 100},
                        'data': {
                            'name': 'Send Status Report',
                            'type': 'info',
                            'message': 'Weekly Project Status Report: {node_generate_status_report}',
                            'recipients': ['project_managers', 'executives']
                        }
                    }
                ],
                'edges': [
                    {'source': 'collect_project_data', 'target': 'generate_status_report'},
                    {'source': 'generate_status_report', 'target': 'send_status_report'}
                ]
            }
        }
    
    def _ai_content_generation_template(self) -> Dict[str, Any]:
        """AI content generation workflow template"""
        return {
            'name': 'AI Content Generation',
            'description': 'AI-powered content creation and optimization',
            'trigger_type': WorkflowTriggerType.MANUAL,
            'trigger_config': {},
            'workflow_definition': {
                'nodes': [
                    {
                        'id': 'generate_outline',
                        'type': 'ai_prompt',
                        'position': {'x': 100, 'y': 100},
                        'data': {
                            'name': 'Generate Content Outline',
                            'prompt': '''Create a detailed content outline for:
                            
                            Topic: {trigger_data.topic}
                            Content Type: {trigger_data.content_type}
                            Target Audience: {trigger_data.target_audience}
                            Word Count: {trigger_data.word_count}
                            Tone: {trigger_data.tone}
                            Key Points: {trigger_data.key_points}
                            
                            Create a structured outline with:
                            - Introduction hook
                            - Main sections with subpoints
                            - Key messages for each section
                            - Call-to-action suggestions
                            
                            Return as structured JSON: {{"outline": {{"introduction": "string", "sections": [{{"title": "string", "points": array}}], "conclusion": "string", "cta_suggestions": array}}}}''',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.6,
                                'max_tokens': 800
                            }
                        }
                    },
                    {
                        'id': 'write_content',
                        'type': 'ai_prompt',
                        'position': {'x': 300, 'y': 100},
                        'data': {
                            'name': 'Write Full Content',
                            'prompt': '''Write complete content based on this outline:
                            
                            {node_generate_outline}
                            
                            Requirements:
                            - Target length: {trigger_data.word_count} words
                            - Tone: {trigger_data.tone}
                            - Include relevant examples
                            - Optimize for readability
                            - Include clear section headings
                            
                            Return the complete content as formatted text.''',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.7,
                                'max_tokens': 2000
                            }
                        }
                    },
                    {
                        'id': 'save_content',
                        'type': 'record_create',
                        'position': {'x': 500, 'y': 100},
                        'data': {
                            'name': 'Save Generated Content',
                            'pipeline_id': '{content_pipeline_id}',
                            'record_data': {
                                'title': '{trigger_data.topic}',
                                'content': '{node_write_content}',
                                'content_type': '{trigger_data.content_type}',
                                'status': 'draft',
                                'generated_by_ai': True,
                                'outline': '{node_generate_outline}',
                                'creation_date': '{timestamp}'
                            }
                        }
                    }
                ],
                'edges': [
                    {'source': 'generate_outline', 'target': 'write_content'},
                    {'source': 'write_content', 'target': 'save_content'}
                ]
            }
        }
    
    def _data_sync_automation_template(self) -> Dict[str, Any]:
        """Data sync automation workflow template"""
        return {
            'name': 'Data Sync Automation',
            'description': 'Automated data synchronization between systems',
            'trigger_type': WorkflowTriggerType.SCHEDULED,
            'trigger_config': {
                'cron_expression': '0 */6 * * *',  # Every 6 hours
                'timezone': 'UTC'
            },
            'workflow_definition': {
                'nodes': [
                    {
                        'id': 'fetch_source_data',
                        'type': 'http_request',
                        'position': {'x': 100, 'y': 100},
                        'data': {
                            'name': 'Fetch Source Data',
                            'method': 'GET',
                            'url': '{source_api_url}/data',
                            'headers': {
                                'Authorization': 'Bearer {source_api_key}'
                            }
                        }
                    },
                    {
                        'id': 'transform_data',
                        'type': 'ai_prompt',
                        'position': {'x': 300, 'y': 100},
                        'data': {
                            'name': 'Transform Data Format',
                            'prompt': '''Transform this data from source format to target format:
                            
                            Source Data:
                            {node_fetch_source_data.data}
                            
                            Target Format Requirements:
                            {target_format_requirements}
                            
                            Field Mappings:
                            {field_mappings}
                            
                            Return transformed data as JSON array matching target format.''',
                            'ai_config': {
                                'model': 'gpt-4',
                                'temperature': 0.1,
                                'max_tokens': 1500
                            }
                        }
                    },
                    {
                        'id': 'sync_to_target',
                        'type': 'http_request',
                        'position': {'x': 500, 'y': 100},
                        'data': {
                            'name': 'Sync to Target System',
                            'method': 'POST',
                            'url': '{target_api_url}/sync',
                            'headers': {
                                'Authorization': 'Bearer {target_api_key}',
                                'Content-Type': 'application/json'
                            },
                            'body': {
                                'data': '{node_transform_data}',
                                'sync_timestamp': '{timestamp}',
                                'source': 'automated_workflow'
                            }
                        }
                    },
                    {
                        'id': 'log_sync_results',
                        'type': 'record_create',
                        'position': {'x': 700, 'y': 100},
                        'data': {
                            'name': 'Log Sync Results',
                            'pipeline_id': '{sync_log_pipeline_id}',
                            'record_data': {
                                'sync_timestamp': '{timestamp}',
                                'records_synced': '{node_transform_data.length}',
                                'source_status': '{node_fetch_source_data.status_code}',
                                'target_status': '{node_sync_to_target.status_code}',
                                'success': '{node_sync_to_target.success}',
                                'errors': '{node_sync_to_target.data.errors}'
                            }
                        }
                    }
                ],
                'edges': [
                    {'source': 'fetch_source_data', 'target': 'transform_data'},
                    {'source': 'transform_data', 'target': 'sync_to_target'},
                    {'source': 'sync_to_target', 'target': 'log_sync_results'}
                ]
            }
        }


# Global template manager instance
workflow_template_manager = WorkflowTemplateManager()