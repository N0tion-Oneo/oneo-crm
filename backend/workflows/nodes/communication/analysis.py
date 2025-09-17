"""
Communication Analysis Node Processors - Analyze communications and score engagement
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from django.utils import timezone
from asgiref.sync import sync_to_async
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class CommunicationAnalysisProcessor(AsyncNodeProcessor):
    """Process communication analysis nodes with AI-powered insights"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["data_path", "analysis_type"],
        "properties": {
            "data_path": {
                "type": "string",
                "description": "Path to communication data in context",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "last_message.content or conversation.messages"
                }
            },
            "analysis_type": {
                "type": "string",
                "enum": ["sentiment", "intent", "engagement", "topic_extraction", "response_suggestion", "language_detection", "custom"],
                "default": "sentiment",
                "description": "Type of analysis to perform",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "ai_config": {
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "enum": ["gpt-4", "gpt-3.5-turbo", "claude-3"],
                        "default": "gpt-4"
                    },
                    "temperature": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 0.3
                    },
                    "max_tokens": {
                        "type": "integer",
                        "minimum": 100,
                        "maximum": 4000,
                        "default": 1000
                    }
                },
                "description": "AI model configuration",
                "ui_hints": {
                    "section": "advanced"
                }
            },
            "output_format": {
                "type": "string",
                "enum": ["structured", "raw"],
                "default": "structured",
                "description": "Output format for analysis results"
            },
            "intent_categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Custom intent categories for intent analysis",
                "ui_hints": {
                    "widget": "tag_input",
                    "show_when": {"analysis_type": "intent"}
                }
            },
            "custom_instructions": {
                "type": "string",
                "description": "Custom analysis instructions",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 4,
                    "placeholder": "Analyze this communication and provide insights about...",
                    "show_when": {"analysis_type": "custom"}
                }
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "analyze_communication"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process communication analysis node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Extract configuration
        analysis_type = config.get('analysis_type', 'sentiment')
        data_path = config.get('data_path', '')
        communication_data = self._get_nested_value(context, data_path) if data_path else None
        ai_config = config.get('ai_config', {})
        output_format = config.get('output_format', 'structured')  # structured, raw
        
        # Validate required fields
        if not communication_data:
            raise ValueError("Communication analysis requires communication data")
        
        try:
            # Generate analysis prompt based on type
            prompt = self._generate_analysis_prompt(analysis_type, communication_data, config)
            
            # Process with AI
            ai_result = await self._process_with_ai(prompt, ai_config, context)
            
            if not ai_result.get('success'):
                raise ValueError(f"AI analysis failed: {ai_result.get('error')}")
            
            # Parse and structure the result
            structured_result = await self._parse_analysis_result(
                analysis_type, ai_result.get('output', ''), communication_data
            )
            
            return {
                'success': True,
                'analysis_type': analysis_type,
                'communication_data_length': len(str(communication_data)),
                'structured_result': structured_result,
                'raw_ai_output': ai_result.get('output', '') if output_format == 'raw' else None,
                'ai_metadata': ai_result.get('ai_metadata', {}),
                'analyzed_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Communication analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'analysis_type': analysis_type,
                'communication_data_length': len(str(communication_data)) if communication_data else 0
            }
    
    def _generate_analysis_prompt(self, analysis_type: str, communication_data: Any, node_data: Dict[str, Any]) -> str:
        """Generate analysis prompt based on type"""
        
        if analysis_type == 'sentiment':
            return f"""Analyze the sentiment of this communication and return a JSON response:

Communication: {communication_data}

Return JSON format:
{{
  "sentiment": "positive|negative|neutral",
  "confidence": 0.85,
  "reasoning": "brief explanation",
  "key_indicators": ["indicator1", "indicator2"]
}}"""
        
        elif analysis_type == 'intent':
            categories = node_data.get('intent_categories', [
                'inquiry', 'complaint', 'purchase_intent', 'support_request',
                'cancellation', 'upgrade', 'information_request', 'other'
            ])
            
            return f"""Analyze the intent of this communication and categorize it:

Communication: {communication_data}

Available categories: {', '.join(categories)}

Return JSON format:
{{
  "intent": "category_name",
  "confidence": 0.90,
  "reasoning": "brief explanation",
  "urgency": "low|medium|high",
  "requires_response": true|false
}}"""
        
        elif analysis_type == 'engagement':
            return f"""Score the engagement level of this communication from 1-10:

Communication: {communication_data}

Consider factors like:
- Response time
- Message length and detail
- Questions asked
- Enthusiasm level
- Forward momentum

Return JSON format:
{{
  "engagement_score": 7.5,
  "engagement_level": "high|medium|low",
  "factors": ["factor1", "factor2"],
  "improvement_suggestions": ["suggestion1"]
}}"""
        
        elif analysis_type == 'topic_extraction':
            return f"""Extract key topics and themes from this communication:

Communication: {communication_data}

Return JSON format:
{{
  "topics": ["topic1", "topic2", "topic3"],
  "main_theme": "primary theme",
  "entities": {{"person": ["name1"], "company": ["company1"], "product": ["product1"]}},
  "action_items": ["action1", "action2"]
}}"""
        
        elif analysis_type == 'response_suggestion':
            return f"""Suggest an appropriate response to this communication:

Communication: {communication_data}

Return JSON format:
{{
  "response_tone": "professional|friendly|empathetic|urgent",
  "suggested_response": "draft response text",
  "key_points_to_address": ["point1", "point2"],
  "follow_up_needed": true|false,
  "follow_up_timeframe": "24 hours|3 days|1 week"
}}"""
        
        elif analysis_type == 'language_detection':
            return f"""Detect the language and analyze communication quality:

Communication: {communication_data}

Return JSON format:
{{
  "language": "en|es|fr|de|etc",
  "confidence": 0.95,
  "formality_level": "formal|informal|casual",
  "clarity_score": 8.5,
  "translation_needed": true|false
}}"""
        
        else:
            # General analysis
            instructions = node_data.get('custom_instructions', 'Analyze this communication and provide insights')
            return f"""{instructions}

Communication: {communication_data}

Provide structured analysis with insights and recommendations."""
    
    async def _process_with_ai(self, prompt: str, ai_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process prompt with AI"""
        
        try:
            # Use AI prompt processor
            from workflows.nodes.ai.prompt import AIPromptProcessor
            ai_processor = AIPromptProcessor()
            
            ai_node_config = {
                'type': 'AI_PROMPT',
                'data': {
                    'prompt': prompt,
                    'ai_config': {
                        'model': ai_config.get('model', 'gpt-4'),
                        'temperature': ai_config.get('temperature', 0.3),  # Lower for analysis
                        'max_tokens': ai_config.get('max_tokens', 1000),
                        **ai_config
                    }
                }
            }
            
            result = await ai_processor.process(ai_node_config, context)
            return result
            
        except Exception as e:
            logger.error(f"AI processing failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _parse_analysis_result(self, analysis_type: str, ai_output: str, communication_data: Any) -> Dict[str, Any]:
        """Parse and structure AI analysis result"""
        
        try:
            import json
            
            # Try to parse as JSON first
            try:
                structured_result = json.loads(ai_output)
                return structured_result
            except json.JSONDecodeError:
                # Fallback parsing for different analysis types
                return self._fallback_parse_result(analysis_type, ai_output, communication_data)
                
        except Exception as e:
            logger.warning(f"Failed to parse analysis result: {e}")
            return {
                'raw_output': ai_output,
                'parse_error': str(e),
                'analysis_type': analysis_type
            }
    
    def _fallback_parse_result(self, analysis_type: str, ai_output: str, communication_data: Any) -> Dict[str, Any]:
        """Fallback parsing when JSON parsing fails"""
        
        result = {
            'raw_output': ai_output,
            'analysis_type': analysis_type,
            'parsed_with_fallback': True
        }
        
        if analysis_type == 'sentiment':
            # Extract sentiment from text
            lower_output = ai_output.lower()
            if 'positive' in lower_output:
                result['sentiment'] = 'positive'
            elif 'negative' in lower_output:
                result['sentiment'] = 'negative'
            else:
                result['sentiment'] = 'neutral'
            
            # Try to extract confidence
            import re
            confidence_match = re.search(r'(\d+(?:\.\d+)?)\s*%', ai_output)
            if confidence_match:
                result['confidence'] = float(confidence_match.group(1)) / 100
            else:
                result['confidence'] = 0.5
        
        elif analysis_type == 'engagement':
            # Extract score from text
            import re
            score_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:/10|out of 10)', ai_output)
            if score_match:
                result['engagement_score'] = float(score_match.group(1))
            else:
                result['engagement_score'] = 5.0
        
        return result
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate communication analysis node inputs"""
        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Check required fields
        if not config.get('data_path'):
            return False

        # Validate analysis type
        analysis_type = config.get('analysis_type', 'sentiment')
        valid_types = [
            'sentiment', 'intent', 'engagement', 'topic_extraction',
            'response_suggestion', 'language_detection', 'custom'
        ]
        if analysis_type not in valid_types:
            return False

        # Validate output format
        output_format = config.get('output_format', 'structured')
        if output_format not in ['structured', 'raw']:
            return False

        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for communication analysis node"""
        checkpoint = await super().create_checkpoint(node_config, context)

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Get communication data size for checkpoint
        data_path = config.get('data_path', '')
        communication_data = self._get_nested_value(context, data_path) if data_path else None

        checkpoint.update({
            'analysis_config': {
                'analysis_type': config.get('analysis_type', 'sentiment'),
                'data_path': data_path,
                'communication_data_size': len(str(communication_data)) if communication_data else 0,
                'output_format': config.get('output_format', 'structured'),
                'ai_model': config.get('ai_config', {}).get('model', 'gpt-4')
            }
        })

        return checkpoint


class EngagementScoringProcessor(AsyncNodeProcessor):
    """Process engagement scoring nodes with comprehensive metrics"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["contact_id_path"],
        "properties": {
            "contact_id_path": {
                "type": "string",
                "description": "Path to contact ID in context",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "contact.id or record.contact_id"
                }
            },
            "scoring_method": {
                "type": "string",
                "enum": ["simple", "comprehensive", "ai_powered"],
                "default": "comprehensive",
                "description": "Scoring calculation method",
                "ui_hints": {
                    "widget": "radio"
                }
            },
            "time_window_days": {
                "type": "integer",
                "minimum": 1,
                "maximum": 365,
                "default": 30,
                "description": "Days of history to consider for scoring"
            },
            "scoring_criteria": {
                "type": "object",
                "properties": {
                    "weight_email_opens": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 0.2
                    },
                    "weight_email_clicks": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 0.3
                    },
                    "weight_responses": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 0.5
                    }
                },
                "description": "Custom scoring weights",
                "ui_hints": {
                    "section": "advanced",
                    "show_when": {"scoring_method": ["comprehensive", "simple"]}
                }
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "score_engagement"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process engagement scoring node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Extract configuration
        contact_id_path = config.get('contact_id_path', '')
        contact_id = self._get_nested_value(context, contact_id_path) if contact_id_path else None
        scoring_criteria = config.get('scoring_criteria', {})
        scoring_method = config.get('scoring_method', 'comprehensive')  # simple, comprehensive, ai_powered
        time_window_days = config.get('time_window_days', 30)
        
        # Validate required fields
        if not contact_id:
            raise ValueError("Engagement scoring requires contact_id")
        
        try:
            # Get contact data
            contact_data = await self._get_contact_data(contact_id)
            
            if not contact_data:
                raise ValueError(f"Contact {contact_id} not found")
            
            # Calculate engagement score based on method
            if scoring_method == 'simple':
                score_result = await self._calculate_simple_score(contact_data, scoring_criteria)
            elif scoring_method == 'comprehensive':
                score_result = await self._calculate_comprehensive_score(
                    contact_data, scoring_criteria, time_window_days
                )
            elif scoring_method == 'ai_powered':
                score_result = await self._calculate_ai_powered_score(
                    contact_data, scoring_criteria, context
                )
            else:
                raise ValueError(f"Unknown scoring method: {scoring_method}")
            
            # Update contact with engagement score
            await self._update_contact_engagement_score(contact_id, score_result)
            
            return {
                'success': True,
                'contact_id': contact_id,
                'engagement_score': score_result['score'],
                'engagement_level': score_result['level'],
                'scoring_method': scoring_method,
                'scoring_breakdown': score_result['breakdown'],
                'recommendations': score_result.get('recommendations', []),
                'calculated_at': timezone.now().isoformat(),
                'time_window_days': time_window_days
            }
            
        except Exception as e:
            logger.error(f"Engagement scoring failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'contact_id': contact_id,
                'scoring_method': scoring_method
            }
    
    async def _get_contact_data(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """Get contact data for scoring"""
        
        try:
            from pipelines.models import Record
            
            contact = await sync_to_async(Record.objects.get)(id=contact_id, is_deleted=False)
            return contact.data
            
        except Exception as e:
            logger.error(f"Failed to get contact data: {e}")
            return None
    
    async def _calculate_simple_score(self, contact_data: Dict[str, Any], criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate simple engagement score"""
        
        score = 5.0  # Base score
        breakdown = {}
        
        # Email engagement
        email_opens = contact_data.get('email_opens', 0)
        email_clicks = contact_data.get('email_clicks', 0)
        if email_opens > 0:
            score += min(email_opens * 0.5, 2.0)
            breakdown['email_opens'] = min(email_opens * 0.5, 2.0)
        
        if email_clicks > 0:
            score += min(email_clicks * 1.0, 3.0)
            breakdown['email_clicks'] = min(email_clicks * 1.0, 3.0)
        
        # Website engagement
        page_views = contact_data.get('page_views', 0)
        if page_views > 0:
            score += min(page_views * 0.2, 2.0)
            breakdown['page_views'] = min(page_views * 0.2, 2.0)
        
        # Response rate
        responses = contact_data.get('responses', 0)
        messages_sent = contact_data.get('messages_sent', 1)
        response_rate = responses / messages_sent if messages_sent > 0 else 0
        score += response_rate * 5.0
        breakdown['response_rate'] = response_rate * 5.0
        
        # Cap at 10
        score = min(score, 10.0)
        
        # Determine level
        if score >= 8.0:
            level = 'high'
        elif score >= 5.0:
            level = 'medium'
        else:
            level = 'low'
        
        return {
            'score': round(score, 2),
            'level': level,
            'breakdown': breakdown
        }
    
    async def _calculate_comprehensive_score(
        self, 
        contact_data: Dict[str, Any], 
        criteria: Dict[str, Any], 
        time_window_days: int
    ) -> Dict[str, Any]:
        """Calculate comprehensive engagement score with multiple factors"""
        
        from datetime import datetime, timedelta
        
        score = 0.0
        breakdown = {}
        max_score = 100.0
        
        # Time-based activity scoring
        recent_cutoff = datetime.now() - timedelta(days=time_window_days)
        
        # Communication frequency (20 points max)
        recent_communications = self._count_recent_activities(
            contact_data.get('communication_history', []), recent_cutoff
        )
        comm_score = min(recent_communications * 2.0, 20.0)
        score += comm_score
        breakdown['communication_frequency'] = comm_score
        
        # Response quality (25 points max)
        avg_response_time = contact_data.get('avg_response_time_hours', 48)
        response_quality_score = max(25.0 - (avg_response_time / 24 * 5), 0)
        score += response_quality_score
        breakdown['response_quality'] = response_quality_score
        
        # Content engagement (20 points max)
        email_engagement = (
            contact_data.get('email_opens', 0) * 1.0 +
            contact_data.get('email_clicks', 0) * 2.0 +
            contact_data.get('email_replies', 0) * 3.0
        )
        content_score = min(email_engagement, 20.0)
        score += content_score
        breakdown['content_engagement'] = content_score
        
        # Meeting participation (15 points max)
        meetings_attended = contact_data.get('meetings_attended', 0)
        meetings_scheduled = contact_data.get('meetings_scheduled', 0)
        meeting_score = min((meetings_attended * 5.0) + (meetings_scheduled * 3.0), 15.0)
        score += meeting_score
        breakdown['meeting_participation'] = meeting_score
        
        # Sales progression (20 points max)
        current_stage = contact_data.get('sales_stage', 'lead')
        stage_scores = {
            'lead': 2, 'qualified': 5, 'opportunity': 10, 
            'proposal': 15, 'negotiation': 18, 'closed_won': 20
        }
        progression_score = stage_scores.get(current_stage, 0)
        score += progression_score
        breakdown['sales_progression'] = progression_score
        
        # Convert to 1-10 scale
        final_score = (score / max_score) * 10
        final_score = min(final_score, 10.0)
        
        # Determine level
        if final_score >= 7.5:
            level = 'high'
        elif final_score >= 4.0:
            level = 'medium'
        else:
            level = 'low'
        
        # Generate recommendations
        recommendations = self._generate_recommendations(final_score, breakdown, contact_data)
        
        return {
            'score': round(final_score, 2),
            'level': level,
            'breakdown': breakdown,
            'recommendations': recommendations
        }
    
    async def _calculate_ai_powered_score(
        self, 
        contact_data: Dict[str, Any], 
        criteria: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate AI-powered engagement score"""
        
        try:
            # Use AI analysis processor
            from workflows.nodes.ai.prompt import AIPromptProcessor
            ai_processor = AIPromptProcessor()
            
            prompt = f"""Analyze this contact's engagement level and provide a comprehensive score from 1-10:

Contact Data: {contact_data}

Scoring Criteria: {criteria}

Consider factors like:
- Communication frequency and quality
- Response times and rates
- Content engagement (opens, clicks, downloads)
- Meeting participation
- Sales progression
- Recent activity trends

Return JSON format:
{{
  "engagement_score": 7.5,
  "engagement_level": "high|medium|low",
  "reasoning": "detailed explanation",
  "strengths": ["strength1", "strength2"],
  "improvement_areas": ["area1", "area2"],
  "recommendations": ["rec1", "rec2"]
}}"""
            
            ai_config = {
                'type': 'AI_PROMPT',
                'data': {
                    'prompt': prompt,
                    'ai_config': {
                        'model': 'gpt-4',
                        'temperature': 0.3,
                        'max_tokens': 1000
                    }
                }
            }
            
            ai_result = await ai_processor.process(ai_config, context)
            
            if ai_result.get('success'):
                try:
                    import json
                    ai_analysis = json.loads(ai_result.get('output', '{}'))
                    
                    return {
                        'score': ai_analysis.get('engagement_score', 5.0),
                        'level': ai_analysis.get('engagement_level', 'medium'),
                        'breakdown': {'ai_analysis': ai_analysis.get('reasoning', '')},
                        'recommendations': ai_analysis.get('recommendations', [])
                    }
                except json.JSONDecodeError:
                    # Fallback to simple scoring
                    return await self._calculate_simple_score(contact_data, criteria)
            else:
                # Fallback to simple scoring
                return await self._calculate_simple_score(contact_data, criteria)
                
        except Exception as e:
            logger.error(f"AI-powered scoring failed: {e}")
            # Fallback to simple scoring
            return await self._calculate_simple_score(contact_data, criteria)
    
    def _count_recent_activities(self, activities: List[Dict], cutoff_date: datetime) -> int:
        """Count activities since cutoff date"""
        
        count = 0
        for activity in activities:
            try:
                activity_date = datetime.fromisoformat(activity.get('date', ''))
                if activity_date >= cutoff_date:
                    count += 1
            except (ValueError, TypeError):
                continue
        
        return count
    
    def _generate_recommendations(
        self, 
        score: float, 
        breakdown: Dict[str, Any], 
        contact_data: Dict[str, Any]
    ) -> List[str]:
        """Generate engagement improvement recommendations"""
        
        recommendations = []
        
        if score < 4.0:
            recommendations.append("Consider re-engagement campaign with personalized content")
            recommendations.append("Schedule a discovery call to understand current needs")
        
        if breakdown.get('response_quality', 0) < 10:
            recommendations.append("Improve response time and follow-up consistency")
        
        if breakdown.get('content_engagement', 0) < 10:
            recommendations.append("Send more targeted, valuable content")
            recommendations.append("Try different content formats (video, infographics)")
        
        if breakdown.get('meeting_participation', 0) < 5:
            recommendations.append("Propose a meeting or demo to increase engagement")
        
        if contact_data.get('sales_stage') == 'lead':
            recommendations.append("Focus on lead qualification and nurturing")
        
        return recommendations[:3]  # Limit to top 3 recommendations
    
    async def _update_contact_engagement_score(self, contact_id: str, score_result: Dict[str, Any]):
        """Update contact with new engagement score"""
        
        try:
            from pipelines.models import Record
            
            contact = await sync_to_async(Record.objects.get)(id=contact_id, is_deleted=False)
            
            # Update engagement data
            contact.data.update({
                'engagement_score': score_result['score'],
                'engagement_level': score_result['level'],
                'engagement_last_calculated': timezone.now().isoformat(),
                'engagement_breakdown': score_result['breakdown']
            })
            
            await sync_to_async(contact.save)()
            
            logger.info(f"Engagement score updated for contact {contact_id}: {score_result['score']}")
            
        except Exception as e:
            logger.warning(f"Failed to update contact engagement score: {e}")
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate engagement scoring node inputs"""
        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Check required fields
        if not config.get('contact_id_path'):
            return False

        # Validate scoring method
        scoring_method = config.get('scoring_method', 'comprehensive')
        valid_methods = ['simple', 'comprehensive', 'ai_powered']
        if scoring_method not in valid_methods:
            return False

        # Validate time window
        time_window_days = config.get('time_window_days', 30)
        if not isinstance(time_window_days, int) or time_window_days <= 0:
            return False

        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for engagement scoring node"""
        checkpoint = await super().create_checkpoint(node_config, context)

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Resolve contact ID for checkpoint
        contact_id_path = config.get('contact_id_path', '')
        resolved_contact_id = self._get_nested_value(context, contact_id_path) if contact_id_path else None

        checkpoint.update({
            'engagement_scoring_config': {
                'contact_id_path': contact_id_path,
                'resolved_contact_id': resolved_contact_id,
                'scoring_method': config.get('scoring_method', 'comprehensive'),
                'time_window_days': config.get('time_window_days', 30),
                'criteria_count': len(config.get('scoring_criteria', {}))
            }
        })

        return checkpoint