"""
Communication Workflow Templates using reusable workflow building blocks
Modern templates that leverage the reusable workflow system
"""
from typing import Dict, Any, List
from django.contrib.auth import get_user_model

User = get_user_model()


def create_email_nurture_sequence_template(
    steps: List[Dict[str, Any]],
    ai_enhanced: bool = True,
    business_hours_only: bool = True
) -> Dict[str, Any]:
    """
    Create email nurture sequence using reusable workflow components
    """
    nodes = []
    edges = []
    node_counter = 0
    
    def get_next_node_id():
        nonlocal node_counter
        node_counter += 1
        return f"node_{node_counter}"
    
    # Start node
    start_node_id = get_next_node_id()
    nodes.append({
        "id": start_node_id,
        "type": "start",
        "position": {"x": 100, "y": 100},
        "data": {
            "name": "Email Nurture Start",
            "description": "Start email nurture sequence"
        }
    })
    prev_node_id = start_node_id
    
    # Contact validation using reusable workflow
    contact_validation_id = get_next_node_id()
    nodes.append({
        "id": contact_validation_id,
        "type": "SUB_WORKFLOW",
        "position": {"x": 100, "y": 200},
        "data": {
            "name": "Validate & Enrich Contact",
            "description": "Ensure contact data is complete and enriched",
            "workflow_name": "Contact Enrichment",
            "version": "1.0",
            "inputs": {
                "contact_data": "{trigger_data.contact_data}",
                "enrichment_sources": ["ai_analysis"],
                "fields_to_enrich": ["company", "title", "industry"]
            },
            "outputs": ["enriched_data", "confidence_score"]
        }
    })
    edges.append({
        "id": f"edge_{prev_node_id}_to_{contact_validation_id}",
        "source": prev_node_id,
        "target": contact_validation_id,
        "type": "default"
    })
    prev_node_id = contact_validation_id
    
    # Lead scoring (if enabled)
    if ai_enhanced:
        lead_scoring_id = get_next_node_id()
        nodes.append({
            "id": lead_scoring_id,
            "type": "SUB_WORKFLOW",
            "position": {"x": 100, "y": 300},
            "data": {
                "name": "Score Lead Quality",
                "description": "AI-powered lead scoring for personalization",
                "workflow_name": "Lead Scoring",
                "version": "1.0",
                "inputs": {
                    "lead_data": f"{{node_{contact_validation_id}.outputs.enriched_data}}",
                    "scoring_criteria": {
                        "company_size": {"weight": 0.2},
                        "industry_fit": {"weight": 0.3},
                        "engagement": {"weight": 0.5}
                    },
                    "threshold": 60
                },
                "outputs": ["score", "grade", "qualified", "reasoning"]
            }
        })
        edges.append({
            "id": f"edge_{prev_node_id}_to_{lead_scoring_id}",
            "source": prev_node_id,
            "target": lead_scoring_id,
            "type": "default"
        })
        prev_node_id = lead_scoring_id
    
    # Process each email step
    for i, step in enumerate(steps):
        y_position = 400 + (i * 200)
        
        # Content personalization
        content_node_id = get_next_node_id()
        if ai_enhanced:
            nodes.append({
                "id": content_node_id,
                "type": "AI_PROMPT",
                "position": {"x": 100, "y": y_position},
                "data": {
                    "name": f"Personalize Email {i + 1}",
                    "description": f"AI-personalized content for step {i + 1}",
                    "prompt": f"""
Create a personalized email for this nurture sequence step.

Contact Information:
{{node_{contact_validation_id}.outputs.enriched_data}}

Lead Score & Profile:
{{node_{lead_scoring_id}.outputs.reasoning if 'lead_scoring_id' in locals() else 'No scoring data'}}

Email Template:
{step.get('content_template', '')}

Step Objective: {step.get('objective', 'Nurture relationship')}

Personalization Guidelines:
- Use contact's name and company
- Reference their industry if known
- Adjust tone based on lead score
- Include relevant pain points
- Keep it professional but engaging

Return only the personalized email content with subject line:
""",
                    "ai_config": {
                        "model": "gpt-4",
                        "temperature": 0.7,
                        "max_tokens": 500
                    }
                }
            })
        else:
            # Template-based personalization
            nodes.append({
                "id": content_node_id,
                "type": "MERGE_DATA",
                "position": {"x": 100, "y": y_position},
                "data": {
                    "name": f"Personalize Email {i + 1}",
                    "description": f"Template-based personalization for step {i + 1}",
                    "template": step.get('content_template', ''),
                    "merge_sources": [
                        f"node_{contact_validation_id}.outputs.enriched_data",
                        "trigger_data"
                    ],
                    "output_field": "personalized_content"
                }
            })
        
        edges.append({
            "id": f"edge_{prev_node_id}_to_{content_node_id}",
            "source": prev_node_id,
            "target": content_node_id,
            "type": "default"
        })
        
        # Email sending
        email_node_id = get_next_node_id()
        nodes.append({
            "id": email_node_id,
            "type": "UNIPILE_SEND_EMAIL",
            "position": {"x": 100, "y": y_position + 50},
            "data": {
                "name": f"Send Email {i + 1}",
                "description": f"Send nurture email step {i + 1}",
                "user_id": "{trigger_data.user_id}",
                "recipient_email": f"{{node_{contact_validation_id}.outputs.enriched_data.email}}",
                "subject": step.get('subject_template', f'Follow-up #{i + 1}'),
                "content": f"{{node_{content_node_id}.output}}",
                "tracking_enabled": True,
                "sequence_metadata": {
                    "sequence_name": "{workflow.name}",
                    "step_number": i + 1,
                    "total_steps": len(steps)
                }
            }
        })
        
        edges.append({
            "id": f"edge_{content_node_id}_to_{email_node_id}",
            "source": content_node_id,
            "target": email_node_id,
            "type": "default"
        })
        
        # Wait delay (if specified)
        delay_days = step.get('delay_days', 0)
        if delay_days > 0 and i < len(steps) - 1:  # Don't add delay after last step
            wait_node_id = get_next_node_id()
            nodes.append({
                "id": wait_node_id,
                "type": "WAIT_DELAY",
                "position": {"x": 100, "y": y_position + 100},
                "data": {
                    "name": f"Wait {delay_days} Days",
                    "description": f"Wait {delay_days} days before next email",
                    "delay_type": "days",
                    "delay_value": delay_days,
                    "business_hours_only": business_hours_only
                }
            })
            
            edges.append({
                "id": f"edge_{email_node_id}_to_{wait_node_id}",
                "source": email_node_id,
                "target": wait_node_id,
                "type": "default"
            })
            prev_node_id = wait_node_id
        else:
            prev_node_id = email_node_id
    
    # End node
    end_node_id = get_next_node_id()
    nodes.append({
        "id": end_node_id,
        "type": "end",
        "position": {"x": 100, "y": 400 + (len(steps) * 200) + 100},
        "data": {
            "name": "Nurture Complete",
            "description": "Email nurture sequence completed"
        }
    })
    
    edges.append({
        "id": f"edge_{prev_node_id}_to_{end_node_id}",
        "source": prev_node_id,
        "target": end_node_id,
        "type": "default"
    })
    
    return {
        "name": "Email Nurture Sequence",
        "description": f"AI-enhanced email nurture with {len(steps)} touchpoints",
        "category": "Communication",
        "workflow_definition": {
            "nodes": nodes,
            "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 1},
            "metadata": {
                "template_type": "email_nurture",
                "uses_reusable_workflows": True,
                "ai_enhanced": ai_enhanced,
                "business_hours_only": business_hours_only,
                "total_steps": len(steps)
            }
        },
        "estimated_setup_time": "5 minutes",
        "complexity": "Medium"
    }


