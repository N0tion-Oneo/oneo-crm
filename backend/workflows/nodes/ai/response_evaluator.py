"""
AI Response Evaluator Node - Evaluate responses using AI to determine next actions
"""
import logging
from typing import Dict, Any, List, Optional
from workflows.nodes.base import AsyncNodeProcessor
import openai
from django.conf import settings
import json

logger = logging.getLogger(__name__)


class AIResponseEvaluatorProcessor(AsyncNodeProcessor):
    """Evaluate responses using AI to determine conversation flow"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["evaluation_type"],
        "properties": {
            "evaluation_type": {
                "type": "string",
                "enum": ["objective", "sentiment", "intent", "custom"],
                "default": "objective",
                "description": "Type of evaluation to perform",
                "ui_hints": {
                    "widget": "radio"
                }
            },
            "response_source": {
                "type": "string",
                "description": "Path to response in context (e.g., 'last_message')",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "{{last_message}} or node_123.output"
                }
            },
            "response": {
                "type": "string",
                "description": "Direct response to evaluate (if not using response_source)",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 4,
                    "placeholder": "Paste response text to evaluate",
                    "show_when": {"response_source": ""}
                }
            },
            "objective": {
                "type": "string",
                "description": "Conversation objective for evaluation",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 3,
                    "placeholder": "Get the prospect to schedule a demo call",
                    "show_when": {"evaluation_type": "objective"}
                }
            },
            "evaluation_criteria": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"}
                    }
                },
                "description": "Custom criteria for evaluation",
                "ui_hints": {
                    "widget": "criteria_builder",
                    "show_when": {"evaluation_type": "custom"}
                }
            },
            "threshold": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "default": 0.7,
                "description": "Score threshold for positive outcome",
                "ui_hints": {
                    "widget": "slider",
                    "step": 0.05
                }
            },
            "use_scoring": {
                "type": "boolean",
                "default": False,
                "description": "Get detailed scoring with JSON response"
            },
            "fallback_outcome": {
                "type": "string",
                "enum": ["continue", "stop", "escalate"],
                "default": "continue",
                "description": "Action if evaluation fails",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "branch_mapping": {
                "type": "object",
                "properties": {
                    "success_path": {"type": "string"},
                    "failure_path": {"type": "string"},
                    "escalation_path": {"type": "string"},
                    "recovery_path": {"type": "string"},
                    "opt_out_path": {"type": "string"}
                },
                "description": "Map evaluation outcomes to workflow branches",
                "ui_hints": {
                    "widget": "branch_mapper",
                    "section": "advanced"
                }
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "ai_response_evaluator"
        self.supports_replay = True
        self.supports_checkpoints = True

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process AI response evaluation"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Extract configuration
        evaluation_type = config.get('evaluation_type', 'objective')
        evaluation_criteria = config.get('evaluation_criteria', [])
        threshold = config.get('threshold', 0.7)
        use_scoring = config.get('use_scoring', False)
        fallback_outcome = config.get('fallback_outcome', 'continue')
        branch_mapping = config.get('branch_mapping', {})

        # Get response to evaluate
        response_source = config.get('response_source', '')
        if response_source:
            response_to_evaluate = self._get_nested_value(context, response_source) or ''
        else:
            response_to_evaluate = config.get('response', '') or context.get('last_message', '') or context.get('response_content', '')

        # Context for evaluation
        conversation_objective = config.get('objective') or context.get('conversation_objective', '')
        conversation_history = context.get('conversation_history', [])
        participant_info = context.get('participant_info', {})

        try:
            # Perform evaluation based on type
            evaluation_result = await self._evaluate_response(
                response_to_evaluate,
                evaluation_type,
                evaluation_criteria,
                conversation_objective,
                conversation_history,
                participant_info,
                use_scoring
            )

            # Determine outcome
            outcome = self._determine_outcome(
                evaluation_result,
                threshold,
                evaluation_type
            )

            # Extract actionable insights
            insights = self._extract_insights(evaluation_result)

            # Update context with evaluation results
            context['evaluation_result'] = evaluation_result
            context['evaluation_outcome'] = outcome
            context['evaluation_insights'] = insights
            context['should_continue'] = outcome.get('continue_conversation', True)

            return {
                'success': True,
                'evaluation_type': evaluation_type,
                'outcome': outcome,
                'score': evaluation_result.get('score'),
                'confidence': evaluation_result.get('confidence'),
                'insights': insights,
                'next_action': outcome.get('recommended_action'),
                'should_continue': outcome.get('continue_conversation', True),
                'branch_to': outcome.get('branch_to')
            }

        except Exception as e:
            logger.error(f"AI response evaluation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'fallback_outcome': fallback_outcome
            }

    async def _evaluate_response(
        self,
        response: str,
        eval_type: str,
        criteria: List[Dict],
        objective: str,
        history: List,
        participant: Dict,
        use_scoring: bool
    ) -> Dict[str, Any]:
        """Evaluate response using AI"""

        system_prompt = self._build_evaluation_prompt(eval_type, criteria, use_scoring)
        user_prompt = self._build_evaluation_context(
            response,
            eval_type,
            criteria,
            objective,
            history,
            participant
        )

        try:
            openai.api_key = settings.OPENAI_API_KEY

            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent evaluation
                response_format={"type": "json_object"} if use_scoring else None
            )

            result_text = response.choices[0].message.content.strip()

            if use_scoring:
                try:
                    return json.loads(result_text)
                except json.JSONDecodeError:
                    # Fallback to text parsing
                    return self._parse_text_evaluation(result_text)
            else:
                return self._parse_text_evaluation(result_text)

        except Exception as e:
            logger.error(f"OpenAI API error in evaluation: {e}")
            raise

    def _build_evaluation_prompt(self, eval_type: str, criteria: List[Dict], use_scoring: bool) -> str:
        """Build system prompt for evaluation"""

        base_prompt = "You are an AI evaluator analyzing conversation responses."

        type_prompts = {
            'objective': """Evaluate if the response indicates the conversation objective has been met.
