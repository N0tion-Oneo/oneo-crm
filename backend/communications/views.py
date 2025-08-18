"""
REST API Views for Communication System
Focused purely on communication functionality - channels, messages, conversations
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from django.db.models import Q, Count, Avg
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from api.permissions import CommunicationPermission, MessagePermission, ChannelPermission, CommunicationTrackingPermission
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from asgiref.sync import sync_to_async

from .models import (
    Channel, Conversation, Message, CommunicationAnalytics, MessageDirection
)
from .serializers import (
    ChannelSerializer, ConversationListSerializer, ConversationDetailSerializer,
    MessageSerializer, MessageCreateSerializer,
    CommunicationAnalyticsSerializer, ChannelConnectionSerializer,
    MessageSendSerializer, BulkMessageSerializer
)
from .unipile_sdk import unipile_service
from pipelines.models import Record


class ChannelViewSet(viewsets.ModelViewSet):
    """ViewSet for communication channels"""
    
    queryset = Channel.objects.select_related('created_by')
    serializer_class = ChannelSerializer
    permission_classes = [ChannelPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['channel_type', 'is_active']
    search_fields = ['name', 'description', 'external_account_id']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user)
    
    @extend_schema(
        summary="Test channel connection",
        responses={200: {'type': 'object', 'properties': {
            'connected': {'type': 'boolean'},
            'message': {'type': 'string'}
        }}}
    )
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test connection to external channel"""
        channel = self.get_object()
        
        try:
            # Test connection asynchronously
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    unipile_service.test_connection(channel.external_account_id)
                )
                
                return Response({
                    'connected': result.get('connected', False),
                    'message': result.get('message', 'Connection test completed')
                })
                
            finally:
                loop.close()
                
        except Exception as e:
            return Response({
                'connected': False,
                'message': f'Connection test failed: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Sync channel messages",
        responses={200: {'type': 'object', 'properties': {
            'synced': {'type': 'integer'},
            'message': {'type': 'string'}
        }}}
    )
    @action(detail=True, methods=['post'])
    def sync_messages(self, request, pk=None):
        """Sync messages from external channel"""
        channel = self.get_object()
        
        # Queue sync task
        from .tasks import sync_channel_messages
        from django.db import connection
        
        sync_channel_messages.delay(
            str(channel.id), 
            connection.schema_name
        )
        
        return Response({
            'message': f'Message sync queued for channel {channel.name}',
            'queued': True
        })


class ConversationViewSet(viewsets.ModelViewSet):
    """ViewSet for conversations"""
    
    queryset = Conversation.objects.select_related('channel', 'primary_contact_record')
    permission_classes = [CommunicationPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['channel', 'status', 'priority']
    search_fields = ['subject', 'external_thread_id', 'primary_contact_record__data__first_name', 'primary_contact_record__data__company']
    ordering_fields = ['updated_at', 'created_at', 'message_count']
    ordering = ['-updated_at']
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail views"""
        if self.action == 'list':
            return ConversationListSerializer
        return ConversationDetailSerializer
    
    @extend_schema(
        summary="Get conversation statistics",
        responses={200: {'type': 'object', 'properties': {
            'total_conversations': {'type': 'integer'},
            'active_conversations': {'type': 'integer'},
            'average_response_time': {'type': 'number'}
        }}}
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get conversation statistics"""
        queryset = self.get_queryset()
        
        stats = {
            'total_conversations': queryset.count(),
            'active_conversations': queryset.filter(status='active').count(),
            'archived_conversations': queryset.filter(status='archived').count(),
            'average_message_count': queryset.aggregate(
                avg_messages=Avg('message_count')
            )['avg_messages'] or 0
        }
        
        return Response(stats)
    
    @extend_schema(
        summary="Archive conversation",
        responses={200: ConversationDetailSerializer}
    )
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a conversation"""
        conversation = self.get_object()
        conversation.status = 'archived'
        conversation.save()
        
        return Response(ConversationDetailSerializer(conversation).data)


class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet for messages"""
    
    queryset = Message.objects.select_related('channel', 'conversation', 'contact_record')
    permission_classes = [MessagePermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['direction', 'status', 'channel', 'conversation']
    search_fields = ['content', 'subject', 'contact_email']
    ordering_fields = ['created_at', 'sent_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Use different serializers for create vs other actions"""
        if self.action == 'create':
            return MessageCreateSerializer
        elif self.action == 'send_bulk':
            return BulkMessageSerializer
        elif self.action == 'send':
            return MessageSendSerializer
        return MessageSerializer
    
    @extend_schema(
        summary="Send a message",
        request=MessageSendSerializer,
        responses={201: MessageSerializer}
    )
    @action(detail=False, methods=['post'])
    def send(self, request):
        """Send a message through a channel"""
        serializer = MessageSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        channel_id = serializer.validated_data['channel_id']
        message_data = serializer.validated_data
        
        # Queue message sending
        from .tasks import send_scheduled_message
        from django.db import connection
        
        send_scheduled_message.delay(
            message_data=message_data,
            tenant_schema=connection.schema_name,
            channel_id=channel_id
        )
        
        return Response({
            'message': 'Message queued for sending',
            'queued': True
        }, status=status.HTTP_202_ACCEPTED)
    
    @extend_schema(
        summary="Send bulk messages",
        request=BulkMessageSerializer,
        responses={202: {'type': 'object', 'properties': {
            'queued': {'type': 'integer'},
            'message': {'type': 'string'}
        }}}
    )
    @action(detail=False, methods=['post'])
    def send_bulk(self, request):
        """Send bulk messages"""
        serializer = BulkMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Queue bulk message sending
        message_count = len(serializer.validated_data.get('recipients', []))
        
        return Response({
            'queued': message_count,
            'message': f'{message_count} messages queued for sending'
        }, status=status.HTTP_202_ACCEPTED)
    
    @extend_schema(
        summary="Connect message to existing contact",
        request={'type': 'object', 'properties': {
            'contact_id': {'type': 'integer'},
            'override_domain_validation': {'type': 'boolean', 'default': False},
            'override_reason': {'type': 'string'}
        }},
        responses={200: {'type': 'object', 'properties': {
            'status': {'type': 'string'},
            'contact_id': {'type': 'integer'},
            'domain_validated': {'type': 'boolean'}
        }}}
    )
    @action(detail=True, methods=['post'])
    def connect_contact(self, request, pk=None):
        """Manually connect a message to an existing contact with domain validation"""
        from communications.resolvers.relationship_context import RelationshipContextResolver
        from django.db import connection as db_connection
        
        message = self.get_object()
        contact_id = request.data.get('contact_id')
        override_domain_validation = request.data.get('override_domain_validation', False)
        
        if not contact_id:
            return Response(
                {'error': 'contact_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            contact_record = Record.objects.get(id=contact_id, is_deleted=False)
            
            # Initialize relationship resolver with tenant context
            tenant_id = db_connection.tenant.id if hasattr(db_connection, 'tenant') else None
            if tenant_id:
                relationship_resolver = RelationshipContextResolver(tenant_id=tenant_id)
                
                # Perform domain validation
                message_email = message.metadata.get('unmatched_contact_data', {}).get('email')
                if not message_email:
                    # Extract from message metadata
                    sender_info = message.metadata.get('sender', {})
                    message_email = sender_info.get('email') if isinstance(sender_info, dict) else None
                
                relationship_context = relationship_resolver.get_relationship_context(contact_record, message_email)
                
                # Warn if domain doesn't match but allow override
                if not relationship_context['domain_validated'] and not override_domain_validation:
                    return Response({
                        'warning': 'domain_mismatch',
                        'message': f"Email domain doesn't match contact's related pipeline records. Are you sure?",
                        'domain_details': {
                            'message_domain': relationship_context['message_domain'],
                            'pipeline_context': relationship_context['pipeline_context']
                        },
                        'requires_override': True
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Connect contact
                message.contact_record = contact_record
                message.metadata['relationship_context'] = relationship_context
                message.metadata['domain_validated'] = relationship_context['domain_validated']
                message.metadata.pop('needs_manual_resolution', None)
                
                if not relationship_context['domain_validated']:
                    message.metadata['domain_override_by'] = request.user.id
                    message.metadata['domain_override_reason'] = request.data.get('override_reason', '')
                
                message.save()
                
                # Update conversation primary contact (always update on manual connection)
                if message.conversation:
                    message.conversation.primary_contact_record = contact_record
                    message.conversation.metadata = message.conversation.metadata or {}
                    message.conversation.metadata['relationship_context'] = relationship_context
                    message.conversation.metadata['domain_validated'] = relationship_context['domain_validated']
                    message.conversation.metadata.pop('needs_manual_resolution', None)
                    message.conversation.save()
                
                return Response({
                    'status': 'connected',
                    'contact_id': contact_id,
                    'domain_validated': relationship_context['domain_validated']
                })
            else:
                # No tenant context, connect without validation
                message.contact_record = contact_record
                message.metadata.pop('needs_manual_resolution', None)
                message.save()
                
                # Update conversation primary contact
                if message.conversation:
                    message.conversation.primary_contact_record = contact_record
                    message.conversation.metadata = message.conversation.metadata or {}
                    message.conversation.metadata.pop('needs_manual_resolution', None)
                    message.conversation.save()
                
                return Response({
                    'status': 'connected',
                    'contact_id': contact_id,
                    'domain_validated': True
                })
                
        except Record.DoesNotExist:
            return Response({'error': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @extend_schema(
        summary="Create new contact from message data",
        request={'type': 'object', 'properties': {
            'pipeline_id': {'type': 'integer'},
            'contact_data': {'type': 'object'}
        }},
        responses={201: {'type': 'object', 'properties': {
            'status': {'type': 'string'},
            'contact_id': {'type': 'integer'},
            'contact_data': {'type': 'object'}
        }}}
    )
    @action(detail=True, methods=['post'])
    def create_contact(self, request, pk=None):
        """Create a new contact record from unmatched communication data"""
        message = self.get_object()
        pipeline_id = request.data.get('pipeline_id')
        contact_data = request.data.get('contact_data', {})
        
        if not pipeline_id:
            return Response(
                {'error': 'pipeline_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Merge with unmatched contact data from message
        unmatched_data = message.metadata.get('unmatched_contact_data', {})
        merged_data = {**unmatched_data, **contact_data}
        
        try:
            from pipelines.models import Pipeline
            pipeline = Pipeline.objects.get(id=pipeline_id)
            
            # Create new contact record
            contact_record = Record.objects.create(
                pipeline=pipeline,
                title=merged_data.get('name', merged_data.get('email', 'Unknown Contact')),
                data=merged_data,
                created_by=request.user
            )
            
            # Connect to message
            message.contact_record = contact_record
            message.metadata.pop('needs_manual_resolution', None)
            message.save()
            
            # Update conversation primary contact (always update on manual creation)
            if message.conversation:
                message.conversation.primary_contact_record = contact_record
                message.conversation.metadata = message.conversation.metadata or {}
                message.conversation.metadata.pop('needs_manual_resolution', None)
                message.conversation.save()
            
            return Response({
                'status': 'created',
                'contact_id': contact_record.id,
                'contact_data': contact_record.data
            }, status=status.HTTP_201_CREATED)
            
        except Pipeline.DoesNotExist:
            return Response({'error': 'Pipeline not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @extend_schema(
        summary="Get messages needing manual contact resolution",
        responses={200: MessageSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def unmatched_contacts(self, request):
        """Get list of messages that need manual contact resolution"""
        unmatched_messages = Message.objects.filter(
            contact_record__isnull=True,
            metadata__needs_manual_resolution=True
        ).select_related('conversation', 'channel').order_by('-created_at')
        
        serializer = self.get_serializer(unmatched_messages, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get messages with domain validation warnings",
        responses={200: MessageSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def domain_validation_warnings(self, request):
        """Get communications with domain validation warnings"""
        warnings = Message.objects.filter(
            metadata__needs_domain_review=True
        ).exclude(
            contact_record__is_deleted=True
        ).select_related('conversation', 'channel', 'contact_record').order_by('-created_at')
        
        serializer = self.get_serializer(warnings, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Disconnect conversation from contact",
        responses={200: {'type': 'object', 'properties': {
            'status': {'type': 'string'},
            'conversation_id': {'type': 'string'},
            'message': {'type': 'string'}
        }}}
    )
    @action(detail=True, methods=['post'])
    def disconnect_contact(self, request, pk=None):
        """Disconnect conversation from its linked contact record"""
        message = self.get_object()
        conversation = message.conversation
        
        if not conversation:
            return Response(
                {'error': 'Message has no associated conversation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not conversation.primary_contact_record:
            return Response(
                {'error': 'Conversation is not connected to any contact'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Store the disconnected contact info for audit trail
            disconnected_contact = {
                'contact_id': conversation.primary_contact_record.id,
                'contact_title': conversation.primary_contact_record.title,
                'pipeline_name': conversation.primary_contact_record.pipeline.name,
                'disconnected_at': timezone.now().isoformat(),
                'disconnected_by': request.user.id if request.user.is_authenticated else None
            }
            
            # Remove the contact connection
            conversation.primary_contact_record = None
            
            # Update metadata to track disconnection
            if not conversation.metadata:
                conversation.metadata = {}
                
            # Add to disconnection history
            if 'disconnection_history' not in conversation.metadata:
                conversation.metadata['disconnection_history'] = []
            conversation.metadata['disconnection_history'].append(disconnected_contact)
            
            # Remove auto-resolution metadata since this is now manually disconnected
            conversation.metadata.pop('auto_resolved', None)
            conversation.metadata.pop('auto_resolved_at', None)
            conversation.metadata.pop('resolution_method', None)
            
            # Mark as manually disconnected
            conversation.metadata['manually_disconnected'] = True
            conversation.metadata['manually_disconnected_at'] = timezone.now().isoformat()
            
            conversation.save()
            
            # Also disconnect the message if it was linked to the same contact
            if message.contact_record and message.contact_record.id == disconnected_contact['contact_id']:
                message.contact_record = None
                
                # Update message metadata
                if not message.metadata:
                    message.metadata = {}
                message.metadata['contact_disconnected'] = True
                message.metadata['disconnected_at'] = timezone.now().isoformat()
                
                message.save()
            
            return Response({
                'status': 'disconnected',
                'conversation_id': str(conversation.id),
                'message': f"Conversation disconnected from {disconnected_contact['contact_title']}",
                'disconnected_contact': disconnected_contact
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to disconnect contact: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CommunicationAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for communication analytics (read-only)"""
    
    queryset = CommunicationAnalytics.objects.all()
    serializer_class = CommunicationAnalyticsSerializer
    permission_classes = [CommunicationTrackingPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['date', 'channel']
    ordering_fields = ['date']
    ordering = ['-date']
    
    @extend_schema(
        summary="Get analytics summary",
        parameters=[
            OpenApiParameter(name='start_date', type=str, location='query'),
            OpenApiParameter(name='end_date', type=str, location='query'),
        ],
        responses={200: CommunicationAnalyticsSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get analytics summary for date range"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            start_date = datetime.fromisoformat(start_date).date()
            end_date = datetime.fromisoformat(end_date).date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        analytics = self.get_queryset().filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        return Response(CommunicationAnalyticsSerializer(analytics, many=True).data)


# Contact Resolution Monitoring API Views

class ContactResolutionMonitoringView(viewsets.GenericViewSet):
    """API endpoints for monitoring automatic contact resolution"""
    
    permission_classes = [CommunicationPermission]
    
    @extend_schema(
        summary="Get unconnected conversation statistics",
        responses={200: {'type': 'object', 'properties': {
            'total_unconnected': {'type': 'integer'},
            'recent_unconnected': {'type': 'integer'},
            'auto_resolved_total': {'type': 'integer'},
            'by_channel_type': {'type': 'array'},
            'resolution_candidates': {'type': 'integer'}
        }}}
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get statistics about unconnected conversations"""
        try:
            from communications.services.auto_resolution import UnconnectedConversationResolver
            from django.db import connection as db_connection
            
            # Get tenant ID
            tenant_id = db_connection.tenant.id if hasattr(db_connection, 'tenant') else None
            if not tenant_id:
                return Response(
                    {'error': 'Could not determine tenant context'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Initialize resolver and get stats
            resolver = UnconnectedConversationResolver(tenant_id=tenant_id)
            stats = resolver.get_unconnected_conversation_stats()
            
            return Response(stats)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to get statistics: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Trigger manual contact resolution",
        request={'type': 'object', 'properties': {
            'conversation_ids': {'type': 'array', 'items': {'type': 'string'}},
            'limit': {'type': 'integer', 'default': 50},
            'dry_run': {'type': 'boolean', 'default': False}
        }},
        responses={202: {'type': 'object', 'properties': {
            'task_id': {'type': 'string'},
            'status': {'type': 'string'}
        }}}
    )
    @action(detail=False, methods=['post'])
    def resolve(self, request):
        """Manually trigger contact resolution"""
        try:
            from communications.tasks import resolve_unconnected_conversations_task, resolve_conversation_contact_task
            from django.db import connection as db_connection
            
            # Get tenant schema
            tenant_schema = db_connection.schema_name if hasattr(db_connection, 'schema_name') else None
            if not tenant_schema or tenant_schema == 'public':
                return Response(
                    {'error': 'Could not determine tenant schema'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            conversation_ids = request.data.get('conversation_ids', [])
            limit = request.data.get('limit', 50)
            dry_run = request.data.get('dry_run', False)
            
            if dry_run:
                # For dry run, use the service directly
                from communications.services.auto_resolution import UnconnectedConversationResolver
                
                tenant_id = db_connection.tenant.id if hasattr(db_connection, 'tenant') else None
                if not tenant_id:
                    return Response(
                        {'error': 'Could not determine tenant ID'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                resolver = UnconnectedConversationResolver(tenant_id=tenant_id)
                
                if conversation_ids:
                    result = resolver.resolve_specific_conversations(conversation_ids)
                else:
                    result = resolver.resolve_batch(limit=limit, priority_recent=True)
                
                return Response({
                    'status': 'dry_run_completed',
                    'result': result
                })
            
            if conversation_ids:
                # Process specific conversations
                task_results = []
                for conversation_id in conversation_ids:
                    task = resolve_conversation_contact_task.delay(
                        conversation_id=str(conversation_id),
                        tenant_schema=tenant_schema
                    )
                    task_results.append({
                        'conversation_id': conversation_id,
                        'task_id': task.id
                    })
                
                return Response({
                    'status': 'tasks_queued',
                    'method': 'specific_conversations',
                    'queued_tasks': len(task_results),
                    'task_results': task_results
                }, status=status.HTTP_202_ACCEPTED)
            else:
                # Batch processing
                task = resolve_unconnected_conversations_task.delay(
                    tenant_schema=tenant_schema,
                    limit=limit
                )
                
                return Response({
                    'status': 'task_queued',
                    'method': 'batch_processing',
                    'task_id': task.id,
                    'limit': limit
                }, status=status.HTTP_202_ACCEPTED)
                
        except Exception as e:
            return Response(
                {'error': f'Failed to trigger resolution: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Get resolution candidates for a conversation",
        parameters=[
            OpenApiParameter(
                name='conversation_id',
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description='Conversation ID to analyze'
            ),
            OpenApiParameter(
                name='limit',
                type=int,
                location=OpenApiParameter.QUERY,
                default=5,
                description='Maximum candidates to return'
            )
        ],
        responses={200: {'type': 'object', 'properties': {
            'conversation_id': {'type': 'string'},
            'candidates': {'type': 'array'}
        }}}
    )
    @action(detail=False, methods=['get'])
    def candidates(self, request):
        """Get potential contact resolution candidates for a conversation"""
        try:
            conversation_id = request.query_params.get('conversation_id')
            limit = int(request.query_params.get('limit', 5))
            
            if not conversation_id:
                return Response(
                    {'error': 'conversation_id parameter is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            from communications.services.auto_resolution import UnconnectedConversationResolver
            from django.db import connection as db_connection
            
            # Get tenant ID
            tenant_id = db_connection.tenant.id if hasattr(db_connection, 'tenant') else None
            if not tenant_id:
                return Response(
                    {'error': 'Could not determine tenant context'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                conversation = Conversation.objects.get(id=conversation_id)
            except Conversation.DoesNotExist:
                return Response(
                    {'error': 'Conversation not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get candidates
            resolver = UnconnectedConversationResolver(tenant_id=tenant_id)
            candidates = resolver.get_resolution_candidates(conversation, limit=limit)
            
            return Response({
                'conversation_id': conversation_id,
                'conversation_subject': conversation.subject or 'No subject',
                'candidates': candidates
            })
            
        except ValueError:
            return Response(
                {'error': 'Invalid limit parameter'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to get candidates: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Get auto-resolution history",
        parameters=[
            OpenApiParameter(
                name='days',
                type=int,
                location=OpenApiParameter.QUERY,
                default=30,
                description='Days of history to retrieve'
            ),
            OpenApiParameter(
                name='channel_type',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by channel type'
            )
        ],
        responses={200: {'type': 'object', 'properties': {
            'total_auto_resolved': {'type': 'integer'},
            'resolution_history': {'type': 'array'},
            'success_rate': {'type': 'string'},
            'avg_resolution_time': {'type': 'string'}
        }}}
    )
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get history of automatic contact resolutions"""
        try:
            days = int(request.query_params.get('days', 30))
            channel_type = request.query_params.get('channel_type')
            
            # Calculate date range
            from datetime import timedelta
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            # Build query for auto-resolved conversations
            query = Conversation.objects.filter(
                primary_contact_record__isnull=False,
                metadata__auto_resolved=True,
                updated_at__gte=start_date
            ).select_related('primary_contact_record', 'channel')
            
            if channel_type:
                query = query.filter(channel__channel_type=channel_type)
            
            auto_resolved_conversations = query.order_by('-updated_at')
            
            # Build history data
            history = []
            for conversation in auto_resolved_conversations[:100]:  # Limit to 100 recent
                resolution_data = {
                    'conversation_id': str(conversation.id),
                    'resolved_at': conversation.metadata.get('auto_resolved_at'),
                    'resolution_method': conversation.metadata.get('resolution_method'),
                    'contact_id': conversation.primary_contact_record.id,
                    'contact_title': conversation.primary_contact_record.title,
                    'pipeline_name': conversation.primary_contact_record.pipeline.name,
                    'channel_type': conversation.channel.channel_type,
                    'domain_validated': conversation.metadata.get('domain_validated', True)
                }
                history.append(resolution_data)
            
            # Calculate statistics
            total_count = auto_resolved_conversations.count()
            domain_validated_count = auto_resolved_conversations.filter(
                metadata__domain_validated=True
            ).count()
            
            success_rate = f"{(domain_validated_count / total_count * 100):.1f}%" if total_count > 0 else "0%"
            
            return Response({
                'total_auto_resolved': total_count,
                'resolution_history': history,
                'success_rate': success_rate,
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                },
                'filters': {
                    'channel_type': channel_type
                }
            })
            
        except ValueError:
            return Response(
                {'error': 'Invalid days parameter'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to get resolution history: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )