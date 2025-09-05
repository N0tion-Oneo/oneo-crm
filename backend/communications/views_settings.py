"""
ViewSets for Participant Settings Management
"""
import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from api.permissions import ParticipantSettingsPermission

from .models import (
    ParticipantSettings, ParticipantBlacklist, 
    ParticipantOverride, ChannelParticipantSettings
)
from .serializers import (
    ParticipantSettingsSerializer, ParticipantBlacklistSerializer,
    ParticipantOverrideSerializer, ChannelParticipantSettingsSerializer,
    BatchAutoCreateSerializer
)
from .services.auto_create_service import AutoCreateContactService

logger = logging.getLogger(__name__)


class ParticipantSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing participant auto-creation settings
    """
    
    queryset = ParticipantSettings.objects.all()
    serializer_class = ParticipantSettingsSerializer
    permission_classes = [ParticipantSettingsPermission]
    
    def get_object(self):
        """Get or create settings for current tenant"""
        return ParticipantSettings.get_or_create_for_tenant()
    
    def list(self, request, *args, **kwargs):
        """Return single settings object for tenant"""
        settings = self.get_object()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Process batch auto-creation",
        request=BatchAutoCreateSerializer,
        responses={200: {'type': 'object', 'properties': {
            'created': {'type': 'integer'},
            'skipped': {'type': 'integer'},
            'errors': {'type': 'integer'},
            'duplicates': {'type': 'integer'}
        }}}
    )
    @action(detail=False, methods=['post'])
    def process_batch(self, request):
        """Process batch of participants for auto-creation"""
        serializer = BatchAutoCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from django.db import connection as db_connection
            tenant = getattr(db_connection, 'tenant', None)
            
            service = AutoCreateContactService(tenant=tenant)
            
            batch_size = serializer.validated_data.get('batch_size')
            dry_run = serializer.validated_data.get('dry_run', False)
            
            if dry_run:
                # Just preview what would happen
                from .models import Participant, ParticipantOverride
                
                # Get all unlinked participants (no contact_record)
                unlinked_query = Participant.objects.filter(
                    contact_record__isnull=True
                )
                
                # Exclude those with never_auto_create override
                # Use left outer join to handle participants without override settings
                excluded_ids = ParticipantOverride.objects.filter(
                    never_auto_create=True
                ).values_list('participant_id', flat=True)
                
                eligible_query = unlinked_query.exclude(id__in=excluded_ids)
                
                # Get total count before slicing
                total_unlinked = eligible_query.count()
                
                # Check a batch for eligibility
                batch_to_check = eligible_query[:batch_size or 100]
                
                eligible_count = 0
                checked_count = 0
                reasons = {}
                contacts_would_create = 0
                companies_would_create = 0
                companies_would_link = 0
                domains_seen = set()  # Track domains to avoid counting same company multiple times
                
                for p in batch_to_check:
                    checked_count += 1
                    should_create, reason = service.should_auto_create(p)
                    if should_create:
                        eligible_count += 1
                        contacts_would_create += 1
                        
                        # Check if would create or link company
                        if service.settings.auto_link_by_domain and p.email and not p.secondary_record:
                            email_lower = p.email.lower()
                            if '@' in email_lower:  # Ensure it's a valid email
                                domain = email_lower.split('@')[-1]
                                
                                # Skip personal domains - use service's constant
                                if domain not in service.PERSONAL_EMAIL_DOMAINS and domain not in domains_seen:
                                    domains_seen.add(domain)  # Mark domain as seen
                                    
                                    # Check if company exists
                                    from communications.record_communications.services.identifier_extractor import RecordIdentifierExtractor
                                    extractor = RecordIdentifierExtractor()
                                    existing_companies = extractor.find_company_records_by_domain(
                                        domain=domain,
                                        pipeline_slugs=['companies', 'organizations', 'accounts']
                                    )
                                    
                                    if existing_companies:
                                        companies_would_link += 1
                                    elif service.settings.create_company_if_missing:
                                        # Check if enough participants for company creation
                                        from communications.models import Participant
                                        domain_participants = Participant.objects.filter(
                                            email__iendswith=f'@{domain}'
                                        ).count()
                                        
                                        if domain_participants >= service.settings.min_employees_for_company:
                                            companies_would_create += 1
                    else:
                        # Track rejection reasons
                        if reason not in reasons:
                            reasons[reason] = 0
                        reasons[reason] += 1
                
                result = {
                    'dry_run': True,
                    'eligible_count': eligible_count,
                    'total_checked': checked_count,
                    'total_unlinked': total_unlinked,
                    'contacts_would_create': contacts_would_create,
                    'companies_would_create': companies_would_create,
                    'companies_would_link': companies_would_link,
                    'rejection_reasons': reasons
                }
                logger.info(f"Dry run result: {result}")
                return Response(result)
            else:
                # Actually process
                results = service.process_batch(batch_size=batch_size, user=request.user)
                return Response(results)
                
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Get pipelines compatible for participant auto-creation",
        responses={200: {'type': 'array', 'items': {'type': 'object'}}}
    )
    @action(detail=False, methods=['get'])
    def compatible_pipelines(self, request):
        """Get pipelines that have duplicate detection rules using email or phone fields"""
        try:
            from pipelines.models import Pipeline, Field
            from pipelines.serializers import PipelineSerializer
            from duplicates.models import DuplicateRule
            import json
            
            def extract_fields_from_logic(logic):
                """Extract field slugs from duplicate rule logic"""
                fields = set()
                
                def traverse(node):
                    if isinstance(node, dict):
                        if 'field' in node:
                            fields.add(node['field'])
                        for value in node.values():
                            traverse(value)
                    elif isinstance(node, list):
                        for item in node:
                            traverse(item)
                
                traverse(logic)
                return fields
            
            # Find pipelines with duplicate rules that use email/phone fields
            result = []
            
            for pipeline in Pipeline.objects.all():
                # Get active duplicate rules for this pipeline
                rules = DuplicateRule.objects.filter(
                    pipeline=pipeline,
                    is_active=True
                )
                
                if not rules.exists():
                    continue  # Skip pipelines without duplicate rules
                
                # Check if any rules use email or phone fields
                email_fields_used = set()
                phone_fields_used = set()
                
                for rule in rules:
                    # Extract field slugs from rule logic
                    field_slugs = extract_fields_from_logic(rule.logic)
                    
                    # Check if these are email or phone fields
                    for slug in field_slugs:
                        field = Field.objects.filter(
                            pipeline=pipeline,
                            slug=slug,
                            is_deleted=False
                        ).first()
                        
                        if field:
                            if field.field_type == 'email':
                                email_fields_used.add(field.name)
                            elif field.field_type == 'phone':
                                phone_fields_used.add(field.name)
                
                # Only include if has email or phone fields in rules
                if email_fields_used or phone_fields_used:
                    pipeline_data = PipelineSerializer(pipeline).data
                    pipeline_data['email_fields'] = list(email_fields_used)
                    pipeline_data['phone_fields'] = list(phone_fields_used)
                    pipeline_data['is_compatible'] = True
                    pipeline_data['has_duplicate_rules'] = True
                    result.append(pipeline_data)
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"Error getting compatible pipelines: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Get pipelines compatible for company linking",
        responses={200: {'type': 'array'}}
    )
    @action(detail=False, methods=['get'])
    def company_pipelines(self, request):
        """Get pipelines that have duplicate detection rules using domain/URL fields"""
        try:
            from pipelines.models import Pipeline, Field
            from pipelines.serializers import PipelineSerializer
            from duplicates.models import DuplicateRule
            import json
            
            def extract_fields_from_logic(logic):
                """Extract field slugs from duplicate rule logic"""
                fields = set()
                
                def traverse(node):
                    if isinstance(node, dict):
                        if 'field' in node:
                            fields.add(node['field'])
                        for value in node.values():
                            traverse(value)
                    elif isinstance(node, list):
                        for item in node:
                            traverse(item)
                
                traverse(logic)
                return fields
            
            # Find pipelines with duplicate rules that use domain/URL fields
            result = []
            
            for pipeline in Pipeline.objects.all():
                # Get active duplicate rules for this pipeline
                rules = DuplicateRule.objects.filter(
                    pipeline=pipeline,
                    is_active=True
                )
                
                if not rules.exists():
                    continue  # Skip pipelines without duplicate rules
                
                # Check if any rules use domain or URL fields
                domain_fields_used = set()
                url_fields_used = set()
                
                for rule in rules:
                    # Extract field slugs from rule logic
                    field_slugs = extract_fields_from_logic(rule.logic)
                    
                    # Check if these are domain or URL fields
                    for slug in field_slugs:
                        field = Field.objects.filter(
                            pipeline=pipeline,
                            slug=slug,
                            is_deleted=False
                        ).first()
                        
                        if field:
                            field_name_lower = field.slug.lower()
                            # Check for domain fields
                            if any(x in field_name_lower for x in ['domain', 'website', 'company_domain']):
                                domain_fields_used.add(field.name)
                            # Check for URL fields
                            elif field.field_type == 'url' or any(x in field_name_lower for x in ['url', 'website', 'web']):
                                url_fields_used.add(field.name)
                
                # Only include if has domain or URL fields in rules
                if domain_fields_used or url_fields_used:
                    pipeline_data = PipelineSerializer(pipeline).data
                    pipeline_data['domain_fields'] = list(domain_fields_used)
                    pipeline_data['url_fields'] = list(url_fields_used)
                    pipeline_data['is_compatible'] = True
                    pipeline_data['has_duplicate_rules'] = True
                    result.append(pipeline_data)
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"Error getting company pipelines: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Get auto-creation statistics",
        responses={200: {'type': 'object', 'properties': {
            'auto_created': {'type': 'integer'},
            'blacklist_entries': {'type': 'integer'},
            'override_count': {'type': 'integer'},
            'unlinked_participants': {'type': 'integer'}
        }}}
    )
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get statistics about auto-creation"""
        try:
            from django.db import connection as db_connection
            tenant = getattr(db_connection, 'tenant', None)
            
            service = AutoCreateContactService(tenant=tenant)
            
            days = int(request.query_params.get('days', 30))
            stats = service.get_creation_stats(days=days)
            
            return Response(stats)
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ParticipantBlacklistViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing participant blacklist entries
    """
    
    queryset = ParticipantBlacklist.objects.all()
    serializer_class = ParticipantBlacklistSerializer
    permission_classes = [ParticipantSettingsPermission]  # Blacklist management requires settings permission
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['entry_type', 'is_active']
    search_fields = ['value', 'reason']
    ordering_fields = ['added_at']
    ordering = ['-added_at']
    
    def perform_create(self, serializer):
        """Set added_by on creation"""
        serializer.save(added_by=self.request.user)
    
    @extend_schema(
        summary="Check if a value is blacklisted",
        parameters=[
            {'name': 'type', 'in': 'query', 'required': True, 
             'description': 'Type of value to check (email, domain, phone, etc.)'},
            {'name': 'value', 'in': 'query', 'required': True,
             'description': 'Value to check'}
        ],
        responses={200: {'type': 'object', 'properties': {
            'is_blacklisted': {'type': 'boolean'},
            'entry': {'type': 'object', 'nullable': True}
        }}}
    )
    @action(detail=False, methods=['get'])
    def check(self, request):
        """Check if a specific value is blacklisted"""
        entry_type = request.query_params.get('type')
        value = request.query_params.get('value')
        
        if not entry_type or not value:
            return Response(
                {'error': 'Both type and value parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check for exact match
        entry = ParticipantBlacklist.objects.filter(
            entry_type=entry_type,
            value__iexact=value,
            is_active=True
        ).first()
        
        if entry:
            return Response({
                'is_blacklisted': True,
                'entry': ParticipantBlacklistSerializer(entry).data
            })
        
        # For patterns, we need to check against the service
        if entry_type in ['email_pattern', 'name_pattern']:
            from django.db import connection as db_connection
            from .services.auto_create_service import AutoCreateContactService
            
            tenant = getattr(db_connection, 'tenant', None)
            service = AutoCreateContactService(tenant=tenant)
            
            # Check all patterns
            patterns = ParticipantBlacklist.objects.filter(
                entry_type=entry_type,
                is_active=True
            )
            
            for pattern in patterns:
                if service.matches_pattern(value, pattern.value):
                    return Response({
                        'is_blacklisted': True,
                        'entry': ParticipantBlacklistSerializer(pattern).data
                    })
        
        return Response({
            'is_blacklisted': False,
            'entry': None
        })
    
    @extend_schema(
        summary="Bulk add blacklist entries",
        request={'type': 'object', 'properties': {
            'entries': {'type': 'array', 'items': {'type': 'object'}},
            'reason': {'type': 'string'}
        }},
        responses={201: {'type': 'object', 'properties': {
            'created': {'type': 'integer'},
            'failed': {'type': 'integer'}
        }}}
    )
    @action(detail=False, methods=['post'])
    def bulk_add(self, request):
        """Add multiple blacklist entries at once"""
        entries = request.data.get('entries', [])
        reason = request.data.get('reason', '')
        
        created = 0
        failed = 0
        
        for entry_data in entries:
            try:
                ParticipantBlacklist.objects.create(
                    entry_type=entry_data.get('type'),
                    value=entry_data.get('value'),
                    reason=reason,
                    added_by=request.user,
                    is_active=True
                )
                created += 1
            except Exception as e:
                logger.error(f"Failed to create blacklist entry: {e}")
                failed += 1
        
        return Response({
            'created': created,
            'failed': failed
        }, status=status.HTTP_201_CREATED)


class ParticipantOverrideViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing per-participant override settings
    """
    
    queryset = ParticipantOverride.objects.select_related('participant', 'locked_to_record')
    serializer_class = ParticipantOverrideSerializer
    permission_classes = [ParticipantSettingsPermission]  # Override management requires settings permission
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['never_auto_create', 'always_auto_create']
    search_fields = ['participant__name', 'participant__email', 'override_reason', 'internal_notes']
    ordering_fields = ['id']
    ordering = ['-id']
    
    @extend_schema(
        summary="Get override for specific participant",
        parameters=[
            {'name': 'participant_id', 'in': 'query', 'required': True}
        ],
        responses={200: ParticipantOverrideSerializer}
    )
    @action(detail=False, methods=['get'])
    def by_participant(self, request):
        """Get override settings for a specific participant"""
        participant_id = request.query_params.get('participant_id')
        
        if not participant_id:
            return Response(
                {'error': 'participant_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            override = ParticipantOverride.objects.get(participant_id=participant_id)
            serializer = self.get_serializer(override)
            return Response(serializer.data)
        except ParticipantOverride.DoesNotExist:
            return Response(
                {'error': 'No override found for this participant'},
                status=status.HTTP_404_NOT_FOUND
            )


class ChannelParticipantSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing channel-specific participant settings
    """
    
    queryset = ChannelParticipantSettings.objects.all()
    serializer_class = ChannelParticipantSettingsSerializer
    permission_classes = [ParticipantSettingsPermission]  # Channel settings require settings permission
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['channel_type', 'enabled']
    ordering_fields = ['channel_type', 'created_at']
    ordering = ['channel_type']
    
    def get_queryset(self):
        """Filter to current tenant's settings"""
        settings = ParticipantSettings.get_or_create_for_tenant()
        return self.queryset.filter(settings=settings)
    
    def perform_create(self, serializer):
        """Associate with current tenant's settings"""
        settings = ParticipantSettings.get_or_create_for_tenant()
        serializer.save(settings=settings)