Consider partial progress, clear achievement, or need for continuation.""",

            'sentiment': """Analyze the sentiment and emotional tone of the response.
Identify positive, negative, or neutral sentiment with nuances.""",

            'intent': """Identify the intent behind the response.
Determine what the respondent wants or needs next.""",

            'custom': """Evaluate the response against the provided custom criteria.
Be thorough and specific in your assessment."""
        }

        prompt = f"{base_prompt}\n{type_prompts.get(eval_type, type_prompts['custom'])}"

        if criteria:
            criteria_text = "\n".join([f"- {c.get('name', 'Criterion')}: {c.get('description', '')}" for c in criteria])
            prompt += f"\n\nEvaluation Criteria:\n{criteria_text}"

        if use_scoring:
            prompt += """

Provide your evaluation in JSON format:
{
    "score": 0-1 float indicating match level,
    "confidence": 0-1 float indicating evaluation confidence,
    "met_criteria": ["list", "of", "met", "criteria"],
    "unmet_criteria": ["list", "of", "unmet", "criteria"],
    "summary": "Brief evaluation summary",
    "recommendation": "next action recommendation",
    "details": {}
}"""

        return prompt

    def _build_evaluation_context(
        self,
        response: str,
        eval_type: str,
        criteria: List[Dict],
        objective: str,
        history: List,
        participant: Dict
    ) -> str:
        """Build context for evaluation"""

        context_parts = [f"Response to evaluate: {response}"]

        if objective and eval_type == 'objective':
            context_parts.append(f"Conversation objective: {objective}")

        if history:
            recent = history[-2:] if len(history) > 2 else history
            history_text = "\n".join([f"{m.get('sender', 'Unknown')}: {m.get('content', '')}" for m in recent])
            context_parts.append(f"Recent context:\n{history_text}")

        if participant:
            context_parts.append(f"Respondent: {participant.get('name', 'Unknown')} - {participant.get('context', '')}")

        if eval_type == 'custom' and criteria:
            context_parts.append("Evaluate against the specified criteria and provide detailed assessment.")

        return "\n\n".join(context_parts)

    def _parse_text_evaluation(self, text: str) -> Dict[str, Any]:
        """Parse text evaluation into structured format"""

        result = {
            'score': 0.5,
            'confidence': 0.7,
            'summary': text[:200] if len(text) > 200 else text,
            'full_evaluation': text
        }

        # Simple keyword-based scoring
        positive_indicators = ['yes', 'agreed', 'accept', 'confirmed', 'positive', 'successful', 'achieved']
        negative_indicators = ['no', 'declined', 'reject', 'negative', 'failed', 'not interested']

        text_lower = text.lower()
        positive_count = sum(1 for word in positive_indicators if word in text_lower)
        negative_count = sum(1 for word in negative_indicators if word in text_lower)

        if positive_count > negative_count:
            result['score'] = min(0.7 + (positive_count * 0.1), 1.0)
        elif negative_count > positive_count:
            result['score'] = max(0.3 - (negative_count * 0.1), 0.0)

        return result

    def _determine_outcome(self, evaluation: Dict, threshold: float, eval_type: str) -> Dict[str, Any]:
        """Determine action outcome based on evaluation"""

        score = evaluation.get('score', 0.5)

        outcome = {
            'continue_conversation': True,
            'recommended_action': 'continue',
            'branch_to': None
        }

        if eval_type == 'objective':
            if score >= threshold:
                outcome['continue_conversation'] = False
                outcome['recommended_action'] = 'complete'
                outcome['branch_to'] = 'success_path'
            elif score < 0.3:
                outcome['recommended_action'] = 'escalate'
                outcome['branch_to'] = 'escalation_path'
            else:
                outcome['recommended_action'] = 'continue_modified'

        elif eval_type == 'sentiment':
            if score < 0.3:  # Very negative
                outcome['recommended_action'] = 'apologize_and_escalate'
                outcome['branch_to'] = 'recovery_path'
            elif score < 0.5:  # Negative
                outcome['recommended_action'] = 'address_concerns'
            elif score > 0.8:  # Very positive
                outcome['recommended_action'] = 'capitalize_momentum'

        elif eval_type == 'intent':
            # Map common intents to actions
            summary = evaluation.get('summary', '').lower()
            if 'question' in summary or 'asking' in summary:
                outcome['recommended_action'] = 'answer_question'
            elif 'complaint' in summary or 'issue' in summary:
                outcome['recommended_action'] = 'address_issue'
            elif 'interested' in summary:
                outcome['recommended_action'] = 'provide_details'
            elif 'not interested' in summary or 'unsubscribe' in summary:
                outcome['continue_conversation'] = False
                outcome['recommended_action'] = 'end_gracefully'
                outcome['branch_to'] = 'opt_out_path'

        return outcome

    def _extract_insights(self, evaluation: Dict) -> List[str]:
        """Extract actionable insights from evaluation"""

        insights = []

        if 'met_criteria' in evaluation:
            for criterion in evaluation['met_criteria']:
                insights.append(f"✓ {criterion}")

        if 'unmet_criteria' in evaluation:
            for criterion in evaluation['unmet_criteria']:
                insights.append(f"✗ {criterion}")

        if 'recommendation' in evaluation:
            insights.append(f"Recommendation: {evaluation['recommendation']}")

        # Add score-based insights
        score = evaluation.get('score', 0.5)
        if score > 0.8:
            insights.append("Strong positive response detected")
        elif score < 0.3:
            insights.append("Negative response - consider alternative approach")

        return insights

