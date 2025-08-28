"""
WhatsApp Live Message Views
Fetches messages directly from UniPile without requiring stored conversations
"""
import logging
from typing import List, Dict, Any, Optional
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_whatsapp_chat_messages_live(request, chat_id):
    """
    Get messages for a WhatsApp chat directly from UniPile (live data)
    Does not require the conversation to be stored locally
    
    Path params:
    - chat_id: The UniPile chat ID
    
    Query params:
    - account_id: UniPile account ID
    - limit: Number of messages to fetch (default: 50)
    - cursor: Pagination cursor from UniPile
    """
    account_id = request.GET.get('account_id')
    limit = int(request.GET.get('limit', 50))
    cursor = request.GET.get('cursor')
    
    if not account_id:
        return Response({
            'success': False,
            'error': 'account_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from oneo_crm.settings import unipile_settings
        from communications.channels.whatsapp.utils.attendee_detection import WhatsAppAttendeeDetector
        from communications.utils.message_direction import determine_whatsapp_direction
        import requests
        
        # Get UniPile configuration
        dsn = unipile_settings.dsn
        access_token = unipile_settings.api_key
        
        # Initialize attendee detector for proper identification
        attendee_detector = WhatsAppAttendeeDetector(account_identifier=account_id)
        
        # Build request URL and headers for fetching messages
        url = f"{dsn}/api/v1/chats/{chat_id}/messages"
        headers = {
            'X-API-KEY': access_token,
            'Accept': 'application/json'
        }
        
        # Build params
        params = {
            'limit': limit,
            'account_id': account_id
        }
        if cursor:
            params['cursor'] = cursor
        
        # Fetch messages from UniPile
        logger.info(f"Fetching messages for chat {chat_id} from UniPile")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            logger.error(f"UniPile API error: {response.status_code} - {response.text}")
            return Response({
                'success': False,
                'messages': [],
                'error': f'Failed to fetch messages: {response.status_code}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        messages_data = response.json()
        
        # Get list of messages
        messages_list = messages_data.get('items', []) if isinstance(messages_data, dict) else messages_data
        
        # Transform messages to match frontend expectations
        messages = []
        for msg in messages_list:
            # Extract attendee information from the message
            attendee_info = attendee_detector.extract_attendee_from_api_message(msg)
            
            # Determine message direction using the unified function
            direction = determine_whatsapp_direction(msg, account_id)
            direction_frontend = 'outbound' if direction == 'out' else 'inbound'
            
            # Build from_attendee information
            from_attendee = {
                'id': attendee_info.get('external_id', ''),
                'phone_number': attendee_info.get('phone_number', ''),
                'name': attendee_info.get('name', 'Unknown'),
                'is_self': attendee_info.get('is_self', False)
            }
            
            # If message is from self (outbound) and no name, use "You"
            if attendee_info.get('is_self') and not from_attendee['name']:
                from_attendee['name'] = 'You'
            
            message = {
                'id': msg.get('id'),
                'external_id': msg.get('id'),
                'text': msg.get('text', ''),
                'from_attendee': from_attendee,
                'sent_at': msg.get('created_at') or msg.get('timestamp'),
                'direction': direction_frontend,
                'status': msg.get('status', 'sent'),
                'attachments': msg.get('attachments', [])
            }
            messages.append(message)
        
        # Get pagination info
        has_more = messages_data.get('has_more', False) if isinstance(messages_data, dict) else False
        next_cursor = messages_data.get('cursor', None) if isinstance(messages_data, dict) else None
        
        # Also fetch basic chat info and attendees
        chat_url = f"{dsn}/api/v1/chats/{chat_id}"
        chat_response = requests.get(chat_url, headers=headers, params={'account_id': account_id})
        
        chat_info = None
        if chat_response.status_code == 200:
            chat_data = chat_response.json()
            
            # Fetch attendees separately as they're not included in chat response
            attendees_url = f"{dsn}/api/v1/chats/{chat_id}/attendees"
            attendees_response = requests.get(attendees_url, headers=headers)
            
            attendees = []
            if attendees_response.status_code == 200:
                attendees_data = attendees_response.json()
                attendees_list = attendees_data.get('items', []) if isinstance(attendees_data, dict) else attendees_data
                
                # Process each attendee using our detector
                for att in attendees_list:
                    attendee_info = attendee_detector.extract_chat_attendees({'attendees': [att]})[0] if attendee_detector.extract_chat_attendees({'attendees': [att]}) else {}
                    attendees.append({
                        'id': att.get('id'),
                        'name': att.get('name', 'Unknown'),
                        'phone_number': attendee_info.get('phone_number', ''),
                        'is_self': att.get('is_self', 0) == 1,
                        'picture_url': att.get('picture_url', '')
                    })
            
            chat_info = {
                'id': chat_data.get('id'),
                'external_thread_id': chat_data.get('id'),
                'name': chat_data.get('name') or chat_data.get('title', 'WhatsApp Chat'),
                'is_group': chat_data.get('type', 0) == 2,  # type 2 is group
                'unread_count': chat_data.get('unread_count', 0),
                'participant_count': len(attendees),
                'attendees': attendees
            }
        
        return Response({
            'success': True,
            'messages': messages,
            'chat': chat_info,
            'has_more': has_more,
            'cursor': next_cursor,
            'source': 'live'
        })
        
    except Exception as e:
        logger.error(f"Error fetching WhatsApp messages: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return Response({
            'success': False,
            'messages': [],
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)