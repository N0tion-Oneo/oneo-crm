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
        print(f"🚀 DynamicRecordFilter.__init__ called with pipeline: {pipeline}")
        super().__init__(*args, **kwargs)
        
        if pipeline:
            print(f"🚀 Adding dynamic filters for pipeline: {pipeline.name}")
            self._add_dynamic_filters(pipeline)
        else:
            print(f"🚀 No pipeline provided to DynamicRecordFilter")
    
    def _add_dynamic_filters(self, pipeline):
        """Add filters based on pipeline field schema"""
        print(f"🔧 _add_dynamic_filters called for {pipeline.name}")
        
        for field in pipeline.fields.all():
            filter_name = f"data__{field.slug}"
            print(f"  📝 Adding filters for field: {field.name} ({field.field_type})")
            
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
                
            elif field.field_type == 'user':
                # User field filters - custom method for JSONB array filtering
                print(f"  📝 Adding user field filter for: {field.slug}")
                user_filter = filters.NumberFilter(method='filter_user_field_contains')
                self.filters[f"{filter_name}__user_id"] = user_filter
                self.filters[f"{filter_name}__isnull"] = filters.BooleanFilter(
                    field_name=f'data__{field.slug}',
                    lookup_expr='isnull'
                )
                print(f"  ✅ Created user filter: {filter_name}__user_id with method: {user_filter.method}")
                
            elif field.field_type in ['tags']:
                # Tags field filters
                self.filters[f"{filter_name}__icontains"] = filters.CharFilter(
                    field_name=f'data__{field.slug}',
                    lookup_expr='icontains'
                )
                self.filters[f"{filter_name}__isnull"] = filters.BooleanFilter(
                    field_name=f'data__{field.slug}',
                    lookup_expr='isnull'
                )
                
            elif field.field_type in ['relation', 'relationship']:
                # Relationship field filters
                self.filters[f"{filter_name}__contains"] = filters.NumberFilter(
                    method='filter_relationship_contains'
                )
                self.filters[f"{filter_name}__isnull"] = filters.BooleanFilter(
                    field_name=f'data__{field.slug}',
                    lookup_expr='isnull'
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
    
    
    def filter_relationship_contains(self, queryset, name, value):
        """Filter records where relationship field contains specific record ID"""
        if not value:
            return queryset
        
        # Extract field slug from filter name
        field_slug = name.replace('data__', '').replace('__contains', '')
        
        # Handle both single values and arrays for relationship fields
        return queryset.extra(
            where=[
                "(data->%s @> %s OR (data->%s)::text = %s)"
            ],
            params=[field_slug, f'[{int(value)}]', field_slug, str(int(value))]
        )
    
    def filter_user_field_contains(self, queryset, name, value):
        """Filter records where user field array contains specific user_id"""
        print(f"🎯🎯🎯 CUSTOM USER FILTER METHOD CALLED! 🎯🎯🎯")
        print(f"🔍 FILTERING USER FIELD: {name} = {value}")
        print(f"🔍 QuerySet before filter: {queryset.count()} records")
        
        if not value:
            print(f"🔍 No value provided, returning original queryset")
            return queryset
        
        # Extract field slug from filter name: data__sales_agent__user_id -> sales_agent
        field_slug = name.replace('data__', '').replace('__user_id', '')
        
        print(f"  🎯 Field slug: {field_slug}")
        print(f"  🔍 Looking for user_id: {value}")
        
        # Use simple JSONB containment with a constructed user object
        # This checks if the array contains an object with the specific user_id
        filtered_queryset = queryset.extra(
            where=[
                "data->%s @> %s::jsonb"
            ],
            params=[field_slug, f'[{{"user_id": {int(value)}}}]']
        )
        
        print(f"🔍 QuerySet after filter: {filtered_queryset.count()} records")
        return filtered_queryset
    
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