"""
Record-level Channel Availability Tracking Service
Tracks which communication channels are available for each Record and their status
"""
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from django.db.models import Q, Count, Max, Min, Exists, OuterRef
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth import get_user_model

from communications.models import (
    Message, Conversation, UserChannelConnection, ChannelType, MessageDirection
)
from pipelines.models import Record, Field
from communications.unipile_sdk import unipile_service

logger = logging.getLogger(__name__)
User = get_user_model()


class RecordChannelAvailabilityTracker:
    """Tracks channel availability and status for Records"""
    
    def __init__(self, user: User):
        self.user = user
        self.logger = logger
        self.cache_ttl = 300  # 5 minutes cache
        
        # Channel priority for smart selection
        self.channel_priority = {
            ChannelType.WHATSAPP: 1,
            ChannelType.LINKEDIN: 2,
            ChannelType.GOOGLE: 3,
            ChannelType.OUTLOOK: 3,
            ChannelType.MAIL: 3,
            ChannelType.INSTAGRAM: 4,
            ChannelType.MESSENGER: 4,
            ChannelType.TELEGRAM: 5,
            ChannelType.TWITTER: 6
        }
    
    def get_record_channel_availability(self, record: Record, refresh_cache: bool = False) -> Dict[str, Any]:
        """
        Get comprehensive channel availability for a Record
        
        Args:
            record: The Record to analyze
            refresh_cache: Whether to bypass cache and refresh data
            
        Returns:
            Dict containing channel availability information
        """
        try:
            cache_key = f"record_channel_availability_{record.id}_{self.user.id}"
            
            if not refresh_cache:
                cached_result = cache.get(cache_key)
                if cached_result:
                    return cached_result
            
            # Analyze Record contact information
            contact_info = self._extract_record_contact_info(record)
            
            # Get user's connected channels
            user_channels = self._get_user_connected_channels()
            
            # Analyze existing communication history
            communication_history = self._analyze_communication_history(record)
            
            # Determine channel availability
            channel_availability = self._determine_channel_availability(
                record, contact_info, user_channels, communication_history
            )
            
            # Add smart recommendations
            recommendations = self._generate_channel_recommendations(
                record, channel_availability, communication_history
            )
            
            result = {
                'record_id': record.id,
                'record_title': record.title,
                'last_updated': timezone.now(),
                'contact_info': contact_info,
                'available_channels': channel_availability,
                'recommendations': recommendations,
                'summary': {
                    'total_available_channels': len([ch for ch in channel_availability if ch['status'] == 'available']),
                    'total_connected_channels': len([ch for ch in channel_availability if ch['user_connected']]),
                    'primary_channel': recommendations.get('primary_channel'),
                    'communication_score': self._calculate_communication_score(channel_availability)
                }
            }
            
            # Cache the result
            cache.set(cache_key, result, self.cache_ttl)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting channel availability for record {record.id}: {e}")
            return {
                'record_id': record.id,
                'error': str(e),
                'available_channels': [],
                'recommendations': {}
            }
    
    def _extract_record_contact_info(self, record: Record) -> Dict[str, Any]:
        """Extract contact information from Record data"""
        contact_info = {
            'emails': [],
            'phones': [],
            'linkedin_urls': [],
            'social_handles': {},
            'websites': [],
            'inferred_channels': set()
        }
        
        if not record.data:
            return contact_info
        
        # Extract from Record fields
        for field_name, field_value in record.data.items():
            if not field_value:
                continue
            
            field_name_lower = field_name.lower()
            field_value_str = str(field_value).strip()
            
            # Email detection
            if any(keyword in field_name_lower for keyword in ['email', 'mail']) or '@' in field_value_str:
                if '@' in field_value_str and '.' in field_value_str:
                    contact_info['emails'].append({
                        'value': field_value_str,
                        'field_name': field_name,
                        'verified': False
                    })
                    contact_info['inferred_channels'].add('email')
            
            # Phone detection
            elif any(keyword in field_name_lower for keyword in ['phone', 'mobile', 'tel', 'whatsapp']):
                # Clean phone number
                clean_phone = ''.join(filter(str.isdigit, field_value_str))
                if len(clean_phone) >= 7:
                    contact_info['phones'].append({
                        'value': clean_phone,
                        'original': field_value_str,
                        'field_name': field_name,
                        'verified': False
                    })
                    if 'whatsapp' in field_name_lower:
                        contact_info['inferred_channels'].add('whatsapp')
                    else:
                        contact_info['inferred_channels'].add('phone')
            
            # LinkedIn detection
            elif 'linkedin' in field_name_lower or 'linkedin.com' in field_value_str:
                contact_info['linkedin_urls'].append({
                    'value': field_value_str,
                    'field_name': field_name,
                    'verified': False
                })
                contact_info['inferred_channels'].add('linkedin')
            
            # Social media detection
            elif any(platform in field_name_lower for platform in ['instagram', 'twitter', 'facebook', 'telegram']):
                for platform in ['instagram', 'twitter', 'facebook', 'telegram']:
                    if platform in field_name_lower:
                        if platform not in contact_info['social_handles']:
                            contact_info['social_handles'][platform] = []
                        contact_info['social_handles'][platform].append({
                            'value': field_value_str,
                            'field_name': field_name,
                            'verified': False
                        })
                        contact_info['inferred_channels'].add(platform)
            
            # Website detection
            elif any(keyword in field_name_lower for keyword in ['website', 'url', 'domain']) or field_value_str.startswith(('http', 'www')):
                contact_info['websites'].append({
                    'value': field_value_str,
                    'field_name': field_name,
                    'verified': False
                })
        
        # Convert set to list for JSON serialization
        contact_info['inferred_channels'] = list(contact_info['inferred_channels'])
        
        return contact_info
    
    def _get_user_connected_channels(self) -> List[Dict[str, Any]]:
        """Get user's connected communication channels"""
        connections = UserChannelConnection.objects.filter(
            user=self.user,
            is_active=True
        ).order_by('channel_type', '-created_at')
        
        user_channels = []
        for connection in connections:
            status_info = connection.get_status_display_info()
            
            user_channels.append({
                'id': str(connection.id),
                'type': connection.channel_type,
                'name': connection.get_channel_type_display(),
                'account_name': connection.account_name,
                'status': connection.account_status,
                'can_send': status_info['can_send'],
                'needs_action': status_info['needs_action'],
                'action_type': status_info.get('action_type'),
                'last_sync': connection.last_sync_at,
                'unipile_account_id': connection.unipile_account_id,
                'connection_config': connection.connection_config or {},
                'created_at': connection.created_at
            })
        
        return user_channels
    
    def _analyze_communication_history(self, record: Record) -> Dict[str, Any]:
        """Analyze existing communication history for the Record"""
        history = {
            'total_messages': 0,
            'channels_used': {},
            'first_contact': None,
            'last_contact': None,
            'preferred_channel': None,
            'response_patterns': {},
            'engagement_score': 0.0
        }
        
        # Get all messages for this Record
        messages = Message.objects.filter(
            Q(contact_record=record) |
            Q(conversation__primary_contact_record=record)
        ).select_related('channel', 'conversation__channel').order_by('created_at')
        
        if not messages.exists():
            return history
        
        history['total_messages'] = messages.count()
        history['first_contact'] = messages.first().created_at
        history['last_contact'] = messages.last().created_at
        
        # Analyze by channel
        channel_stats = {}
        for message in messages:
            channel = message.channel or (message.conversation.channel if message.conversation else None)
            if not channel:
                continue
            
            channel_type = channel.channel_type
            if channel_type not in channel_stats:
                channel_stats[channel_type] = {
                    'total_messages': 0,
                    'inbound_messages': 0,
                    'outbound_messages': 0,
                    'last_message': None,
                    'response_rate': 0.0,
                    'avg_response_time': None
                }
            
            channel_stats[channel_type]['total_messages'] += 1
            
            if message.direction == MessageDirection.INBOUND:
                channel_stats[channel_type]['inbound_messages'] += 1
            else:
                channel_stats[channel_type]['outbound_messages'] += 1
            
            channel_stats[channel_type]['last_message'] = message.created_at
        
        # Calculate response rates and engagement scores
        for channel_type, stats in channel_stats.items():
            if stats['inbound_messages'] > 0:
                stats['response_rate'] = (stats['outbound_messages'] / stats['inbound_messages']) * 100
            
            # Simple engagement score based on message frequency and recency
            recency_factor = 1.0
            if stats['last_message']:
                days_since = (timezone.now() - stats['last_message']).days
                recency_factor = max(0.1, 1.0 - (days_since / 30))  # Decay over 30 days
            
            stats['engagement_score'] = stats['total_messages'] * recency_factor * (stats['response_rate'] / 100)
        
        history['channels_used'] = channel_stats
        
        # Determine preferred channel (highest engagement score)
        if channel_stats:
            preferred = max(channel_stats.items(), key=lambda x: x[1]['engagement_score'])
            history['preferred_channel'] = preferred[0]
            history['engagement_score'] = preferred[1]['engagement_score']
        
        return history
    
    def _determine_channel_availability(self, record: Record, contact_info: Dict[str, Any], 
                                      user_channels: List[Dict[str, Any]], 
                                      communication_history: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Determine which channels are available for communication with the Record"""
        
        # Create mapping of user connected channels by type
        user_channels_by_type = {}
        for channel in user_channels:
            channel_type = channel['type']
            if channel_type not in user_channels_by_type:
                user_channels_by_type[channel_type] = []
            user_channels_by_type[channel_type].append(channel)
        
        availability = []
        
        # Check each possible channel type
        for channel_choice in ChannelType.choices:
            channel_type = channel_choice[0]  # Get the value from (value, label) tuple
            channel_info = {
                'channel_type': channel_type,
                'display_name': channel_type.title(),
                'status': 'unavailable',
                'user_connected': channel_type in user_channels_by_type,
                'contact_info_available': False,
                'has_history': channel_type in communication_history.get('channels_used', {}),
                'priority': self.channel_priority.get(channel_type, 10),
                'connection_details': user_channels_by_type.get(channel_type, []),
                'contact_details': [],
                'availability_reasons': [],
                'limitations': []
            }
            
            # Check if contact information is available for this channel
            contact_available = False
            
            if channel_type in ['gmail', 'outlook', 'mail']:
                if contact_info['emails']:
                    contact_available = True
                    channel_info['contact_details'] = contact_info['emails']
            
            elif channel_type == 'whatsapp':
                if contact_info['phones']:
                    contact_available = True
                    channel_info['contact_details'] = contact_info['phones']
            
            elif channel_type == 'linkedin':
                if contact_info['linkedin_urls']:
                    contact_available = True
                    channel_info['contact_details'] = contact_info['linkedin_urls']
            
            elif channel_type in ['instagram', 'messenger', 'twitter', 'telegram']:
                if channel_type in contact_info['social_handles']:
                    contact_available = True
                    channel_info['contact_details'] = contact_info['social_handles'][channel_type]
            
            channel_info['contact_info_available'] = contact_available
            
            # Determine overall availability status
            if channel_info['user_connected'] and contact_available:
                # Check if user's connection can send messages
                active_connections = [
                    conn for conn in user_channels_by_type.get(channel_type, [])
                    if conn['can_send'] and not conn['needs_action']
                ]
                
                if active_connections:
                    channel_info['status'] = 'available'
                    channel_info['availability_reasons'].append('User connected and contact info available')
                else:
                    channel_info['status'] = 'limited'
                    channel_info['availability_reasons'].append('User connected but account needs attention')
                    channel_info['limitations'].append('Account connection issues')
            
            elif channel_info['user_connected'] and not contact_available:
                channel_info['status'] = 'limited'
                channel_info['availability_reasons'].append('User connected but no contact info')
                channel_info['limitations'].append('Missing contact information')
            
            elif not channel_info['user_connected'] and contact_available:
                channel_info['status'] = 'limited'
                channel_info['availability_reasons'].append('Contact info available but user not connected')
                channel_info['limitations'].append('User account not connected')
            
            elif channel_info['has_history']:
                channel_info['status'] = 'historical'
                channel_info['availability_reasons'].append('Previous communication history exists')
                if not channel_info['user_connected']:
                    channel_info['limitations'].append('User account not connected')
                if not contact_available:
                    channel_info['limitations'].append('Contact info not current')
            
            else:
                channel_info['status'] = 'unavailable'
                channel_info['availability_reasons'].append('No connection or contact information')
            
            # Add historical data if available
            if channel_info['has_history']:
                hist_data = communication_history['channels_used'][channel_type]
                channel_info['history'] = {
                    'total_messages': hist_data['total_messages'],
                    'last_contact': hist_data['last_message'],
                    'response_rate': hist_data['response_rate'],
                    'engagement_score': hist_data['engagement_score']
                }
            
            availability.append(channel_info)
        
        # Sort by priority and availability
        availability.sort(key=lambda x: (
            x['status'] != 'available',  # Available first
            x['status'] != 'limited',    # Limited second
            x['status'] != 'historical', # Historical third
            x['priority']                # Then by priority
        ))
        
        return availability
    
    def _generate_channel_recommendations(self, record: Record, availability: List[Dict[str, Any]], 
                                        history: Dict[str, Any]) -> Dict[str, Any]:
        """Generate smart channel recommendations for the Record"""
        
        recommendations = {
            'primary_channel': None,
            'alternative_channels': [],
            'setup_recommendations': [],
            'engagement_strategy': {},
            'reasoning': []
        }
        
        # Get available channels
        available_channels = [ch for ch in availability if ch['status'] == 'available']
        limited_channels = [ch for ch in availability if ch['status'] == 'limited']
        
        # Primary channel selection
        if available_channels:
            # Prefer channel with existing history and high engagement
            primary_candidate = None
            
            for channel in available_channels:
                score = 0
                
                # History bonus
                if channel['has_history']:
                    score += channel.get('history', {}).get('engagement_score', 0) * 10
                
                # Priority bonus (lower priority number = higher score)
                score += (10 - channel['priority']) * 2
                
                # Recent activity bonus
                if channel.get('history', {}).get('last_contact'):
                    last_contact = channel['history']['last_contact']
                    days_ago = (timezone.now() - last_contact).days
                    if days_ago <= 7:
                        score += 5
                    elif days_ago <= 30:
                        score += 2
                
                channel['recommendation_score'] = score
                
                if not primary_candidate or score > primary_candidate['recommendation_score']:
                    primary_candidate = channel
            
            if primary_candidate:
                recommendations['primary_channel'] = {
                    'channel_type': primary_candidate['channel_type'],
                    'display_name': primary_candidate['display_name'],
                    'score': primary_candidate['recommendation_score'],
                    'reason': self._get_primary_channel_reason(primary_candidate, history)
                }
                
                # Alternative channels (other available channels)
                alternatives = [ch for ch in available_channels if ch != primary_candidate]
                recommendations['alternative_channels'] = [
                    {
                        'channel_type': ch['channel_type'],
                        'display_name': ch['display_name'],
                        'reason': f"Alternative option with {ch['priority']} priority"
                    }
                    for ch in alternatives[:3]  # Top 3 alternatives
                ]
        
        # Setup recommendations for limited/unavailable channels
        for channel in limited_channels:
            if not channel['user_connected']:
                recommendations['setup_recommendations'].append({
                    'action': 'connect_account',
                    'channel_type': channel['channel_type'],
                    'display_name': channel['display_name'],
                    'priority': 'high' if channel['contact_info_available'] else 'medium',
                    'description': f"Connect your {channel['display_name']} account to enable messaging"
                })
            
            elif not channel['contact_info_available']:
                recommendations['setup_recommendations'].append({
                    'action': 'add_contact_info',
                    'channel_type': channel['channel_type'],
                    'display_name': channel['display_name'],
                    'priority': 'medium',
                    'description': f"Add {channel['display_name']} contact information for {record.title}"
                })
        
        # Engagement strategy
        if history['preferred_channel']:
            recommendations['engagement_strategy'] = {
                'preferred_channel': history['preferred_channel'],
                'best_response_rate': max(
                    (stats['response_rate'] for stats in history['channels_used'].values()),
                    default=0
                ),
                'suggested_approach': self._get_engagement_approach(history)
            }
        
        return recommendations
    
    def _get_primary_channel_reason(self, channel: Dict[str, Any], history: Dict[str, Any]) -> str:
        """Get reason for primary channel recommendation"""
        reasons = []
        
        if channel['has_history']:
            engagement = channel.get('history', {}).get('engagement_score', 0)
            if engagement > 5:
                reasons.append("high engagement history")
            elif engagement > 2:
                reasons.append("good engagement history")
            else:
                reasons.append("previous communication")
        
        if channel['priority'] <= 2:
            reasons.append("high priority channel")
        
        if not reasons:
            reasons.append("available and connected")
        
        return f"Recommended due to {', '.join(reasons)}"
    
    def _get_engagement_approach(self, history: Dict[str, Any]) -> str:
        """Get suggested engagement approach based on history"""
        if not history['channels_used']:
            return "Start with a friendly introduction"
        
        total_messages = history['total_messages']
        last_contact = history['last_contact']
        
        if last_contact:
            days_since = (timezone.now() - last_contact).days
            
            if days_since <= 7:
                return "Continue the recent conversation"
            elif days_since <= 30:
                return "Reference recent interaction and continue"
            elif days_since <= 90:
                return "Acknowledge the time gap and reconnect"
            else:
                return "Re-establish relationship with a friendly check-in"
        
        if total_messages > 10:
            return "Build on established relationship"
        else:
            return "Develop the relationship gradually"
    
    def _calculate_communication_score(self, availability: List[Dict[str, Any]]) -> float:
        """Calculate overall communication readiness score"""
        available_channels = [ch for ch in availability if ch['status'] == 'available']
        limited_channels = [ch for ch in availability if ch['status'] == 'limited']
        historical_channels = [ch for ch in availability if ch['status'] == 'historical']
        
        score = 0.0
        
        # Available channels contribute most
        score += len(available_channels) * 3.0
        
        # Limited channels contribute moderately
        score += len(limited_channels) * 1.5
        
        # Historical channels contribute minimally
        score += len(historical_channels) * 0.5
        
        # Bonus for high-priority channels
        for channel in available_channels:
            if channel['priority'] <= 2:
                score += 1.0
        
        # Normalize to 0-10 scale
        max_possible_score = len(ChannelType.choices) * 3.0 + 3.0  # Assume 3 high-priority
        normalized_score = (score / max_possible_score) * 10.0
        
        return min(10.0, normalized_score)
    
    def bulk_analyze_channel_availability(self, record_ids: List[int]) -> Dict[str, Any]:
        """Analyze channel availability for multiple Records in bulk"""
        try:
            results = {}
            failed_records = []
            
            records = Record.objects.filter(id__in=record_ids, is_deleted=False)
            
            for record in records:
                try:
                    availability = self.get_record_channel_availability(record)
                    results[str(record.id)] = availability
                except Exception as e:
                    failed_records.append({
                        'record_id': record.id,
                        'error': str(e)
                    })
                    self.logger.error(f"Error analyzing record {record.id}: {e}")
            
            return {
                'success': True,
                'total_records': len(record_ids),
                'successful_analyses': len(results),
                'failed_analyses': len(failed_records),
                'results': results,
                'failed_records': failed_records
            }
            
        except Exception as e:
            self.logger.error(f"Error in bulk channel availability analysis: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': {}
            }
    
    def invalidate_record_cache(self, record_id: int):
        """Invalidate cache for a specific Record"""
        cache_key = f"record_channel_availability_{record_id}_{self.user.id}"
        cache.delete(cache_key)
    
    def refresh_all_cache(self):
        """Refresh cache for all Records (use with caution)"""
        # This would be expensive - typically not recommended
        # Could implement with cache versioning instead
        pass


# Factory function for easy instantiation
def get_channel_availability_tracker(user: User) -> RecordChannelAvailabilityTracker:
    """Get a channel availability tracker for a user"""
    return RecordChannelAvailabilityTracker(user)