"""
UniPile LinkedIn Client
Handles advanced LinkedIn operations including job postings, search, connections, and analytics
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class UnipileLinkedInClient:
    """LinkedIn-specific UniPile client for advanced LinkedIn features"""
    
    def __init__(self, client):
        self.client = client
    
    # Job Posting Management
    async def create_job_posting(
        self, 
        account_id: str,
        job_title: str,
        company_name: str,
        location: str,
        description: str,
        requirements: str,
        employment_type: str = "FULL_TIME",
        experience_level: str = "MID_LEVEL",
        salary_range: Optional[Dict] = None,
        skills: Optional[List[str]] = None,
        apply_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new job posting on LinkedIn"""
        try:
            data = {
                'account_id': account_id,
                'job_title': job_title,
                'company_name': company_name,
                'location': location,
                'description': description,
                'requirements': requirements,
                'employment_type': employment_type,  # FULL_TIME, PART_TIME, CONTRACT, INTERNSHIP
                'experience_level': experience_level,  # ENTRY_LEVEL, MID_LEVEL, SENIOR_LEVEL, DIRECTOR, EXECUTIVE
            }
            
            if salary_range:
                data['salary_range'] = salary_range
            if skills:
                data['skills'] = skills
            if apply_url:
                data['apply_url'] = apply_url
                
            response = await self.client._make_request('POST', 'linkedin/jobs', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to create job posting: {e}")
            raise
    
    async def get_job_postings(
        self, 
        account_id: str,
        status: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get job postings for account"""
        try:
            params = {
                'account_id': account_id,
                'limit': limit
            }
            if status:
                params['status'] = status  # ACTIVE, PAUSED, CLOSED, DRAFT
            if cursor:
                params['cursor'] = cursor
                
            response = await self.client._make_request('GET', 'linkedin/jobs', params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to get job postings: {e}")
            raise
    
    # People Search
    async def search_people(
        self, 
        account_id: str,
        keywords: Optional[str] = None,
        location: Optional[str] = None,
        company: Optional[str] = None,
        industry: Optional[str] = None,
        current_position: Optional[str] = None,
        connection_degree: Optional[str] = None,
        limit: int = 25
    ) -> Dict[str, Any]:
        """Search for people on LinkedIn"""
        try:
            params = {
                'account_id': account_id,
                'limit': limit
            }
            
            if keywords:
                params['keywords'] = keywords
            if location:
                params['location'] = location
            if company:
                params['company'] = company
            if industry:
                params['industry'] = industry
            if current_position:
                params['current_position'] = current_position
            if connection_degree:
                params['connection_degree'] = connection_degree  # 1ST, 2ND, 3RD_PLUS
                
            response = await self.client._make_request('GET', 'linkedin/search/people', params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to search people: {e}")
            raise
    
    # Connection Management
    async def send_connection_request(
        self, 
        account_id: str,
        profile_id: str,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send connection request to LinkedIn profile"""
        try:
            data = {
                'account_id': account_id,
                'profile_id': profile_id
            }
            if message:
                data['message'] = message
                
            response = await self.client._make_request('POST', 'linkedin/connections/invite', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to send connection request to {profile_id}: {e}")
            raise
    
    async def get_connections(
        self, 
        account_id: str,
        limit: int = 50,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get LinkedIn connections"""
        try:
            params = {
                'account_id': account_id,
                'limit': limit
            }
            if cursor:
                params['cursor'] = cursor
                
            response = await self.client._make_request('GET', 'linkedin/connections', params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to get connections: {e}")
            raise
    
    # InMail Management
    async def send_inmail(
        self, 
        account_id: str,
        recipient_profile_id: str,
        subject: str,
        message: str
    ) -> Dict[str, Any]:
        """Send InMail message to LinkedIn profile"""
        try:
            data = {
                'account_id': account_id,
                'recipient_profile_id': recipient_profile_id,
                'subject': subject,
                'message': message
            }
            response = await self.client._make_request('POST', 'linkedin/inmail/send', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to send InMail to {recipient_profile_id}: {e}")
            raise
    
    # Content and Posts
    async def create_post(
        self, 
        account_id: str,
        content: str,
        visibility: str = "PUBLIC",
        attachments: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Create a LinkedIn post"""
        try:
            data = {
                'account_id': account_id,
                'content': content,
                'visibility': visibility  # PUBLIC, CONNECTIONS, LOGGED_IN
            }
            if attachments:
                data['attachments'] = attachments
                
            response = await self.client._make_request('POST', 'linkedin/posts', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to create post: {e}")
            raise