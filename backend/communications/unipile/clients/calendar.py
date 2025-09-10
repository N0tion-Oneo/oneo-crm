"""
UniPile Calendar Client
Handles calendar operations including event management and scheduling
Extended with availability checking for meeting scheduling
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class UnipileCalendarClient:
    """Calendar-specific UniPile client for calendar integration"""
    
    def __init__(self, client):
        self.client = client
    
    async def get_calendars(self, account_id: str) -> Dict[str, Any]:
        """Get available calendars"""
        try:
            params = {'account_id': account_id}
            response = await self.client._make_request('GET', 'calendars', params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to get calendars: {e}")
            raise
    
    async def get_events(
        self, 
        account_id: str,
        calendar_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        expand_recurring: bool = True
    ) -> Dict[str, Any]:
        """Get calendar events from a specific calendar"""
        try:
            from urllib.parse import quote
            
            params = {
                'account_id': account_id,
            }
            # Don't include limit if we want all events in date range
            if start_date and end_date:
                params['start'] = start_date
                params['end'] = end_date
                # Add expand_recurring parameter when we have a date range
                if expand_recurring:
                    params['expand_recurring'] = 'true'
            else:
                params['limit'] = limit
                
            # URL encode the calendar_id for the path
            encoded_calendar_id = quote(calendar_id, safe='')
            endpoint = f'calendars/{encoded_calendar_id}/events'
            
            logger.info(f"UniPile API call - Endpoint: {endpoint}")
            logger.info(f"UniPile API call - Params: {params}")
            
            response = await self.client._make_request('GET', endpoint, params=params)
            
            # Log response details
            if isinstance(response, dict):
                logger.info(f"UniPile API response - Status: {response.get('status', 'unknown')}")
                if 'data' in response:
                    logger.info(f"UniPile API response - Event count: {len(response.get('data', []))}")
                if 'error' in response:
                    logger.error(f"UniPile API error: {response.get('error')}")
            
            return response
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            raise
    
    async def create_event(
        self, 
        account_id: str,
        calendar_id: str,
        title: str,
        start_time: str,
        end_time: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        is_all_day: bool = False,
        transparency: str = 'opaque',
        visibility: str = 'private'
    ) -> Dict[str, Any]:
        """Create calendar event"""
        try:
            # Prepare the request body according to UniPile format
            data = {
                'title': title,
                'start': {
                    'date_time': start_time,
                    'time_zone': 'UTC'  # You may want to make this configurable
                },
                'end': {
                    'date_time': end_time,
                    'time_zone': 'UTC'
                },
                'transparency': transparency,
                'visibility': visibility,
                'is_all_day': is_all_day
            }
            
            if description:
                data['body'] = description
            if location:
                data['location'] = location
            if attendees:
                data['attendees'] = [{'email': email} for email in attendees]
            
            # Use the correct endpoint with calendar_id in path
            endpoint = f'calendars/{calendar_id}/events'
            params = {'account_id': account_id}
            
            response = await self.client._make_request('POST', endpoint, data=data, params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            raise
    
    async def update_event(
        self, 
        account_id: str,
        event_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update calendar event"""
        try:
            data = {
                'account_id': account_id,
                **updates
            }
            response = await self.client._make_request('PUT', f'events/{event_id}', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to update event {event_id}: {e}")
            raise
    
    async def delete_event(self, account_id: str, event_id: str) -> Dict[str, Any]:
        """Delete calendar event"""
        try:
            data = {'account_id': account_id}
            response = await self.client._make_request('DELETE', f'events/{event_id}', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to delete event {event_id}: {e}")
            raise
    
    # ==========================================
    # Scheduling & Availability Methods
    # ==========================================
    
    async def check_availability(
        self,
        account_id: str,
        start_date: str,
        end_date: str,
        duration_minutes: int,
        calendar_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check calendar availability for a given time range
        Returns busy/free periods based on existing events
        """
        try:
            # Get all events in the date range
            events = await self.get_events(
                account_id=account_id,
                calendar_id=calendar_id,
                start_date=start_date,
                end_date=end_date,
                limit=200  # Get more events for availability checking
            )
            
            # Process events to find busy periods
            busy_periods = []
            for event in events.get('data', []):
                # Skip all-day events for now (could be configurable)
                if event.get('is_all_day'):
                    continue
                
                start = event.get('start', {})
                end = event.get('end', {})
                
                if start.get('date_time') and end.get('date_time'):
                    busy_periods.append({
                        'start': start['date_time'],
                        'end': end['date_time'],
                        'title': event.get('title', 'Busy')
                    })
            
            return {
                'busy_periods': busy_periods,
                'duration_minutes': duration_minutes,
                'date_range': {
                    'start': start_date,
                    'end': end_date
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to check availability: {e}")
            raise
    
    async def find_free_slots(
        self,
        account_id: str,
        date_range: Tuple[str, str],
        duration_minutes: int,
        working_hours: Dict[str, List[Dict[str, str]]],
        calendar_id: Optional[str] = None,
        buffer_minutes: int = 0,
        timezone_str: str = 'UTC'
    ) -> List[Dict[str, Any]]:
        """
        Find available time slots within working hours
        
        Args:
            account_id: UniPile account ID
            date_range: Tuple of (start_date, end_date) in ISO format
            duration_minutes: Duration of the meeting in minutes
            working_hours: Dict of day names to list of time ranges
                          e.g., {"monday": [{"start": "09:00", "end": "17:00"}]}
            calendar_id: Optional specific calendar ID
            buffer_minutes: Buffer time between meetings
            timezone_str: Timezone for the working hours
            
        Returns:
            List of available time slots
        """
        try:
            start_date, end_date = date_range
            
            # Get busy periods from calendar
            availability = await self.check_availability(
                account_id=account_id,
                start_date=start_date,
                end_date=end_date,
                duration_minutes=duration_minutes,
                calendar_id=calendar_id
            )
            
            busy_periods = availability['busy_periods']
            
            # Convert busy periods to datetime objects for easier comparison
            busy_times = []
            for period in busy_periods:
                try:
                    start_dt = datetime.fromisoformat(period['start'].replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(period['end'].replace('Z', '+00:00'))
                    # Add buffer time
                    if buffer_minutes > 0:
                        start_dt -= timedelta(minutes=buffer_minutes)
                        end_dt += timedelta(minutes=buffer_minutes)
                    busy_times.append((start_dt, end_dt))
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping invalid busy period: {e}")
                    continue
            
            # Generate available slots based on working hours
            available_slots = []
            current_date = datetime.fromisoformat(start_date.replace('Z', '+00:00')).date()
            end_date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00')).date()
            
            while current_date <= end_date_obj:
                # Get working hours for this day
                day_name = current_date.strftime('%A').lower()
                day_hours = working_hours.get(day_name, [])
                
                for time_range in day_hours:
                    start_time = datetime.strptime(time_range['start'], '%H:%M').time()
                    end_time = datetime.strptime(time_range['end'], '%H:%M').time()
                    
                    # Create datetime objects for the working period
                    work_start = datetime.combine(current_date, start_time).replace(tzinfo=timezone.utc)
                    work_end = datetime.combine(current_date, end_time).replace(tzinfo=timezone.utc)
                    
                    # Generate slots within working hours
                    slot_start = work_start
                    while slot_start + timedelta(minutes=duration_minutes) <= work_end:
                        slot_end = slot_start + timedelta(minutes=duration_minutes)
                        
                        # Check if slot conflicts with any busy period
                        is_available = True
                        for busy_start, busy_end in busy_times:
                            # Check for overlap
                            if not (slot_end <= busy_start or slot_start >= busy_end):
                                is_available = False
                                break
                        
                        if is_available:
                            available_slots.append({
                                'start': slot_start.isoformat(),
                                'end': slot_end.isoformat(),
                                'duration_minutes': duration_minutes
                            })
                        
                        # Move to next potential slot
                        slot_start += timedelta(minutes=30)  # 30-minute increments
                
                # Move to next day
                current_date += timedelta(days=1)
            
            return available_slots
            
        except Exception as e:
            logger.error(f"Failed to find free slots: {e}")
            raise
    
    async def create_meeting_event(
        self,
        account_id: str,
        calendar_id: str,
        meeting_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a calendar event specifically for a meeting
        Includes meeting URL, attendees, and reminders
        """
        try:
            # Extract meeting details
            title = meeting_details.get('title', 'Meeting')
            start_time = meeting_details['start_time']
            end_time = meeting_details['end_time']
            attendees = meeting_details.get('attendees', [])
            description = meeting_details.get('description', '')
            location = meeting_details.get('location', '')
            meeting_url = meeting_details.get('meeting_url', '')
            
            # Add meeting URL to description if provided
            if meeting_url:
                description = f"{description}\n\nJoin meeting: {meeting_url}"
            
            # Format attendees for UniPile
            formatted_attendees = []
            for attendee in attendees:
                if isinstance(attendee, str):
                    formatted_attendees.append({'email': attendee})
                else:
                    formatted_attendees.append(attendee)
            
            # Create the event
            data = {
                'account_id': account_id,
                'calendar_id': calendar_id,
                'title': title,
                'body': description,
                'location': location or meeting_url,
                'start': {
                    'date_time': start_time,
                    'time_zone': meeting_details.get('timezone', 'UTC')
                },
                'end': {
                    'date_time': end_time,
                    'time_zone': meeting_details.get('timezone', 'UTC')
                },
                'attendees': formatted_attendees,
                'transparency': 'opaque',  # Mark as busy
                'visibility': 'private'
            }
            
            # Add conference details if provided
            conference_provider = meeting_details.get('conference_provider')
            if conference_provider:
                data['conference'] = {
                    'provider': conference_provider,
                    'url': meeting_url
                }
            
            # Create the event
            endpoint = f'calendars/{calendar_id}/events'
            response = await self.client._make_request('POST', endpoint, data=data)
            return response
            
        except Exception as e:
            logger.error(f"Failed to create meeting event: {e}")
            raise
    
    async def update_meeting_event(
        self,
        account_id: str,
        event_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a meeting event with new details
        Handles rescheduling, attendee changes, etc.
        """
        try:
            # Format the update data
            data = {'account_id': account_id}
            
            # Handle time updates
            if 'start_time' in updates:
                data['start'] = {
                    'date_time': updates['start_time'],
                    'time_zone': updates.get('timezone', 'UTC')
                }
            
            if 'end_time' in updates:
                data['end'] = {
                    'date_time': updates['end_time'],
                    'time_zone': updates.get('timezone', 'UTC')
                }
            
            # Handle other updates
            if 'title' in updates:
                data['title'] = updates['title']
            
            if 'description' in updates:
                data['body'] = updates['description']
            
            if 'location' in updates:
                data['location'] = updates['location']
            
            if 'attendees' in updates:
                formatted_attendees = []
                for attendee in updates['attendees']:
                    if isinstance(attendee, str):
                        formatted_attendees.append({'email': attendee})
                    else:
                        formatted_attendees.append(attendee)
                data['attendees'] = formatted_attendees
            
            # Update the event
            response = await self.client._make_request('PUT', f'events/{event_id}', data=data)
            return response
            
        except Exception as e:
            logger.error(f"Failed to update meeting event {event_id}: {e}")
            raise
    
    async def get_calendar_for_scheduling(
        self,
        account_id: str
    ) -> Optional[str]:
        """
        Get the primary calendar ID for scheduling
        Returns the default calendar or the first available one
        """
        try:
            calendars = await self.get_calendars(account_id)
            
            # Look for the default calendar
            for calendar in calendars.get('data', []):
                if calendar.get('is_default'):
                    return calendar['id']
            
            # If no default, return the first owned calendar
            for calendar in calendars.get('data', []):
                if calendar.get('is_owned_by_user') and not calendar.get('is_read_only'):
                    return calendar['id']
            
            # Last resort: return any writable calendar
            for calendar in calendars.get('data', []):
                if not calendar.get('is_read_only'):
                    return calendar['id']
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get calendar for scheduling: {e}")
            return None