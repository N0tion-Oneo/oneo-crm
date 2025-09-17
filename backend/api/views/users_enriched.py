"""
Enriched user ViewSet for workflow user selection
Provides user data with all related information including:
- Staff profiles
- Channel connections (UniPile accounts)
- Scheduling profiles
- Meeting types
"""

from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Prefetch
from authentication.serializers import UserEnrichedSerializer
from communications.models import UserChannelConnection, ChannelType

User = get_user_model()


class UserEnrichedViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for enriched user data used in workflow configurations.
    Provides comprehensive user information including connected accounts,
    staff profiles, and scheduling data.
    """

    serializer_class = UserEnrichedSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering_fields = ['email', 'username', 'last_activity']
    ordering = ['email']

    def get_queryset(self):
        """
        Get users with all related data prefetched for performance.
        """
        queryset = User.objects.filter(
            is_active=True
        ).select_related(
            'user_type',
            'staff_profile',
            'staff_profile__reporting_manager'
        ).prefetch_related(
            'channel_connections',
            'scheduling_profiles',
            'meeting_types'
        )

        # Filter by channel if specified
        channel_filter = self.request.query_params.get('channel_filter')
        if channel_filter:
            # Map channel filter to actual channel types
            channel_map = {
                'email': [ChannelType.GOOGLE, ChannelType.OUTLOOK, ChannelType.MAIL],
                'linkedin': [ChannelType.LINKEDIN],
                'whatsapp': [ChannelType.WHATSAPP],
                'instagram': [ChannelType.INSTAGRAM],
                'messenger': [ChannelType.MESSENGER],
                'telegram': [ChannelType.TELEGRAM],
                'twitter': [ChannelType.TWITTER],
            }

            channel_types = channel_map.get(channel_filter.lower(), [])
            if channel_types:
                # Filter to users who have active connections for specified channel
                queryset = queryset.filter(
                    channel_connections__channel_type__in=channel_types,
                    channel_connections__is_active=True,
                    channel_connections__account_status='active'
                ).distinct()

        # Filter by having any channel connections
        has_connections = self.request.query_params.get('has_connections')
        if has_connections == 'true':
            queryset = queryset.filter(
                channel_connections__is_active=True,
                channel_connections__account_status='active'
            ).distinct()

        return queryset

    @action(detail=False, methods=['get'])
    def by_channel(self, request):
        """
        Get users grouped by their channel connections.
        Useful for trigger configuration where you want to see who has which channels.
        """
        channel_type = request.query_params.get('channel_type')

        if not channel_type:
            return Response({
                'error': 'channel_type parameter is required'
            }, status=400)

        # Map channel filter to actual channel types
        channel_map = {
            'email': [ChannelType.GOOGLE, ChannelType.OUTLOOK, ChannelType.MAIL],
            'linkedin': [ChannelType.LINKEDIN],
            'whatsapp': [ChannelType.WHATSAPP],
            'instagram': [ChannelType.INSTAGRAM],
            'messenger': [ChannelType.MESSENGER],
            'telegram': [ChannelType.TELEGRAM],
            'twitter': [ChannelType.TWITTER],
        }

        channel_types = channel_map.get(channel_type.lower())
        if not channel_types:
            return Response({
                'error': f'Invalid channel_type: {channel_type}'
            }, status=400)

        # Get users with active connections for this channel
        users = User.objects.filter(
            channel_connections__channel_type__in=channel_types,
            channel_connections__is_active=True,
            channel_connections__account_status='active',
            is_active=True
        ).distinct().select_related(
            'user_type',
            'staff_profile'
        ).prefetch_related(
            Prefetch(
                'channel_connections',
                queryset=UserChannelConnection.objects.filter(
                    channel_type__in=channel_types,
                    is_active=True,
                    account_status='active'
                )
            )
        )

        serializer = self.get_serializer(users, many=True)

        # Format response with channel-specific information
        formatted_users = []
        for user_data in serializer.data:
            # Get relevant channel connections
            channel_connections = user_data.get('channel_connections', {})
            relevant_connections = []

            for ct in channel_types:
                if ct in channel_connections:
                    relevant_connections.extend(channel_connections[ct])

            if relevant_connections:
                formatted_users.append({
                    'id': user_data['id'],
                    'email': user_data['email'],
                    'full_name': user_data['full_name'],
                    'staff_profile': user_data.get('staff_profile'),
                    'connections': relevant_connections,
                    'primary_account': user_data.get('primary_email_account')
                })

        return Response({
            'channel_type': channel_type,
            'total_users': len(formatted_users),
            'users': formatted_users
        })

    @action(detail=True, methods=['get'])
    def workflow_variables(self, request, pk=None):
        """
        Get available workflow variables for a specific user.
        Returns the paths that can be used in workflow templates.
        """
        user = self.get_object()

        variables = {
            'user': {
                'id': '{{user.id}}',
                'email': '{{user.email}}',
                'username': '{{user.username}}',
                'full_name': '{{user.full_name}}',
                'phone': '{{user.phone}}',
                'user_type': '{{user.user_type_name}}',
            }
        }

        # Add staff profile variables if exists
        if hasattr(user, 'staff_profile') and user.staff_profile:
            variables['staff_profile'] = {
                'job_title': '{{user.staff_profile.job_title}}',
                'department': '{{user.staff_profile.department}}',
                'employee_id': '{{user.staff_profile.employee_id}}',
                'work_location': '{{user.staff_profile.work_location}}',
                'office_location': '{{user.staff_profile.office_location}}',
                'reporting_manager': '{{user.staff_profile.reporting_manager_name}}',
            }

        # Add channel connection variables
        channel_connections = UserChannelConnection.objects.filter(
            user=user,
            is_active=True
        )

        if channel_connections.exists():
            variables['channel_connections'] = {}
            for conn in channel_connections:
                channel_key = conn.channel_type.lower()
                if channel_key not in variables['channel_connections']:
                    variables['channel_connections'][channel_key] = []

                variables['channel_connections'][channel_key].append({
                    'account_name': f'{{{{user.channel_connections.{channel_key}[{len(variables["channel_connections"][channel_key])}].account_name}}}}',
                    'account_id': f'{{{{user.channel_connections.{channel_key}[{len(variables["channel_connections"][channel_key])}].account_id}}}}',
                })

        # Add scheduling variables
        if user.scheduling_profiles.exists():
            variables['scheduling'] = {
                'timezone': '{{user.scheduling_profiles[0].timezone}}',
                'buffer_minutes': '{{user.scheduling_profiles[0].buffer_minutes}}',
                'booking_link': '{{user.scheduling_profiles[0].booking_link}}',
            }

        # Add meeting type variables
        if user.meeting_types.filter(is_active=True).exists():
            variables['meeting_types'] = []
            for idx, meeting_type in enumerate(user.meeting_types.filter(is_active=True)[:3]):
                variables['meeting_types'].append({
                    'name': f'{{{{user.meeting_types[{idx}].name}}}}',
                    'booking_url': f'{{{{user.meeting_types[{idx}].booking_url}}}}',
                    'duration': f'{{{{user.meeting_types[{idx}].duration_minutes}}}}',
                })

        return Response({
            'user_id': user.id,
            'user_email': user.email,
            'variables': variables
        })