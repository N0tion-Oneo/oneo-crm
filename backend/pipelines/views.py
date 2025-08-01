"""
Views for pipeline system API
"""
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
import json
import csv
import io
from openpyxl import Workbook
from django.http import HttpResponse

from .models import Pipeline, Field, Record, PipelineTemplate
from .serializers import (
    PipelineSerializer, PipelineCreateSerializer, FieldSerializer,
    RecordSerializer, RecordCreateSerializer, PipelineTemplateSerializer,
    PipelineTemplateCreatePipelineSerializer, FieldValidationSerializer,
    RecordSearchSerializer, BulkRecordActionSerializer
)
from .ai_processor import AIFieldManager, process_ai_fields_sync
from authentication.permissions import SyncPermissionManager


class PipelineViewSet(viewsets.ModelViewSet):
    """ViewSet for managing pipelines"""
    queryset = Pipeline.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['pipeline_type', 'is_active', 'access_level']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at', 'record_count']
    ordering = ['-updated_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PipelineCreateSerializer
        return PipelineSerializer
    
    def get_queryset(self):
        """Filter pipelines based on user permissions"""
        user = self.request.user
        if user.is_superuser:
            return Pipeline.objects.all()
        
        # Use comprehensive permission system
        permission_manager = SyncPermissionManager(user)
        
        # Check if user has read_all permission for pipelines
        if permission_manager.has_permission('action', 'pipelines', 'read_all'):
            return Pipeline.objects.all()
        
        # Filter to only pipelines user has access to
        accessible_pipeline_ids = self._get_accessible_pipeline_ids(user)
        return Pipeline.objects.filter(id__in=accessible_pipeline_ids)
    
    def _get_accessible_pipeline_ids(self, user):
        """Get pipeline IDs that user has access to"""
        permission_manager = SyncPermissionManager(user)
        accessible_ids = []
        
        # Check each pipeline for read access
        for pipeline in Pipeline.objects.all():
            if (permission_manager.has_permission('action', 'pipelines', 'read', str(pipeline.id)) or
                permission_manager.has_permission('action', 'pipelines', 'read') or
                pipeline.created_by == user or
                pipeline.access_level in ['public', 'internal']):
                accessible_ids.append(pipeline.id)
        
        return accessible_ids
    
    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone a pipeline"""
        pipeline = self.get_object()
        name = request.data.get('name')
        
        if not name:
            return Response(
                {'error': 'Name is required for cloning'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cloned_pipeline = pipeline.clone(name, request.user)
            serializer = PipelineSerializer(cloned_pipeline)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def fields(self, request, pk=None):
        """Get pipeline fields"""
        pipeline = self.get_object()
        fields = pipeline.fields.all()
        serializer = FieldSerializer(fields, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_field(self, request, pk=None):
        """Add a field to the pipeline"""
        pipeline = self.get_object()
        serializer = FieldSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(pipeline=pipeline, created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def records(self, request, pk=None):
        """Get pipeline records"""
        pipeline = self.get_object()
        records = pipeline.records.filter(is_deleted=False)
        
        # Apply search filters
        search_serializer = RecordSearchSerializer(
            data=request.query_params,
            pipeline=pipeline
        )
        
        if search_serializer.is_valid():
            data = search_serializer.validated_data
            
            # Apply filters
            if data.get('q'):
                records = records.extra(
                    where=["search_vector @@ plainto_tsquery(%s)"],
                    params=[data['q']]
                )
            
            if data.get('status'):
                records = records.filter(status=data['status'])
            
            if data.get('tags'):
                records = records.filter(tags__overlap=data['tags'])
            
            if data.get('created_after'):
                records = records.filter(created_at__gte=data['created_after'])
            
            if data.get('created_before'):
                records = records.filter(created_at__lte=data['created_before'])
            
            # Apply dynamic field filters
            for field in pipeline.fields.filter(is_searchable=True):
                field_name = f"field_{field.slug}"
                
                if field_name in data:
                    records = records.filter(
                        **{f"data__{field.slug}__icontains": data[field_name]}
                    )
        
        # Paginate results
        page = self.paginate_queryset(records)
        if page is not None:
            serializer = RecordSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = RecordSerializer(records, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def create_record(self, request, pk=None):
        """Create a new record in the pipeline"""
        pipeline = self.get_object()
        serializer = RecordCreateSerializer(
            data=request.data,
            context={'request': request, 'pipeline': pipeline}
        )
        
        if serializer.is_valid():
            record = serializer.save()
            
            # Process AI fields asynchronously if present
            if pipeline.get_ai_fields().exists():
                try:
                    ai_results = process_ai_fields_sync(record)
                    if ai_results:
                        record.data.update(ai_results)
                        record.save(update_fields=['data'])
                except Exception as e:
                    # AI processing failed, but record was created successfully
                    pass
            
            response_serializer = RecordSerializer(record, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """Export pipeline records"""
        pipeline = self.get_object()
        export_format = request.query_params.get('format', 'csv')
        
        records = pipeline.records.filter(is_deleted=False)
        
        if export_format == 'json':
            data = []
            for record in records:
                record_data = record.to_dict(include_metadata=True)
                data.append(record_data)
            
            response = HttpResponse(
                json.dumps(data, indent=2),
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="{pipeline.slug}_records.json"'
            
        elif export_format == 'xlsx':
            wb = Workbook()
            ws = wb.active
            ws.title = pipeline.name
            
            # Write headers
            headers = ['ID', 'Title', 'Status', 'Created At', 'Updated At']
            field_headers = [field.name for field in pipeline.fields.all()]
            headers.extend(field_headers)
            
            for col, header in enumerate(headers, 1):
                ws.cell(row=1, column=col, value=header)
            
            # Write data
            for row, record in enumerate(records, 2):
                ws.cell(row=row, column=1, value=record.id)
                ws.cell(row=row, column=2, value=record.title)
                ws.cell(row=row, column=3, value=record.status)
                ws.cell(row=row, column=4, value=record.created_at)
                ws.cell(row=row, column=5, value=record.updated_at)
                
                for col, field in enumerate(pipeline.fields.all(), 6):
                    value = record.data.get(field.slug, '')
                    ws.cell(row=row, column=col, value=str(value))
            
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{pipeline.slug}_records.xlsx"'
            
        else:  # CSV format
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            headers = ['ID', 'Title', 'Status', 'Created At', 'Updated At']
            field_headers = [field.name for field in pipeline.fields.all()]
            headers.extend(field_headers)
            writer.writerow(headers)
            
            # Write data
            for record in records:
                row = [
                    record.id,
                    record.title,
                    record.status,
                    record.created_at,
                    record.updated_at
                ]
                
                for field in pipeline.fields.all():
                    value = record.data.get(field.slug, '')
                    row.append(str(value))
                
                writer.writerow(row)
            
            response = HttpResponse(output.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{pipeline.slug}_records.csv"'
        
        return response


class FieldViewSet(viewsets.ModelViewSet):
    """ViewSet for managing pipeline fields"""
    queryset = Field.objects.all()
    serializer_class = FieldSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['pipeline', 'field_type', 'is_required', 'is_ai_field']
    ordering_fields = ['display_order', 'name', 'created_at']
    ordering = ['display_order']
    
    def get_queryset(self):
        """Filter fields based on pipeline access"""
        user = self.request.user
        if user.is_superuser:
            return Field.objects.all()
        
        # Use comprehensive permission system
        permission_manager = SyncPermissionManager(user)
        
        # Get accessible pipelines and filter fields accordingly
        if permission_manager.has_permission('action', 'pipelines', 'read_all'):
            accessible_pipelines = Pipeline.objects.all()
        else:
            accessible_pipeline_ids = self._get_accessible_pipeline_ids(user, permission_manager)
            accessible_pipelines = Pipeline.objects.filter(id__in=accessible_pipeline_ids)
        
        return Field.objects.filter(pipeline__in=accessible_pipelines)
    
    def _get_accessible_pipeline_ids(self, user, permission_manager):
        """Get pipeline IDs that user has access to"""
        accessible_ids = []
        
        for pipeline in Pipeline.objects.all():
            if (permission_manager.has_permission('action', 'pipelines', 'read', str(pipeline.id)) or
                permission_manager.has_permission('action', 'pipelines', 'read') or
                pipeline.created_by == user or
                pipeline.access_level in ['public', 'internal']):
                accessible_ids.append(pipeline.id)
        
        return accessible_ids
    
    @action(detail=True, methods=['post'])
    def validate_value(self, request, pk=None):
        """Validate a value against the field"""
        field = self.get_object()
        serializer = FieldValidationSerializer(
            data=request.data,
            context={'field': field}
        )
        
        if serializer.is_valid():
            return Response({
                'is_valid': True,
                'cleaned_value': serializer.validated_data['cleaned_value']
            })
        
        return Response({
            'is_valid': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class RecordViewSet(viewsets.ModelViewSet):
    """ViewSet for managing pipeline records"""
    queryset = Record.objects.filter(is_deleted=False)
    serializer_class = RecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['pipeline', 'status']
    search_fields = ['title', 'data']
    ordering_fields = ['created_at', 'updated_at', 'title']
    ordering = ['-updated_at']
    
    def get_queryset(self):
        """Filter records based on pipeline access"""
        user = self.request.user
        if user.is_superuser:
            return Record.objects.filter(is_deleted=False)
        
        # Use comprehensive permission system
        permission_manager = SyncPermissionManager(user)
        
        # Get accessible pipelines and filter records accordingly
        if permission_manager.has_permission('action', 'pipelines', 'read_all'):
            accessible_pipelines = Pipeline.objects.all()
        else:
            accessible_pipeline_ids = self._get_accessible_pipeline_ids(user, permission_manager)
            accessible_pipelines = Pipeline.objects.filter(id__in=accessible_pipeline_ids)
        
        return Record.objects.filter(is_deleted=False, pipeline__in=accessible_pipelines)
    
    def _get_accessible_pipeline_ids(self, user, permission_manager):
        """Get pipeline IDs that user has access to"""
        accessible_ids = []
        
        for pipeline in Pipeline.objects.all():
            if (permission_manager.has_permission('action', 'pipelines', 'read', str(pipeline.id)) or
                permission_manager.has_permission('action', 'pipelines', 'read') or
                pipeline.created_by == user or
                pipeline.access_level in ['public', 'internal']):
                accessible_ids.append(pipeline.id)
        
        return accessible_ids
    
    def get_serializer_context(self):
        """Add pipeline to serializer context"""
        context = super().get_serializer_context()
        if hasattr(self, 'get_object'):
            try:
                obj = self.get_object()
                context['pipeline'] = obj.pipeline
            except:
                pass
        return context
    
    @action(detail=True, methods=['post'])
    def soft_delete(self, request, pk=None):
        """Soft delete a record"""
        record = self.get_object()
        record.soft_delete(request.user)
        return Response({'message': 'Record deleted successfully'})
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted record"""
        record = get_object_or_404(Record, pk=pk, is_deleted=True)
        record.restore()
        serializer = self.get_serializer(record)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def process_ai_fields(self, request, pk=None):
        """Manually trigger AI field processing"""
        record = self.get_object()
        
        try:
            ai_results = process_ai_fields_sync(record, force_update=True)
            if ai_results:
                record.data.update(ai_results)
                record.save(update_fields=['data'])
            
            serializer = self.get_serializer(record)
            return Response({
                'message': 'AI fields processed successfully',
                'ai_results': ai_results,
                'record': serializer.data
            })
        
        except Exception as e:
            return Response(
                {'error': f'AI processing failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Perform bulk actions on records"""
        serializer = BulkRecordActionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        action_type = data['action']
        record_ids = data['record_ids']
        
        # Get records user has access to
        records = self.get_queryset().filter(id__in=record_ids)
        
        if not records.exists():
            return Response(
                {'error': 'No accessible records found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        result = {'processed': 0, 'errors': []}
        
        if action_type == 'delete':
            for record in records:
                record.soft_delete(request.user)
                result['processed'] += 1
        
        elif action_type == 'update_status':
            new_status = data['status']
            records.update(status=new_status, updated_by=request.user)
            result['processed'] = records.count()
        
        elif action_type == 'add_tags':
            tags = data['tags']
            for record in records:
                record.tags = list(set(record.tags + tags))
                record.updated_by = request.user
                record.save(update_fields=['tags', 'updated_by'])
                result['processed'] += 1
        
        elif action_type == 'remove_tags':
            tags = data['tags']
            for record in records:
                record.tags = [tag for tag in record.tags if tag not in tags]
                record.updated_by = request.user
                record.save(update_fields=['tags', 'updated_by'])
                result['processed'] += 1
        
        elif action_type == 'export':
            # Return export data instead of performing action
            export_data = []
            for record in records:
                export_data.append(record.to_dict(include_metadata=True))
            
            return Response({
                'export_data': export_data,
                'count': len(export_data)
            })
        
        return Response(result)


class PipelineTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing pipeline templates"""
    queryset = PipelineTemplate.objects.all()
    serializer_class = PipelineTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_system', 'is_public']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'usage_count', 'created_at']
    ordering = ['-usage_count', 'name']
    
    def get_queryset(self):
        """Filter templates based on visibility and permissions"""
        user = self.request.user
        if user.is_superuser:
            return PipelineTemplate.objects.all()
        
        # Use comprehensive permission system
        permission_manager = SyncPermissionManager(user)
        
        # Check if user has full template access
        if permission_manager.has_permission('action', 'pipelines', 'read_all'):
            return PipelineTemplate.objects.all()
        
        # Show public templates and user's own templates
        return PipelineTemplate.objects.filter(
            Q(is_public=True) |
            Q(created_by=user)
        )
    
    @action(detail=True, methods=['post'])
    def create_pipeline(self, request, pk=None):
        """Create a pipeline from this template"""
        template = self.get_object()
        serializer = PipelineTemplateCreatePipelineSerializer(
            data=request.data,
            context={'template': template, 'request': request}
        )
        
        if serializer.is_valid():
            pipeline = serializer.save()
            pipeline_serializer = PipelineSerializer(pipeline)
            return Response(pipeline_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Get template preview data"""
        template = self.get_object()
        
        return Response({
            'template_data': template.template_data,
            'preview_config': template.preview_config,
            'sample_data': template.sample_data
        })


class PipelineStatsViewSet(viewsets.ViewSet):
    """ViewSet for pipeline statistics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request):
        """Get overall pipeline statistics"""
        user = request.user
        
        # Get user's accessible pipelines using permission system
        permission_manager = SyncPermissionManager(user)
        
        if permission_manager.has_permission('action', 'pipelines', 'read_all'):
            pipelines = Pipeline.objects.all()
        else:
            accessible_pipeline_ids = self._get_accessible_pipeline_ids(user, permission_manager)
            pipelines = Pipeline.objects.filter(id__in=accessible_pipeline_ids)
        
        stats = {
            'total_pipelines': pipelines.count(),
            'total_records': Record.objects.filter(
                pipeline__in=pipelines,
                is_deleted=False
            ).count(),
            'pipeline_types': {},
            'recent_activity': []
        }
        
        # Pipeline type breakdown
        for pipeline_type, _ in Pipeline.PIPELINE_TYPES:
            count = pipelines.filter(pipeline_type=pipeline_type).count()
            if count > 0:
                stats['pipeline_types'][pipeline_type] = count
        
        # Recent activity
        recent_records = Record.objects.filter(
            pipeline__in=pipelines,
            is_deleted=False
        ).select_related('pipeline').order_by('-updated_at')[:10]
        
        for record in recent_records:
            stats['recent_activity'].append({
                'id': record.id,
                'title': record.title,
                'pipeline': record.pipeline.name,
                'updated_at': record.updated_at
            })
        
        return Response(stats)
    
    def _get_accessible_pipeline_ids(self, user, permission_manager):
        """Get pipeline IDs that user has access to"""
        accessible_ids = []
        
        for pipeline in Pipeline.objects.all():
            if (permission_manager.has_permission('action', 'pipelines', 'read', str(pipeline.id)) or
                permission_manager.has_permission('action', 'pipelines', 'read') or
                pipeline.created_by == user or
                pipeline.access_level in ['public', 'internal']):
                accessible_ids.append(pipeline.id)
        
        return accessible_ids
    
    @action(detail=False, methods=['get'])
    def pipeline_stats(self, request):
        """Get detailed statistics for a specific pipeline"""
        pipeline_id = request.query_params.get('pipeline_id')
        if not pipeline_id:
            return Response(
                {'error': 'pipeline_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            pipeline = Pipeline.objects.get(id=pipeline_id)
        except Pipeline.DoesNotExist:
            return Response(
                {'error': 'Pipeline not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        records = pipeline.records.filter(is_deleted=False)
        
        stats = {
            'pipeline': {
                'id': pipeline.id,
                'name': pipeline.name,
                'type': pipeline.pipeline_type
            },
            'total_records': records.count(),
            'status_breakdown': {},
            'creation_timeline': [],
            'ai_field_stats': {}
        }
        
        # Status breakdown
        status_counts = records.values('status').annotate(
            count=models.Count('id')
        )
        for item in status_counts:
            stats['status_breakdown'][item['status']] = item['count']
        
        # AI field statistics
        ai_fields = pipeline.fields.filter(is_ai_field=True)
        for field in ai_fields:
            ai_records = records.exclude(data__isnull=True).exclude(
                **{f'data__{field.slug}__isnull': True}
            )
            stats['ai_field_stats'][field.name] = {
                'processed_records': ai_records.count(),
                'success_rate': (ai_records.count() / records.count() * 100) if records.count() > 0 else 0
            }
        
        return Response(stats)