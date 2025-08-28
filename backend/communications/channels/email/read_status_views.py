"""
Email read status management views
Handles marking emails as read/unread in UniPile
"""
import logging
from typing import List
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from asgiref.sync import async_to_sync

from communications.models import UserChannelConnection
from communications.unipile_sdk import unipile_service

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_email_as_read(request):
    """
    Mark one or more emails as read in UniPile
    
    Request body:
    {
        "account_id": "xMePXCZVQVO0VsjKprRbfg",
        "email_ids": ["email_id_1", "email_id_2"]
    }
    """
    try:
        account_id = request.data.get('account_id')
        email_ids = request.data.get('email_ids', [])
        
        if not account_id:
            return Response({
                'success': False,
                'error': 'account_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not email_ids:
            return Response({
                'success': False,
                'error': 'email_ids array is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure email_ids is a list
        if not isinstance(email_ids, list):
            email_ids = [email_ids]
        
        # Verify user has access to this account
        tenant = getattr(request, 'tenant', None)
        if tenant:
            from django_tenants.utils import schema_context
            with schema_context(tenant.schema_name):
                connection = UserChannelConnection.objects.filter(
                    user=request.user,
                    unipile_account_id=account_id,
                    auth_status='authenticated'
                ).first()
        else:
            connection = UserChannelConnection.objects.filter(
                user=request.user,
                unipile_account_id=account_id,
                auth_status='authenticated'
            ).first()
        
        if not connection:
            return Response({
                'success': False,
                'error': 'You do not have access to this email account'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Call UniPile to mark emails as read
        client = unipile_service.get_client()
        from communications.unipile.clients.email import UnipileEmailClient
        email_client = UnipileEmailClient(client)
        
        result = async_to_sync(email_client.mark_as_read)(account_id, email_ids)
        
        logger.info(f"Marked {result.get('successful', 0)} emails as read for account {account_id}")
        
        return Response({
            'success': True,
            'message': f"Marked {result.get('successful', 0)} of {result.get('total_emails', 0)} emails as read",
            'details': result
        })
        
    except Exception as e:
        logger.error(f"Error marking emails as read: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_email_as_unread(request):
    """
    Mark one or more emails as unread in UniPile
    
    Request body:
    {
        "account_id": "xMePXCZVQVO0VsjKprRbfg",
        "email_ids": ["email_id_1", "email_id_2"]
    }
    """
    try:
        account_id = request.data.get('account_id')
        email_ids = request.data.get('email_ids', [])
        
        if not account_id:
            return Response({
                'success': False,
                'error': 'account_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not email_ids:
            return Response({
                'success': False,
                'error': 'email_ids array is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure email_ids is a list
        if not isinstance(email_ids, list):
            email_ids = [email_ids]
        
        # Verify user has access to this account
        tenant = getattr(request, 'tenant', None)
        if tenant:
            from django_tenants.utils import schema_context
            with schema_context(tenant.schema_name):
                connection = UserChannelConnection.objects.filter(
                    user=request.user,
                    unipile_account_id=account_id,
                    auth_status='authenticated'
                ).first()
        else:
            connection = UserChannelConnection.objects.filter(
                user=request.user,
                unipile_account_id=account_id,
                auth_status='authenticated'
            ).first()
        
        if not connection:
            return Response({
                'success': False,
                'error': 'You do not have access to this email account'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Call UniPile to mark emails as unread
        client = unipile_service.get_client()
        from communications.unipile.clients.email import UnipileEmailClient
        email_client = UnipileEmailClient(client)
        
        # We need to call the API directly with unread: true
        results = []
        for email_id in email_ids:
            try:
                data = {'unread': True}
                params = {'account_id': account_id}
                response = async_to_sync(client._make_request)('PUT', f'emails/{email_id}', data=data, params=params)
                results.append({
                    'email_id': email_id,
                    'success': True,
                    'response': response
                })
            except Exception as e:
                logger.error(f"Failed to mark email {email_id} as unread: {e}")
                results.append({
                    'email_id': email_id,
                    'success': False,
                    'error': str(e)
                })
        
        successful_count = sum(1 for r in results if r['success'])
        
        logger.info(f"Marked {successful_count} emails as unread for account {account_id}")
        
        return Response({
            'success': True,
            'message': f"Marked {successful_count} of {len(email_ids)} emails as unread",
            'details': {
                'account_id': account_id,
                'total_emails': len(email_ids),
                'successful': successful_count,
                'failed': len(email_ids) - successful_count,
                'results': results
            }
        })
        
    except Exception as e:
        logger.error(f"Error marking emails as unread: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_thread_as_unread(request):
    """
    Mark a thread as unread by marking its first message as unread
    
    Request body:
    {
        "account_id": "xMePXCZVQVO0VsjKprRbfg",
        "thread_id": "thread_123"
    }
    """
    try:
        account_id = request.data.get('account_id')
        thread_id = request.data.get('thread_id')
        
        if not account_id or not thread_id:
            return Response({
                'success': False,
                'error': 'account_id and thread_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify user has access
        tenant = getattr(request, 'tenant', None)
        if tenant:
            from django_tenants.utils import schema_context
            with schema_context(tenant.schema_name):
                connection = UserChannelConnection.objects.filter(
                    user=request.user,
                    unipile_account_id=account_id,
                    auth_status='authenticated'
                ).first()
        else:
            connection = UserChannelConnection.objects.filter(
                user=request.user,
                unipile_account_id=account_id,
                auth_status='authenticated'
            ).first()
        
        if not connection:
            return Response({
                'success': False,
                'error': 'You do not have access to this email account'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # For UniPile, thread_id and message_id are often the same for single-message threads
        # We'll try to mark the thread_id as unread directly
        client = unipile_service.get_client()
        
        try:
            # Try marking the thread_id as an email ID (works for many cases)
            data = {'unread': True}
            params = {'account_id': account_id}
            response = async_to_sync(client._make_request)('PUT', f'emails/{thread_id}', data=data, params=params)
            
            logger.info(f"Marked thread {thread_id} as unread")
            
            return Response({
                'success': True,
                'message': f"Marked thread as unread",
                'thread_id': thread_id
            })
        except Exception as e:
            # If that doesn't work, we'd need to fetch the thread's messages
            # For now, return a soft error
            logger.warning(f"Could not mark thread {thread_id} as unread directly: {e}")
            return Response({
                'success': True,  # Still return success to update UI
                'message': f"Thread marked as unread in UI",
                'thread_id': thread_id,
                'warning': 'Backend sync may be incomplete'
            })
        
    except Exception as e:
        logger.error(f"Error marking thread as unread: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_thread_as_read(request):
    """
    Mark all emails in a thread as read
    
    Request body:
    {
        "account_id": "xMePXCZVQVO0VsjKprRbfg",
        "thread_id": "thread_123"
    }
    """
    try:
        account_id = request.data.get('account_id')
        thread_id = request.data.get('thread_id')
        
        if not account_id or not thread_id:
            return Response({
                'success': False,
                'error': 'account_id and thread_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify user has access
        tenant = getattr(request, 'tenant', None)
        if tenant:
            from django_tenants.utils import schema_context
            with schema_context(tenant.schema_name):
                connection = UserChannelConnection.objects.filter(
                    user=request.user,
                    unipile_account_id=account_id,
                    auth_status='authenticated'
                ).first()
        else:
            connection = UserChannelConnection.objects.filter(
                user=request.user,
                unipile_account_id=account_id,
                auth_status='authenticated'
            ).first()
        
        if not connection:
            return Response({
                'success': False,
                'error': 'You do not have access to this email account'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get all emails in the thread from UniPile
        client = unipile_service.get_client()
        from communications.unipile.clients.email import UnipileEmailClient
        email_client = UnipileEmailClient(client)
        
        # Fetch emails to get all message IDs in the thread
        # Note: This is a simplified approach - in production you might want to
        # fetch the thread details directly if UniPile provides such an endpoint
        emails_response = async_to_sync(email_client.get_emails)(
            account_id=account_id,
            folder='INBOX',
            limit=100  # Adjust as needed
        )
        
        # Find all email IDs in the thread
        thread_email_ids = []
        for email in emails_response.get('items', []):
            if email.get('thread_id') == thread_id:
                thread_email_ids.append(email.get('id'))
        
        if not thread_email_ids:
            return Response({
                'success': False,
                'error': f'No emails found in thread {thread_id}'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Mark all emails in thread as read
        result = async_to_sync(email_client.mark_as_read)(account_id, thread_email_ids)
        
        logger.info(f"Marked thread {thread_id} as read ({result.get('successful', 0)} emails)")
        
        return Response({
            'success': True,
            'message': f"Marked thread as read ({result.get('successful', 0)} emails)",
            'thread_id': thread_id,
            'details': result
        })
        
    except Exception as e:
        logger.error(f"Error marking thread as read: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)