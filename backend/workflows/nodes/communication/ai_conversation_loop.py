"""
AI-Powered Conversation Loop Processor
Manages complete conversation flows with AI-driven objective evaluation and response generation
"""
import asyncio
import json
import logging
import importlib.util
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from asgiref.sync import sync_to_async

from workflows.nodes.base import AsyncNodeProcessor
from workflows.ai_integration import workflow_ai_processor
from communications.models import (
    Message, Conversation, Participant, ConversationParticipant,
    MessageDirection, MessageStatus, ChannelType
)
# Import needs to be done dynamically due to module/directory name conflict
# Will import communication_service instance when needed
from pipelines.models import Record

logger = logging.getLogger(__name__)


class AIConversationLoopProcessor(AsyncNodeProcessor):
    """
    Single node that manages an entire AI-powered conversation loop.
    Internally orchestrates sending, waiting, evaluating, and responding.
    """

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["objective", "initial_message"],
        "properties": {
            "objective": {
                "type": "string",
                "minLength": 1,
                "description": "The conversation objective to achieve",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 3,
                    "placeholder": "Schedule a demo call with the prospect"
                }
            },
            "initial_message": {
                "type": "string",
                "minLength": 1,
                "description": "The first message to send",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 6,
                    "placeholder": "Hi {{contact_name}}, I noticed you viewed our pricing page..."
                }
            },
            "success_criteria": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Criteria to determine success",
                "ui_hints": {
                    "widget": "tag_input",
                    "placeholder": "Add success criteria (e.g., Meeting scheduled, Phone number provided)"
                }
            },
            "max_iterations": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "default": 5,
                "description": "Maximum conversation turns"
            },
            "response_timeout_hours": {
                "type": "number",
                "minimum": 0.5,
                "maximum": 168,
                "default": 24,
                "description": "Hours to wait for response"
            },
            "channel": {
                "type": "string",
                "enum": ["email", "whatsapp", "linkedin", "sms"],
                "default": "email",
                "description": "Communication channel",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "recipient_source": {
                "type": "string",
                "description": "Path to recipient in context",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "{{record.email}} or trigger.contact"
                }
            },
            "ai_model": {
                "type": "string",
                "enum": ["gpt-4", "gpt-3.5-turbo", "claude-3"],
                "default": "gpt-4",
                "description": "AI model for evaluation and generation",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "temperature": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "default": 0.7,
                "description": "AI creativity level",
                "ui_hints": {
                    "widget": "slider",
                    "step": 0.1
                }
            },
            "enable_handoff": {
                "type": "boolean",
                "default": True,
                "description": "Enable human handoff when needed"
            },
            "handoff_criteria": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Triggers for human handoff",
                "ui_hints": {
                    "widget": "tag_input",
                    "placeholder": "Add handoff triggers (e.g., Complaint, Technical question)",
                    "show_when": {"enable_handoff": True}
                }
            },
            "opt_out_keywords": {
                "type": "array",
                "items": {"type": "string"},
                "default": ["unsubscribe", "stop", "opt out", "remove me"],
                "description": "Keywords to detect opt-out intent",
                "ui_hints": {
                    "widget": "tag_input"
                }
            },
            "follow_up_delay_hours": {
                "type": "number",
                "minimum": 0,
                "maximum": 72,
                "default": 0,
                "description": "Hours to wait between follow-ups"
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "ai_conversation_loop"
        self.supports_replay = True
        self.supports_checkpoints = True
        # Communication service will be imported lazily when needed
        # due to module/directory naming conflict
        self._communication_service = None

    @property
    def communication_service(self):
        """Lazy load communication service to avoid import conflicts"""
        if self._communication_service is None:
            # Get the services.py file directly by manipulating import path
            spec = importlib.util.spec_from_file_location(
                "communications_services_file",
                "/Users/joshcowan/Oneo CRM/backend/communications/services.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._communication_service = module.communication_service
        return self._communication_service

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the conversation loop"""

        node_data = node_config.get('data', {})

        # Get or initialize conversation state
        conversation_state = await self._get_or_init_conversation_state(node_data, context)

        try:
            # Check if we're at max iterations
            if conversation_state['iteration'] >= conversation_state['max_iterations']:
                return await self._handle_max_iterations(conversation_state)

            # If first iteration, send initial message
            if conversation_state['iteration'] == 0:
                await self._send_initial_message(conversation_state, node_data, context)
                conversation_state['iteration'] += 1

                # Store state for next iteration
                return {
                    'success': True,
                    'continue_loop': True,
                    'conversation_state': conversation_state,
                    'action': 'initial_message_sent',
                    'message': 'Initial message sent, waiting for response'
                }

            # Wait for response
            response = await self._wait_for_response(conversation_state, node_data)

            if not response:
                # Timeout reached
                return await self._handle_timeout(conversation_state)

            # Add response to conversation history
            conversation_state['messages'].append({
                'direction': 'inbound',
                'content': response.get('content', ''),
                'channel': response.get('channel', conversation_state['current_channel']),
                'timestamp': response.get('timestamp', timezone.now().isoformat()),
                'sender': response.get('sender', 'participant')
            })

            # AI evaluates the response AND generates next message
            evaluation = await self._ai_evaluate_and_respond(
                objective=conversation_state['objective'],
                success_criteria=conversation_state['success_criteria'],
                conversation_history=conversation_state['messages'],
                latest_response=response.get('content', ''),
                ai_config={
                    'model': node_data.get('config', {}).get('ai_model', 'gpt-4'),
                    'temperature': node_data.get('config', {}).get('temperature', 0.7)
                },
                participant_info=conversation_state.get('participant_info', {})
            )

            # Store evaluation in state
            conversation_state['evaluations'].append({
                'iteration': conversation_state['iteration'],
                'confidence': evaluation.get('confidence', 0),
                'objective_achieved': evaluation.get('objective_achieved', False),
                'analysis': evaluation.get('analysis', '')
            })

            # Handle evaluation results
            if evaluation.get('objective_achieved'):
                return await self._complete_success(conversation_state, evaluation)

            if evaluation.get('opt_out_detected'):
                return await self._handle_opt_out(conversation_state, evaluation)

            if evaluation.get('human_handoff_needed'):
                return await self._create_handoff_task(conversation_state, evaluation, context)

            # Send AI-generated response
            if evaluation.get('next_message'):
                await self._send_response(
                    evaluation['next_message'],
                    conversation_state,
                    response.get('channel', conversation_state['current_channel'])
                )

                # Add sent message to history
                conversation_state['messages'].append({
                    'direction': 'outbound',
                    'content': evaluation['next_message'],
                    'channel': response.get('channel', conversation_state['current_channel']),
                    'timestamp': timezone.now().isoformat(),
                    'sender': 'ai'
                })

            # Update state for next iteration
            conversation_state['iteration'] += 1
            conversation_state['last_evaluation'] = evaluation

            return {
                'success': True,
                'continue_loop': not evaluation.get('objective_achieved', False),
                'conversation_state': conversation_state,
                'evaluation': evaluation,
                'action': 'response_sent',
                'iteration': conversation_state['iteration']
            }

        except Exception as e:
            logger.error(f"Conversation loop error: {e}")
            return {
                'success': False,
                'error': str(e),
                'conversation_state': conversation_state
            }

    async def _get_or_init_conversation_state(
        self,
        node_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get existing or initialize new conversation state"""

        # Check if we have existing state from previous iteration
        existing_state = context.get('conversation_state')
        if existing_state:
            return existing_state

        # Initialize new conversation state
        record_id = context.get('record_id')
        participant_info = {}

        # Get participant info if we have a record
        if record_id:
            try:
                record = await sync_to_async(Record.objects.get)(id=record_id)
                participant_info = {
                    'name': record.data.get('name', ''),
                    'email': record.data.get('email', ''),
                    'phone': record.data.get('phone', ''),
                    'company': record.data.get('company', ''),
                    'role': record.data.get('role', ''),
                    'record_id': str(record_id)
                }
            except Record.DoesNotExist:
                logger.warning(f"Record {record_id} not found")

        # Get configuration
        config = node_data.get('config', {})

        return {
            'conversation_id': None,  # Will be set when first message is sent
            'participant_id': None,   # Will be set when participant is identified
            'participant_info': participant_info,
            'objective': config.get('objective', ''),
            'success_criteria': config.get('success_criteria', []),
            'messages': [],
            'evaluations': [],
            'iteration': 0,
            'max_iterations': config.get('max_iterations', 5),
            'current_channel': config.get('channel', 'email'),
            'started_at': timezone.now().isoformat(),
            'last_evaluation': None,
            'response_timeout_hours': config.get('response_timeout_hours', 24),
            'opt_out_keywords': config.get('opt_out_keywords', ['unsubscribe', 'stop', 'opt out', 'remove me'])
        }

    async def _send_initial_message(
        self,
        conversation_state: Dict[str, Any],
        node_data: Dict[str, Any],
        context: Dict[str, Any]
    ):
        """Send the initial message to start the conversation"""

        config = node_data.get('config', {})
        initial_message = config.get('initial_message', '')
        participant_info = conversation_state.get('participant_info', {})

        # Format the message with participant info
        try:
            formatted_message = initial_message.format(**participant_info)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}, using raw template")
            formatted_message = initial_message

        # Determine recipient
        channel = conversation_state['current_channel']
        recipient = None

        if channel == 'email':
            recipient = participant_info.get('email')
        elif channel == 'whatsapp':
            recipient = participant_info.get('phone')
        elif channel == 'linkedin':
            recipient = participant_info.get('linkedin_id')

        if not recipient:
            raise ValueError(f"No recipient found for channel {channel}")

        # Send via communication service
        # Note: In production, this would use the actual UniPile integration
        logger.info(f"Sending initial message via {channel} to {recipient}")

        # Store in conversation history
        conversation_state['messages'].append({
            'direction': 'outbound',
            'content': formatted_message,
            'channel': channel,
            'timestamp': timezone.now().isoformat(),
            'sender': 'ai'
        })

    async def _wait_for_response(
        self,
        conversation_state: Dict[str, Any],
        node_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Wait for a response from the participant"""

        config = node_data.get('config', {})
        timeout_hours = conversation_state.get('response_timeout_hours', config.get('response_timeout_hours', 24))
        timeout_minutes = int(timeout_hours * 60)
        timeout_time = timezone.now() + timedelta(minutes=timeout_minutes)

        # Poll for response (simplified for implementation)
        # In production, this would check actual messages in the database
        while timezone.now() < timeout_time:
            # Check for new messages in conversation
            # This is a simplified check - actual implementation would query Message model

            # For now, simulate waiting
            await asyncio.sleep(10)  # Check every 10 seconds

            # In production: Query for new inbound messages
            # messages = await sync_to_async(Message.objects.filter)(...)

            # For demonstration, return a simulated response after first check
            if conversation_state['iteration'] == 1:
                return {
                    'content': "I'm interested in learning more. What times work for a demo?",
                    'channel': conversation_state['current_channel'],
                    'timestamp': timezone.now().isoformat(),
                    'sender': 'participant'
                }

            break  # Remove in production

        return None  # Timeout

    async def _ai_evaluate_and_respond(
        self,
        objective: str,
        success_criteria: List[str],
        conversation_history: List[Dict],
        latest_response: str,
        ai_config: Dict[str, Any],
        participant_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use AI to evaluate the conversation and generate next response"""

        # Format conversation history for AI
        formatted_history = "\n".join([
            f"{msg['sender']}: {msg['content']}"
            for msg in conversation_history
        ])

        # Format success criteria
        criteria_text = "\n".join([f"- {criterion}" for criterion in success_criteria])

        prompt = f"""
You are managing a conversation with the following objective:
{objective}

Success Criteria:
{criteria_text}

Participant Information:
Name: {participant_info.get('name', 'Unknown')}
Company: {participant_info.get('company', 'Unknown')}
Role: {participant_info.get('role', 'Unknown')}

Conversation History:
{formatted_history}

Latest Response from Participant:
{latest_response}

Analyze this conversation and provide a JSON response with the following structure:
{{
    "objective_achieved": boolean (true if the objective has been met),
    "confidence": number (0-100, your confidence that the objective is achieved),
    "opt_out_detected": boolean (true if the participant wants to stop),
    "human_handoff_needed": boolean (true if human intervention is needed),
    "analysis": "string explaining your evaluation",
    "next_message": "string with the next message to send (empty if objective achieved or exit condition met)",
    "reasoning": "string explaining your message strategy"
}}

Be conversational but professional. Focus on achieving the objective while respecting the participant's time and responses.
"""

        try:
            # Use the existing AI processor
            from django.db import connection

            result = await workflow_ai_processor.process_ai_field_async(
                record_data={'prompt': prompt},
                field_config={
                    'ai_prompt': prompt,
                    'ai_model': ai_config.get('model', 'gpt-4'),
                    'temperature': ai_config.get('temperature', 0.7),
                    'max_tokens': ai_config.get('max_tokens', 1000),
                    'response_format': {'type': 'json_object'}
                },
                tenant=connection.tenant,
                user=None
            )

            # Parse the AI response
            ai_response = json.loads(result.get('content', '{}'))

            return ai_response

        except Exception as e:
            logger.error(f"AI evaluation failed: {e}")
            # Return a safe default
            return {
                'objective_achieved': False,
                'confidence': 0,
                'opt_out_detected': False,
                'human_handoff_needed': False,
                'analysis': f'AI evaluation error: {str(e)}',
                'next_message': '',
                'reasoning': 'Error in AI processing'
            }

    async def _send_response(
        self,
        message: str,
        conversation_state: Dict[str, Any],
        channel: str
    ):
        """Send a response message"""

        participant_info = conversation_state.get('participant_info', {})

        # Determine recipient based on channel
        recipient = None
        if channel == 'email':
            recipient = participant_info.get('email')
        elif channel == 'whatsapp':
            recipient = participant_info.get('phone')
        elif channel == 'linkedin':
            recipient = participant_info.get('linkedin_id')

        if recipient:
            logger.info(f"Sending message via {channel} to {recipient}: {message[:100]}...")
            # In production, use actual communication service

    async def _complete_success(
        self,
        conversation_state: Dict[str, Any],
        evaluation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle successful objective completion"""

        return {
            'success': True,
            'continue_loop': False,
            'conversation_state': conversation_state,
            'result': 'objective_achieved',
            'final_evaluation': evaluation,
            'total_iterations': conversation_state['iteration'],
            'message': f"Objective achieved with {evaluation.get('confidence', 0)}% confidence"
        }

    async def _handle_opt_out(
        self,
        conversation_state: Dict[str, Any],
        evaluation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle participant opt-out"""

        return {
            'success': True,
            'continue_loop': False,
            'conversation_state': conversation_state,
            'result': 'opt_out',
            'final_evaluation': evaluation,
            'message': 'Participant opted out of conversation'
        }

    async def _create_handoff_task(
        self,
        conversation_state: Dict[str, Any],
        evaluation: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a task for human handoff"""

        # In production, create an actual task/notification
        logger.info(f"Creating human handoff task for conversation")

        return {
            'success': True,
            'continue_loop': False,
            'conversation_state': conversation_state,
            'result': 'human_handoff',
            'final_evaluation': evaluation,
            'message': 'Conversation handed off to human agent'
        }

    async def _handle_max_iterations(
        self,
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle reaching max iterations"""

        return {
            'success': True,
            'continue_loop': False,
            'conversation_state': conversation_state,
            'result': 'max_iterations_reached',
            'message': f"Maximum iterations ({conversation_state['max_iterations']}) reached"
        }

    async def _handle_timeout(
        self,
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle response timeout"""

        return {
            'success': True,
            'continue_loop': False,
            'conversation_state': conversation_state,
            'result': 'timeout',
            'message': 'Response timeout reached'
        }