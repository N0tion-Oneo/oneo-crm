"""
API views for handling workflow trigger events
These endpoints receive external events and trigger appropriate workflows
"""
import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from workflows.trigger_registry import trigger_registry

logger = logging.getLogger(__name__)


class TriggerEventBaseView(APIView):
    """Base view for trigger events with common functionality"""

    async def trigger_workflows(self, trigger_type, trigger_data):
        """Common method to trigger workflows for an event"""
        try:
            execution_ids = await trigger_registry.trigger_workflows(
                trigger_type=trigger_type,
                trigger_data=trigger_data
            )

            return Response({
                'success': True,
                'triggered_workflows': len(execution_ids),
                'execution_ids': execution_ids
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to trigger workflows for {trigger_type}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class FormSubmissionTriggerView(TriggerEventBaseView):
    """Handle form submission events"""
    permission_classes = [AllowAny]  # Forms are public

    async def post(self, request):
        """Process form submission and trigger workflows"""
        try:
            # Extract form data
            pipeline_id = request.data.get('pipeline_id')
            form_mode = request.data.get('form_mode', 'create')
            form_data = request.data.get('form_data', {})
            stage = request.data.get('stage')

            if not pipeline_id:
                return Response({
                    'error': 'pipeline_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Prepare trigger data
            trigger_data = {
                'pipeline_id': pipeline_id,
                'form_mode': form_mode,
                'form_data': form_data,
                'stage': stage,
                'submitted_at': timezone.now().isoformat(),
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT')
            }

            logger.info(f"Form submission received for pipeline {pipeline_id}")

            # Trigger workflows
            return await self.trigger_workflows('form_submitted', trigger_data)

        except Exception as e:
            logger.error(f"Form submission trigger error: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class WebhookTriggerView(TriggerEventBaseView):
    """Handle webhook trigger events"""
    permission_classes = [AllowAny]  # Webhooks need to be accessible

    async def post(self, request, webhook_path=None):
        """Process webhook and trigger workflows"""
        try:
            # Prepare trigger data
            trigger_data = {
                'path': webhook_path,
                'method': request.method,
                'headers': dict(request.headers),
                'body': request.data,
                'query_params': dict(request.GET),
                'received_at': timezone.now().isoformat()
            }

            logger.info(f"Webhook received at path: {webhook_path}")

            # Trigger workflows
            return await self.trigger_workflows('webhook', trigger_data)

        except Exception as e:
            logger.error(f"Webhook trigger error: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RecordEventTriggerView(TriggerEventBaseView):
    """Handle record-based trigger events (created/updated)"""
    # This will use normal authentication

    async def trigger_record_event(self, event_type, record_data):
        """Trigger workflows for record events"""
        try:
            trigger_data = {
                'record_id': record_data.get('id'),
                'pipeline_id': record_data.get('pipeline_id'),
                'event_type': event_type,
                'record_data': record_data,
                'triggered_at': timezone.now().isoformat(),
                'triggered_by': str(self.request.user.id) if self.request.user else None
            }

            logger.info(f"Record {event_type} event for pipeline {record_data.get('pipeline_id')}")

            # Trigger workflows
            return await self.trigger_workflows(f'record_{event_type}', trigger_data)

        except Exception as e:
            logger.error(f"Record event trigger error: {e}")
            return None


class EmailReceivedTriggerView(TriggerEventBaseView):
    """Handle email received trigger events"""
    permission_classes = [AllowAny]  # Email webhooks need to be accessible

    async def post(self, request):
        """Process received email and trigger workflows"""
        try:
            # Extract email data
            email_data = {
                'from': request.data.get('from'),
                'to': request.data.get('to'),
                'subject': request.data.get('subject'),
                'body': request.data.get('body'),
                'html': request.data.get('html'),
                'attachments': request.data.get('attachments', []),
                'received_at': timezone.now().isoformat()
            }

            logger.info(f"Email received from {email_data['from']}")

            # Trigger workflows
            return await self.trigger_workflows('email_received', email_data)

        except Exception as e:
            logger.error(f"Email trigger error: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Import for timezone
from django.utils import timezone