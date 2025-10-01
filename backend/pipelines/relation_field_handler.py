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
        self.target_pipeline_id = self.config.get('target_pipeline_id') or self.config.get('target_pipeline')
        self.allow_multiple = self.config.get('allow_multiple', False)
        self.display_field = self.config.get('display_field', 'title')

        # Bidirectional field support
        self.is_auto_generated = field.is_auto_generated
        self.reverse_field_id = field.reverse_field_id
        self.is_reverse_field = self.config.get('is_reverse_field', False)

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

        # For auto-generated reverse fields, use the original field's RelationshipType
        if self.is_auto_generated and self.is_reverse_field:
            original_field = self.get_original_field()
            if original_field:
                # Create handler for original field and get its relationship type
                original_handler = RelationFieldHandler(original_field)
                return original_handler.relationship_type

        # For manually created reverse fields (old fields marked as reverse), use original field's RelationshipType
        if self.is_reverse_field and self.reverse_field_id:
            try:
                original_field = Field.objects.get(id=self.reverse_field_id, is_deleted=False)
                # Create handler for original field and get its relationship type
                original_handler = RelationFieldHandler(original_field)
                return original_handler.relationship_type
            except Field.DoesNotExist:
                pass

        # Generate unique slug for this field (for original fields)
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

    def get_reverse_field(self) -> Optional[Field]:
        """Get the reverse field for this bidirectional relation"""
        if self.reverse_field_id:
            try:
                return Field.objects.get(id=self.reverse_field_id, is_deleted=False)
            except Field.DoesNotExist:
                return None
        return None

    def get_original_field(self) -> Optional[Field]:
        """Get the original field if this is an auto-generated reverse field"""
        if self.is_auto_generated and 'original_field_id' in (self.field.auto_reverse_config or {}):
            try:
                original_field_id = self.field.auto_reverse_config['original_field_id']
                return Field.objects.get(id=original_field_id, is_deleted=False)
            except Field.DoesNotExist:
                return None
        return None

    def get_bidirectional_relationships(self, record: Record, include_deleted: bool = True) -> List[Relationship]:
        """
        Get relationships for bidirectional fields - includes both directions
        Now that reverse fields share the same RelationshipType, we can use standard querying

        Args:
            record: The record to find relationships for
            include_deleted: Whether to include soft-deleted relationships
        """
        # All fields (original and reverse) now use the same RelationshipType,
        # so we can use the standard bidirectional query
        return self.get_relationships(record, include_deleted=include_deleted)

    def get_relationships(self, record: Record, include_deleted: bool = True) -> List[Relationship]:
        """
        Get all relationships for this field and record
        Uses bidirectional query to find relationships in both directions

        Args:
            record: The record to find relationships for
            include_deleted: Whether to include soft-deleted relationships
                           True for internal operations (resurrection)
                           False for display/serialization
        """
        manager = Relationship.all_objects if include_deleted else Relationship.objects
        return manager.filter(
            Q(
                source_record_id=record.id,
                source_pipeline_id=self.pipeline.id,
                relationship_type=self.relationship_type
            ) | Q(
                target_record_id=record.id,
                target_pipeline_id=self.pipeline.id,
                relationship_type=self.relationship_type
            )
        ).select_related('source_pipeline', 'target_pipeline', 'relationship_type')

    def get_related_ids(self, record: Record) -> Union[List[int], int, None]:
        """Get related record IDs for serialization - supports bidirectional fields"""
        relationships = self.get_bidirectional_relationships(record, include_deleted=False)

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

    def get_related_records_with_display(self, record: Record) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
        """Get related records with display values for API serialization"""
        relationships = self.get_bidirectional_relationships(record, include_deleted=False)

        if not relationships:
            return [] if self.allow_multiple else None

        related_records = []
        for rel in relationships:
            # Determine which record is the target
            if rel.source_record_id == record.id:
                target_record_id = rel.target_record_id
                target_pipeline_id = rel.target_pipeline_id
            else:
                target_record_id = rel.source_record_id
                target_pipeline_id = rel.source_pipeline_id

            try:
                # Get the target record
                target_record = Record.objects.get(
                    id=target_record_id,
                    pipeline_id=target_pipeline_id,
                    is_deleted=False
                )

                # Get display value using configured display field
                display_value = target_record.data.get(self.display_field)
                if not display_value:
                    # Try alternate field name matching (e.g., "Company Name" vs "company_name")
                    alt_field = self.display_field.lower().replace(' ', '_')
                    display_value = target_record.data.get(alt_field)

                if not display_value:
                    display_value = target_record.title or f"Record #{target_record_id}"

                related_records.append({
                    'id': target_record_id,
                    'display_value': display_value
                })

            except Record.DoesNotExist:
                # Skip deleted or missing records
                continue

        # Return based on cardinality
        if self.allow_multiple:
            return related_records
        else:
            return related_records[0] if related_records else None


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
        # Manager includes soft-deleted relationships for proper resurrection
        current_relationships = Relationship.all_objects.filter(
            relationship_type_id=self.relationship_type.id
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

        # Special case: if new_target_ids is empty, we're clearing the field
        # In this case, we should soft-delete ALL active relationships, not just those in current_target_ids
        if len(new_target_ids) == 0 and len(current_target_ids) > 0:
            print(f"   → Clearing field - soft-deleting all active relationships")
            # Find all active relationships for this field (exclude already soft-deleted)
            active_relationships = current_relationships.filter(is_deleted=False)
            from django.utils import timezone

            for rel in active_relationships:
                rel.is_deleted = True
                rel.deleted_by = user
                rel.deleted_at = timezone.now()
                rel.save()
                results['removed'] += 1
                print(f"      ✓ Soft deleted active relationship {rel.id}")

        elif to_remove:
            print(f"   → Removing specific relationships for: {list(to_remove)}")
            from django.utils import timezone

            for target_id in to_remove:
                if target_id in relationships_map:
                    rel = relationships_map[target_id]
                    if not rel.is_deleted:  # Only delete if not already soft-deleted
                        rel.is_deleted = True
                        rel.deleted_by = user
                        rel.deleted_at = timezone.now()
                        rel.save()
                        results['removed'] += 1
                        print(f"      ✓ Soft deleted relationship to {target_id}")
                    else:
                        print(f"      → Relationship to {target_id} already soft-deleted")

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
                existing = Relationship.all_objects.filter(
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
                        print(f"   ✓ Resurrected bidirectional relationship to {target_id}")
                    else:
                        results['unchanged'] += 1
                        print(f"   → Bidirectional relationship already exists to {target_id}")
                else:
                    # Create new relationship with consistent direction for bidirectional relationships
                    # CRITICAL: For bidirectional relationships, always use consistent source/target ordering
                    # to avoid creating duplicate records. Use lower record ID as source for consistency.

                    # Determine consistent direction based on record IDs (lower ID always as source)
                    if record.id < target_id:
                        # Current record has lower ID - use as source
                        source_pipeline_id = self.pipeline.id
                        source_record_id = record.id
                        target_pipeline_id = self.target_pipeline_id
                        target_record_id = target_id
                    else:
                        # Target record has lower ID - use as source
                        source_pipeline_id = self.target_pipeline_id
                        source_record_id = target_id
                        target_pipeline_id = self.pipeline.id
                        target_record_id = record.id

                    print(f"   → Creating bidirectional relationship: {source_record_id} → {target_record_id}")

                    print(f"   🔄 CREATING relationship: {source_record_id} → {target_record_id} (type: {self.relationship_type.id})")

                    relationship, created = Relationship.objects.get_or_create(
                        relationship_type_id=self.relationship_type.id,
                        source_pipeline_id=source_pipeline_id,
                        source_record_id=source_record_id,
                        target_pipeline_id=target_pipeline_id,
                        target_record_id=target_record_id,
                        defaults={
                            'created_by': user,
                            'strength': 1.0,
                            'is_deleted': False
                        }
                    )

                    if created:
                        results['created'] += 1
                        print(f"   ✅ CREATED NEW relationship ID {relationship.id}: {source_record_id} → {target_record_id}")
                        print(f"   📡 This should trigger post_save signal for Relationship {relationship.id}")
                    else:
                        # Shouldn't happen due to our checks, but handle it
                        if relationship.is_deleted:
                            print(f"   🔄 RESURRECTING relationship ID {relationship.id}: {source_record_id} → {target_record_id}")
                            relationship.is_deleted = False
                            relationship.deleted_by = None
                            relationship.deleted_at = None
                            relationship.save()
                            results['created'] += 1
                            print(f"   ✅ RESURRECTED relationship ID {relationship.id}: {source_record_id} → {target_record_id}")
                            print(f"   📡 This should trigger post_save signal for Relationship {relationship.id}")
                        else:
                            results['unchanged'] += 1
                            print(f"   ➡️ Relationship ID {relationship.id} already existed: {source_record_id} → {target_record_id}")

            except Record.DoesNotExist:
                print(f"   ⚠️ Target record {target_id} not found")
            except Exception as e:
                print(f"   ❌ Error creating relationship to {target_id}: {e}")

        # Handle unchanged relationships - check if any are soft-deleted and need resurrection
        unchanged = new_target_ids & current_target_ids
        for target_id in unchanged:
            if target_id in relationships_map:
                rel = relationships_map[target_id]
                if rel.is_deleted:
                    # Resurrect soft-deleted relationship
                    rel.is_deleted = False
                    rel.deleted_by = None
                    rel.deleted_at = None
                    rel.save()
                    results['created'] += 1
                    results['unchanged'] -= 1 if results['unchanged'] > 0 else 0
                    print(f"   ✓ Resurrected unchanged relationship to {target_id}")
                else:
                    print(f"   → Unchanged relationship to {target_id} already active")

        results['unchanged'] = len(unchanged) - results.get('resurrected', 0)

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