"""
Base views for channel API endpoints
All channel-specific views should inherit from this
"""
from abc import ABC, abstractmethod
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


class BaseChannelViews(ABC):
    """Abstract base class for channel views"""
    
    def __init__(self):
        """Initialize the channel views"""
        self.channel_type = self.get_channel_type()
        self.service = self.get_service()
    
    @abstractmethod
    def get_channel_type(self) -> str:
        """Return the channel type (e.g., 'whatsapp', 'email', 'linkedin')"""
        pass
    
    @abstractmethod
    def get_service(self):
        """Return the channel-specific service instance"""
        pass
    
    def get_conversations_view(self):
        """
        Create view function for getting conversations
        Returns a view function that can be used in URL patterns
        """
        @api_view(['GET'])
        @permission_classes([IsAuthenticated])
        def view(request):
            account_id = request.GET.get('account_id')
            limit = int(request.GET.get('limit', 50))
            cursor = request.GET.get('cursor')
            force_sync = request.GET.get('force_sync', 'false').lower() == 'true'
            
            if not account_id:
                return Response({
                    'success': False,
                    'error': 'account_id parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                from asgiref.sync import async_to_sync
                result = async_to_sync(self.service.sync_conversations)(
                    user=request.user,
                    account_id=account_id,
                    force_sync=force_sync
                )
                
                return Response({
                    'success': True,
                    'conversations': result.get('conversations', []),
                    'pagination': {
                        'limit': limit,
                        'cursor': cursor,
                        'next_cursor': result.get('next_cursor'),
                        'has_more': result.get('has_more', False)
                    },
                    'cache_info': {
                        'from_cache': not force_sync,
                        'sync_triggered': force_sync
                    }
                })
                
            except Exception as e:
                logger.error(f"Failed to get {self.channel_type} conversations: {e}")
                return Response({
                    'success': False,
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return view
    
    def get_messages_view(self):
        """
        Create view function for getting messages
        Returns a view function that can be used in URL patterns
        """
        @api_view(['GET'])
        @permission_classes([IsAuthenticated])
        def view(request, conversation_id):
            account_id = request.GET.get('account_id')
            limit = int(request.GET.get('limit', 50))
            cursor = request.GET.get('cursor')
            force_sync = request.GET.get('force_sync', 'true').lower() == 'true'
            
            if not account_id:
                return Response({
                    'success': False,
                    'error': 'account_id parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                from asgiref.sync import async_to_sync
                result = async_to_sync(self.service.sync_messages)(
                    user=request.user,
                    account_id=account_id,
                    conversation_id=conversation_id,
                    force_sync=force_sync
                )
                
                return Response({
                    'success': True,
                    'messages': result.get('messages', []),
                    'conversation_id': conversation_id,
                    'pagination': {
                        'limit': limit,
                        'cursor': cursor,
                        'next_cursor': result.get('next_cursor'),
                        'has_more': result.get('has_more', False)
                    }
                })
                
            except Exception as e:
                logger.error(f"Failed to get {self.channel_type} messages: {e}")
                return Response({
                    'success': False,
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return view
    
    def send_message_view(self):
        """
        Create view function for sending messages
        Returns a view function that can be used in URL patterns
        """
        @api_view(['POST'])
        @permission_classes([IsAuthenticated])
        def view(request, conversation_id):
            account_id = request.data.get('account_id')
            content = request.data.get('text') or request.data.get('content')
            attachments = request.data.get('attachments', [])
            
            if not account_id:
                return Response({
                    'success': False,
                    'error': 'account_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not content and not attachments:
                return Response({
                    'success': False,
                    'error': 'Either text or attachments are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                from asgiref.sync import async_to_sync
                result = async_to_sync(self.service.send_message)(
                    user=request.user,
                    account_id=account_id,
                    conversation_id=conversation_id,
                    content=content,
                    attachments=attachments
                )
                
                if result.get('success'):
                    return Response({
                        'success': True,
                        'message': result.get('message'),
                        'message_id': result.get('message', {}).get('id')
                    })
                else:
                    return Response({
                        'success': False,
                        'error': result.get('error', 'Failed to send message')
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Exception as e:
                logger.error(f"Failed to send {self.channel_type} message: {e}")
                return Response({
                    'success': False,
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return view
    
    def mark_read_view(self):
        """
        Create view function for marking messages as read
        Returns a view function that can be used in URL patterns
        """
        @api_view(['POST'])
        @permission_classes([IsAuthenticated])
        def view(request, conversation_id, message_id):
            account_id = request.data.get('account_id')
            
            if not account_id:
                return Response({
                    'success': False,
                    'error': 'account_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                from asgiref.sync import async_to_sync
                result = async_to_sync(self.service.client.mark_as_read)(
                    account_id=account_id,
                    conversation_id=conversation_id,
                    message_id=message_id
                )
                
                return Response({
                    'success': True,
                    'result': result
                })
                
            except Exception as e:
                logger.error(f"Failed to mark {self.channel_type} message as read: {e}")
                return Response({
                    'success': False,
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return view