"""
Custom filter classes for dynamic API filtering
"""
import django_filters
from django_filters import rest_framework as filters
from django.db import models
from pipelines.models import Pipeline, Record, Field
from relationships.models import Relationship


class PipelineFilter(filters.FilterSet):
    """Comprehensive pipeline filtering"""
    name = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    pipeline_type = filters.ChoiceFilter(choices=Pipeline.PIPELINE_TYPES)
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    is_active = filters.BooleanFilter()
    created_by = filters.NumberFilter()
    
    # Advanced filters
    has_records = filters.BooleanFilter(method='filter_has_records')
    record_count_min = filters.NumberFilter(method='filter_record_count_min')
    record_count_max = filters.NumberFilter(method='filter_record_count_max')
    
    class Meta:
        model = Pipeline
        fields = ['name', 'pipeline_type', 'is_active', 'created_by']
    
    def filter_has_records(self, queryset, name, value):
        """Filter pipelines that have/don't have records"""
        if value:
            return queryset.filter(records__isnull=False).distinct()
        else:
            return queryset.filter(records__isnull=True)
    
    def filter_record_count_min(self, queryset, name, value):
        """Filter by minimum record count"""
        return queryset.annotate(
            record_count=models.Count('records', filter=models.Q(records__is_deleted=False))
        ).filter(record_count__gte=value)
    
    def filter_record_count_max(self, queryset, name, value):
        """Filter by maximum record count"""
        return queryset.annotate(
            record_count=models.Count('records', filter=models.Q(records__is_deleted=False))
        ).filter(record_count__lte=value)


class DynamicRecordFilter(filters.FilterSet):
    """Dynamic filter for records based on pipeline schema"""
    
    # Standard fields
    status = filters.CharFilter()
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    created_by = filters.NumberFilter()
    updated_by = filters.NumberFilter()
    
    # Search
    search = filters.CharFilter(method='filter_search')
    
    def __init__(self, *args, **kwargs):
        pipeline = kwargs.pop('pipeline', None)
        super().__init__(*args, **kwargs)
        
        if pipeline:
            self._add_dynamic_filters(pipeline)
    
    def _add_dynamic_filters(self, pipeline):
        """Add filters based on pipeline field schema"""
        for field in pipeline.fields.all():
            filter_name = f"data__{field.slug}"
            
            if field.field_type in ['text', 'textarea', 'email', 'url']:
                # Text field filters
                self.filters[filter_name] = filters.CharFilter(
                    field_name=f'data__{field.slug}',
                    lookup_expr='icontains'
                )
                self.filters[f"{filter_name}__exact"] = filters.CharFilter(
                    field_name=f'data__{field.slug}',
                    lookup_expr='exact'
                )
                self.filters[f"{filter_name}__isnull"] = filters.BooleanFilter(
                    field_name=f'data__{field.slug}',
                    lookup_expr='isnull'
                )
                
            elif field.field_type in ['number', 'decimal']:
                # Numeric field filters
                self.filters[filter_name] = filters.NumberFilter(
                    field_name=f'data__{field.slug}'
                )
                self.filters[f"{filter_name}__gte"] = filters.NumberFilter(
                    field_name=f'data__{field.slug}',
                    lookup_expr='gte'
                )
                self.filters[f"{filter_name}__lte"] = filters.NumberFilter(
                    field_name=f'data__{field.slug}',
                    lookup_expr='lte'
                )
                self.filters[f"{filter_name}__gt"] = filters.NumberFilter(
                    field_name=f'data__{field.slug}',
                    lookup_expr='gt'
                )
                self.filters[f"{filter_name}__lt"] = filters.NumberFilter(
                    field_name=f'data__{field.slug}',
                    lookup_expr='lt'
                )
                
            elif field.field_type in ['date', 'datetime']:
                # Date field filters
                self.filters[f"{filter_name}__gte"] = filters.DateTimeFilter(
                    field_name=f'data__{field.slug}',
                    lookup_expr='gte'
                )
                self.filters[f"{filter_name}__lte"] = filters.DateTimeFilter(
                    field_name=f'data__{field.slug}',
                    lookup_expr='lte'
                )
                self.filters[f"{filter_name}__date"] = filters.DateFilter(
                    field_name=f'data__{field.slug}__date'
                )
                
            elif field.field_type == 'boolean':
                # Boolean field filter
                self.filters[filter_name] = filters.BooleanFilter(
                    field_name=f'data__{field.slug}'
                )
                
            elif field.field_type in ['select', 'multiselect']:
                # Choice field filters
                self.filters[filter_name] = filters.CharFilter(
                    field_name=f'data__{field.slug}',
                    lookup_expr='exact'
                )
                self.filters[f"{filter_name}__in"] = filters.CharFilter(
                    field_name=f'data__{field.slug}',
                    lookup_expr='in',
                    method='filter_choice_in'
                )
    
    def filter_search(self, queryset, name, value):
        """Full-text search across record data"""
        if not value:
            return queryset
        
        # Use PostgreSQL full-text search if available
        try:
            from django.contrib.postgres.search import SearchQuery, SearchRank
            search_query = SearchQuery(value)
            return queryset.filter(
                search_vector=search_query
            ).annotate(
                rank=SearchRank('search_vector', search_query)
            ).order_by('-rank')
        except:
            # Fallback to JSON field search
            return queryset.filter(data__icontains=value)
    
    def filter_choice_in(self, queryset, name, value):
        """Filter for multiple choice values"""
        if not value:
            return queryset
        
        values = [v.strip() for v in value.split(',')]
        field_name = name.replace('__in', '')
        return queryset.filter(**{f"{field_name}__in": values})
    
    class Meta:
        model = Record
        fields = ['status', 'created_by', 'updated_by']


class RelationshipFilter(filters.FilterSet):
    """Filter for relationship queries"""
    relationship_type = filters.NumberFilter()
    relationship_type_slug = filters.CharFilter(
        field_name='relationship_type__slug'
    )
    status = filters.ChoiceFilter(choices=Relationship.STATUS_CHOICES)
    strength_min = filters.NumberFilter(field_name='strength', lookup_expr='gte')
    strength_max = filters.NumberFilter(field_name='strength', lookup_expr='lte')
    is_verified = filters.BooleanFilter()
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    # Pipeline-specific filters
    source_pipeline = filters.NumberFilter()
    target_pipeline = filters.NumberFilter()
    
    # User assignment filters
    user = filters.NumberFilter()
    role = filters.ChoiceFilter(choices=Relationship.ROLE_CHOICES)
    
    class Meta:
        model = Relationship
        fields = ['relationship_type', 'status', 'is_verified', 'user', 'role']


class GlobalSearchFilter(filters.FilterSet):
    """Global search across all records"""
    q = filters.CharFilter(method='filter_global_search')
    pipeline_ids = filters.CharFilter(method='filter_pipeline_ids')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    status = filters.CharFilter()
    
    def filter_global_search(self, queryset, name, value):
        """Global search implementation"""
        if not value:
            return queryset
        
        # Search in title and data fields
        return queryset.filter(
            models.Q(title__icontains=value) |
            models.Q(data__icontains=value)
        )
    
    def filter_pipeline_ids(self, queryset, name, value):
        """Filter by multiple pipeline IDs"""
        if not value:
            return queryset
        
        try:
            pipeline_ids = [int(pid.strip()) for pid in value.split(',')]
            return queryset.filter(pipeline_id__in=pipeline_ids)
        except ValueError:
            return queryset.none()
    
    class Meta:
        model = Record
        fields = ['status']