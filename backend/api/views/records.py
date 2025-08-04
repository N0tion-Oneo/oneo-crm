"""
Record API views with dynamic schema adaptation
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404

from pipelines.models import Pipeline, Record
from api.serializers import (
    RecordSerializer, DynamicRecordSerializer, RecordRelationshipSerializer,
    BulkRecordSerializer
)
from api.filters import DynamicRecordFilter, GlobalSearchFilter
from api.permissions import RecordPermission
from authentication.permissions import AsyncPermissionManager as PermissionManager


class RecordViewSet(viewsets.ModelViewSet):
    """
    Dynamic record API that adapts to pipeline schema
    """
    permission_classes = [RecordPermission]
    filter_backends = [DjangoFilterBackend]
    search_fields = ['title', 'data']
    ordering_fields = ['title', 'status', 'created_at', 'updated_at']
    ordering = ['-updated_at']
    
    def get_queryset(self):
        """Get records for specific pipeline or cross-pipeline"""
        pipeline_pk = self.kwargs.get('pipeline_pk')
        
        if pipeline_pk:
            # Pipeline-specific records
            return Record.objects.filter(
                pipeline_id=pipeline_pk,
                is_deleted=False
            ).select_related('pipeline', 'created_by', 'updated_by')
        else:
            # Cross-pipeline record search
            user = self.request.user
            permission_manager = PermissionManager(user)
            
            # Get accessible pipeline IDs
            accessible_pipelines = []
            for pipeline in Pipeline.objects.filter(is_active=True):
                if permission_manager.has_permission('action', 'records', 'read', str(pipeline.id)):
                    accessible_pipelines.append(pipeline.id)
            
            return Record.objects.filter(
                pipeline_id__in=accessible_pipelines,
                is_deleted=False
            ).select_related('pipeline', 'created_by', 'updated_by')
    
    def get_serializer_class(self):
        """Return dynamic serializer based on pipeline"""
        pipeline_pk = self.kwargs.get('pipeline_pk')
        
        if pipeline_pk:
            try:
                pipeline = Pipeline.objects.get(id=pipeline_pk)
                return DynamicRecordSerializer.for_pipeline(pipeline)
            except Pipeline.DoesNotExist:
                pass
        
        return RecordSerializer
    
    def get_serializer_context(self):
        """Add pipeline context to serializer"""
        context = super().get_serializer_context()
        
        pipeline_pk = self.kwargs.get('pipeline_pk')
        if pipeline_pk:
            try:
                context['pipeline'] = Pipeline.objects.get(id=pipeline_pk)
            except Pipeline.DoesNotExist:
                pass
        
        return context
    
    def get_filterset_class(self):
        """Return dynamic filterset based on pipeline"""
        pipeline_pk = self.kwargs.get('pipeline_pk')
        
        if pipeline_pk:
            try:
                pipeline = Pipeline.objects.get(id=pipeline_pk)
                # Create dynamic filter instance
                return lambda *args, **kwargs: DynamicRecordFilter(
                    *args, pipeline=pipeline, **kwargs
                )
            except Pipeline.DoesNotExist:
                pass
        
        return None
    
    def perform_create(self, serializer):
        """Set pipeline and user when creating record"""
        pipeline_pk = self.kwargs.get('pipeline_pk')
        if pipeline_pk:
            pipeline = Pipeline.objects.get(id=pipeline_pk)
            serializer.save(
                pipeline=pipeline,
                created_by=self.request.user,
                updated_by=self.request.user
            )
        else:
            # Cross-pipeline creation requires pipeline_id in data
            pipeline_id = self.request.data.get('pipeline_id')
            if pipeline_id:
                pipeline = Pipeline.objects.get(id=pipeline_id)
                serializer.save(
                    pipeline=pipeline,
                    created_by=self.request.user,
                    updated_by=self.request.user
                )
            else:
                raise ValueError("Pipeline ID required for record creation")
    
    @extend_schema(
        summary="Bulk create records",
        description="Create multiple records in a single request",
        request=BulkRecordSerializer
    )
    @action(detail=False, methods=['post'])
    def bulk_create(self, request, pipeline_pk=None):
        """Bulk create multiple records"""
        pipeline = Pipeline.objects.get(id=pipeline_pk)
        serializer = BulkRecordSerializer(
            data=request.data,
            context={'pipeline': pipeline}
        )
        
        if serializer.is_valid():
            validated_records = serializer.validated_data['records']
            
            # Create records
            created_records = []
            for record_data in validated_records:
                record = Record.objects.create(
                    pipeline=pipeline,
                    data=record_data,
                    created_by=request.user,
                    updated_by=request.user
                )
                created_records.append(record)
            
            # Serialize created records
            response_serializer = self.get_serializer(created_records, many=True)
            
            return Response({
                'created': response_serializer.data,
                'created_count': len(created_records),
                'success': True
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Bulk update records",
        description="Update multiple records with different data",
        request={
            "type": "object",
            "properties": {
                "updates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "data": {"type": "object"}
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['patch'])
    def bulk_update(self, request, pipeline_pk=None):
        """Bulk update multiple records"""
        updates = request.data.get('updates', [])
        pipeline = Pipeline.objects.get(id=pipeline_pk) if pipeline_pk else None
        
        updated_records = []
        errors = []
        
        for update_data in updates:
            record_id = update_data.get('id')
            new_data = update_data.get('data', {})
            
            try:
                record = Record.objects.get(
                    id=record_id,
                    pipeline=pipeline,
                    is_deleted=False
                )
                
                # Validate new data if pipeline specified
                if pipeline:
                    validation_result = pipeline.validate_record_data(new_data)
                    if not validation_result['is_valid']:
                        errors.append({
                            'record_id': record_id,
                            'errors': validation_result['errors']
                        })
                        continue
                    new_data = validation_result['cleaned_data']
                
                # Update record
                record.data.update(new_data)
                record.updated_by = request.user
                record.save()
                updated_records.append(record)
                
            except Record.DoesNotExist:
                errors.append({
                    'record_id': record_id,
                    'errors': {'general': ['Record not found']}
                })
            except Exception as e:
                errors.append({
                    'record_id': record_id,
                    'errors': {'general': [str(e)]}
                })
        
        # Serialize updated records
        response_serializer = self.get_serializer(updated_records, many=True)
        
        return Response({
            'updated': response_serializer.data,
            'updated_count': len(updated_records),
            'errors': errors,
            'error_count': len(errors)
        })
    
    @extend_schema(
        summary="Get record relationships",
        description="Get all relationships for a specific record",
        parameters=[
            OpenApiParameter('depth', int, description='Traversal depth (default: 1)'),
            OpenApiParameter('direction', str, description='Traversal direction (forward/reverse/both)'),
            OpenApiParameter('relationship_types', str, description='Comma-separated relationship type IDs')
        ]
    )
    @action(detail=True, methods=['get'])
    def relationships(self, request, pk=None, pipeline_pk=None):
        """Get relationships for a specific record"""
        record = self.get_object()
        depth = int(request.query_params.get('depth', 1))
        direction = request.query_params.get('direction', 'both')
        relationship_types = request.query_params.get('relationship_types')
        
        # Parse relationship types
        relationship_type_ids = None
        if relationship_types:
            try:
                relationship_type_ids = [int(x.strip()) for x in relationship_types.split(',')]
            except ValueError:
                return Response(
                    {'error': 'Invalid relationship_types format'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Use relationship query manager
        from relationships.queries import RelationshipQueryManager
        query_manager = RelationshipQueryManager(request.user)
        
        relationships = query_manager.get_related_records(
            source_pipeline_id=record.pipeline_id,
            source_record_id=record.id,
            relationship_types=relationship_type_ids,
            max_depth=depth,
            direction=direction,
            include_paths=True
        )
        
        return Response(relationships)
    
    @extend_schema(
        summary="Get record history",
        description="Get change history for a specific record"
    )
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None, pipeline_pk=None):
        """Get change history for a record"""
        record = self.get_object()
        
        # Get audit logs for this record
        from core.models import AuditLog
        audit_logs = AuditLog.objects.filter(
            model_name='Record',
            object_id=str(record.id)
        ).order_by('-timestamp')
        
        # Format audit logs into activity entries
        activities = []
        for log in audit_logs:
            # Map action to frontend expected type
            activity_type = 'field_change' if log.action == 'updated' else (
                'system' if log.action in ['created', 'deleted'] else 'comment'
            )
            
            activity = {
                'id': log.id,
                'type': activity_type,
                'message': self._format_audit_changes(log.changes, log.action),
                'user': {
                    'first_name': log.user.first_name if log.user else '',
                    'last_name': log.user.last_name if log.user else '',
                    'email': log.user.email if log.user else ''
                } if log.user else None,
                'created_at': log.timestamp.isoformat()
            }
            activities.append(activity)
        
        history = {
            'record_id': record.id,
            'pipeline_id': record.pipeline_id,
            'pipeline_name': record.pipeline.name,
            'record_title': record.title,
            'created_at': record.created_at,
            'created_by': record.created_by.email if record.created_by else None,
            'updated_at': record.updated_at,
            'updated_by': record.updated_by.email if record.updated_by else None,
            'activities': activities,
            'activity_count': len(activities)
        }
        
        return Response(history)
    
    def _format_audit_changes(self, changes, action):
        """Format audit log changes for display"""
        if action == 'created':
            # Show initial field values when record was created
            initial_values = []
            if 'data' in changes and isinstance(changes['data'], dict):
                for field, value in changes['data'].items():
                    if value is not None and value != '' and value != 'None':
                        display_name = self._get_field_display_name(field)
                        formatted_value = self._format_field_value(value)
                        initial_values.append(f"{display_name}: {formatted_value}")
            
            if initial_values:
                return f"Record created with:\n" + '\n'.join(initial_values)
            else:
                return f"Record created in {changes.get('pipeline', 'Unknown')} pipeline"
        
        elif action == 'updated':
            formatted_changes = []
            
            # Format data changes
            if 'data_changes' in changes:
                for field, change in changes['data_changes'].items():
                    old_val = change.get('old')
                    new_val = change.get('new')
                    
                    # Get display name for field
                    display_name = self._get_field_display_name(field)
                    
                    # Format values for better readability
                    old_display = self._format_field_value(old_val)
                    new_display = self._format_field_value(new_val)
                    
                    formatted_changes.append(f"{display_name}: {old_display} → {new_display}")
            
            # Format status changes
            if 'status' in changes:
                status_change = changes['status']
                old_status = self._format_field_value(status_change.get('old'))
                new_status = self._format_field_value(status_change.get('new'))
                formatted_changes.append(f"Status: {old_status} → {new_status}")
            
            # Show all changes individually with line breaks for detailed view
            if formatted_changes:
                return '\n'.join(formatted_changes)
            else:
                return 'Record updated'
        
        elif action == 'deleted':
            return f"Record deleted from {changes.get('pipeline', 'Unknown')} pipeline"
        
        return f"Record {action}"
    
    def _get_field_display_name(self, field_name):
        """Get human-readable display name for a field"""
        # Try to get the field from the pipeline to get display_name
        try:
            # Use request context to get the pipeline for field lookup
            if hasattr(self.request, '_cached_pipeline'):
                pipeline = self.request._cached_pipeline
            else:
                pipeline_pk = self.kwargs.get('pipeline_pk')
                if pipeline_pk:
                    from pipelines.models import Pipeline
                    pipeline = Pipeline.objects.get(id=pipeline_pk)
                    self.request._cached_pipeline = pipeline
                else:
                    return field_name.replace('_', ' ').title()
            
            # Look up the field by name to get display_name
            field = pipeline.fields.filter(name=field_name).first()
            if field and field.display_name:
                return field.display_name
                
        except Exception as e:
            # Log the error but don't fail
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Could not get field display name for {field_name}: {e}")
        
        # Fallback to converting field name to readable format
        return field_name.replace('_', ' ').title()
    
    def _format_field_value(self, value):
        """Format field values for display"""
        if value is None or value == '' or value == 'None':
            return "(empty)"
        
        # Handle dates
        if isinstance(value, str) and 'T' in value and value.endswith('+00:00'):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return dt.strftime('%b %d, %Y at %I:%M %p')
            except:
                pass
        
        # Handle phone objects
        if isinstance(value, dict) and 'country_code' in value and 'number' in value:
            return f"{value['country_code']} {value['number']}"
        
        # Handle currency objects
        if isinstance(value, dict) and 'amount' in value and 'currency' in value:
            return f"{value['currency']} {value['amount']}"
        
        # Handle lists (like tags)
        if isinstance(value, list):
            if len(value) == 0:
                return "(empty)"
            elif len(value) <= 3:
                return ', '.join(str(v) for v in value)
            else:
                return f"{', '.join(str(v) for v in value[:2])} and {len(value)-2} more"
        
        # Handle strings
        if isinstance(value, str):
            # Check if it looks like a JavaScript event object (data quality issue)
            if value.startswith("{'_targetInst'") or "'type': 'change'" in value:
                return "(invalid data)"
            
            # Truncate long strings
            if len(value) > 50:
                return value[:47] + "..."
        
        return str(value)
    
    @extend_schema(
        summary="Get stage trigger status",
        description="Get current stage and missing required fields information"
    )
    @action(detail=True, methods=['get'])
    def stage_trigger_status(self, request, pk=None, pipeline_pk=None):
        """Get stage trigger status for a record"""
        record = self.get_object()
        
        from pipelines.triggers import get_stage_trigger_status
        trigger_status = get_stage_trigger_status(record)
        
        return Response(trigger_status)

    @extend_schema(
        summary="Duplicate record",
        description="Create a copy of an existing record"
    )
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None, pipeline_pk=None):
        """Duplicate an existing record"""
        source_record = self.get_object()
        
        # Create new record with copied data
        new_record = Record.objects.create(
            pipeline=source_record.pipeline,
            data=source_record.data.copy(),
            status='draft',  # New records start as draft
            created_by=request.user,
            updated_by=request.user
        )
        
        serializer = self.get_serializer(new_record)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        summary="Validate record data",
        description="Validate record data against pipeline schema without saving. " \
                   "Error messages include source prefixes like [BACKEND_VALIDATOR], " \
                   "[STORAGE_CONSTRAINT], or [BUSINESS_RULES] for debugging."
    )
    @action(detail=False, methods=['post'])
    def validate(self, request, pipeline_pk=None):
        """Validate record data without creating"""
        pipeline = Pipeline.objects.get(id=pipeline_pk)
        data = request.data.get('data', {})
        
        validation_result = pipeline.validate_record_data(data)
        
        return Response({
            'is_valid': validation_result['is_valid'],
            'errors': validation_result['errors'],
            'cleaned_data': validation_result.get('cleaned_data'),
            'pipeline_id': pipeline.id,
            'pipeline_name': pipeline.name,
            'validation_source': 'backend_validator'  # Clear indicator for API consumers
        })
    
    def destroy(self, request, *args, **kwargs):
        """
        Hard delete a record (permanent deletion)
        This triggers post_delete signal for real-time updates
        """
        instance = self.get_object()
        
        # Perform hard deletion (triggers post_delete signal)
        instance.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @extend_schema(
        summary="Soft delete a record",
        description="Marks a record as deleted without removing it from database. Can be restored later.",
        responses={200: {"description": "Record soft deleted successfully"}}
    )
    @action(detail=True, methods=['post'])
    def soft_delete(self, request, pk=None, pipeline_pk=None):
        """Soft delete a record (can be restored)"""
        record = self.get_object()
        
        # Perform soft deletion (triggers post_save signal with is_deleted=True)
        record.soft_delete(request.user)
        
        return Response({
            'message': 'Record soft deleted successfully',
            'record_id': str(record.id),
            'deleted_at': record.deleted_at.isoformat() if record.deleted_at else None
        })
    
    @extend_schema(
        summary="Restore a soft-deleted record",
        description="Restores a previously soft-deleted record, making it active again.",
        responses={200: DynamicRecordSerializer}
    )
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None, pipeline_pk=None):
        """Restore a soft-deleted record"""
        # Find the soft-deleted record
        pipeline_pk = self.kwargs.get('pipeline_pk')
        if pipeline_pk:
            record = get_object_or_404(
                Record, 
                pk=pk, 
                pipeline_id=pipeline_pk, 
                is_deleted=True
            )
        else:
            record = get_object_or_404(Record, pk=pk, is_deleted=True)
        
        # Restore the record (triggers post_save signal)
        record.restore()
        
        # Return the restored record
        serializer = self.get_serializer(record)
        return Response({
            'message': 'Record restored successfully',
            'record': serializer.data
        })
    
    @extend_schema(
        summary="Get deleted records",
        description="List all soft-deleted records for the pipeline",
        responses={200: DynamicRecordSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def deleted(self, request, pipeline_pk=None):
        """Get all soft-deleted records"""
        pipeline_pk = self.kwargs.get('pipeline_pk')
        
        if pipeline_pk:
            # Pipeline-specific deleted records
            queryset = Record.objects.filter(
                pipeline_id=pipeline_pk,
                is_deleted=True
            ).select_related('pipeline', 'created_by', 'updated_by', 'deleted_by')
        else:
            # Cross-pipeline deleted records (with permission checking)
            user = request.user
            permission_manager = PermissionManager(user)
            
            # Get accessible pipeline IDs
            accessible_pipelines = []
            for pipeline in Pipeline.objects.filter(is_active=True):
                if permission_manager.has_permission('action', 'pipelines', 'read', pipeline.id):
                    accessible_pipelines.append(pipeline.id)
            
            queryset = Record.objects.filter(
                pipeline_id__in=accessible_pipelines,
                is_deleted=True
            ).select_related('pipeline', 'created_by', 'updated_by', 'deleted_by')
        
        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Search suggestions",
        description="Get search suggestions based on partial query"
    )
    @action(detail=False, methods=['get'])
    def suggestions(self, request):
        """Get search suggestions"""
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response({'suggestions': []})
        
        # Get title suggestions
        title_suggestions = Record.objects.filter(
            title__icontains=query,
            is_deleted=False
        ).values_list('title', flat=True).distinct()[:10]
        
        # Get data field suggestions (this could be more sophisticated)
        data_suggestions = []
        
        suggestions = {
            'titles': list(title_suggestions),
            'data_fields': data_suggestions,
            'query': query
        }
        
        return Response({'suggestions': suggestions})


class GlobalSearchViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Global search across all accessible records
    """
    serializer_class = RecordSerializer
    permission_classes = [RecordPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_class = GlobalSearchFilter
    
    def get_queryset(self):
        """Get records from all accessible pipelines"""
        user = self.request.user
        permission_manager = PermissionManager(user)
        
        # Get accessible pipeline IDs
        accessible_pipelines = []
        for pipeline in Pipeline.objects.filter(is_active=True):
            if permission_manager.has_permission('action', 'records', 'read', str(pipeline.id)):
                accessible_pipelines.append(pipeline.id)
        
        return Record.objects.filter(
            pipeline_id__in=accessible_pipelines,
            is_deleted=False
        ).select_related('pipeline', 'created_by', 'updated_by')
    
    @extend_schema(
        summary="Search across all pipelines",
        description="Search for records across all accessible pipelines",
        parameters=[
            OpenApiParameter('q', str, description='Search query'),
            OpenApiParameter('pipeline_ids', str, description='Comma-separated pipeline IDs to search'),
            OpenApiParameter('limit', int, description='Maximum number of results')
        ]
    )
    def list(self, request, *args, **kwargs):
        """Enhanced list with search ranking"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Apply search query with ranking if available
        search_query = request.query_params.get('q')
        if search_query:
            try:
                # Use PostgreSQL full-text search if available
                from django.contrib.postgres.search import SearchQuery, SearchRank
                search_q = SearchQuery(search_query)
                queryset = queryset.filter(
                    search_vector=search_q
                ).annotate(
                    rank=SearchRank('search_vector', search_q)
                ).order_by('-rank')
            except:
                # Fallback to simple text search
                queryset = queryset.filter(
                    Q(title__icontains=search_query) |
                    Q(data__icontains=search_query)
                )
        
        # Apply limit
        limit = request.query_params.get('limit')
        if limit:
            try:
                queryset = queryset[:int(limit)]
            except ValueError:
                pass
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Search suggestions",
        description="Get search suggestions based on partial query"
    )
    @action(detail=False, methods=['get'])
    def suggestions(self, request):
        """Get search suggestions"""
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response({'suggestions': []})
        
        # Get title suggestions
        title_suggestions = Record.objects.filter(
            title__icontains=query,
            is_deleted=False
        ).values_list('title', flat=True).distinct()[:10]
        
        # Get data field suggestions (this could be more sophisticated)
        data_suggestions = []
        
        suggestions = {
            'titles': list(title_suggestions),
            'data_fields': data_suggestions,
            'query': query
        }
        
        return Response({'suggestions': suggestions})