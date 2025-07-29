"""
System pipeline templates for common use cases
"""
from typing import Dict, List, Any


class PipelineTemplateFactory:
    """Factory for creating pipeline templates"""
    
    @staticmethod
    def get_crm_template() -> Dict[str, Any]:
        """CRM pipeline template with AI-enhanced lead intelligence"""
        return {
            'pipeline': {
                'name': 'CRM Pipeline',
                'description': 'Customer Relationship Management system with AI-powered lead intelligence',
                'icon': 'users',
                'color': '#10B981',
                'pipeline_type': 'crm',
                'settings': {
                    'enable_stages': True,
                    'enable_tasks': True,
                    'enable_notes': True,
                    'default_stage': 'lead',
                }
            },
            'fields': [
                {
                    'name': 'Company Name',
                    'slug': 'company_name',
                    'field_type': 'text',
                    'is_required': True,
                    'display_order': 1,
                    'field_config': {
                        'max_length': 255,
                        'placeholder': 'Enter company name'
                    }
                },
                {
                    'name': 'Contact Person',
                    'slug': 'contact_person',
                    'field_type': 'text',
                    'is_required': True,
                    'display_order': 2,
                    'field_config': {
                        'max_length': 255
                    }
                },
                {
                    'name': 'Email',
                    'slug': 'email',
                    'field_type': 'email',
                    'is_required': True,
                    'display_order': 3,
                    'is_unique': True
                },
                {
                    'name': 'Phone',
                    'slug': 'phone',
                    'field_type': 'phone',
                    'display_order': 4
                },
                {
                    'name': 'Website',
                    'slug': 'website',
                    'field_type': 'url',
                    'display_order': 5
                },
                {
                    'name': 'Industry',
                    'slug': 'industry',
                    'field_type': 'select',
                    'display_order': 6,
                    'field_config': {
                        'options': [
                            {'value': 'technology', 'label': 'Technology'},
                            {'value': 'healthcare', 'label': 'Healthcare'},
                            {'value': 'finance', 'label': 'Finance'},
                            {'value': 'education', 'label': 'Education'},
                            {'value': 'retail', 'label': 'Retail'},
                            {'value': 'manufacturing', 'label': 'Manufacturing'},
                            {'value': 'other', 'label': 'Other'}
                        ],
                        'allow_custom': True
                    }
                },
                {
                    'name': 'Deal Value',
                    'slug': 'deal_value',
                    'field_type': 'decimal',
                    'display_order': 7,
                    'field_config': {
                        'min_value': 0,
                        'decimal_places': 2,
                        'max_digits': 12
                    }
                },
                {
                    'name': 'Stage',
                    'slug': 'stage',
                    'field_type': 'select',
                    'is_required': True,
                    'display_order': 8,
                    'field_config': {
                        'options': [
                            {'value': 'lead', 'label': 'Lead'},
                            {'value': 'qualified', 'label': 'Qualified'},
                            {'value': 'proposal', 'label': 'Proposal'},
                            {'value': 'negotiation', 'label': 'Negotiation'},
                            {'value': 'closed_won', 'label': 'Closed Won'},
                            {'value': 'closed_lost', 'label': 'Closed Lost'}
                        ]
                    }
                },
                {
                    'name': 'Expected Close Date',
                    'slug': 'expected_close_date',
                    'field_type': 'date',
                    'display_order': 9
                },
                {
                    'name': 'Lead Source',
                    'slug': 'lead_source',
                    'field_type': 'select',
                    'display_order': 10,
                    'field_config': {
                        'options': [
                            {'value': 'website', 'label': 'Website'},
                            {'value': 'referral', 'label': 'Referral'},
                            {'value': 'social_media', 'label': 'Social Media'},
                            {'value': 'cold_outreach', 'label': 'Cold Outreach'},
                            {'value': 'event', 'label': 'Event'},
                            {'value': 'advertising', 'label': 'Advertising'}
                        ],
                        'allow_custom': True
                    }
                },
                {
                    'name': 'Notes',
                    'slug': 'notes',
                    'field_type': 'textarea',
                    'display_order': 11,
                    'field_config': {
                        'max_length': 2000,
                        'multiline': True
                    }
                },
                {
                    'name': 'AI Lead Intelligence',
                    'slug': 'ai_lead_intelligence',
                    'field_type': 'ai_field',
                    'display_order': 12,
                    'is_ai_field': True,
                    'ai_config': {
                        'ai_prompt': 'Analyze this CRM lead comprehensively: Company: {company_name}, Contact: {contact_person}, Industry: {industry}, Deal Value: ${deal_value}, Stage: {stage}, Source: {lead_source}, Notes: {notes}. Use web search to research the company and provide: 1) Company intelligence, 2) Deal assessment, 3) Next action recommendations, 4) Risk factors.',
                        'enable_tools': True,
                        'allowed_tools': ['web_search'],
                        'include_all_fields': True,
                        'output_type': 'json',
                        'output_format': '{"company_intelligence": "", "deal_assessment": "", "next_actions": [], "risk_factors": [], "confidence_score": 85}',
                        'auto_update': True,
                        'update_triggers': ['notes', 'stage', 'deal_value'],
                        'cache_duration': 43200,  # 12 hours
                        'tool_budget': {'web_search': 5}
                    }
                }
            ]
        }
    
    @staticmethod
    def get_ats_template() -> Dict[str, Any]:
        """ATS (Applicant Tracking System) template with AI candidate analysis"""
        return {
            'pipeline': {
                'name': 'ATS Pipeline',
                'description': 'Applicant Tracking System for hiring with AI-powered candidate intelligence',
                'icon': 'briefcase',
                'color': '#8B5CF6',
                'pipeline_type': 'ats',
                'settings': {
                    'enable_stages': True,
                    'enable_interviews': True,
                    'enable_scoring': True,
                    'default_stage': 'applied',
                }
            },
            'fields': [
                {
                    'name': 'Full Name',
                    'slug': 'full_name',
                    'field_type': 'text',
                    'is_required': True,
                    'display_order': 1,
                    'field_config': {
                        'max_length': 255
                    }
                },
                {
                    'name': 'Email',
                    'slug': 'email',
                    'field_type': 'email',
                    'is_required': True,
                    'is_unique': True,
                    'display_order': 2
                },
                {
                    'name': 'Phone',
                    'slug': 'phone',
                    'field_type': 'phone',
                    'display_order': 3
                },
                {
                    'name': 'Position Applied',
                    'slug': 'position',
                    'field_type': 'text',
                    'is_required': True,
                    'display_order': 4
                },
                {
                    'name': 'Department',
                    'slug': 'department',
                    'field_type': 'select',
                    'display_order': 5,
                    'field_config': {
                        'options': [
                            {'value': 'engineering', 'label': 'Engineering'},
                            {'value': 'sales', 'label': 'Sales'},
                            {'value': 'marketing', 'label': 'Marketing'},
                            {'value': 'hr', 'label': 'Human Resources'},
                            {'value': 'finance', 'label': 'Finance'},
                            {'value': 'operations', 'label': 'Operations'}
                        ]
                    }
                },
                {
                    'name': 'Experience Level',
                    'slug': 'experience_level',
                    'field_type': 'select',
                    'display_order': 6,
                    'field_config': {
                        'options': [
                            {'value': 'entry', 'label': 'Entry Level (0-2 years)'},
                            {'value': 'mid', 'label': 'Mid Level (3-5 years)'},
                            {'value': 'senior', 'label': 'Senior Level (6-10 years)'},
                            {'value': 'lead', 'label': 'Lead/Principal (10+ years)'},
                            {'value': 'executive', 'label': 'Executive'}
                        ]
                    }
                },
                {
                    'name': 'Expected Salary',
                    'slug': 'expected_salary',
                    'field_type': 'decimal',
                    'display_order': 7,
                    'field_config': {
                        'min_value': 0,
                        'decimal_places': 0,
                        'max_digits': 10
                    }
                },
                {
                    'name': 'Resume',
                    'slug': 'resume',
                    'field_type': 'file',
                    'display_order': 8,
                    'field_config': {
                        'allowed_types': ['pdf', 'doc', 'docx'],
                        'max_size': 10485760  # 10MB
                    }
                },
                {
                    'name': 'Application Stage',
                    'slug': 'stage',
                    'field_type': 'select',
                    'is_required': True,
                    'display_order': 9,
                    'field_config': {
                        'options': [
                            {'value': 'applied', 'label': 'Applied'},
                            {'value': 'screening', 'label': 'Initial Screening'},
                            {'value': 'phone_interview', 'label': 'Phone Interview'},
                            {'value': 'technical_interview', 'label': 'Technical Interview'},
                            {'value': 'final_interview', 'label': 'Final Interview'},
                            {'value': 'offer_extended', 'label': 'Offer Extended'},
                            {'value': 'hired', 'label': 'Hired'},
                            {'value': 'rejected', 'label': 'Rejected'}
                        ]
                    }
                },
                {
                    'name': 'Interview Score',
                    'slug': 'interview_score',
                    'field_type': 'number',
                    'display_order': 10,
                    'field_config': {
                        'min_value': 1,
                        'max_value': 10,
                        'step': 0.5
                    }
                },
                {
                    'name': 'Skills',
                    'slug': 'skills',
                    'field_type': 'multiselect',
                    'display_order': 11,
                    'field_config': {
                        'options': [
                            {'value': 'python', 'label': 'Python'},
                            {'value': 'javascript', 'label': 'JavaScript'},
                            {'value': 'react', 'label': 'React'},
                            {'value': 'nodejs', 'label': 'Node.js'},
                            {'value': 'sql', 'label': 'SQL'},
                            {'value': 'aws', 'label': 'AWS'},
                            {'value': 'docker', 'label': 'Docker'},
                            {'value': 'kubernetes', 'label': 'Kubernetes'}
                        ],
                        'allow_custom': True,
                        'allow_multiple': True
                    }
                },
                {
                    'name': 'Interview Notes',
                    'slug': 'interview_notes',
                    'field_type': 'textarea',
                    'display_order': 12,
                    'field_config': {
                        'max_length': 3000,
                        'multiline': True
                    }
                },
                {
                    'name': 'AI Candidate Intelligence',
                    'slug': 'ai_candidate_intelligence',
                    'field_type': 'ai_field',
                    'display_order': 13,
                    'is_ai_field': True,
                    'ai_config': {
                        'ai_prompt': 'Comprehensive candidate analysis for {full_name} applying for {position} in {department}: Experience: {experience_level}, Skills: {skills}, Expected Salary: ${expected_salary}, Interview Score: {interview_score}/10, Notes: {interview_notes}. Use code interpreter to analyze resume if available. Provide: 1) Skill match analysis, 2) Cultural fit assessment, 3) Salary benchmarking, 4) Interview questions, 5) Hiring recommendation.',
                        'enable_tools': True,
                        'allowed_tools': ['code_interpreter', 'web_search'],
                        'include_all_fields': True,
                        'output_type': 'json',
                        'output_format': '{"skill_match_score": 85, "cultural_fit": "high", "salary_benchmark": {"min": 80000, "max": 120000}, "interview_questions": [], "recommendation": "strong_hire", "reasoning": ""}',
                        'auto_update': True,
                        'update_triggers': ['interview_score', 'interview_notes', 'skills'],
                        'cache_duration': 86400,  # 24 hours
                        'tool_budget': {'code_interpreter': 3, 'web_search': 3},
                        'timeout': 300
                    }
                }
            ]
        }
    
    @staticmethod
    def get_cms_template() -> Dict[str, Any]:
        """CMS (Content Management System) template with AI content intelligence"""
        return {
            'pipeline': {
                'name': 'CMS Pipeline',
                'description': 'Content Management System for articles and pages with AI-powered content intelligence',
                'icon': 'document-text',
                'color': '#F59E0B',
                'pipeline_type': 'cms',
                'settings': {
                    'enable_publishing': True,
                    'enable_seo': True,
                    'enable_categories': True,
                    'default_status': 'draft',
                }
            },
            'fields': [
                {
                    'name': 'Title',
                    'slug': 'title',
                    'field_type': 'text',
                    'is_required': True,
                    'display_order': 1,
                    'field_config': {
                        'max_length': 255
                    }
                },
                {
                    'name': 'Slug',
                    'slug': 'slug',
                    'field_type': 'text',
                    'is_required': True,
                    'is_unique': True,
                    'display_order': 2,
                    'field_config': {
                        'max_length': 255,
                        'pattern': '^[a-z0-9-]+$',
                        'help_text': 'URL-friendly version of the title'
                    }
                },
                {
                    'name': 'Content',
                    'slug': 'content',
                    'field_type': 'textarea',
                    'is_required': True,
                    'display_order': 3,
                    'field_config': {
                        'multiline': True
                    }
                },
                {
                    'name': 'Excerpt',
                    'slug': 'excerpt',
                    'field_type': 'textarea',
                    'display_order': 4,
                    'field_config': {
                        'max_length': 500,
                        'multiline': True
                    }
                },
                {
                    'name': 'Featured Image',
                    'slug': 'featured_image',
                    'field_type': 'image',
                    'display_order': 5,
                    'field_config': {
                        'max_size': 5242880,  # 5MB
                        'allowed_types': ['jpg', 'jpeg', 'png', 'webp']
                    }
                },
                {
                    'name': 'Category',
                    'slug': 'category',
                    'field_type': 'select',
                    'display_order': 6,
                    'field_config': {
                        'options': [
                            {'value': 'blog', 'label': 'Blog Post'},
                            {'value': 'news', 'label': 'News'},
                            {'value': 'tutorial', 'label': 'Tutorial'},
                            {'value': 'case_study', 'label': 'Case Study'},
                            {'value': 'page', 'label': 'Static Page'}
                        ],
                        'allow_custom': True
                    }
                },
                {
                    'name': 'Tags',
                    'slug': 'tags',
                    'field_type': 'multiselect',
                    'display_order': 7,
                    'field_config': {
                        'allow_custom': True,
                        'allow_multiple': True
                    }
                },
                {
                    'name': 'Status',
                    'slug': 'status',
                    'field_type': 'select',
                    'is_required': True,
                    'display_order': 8,
                    'field_config': {
                        'options': [
                            {'value': 'draft', 'label': 'Draft'},
                            {'value': 'review', 'label': 'Under Review'},
                            {'value': 'published', 'label': 'Published'},
                            {'value': 'archived', 'label': 'Archived'}
                        ]
                    }
                },
                {
                    'name': 'Publish Date',
                    'slug': 'publish_date',
                    'field_type': 'datetime',
                    'display_order': 9
                },
                {
                    'name': 'SEO Title',
                    'slug': 'seo_title',
                    'field_type': 'text',
                    'display_order': 10,
                    'field_config': {
                        'max_length': 60,
                        'help_text': 'Title for search engines (60 chars max)'
                    }
                },
                {
                    'name': 'SEO Description',
                    'slug': 'seo_description',
                    'field_type': 'textarea',
                    'display_order': 11,
                    'field_config': {
                        'max_length': 160,
                        'help_text': 'Description for search engines (160 chars max)'
                    }
                },
                {
                    'name': 'AI Content Intelligence',
                    'slug': 'ai_content_intelligence',
                    'field_type': 'ai_field',
                    'display_order': 12,
                    'is_ai_field': True,
                    'ai_config': {
                        'ai_prompt': 'Analyze this {category} content: Title: "{title}", Content: {content}, Category: {category}, Tags: {tags}, Status: {status}. Use web search for topic research if needed. Provide: 1) Content summary, 2) SEO optimization suggestions, 3) Related topics to explore, 4) Content performance prediction, 5) Social media suggestions.',
                        'enable_tools': True,
                        'allowed_tools': ['web_search'],
                        'include_all_fields': True,
                        'output_type': 'json',
                        'output_format': '{"summary": "", "seo_suggestions": [], "related_topics": [], "performance_prediction": "high", "social_suggestions": [], "readability_score": 85}',
                        'auto_update': True,
                        'update_triggers': ['content', 'title', 'category'],
                        'cache_duration': 21600,  # 6 hours
                        'tool_budget': {'web_search': 3}
                    }
                }
            ]
        }
    
    @staticmethod
    def get_project_template() -> Dict[str, Any]:
        """Project management template"""
        return {
            'pipeline': {
                'name': 'Project Management Pipeline',
                'description': 'Track projects, tasks, and deliverables',
                'icon': 'clipboard-list',
                'color': '#06B6D4',
                'pipeline_type': 'custom',
                'settings': {
                    'enable_milestones': True,
                    'enable_time_tracking': True,
                    'default_status': 'planning',
                }
            },
            'fields': [
                {
                    'name': 'Project Name',
                    'slug': 'project_name',
                    'field_type': 'text',
                    'is_required': True,
                    'display_order': 1,
                    'field_config': {'max_length': 255}
                },
                {
                    'name': 'Description',
                    'slug': 'description',
                    'field_type': 'textarea',
                    'display_order': 2,
                    'field_config': {'multiline': True}
                },
                {
                    'name': 'Project Manager',
                    'slug': 'project_manager',
                    'field_type': 'user',
                    'is_required': True,
                    'display_order': 3
                },
                {
                    'name': 'Start Date',
                    'slug': 'start_date',
                    'field_type': 'date',
                    'display_order': 4
                },
                {
                    'name': 'End Date',
                    'slug': 'end_date',
                    'field_type': 'date',
                    'display_order': 5
                },
                {
                    'name': 'Budget',
                    'slug': 'budget',
                    'field_type': 'decimal',
                    'display_order': 6,
                    'field_config': {'decimal_places': 2}
                },
                {
                    'name': 'Priority',
                    'slug': 'priority',
                    'field_type': 'select',
                    'display_order': 7,
                    'field_config': {
                        'options': [
                            {'value': 'low', 'label': 'Low'},
                            {'value': 'medium', 'label': 'Medium'},
                            {'value': 'high', 'label': 'High'},
                            {'value': 'urgent', 'label': 'Urgent'}
                        ]
                    }
                },
                {
                    'name': 'Status',
                    'slug': 'status',
                    'field_type': 'select',
                    'is_required': True,
                    'display_order': 8,
                    'field_config': {
                        'options': [
                            {'value': 'planning', 'label': 'Planning'},
                            {'value': 'active', 'label': 'Active'},
                            {'value': 'on_hold', 'label': 'On Hold'},
                            {'value': 'completed', 'label': 'Completed'},
                            {'value': 'cancelled', 'label': 'Cancelled'}
                        ]
                    }
                },
                {
                    'name': 'Progress',
                    'slug': 'progress',
                    'field_type': 'number',
                    'display_order': 9,
                    'field_config': {
                        'min_value': 0,
                        'max_value': 100
                    }
                },
                {
                    'name': 'Notes',
                    'slug': 'notes',
                    'field_type': 'textarea',
                    'display_order': 10,
                    'field_config': {'multiline': True}
                }
            ]
        }


# Template registry
SYSTEM_TEMPLATES = {
    'crm': PipelineTemplateFactory.get_crm_template,
    'ats': PipelineTemplateFactory.get_ats_template,
    'cms': PipelineTemplateFactory.get_cms_template,
    'project': PipelineTemplateFactory.get_project_template,
}


def get_template_by_category(category: str) -> Dict[str, Any]:
    """Get template by category"""
    template_func = SYSTEM_TEMPLATES.get(category)
    if template_func:
        return template_func()
    raise ValueError(f"Unknown template category: {category}")


def get_all_template_categories() -> List[str]:
    """Get all available template categories"""
    return list(SYSTEM_TEMPLATES.keys())