def create_multichannel_outreach_template(
    channels: List[str] = ["email", "linkedin"],
    sequence_steps: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create multi-channel outreach sequence template
    """
    if sequence_steps is None:
        sequence_steps = [
            {"channel": "email", "delay_days": 0, "objective": "introduction"},
            {"channel": "linkedin", "delay_days": 3, "objective": "connection"},
            {"channel": "email", "delay_days": 7, "objective": "follow_up"},
            {"channel": "linkedin", "delay_days": 14, "objective": "value_proposition"}
        ]
    
    nodes = []
    edges = []
    node_counter = 0
    
    def get_next_node_id():
        nonlocal node_counter
        node_counter += 1
        return f"node_{node_counter}"
    
    # Start node
    start_node_id = get_next_node_id()
    nodes.append({
        "id": start_node_id,
        "type": "start",
        "position": {"x": 100, "y": 100},
        "data": {
            "name": "Multi-channel Outreach Start",
            "description": "Start multi-channel outreach sequence"
        }
    })
    prev_node_id = start_node_id
    
    # Contact enrichment and channel availability check
    enrichment_node_id = get_next_node_id()
    nodes.append({
        "id": enrichment_node_id,
        "type": "SUB_WORKFLOW",
        "position": {"x": 100, "y": 200},
        "data": {
            "name": "Enrich Contact & Check Channels",
            "description": "Enrich contact data and verify channel availability",
            "workflow_name": "Contact Enrichment",
            "version": "1.0",
            "inputs": {
                "contact_data": "{trigger_data.contact_data}",
                "enrichment_sources": ["ai_analysis", "linkedin"],
                "fields_to_enrich": ["email", "linkedin_url", "phone", "company", "title"]
            },
            "outputs": ["enriched_data", "confidence_score", "sources_used"]
        }
    })
    
    edges.append({
        "id": f"edge_{prev_node_id}_to_{enrichment_node_id}",
        "source": prev_node_id,
        "target": enrichment_node_id,
        "type": "default"
    })
    prev_node_id = enrichment_node_id
    
    # Lead scoring for personalization
    scoring_node_id = get_next_node_id()
    nodes.append({
        "id": scoring_node_id,
        "type": "SUB_WORKFLOW",
        "position": {"x": 100, "y": 300},
        "data": {
            "name": "Score Lead for Personalization",
            "description": "Score lead to customize messaging approach",
            "workflow_name": "Lead Scoring",
            "version": "1.0",
            "inputs": {
                "lead_data": f"{{node_{enrichment_node_id}.outputs.enriched_data}}",
                "scoring_criteria": {
                    "seniority": {"weight": 0.4},
                    "company_size": {"weight": 0.3},
                    "industry_relevance": {"weight": 0.3}
                },
                "threshold": 50
            },
            "outputs": ["score", "grade", "reasoning", "recommendations"]
        }
    })
    
    edges.append({
        "id": f"edge_{prev_node_id}_to_{scoring_node_id}",
        "source": prev_node_id,
        "target": scoring_node_id,
        "type": "default"
    })
    prev_node_id = scoring_node_id
    
    # Process each outreach step
    for i, step in enumerate(sequence_steps):
        y_position = 400 + (i * 250)
        channel = step.get('channel', 'email')
        delay_days = step.get('delay_days', 0)
        objective = step.get('objective', 'outreach')
        
        # Add delay before step if specified
        if delay_days > 0:
            wait_node_id = get_next_node_id()
            nodes.append({
                "id": wait_node_id,
                "type": "WAIT_DELAY",
                "position": {"x": 100, "y": y_position},
                "data": {
                    "name": f"Wait {delay_days} Days",
                    "description": f"Wait {delay_days} days before {channel} outreach",
                    "delay_type": "days",
                    "delay_value": delay_days,
                    "business_hours_only": True
                }
            })
            
            edges.append({
                "id": f"edge_{prev_node_id}_to_{wait_node_id}",
                "source": prev_node_id,
                "target": wait_node_id,
                "type": "default"
            })
            prev_node_id = wait_node_id
            y_position += 50
        
        # Content generation
        content_node_id = get_next_node_id()
        nodes.append({
            "id": content_node_id,
            "type": "AI_PROMPT",
            "position": {"x": 100, "y": y_position},
            "data": {
                "name": f"Generate {channel.title()} Content {i + 1}",
                "description": f"AI-generated {channel} message for step {i + 1}",
                "prompt": f"""
Create a personalized {channel} message for this outreach sequence.

Contact Profile:
{{node_{enrichment_node_id}.outputs.enriched_data}}

Lead Score & Analysis:
{{node_{scoring_node_id}.outputs.reasoning}}

Channel: {channel}
Objective: {objective}
Step: {i + 1} of {len(sequence_steps)}

Guidelines for {channel}:
{_get_channel_guidelines(channel)}

Create an engaging, personalized message that:
1. References their background/company appropriately
2. Provides clear value proposition
3. Has appropriate call-to-action for {objective}
4. Matches the {channel} platform tone

Return the message content only:
""",
                "ai_config": {
                    "model": "gpt-4",
                    "temperature": 0.8,
                    "max_tokens": 300
                }
            }
        })
        
        edges.append({
            "id": f"edge_{prev_node_id}_to_{content_node_id}",
            "source": prev_node_id,
            "target": content_node_id,
            "type": "default"
        })
        
        # Send message
        send_node_id = get_next_node_id()
        
        if channel == "email":
            node_type = "UNIPILE_SEND_EMAIL"
            send_config = {
                "recipient_email": f"{{node_{enrichment_node_id}.outputs.enriched_data.email}}",
                "subject": f"{{node_{content_node_id}.output.subject}}",
                "content": f"{{node_{content_node_id}.output.body}}"
            }
        elif channel == "linkedin":
            node_type = "UNIPILE_SEND_LINKEDIN"
            send_config = {
                "recipient_profile": f"{{node_{enrichment_node_id}.outputs.enriched_data.linkedin_url}}",
                "message_content": f"{{node_{content_node_id}.output}}"
            }
        elif channel == "whatsapp":
            node_type = "UNIPILE_SEND_WHATSAPP"
            send_config = {
                "recipient_phone": f"{{node_{enrichment_node_id}.outputs.enriched_data.phone}}",
                "message_content": f"{{node_{content_node_id}.output}}"
            }
        else:
            # Default to email
            node_type = "UNIPILE_SEND_EMAIL"
            send_config = {
                "recipient_email": f"{{node_{enrichment_node_id}.outputs.enriched_data.email}}",
                "subject": f"Follow-up #{i + 1}",
                "content": f"{{node_{content_node_id}.output}}"
            }
        
        nodes.append({
            "id": send_node_id,
            "type": node_type,
            "position": {"x": 100, "y": y_position + 50},
            "data": {
                "name": f"Send {channel.title()} {i + 1}",
                "description": f"Send {channel} message for step {i + 1}",
                "user_id": "{trigger_data.user_id}",
                **send_config,
                "tracking_enabled": True,
                "sequence_metadata": {
                    "sequence_name": "{workflow.name}",
                    "channel": channel,
                    "step_number": i + 1,
                    "objective": objective
                }
            }
        })
        
        edges.append({
            "id": f"edge_{content_node_id}_to_{send_node_id}",
            "source": content_node_id,
            "target": send_node_id,
            "type": "default"
        })
        
        prev_node_id = send_node_id
    
    # End node
    end_node_id = get_next_node_id()
    nodes.append({
        "id": end_node_id,
        "type": "end",
        "position": {"x": 100, "y": 400 + (len(sequence_steps) * 250) + 100},
        "data": {
            "name": "Outreach Complete",
            "description": "Multi-channel outreach sequence completed"
        }
    })
    
    edges.append({
        "id": f"edge_{prev_node_id}_to_{end_node_id}",
        "source": prev_node_id,
        "target": end_node_id,
        "type": "default"
    })
    
    return {
        "name": "Multi-channel Outreach Sequence",
        "description": f"AI-powered outreach across {len(set(step.get('channel') for step in sequence_steps))} channels",
        "category": "Communication",
        "workflow_definition": {
            "nodes": nodes,
            "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 1},
            "metadata": {
                "template_type": "multichannel_outreach",
                "uses_reusable_workflows": True,
                "channels": list(set(step.get('channel') for step in sequence_steps)),
                "total_steps": len(sequence_steps)
            }
        },
        "estimated_setup_time": "10 minutes", 
        "complexity": "Medium-High"
    }


def _get_channel_guidelines(channel: str) -> str:
    """Get writing guidelines for specific communication channels"""
    guidelines = {
        "email": """
- Professional but approachable tone
- Clear subject line that creates curiosity
- 2-3 short paragraphs maximum
- Strong call-to-action
- Professional signature
""",
        "linkedin": """
- Conversational and networking-focused tone
- Reference their LinkedIn profile/posts if relevant
- Keep message under 200 words
- Focus on mutual connections or interests
- Professional but personal approach
""",
        "whatsapp": """
- Casual but respectful tone
- Very brief messages (under 100 words)
- Use emojis sparingly
- Quick, easy call-to-action
- Mobile-friendly formatting
""",
        "sms": """
- Very concise (160 characters max)
- Clear identification of sender
- Direct call-to-action
- Include opt-out option
- Professional but brief
"""
    }
    return guidelines.get(channel, guidelines["email"])


# Export available templates
COMMUNICATION_TEMPLATES = {
    "email_nurture_sequence": create_email_nurture_sequence_template,
    "multichannel_outreach": create_multichannel_outreach_template,
}