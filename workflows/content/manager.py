"""
Content Management System - Central manager for content assets and templates
Provides the core functionality for managing reusable content across workflows
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.core.files.uploadedfile import UploadedFile

from .models import (
    ContentLibrary, ContentAsset, ContentTag, ContentUsage, 
    ContentApproval, ContentType, ContentStatus, ContentVisibility
)

User = get_user_model()
logger = logging.getLogger(__name__)


class ContentManager:
    """Central manager for content operations"""
    
    def __init__(self):
        self.supported_extensions = {
            ContentType.IMAGE_ASSET: ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'],
            ContentType.DOCUMENT_ASSET: ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'],
            ContentType.VIDEO_ASSET: ['mp4', 'mov', 'avi', 'webm'],
        }
    
    # Library Management
    
    def create_library(
        self, 
        name: str, 
        description: str, 
        created_by: User,
        parent_library: Optional[ContentLibrary] = None,
        visibility: str = ContentVisibility.ORGANIZATION,
        requires_approval: bool = False
    ) -> ContentLibrary:
        """Create a new content library"""
        
        library = ContentLibrary.objects.create(
            name=name,
            description=description,
            parent_library=parent_library,
            visibility=visibility,
            created_by=created_by,
            requires_approval=requires_approval
        )
        
        logger.info(f"Created content library: {name} by {created_by.username}")
        return library
    
    def get_accessible_libraries(self, user: User) -> List[ContentLibrary]:
        """Get libraries accessible to a user"""
        
        return ContentLibrary.objects.filter(
            Q(visibility=ContentVisibility.PUBLIC) |
            Q(visibility=ContentVisibility.ORGANIZATION) |
            Q(created_by=user) |
            Q(allowed_users=user),
            is_active=True
        ).distinct().order_by('name')
    
    # Content Asset Management
    
    def create_text_content(
        self,
        name: str,
        content_type: str,
        content_text: str,
        library: ContentLibrary,
        created_by: User,
        description: str = "",
        template_variables: List[str] = None,
        tags: List[str] = None,
        visibility: str = ContentVisibility.ORGANIZATION
    ) -> ContentAsset:
        """Create text-based content (templates, snippets)"""
        
        # Validate content type
        if content_type not in [ContentType.EMAIL_TEMPLATE, ContentType.MESSAGE_TEMPLATE, 
                               ContentType.HTML_SNIPPET, ContentType.TEXT_SNIPPET]:
            raise ValueError(f"Invalid content type for text content: {content_type}")
        
        # Extract variables from content if not provided
        if template_variables is None:
            template_variables = self._extract_template_variables(content_text)
        
        asset = ContentAsset.objects.create(
            name=name,
            description=description,
            content_type=content_type,
            content_text=content_text,
            template_variables=template_variables,
            library=library,
            created_by=created_by,
            visibility=visibility,
            status=ContentStatus.APPROVED if not library.requires_approval else ContentStatus.DRAFT
        )
        
        # Add tags
        if tags:
            self._add_tags_to_asset(asset, tags, created_by)
        
        logger.info(f"Created text content: {name} in library {library.name}")
        return asset
    
    def create_file_content(
        self,
        name: str,
        content_type: str,
        content_file: UploadedFile,
        library: ContentLibrary,
        created_by: User,
        description: str = "",
        tags: List[str] = None,
        visibility: str = ContentVisibility.ORGANIZATION
    ) -> ContentAsset:
        """Create file-based content (images, documents, videos)"""
        
        # Validate file extension
        if not self._validate_file_extension(content_file.name, content_type):
            raise ValueError(f"Invalid file extension for content type: {content_type}")
        
        asset = ContentAsset.objects.create(
            name=name,
            description=description,
            content_type=content_type,
            content_file=content_file,
            library=library,
            created_by=created_by,
            visibility=visibility,
            file_size=content_file.size,
            mime_type=getattr(content_file, 'content_type', ''),
            status=ContentStatus.APPROVED if not library.requires_approval else ContentStatus.DRAFT
        )
        
        # Add file metadata
        metadata = self._extract_file_metadata(content_file, content_type)
        if metadata:
            asset.metadata = metadata
            asset.save(update_fields=['metadata'])
        
        # Add tags
        if tags:
            self._add_tags_to_asset(asset, tags, created_by)
        
        logger.info(f"Created file content: {name} in library {library.name}")
        return asset
    
    def create_data_content(
        self,
        name: str,
        content_data: Dict[str, Any],
        library: ContentLibrary,
        created_by: User,
        description: str = "",
        tags: List[str] = None,
        visibility: str = ContentVisibility.ORGANIZATION
    ) -> ContentAsset:
        """Create structured data content (JSON, configuration)"""
        
        asset = ContentAsset.objects.create(
            name=name,
            description=description,
            content_type=ContentType.JSON_DATA,
            content_data=content_data,
            library=library,
            created_by=created_by,
            visibility=visibility,
            status=ContentStatus.APPROVED if not library.requires_approval else ContentStatus.DRAFT
        )
        
        # Add tags
        if tags:
            self._add_tags_to_asset(asset, tags, created_by)
        
        logger.info(f"Created data content: {name} in library {library.name}")
        return asset
    
    def get_content_for_workflow(
        self, 
        user: User, 
        content_type: Optional[str] = None,
        library_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[ContentAsset]:
        """Get content assets available for use in workflows"""
        
        query = Q(
            status=ContentStatus.APPROVED,
            is_current_version=True
        )
        
        # Filter by accessibility
        query &= (
            Q(visibility=ContentVisibility.PUBLIC) |
            Q(visibility=ContentVisibility.ORGANIZATION) |
            Q(created_by=user) |
            Q(library__allowed_users=user)
        )
        
        # Apply filters
        if content_type:
            query &= Q(content_type=content_type)
        
        if library_id:
            query &= Q(library_id=library_id)
        
        queryset = ContentAsset.objects.filter(query).select_related(
            'library', 'created_by'
        ).prefetch_related('tags')
        
        # Filter by tags
        if tags:
            for tag in tags:
                queryset = queryset.filter(tags__name=tag)
        
        return queryset.order_by('-usage_count', '-created_at')
    
    # Content Usage Tracking
    
    def track_content_usage(
        self,
        content_asset: ContentAsset,
        workflow_id: str,
        workflow_name: str,
        node_id: str,
        node_type: str,
        usage_type: str = "template",
        variables_used: Dict[str, Any] = None
    ) -> ContentUsage:
        """Track content usage in workflows"""
        
        usage, created = ContentUsage.objects.get_or_create(
            content_asset=content_asset,
            workflow_id=workflow_id,
            node_id=node_id,
            defaults={
                'workflow_name': workflow_name,
                'node_type': node_type,
                'usage_type': usage_type,
                'variables_used': variables_used or {},
                'execution_count': 0
            }
        )
        
        if not created:
            # Update existing usage record
            usage.workflow_name = workflow_name
            usage.node_type = node_type
            usage.usage_type = usage_type
            if variables_used:
                usage.variables_used = variables_used
            usage.save()
        
        # Increment asset usage count
        content_asset.increment_usage()
        
        return usage
    
    def record_content_execution(
        self,
        content_asset: ContentAsset,
        workflow_id: str,
        node_id: str,
        success: bool = True,
        execution_metadata: Dict[str, Any] = None
    ):
        """Record a content execution for analytics"""
        
        try:
            usage = ContentUsage.objects.get(
                content_asset=content_asset,
                workflow_id=workflow_id,
                node_id=node_id
            )
            
            usage.execution_count += 1
            usage.last_execution = timezone.now()
            
            # Update success rate
            if usage.success_rate is None:
                usage.success_rate = 100.0 if success else 0.0
            else:
                # Simple moving average
                current_rate = float(usage.success_rate)
                new_rate = (current_rate + (100.0 if success else 0.0)) / 2
                usage.success_rate = round(new_rate, 2)
            
            if execution_metadata:
                usage.metadata.update(execution_metadata)
            
            usage.save()
            
        except ContentUsage.DoesNotExist:
            logger.warning(f"Usage record not found for content {content_asset.id} in workflow {workflow_id}")
    
    # Content Rendering
    
    def render_content(
        self,
        content_asset: ContentAsset,
        variables: Dict[str, Any] = None,
        workflow_context: Dict[str, Any] = None
    ) -> str:
        """Render content with variables and context"""
        
        try:
            if content_asset.content_type in [ContentType.EMAIL_TEMPLATE, ContentType.MESSAGE_TEMPLATE, ContentType.HTML_SNIPPET]:
                return content_asset.render_template(variables or {})
            else:
                return content_asset.get_content()
                
        except Exception as e:
            logger.error(f"Error rendering content {content_asset.id}: {e}")
            return content_asset.get_content()  # Fallback to raw content
    
    def get_content_variables(self, content_asset: ContentAsset) -> List[Dict[str, Any]]:
        """Get available variables for a content asset"""
        
        variables = []
        for var_name in content_asset.template_variables:
            var_info = {
                'name': var_name,
                'required': True,  # Could be enhanced with schema validation
                'type': 'string',  # Could be enhanced with schema validation
                'description': f"Variable: {var_name}"
            }
            
            # Get type and description from schema if available
            if content_asset.variable_schema and var_name in content_asset.variable_schema:
                schema_info = content_asset.variable_schema[var_name]
                var_info.update(schema_info)
            
            variables.append(var_info)
        
        return variables
    
    # Analytics and Reporting
    
    def get_content_analytics(self, content_asset: ContentAsset) -> Dict[str, Any]:
        """Get usage analytics for a content asset"""
        
        usage_records = ContentUsage.objects.filter(content_asset=content_asset)
        
        total_executions = sum(record.execution_count for record in usage_records)
        avg_success_rate = usage_records.aggregate(
            avg_rate=Avg('success_rate')
        )['avg_rate'] or 0
        
        workflows_using = usage_records.count()
        last_used = max(
            (record.last_execution for record in usage_records if record.last_execution),
            default=None
        )
        
        return {
            'total_usage_count': content_asset.usage_count,
            'total_executions': total_executions,
            'workflows_using_count': workflows_using,
            'average_success_rate': round(avg_success_rate, 2),
            'last_used_at': last_used,
            'performance_score': content_asset.performance_score,
            'usage_by_workflow': [
                {
                    'workflow_id': record.workflow_id,
                    'workflow_name': record.workflow_name,
                    'execution_count': record.execution_count,
                    'success_rate': record.success_rate,
                    'last_execution': record.last_execution
                }
                for record in usage_records
            ]
        }
    
    def get_library_analytics(self, library: ContentLibrary) -> Dict[str, Any]:
        """Get analytics for a content library"""
        
        assets = ContentAsset.objects.filter(library=library, is_current_version=True)
        
        total_assets = assets.count()
        total_usage = sum(asset.usage_count for asset in assets)
        
        assets_by_type = assets.values('content_type').annotate(count=Count('id'))
        assets_by_status = assets.values('status').annotate(count=Count('id'))
        
        return {
            'total_assets': total_assets,
            'total_usage_count': total_usage,
            'assets_by_type': list(assets_by_type),
            'assets_by_status': list(assets_by_status),
            'most_used_assets': [
                {
                    'id': str(asset.id),
                    'name': asset.name,
                    'usage_count': asset.usage_count,
                    'content_type': asset.content_type
                }
                for asset in assets.order_by('-usage_count')[:10]
            ]
        }
    
    # Helper Methods
    
    def _extract_template_variables(self, content: str) -> List[str]:
        """Extract template variables from content (simple {{variable}} format)"""
        import re
        
        pattern = r'\{\{([^}]+)\}\}'
        variables = re.findall(pattern, content)
        return list(set(var.strip() for var in variables))
    
    def _validate_file_extension(self, filename: str, content_type: str) -> bool:
        """Validate file extension against content type"""
        
        if content_type not in self.supported_extensions:
            return True  # Allow if no specific restrictions
        
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
        return file_ext in self.supported_extensions[content_type]
    
    def _extract_file_metadata(self, file: UploadedFile, content_type: str) -> Dict[str, Any]:
        """Extract metadata from uploaded files"""
        
        metadata = {
            'original_filename': file.name,
            'size': file.size,
            'content_type': getattr(file, 'content_type', '')
        }
        
        # Could be enhanced with image dimensions, video duration, etc.
        # For now, just basic metadata
        
        return metadata
    
    def _add_tags_to_asset(self, asset: ContentAsset, tag_names: List[str], user: User):
        """Add tags to a content asset"""
        
        for tag_name in tag_names:
            tag, created = ContentTag.objects.get_or_create(
                name=tag_name.lower().strip(),
                defaults={'created_by': user}
            )
            asset.tags.add(tag)
            
            if not created:
                tag.usage_count += 1
                tag.save(update_fields=['usage_count'])


# Global content manager instance
content_manager = ContentManager()