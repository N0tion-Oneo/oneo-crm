"""
Simplified Relation Field Handler - Bridge between relation fields and relationships
Implements proper bidirectional relationships with single record storage
"""
from typing import List, Dict, Any, Optional, Union
from django.db.models import Q
from django.contrib.auth import get_user_model
from relationships.models import Relationship, RelationshipType
from pipelines.models import Field, Record

User = get_user_model()


class RelationFieldHandler:
    """
    Handles relation field operations with proper bidirectional support
    - Single record storage (no duplicates)
    - Proper deletion handling
    - Clean bidirectional queries
    """

    def __init__(self, field: Field):
        """Initialize handler with field configuration"""
        self.field = field
        self.pipeline = field.pipeline

        # Parse field configuration
        self.config = field.field_config or {}
        self.target_pipeline_id = self.config.get('target_pipeline_id')
        self.allow_multiple = self.config.get('allow_multiple', False)
        self.display_field = self.config.get('display_field', 'title')

        # Lazy load relationship type
        self._relationship_type = None

    @property
    def relationship_type(self) -> RelationshipType:
        """Get or create the RelationshipType for this field"""
        if self._relationship_type is None:
            self._relationship_type = self._get_or_create_relationship_type()
        return self._relationship_type

    def _get_or_create_relationship_type(self) -> RelationshipType:
        """Get existing or create new RelationshipType"""
        # Generate unique slug for this field
        slug = f"{self.pipeline.slug}_{self.field.slug}"

        # Determine cardinality
        cardinality = 'many_to_many' if self.allow_multiple else 'one_to_many'

        # Get or create the relationship type
        rel_type, created = RelationshipType.objects.get_or_create(
            slug=slug,
            defaults={
                'name': f"{self.pipeline.name} - {self.field.name}",
                'forward_label': self.field.name,
                'reverse_label': f"{self.pipeline.name} (reverse)",
                'cardinality': cardinality,
                'is_bidirectional': True
            }
        )

        if created:
            print(f"✅ Created RelationshipType: {slug}")

        return rel_type

    def get_relationships(self, record: Record) -> List[Relationship]:
        """
        Get all relationships for this field and record
        Uses bidirectional query to find relationships in both directions
        """
        return Relationship.objects.filter(
            Q(
                source_record_id=record.id,
                source_pipeline=self.pipeline,
                relationship_type=self.relationship_type
            ) | Q(
                target_record_id=record.id,
                target_pipeline=self.pipeline,
                relationship_type=self.relationship_type
            ),
            is_deleted=False  # Only active relationships
        ).select_related('source_pipeline', 'target_pipeline', 'relationship_type')

    def get_related_ids(self, record: Record) -> Union[List[int], int, None]:
        """Get related record IDs for serialization"""
        relationships = self.get_relationships(record)

        # Collect IDs based on direction
        related_ids = []
        for rel in relationships:
            if rel.source_record_id == record.id:
                related_ids.append(rel.target_record_id)
            else:
                related_ids.append(rel.source_record_id)

        # Return based on cardinality
        if self.allow_multiple:
            return related_ids
        else:
            return related_ids[0] if related_ids else None

    def set_relationships(self, record: Record, target_ids: Any, user: Optional[User] = None) -> Dict[str, Any]:
        """
        Create/update relationships for this field
        CRITICAL: Properly handles bidirectional relationships with single records
        """
        print(f"🔵 set_relationships: record={record.id}, target_ids={target_ids}, type={type(target_ids)}")

        # Normalize input to list - CRITICAL for proper deletion
        if target_ids is None or target_ids == '':
            target_ids = []
            print("   → Normalized None/empty to []")
        elif not isinstance(target_ids, list):
            target_ids = [target_ids]
            print(f"   → Normalized single value to list: {target_ids}")

        # Filter out invalid values and convert to integers
        target_ids = [int(id) for id in target_ids if id is not None and str(id).isdigit()]
        print(f"   → Final target_ids: {target_ids}")

        # Enforce cardinality
        if not self.allow_multiple and len(target_ids) > 1:
            target_ids = target_ids[:1]

        # Get current relationships - check BOTH directions
        current_relationships = Relationship.objects.filter(
            relationship_type_id=self.relationship_type.id,
            is_deleted=False
        ).filter(
            Q(
                source_record_id=record.id,
                source_pipeline_id=self.pipeline.id
            ) | Q(
                target_record_id=record.id,
                target_pipeline_id=self.pipeline.id
            )
        )

        print(f"   → Found {current_relationships.count()} current relationships")

        # Collect current target IDs from both directions
        current_target_ids = set()
        relationships_map = {}  # Map target_id to relationship for deletion

        for rel in current_relationships:
            if rel.source_record_id == record.id:
                target_id = rel.target_record_id
            else:
                target_id = rel.source_record_id

            current_target_ids.add(target_id)
            relationships_map[target_id] = rel

        new_target_ids = set(target_ids)

        print(f"   → Current: {list(current_target_ids)}, New: {list(new_target_ids)}")

        results = {
            'created': 0,
            'removed': 0,
            'unchanged': 0
        }

        # Remove relationships that are no longer needed
        to_remove = current_target_ids - new_target_ids
        if to_remove:
            print(f"   → Removing relationships for: {list(to_remove)}")
            from django.utils import timezone

            for target_id in to_remove:
                if target_id in relationships_map:
                    rel = relationships_map[target_id]
                    rel.is_deleted = True
                    rel.deleted_by = user
                    rel.deleted_at = timezone.now()
                    rel.save()
                    results['removed'] += 1
                    print(f"      ✓ Soft deleted relationship to {target_id}")

        # Add new relationships
        to_add = new_target_ids - current_target_ids
        for target_id in to_add:
            try:
                # Verify target record exists
                target_record = Record.objects.get(
                    id=target_id,
                    pipeline_id=self.target_pipeline_id,
                    is_deleted=False
                )

                # Check for existing relationship in BOTH directions (including soft-deleted)
                existing = Relationship.objects.filter(
                    relationship_type_id=self.relationship_type.id
                ).filter(
                    Q(
                        source_pipeline_id=self.pipeline.id,
                        source_record_id=record.id,
                        target_pipeline_id=self.target_pipeline_id,
                        target_record_id=target_id
                    ) | Q(
                        source_pipeline_id=self.target_pipeline_id,
                        source_record_id=target_id,
                        target_pipeline_id=self.pipeline.id,
                        target_record_id=record.id
                    )
                ).first()

                if existing:
                    if existing.is_deleted:
                        # Resurrect soft-deleted relationship
                        existing.is_deleted = False
                        existing.deleted_by = None
                        existing.deleted_at = None
                        existing.save()
                        results['created'] += 1
                        print(f"   ✓ Resurrected relationship to {target_id}")
                    else:
                        results['unchanged'] += 1
                        print(f"   → Relationship already exists to {target_id}")
                else:
                    # Create new relationship - use get_or_create for safety
                    relationship, created = Relationship.objects.get_or_create(
                        relationship_type_id=self.relationship_type.id,
                        source_pipeline_id=self.pipeline.id,
                        source_record_id=record.id,
                        target_pipeline_id=self.target_pipeline_id,
                        target_record_id=target_id,
                        defaults={
                            'created_by': user,
                            'strength': 1.0,
                            'is_deleted': False
                        }
                    )

                    if created:
                        results['created'] += 1
                        print(f"   ✓ Created relationship to {target_id}")
                    else:
                        # Shouldn't happen due to our checks, but handle it
                        if relationship.is_deleted:
                            relationship.is_deleted = False
                            relationship.deleted_by = None
                            relationship.deleted_at = None
                            relationship.save()
                            results['created'] += 1
                            print(f"   ✓ Resurrected existing relationship to {target_id}")
                        else:
                            results['unchanged'] += 1
                            print(f"   → Relationship already existed to {target_id}")

            except Record.DoesNotExist:
                print(f"   ⚠️ Target record {target_id} not found")
            except Exception as e:
                print(f"   ❌ Error creating relationship to {target_id}: {e}")

        # Count unchanged
        unchanged = new_target_ids & current_target_ids
        results['unchanged'] = len(unchanged)

        print(f"   → Results: {results}")
        return results


def sync_relation_field(record: Record, field: Field, value: Any, user: Optional[User] = None) -> Dict[str, Any]:
    """
    Sync a relation field value to the relationship system
    Main entry point for syncing relation fields when records are saved
    """
    if field.field_type != 'relation':
        return {'error': 'Field is not a relation field'}

    handler = RelationFieldHandler(field)
    return handler.set_relationships(record, value, user)