"""
Webhook receiver endpoint for workflow triggers
"""
import hashlib
import hmac
import json
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync
import logging

from workflows.models import Workflow, WorkflowTrigger
from workflows.engine import workflow_engine

User = get_user_model()
logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(['POST', 'GET', 'PUT'])
@permission_classes([AllowAny])  # Webhooks come from external sources
def workflow_webhook_receiver(request, workflow_id):
    """
    Receive webhook calls to trigger workflows

    Supports:
    - Secret token validation for security
    - Multiple HTTP methods (GET, POST, PUT)
    - JSON payload parsing
    - Automatic workflow triggering
    """
    try:
        # Get the workflow
        workflow = get_object_or_404(Workflow, id=workflow_id)

        # Find webhook trigger configuration
        webhook_trigger = None
        if hasattr(workflow, 'triggers') and workflow.triggers:
            for trigger in workflow.triggers:
                if trigger.get('type') == 'webhook':
                    webhook_trigger = trigger
                    break

        if not webhook_trigger:
            logger.warning(f"Workflow {workflow_id} doesn't have webhook trigger configured")
            return Response(
                {"error": "Webhook trigger not configured for this workflow"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate secret token if configured
        if webhook_trigger.get('config', {}).get('secret'):
            expected_secret = webhook_trigger['config']['secret']

            # Check for secret in headers
            provided_secret = request.headers.get('X-Webhook-Secret', '')

            # Also check for signature-based validation (GitHub/Stripe style)
            signature = request.headers.get('X-Webhook-Signature', '')
            if signature and request.body:
                expected_signature = hmac.new(
                    expected_secret.encode(),
                    request.body,
                    hashlib.sha256
                ).hexdigest()

                if not hmac.compare_digest(signature, expected_signature):
                    logger.warning(f"Invalid webhook signature for workflow {workflow_id}")
                    return Response(
                        {"error": "Invalid webhook signature"},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            elif provided_secret != expected_secret:
                logger.warning(f"Invalid webhook secret for workflow {workflow_id}")
                return Response(
                    {"error": "Invalid webhook secret"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        # Check if method matches configuration
        configured_method = webhook_trigger.get('config', {}).get('method', 'POST')
        if request.method != configured_method:
            return Response(
                {"error": f"Method {request.method} not allowed. Expected {configured_method}"},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )

        # Parse webhook payload
        webhook_data = {
            "webhook_headers": dict(request.headers),
            "webhook_method": request.method,
            "webhook_path": request.path,
            "webhook_query_params": dict(request.GET),
        }

        # Add body data
        if request.method in ['POST', 'PUT']:
            try:
                webhook_data["webhook_body"] = request.data
            except:
                webhook_data["webhook_body"] = {}

        # Get system user for webhook triggers
        system_user = User.objects.filter(email='system@oneo.com').first()
        if not system_user:
            # Create system user if it doesn't exist
            system_user = User.objects.create(
                email='system@oneo.com',
                username='system',
                first_name='System',
                last_name='User',
                is_active=True
            )

        # Trigger the workflow asynchronously
        try:
            execution = async_to_sync(workflow_engine.execute_workflow)(
                workflow=workflow,
                trigger_data=webhook_data,
                triggered_by=system_user,
                tenant=workflow.tenant
            )

            logger.info(f"Workflow {workflow_id} triggered via webhook, execution ID: {execution.id}")

            return Response({
                "success": True,
                "message": "Workflow triggered successfully",
                "execution_id": str(execution.id),
                "workflow_id": str(workflow.id),
                "workflow_name": workflow.name
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to trigger workflow {workflow_id} via webhook: {str(e)}")
            return Response({
                "error": "Failed to trigger workflow",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Workflow.DoesNotExist:
        logger.warning(f"Webhook received for non-existent workflow {workflow_id}")
        return Response(
            {"error": "Workflow not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Webhook processing error for workflow {workflow_id}: {str(e)}")
        return Response({
            "error": "Internal server error",
            "details": str(e) if request.user.is_authenticated else "An error occurred"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def webhook_test(request, workflow_id):
    """
    Test endpoint to verify webhook configuration
    Returns webhook URL and configuration details
    """
    try:
        workflow = get_object_or_404(Workflow, id=workflow_id)

        # Check permissions
        if not request.user.has_perm('workflows.view_workflow', workflow):
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Find webhook trigger
        webhook_trigger = None
        if hasattr(workflow, 'triggers') and workflow.triggers:
            for trigger in workflow.triggers:
                if trigger.get('type') == 'webhook':
                    webhook_trigger = trigger
                    break

        if not webhook_trigger:
            return Response({
                "configured": False,
                "message": "No webhook trigger configured for this workflow"
            })

        # Build webhook URL
        webhook_url = request.build_absolute_uri(f'/api/v1/workflows/{workflow_id}/webhook/')

        return Response({
            "configured": True,
            "webhook_url": webhook_url,
            "method": webhook_trigger.get('config', {}).get('method', 'POST'),
            "has_secret": bool(webhook_trigger.get('config', {}).get('secret')),
            "trigger_config": webhook_trigger,
            "test_curl": f"curl -X {webhook_trigger.get('config', {}).get('method', 'POST')} {webhook_url} -H 'Content-Type: application/json' -d '{{\"test\": true}}'"
        })

    except Workflow.DoesNotExist:
        return Response(
            {"error": "Workflow not found"},
            status=status.HTTP_404_NOT_FOUND
        )