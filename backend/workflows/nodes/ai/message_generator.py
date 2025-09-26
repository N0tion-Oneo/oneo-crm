"""
AI Message Generator Node - Generate contextual messages using AI
"""
import logging
from typing import Dict, Any, Optional
from workflows.nodes.base import AsyncNodeProcessor
import openai
from django.conf import settings

logger = logging.getLogger(__name__)


class AIMessageGeneratorProcessor(AsyncNodeProcessor):
    """Generate AI-powered messages based on context and objectives"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["prompt_template"],
        "properties": {
            "prompt_template": {
                "type": "string",
                "minLength": 1,
                "description": "Template for message generation with context variables",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 6,
                    "placeholder": "Follow up on {{last_message}} and mention {{product_name}}. Address their concern about {{concern}} and suggest next steps."
                }
            },
            "tone": {
                "type": "string",
                "enum": ["professional", "friendly", "casual", "formal", "persuasive", "empathetic"],
                "default": "professional",
                "description": "Message tone and style",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "target_channel": {
                "type": "string",
                "enum": ["email", "whatsapp", "linkedin", "sms"],
                "default": "email",
                "description": "Target communication channel for formatting",
                "ui_hints": {
                    "widget": "radio"
                }
            },
            "max_length": {
                "type": "integer",
                "minimum": 10,
                "maximum": 4000,
                "default": 500,
                "description": "Maximum message length in characters"
            },
            "include_context": {
                "type": "boolean",
                "default": True,
                "description": "Include conversation history and context in generation"
            },
            "temperature": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 2.0,
                "default": 0.7,
                "description": "AI creativity level (0=focused, 2=creative)",
                "ui_hints": {
                    "widget": "slider",
                    "step": 0.1
                }
            },
            "fallback_message": {
                "type": "string",
                "description": "Fallback message if generation fails",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 4,
                    "placeholder": "Thank you for your message. We'll get back to you soon."
                }
            },
            "system_instructions": {
                "type": "string",
                "description": "Additional instructions for the AI",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 3,
                    "placeholder": "Always include a call-to-action. Avoid technical jargon.",
                    "section": "advanced"
                }
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "ai_message_generator"
        self.supports_replay = True
        self.supports_checkpoints = True

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process AI message generation"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Extract configuration
        prompt_template = config.get('prompt_template', '')
        tone = config.get('tone', 'professional')
        max_length = config.get('max_length', 500)
        temperature = config.get('temperature', 0.7)
        include_context = config.get('include_context', True)
        fallback_message = config.get('fallback_message', '')
        system_instructions = config.get('system_instructions', '')

        # Optional context enrichment
        conversation_history = context.get('conversation_history', [])
        last_message = context.get('last_message', '')
        participant_info = context.get('participant_info', {})
        objective = context.get('conversation_objective', '')
        current_state = context.get('conversation_state', {})

        # Channel-specific formatting
        target_channel = config.get('target_channel') or context.get('channel', 'email')

        try:
            # Build the AI prompt
            system_prompt = self._build_system_prompt(tone, target_channel, max_length, system_instructions)
            user_prompt = self._build_user_prompt(
                prompt_template,
                conversation_history,
                last_message,
                participant_info,
                objective,
                current_state,
                include_context,
                context
            )

            # Generate message using AI
            generated_message = await self._generate_with_ai(
                system_prompt,
                user_prompt,
                temperature,
                max_length
            )

            # Format for specific channel
            formatted_message = self._format_for_channel(
                generated_message,
                target_channel
            )

            # Update context with generated message
            context['generated_message'] = formatted_message
            context['last_generated_message'] = formatted_message

            return {
                'success': True,
                'generated_message': formatted_message,
                'channel': target_channel,
                'tone': tone,
                'prompt_used': user_prompt[:200] + '...' if len(user_prompt) > 200 else user_prompt,
                'message_length': len(formatted_message)
            }

        except Exception as e:
            logger.error(f"AI message generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'fallback_message': fallback_message
            }

    def _build_system_prompt(self, tone: str, channel: str, max_length: int, additional_instructions: str = '') -> str:
        """Build system prompt for AI"""

        tone_instructions = {
            'professional': 'Use a professional, business-appropriate tone.',
            'friendly': 'Use a warm, friendly, and approachable tone.',
            'casual': 'Use a casual, conversational tone.',
            'formal': 'Use a formal, respectful tone.',
            'persuasive': 'Use a persuasive, compelling tone.',
            'empathetic': 'Use an empathetic, understanding tone.'
        }

        channel_instructions = {
            'email': 'Format as a professional email without subject line.',
            'whatsapp': 'Format as a WhatsApp message - concise and conversational.',
            'linkedin': 'Format as a LinkedIn message - professional networking style.',
            'sms': 'Format as an SMS - very brief, under 160 characters if possible.'
        }

        system_prompt = f"""You are an AI assistant generating messages for business communication.
{tone_instructions.get(tone, tone_instructions['professional'])}
{channel_instructions.get(channel, channel_instructions['email'])}
Keep the message under {max_length} characters.
Do not include greetings or signatures unless specifically requested.
Focus on the core message content."""

        if additional_instructions:
            system_prompt += f"\n\nAdditional Instructions: {additional_instructions}"

        return system_prompt

    def _build_user_prompt(
        self,
        template: str,
        history: list,
        last_message: str,
        participant: dict,
        objective: str,
        state: dict,
        include_context: bool,
        context: dict
    ) -> str:
        """Build user prompt with context"""

        # Format template with context variables
        formatted_template = self.format_template(template, context)

        prompt_parts = []

        if objective:
            prompt_parts.append(f"Conversation Objective: {objective}")

        if include_context and history:
            # Include recent conversation history
            recent_history = history[-3:] if len(history) > 3 else history
            history_text = "\n".join([
                f"{msg.get('sender', 'Unknown')}: {msg.get('content', '')}"
                for msg in recent_history
            ])
            prompt_parts.append(f"Recent Conversation:\n{history_text}")

        if last_message:
            prompt_parts.append(f"Last Message Received: {last_message}")

        if participant:
            prompt_parts.append(f"Recipient Info: {participant.get('name', 'Unknown')} - {participant.get('context', '')}")

        if state:
            prompt_parts.append(f"Current State: {state}")

        prompt_parts.append(f"Generate a message that: {formatted_template}")

        return "\n\n".join(prompt_parts)

    async def _generate_with_ai(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate message using OpenAI"""

        try:
            openai.api_key = settings.OPENAI_API_KEY

            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            # Return a fallback or re-raise based on configuration
            raise

    def _format_for_channel(self, message: str, channel: str) -> str:
        """Format message for specific channel"""

        if channel == 'sms':
            # Ensure SMS length limits
            if len(message) > 160:
                message = message[:157] + '...'
        elif channel == 'whatsapp':
            # WhatsApp formatting (basic emoji support, etc.)
            message = message.replace('**', '*')  # Bold formatting
        elif channel == 'linkedin':
            # LinkedIn message limits
            if len(message) > 300:
                message = message[:297] + '...'

        return message

    def _format_template(self, template: str, context: Dict[str, Any]) -> str:
        """Format template with context variables"""
        if not template:
            return ''

        try:
            return template.format(**context)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template
        except Exception as e:
            logger.error(f"Template formatting error: {e}")
            return template

