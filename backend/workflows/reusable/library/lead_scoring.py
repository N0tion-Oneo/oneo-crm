"""
Reusable Lead Scoring Workflow
AI-powered lead scoring with customizable criteria
"""

LEAD_SCORING_WORKFLOW = {
    "name": "Lead Scoring",
    "version": "1.0",
    "description": "AI-powered lead scoring with customizable criteria and detailed reasoning",
    "category": "CRM",
    "input_schema": {
        "type": "object",
        "properties": {
            "lead_data": {
                "type": "object",
                "description": "Lead information to score",
                "required": True
            },
            "scoring_criteria": {
                "type": "object",
                "description": "Custom scoring criteria",
                "default": {
                    "company_size": {"weight": 0.3, "min_employees": 10},
                    "budget": {"weight": 0.25, "min_budget": 10000},
                    "timeline": {"weight": 0.2, "urgent_keywords": ["asap", "immediately", "urgent"]},
                    "fit": {"weight": 0.25, "industry_match": True}
                }
            },
            "threshold": {
                "type": "number",
                "description": "Minimum score threshold for qualified leads",
                "default": 70
            },
            "model": {
                "type": "string",
                "description": "AI model to use for scoring",
                "default": "gpt-4",
                "enum": ["gpt-4", "gpt-3.5-turbo", "claude-3"]
            }
        },
        "required": ["lead_data"]
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "score": {
                "type": "number",
                "description": "Lead score from 0-100"
            },
            "grade": {
                "type": "string",
                "description": "Letter grade based on score",
                "enum": ["A", "B", "C", "D", "F"]
            },
            "qualified": {
                "type": "boolean",
                "description": "Whether lead meets qualification threshold"
            },
            "reasoning": {
                "type": "string",
                "description": "AI explanation of scoring decision"
            },
            "factors": {
                "type": "array",
                "description": "Key factors that influenced the score",
                "items": {"type": "string"}
            },
            "recommendations": {
                "type": "array",
                "description": "Next steps recommendations",
                "items": {"type": "string"}
            }
        },
        "required": ["score", "grade", "qualified", "reasoning"]
    },
    "workflow_definition": {
        "nodes": [
            {
                "id": "start_node",
                "type": "start",
                "position": {"x": 100, "y": 100},
                "data": {
                    "name": "Start Lead Scoring",
                    "description": "Begin lead scoring process"
                }
            },
            {
                "id": "extract_lead_info",
                "type": "MERGE_DATA",
                "position": {"x": 100, "y": 200},
                "data": {
                    "name": "Extract Lead Information",
                    "description": "Extract and structure lead data",
                    "merge_sources": ["trigger_data.lead_data"],
                    "output_fields": [
                        "company_name", "industry", "company_size", "budget", 
                        "timeline", "contact_name", "contact_title", "pain_points"
                    ]
                }
            },
            {
                "id": "analyze_lead_fit",
                "type": "AI_ANALYSIS",
                "position": {"x": 100, "y": 300},
                "data": {
                    "name": "Analyze Lead Fit",
                    "description": "AI analysis of lead qualification factors",
                    "analysis_type": "lead_qualification",
                    "data_source": "node_extract_lead_info.output",
                    "ai_config": {
                        "model": "{trigger_data.model}",
                        "temperature": 0.3,
                        "max_tokens": 300
                    },
                    "analysis_prompt": """
Analyze this lead data for B2B qualification:

Lead Information:
{node_extract_lead_info.output}

Scoring Criteria:
{trigger_data.scoring_criteria}

Evaluate the lead across these dimensions:
1. Company Size & Stability
2. Budget Indicators
3. Timeline Urgency
4. Industry/Solution Fit
5. Decision-Making Authority

Return JSON with:
- company_score (0-100)
- budget_score (0-100) 
- timeline_score (0-100)
- fit_score (0-100)
- authority_score (0-100)
- key_factors (array of strings)
- risk_factors (array of strings)
"""
                }
            },
            {
                "id": "calculate_final_score",
                "type": "AI_PROMPT",
                "position": {"x": 100, "y": 400},
                "data": {
                    "name": "Calculate Final Score",
                    "description": "Calculate weighted final score with reasoning",
                    "prompt": """
Based on the lead analysis, calculate a final lead score:

Analysis Results:
{node_analyze_lead_fit.output}

Scoring Criteria Weights:
{trigger_data.scoring_criteria}

Lead Data:
{trigger_data.lead_data}

Calculate a final score (0-100) using the weighted criteria and provide:

1. FINAL_SCORE: [0-100 number]
2. GRADE: [A/B/C/D/F based on: A=90+, B=80-89, C=70-79, D=60-69, F=<60]
3. QUALIFIED: [true/false based on threshold: {trigger_data.threshold}]
4. REASONING: [2-3 sentence explanation of the score]
5. TOP_FACTORS: [3-5 key factors that drove the score]
6. RECOMMENDATIONS: [2-4 specific next steps]

Return as JSON format:
{
  "score": 85,
  "grade": "B", 
  "qualified": true,
  "reasoning": "Strong lead with good company fit...",
  "factors": ["Large company size", "Clear budget authority"],
  "recommendations": ["Schedule demo", "Send case study"]
}
""",
                    "ai_config": {
                        "model": "{trigger_data.model}",
                        "temperature": 0.1,
                        "max_tokens": 400
                    }
                }
            },
            {
                "id": "format_output",
                "type": "MERGE_DATA",
                "position": {"x": 100, "y": 500},
                "data": {
                    "name": "Format Final Output",
                    "description": "Structure the final scoring output",
                    "merge_sources": ["node_calculate_final_score.output"],
                    "merge_strategy": "parse_json",
                    "output_mapping": {
                        "score": "score",
                        "grade": "grade", 
                        "qualified": "qualified",
                        "reasoning": "reasoning",
                        "factors": "factors",
                        "recommendations": "recommendations"
                    }
                }
            },
            {
                "id": "end_node",
                "type": "end",
                "position": {"x": 100, "y": 600},
                "data": {
                    "name": "Lead Scoring Complete",
                    "description": "Lead scoring process completed"
                }
            }
        ],
        "edges": [
            {
                "id": "edge_start_to_extract",
                "source": "start_node",
                "target": "extract_lead_info",
                "type": "default"
            },
            {
                "id": "edge_extract_to_analyze",
                "source": "extract_lead_info", 
                "target": "analyze_lead_fit",
                "type": "default"
            },
            {
                "id": "edge_analyze_to_calculate",
                "source": "analyze_lead_fit",
                "target": "calculate_final_score", 
                "type": "default"
            },
            {
                "id": "edge_calculate_to_format",
                "source": "calculate_final_score",
                "target": "format_output",
                "type": "default"
            },
            {
                "id": "edge_format_to_end",
                "source": "format_output",
                "target": "end_node",
                "type": "default"
            }
        ],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
        "metadata": {
            "reusable_workflow": True,
            "category": "CRM",
            "estimated_execution_time": "5-10 seconds",
            "ai_model_usage": "Medium"
        }
    }
}


