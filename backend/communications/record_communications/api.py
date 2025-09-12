"""
API endpoints for record-centric communications
"""
import logging
import json
from datetime import datetime, timedelta

from django.db.models import Q, Count, Max, Prefetch, Sum
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers

from pipelines.models import Record
from communications.models import (
    Conversation, Message, Participant, UserChannelConnection,
    MessageDirection, MessageStatus
)
from rest_framework.permissions import IsAuthenticated

from .models import (
    RecordCommunicationProfile, RecordSyncJob,
    RecordAttendeeMapping
)
from .serializers import (
    RecordCommunicationProfileSerializer,
    RecordConversationSerializer,
    RecordMessageSerializer,
    RecordSyncJobSerializer,
    RecordCommunicationStatsSerializer,
    SyncTriggerSerializer,
    QuickReplySerializer,
    RecordAttendeeMappingSerializer
)
from .services import RecordIdentifierExtractor, MessageMapper
from .services.record_sync_orchestrator import RecordSyncOrchestrator

logger = logging.getLogger(__name__)


class RecordCommunicationsViewSet(viewsets.ViewSet):
    """
    ViewSet for record-centric communication management.
    All communications are accessed through the record context.
    """
    
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.identifier_extractor = RecordIdentifierExtractor()
        # Note: RecordSyncOrchestrator is instantiated per request with UniPile client
        self.message_mapper = MessageMapper()
    
    def _get_record_conversation_ids(self, record):
        """Helper method to get all conversation IDs for a record through participants"""
        from communications.models import ConversationParticipant
        from django.db.models import Q
        
        # Get all participants linked to this record (both primary and secondary)
        participants = Participant.objects.filter(
            Q(contact_record=record) | Q(secondary_record=record)
        )
        
        # Get conversations through participants
        return ConversationParticipant.objects.filter(
            participant__in=participants
        ).values_list('conversation_id', flat=True).distinct()
    
    @extend_schema(
        summary="Get communication profile for a record",
        responses={200: RecordCommunicationProfileSerializer}
    )
    @action(detail=True, methods=['get'])
    def profile(self, request, pk=None):
        """Get or create communication profile for a record"""
        try:
            record = Record.objects.get(pk=pk)
            
            # Get or create profile
            profile, created = RecordCommunicationProfile.objects.get_or_create(
                record=record,
                defaults={
                    'pipeline': record.pipeline,
                    'created_by': request.user
                }
            )
            
            # Extract identifiers if newly created or empty
            if created or not profile.communication_identifiers:
                identifiers = self.identifier_extractor.extract_identifiers_from_record(record)
                identifier_fields = self.identifier_extractor.get_identifier_fields(record.pipeline_id)
                
                profile.communication_identifiers = identifiers
                profile.identifier_fields = identifier_fields
                profile.save()
            
            serializer = RecordCommunicationProfileSerializer(profile)
            return Response(serializer.data)
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        summary="Get all conversations for a record with smart loading",
        parameters=[
            OpenApiParameter(name='mode', type=str, default='smart',
                           description='Loading mode: smart (default), all, or single channel'),
            OpenApiParameter(name='channel_type', type=str, required=False,
                           description='Filter by channel type when mode is not smart'),
            OpenApiParameter(name='limit', type=int, default=20),
            OpenApiParameter(name='offset', type=int, default=0),
        ],
        responses={200: RecordConversationSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def conversations(self, request, pk=None):
        """Get conversations with smart loading strategy:
        - WhatsApp/LinkedIn: All conversations (few expected)
        - Email: Last 10 conversations only (many expected)
        """
        try:
            record = Record.objects.get(pk=pk)
            
            # Get query parameters
            mode = request.query_params.get('mode', 'smart')
            channel_type = request.query_params.get('channel_type')
            limit = int(request.query_params.get('limit', 20))
            offset = int(request.query_params.get('offset', 0))
            
            # Get conversation IDs for this record through participants
            conversation_ids = self._get_record_conversation_ids(record)
            
            if mode == 'smart':
                # Smart loading: All WhatsApp/LinkedIn/Calendar + last 10 emails
                conversations_query = Conversation.objects.filter(
                    id__in=conversation_ids
                ).select_related('channel')
                
                # Get all WhatsApp, LinkedIn, and Calendar conversations
                social_conversations = conversations_query.filter(
                    channel__channel_type__in=['whatsapp', 'linkedin', 'calendar', 'scheduling']  # Include both for compatibility
                )
                
                # Get last 10 email conversations (gmail, email, or any email-like channel)
                email_conversations = conversations_query.filter(
                    channel__channel_type__in=['email', 'gmail', 'outlook', 'office365']
                ).order_by('-last_message_at')[:10]
                
                # Combine and order by last message
                from django.db.models import Q
                combined_ids = list(social_conversations.values_list('id', flat=True)) + \
                              list(email_conversations.values_list('id', flat=True))
                
                conversations = Conversation.objects.filter(
                    id__in=combined_ids
                ).select_related('channel').order_by('-last_message_at')
                
                total_count = len(combined_ids)
                
            else:
                # Standard mode with optional channel filter
                conversations_query = Conversation.objects.filter(
                    id__in=conversation_ids
                ).select_related('channel')
                
                if channel_type:
                    # Map frontend channel types to backend channel types
                    if channel_type == 'email':
                        # Email tab should include all email-type channels
                        conversations_query = conversations_query.filter(
                            channel__channel_type__in=['email', 'gmail', 'outlook', 'office365']
                        )
                    elif channel_type == 'calendar':
                        # Calendar tab should include both calendar and scheduling (for compatibility)
                        conversations_query = conversations_query.filter(
                            channel__channel_type__in=['calendar', 'scheduling']
                        )
                    else:
                        # For other channels (whatsapp, linkedin), use exact match
                        conversations_query = conversations_query.filter(
                            channel__channel_type=channel_type
                        )
                
                total_count = conversations_query.count()
                conversations = conversations_query.order_by('-last_message_at')[offset:offset + limit]
            
            serializer = RecordConversationSerializer(conversations, many=True)
            
            # Return with pagination metadata
            return Response({
                'count': total_count,
                'next': offset + limit < total_count if mode != 'smart' else False,
                'previous': offset > 0 if mode != 'smart' else False,
                'results': serializer.data,
                'mode': mode
            })
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        summary="Get messages for a specific conversation",
        parameters=[
            OpenApiParameter(name='conversation_id', type=str, required=True),
            OpenApiParameter(name='limit', type=int, default=30),
            OpenApiParameter(name='offset', type=int, default=0),
        ],
        responses={200: RecordMessageSerializer(many=True)}
    )
    @action(detail=True, methods=['get'], url_path='conversation-messages')
    def conversation_messages(self, request, pk=None):
        """Get messages for a specific conversation with pagination"""
        try:
            record = Record.objects.get(pk=pk)
            conversation_id = request.query_params.get('conversation_id')
            
            if not conversation_id:
                return Response(
                    {'error': 'conversation_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify the conversation is linked to this record through participants
            conversation_ids = self._get_record_conversation_ids(record)
            
            # Convert conversation_id to UUID if it's a string
            import uuid
            try:
                conv_uuid = uuid.UUID(conversation_id)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid conversation_id format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if conv_uuid not in conversation_ids:
                return Response(
                    {'error': 'Conversation not found for this record'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get pagination parameters
            limit = int(request.query_params.get('limit', 30))
            offset = int(request.query_params.get('offset', 0))
            
            # Get messages for the conversation (reverse chronological - newest first)
            # Order by actual message timestamp, not sync time
            from django.db.models.functions import Coalesce
            from django.db.models import F
            messages = Message.objects.filter(
                conversation_id=conv_uuid
            ).select_related(
                'sender_participant', 'conversation', 'channel'
            ).annotate(
                actual_timestamp=Coalesce('sent_at', 'received_at', 'created_at')
            ).order_by('-actual_timestamp')[offset:offset + limit]
            
            # Get total count
            total_count = Message.objects.filter(
                conversation_id=conv_uuid
            ).count()
            
            serializer = RecordMessageSerializer(messages, many=True)
            
            return Response({
                'count': total_count,
                'next': offset + limit < total_count,
                'previous': offset > 0,
                'results': serializer.data
            })
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        summary="Get unified timeline of all communications",
        parameters=[
            OpenApiParameter(name='limit', type=int, default=100),
            OpenApiParameter(name='offset', type=int, default=0),
            OpenApiParameter(name='channel_type', type=str, required=False)
        ],
        responses={200: RecordMessageSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        """Get unified timeline of all messages for this record"""
        try:
            record = Record.objects.get(pk=pk)
            
            # Get query parameters
            limit = int(request.query_params.get('limit', 100))
            offset = int(request.query_params.get('offset', 0))
            channel_type = request.query_params.get('channel_type')
            
            # Get all conversations linked to this record through participants
            conversation_ids = self._get_record_conversation_ids(record)
            
            # Get all messages from these conversations
            messages = Message.objects.filter(
                conversation_id__in=conversation_ids
            )
            
            # Filter by channel type if specified
            if channel_type:
                messages = messages.filter(channel__channel_type=channel_type)
            
            # Get total count before pagination
            total_count = messages.count()
            
            # Order by actual message timestamp (newest first) and apply pagination
            from django.db.models.functions import Coalesce
            from django.db.models import F
            messages = messages.select_related(
                'sender_participant', 'conversation', 'channel'
            ).annotate(
                actual_timestamp=Coalesce('sent_at', 'received_at', 'created_at')
            ).order_by('-actual_timestamp')[offset:offset + limit]
            
            serializer = RecordMessageSerializer(messages, many=True)
            
            # Return paginated response
            return Response({
                'count': total_count,
                'next': offset + limit < total_count,
                'previous': offset > 0,
                'results': serializer.data
            })
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        summary="Get communication statistics for a record",
        responses={200: RecordCommunicationStatsSerializer}
    )
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get communication statistics for this record"""
        try:
            record = Record.objects.get(pk=pk)
            
            # Get profile for basic stats
            profile = RecordCommunicationProfile.objects.filter(
                record=record
            ).first()
            
            if not profile:
                # No communications yet
                return Response({
                    'total_conversations': 0,
                    'total_messages': 0,
                    'total_unread': 0,
                    'last_activity': None,
                    'channels': [],
                    'participants_count': 0
                })
            
            # Get all linked conversations through participants
            conversation_ids = self._get_record_conversation_ids(record)
            
            # Get channel breakdown
            channel_stats = Conversation.objects.filter(
                id__in=conversation_ids
            ).values('channel__channel_type').annotate(
                count=Count('id'),
                messages=Count('messages')
            )
            
            channel_breakdown = {
                stat['channel__channel_type']: {
                    'conversations': stat['count'],
                    'messages': stat['messages']
                }
                for stat in channel_stats
            }
            
            # Get unique participants
            participants = Participant.objects.filter(
                Q(contact_record=record) | Q(secondary_record=record)
            ).distinct()
            
            # Activity timeline (last 30 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            daily_activity = Message.objects.filter(
                conversation_id__in=conversation_ids,
                created_at__gte=thirty_days_ago
            ).extra(
                select={'day': 'date(created_at)'}
            ).values('day').annotate(
                count=Count('id')
            ).order_by('day')
            
            # Calculate total_unread dynamically from actual conversation unread counts
            total_unread = Conversation.objects.filter(
                id__in=conversation_ids
            ).aggregate(total=Sum('unread_count'))['total'] or 0
            
            stats = {
                'total_conversations': profile.total_conversations,
                'total_messages': profile.total_messages,
                'total_unread': total_unread,  # Use computed value instead of stored field
                'last_activity': profile.last_message_at,
                'channels': list(channel_breakdown.keys()),
                'participants_count': participants.count(),
                'channel_breakdown': channel_breakdown,
                'activity_timeline': list(daily_activity)
            }
            
            serializer = RecordCommunicationStatsSerializer(stats)
            return Response(serializer.data)
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        summary="Trigger sync for a record",
        request=SyncTriggerSerializer,
        responses={200: RecordSyncJobSerializer}
    )
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Trigger communication sync for this record"""
        logger.info(f"Sync requested for record {pk}")
        logger.info(f"Request data: {request.data}")
        try:
            record = Record.objects.get(pk=pk)
            
            # Check if sync is already in progress
            profile, _ = RecordCommunicationProfile.objects.get_or_create(
                record=record,
                defaults={'pipeline': record.pipeline}
            )
            
            if profile.sync_in_progress:
                return Response(
                    {'error': 'Sync already in progress for this record'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if recently synced (unless forced)
            # Handle empty request body
            serializer = SyncTriggerSerializer(data=request.data if request.data else {})
            serializer.is_valid(raise_exception=True)
            
            force = serializer.validated_data.get('force', False)
            if not force and profile.last_full_sync:
                time_since_sync = timezone.now() - profile.last_full_sync
                if time_since_sync.total_seconds() < 3600:  # 1 hour
                    return Response(
                        {'error': 'Record was synced recently. Use force=true to sync again.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Queue sync task
            from communications.record_communications.tasks import sync_record_communications
            from django.db import connection
            
            # Log the task details
            tenant_schema = connection.schema_name
            logger.info(f"Queueing sync task for record {record.id} in tenant {tenant_schema}")
            
            # Let the TenantTaskRouter handle routing based on tenant_schema in kwargs
            # The router will route to {tenant_schema}_sync queue
            result = sync_record_communications.apply_async(
                args=[record.id],
                kwargs={
                    'tenant_schema': tenant_schema,
                    'triggered_by_id': request.user.id,
                    'trigger_reason': 'Manual API trigger'
                }
                # No explicit queue - let router handle it
            )
            
            logger.info(f"Task queued with ID: {result.id}")
            
            # Create sync job record
            sync_job = RecordSyncJob.objects.create(
                record=record,
                profile=profile,
                job_type='full_history',
                status='pending',
                triggered_by=request.user,
                trigger_reason='Manual API trigger',
                celery_task_id=result.id
            )
            
            serializer = RecordSyncJobSerializer(sync_job)
            return Response(serializer.data)
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in sync endpoint: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Sync failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Get sync status for a record",
        responses={200: RecordSyncJobSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def sync_status(self, request, pk=None):
        """Get sync job history for this record"""
        try:
            record = Record.objects.get(pk=pk)
            
            # Get recent sync jobs
            jobs = RecordSyncJob.objects.filter(
                record=record
            ).order_by('-created_at')[:10]
            
            serializer = RecordSyncJobSerializer(jobs, many=True)
            return Response(serializer.data)
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        summary="Send a quick reply from record context",
        request=QuickReplySerializer,
        responses={200: {'description': 'Message sent successfully'}}
    )
    @action(detail=True, methods=['post'])
    def quick_reply(self, request, pk=None):
        """Send a quick reply to a conversation or start a new one"""
        try:
            record = Record.objects.get(pk=pk)
            
            serializer = QuickReplySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            data = serializer.validated_data
            conversation_id = data.get('conversation_id')
            channel_type = data['channel_type']
            content = data['content']
            
            # TODO: Implement actual message sending via UniPile
            # This would use the appropriate channel client to send the message
            
            return Response({
                'status': 'success',
                'message': 'Message sent successfully'
            })
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        summary="Send email from record context",
        request=inline_serializer(
            name='SendEmailSerializer',
            fields={
                'from_account_id': serializers.CharField(help_text='UniPile account ID to send from'),
                'to': serializers.ListField(child=serializers.EmailField(), help_text='Recipient email addresses'),
                'cc': serializers.ListField(child=serializers.EmailField(), required=False, help_text='CC recipients'),
                'bcc': serializers.ListField(child=serializers.EmailField(), required=False, help_text='BCC recipients'),
                'subject': serializers.CharField(help_text='Email subject'),
                'body': serializers.CharField(help_text='Email body (HTML)'),
                'reply_to_message_id': serializers.CharField(required=False, help_text='Message ID if replying'),
                'reply_mode': serializers.ChoiceField(choices=['reply', 'reply-all', 'forward'], required=False),
                'conversation_id': serializers.CharField(required=False, help_text='Existing conversation ID')
            }
        ),
        responses={200: {'description': 'Email sent successfully'}}
    )
    @action(detail=True, methods=['post'])
    def send_email(self, request, pk=None):
        """Send an email from record context"""
        try:
            from communications.channels.email.service import EmailService
            from asgiref.sync import async_to_sync
            
            record = Record.objects.get(pk=pk)
            
            # Log the full request data for debugging
            logger.info(f"📧 Email send request received for record {pk}")
            logger.info(f"📧 Request data: {json.dumps(request.data, indent=2)}")
            
            # Get data from request
            account_id = request.data.get('from_account_id')
            to = request.data.get('to', [])
            cc = request.data.get('cc', [])
            bcc = request.data.get('bcc', [])
            subject = request.data.get('subject', '')
            body = request.data.get('body', '')
            reply_to_message_id = request.data.get('reply_to_message_id')
            reply_mode = request.data.get('reply_mode')
            conversation_id = request.data.get('conversation_id')
            
            # Log parsed data
            logger.info(f"📧 Parsed - Account ID: {account_id}")
            logger.info(f"📧 Parsed - To: {to} (type: {type(to)})")
            logger.info(f"📧 Parsed - Subject: {repr(subject)} (empty: {not subject}, len: {len(subject)})")
            logger.info(f"📧 Parsed - Body length: {len(body)} chars")
            logger.info(f"📧 Parsed - Reply mode: {reply_mode}, Reply to ID: {reply_to_message_id}")
            
            # If replying to a specific message, get its UniPile ID for threading
            reply_to_external_id = None
            if reply_to_message_id:
                try:
                    reply_message = Message.objects.get(id=reply_to_message_id)
                    
                    # For threading, UniPile needs the UniPile message ID
                    if reply_message.metadata and 'unipile_id' in reply_message.metadata:
                        # Use the unipile_id - this is what UniPile expects for reply_to
                        reply_to_external_id = reply_message.metadata['unipile_id']
                        logger.info(f"Using unipile_id from reply message for threading: {reply_to_external_id}")
                    else:
                        # Can't thread to this message - it doesn't exist in UniPile
                        # Don't try to use Gmail Message-IDs or internal IDs
                        logger.warning(f"Reply message {reply_to_message_id} has no valid UniPile ID for threading - will send without reply_to")
                    
                except Message.DoesNotExist:
                    logger.warning(f"Reply-to message {reply_to_message_id} not found")
            
            if not account_id or not to or not body:
                return Response({
                    'success': False,
                    'error': 'from_account_id, to, and body are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the user's email connection
            connection = UserChannelConnection.objects.filter(
                user=request.user,
                unipile_account_id=account_id
            ).first()
            
            if not connection:
                return Response({
                    'success': False,
                    'error': 'Email connection not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Initialize email service
            service = EmailService(account_identifier=connection.account_name)
            
            # Format recipients as UniPile expects
            def format_recipients(emails):
                if not emails:
                    return None
                if isinstance(emails, str):
                    emails = [emails]
                return [{'identifier': email.strip(), 'display_name': ''} for email in emails if email.strip()]
            
            to_formatted = format_recipients(to)
            cc_formatted = format_recipients(cc)
            bcc_formatted = format_recipients(bcc)
            
            # Get conversation for threading
            conversation = None
            email_reply_to = None  # For UniPile threading
            
            # IMPORTANT: Only set reply_to when this is actually a reply
            # Check if this is a reply by looking for reply_to_message_id or reply_mode
            is_reply = bool(reply_to_message_id or reply_mode)
            
            # Use the specific reply_to_external_id if we have one
            if reply_to_external_id:
                email_reply_to = reply_to_external_id
                logger.info(f"📧 Using specific reply_to from message: {email_reply_to}")
            
            if conversation_id and is_reply:
                # Only use existing conversation if this is a REPLY
                try:
                    conversation = Conversation.objects.get(id=conversation_id)
                    logger.info(f"📧 Reply email - using existing conversation {conversation_id}")
                    
                    # Look for reply_to from conversation if we don't already have a specific reply_to
                    if not email_reply_to:
                        # For threading, we need to find the last message in this conversation
                        # and use its UniPile ID as reply_to
                        last_message = Message.objects.filter(
                            conversation=conversation
                        ).order_by('-created_at').first()
                        
                        if last_message:
                            # Try to get the UniPile ID from metadata or external_message_id
                            if last_message.metadata and 'unipile_id' in last_message.metadata:
                                email_reply_to = last_message.metadata['unipile_id']
                                logger.info(f"📧 Using unipile_id from conversation for reply_to: {email_reply_to}")
                            elif last_message.external_message_id:
                                email_reply_to = last_message.external_message_id
                                logger.info(f"📧 Using external_message_id from conversation for reply_to: {email_reply_to}")
                            else:
                                logger.info(f"📧 No valid UniPile ID found for threading")
                        else:
                            logger.info(f"📧 No previous message found in conversation for threading")
                        
                except Conversation.DoesNotExist:
                    logger.warning(f"Conversation {conversation_id} not found")
                    conversation = None
            elif conversation_id and not is_reply:
                # NEW EMAIL but conversation_id was provided
                # This happens when user is viewing a conversation but sends a NEW email
                # We should create a NEW conversation for this new email thread
                logger.info(f"📧 New email requested while viewing conversation {conversation_id} - creating NEW conversation")
                conversation = None  # Will trigger new conversation creation below
            
            # Create new conversation if needed (for new emails)
            if not conversation:
                logger.info(f"📧 Creating new conversation for new email thread")
                
                # Get the channel for this account
                from communications.models import Channel
                channel = Channel.objects.filter(
                    unipile_account_id=account_id,
                    channel_type='gmail'
                ).first()
                
                if channel:
                    # Create a new conversation with a temporary thread ID
                    # This will be updated with the real Gmail thread ID after sending
                    conversation = Conversation.objects.create(
                        channel=channel,
                        external_thread_id=f"temp_{timezone.now().timestamp()}",
                        subject=subject or "New email",
                        status='active'
                    )
                    logger.info(f"📧 Created new conversation {conversation.id} for new email thread")
                    
                    # No need to create RecordCommunicationLink anymore
                    # The conversation is linked through participants
                else:
                    logger.warning(f"📧 No Gmail channel found for account {account_id}")
            
            # Handle attachments if provided
            attachments = request.data.get('attachments', [])
            attachment_data = []
            if attachments:
                logger.info(f"Processing {len(attachments)} attachments for email")
                for att in attachments:
                    # Attachments come from frontend with base64 data
                    attachment_data.append({
                        'filename': att.get('filename', 'attachment'),
                        'content_type': att.get('content_type', 'application/octet-stream'),
                        'data': att.get('data'),  # Base64 encoded data from frontend
                    })
            
            # Send email via UniPile
            # Prefer conversation threading over individual message reply if we have a valid UniPile ID
            # This handles cases where the individual message doesn't exist in UniPile (e.g., webhook-created messages)
            final_reply_to = email_reply_to or reply_to_external_id
            
            # Only include reply_to if it's a valid UniPile message ID (not a Gmail Message-ID)
            # UniPile message IDs are typically alphanumeric without @ symbols
            # Gmail Message-IDs have the format <...@mail.gmail.com>
            if final_reply_to and '@' in str(final_reply_to):
                logger.warning(f"Skipping invalid reply_to (Gmail Message-ID format): {final_reply_to}")
                final_reply_to = None
            
            # Log what we're about to send to UniPile
            logger.info(f"📧 SENDING TO UNIPILE:")
            logger.info(f"📧   Email Type: {'REPLY' if is_reply else 'NEW EMAIL'}")
            logger.info(f"📧   Subject being sent: {repr(subject)} (type: {type(subject)})")
            logger.info(f"📧   Reply-to: {final_reply_to} (should be None for new emails)")
            logger.info(f"📧   To: {to_formatted}")
            
            result = async_to_sync(service.send_email)(
                account_id=account_id,
                to=to_formatted,
                subject=subject,
                body=body,
                cc=cc_formatted,
                bcc=bcc_formatted,
                reply_to=final_reply_to,  # Use reply_to for UniPile threading (if valid)
                attachments=attachment_data if attachment_data else None
                # Note: thread_id is not used - UniPile uses reply_to for threading
            )
            
            if result.get('success'):
                logger.info(f"Email sent successfully from record {pk} with tracking_id: {result.get('tracking_id')}")
                
                # Create message record and link to record if conversation exists  
                # Note: We already fetched conversation above for thread_id
                if conversation and result.get('success'):
                    # Create outbound message with external ID for future threading
                    # UniPile returns the UniPile message ID in response.id
                    # This is the ID we need for reply threading
                    unipile_id = result.get('response', {}).get('id')
                    provider_id = result.get('response', {}).get('provider_id')
                    tracking_id = result.get('tracking_id')
                    
                    # Note: provider_id is the Gmail message ID, not thread ID
                    # Threading is maintained through reply_to parameter
                    
                    # Prepare attachment metadata for storage
                    attachment_metadata = []
                    if attachment_data:
                        for i, att in enumerate(attachment_data):
                            attachment_metadata.append({
                                'id': f"pending_{i}",  # Temporary ID until webhook provides real one
                                'filename': att.get('filename'),
                                'content_type': att.get('content_type'),
                                'size': len(att.get('data', '')) if att.get('data') else 0,
                                'pending': True,  # Mark as pending UniPile processing
                                'attachment_id': None  # Will be filled by webhook
                            })
                    
                    # Store the UniPile ID as external_message_id for reply threading
                    message = Message.objects.create(
                        conversation=conversation,
                        channel=conversation.channel,
                        external_message_id=unipile_id,  # Store UniPile ID for threading
                        direction='outbound',
                        subject=subject,
                        content=body,
                        contact_email=to[0] if to else '',
                        status='sent',
                        sent_at=timezone.now(),
                        metadata={
                            'from': {'email': connection.user.email, 'name': connection.user.get_full_name()},
                            'to': [{'email': email, 'name': ''} for email in to],
                            'cc': [{'email': email, 'name': ''} for email in cc] if cc else [],
                            'tracking_id': tracking_id,
                            'unipile_id': unipile_id,
                            'provider_id': provider_id,
                            'reply_mode': reply_mode,
                            'sent_via': 'record_context',
                            'reply_to': final_reply_to if final_reply_to else None,
                            'attachments': attachment_metadata if attachment_metadata else None
                        }
                    )
                    
                    # Update profile metrics
                    profile = RecordCommunicationProfile.objects.filter(record=record).first()
                    if profile:
                        profile.total_messages += 1
                        profile.last_message_at = timezone.now()
                        profile.save(update_fields=['total_messages', 'last_message_at'])
                
                response_data = {
                    'success': True,
                    'tracking_id': result.get('tracking_id'),
                    'message': 'Email sent successfully'
                }
                
                # Include conversation_id in response if a new conversation was created
                if conversation:
                    response_data['conversation_id'] = str(conversation.id)
                    if not is_reply:
                        response_data['new_conversation_created'] = True
                
                return Response(response_data)
            else:
                return Response({
                    'success': False,
                    'error': result.get('error', 'Failed to send email')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to send email from record {pk}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @extend_schema(
        summary="Download an attachment from a message",
        parameters=[
            OpenApiParameter(name='message_id', type=str, required=True),
            OpenApiParameter(name='attachment_id', type=str, required=True),
        ],
        responses={200: {'description': 'Attachment file'}}
    )
    @action(detail=True, methods=['get'], url_path='download-attachment')
    def download_attachment(self, request, pk=None):
        """Download an attachment from a message"""
        message_id = request.query_params.get('message_id')
        attachment_id = request.query_params.get('attachment_id')
        
        if not message_id or not attachment_id:
            return Response(
                {'error': 'Both message_id and attachment_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get the message
            message = Message.objects.get(id=message_id)
            
            # Check if message belongs to this record's conversations
            record = Record.objects.get(pk=pk)
            conversation_ids = self._get_record_conversation_ids(record)
            
            if message.conversation_id not in conversation_ids:
                return Response(
                    {'error': 'Message not found in record conversations'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get attachment metadata
            attachments = message.metadata.get('attachments', []) if message.metadata else []
            attachment = None
            
            logger.info(f"Looking for attachment_id: {attachment_id}")
            logger.info(f"Message has {len(attachments)} attachments")
            
            for att in attachments:
                att_id = att.get('attachment_id') or att.get('id')
                logger.info(f"Checking attachment: {att_id} == {attachment_id}?")
                if att_id == attachment_id:
                    attachment = att
                    break
            
            if not attachment:
                logger.error(f"Attachment not found. Available attachments: {[att.get('attachment_id', att.get('id')) for att in attachments]}")
                return Response(
                    {'error': f'Attachment {attachment_id} not found in message'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get UniPile attachment
            from communications.channels.email.service import EmailService
            service = EmailService()
            
            # Use the external message ID (UniPile ID) and attachment ID
            unipile_message_id = message.metadata.get('unipile_id') if message.metadata else None
            external_message_id = message.external_message_id
            
            logger.info(f"Message external_message_id: {external_message_id}")
            logger.info(f"Message metadata unipile_id: {unipile_message_id}")
            
            if not unipile_message_id and not external_message_id:
                return Response(
                    {'error': 'Unable to determine message ID for UniPile'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Download from UniPile
            import requests
            from django.conf import settings
            from django.http import HttpResponse
            
            api_key = getattr(settings, 'UNIPILE_API_KEY', None)
            base_url = getattr(settings, 'UNIPILE_DSN', 'https://api18.unipile.com:14890')
            
            if not api_key:
                return Response(
                    {'error': 'UniPile API key not configured'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Check if this is an email message
            conversation = message.conversation
            channel = conversation.channel if conversation else None
            channel_type = channel.channel_type if channel else None
            
            # Get the UniPile account ID from the channel
            unipile_account_id = channel.unipile_account_id if channel else None
            
            # Use appropriate endpoint based on channel type
            if channel_type in ['gmail', 'outlook', 'mail', 'email']:
                # Try using the UniPile message ID first
                # The unipile_id from metadata should be the correct UniPile message ID
                if unipile_message_id:
                    download_url = f"{base_url}/api/v1/emails/{unipile_message_id}/attachments/{attachment_id}"
                    logger.info(f"Using UniPile message ID: {unipile_message_id}")
                else:
                    # Fallback to external_message_id with URL encoding
                    import urllib.parse
                    email_id = urllib.parse.quote(message.external_message_id, safe='')
                    if unipile_account_id:
                        download_url = f"{base_url}/api/v1/emails/{email_id}/attachments/{attachment_id}?account_id={unipile_account_id}"
                    else:
                        download_url = f"{base_url}/api/v1/emails/{email_id}/attachments/{attachment_id}"
                    logger.info(f"Using provider email ID (encoded): {email_id}")
            else:
                # Use messages endpoint for other channels (WhatsApp, LinkedIn, etc.)
                download_url = f"{base_url}/api/v1/messages/{unipile_message_id}/attachments/{attachment_id}"
            
            headers = {
                "accept": "*/*",
                "X-API-KEY": api_key
            }
            
            logger.info(f"Downloading attachment from UniPile: {download_url}")
            logger.info(f"Channel type: {channel_type}, Account ID: {unipile_account_id}")
            
            try:
                import time
                max_retries = 3
                retry_delay = 1  # seconds
                
                for attempt in range(max_retries):
                    try:
                        response = requests.get(download_url, headers=headers, timeout=30)
                        
                        if response.status_code == 200:
                            break  # Success, exit retry loop
                        elif response.status_code == 503:
                            # Service unavailable, retry
                            if attempt < max_retries - 1:
                                logger.warning(f"UniPile service unavailable, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                                time.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                                continue
                            else:
                                logger.error(f"UniPile API error 503 after {max_retries} attempts: {response.text}")
                                return Response(
                                    {'error': 'UniPile service temporarily unavailable. Please try again later.'},
                                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                                )
                        else:
                            logger.error(f"UniPile API error {response.status_code}: {response.text}")
                            # Try to provide more specific error messages
                            if response.status_code == 404:
                                error_msg = 'Attachment not found. It may have been deleted or expired.'
                            elif response.status_code == 422:
                                error_msg = 'Invalid message or attachment ID format.'
                            else:
                                error_msg = f'UniPile API error: {response.status_code}'
                            
                            return Response(
                                {'error': error_msg},
                                status=status.HTTP_502_BAD_GATEWAY
                            )
                    except requests.exceptions.Timeout:
                        if attempt < max_retries - 1:
                            logger.warning(f"Request timeout, retrying... (attempt {attempt + 1}/{max_retries})")
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            return Response(
                                {'error': 'Request timeout after multiple attempts'},
                                status=status.HTTP_504_GATEWAY_TIMEOUT
                            )
                
                # Return the file
                # Get content type from UniPile response
                response_content_type = response.headers.get('Content-Type', 'application/octet-stream')
                
                # Try to get filename from attachment metadata first
                filename = attachment.get('filename', 'attachment')
                logger.info(f"Filename from metadata: {filename}")
                
                # If we don't have a good filename, try to extract from attachment_id
                if filename == 'attachment' or not filename:
                    import base64
                    import urllib.parse
                    try:
                        # Decode the base64 attachment ID
                        decoded_id = base64.b64decode(attachment_id).decode('utf-8', errors='ignore')
                        # The format appears to be: [garbage].size.filename
                        # Split by dots and get the last part
                        parts = decoded_id.split('.')
                        if len(parts) >= 2:
                            # The last part should be the filename (URL encoded)
                            encoded_filename = parts[-1]
                            # URL decode it
                            extracted_filename = urllib.parse.unquote(encoded_filename)
                            if extracted_filename and extracted_filename != '':
                                filename = extracted_filename
                                logger.info(f"Extracted filename from attachment_id: {filename}")
                    except Exception as e:
                        logger.warning(f"Could not extract filename from attachment_id: {e}")
                
                # Ensure filename has an extension based on content type if needed
                if '.' not in filename and response_content_type:
                    # Add extension based on content type
                    import mimetypes
                    ext = mimetypes.guess_extension(response_content_type)
                    if ext:
                        filename = f"{filename}{ext}"
                
                logger.info(f"Serving attachment: filename={filename}, content_type={response_content_type}")
                
                http_response = HttpResponse(
                    response.content,
                    content_type=response_content_type
                )
                http_response['Content-Disposition'] = f'attachment; filename="{filename}"'
                http_response['Content-Length'] = len(response.content)
                
                return http_response
                
            except requests.exceptions.Timeout:
                return Response(
                    {'error': 'UniPile API timeout'},
                    status=status.HTTP_504_GATEWAY_TIMEOUT
                )
            except requests.exceptions.RequestException as e:
                return Response(
                    {'error': f'UniPile API request failed: {str(e)}'},
                    status=status.HTTP_502_BAD_GATEWAY
                )
                
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Message.DoesNotExist:
            return Response(
                {'error': 'Message not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error downloading attachment: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Mark a specific message as read or unread",
        parameters=[
            OpenApiParameter(name='message_id', type=str, required=True, location='query'),
            OpenApiParameter(name='mark_as_read', type=bool, default=True, location='query'),
        ],
        responses={200: {'description': 'Message read status updated'}}
    )
    @action(detail=True, methods=['post'], url_path='mark-message-read')
    def mark_message_read(self, request, pk=None):
        """Mark a specific message as read or unread"""
        try:
            record = Record.objects.get(pk=pk)
            message_id = request.query_params.get('message_id') or request.data.get('message_id')
            mark_as_read = request.query_params.get('mark_as_read', 'true').lower() == 'true'
            
            if not message_id:
                return Response(
                    {'error': 'message_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get the message and verify it belongs to this record
            message = Message.objects.filter(id=message_id).first()
            
            if not message:
                return Response(
                    {'error': 'Message not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Verify message is linked to this record through participants
            conversation_ids = self._get_record_conversation_ids(record)
            
            if message.conversation_id not in conversation_ids:
                return Response(
                    {'error': 'Message not associated with this record'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get UniPile IDs from message metadata
            unipile_id = None
            account_id = None
            
            if message.metadata:
                unipile_id = message.metadata.get('unipile_id')
                # Get account ID from channel
                if message.channel:
                    account_id = message.channel.unipile_account_id
            
            # If we don't have UniPile ID, try external_message_id
            if not unipile_id:
                unipile_id = message.external_message_id
            
            if not unipile_id:
                return Response(
                    {'error': 'Cannot update read status - missing UniPile message ID'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Call UniPile API to update read status
            from communications.channels.email.service import EmailService
            from asgiref.sync import async_to_sync
            
            service = EmailService()
            result = async_to_sync(service.mark_email_as_read)(
                email_id=unipile_id,
                account_id=account_id,
                mark_as_read=mark_as_read
            )
            
            if result.get('success'):
                # Update local message status
                new_status = MessageStatus.READ if mark_as_read else MessageStatus.DELIVERED
                message.status = new_status
                
                # Update metadata
                if message.metadata:
                    message.metadata['read_status'] = mark_as_read
                    if mark_as_read:
                        message.metadata['read_date'] = timezone.now().isoformat()
                else:
                    message.metadata = {
                        'read_status': mark_as_read,
                        'read_date': timezone.now().isoformat() if mark_as_read else None
                    }
                
                message.save(update_fields=['status', 'metadata'])
                
                # Update conversation unread count
                if message.conversation:
                    unread_count = message.conversation.messages.filter(
                        direction=MessageDirection.INBOUND,
                        status__in=[MessageStatus.DELIVERED, MessageStatus.SENT, MessageStatus.PENDING]
                    ).exclude(status=MessageStatus.READ).count()
                    
                    message.conversation.unread_count = unread_count
                    message.conversation.save(update_fields=['unread_count'])
                
                logger.info(f"Message {message_id} marked as {'read' if mark_as_read else 'unread'}")
                
                return Response({
                    'success': True,
                    'message_id': str(message_id),
                    'status': new_status,
                    'unread_count': message.conversation.unread_count if message.conversation else 0
                })
            else:
                return Response({
                    'success': False,
                    'error': result.get('error', 'Failed to update read status in email provider')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to mark message as read: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='messages/(?P<message_id>[^/]+)/mark-read')
    def mark_single_message_read(self, request, pk=None, message_id=None):
        """Mark a single message as read"""
        # Create mutable copy of request data
        mutable_data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        mutable_data['message_id'] = message_id
        mutable_data['mark_as_read'] = True
        request._full_data = mutable_data
        return self.mark_message_read(request, pk)
    
    @action(detail=True, methods=['post'], url_path='messages/(?P<message_id>[^/]+)/mark-unread')
    def mark_single_message_unread(self, request, pk=None, message_id=None):
        """Mark a single message as unread"""
        # Create mutable copy of request data
        mutable_data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        mutable_data['message_id'] = message_id
        mutable_data['mark_as_read'] = False
        request._full_data = mutable_data
        return self.mark_message_read(request, pk)
    
    @extend_schema(
        summary="Mark conversations as read (frontend compatibility)",
        responses={200: {'description': 'Marked as read'}}
    )
    @action(detail=True, methods=['post'], url_path='mark_read')
    def mark_read(self, request, pk=None):
        """Mark messages as read - supports both single message and all messages"""
        message_id = request.data.get('message_id')
        conversation_id = request.data.get('conversation_id')
        
        if message_id:
            # Mark single message as read
            return self.mark_message_read(request, pk)
        elif conversation_id:
            # Mark all messages in conversation as read
            return self.mark_conversation_read(request, pk)
        else:
            # Mark all messages for record as read
            return self.mark_all_read(request, pk)
    
    @action(detail=True, methods=['post'], url_path='mark-conversation-read')
    def mark_conversation_read(self, request, pk=None):
        """Mark all messages in a specific conversation as read"""
        try:
            from communications.channels.messaging.service import MessagingService
            from asgiref.sync import async_to_sync
            
            conversation_id = request.data.get('conversation_id')
            is_read = request.data.get('is_read', True)
            force_recalculate = request.data.get('force_recalculate', False)
            
            if not conversation_id:
                return Response(
                    {'error': 'conversation_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get the conversation
            conversation = Conversation.objects.get(id=conversation_id)
            channel_type = conversation.channel.channel_type if conversation.channel else None
            
            # Update local message status
            messages = Message.objects.filter(
                conversation=conversation,
                direction=MessageDirection.INBOUND
            )
            
            if is_read:
                messages = messages.exclude(status=MessageStatus.READ)
                new_status = MessageStatus.READ
            else:
                messages = messages.filter(status=MessageStatus.READ)
                new_status = MessageStatus.DELIVERED
            
            updated_count = messages.update(
                status=new_status,
                updated_at=timezone.now()
            )
            
            # Always recalculate the unread_count to ensure it's accurate
            # Count all inbound messages that are not marked as read
            actual_unread_count = Message.objects.filter(
                conversation=conversation,
                direction=MessageDirection.INBOUND
            ).exclude(
                status__in=[MessageStatus.READ, 'read']  # Check both uppercase and lowercase
            ).count()
            
            # Log if there's a discrepancy
            if conversation.unread_count != actual_unread_count:
                logger.info(f"Fixing unread_count discrepancy for conversation {conversation_id}: "
                           f"was {conversation.unread_count}, actually {actual_unread_count}")
            
            # Update the conversation's unread_count
            conversation.unread_count = actual_unread_count
            conversation.save(update_fields=['unread_count'])
            
            # Sync with UniPile for WhatsApp/LinkedIn
            if channel_type in ['whatsapp', 'linkedin'] and conversation.external_thread_id:
                try:
                    service = MessagingService(channel_type=channel_type)
                    result = async_to_sync(service.mark_chat_as_read)(
                        chat_id=conversation.external_thread_id,
                        is_read=is_read
                    )
                    
                    if not result.get('success'):
                        logger.warning(f"Failed to sync read status with UniPile: {result.get('error')}")
                except Exception as e:
                    logger.error(f"Error syncing read status with UniPile: {e}")
            
            return Response({
                'success': True,
                'updated_count': updated_count,
                'conversation_id': str(conversation.id),
                'is_read': is_read,
                'unread_count': conversation.unread_count
            })
            
        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to mark conversation as read: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='(?P<conversation_id>[^/]+)/mark-conversation-unread')
    def mark_conversation_unread(self, request, conversation_id=None):
        """Mark conversation as unread by marking at least one message as unread"""
        try:
            from communications.channels.messaging.service import MessagingService
            from asgiref.sync import async_to_sync
            
            mark_as_unread = request.data.get('mark_as_unread', True)
            
            # Get the conversation
            conversation = Conversation.objects.get(id=conversation_id)
            channel_type = conversation.channel.channel_type if conversation.channel else None
            
            if mark_as_unread:
                # Mark the most recent inbound message as unread to trigger unread state
                last_inbound = Message.objects.filter(
                    conversation=conversation,
                    direction=MessageDirection.INBOUND
                ).order_by('-created_at').first()
                
                if last_inbound:
                    last_inbound.status = MessageStatus.DELIVERED
                    last_inbound.updated_at = timezone.now()
                    last_inbound.save(update_fields=['status', 'updated_at'])
                    
                    # Update conversation unread count to at least 1
                    conversation.unread_count = max(1, Message.objects.filter(
                        conversation=conversation,
                        direction=MessageDirection.INBOUND
                    ).exclude(
                        status__in=[MessageStatus.READ, 'read']
                    ).count())
                else:
                    # No inbound messages to mark as unread
                    return Response({
                        'success': False,
                        'error': 'No messages to mark as unread'
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Mark all as read (same as mark_conversation_read with is_read=True)
                messages = Message.objects.filter(
                    conversation=conversation,
                    direction=MessageDirection.INBOUND
                ).exclude(status=MessageStatus.READ)
                
                messages.update(
                    status=MessageStatus.READ,
                    updated_at=timezone.now()
                )
                
                conversation.unread_count = 0
            
            conversation.save(update_fields=['unread_count'])
            
            # Sync with UniPile for WhatsApp/LinkedIn
            if channel_type in ['whatsapp', 'linkedin'] and conversation.external_thread_id:
                try:
                    service = MessagingService(channel_type=channel_type)
                    result = async_to_sync(service.mark_chat_as_read)(
                        chat_id=conversation.external_thread_id,
                        is_read=not mark_as_unread
                    )
                    
                    if not result.get('success'):
                        logger.warning(f"Failed to sync read status with UniPile: {result.get('error')}")
                except Exception as e:
                    logger.error(f"Error syncing read status with UniPile: {e}")
            
            return Response({
                'success': True,
                'conversation_id': str(conversation.id),
                'is_unread': mark_as_unread,
                'unread_count': conversation.unread_count
            })
            
        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to mark conversation as unread: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Mark all conversations as read",
        responses={200: {'description': 'Marked as read'}}
    )
    @action(detail=True, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request, pk=None):
        """Mark all messages for this record as read"""
        try:
            record = Record.objects.get(pk=pk)
            
            # Get all unread messages for this record
            conversations = self._get_record_conversation_ids(record)
            
            unread_messages = Message.objects.filter(
                conversation__in=conversations,
                direction=MessageDirection.INBOUND,
                status__in=[MessageStatus.DELIVERED, MessageStatus.SENT, MessageStatus.PENDING]
            ).exclude(status=MessageStatus.READ)
            
            from communications.tasks import sync_email_read_status_to_provider
            from django.db import connection
            
            updated_count = 0
            email_sync_count = 0
            
            for message in unread_messages:
                # Update local status
                message.status = MessageStatus.READ
                if message.metadata:
                    message.metadata['read_status'] = True
                    message.metadata['read_date'] = timezone.now().isoformat()
                else:
                    message.metadata = {
                        'read_status': True,
                        'read_date': timezone.now().isoformat()
                    }
                message.save(update_fields=['status', 'metadata'])
                updated_count += 1
                
                # Queue sync with email provider if this is an email
                if message.channel and message.channel.channel_type == 'email' and message.external_id:
                    try:
                        sync_email_read_status_to_provider.delay(
                            message_id=message.id,
                            tenant_schema=connection.schema_name,
                            mark_as_read=True
                        )
                        email_sync_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to queue read status sync for message {message.id}: {e}")
            
            # Update all conversation unread counts
            Conversation.objects.filter(
                id__in=conversations
            ).update(unread_count=0)
            
            # Update profile
            profile = RecordCommunicationProfile.objects.filter(
                record=record
            ).first()
            
            if profile:
                profile.total_unread = 0
                profile.save(update_fields=['total_unread'])
            
            response_message = f'Marked {updated_count} messages as read'
            if email_sync_count > 0:
                response_message += f' (syncing {email_sync_count} emails to provider)'
            
            return Response({
                'success': True,
                'messages_updated': updated_count,
                'emails_syncing': email_sync_count,
                'message': response_message
            })
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send WhatsApp or LinkedIn message from record context"""
        try:
            from communications.channels.messaging.service import MessagingService
            from asgiref.sync import async_to_sync
            
            record = Record.objects.get(pk=pk)
            
            # Log the request
            logger.info(f"💬 Message send request received for record {pk}")
            logger.info(f"💬 Request data: {json.dumps(request.data, indent=2)}")
            
            # Get data from request
            account_id = request.data.get('from_account_id')
            to = request.data.get('to')  # Phone number or LinkedIn ID
            text = request.data.get('text', '').strip()
            conversation_id = request.data.get('conversation_id')
            attachments = request.data.get('attachments', [])
            
            if not account_id or not text:
                return Response({
                    'success': False,
                    'error': 'from_account_id and text are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the user's connection to determine channel type
            connection = UserChannelConnection.objects.filter(
                user=request.user,
                unipile_account_id=account_id
            ).first()
            
            if not connection:
                return Response({
                    'success': False,
                    'error': 'Account connection not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            channel_type = connection.channel_type
            
            # Validate channel type
            if channel_type not in ['whatsapp', 'linkedin']:
                return Response({
                    'success': False,
                    'error': f'Channel type {channel_type} does not support messaging. Use send_email for email.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Initialize messaging service
            service = MessagingService(channel_type=channel_type)
            
            # Get or create conversation
            conversation = None
            chat_id = None
            
            if conversation_id:
                # Use existing conversation
                conversation = Conversation.objects.get(id=conversation_id)
                chat_id = conversation.external_thread_id
                logger.info(f"💬 Using existing conversation {conversation_id} with chat_id {chat_id}")
            elif to:
                # Find existing chat or create new one with the recipient
                logger.info(f"💬 Looking for existing chat or creating new one with {to}")
                
                # Format attendee ID based on channel type
                if channel_type == 'whatsapp':
                    # Ensure phone number is in correct format
                    import re
                    phone = re.sub(r'[^\d+]', '', to)  # Remove non-digits except +
                    if not phone.startswith('+'):
                        # Assume US number if no country code
                        phone = f'+1{phone}' if len(phone) == 10 else f'+{phone}'
                    attendee_id = f"{phone.replace('+', '')}@s.whatsapp.net"
                else:  # linkedin
                    # to should be the LinkedIn member URN or profile ID
                    attendee_id = to
                
                # Find existing chat or create new one
                result = async_to_sync(service.find_or_create_chat)(
                    account_id=account_id,
                    attendee_id=attendee_id,
                    text=text,
                    attachments=attachments
                )
                
                if result.get('success'):
                    chat_id = result.get('chat_id')
                    was_created = result.get('created', False)
                    was_found = result.get('found', False)
                    
                    # Create conversation in database
                    from communications.models import Channel
                    channel, _ = Channel.objects.get_or_create(
                        unipile_account_id=account_id,
                        channel_type=channel_type,
                        defaults={
                            'name': f"{channel_type.title()} - {connection.account_name}",
                            'auth_status': 'authenticated',
                            'is_active': True,
                            'created_by': request.user
                        }
                    )
                    
                    # Check if conversation already exists for this chat
                    conversation, created = Conversation.objects.get_or_create(
                        channel=channel,
                        external_thread_id=chat_id,
                        defaults={
                            'subject': f"Chat with {to}",
                            'status': 'active',
                            'metadata': {
                                'started_from_record': str(record.id),
                                'recipient': to
                            }
                        }
                    )
                    
                    if created:
                        logger.info(f"✅ Created new conversation {conversation.id} for chat {chat_id}")
                    else:
                        logger.info(f"✅ Using existing conversation {conversation.id} for chat {chat_id}")
                    
                    # No need to create RecordCommunicationLink anymore
                    # The conversation is linked through participants
                    
                    if was_created:
                        logger.info(f"✅ Created new chat {chat_id} and conversation {conversation.id}")
                        # Message was already sent when creating chat
                        return Response({
                            'success': True,
                            'conversation_id': str(conversation.id),
                            'chat_id': chat_id,
                            'new_chat': True,
                            'message': f'{channel_type.title()} message sent and new chat created'
                        })
                    elif was_found:
                        logger.info(f"✅ Found existing chat {chat_id}, need to send message")
                        # Found existing chat, need to send the message
                        # Continue to the send message section below
                        pass
                    else:
                        logger.error(f"Unexpected state: chat not found and not created")
                        return Response({
                            'success': False,
                            'error': 'Could not find or create chat'
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                else:
                    return Response({
                        'success': False,
                        'error': result.get('error', 'Failed to start new chat')
                    }, status=status.HTTP_502_BAD_GATEWAY)
            else:
                return Response({
                    'success': False,
                    'error': 'Either conversation_id or to (recipient) is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Send message to existing chat
            if chat_id and conversation:
                result = async_to_sync(service.send_message)(
                    chat_id=chat_id,
                    text=text,
                    attachments=attachments
                )
                
                if result.get('success'):
                    # Create message in database
                    message = Message.objects.create(
                        channel=conversation.channel,
                        conversation=conversation,
                        external_message_id=result.get('message_id'),
                        content=text,
                        direction=MessageDirection.OUTBOUND,
                        status=MessageStatus.SENT,
                        metadata={
                            'sent_from_record': str(record.id),
                            'attachments': attachments
                        }
                    )
                    
                    # Update conversation last message time
                    conversation.last_message_at = timezone.now()
                    conversation.save(update_fields=['last_message_at'])
                    
                    logger.info(f"✅ Sent {channel_type} message {message.id} to chat {chat_id}")
                    
                    return Response({
                        'success': True,
                        'message_id': str(message.id),
                        'conversation_id': str(conversation.id),
                        'message': f'{channel_type.title()} message sent successfully'
                    })
                else:
                    return Response({
                        'success': False,
                        'error': result.get('error', 'Failed to send message')
                    }, status=status.HTTP_502_BAD_GATEWAY)
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )