"""
Custom calendar event views for manual event creation
Separate from the formal scheduling system
"""
import logging
from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from asgiref.sync import async_to_sync

from communications.models import (
    Channel, ChannelType, Conversation, Message, 
    Participant, ConversationParticipant,
    MessageDirection, MessageStatus
)
from communications.unipile.clients.calendar import UnipileCalendarClient
from communications.unipile.core.client import UnipileClient
from pipelines.models import Record
from django.conf import settings

logger = logging.getLogger(__name__)


class CustomCalendarEventViewSet(viewsets.ViewSet):
    """
    ViewSet for creating custom calendar events
    These are manual events, not formal scheduled meetings
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def create_event(self, request):
        """
        Create a custom calendar event
        
        Expected data:
        - title: Event title
        - event_type: meeting/call/task/reminder
        - start_time: ISO datetime
        - end_time: ISO datetime
        - location: Location/meeting link
        - location_type: google_meet/teams/zoom/phone/in_person/other
        - description: Event description
        - attendees: List of email addresses
        - record_id: Associated record ID
        - add_to_calendar: Boolean to add to user's calendar
        """
        try:
            data = request.data
            user = request.user
            
            # Validate required fields
            if not data.get('title') or not data.get('start_time'):
                return Response(
                    {'error': 'Title and start time are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Step 1: Check for SchedulingProfile (following scheduling pattern)
            from communications.scheduling.models import SchedulingProfile
            profile = SchedulingProfile.objects.filter(user=user).select_related('calendar_connection').first()
            
            if not profile or not profile.calendar_connection:
                logger.warning(f"User {user.username} has no calendar connection configured")
                # Still allow event creation but without calendar sync
                # This matches the scheduling behavior where it continues without calendar creation
            
            # Parse dates
            start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00')) if data.get('end_time') else None
            
            # If no end time, default to 1 hour after start
            if not end_time:
                from datetime import timedelta
                end_time = start_time + timedelta(hours=1)
            
            # Step 2: Get or create CALENDAR channel (following scheduling pattern)
            channel = Channel.objects.filter(
                channel_type=ChannelType.CALENDAR,
                created_by=user
            ).first()
            
            if not channel:
                # Create channel following scheduling pattern
                channel = Channel.objects.create(
                    name=f"{user.get_full_name() or user.username} - Calendar Events",
                    channel_type=ChannelType.CALENDAR,
                    unipile_account_id=profile.calendar_connection.unipile_account_id if profile and profile.calendar_connection else f"calendar_{user.id}",
                    auth_status='authenticated' if profile and profile.calendar_connection else 'pending',
                    created_by=user,
                    metadata={
                        'provider': profile.calendar_connection.provider if profile and profile.calendar_connection else 'manual',
                        'calendar_type': 'custom_events'
                    }
                )
            
            # Step 3: Create conversation (following scheduling pattern)
            import uuid
            conversation = Conversation.objects.create(
                channel=channel,
                external_thread_id=f"event_{uuid.uuid4().hex[:12]}",  # Similar to scheduling pattern
                subject=data['title'],
                conversation_type='calendar_event',  # More specific type
                status='scheduled',  # Event is scheduled, not just active
                metadata={
                    'event_type': data.get('event_type', 'meeting'),
                    'event_details': {
                        'start_time': start_time.isoformat(),
                        'end_time': end_time.isoformat(),
                        'location': data.get('location', ''),
                        'location_type': data.get('location_type', 'other'),
                        'description': data.get('description', ''),
                    },
                    'is_custom_event': True,
                    'created_from': 'record_communications',
                    'created_by': user.id
                }
            )
            
            # Step 4: Add participants (following scheduling pattern)
            # First add the organizer (current user)
            organizer_participant, created = Participant.objects.get_or_create(
                email=user.email,
                defaults={
                    'name': user.get_full_name() or user.username,
                    'participant_type': 'internal'
                }
            )
            ConversationParticipant.objects.create(
                conversation=conversation,
                participant=organizer_participant,
                role='organizer'
            )
            
            # Add attendees
            attendees = data.get('attendees', [])
            for email in attendees:
                if email and email != user.email:  # Don't duplicate organizer
                    participant, created = Participant.objects.get_or_create(
                        email=email,
                        defaults={
                            'name': email.split('@')[0],
                            'participant_type': 'external'
                        }
                    )
                    ConversationParticipant.objects.create(
                        conversation=conversation,
                        participant=participant,
                        role='attendee'
                    )
            
            # Link to record if provided (following scheduling pattern)
            record = None
            if data.get('record_id'):
                try:
                    record = Record.objects.get(id=data['record_id'])
                    # Add record's participant similar to scheduling
                    from pipelines.serializers import RecordSerializer
                    record_data = RecordSerializer(record).data
                    
                    # Get record's email from communication identifiers
                    if hasattr(record, 'communication_identifiers'):
                        email = record.communication_identifiers.get('email', [None])[0]
                        if email and email not in [user.email] + attendees:
                            participant, created = Participant.objects.get_or_create(
                                email=email,
                                defaults={
                                    'name': record_data.get('title', email.split('@')[0]),
                                    'participant_type': 'contact'
                                }
                            )
                            participant.contact_record = record
                            participant.save()
                            
                            ConversationParticipant.objects.create(
                                conversation=conversation,
                                participant=participant,
                                role='contact'  # More specific than 'primary'
                            )
                except Record.DoesNotExist:
                    logger.warning(f"Record {data['record_id']} not found")
            
            # Step 5: Create event message (following scheduling pattern)
            # Build structured message similar to BookingProcessor
            message_parts = [
                f"📅 **Event Scheduled: {data['title']}**",
                "",
                f"**Date & Time:**",
                f"📆 {start_time.strftime('%A, %B %d, %Y')}",
                f"🕐 {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p %Z')}",
                ""
            ]
            
            # Add location information
            if data.get('location'):
                location_icon = {
                    'google_meet': '🎥',
                    'teams': '🎥',
                    'zoom': '🎥',
                    'in_person': '📍',
                    'phone': '📞',
                    'other': '🔗'
                }.get(data.get('location_type', 'other'), '🔗')
                
                message_parts.extend([
                    f"**Location:**",
                    f"{location_icon} {data['location']}",
                    ""
                ])
            
            # Add description if provided
            if data.get('description'):
                message_parts.extend([
                    f"**Details:**",
                    data['description'],
                    ""
                ])
            
            # Add attendees list
            if attendees or (record and hasattr(record, 'communication_identifiers')):
                message_parts.append("**Attendees:**")
                
                # Add organizer
                message_parts.append(f"• {user.get_full_name() or user.username} (Organizer)")
                
                # Add record contact if exists
                if record and hasattr(record, 'communication_identifiers'):
                    email = record.communication_identifiers.get('email', [None])[0]
                    if email:
                        from pipelines.serializers import RecordSerializer
                        record_data = RecordSerializer(record).data
                        message_parts.append(f"• {record_data.get('title', email)}")
                
                # Add other attendees
                for email in attendees:
                    if email and email != user.email:
                        message_parts.append(f"• {email}")
                
                message_parts.append("")
            
            # Create the message
            Message.objects.create(
                channel=channel,  # Message requires channel
                conversation=conversation,
                content="\n".join(message_parts),
                direction=MessageDirection.OUTBOUND,  # System-generated message
                status=MessageStatus.SENT,
                sent_at=timezone.now(),
                metadata={
                    'message_type': 'event_created',
                    'sender_type': 'system',
                    'event_data': {
                        'title': data['title'],
                        'event_type': data.get('event_type', 'meeting'),
                        'start_time': start_time.isoformat(),
                        'end_time': end_time.isoformat(),
                        'location': data.get('location', ''),
                        'location_type': data.get('location_type', 'other'),
                        'description': data.get('description', ''),
                        'attendees': attendees,
                        'organizer': {
                            'id': user.id,
                            'email': user.email,
                            'name': user.get_full_name() or user.username
                        }
                    },
                    'created_by': user.id
                }
            )
            
            # Step 6: Add to calendar if requested (following scheduling pattern)
            calendar_event_id = None
            if data.get('add_to_calendar', True) and profile and profile.calendar_connection:
                try:
                    # Create calendar event via UniPile (same as scheduling)
                    calendar_event_id = async_to_sync(self._create_calendar_event)(
                        profile.calendar_connection.unipile_account_id,
                        data['title'],
                        start_time,
                        end_time,
                        data.get('description', ''),
                        data.get('location', ''),
                        attendees,
                        data.get('location_type')
                    )
                    
                    if calendar_event_id:
                        # Update conversation with calendar event ID
                        conversation.metadata['calendar_event_id'] = calendar_event_id
                        conversation.metadata['unipile_event_id'] = calendar_event_id
                        conversation.save()
                        
                        # Update message with calendar event ID
                        Message.objects.filter(
                            conversation=conversation,
                            metadata__message_type='event_created'
                        ).update(
                            metadata={
                                **Message.objects.filter(
                                    conversation=conversation,
                                    metadata__message_type='event_created'
                                ).first().metadata,
                                'calendar_event_id': calendar_event_id
                            }
                        )
                        
                        logger.info(f"Created calendar event {calendar_event_id} for custom event")
                    else:
                        logger.warning("Calendar event creation returned no ID")
                        
                except Exception as e:
                    logger.error(f"Failed to create calendar event: {e}")
                    # Don't fail the whole request if calendar creation fails
            elif not profile or not profile.calendar_connection:
                logger.info("User has no calendar connection, event created without calendar sync")
            
            return Response({
                'success': True,
                'conversation_id': str(conversation.id),
                'calendar_event_id': calendar_event_id,
                'message': f'Event "{data["title"]}" created successfully'
            })
            
        except Exception as e:
            logger.error(f"Failed to create custom event: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    async def _create_calendar_event(self, account_id, title, start_time, end_time, description, location, attendees, location_type):
        """Create calendar event via UniPile (aligned with scheduling pattern)"""
        try:
            # Initialize UniPile client (same as scheduling)
            from django.db import connection
            tenant = connection.tenant
            
            if hasattr(tenant, 'unipile_config') and tenant.unipile_config.is_configured():
                client = UnipileClient(tenant.unipile_config.dsn, tenant.unipile_config.get_access_token())
            else:
                if not hasattr(settings, 'UNIPILE_DSN'):
                    logger.warning("UniPile not configured")
                    return None
                client = UnipileClient(settings.UNIPILE_DSN, settings.UNIPILE_API_KEY)
            
            calendar_client = UnipileCalendarClient(client)
            
            # Get primary calendar (same as scheduling)
            calendars_response = await calendar_client.get_calendars(account_id)
            if not calendars_response or 'data' not in calendars_response:
                logger.error("Failed to get calendars")
                return None
            
            primary_calendar = None
            for calendar in calendars_response['data']:
                if calendar.get('is_primary'):
                    primary_calendar = calendar['id']
                    break
            
            if not primary_calendar and calendars_response['data']:
                primary_calendar = calendars_response['data'][0]['id']
            
            if not primary_calendar:
                logger.error("No calendar found")
                return None
            
            # Determine conference provider if needed (same as scheduling)
            conference_provider = None
            if location_type == 'google_meet' and not location:
                conference_provider = 'google_meet'
            elif location_type == 'teams' and not location:
                conference_provider = 'teams'
            elif location_type == 'zoom' and not location:
                conference_provider = 'zoom'
            
            # Format attendees similar to scheduling
            formatted_attendees = []
            if attendees:
                for email in attendees:
                    if email:
                        formatted_attendees.append({
                            'email': email,
                            'displayName': email.split('@')[0],
                            'responseStatus': 'needsAction'
                        })
            
            # Create the event (aligned with scheduling pattern)
            event_response = await calendar_client.create_event(
                account_id=account_id,
                calendar_id=primary_calendar,
                title=title,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                description=description or '',
                location=location or '',
                attendees=formatted_attendees if formatted_attendees else None,
                conference_provider=conference_provider
            )
            
            if event_response:
                event_id = event_response.get('id') or event_response.get('event_id')
                if not event_id and 'data' in event_response:
                    event_data = event_response['data']
                    if isinstance(event_data, dict):
                        event_id = event_data.get('id') or event_data.get('event_id')
                
                return event_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return None