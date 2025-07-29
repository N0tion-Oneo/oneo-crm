"""
Relationship query engine with recursive graph traversal
"""
from typing import List, Dict, Any, Optional, Set, Tuple
from django.db import connection, transaction
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.utils import timezone
from pipelines.models import Pipeline, Record
from .models import Relationship, RelationshipType, RelationshipPath
from .permissions import RelationshipPermissionManager
import json
import hashlib
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class RelationshipQueryManager:
    """Manages complex relationship queries and traversal"""
    
    def __init__(self, user: User):
        self.user = user
        self.permission_manager = RelationshipPermissionManager(user)
        self.cache_ttl = 300  # 5 minutes
    
    def get_related_records(
        self,
        source_pipeline_id: int,
        source_record_id: int,
        relationship_types: Optional[List[int]] = None,
        max_depth: int = 1,
        direction: str = 'both',  # 'forward', 'reverse', 'both'
        include_paths: bool = False,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get related records with permission filtering"""
        
        cache_key = self._generate_cache_key(
            'related_records',
            source_pipeline_id,
            source_record_id,
            relationship_types,
            max_depth,
            direction,
            limit
        )
        
        result = cache.get(cache_key)
        if result is not None:
            return result
        
        # Build and execute query
        try:
            result = self._execute_traversal_query(
                source_pipeline_id=source_pipeline_id,
                source_record_id=source_record_id,
                relationship_types=relationship_types,
                max_depth=max_depth,
                direction=direction,
                include_paths=include_paths,
                limit=limit
            )
            
            # Filter results based on permissions
            result = self._filter_results_by_permissions(result)
            
            cache.set(cache_key, result, self.cache_ttl)
            return result
            
        except Exception as e:
            logger.error(f"Error in relationship query: {e}")
            return {
                'relationships': [],
                'records': [],
                'total_count': 0,
                'max_depth_reached': 0,
                'error': str(e)
            }
    
    def find_shortest_path(
        self,
        source_pipeline_id: int,
        source_record_id: int,
        target_pipeline_id: int,
        target_record_id: int,
        max_depth: int = 5
    ) -> Optional[Dict[str, Any]]:
        """Find shortest path between two records"""
        
        cache_key = self._generate_cache_key(
            'shortest_path',
            source_pipeline_id,
            source_record_id,
            target_pipeline_id,
            target_record_id,
            max_depth
        )
        
        result = cache.get(cache_key)
        if result is not None:
            return result
        
        # Check if path already computed and cached in RelationshipPath
        try:
            cached_path = RelationshipPath.objects.filter(
                source_pipeline_id=source_pipeline_id,
                source_record_id=source_record_id,
                target_pipeline_id=target_pipeline_id,
                target_record_id=target_record_id
            ).order_by('path_length').first()
            
            if cached_path and not cached_path.is_expired():
                result = self._convert_path_to_result(cached_path)
                cache.set(cache_key, result, self.cache_ttl)
                return result
                
        except Exception as e:
            logger.warning(f"Error checking cached path: {e}")
        
        # Compute path using recursive CTE
        try:
            result = self._compute_shortest_path(
                source_pipeline_id,
                source_record_id,
                target_pipeline_id,
                target_record_id,
                max_depth
            )
            
            # Cache the computed path
            if result and result.get('found') and result.get('path'):
                self._cache_computed_path(result)
            
            cache.set(cache_key, result, self.cache_ttl)
            return result
            
        except Exception as e:
            logger.error(f"Error computing shortest path: {e}")
            return {'found': False, 'path_length': None, 'path': None, 'error': str(e)}
    
    def _execute_traversal_query(
        self,
        source_pipeline_id: int,
        source_record_id: int,
        relationship_types: Optional[List[int]],
        max_depth: int,
        direction: str,
        include_paths: bool,
        limit: Optional[int]
    ) -> Dict[str, Any]:
        """Execute recursive traversal query using PostgreSQL CTE"""
        
        with connection.cursor() as cursor:
            # Base query parameters
            params = [source_pipeline_id, source_record_id]
            
            # Build relationship type filter
            type_filter = ""
            if relationship_types:
                type_placeholders = ','.join(['%s'] * len(relationship_types))
                type_filter = f"AND r.relationship_type_id IN ({type_placeholders})"
                params.extend(relationship_types)
            
            # Build direction conditions
            forward_condition = """
                r.source_pipeline_id = %s 
                AND r.source_record_id = %s
                AND r.is_deleted = FALSE
                AND r.status = 'active'
            """
            
            reverse_condition = """
                r.target_pipeline_id = %s 
                AND r.target_record_id = %s
                AND r.is_deleted = FALSE
                AND r.status = 'active'
                AND rt.is_bidirectional = TRUE
            """
            
            # Recursive CTE for traversal
            if direction == 'forward':
                direction_sql = forward_condition
                params_for_direction = params[:2]  # Only source params
            elif direction == 'reverse':
                direction_sql = reverse_condition
                params_for_direction = params[:2]  # Only source params
            else:  # both
                direction_sql = f"({forward_condition}) OR ({reverse_condition})"
                params_for_direction = params[:2] + params[:2]  # Both source params twice
            
            query = f"""
            WITH RECURSIVE relationship_traversal AS (
                -- Base case: direct relationships
                SELECT 
                    r.id as relationship_id,
                    r.relationship_type_id,
                    CASE 
                        WHEN r.source_pipeline_id = %s AND r.source_record_id = %s 
                        THEN r.source_pipeline_id
                        ELSE r.target_pipeline_id
                    END as source_pipeline_id,
                    CASE 
                        WHEN r.source_pipeline_id = %s AND r.source_record_id = %s 
                        THEN r.source_record_id
                        ELSE r.target_record_id
                    END as source_record_id,
                    CASE 
                        WHEN r.source_pipeline_id = %s AND r.source_record_id = %s 
                        THEN r.target_pipeline_id
                        ELSE r.source_pipeline_id
                    END as target_pipeline_id,
                    CASE 
                        WHEN r.source_pipeline_id = %s AND r.source_record_id = %s 
                        THEN r.target_record_id
                        ELSE r.source_record_id
                    END as target_record_id,
                    rt.forward_label,
                    rt.reverse_label,
                    1 as depth,
                    ARRAY[r.id] as path_relationships,
                    ARRAY[r.relationship_type_id] as path_types,
                    r.strength as path_strength,
                    CASE 
                        WHEN r.source_pipeline_id = %s AND r.source_record_id = %s 
                        THEN 'forward'
                        ELSE 'reverse'
                    END as direction
                FROM relationships_relationship r
                JOIN relationships_relationshiptype rt ON r.relationship_type_id = rt.id
                WHERE ({direction_sql})
                  {type_filter}
                
                UNION ALL
                
                -- Recursive case: follow relationships
                SELECT 
                    r.id as relationship_id,
                    r.relationship_type_id,
                    rt.source_pipeline_id,
                    rt.source_record_id,
                    CASE 
                        WHEN r.source_pipeline_id = rt.target_pipeline_id AND r.source_record_id = rt.target_record_id
                        THEN r.target_pipeline_id
                        ELSE r.source_pipeline_id
                    END as target_pipeline_id,
                    CASE 
                        WHEN r.source_pipeline_id = rt.target_pipeline_id AND r.source_record_id = rt.target_record_id
                        THEN r.target_record_id
                        ELSE r.source_record_id
                    END as target_record_id,
                    rtype.forward_label,
                    rtype.reverse_label,
                    rt.depth + 1,
                    rt.path_relationships || r.id,
                    rt.path_types || r.relationship_type_id,
                    rt.path_strength * r.strength,
                    CASE 
                        WHEN r.source_pipeline_id = rt.target_pipeline_id AND r.source_record_id = rt.target_record_id
                        THEN 'forward'
                        ELSE 'reverse'
                    END as direction
                FROM relationships_relationship r
                JOIN relationships_relationshiptype rtype ON r.relationship_type_id = rtype.id
                JOIN relationship_traversal rt ON (
                    (r.source_pipeline_id = rt.target_pipeline_id AND r.source_record_id = rt.target_record_id) OR
                    (r.target_pipeline_id = rt.target_pipeline_id AND r.target_record_id = rt.target_record_id)
                )
                WHERE rt.depth < %s
                  AND r.is_deleted = FALSE
                  AND r.status = 'active'
                  AND r.id != ALL(rt.path_relationships)  -- Prevent cycles
                  {type_filter}
            )
            SELECT 
                rt.*,
                sp.name as source_pipeline_name,
                tp.name as target_pipeline_name,
                sr.title as source_record_title,
                tr.title as target_record_title,
                sr.data as source_record_data,
                tr.data as target_record_data
            FROM relationship_traversal rt
            JOIN pipelines_pipeline sp ON rt.source_pipeline_id = sp.id
            JOIN pipelines_pipeline tp ON rt.target_pipeline_id = tp.id
            LEFT JOIN pipelines_record sr ON rt.source_pipeline_id = sr.pipeline_id AND rt.source_record_id = sr.id AND sr.is_deleted = FALSE
            LEFT JOIN pipelines_record tr ON rt.target_pipeline_id = tr.pipeline_id AND rt.target_record_id = tr.id AND tr.is_deleted = FALSE
            ORDER BY rt.depth, rt.path_strength DESC
            """
            
            # Add limit if specified
            if limit:
                query += f" LIMIT {limit}"
            
            # Prepare all parameters
            query_params = (
                params_for_direction + params_for_direction + params_for_direction + params_for_direction + params_for_direction +  # For CASE conditions
                [max_depth]  # For depth limit
            )
            
            if relationship_types:
                query_params = list(query_params) + relationship_types  # Add type filter params again for recursive part
            
            cursor.execute(query, query_params)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        return self._organize_traversal_results(results, include_paths)
    
    def _compute_shortest_path(
        self,
        source_pipeline_id: int,
        source_record_id: int,
        target_pipeline_id: int,
        target_record_id: int,
        max_depth: int
    ) -> Dict[str, Any]:
        """Compute shortest path using bidirectional BFS"""
        
        with connection.cursor() as cursor:
            query = """
            WITH RECURSIVE path_search AS (
                -- Forward search from source
                SELECT 
                    %s as search_pipeline_id,
                    %s as search_record_id,
                    r.target_pipeline_id as current_pipeline_id,
                    r.target_record_id as current_record_id,
                    1 as depth,
                    ARRAY[r.id] as path_relationships,
                    'forward' as search_direction
                FROM relationships_relationship r
                WHERE r.source_pipeline_id = %s 
                  AND r.source_record_id = %s
                  AND r.is_deleted = FALSE
                  AND r.status = 'active'
                
                UNION ALL
                
                -- Continue forward search
                SELECT 
                    ps.search_pipeline_id,
                    ps.search_record_id,
                    r.target_pipeline_id,
                    r.target_record_id,
                    ps.depth + 1,
                    ps.path_relationships || r.id,
                    ps.search_direction
                FROM path_search ps
                JOIN relationships_relationship r ON (
                    r.source_pipeline_id = ps.current_pipeline_id AND 
                    r.source_record_id = ps.current_record_id
                )
                WHERE ps.depth < %s
                  AND r.is_deleted = FALSE
                  AND r.status = 'active'
                  AND r.id != ALL(ps.path_relationships)
            )
            SELECT * FROM path_search 
            WHERE current_pipeline_id = %s AND current_record_id = %s
            ORDER BY depth
            LIMIT 1
            """
            
            cursor.execute(query, [
                source_pipeline_id, source_record_id,  # search identifiers
                source_pipeline_id, source_record_id,  # starting point
                max_depth,  # depth limit
                target_pipeline_id, target_record_id   # target
            ])
            
            result = cursor.fetchone()
            
            if result:
                columns = [col[0] for col in cursor.description]
                path_data = dict(zip(columns, result))
                
                return {
                    'found': True,
                    'path_length': path_data['depth'],
                    'path_relationships': path_data['path_relationships'],
                    'path': self._reconstruct_path_details(path_data['path_relationships'])
                }
            
            return {'found': False, 'path_length': None, 'path': None}
    
    def _filter_results_by_permissions(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Filter query results based on user permissions"""
        if not results.get('relationships'):
            return results
        
        filtered_relationships = []
        
        for rel_data in results['relationships']:
            relationship_type_id = rel_data.get('relationship_type_id')
            direction = rel_data.get('direction', 'forward')
            
            try:
                relationship_type = RelationshipType.objects.get(id=relationship_type_id)
            except RelationshipType.DoesNotExist:
                continue
            
            # Check traversal permission
            if not self.permission_manager.can_traverse_relationship(relationship_type, direction):
                continue
            
            # Filter target record fields based on permissions
            target_pipeline_id = rel_data.get('target_pipeline_id')
            if target_pipeline_id:
                visible_fields = self.permission_manager.get_visible_fields_through_relationship(
                    relationship_type, target_pipeline_id
                )
                
                # Apply field filtering to target record data
                if rel_data.get('target_record_data'):
                    filtered_data = {}
                    for field_name, field_value in rel_data['target_record_data'].items():
                        if visible_fields.get(field_name, True):  # Default to visible
                            filtered_data[field_name] = field_value
                    rel_data['target_record_data'] = filtered_data
            
            filtered_relationships.append(rel_data)
        
        results['relationships'] = filtered_relationships
        results['total_count'] = len(filtered_relationships)
        
        return results
    
    def _organize_traversal_results(
        self, 
        raw_results: List[Dict[str, Any]], 
        include_paths: bool
    ) -> Dict[str, Any]:
        """Organize raw query results into structured format"""
        
        relationships = []
        records_by_id = {}
        
        for row in raw_results:
            # Skip rows with null records (LEFT JOIN may produce these)
            if not row.get('target_record_title'):
                continue
                
            # Build relationship info
            rel_info = {
                'relationship_id': row['relationship_id'],
                'relationship_type_id': row['relationship_type_id'],
                'depth': row['depth'],
                'direction': row['direction'],
                'path_strength': float(row['path_strength']) if row['path_strength'] else 1.0,
                'source_pipeline_id': row['source_pipeline_id'],
                'source_record_id': row['source_record_id'],
                'target_pipeline_id': row['target_pipeline_id'],
                'target_record_id': row['target_record_id'],
                'source_record_title': row.get('source_record_title', ''),
                'target_record_title': row.get('target_record_title', ''),
                'target_record_data': row.get('target_record_data', {})
            }
            
            if include_paths:
                rel_info['path_relationships'] = row.get('path_relationships', [])
                rel_info['path_types'] = row.get('path_types', [])
            
            relationships.append(rel_info)
            
            # Collect unique records
            source_key = f"{row['source_pipeline_id']}:{row['source_record_id']}"
            target_key = f"{row['target_pipeline_id']}:{row['target_record_id']}"
            
            if source_key not in records_by_id and row.get('source_record_title'):
                records_by_id[source_key] = {
                    'pipeline_id': row['source_pipeline_id'],
                    'pipeline_name': row.get('source_pipeline_name', ''),
                    'record_id': row['source_record_id'],
                    'title': row.get('source_record_title', ''),
                    'data': row.get('source_record_data', {})
                }
            
            if target_key not in records_by_id and row.get('target_record_title'):
                records_by_id[target_key] = {
                    'pipeline_id': row['target_pipeline_id'],
                    'pipeline_name': row.get('target_pipeline_name', ''),
                    'record_id': row['target_record_id'],
                    'title': row.get('target_record_title', ''),
                    'data': row.get('target_record_data', {})
                }
        
        return {
            'relationships': relationships,
            'records': list(records_by_id.values()),
            'total_count': len(relationships),
            'max_depth_reached': max(rel['depth'] for rel in relationships) if relationships else 0
        }
    
    def _generate_cache_key(self, operation: str, *args) -> str:
        """Generate cache key for relationship queries"""
        key_parts = [f"rel_query:{self.user.id}", operation] + [str(arg) for arg in args]
        key_string = ":".join(key_parts)
        # Hash long keys to prevent cache key size issues
        if len(key_string) > 200:
            return hashlib.md5(key_string.encode()).hexdigest()
        return key_string
    
    def _cache_computed_path(self, path_result: Dict[str, Any]):
        """Cache computed path in RelationshipPath table"""
        try:
            if not path_result.get('found') or not path_result.get('path_relationships'):
                return
            
            # Extract path information
            path_relationships = path_result['path_relationships']
            path_length = path_result['path_length']
            
            # Get first and last relationships to determine endpoints
            first_rel = Relationship.objects.get(id=path_relationships[0])
            
            # Calculate expiration (24 hours from now)
            expires_at = timezone.now() + timezone.timedelta(hours=24)
            
            # Create or update path cache
            RelationshipPath.objects.update_or_create(
                source_pipeline=first_rel.source_pipeline,
                source_record_id=first_rel.source_record_id,
                target_pipeline=first_rel.target_pipeline,
                target_record_id=first_rel.target_record_id,
                path_length=path_length,
                defaults={
                    'path_relationships': path_relationships,
                    'path_types': [rel.relationship_type_id for rel in 
                                 Relationship.objects.filter(id__in=path_relationships)],
                    'path_strength': 1.0,  # Could calculate actual strength
                    'expires_at': expires_at
                }
            )
            
        except Exception as e:
            logger.warning(f"Error caching computed path: {e}")
    
    def _convert_path_to_result(self, cached_path: RelationshipPath) -> Dict[str, Any]:
        """Convert cached RelationshipPath to result format"""
        return {
            'found': True,
            'path_length': cached_path.path_length,
            'path_relationships': cached_path.path_relationships,
            'path': self._reconstruct_path_details(cached_path.path_relationships),
            'cached': True
        }
    
    def _reconstruct_path_details(self, relationship_ids: List[int]) -> List[Dict[str, Any]]:
        """Reconstruct detailed path information from relationship IDs"""
        if not relationship_ids:
            return []
        
        try:
            relationships = Relationship.objects.filter(
                id__in=relationship_ids,
                is_deleted=False
            ).select_related('relationship_type', 'source_pipeline', 'target_pipeline')
            
            path_details = []
            for rel in relationships:
                path_details.append({
                    'relationship_id': rel.id,
                    'relationship_type': rel.relationship_type.name,
                    'forward_label': rel.relationship_type.forward_label,
                    'reverse_label': rel.relationship_type.reverse_label,
                    'source_pipeline': rel.source_pipeline.name,
                    'source_record_id': rel.source_record_id,
                    'target_pipeline': rel.target_pipeline.name,
                    'target_record_id': rel.target_record_id,
                    'strength': float(rel.strength)
                })
            
            return path_details
            
        except Exception as e:
            logger.error(f"Error reconstructing path details: {e}")
            return []