CONTACT_ENRICHMENT_WORKFLOW = {
    "name": "Contact Enrichment",
    "version": "1.0", 
    "description": "Enrich contact data using multiple sources and AI analysis",
    "category": "CRM",
    "input_schema": {
        "type": "object",
        "properties": {
            "contact_data": {
                "type": "object",
                "description": "Basic contact information to enrich",
                "required": True
            },
            "enrichment_sources": {
                "type": "array",
                "description": "Data sources to use for enrichment",
                "items": {"type": "string"},
                "default": ["clearbit", "hunter", "linkedin", "ai_analysis"]
            },
            "fields_to_enrich": {
                "type": "array", 
                "description": "Specific fields to focus on enriching",
                "items": {"type": "string"},
                "default": ["company", "title", "industry", "location", "social_profiles"]
            }
        },
        "required": ["contact_data"]
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "enriched_data": {
                "type": "object",
                "description": "Enriched contact information"
            },
            "confidence_score": {
                "type": "number", 
                "description": "Confidence in enrichment accuracy (0-100)"
            },
            "sources_used": {
                "type": "array",
                "description": "Data sources that provided information",
                "items": {"type": "string"}
            },
            "fields_enriched": {
                "type": "array",
                "description": "Fields that were successfully enriched", 
                "items": {"type": "string"}
            }
        },
        "required": ["enriched_data", "confidence_score", "sources_used"]
    },
    "workflow_definition": {
        "nodes": [
            {
                "id": "start_enrichment",
                "type": "start",
                "position": {"x": 100, "y": 100},
                "data": {
                    "name": "Start Contact Enrichment",
                    "description": "Begin contact data enrichment process"
                }
            },
            {
                "id": "validate_input",
                "type": "CONDITION",
                "position": {"x": 100, "y": 200},
                "data": {
                    "name": "Validate Input Data",
                    "description": "Check if we have minimum required data",
                    "conditions": [
                        {
                            "left": {"context_path": "trigger_data.contact_data.email"},
                            "operator": "exists",
                            "output": "has_email"
                        },
                        {
                            "left": {"context_path": "trigger_data.contact_data.company"},
                            "operator": "exists", 
                            "output": "has_company"
                        }
                    ],
                    "default_output": "insufficient_data"
                }
            },
            {
                "id": "ai_profile_analysis",
                "type": "AI_ANALYSIS",
                "position": {"x": 100, "y": 300},
                "data": {
                    "name": "AI Profile Analysis",
                    "description": "Use AI to infer missing contact details",
                    "analysis_type": "contact_profiling",
                    "data_source": "trigger_data.contact_data",
                    "ai_config": {
                        "model": "gpt-4",
                        "temperature": 0.2,
                        "max_tokens": 300
                    }
                }
            },
            {
                "id": "merge_enriched_data",
                "type": "MERGE_DATA", 
                "position": {"x": 100, "y": 400},
                "data": {
                    "name": "Merge Enriched Data",
                    "description": "Combine original and enriched data",
                    "merge_sources": [
                        "trigger_data.contact_data",
                        "node_ai_profile_analysis.output"
                    ],
                    "merge_strategy": "preserve_original",
                    "confidence_scoring": True
                }
            },
            {
                "id": "end_enrichment",
                "type": "end",
                "position": {"x": 100, "y": 500},
                "data": {
                    "name": "Enrichment Complete",
                    "description": "Contact enrichment process completed"
                }
            }
        ],
        "edges": [
            {
                "id": "edge_start_to_validate",
                "source": "start_enrichment",
                "target": "validate_input",
                "type": "default"
            },
            {
                "id": "edge_validate_to_analyze",
                "source": "validate_input",
                "target": "ai_profile_analysis",
                "type": "conditional",
                "condition": "has_email"
            },
            {
                "id": "edge_analyze_to_merge",
                "source": "ai_profile_analysis",
                "target": "merge_enriched_data",
                "type": "default"
            },
            {
                "id": "edge_merge_to_end",
                "source": "merge_enriched_data", 
                "target": "end_enrichment",
                "type": "default"
            }
        ],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
        "metadata": {
            "reusable_workflow": True,
            "category": "CRM",
            "estimated_execution_time": "3-8 seconds",
            "ai_model_usage": "Medium"
        }
    }
}