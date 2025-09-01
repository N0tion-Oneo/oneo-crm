"""
API endpoints for record-centric communications
"""
import logging
import json
from datetime import datetime, timedelta

from django.db.models import Q, Count, Max, Prefetch
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers

from pipelines.models import Record
from communications.models import (
    Conversation, Message, Participant, UserChannelConnection
)
from rest_framework.permissions import IsAuthenticated

from .models import (
    RecordCommunicationProfile, RecordCommunicationLink, RecordSyncJob,
    RecordAttendeeMapping
)
from .serializers import (
    RecordCommunicationProfileSerializer,
    RecordConversationSerializer,
    RecordMessageSerializer,
    RecordCommunicationLinkSerializer,
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
            
            # Get all conversation links for this record
            links = RecordCommunicationLink.objects.filter(
                record=record
            ).select_related('conversation', 'conversation__channel')
            
            # Get unique conversation IDs
            conversation_ids = links.values_list('conversation_id', flat=True).distinct()
            
            if mode == 'smart':
                # Smart loading: All WhatsApp/LinkedIn + last 10 emails
                conversations_query = Conversation.objects.filter(
                    id__in=conversation_ids
                ).select_related('channel')
                
                # Get all WhatsApp and LinkedIn conversations
                social_conversations = conversations_query.filter(
                    channel__channel_type__in=['whatsapp', 'linkedin']
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
            
            # Verify the conversation is linked to this record
            link_exists = RecordCommunicationLink.objects.filter(
                record=record,
                conversation_id=conversation_id
            ).exists()
            
            if not link_exists:
                return Response(
                    {'error': 'Conversation not found for this record'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get pagination parameters
            limit = int(request.query_params.get('limit', 30))
            offset = int(request.query_params.get('offset', 0))
            
            # Get messages for the conversation (chronological order for reading)
            messages = Message.objects.filter(
                conversation_id=conversation_id
            ).select_related(
                'sender_participant', 'conversation', 'channel'
            ).order_by('created_at')[offset:offset + limit]
            
            # Get total count
            total_count = Message.objects.filter(
                conversation_id=conversation_id
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
            
            # Get all conversations linked to this record through RecordCommunicationLink
            from communications.record_communications.models import RecordCommunicationLink
            conversation_ids = RecordCommunicationLink.objects.filter(
                record=record
            ).values_list('conversation_id', flat=True)
            
            # Get all messages from these conversations
            messages = Message.objects.filter(
                conversation_id__in=conversation_ids
            )
            
            # Filter by channel type if specified
            if channel_type:
                messages = messages.filter(channel__channel_type=channel_type)
            
            # Get total count before pagination
            total_count = messages.count()
            
            # Order by time (newest first) and apply pagination
            messages = messages.select_related(
                'sender_participant', 'conversation', 'channel'
            ).order_by('-sent_at')[offset:offset + limit]
            
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
            
            # Get all linked conversations
            links = RecordCommunicationLink.objects.filter(record=record)
            conversation_ids = links.values_list('conversation_id', flat=True).distinct()
            
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
            
            stats = {
                'total_conversations': profile.total_conversations,
                'total_messages': profile.total_messages,
                'total_unread': profile.total_unread,
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
            
            result = sync_record_communications.delay(
                record_id=record.id,
                tenant_schema=connection.schema_name,
                triggered_by_id=request.user.id,
                trigger_reason='Manual API trigger'
            )
            
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
            logger.info(f"📧 Parsed - Subject: {subject}")
            logger.info(f"📧 Parsed - Body length: {len(body)} chars")
            
            # If replying to a specific message, get its provider_id for threading
            reply_to_external_id = None
            if reply_to_message_id:
                try:
                    reply_message = Message.objects.get(id=reply_to_message_id)
                    
                    # For threading, we need the provider_id (16-char hex from Gmail)
                    if reply_message.metadata and 'provider_id' in reply_message.metadata:
                        # Use the provider_id - this is what UniPile expects for reply_to
                        reply_to_external_id = reply_message.metadata['provider_id']
                        logger.info(f"Using provider_id from reply message for threading: {reply_to_external_id}")
                    else:
                        logger.warning(f"Reply message {reply_to_message_id} has no provider_id for threading")
                    
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
            
            if conversation_id:
                try:
                    conversation = Conversation.objects.get(id=conversation_id)
                    
                    # For threading, we need to find the last message in this conversation
                    # and use its provider_id (Gmail Message-ID) as reply_to
                    last_message = Message.objects.filter(
                        conversation=conversation
                    ).order_by('-created_at').first()
                    
                    if last_message:
                        # Try to get the provider_id from metadata (16-char hex from Gmail)
                        if last_message.metadata and 'provider_id' in last_message.metadata:
                            email_reply_to = last_message.metadata['provider_id']
                            logger.info(f"📧 Using provider_id for reply_to: {email_reply_to}")
                        else:
                            logger.info(f"📧 No valid provider_id found for threading")
                    else:
                        logger.info(f"📧 No previous message found in conversation for threading")
                        
                except Conversation.DoesNotExist:
                    logger.warning(f"Conversation {conversation_id} not found")
                    conversation = None
            else:
                # No conversation_id provided - this is a new email thread
                # Create a new conversation for it
                logger.info(f"📧 No conversation_id provided, creating new conversation")
                
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
                    
                    # Link conversation to record
                    from communications.record_communications.models import RecordCommunicationLink
                    RecordCommunicationLink.objects.get_or_create(
                        record=record,
                        conversation=conversation
                    )
                else:
                    logger.warning(f"📧 No Gmail channel found for account {account_id}")
            
            # Send email via UniPile
            # Use email_reply_to for conversation threading, or reply_to_external_id for specific reply
            final_reply_to = reply_to_external_id or email_reply_to
            
            result = async_to_sync(service.send_email)(
                account_id=account_id,
                to=to_formatted,
                subject=subject,
                body=body,
                cc=cc_formatted,
                bcc=bcc_formatted,
                reply_to=final_reply_to  # Use reply_to for UniPile threading
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
                            'reply_to': final_reply_to if final_reply_to else None
                        }
                    )
                    
                    # Update profile metrics
                    profile = RecordCommunicationProfile.objects.filter(record=record).first()
                    if profile:
                        profile.total_messages += 1
                        profile.last_message_at = timezone.now()
                        profile.save(update_fields=['total_messages', 'last_message_at'])
                
                return Response({
                    'success': True,
                    'tracking_id': result.get('tracking_id'),
                    'message': 'Email sent successfully'
                })
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
        summary="Mark conversations as read",
        responses={200: {'description': 'Marked as read'}}
    )
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark all conversations for this record as read"""
        try:
            record = Record.objects.get(pk=pk)
            
            # Get profile and reset unread count
            profile = RecordCommunicationProfile.objects.filter(
                record=record
            ).first()
            
            if profile:
                profile.total_unread = 0
                profile.save(update_fields=['total_unread'])
            
            # TODO: Mark actual messages as read in the conversation
            
            return Response({
                'status': 'success',
                'message': 'All conversations marked as read'
            })
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'Record not found'},
                status=status.HTTP_404_NOT_FOUND
            )