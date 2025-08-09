"""
USER Field Handler - Bridge between field system and relationships system
"""
from typing import List, Dict, Any, Optional
from django.contrib.auth import get_user_model
from relationships.models import Relationship, RelationshipType
from pipelines.models import Field, Record, Pipeline

User = get_user_model()


class UserFieldHandler:
    """
    Handles USER field operations by bridging with the relationships system
    """
    
    def __init__(self, field: Field):
        self.field = field
        self.pipeline = field.pipeline
        self.field_config = field.field_config or {}
        
        # Get configuration
        self.relationship_type = self.field_config.get('relationship_type', 'assigned_to')
        self.allow_multiple = self.field_config.get('allow_multiple', True)
        self.default_role = self.field_config.get('default_role', 'primary')
    
    def get_assigned_users(self, record: Record) -> List[Dict[str, Any]]:
        """Get users assigned to this record via this field"""
        try:
            rel_type = RelationshipType.objects.get(slug=self.relationship_type)
            
            relationships = Relationship.objects.filter(
                relationship_type=rel_type,
                target_pipeline=self.pipeline,
                target_record_id=record.id,
                user__isnull=False,
                is_deleted=False
            ).select_related('user')
            
            users = []
            for rel in relationships:
                users.append({
                    'user_id': rel.user.id,
                    'name': rel.user.get_full_name() or rel.user.email,
                    'email': rel.user.email,
                    'role': rel.role,
                    'avatar': getattr(rel.user, 'avatar', None),
                    'relationship_id': rel.id
                })
            
            return users
            
        except RelationshipType.DoesNotExist:
            return []
    
    def assign_users(self, record: Record, user_assignments: List[Dict[str, Any]], 
                    assigned_by: User) -> Dict[str, Any]:
        """Assign users to this record via relationships system"""
        try:
            rel_type = RelationshipType.objects.get(slug=self.relationship_type)
            
            if not rel_type.allow_user_relationships:
                raise ValueError(f"Relationship type '{self.relationship_type}' doesn't allow user assignments")
            
            # Get current assignments
            current_relationships = Relationship.objects.filter(
                relationship_type=rel_type,
                target_pipeline=self.pipeline,
                target_record_id=record.id,
                user__isnull=False,
                is_deleted=False
            )
            
            current_user_ids = set(current_relationships.values_list('user_id', flat=True))
            new_user_ids = set()
            
            results = {
                'assigned': [],
                'updated': [],
                'errors': []
            }
            
            # Process new assignments
            for assignment in user_assignments:
                try:
                    user_id = int(assignment['user_id'])
                    role = assignment.get('role', self.default_role)
                    
                    # Validate user exists
                    user = User.objects.get(id=user_id)
                    new_user_ids.add(user_id)
                    
                    # Check if already assigned
                    existing = current_relationships.filter(user_id=user_id).first()
                    
                    if existing:
                        # Update role if changed
                        if existing.role != role:
                            existing.role = role
                            existing.save(update_fields=['role'])
                            results['updated'].append({
                                'user_id': user_id,
                                'name': user.get_full_name() or user.email,
                                'old_role': existing.role,
                                'new_role': role
                            })
                    else:
                        # Create new assignment
                        relationship = Relationship.objects.create(
                            relationship_type=rel_type,
                            user=user,
                            target_pipeline=self.pipeline,
                            target_record_id=record.id,
                            role=role,
                            created_by=assigned_by
                        )
                        results['assigned'].append({
                            'user_id': user_id,
                            'name': user.get_full_name() or user.email,
                            'role': role,
                            'relationship_id': relationship.id
                        })
                    
                    # Check multiple assignment constraint
                    if not self.allow_multiple and len(new_user_ids) > 1:
                        raise ValueError("This field only allows one user assignment")
                        
                except User.DoesNotExist:
                    results['errors'].append(f"User with ID {user_id} not found")
                except Exception as e:
                    results['errors'].append(f"Error assigning user {user_id}: {str(e)}")
            
            # Remove unassigned users (not in new list)
            users_to_remove = current_user_ids - new_user_ids
            if users_to_remove:
                removed_relationships = current_relationships.filter(user_id__in=users_to_remove)
                for rel in removed_relationships:
                    rel.delete(soft=True)
                    rel.deleted_by = assigned_by
                    rel.save(update_fields=['deleted_by'])
                
                results['removed'] = list(users_to_remove)
            
            return results
            
        except RelationshipType.DoesNotExist:
            return {
                'assigned': [],
                'updated': [],
                'errors': [f"Relationship type '{self.relationship_type}' not found"]
            }
        except Exception as e:
            return {
                'assigned': [],
                'updated': [],
                'errors': [str(e)]
            }
    
    def remove_user(self, record: Record, user_id: int, removed_by: User) -> bool:
        """Remove a user assignment"""
        try:
            rel_type = RelationshipType.objects.get(slug=self.relationship_type)
            
            relationship = Relationship.objects.get(
                relationship_type=rel_type,
                target_pipeline=self.pipeline,
                target_record_id=record.id,
                user_id=user_id,
                is_deleted=False
            )
            
            relationship.delete(soft=True)
            relationship.deleted_by = removed_by
            relationship.save(update_fields=['deleted_by'])
            
            return True
            
        except (RelationshipType.DoesNotExist, Relationship.DoesNotExist):
            return False
    
    def change_user_role(self, record: Record, user_id: int, new_role: str,
                        changed_by: User) -> bool:
        """Change a user's role in this assignment"""
        try:
            rel_type = RelationshipType.objects.get(slug=self.relationship_type)
            
            relationship = Relationship.objects.get(
                relationship_type=rel_type,
                target_pipeline=self.pipeline,
                target_record_id=record.id,
                user_id=user_id,
                is_deleted=False
            )
            
            relationship.role = new_role
            relationship.save(update_fields=['role'])
            
            return True
            
        except (RelationshipType.DoesNotExist, Relationship.DoesNotExist):
            return False


def get_user_field_handler(field: Field) -> Optional[UserFieldHandler]:
    """Factory function to create USER field handler"""
    if field.field_type == 'user':
        return UserFieldHandler(field)
    return None


def handle_user_field_update(record: Record, field: Field, user_assignments: Any, 
                            user: User) -> Dict[str, Any]:
    """
    Handle USER field updates by delegating to relationships system
    
    This function should be called when a USER field is updated via the API
    """
    handler = get_user_field_handler(field)
    if not handler:
        return {'errors': ['Field is not a USER field']}
    
    if not user_assignments:
        # Remove all current assignments
        current_users = handler.get_assigned_users(record)
        for current_user in current_users:
            handler.remove_user(record, current_user['user_id'], user)
        return {'removed': len(current_users), 'assigned': [], 'updated': [], 'errors': []}
    
    # Convert different input formats to standard format
    assignments = []
    
    if isinstance(user_assignments, int):
        # Single user ID
        assignments = [{'user_id': user_assignments, 'role': handler.default_role}]
    elif isinstance(user_assignments, list):
        for item in user_assignments:
            if isinstance(item, int):
                assignments.append({'user_id': item, 'role': handler.default_role})
            elif isinstance(item, dict):
                assignments.append(item)
    elif isinstance(user_assignments, dict):
        if 'user_assignments' in user_assignments:
            assignments = user_assignments['user_assignments']
        else:
            # Single assignment object
            assignments = [user_assignments]
    
    return handler.assign_users(record, assignments, user)