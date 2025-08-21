"""
UniPile Calendar Client
Handles calendar operations including event management and scheduling
"""
import logging
from typing import Dict, List, Any, Optional

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
        calendar_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get calendar events"""
        try:
            params = {
                'account_id': account_id,
                'limit': limit
            }
            if calendar_id:
                params['calendar_id'] = calendar_id
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
                
            response = await self.client._make_request('GET', 'events', params=params)
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
        reminder_minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create calendar event"""
        try:
            data = {
                'account_id': account_id,
                'calendar_id': calendar_id,
                'title': title,
                'start_time': start_time,
                'end_time': end_time
            }
            if description:
                data['description'] = description
            if location:
                data['location'] = location
            if attendees:
                data['attendees'] = attendees
            if reminder_minutes:
                data['reminder_minutes'] = reminder_minutes
                
            response = await self.client._make_request('POST', 'events', data=data)
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