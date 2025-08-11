"""
Unified Record Operation Manager
Single entry point for ALL record operations to eliminate complex save() method
"""
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)
User = get_user_model()


class SaveResult:
    """Standardized result object for record save operations"""
    
    def __init__(self, success: bool, record=None, operation_id: Optional[str] = None, 
                 errors: List[str] = None, warnings: List[str] = None, 
                 metadata: Dict[str, Any] = None):
        self.success = success
        self.record = record
        self.operation_id = operation_id
        self.errors = errors or []
        self.warnings = warnings or []
        self.metadata = metadata or {}
        self.timestamp = timezone.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for API responses"""
        return {
            'success': self.success,
            'record_id': self.record.id if self.record else None,
            'operation_id': self.operation_id,
            'errors': self.errors,
            'warnings': self.warnings,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


class ChangeContext:
    """Context object for change detection and validation"""
    
    def __init__(self, is_new: bool, original_data: Dict[str, Any] = None,
                 changed_fields: Set[str] = None, validation_context: str = 'business_rules'):
        self.is_new = is_new
        self.original_data = original_data or {}
        self.changed_fields = changed_fields or set()
        self.validation_context = validation_context
        self.is_partial_update = len(self.changed_fields) <= 3 and len(self.changed_fields) > 0
        self.changed_field_slug = list(self.changed_fields)[0] if len(self.changed_fields) == 1 else None


class RecordUtils:
    """Utility operations for records"""
    
    @staticmethod
    def generate_title(record_data: Dict[str, Any], pipeline_name: str) -> str:
        """Generate display title from record data"""
        # Look for common title fields
        title_fields = ['name', 'title', 'subject', 'company', 'company_name', 'full_name', 'first_name']
        
        for field_slug in title_fields:
            if field_slug in record_data and record_data[field_slug]:
                return str(record_data[field_slug])[:500]
        
        # Fallback to first non-empty field
        for key, value in record_data.items():
            if value and isinstance(value, (str, int, float)):
                return f"{key}: {str(value)[:100]}"
        
        # Final fallback
        return f"{pipeline_name} Record #New"
    
    @staticmethod
    def get_changed_fields(old_data: Dict[str, Any], new_data: Dict[str, Any]) -> List[str]:
        """Get list of fields that changed"""
        changed_fields = []
        
        logger.info(f"🔍 CHANGE DETECTION: Comparing field data")
        logger.info(f"   📊 Old data keys: {list(old_data.keys())}")
        logger.info(f"   📊 New data keys: {list(new_data.keys())}")
        
        # Check for changed values
        for field_slug in set(old_data.keys()) | set(new_data.keys()):
            old_value = old_data.get(field_slug)
            new_value = new_data.get(field_slug)
            
            logger.info(f"   🔍 Field '{field_slug}':")
            logger.info(f"      📜 Old: {old_value}")
            logger.info(f"      📄 New: {new_value}")
            logger.info(f"      ⚖️  Equal: {old_value == new_value}")
            logger.info(f"      🔢 Types: {type(old_value)} vs {type(new_value)}")
            
            if old_value != new_value:
                logger.info(f"      ✅ CHANGED: Adding '{field_slug}' to changed fields")
                changed_fields.append(field_slug)
            else:
                logger.info(f"      ❌ NO CHANGE: Field '{field_slug}' unchanged")
        
        logger.info(f"🔍 CHANGE DETECTION RESULT: {len(changed_fields)} changed field(s): {changed_fields}")
        return changed_fields


class RecordChangeManager:
    """Handles change detection and validation logic"""
    
    def detect_changes(self, record) -> ChangeContext:
        """Detect what changed in a record and create context"""
        is_new = record.pk is None
        
        print(f"🟢 DATABASE STEP 1: Change Detection Starting")
        print(f"   🆔 Record ID: {record.pk or 'NEW'}")
        print(f"   📦 Data to save: {record.data}")
        print(f"   🏗️  Pipeline: {record.pipeline.name} (ID: {record.pipeline.id})")
        
        if record.data:
            print(f"   🔑 Data contains {len(record.data)} field(s): [{', '.join(record.data.keys())}]")
            print(f"   🔑 Data field types: {[(k, type(v).__name__, v) for k, v in record.data.items()]}")
            null_fields = [k for k, v in record.data.items() if v is None]
            if null_fields:
                print(f"   ⚠️  Data contains {len(null_fields)} NULL fields: [{', '.join(null_fields)}]")
        else:
            print(f"   ❌ No data provided to record!")
        
        # Get pipeline field definitions for reference
        pipeline_fields = list(record.pipeline.fields.all())
        print(f"   🏗️  Pipeline has {len(pipeline_fields)} field definitions:")
        for field in pipeline_fields:
            print(f"      🔧 {field.slug} ({field.field_type}): {field.name}")
        
        # Store original data for change detection
        original_data = {}
        changed_fields = set()
        
        if not is_new:
            try:
                # Import here to avoid circular import
                from .models import Record
                original_record = Record.objects.get(pk=record.pk)
                original_data = original_record.data.copy()
                print(f"   📊 Original data had {len(original_data)} fields")
                
                # 🔍 DEBUG: Enhanced button field debugging
                button_field_name = 'ai_summary_trigger'
                if button_field_name in original_data:
                    original_button = original_data[button_field_name]
                    current_button = record.data.get(button_field_name) if record.data else None
                    print(f"   🔍 BUTTON DEBUG - Original: {original_button}")
                    print(f"   🔍 BUTTON DEBUG - Current:  {current_button}")
                    print(f"   🔍 BUTTON DEBUG - Same?     {original_button == current_button}")
                    
                    if original_button and current_button:
                        print(f"   🔍 BUTTON DETAILS - Original triggered: {original_button.get('triggered')}")
                        print(f"   🔍 BUTTON DETAILS - Current triggered:  {current_button.get('triggered')}")
                        print(f"   🔍 BUTTON DETAILS - Click count change: {original_button.get('click_count')} -> {current_button.get('click_count')}")
                        
            except Exception:  # Record.DoesNotExist or other issues
                pass
        
        # Calculate changed fields
        if not is_new and original_data:
            current_data = record.data or {}
            
            for field_name in set(list(original_data.keys()) + list(current_data.keys())):
                old_value = original_data.get(field_name)
                new_value = current_data.get(field_name)
                if old_value != new_value:
                    changed_fields.add(field_name)
        
        # Determine validation context
        validation_context = self._determine_validation_context(record, is_new, changed_fields)
        
        print(f"🔍 UPDATE ANALYSIS: {len(changed_fields)} field(s) changed: {list(changed_fields)}")
        print(f"   📋 Context: {validation_context}")
        
        return ChangeContext(is_new, original_data, changed_fields, validation_context)
    
    def _determine_validation_context(self, record, is_new: bool, changed_fields: Set[str]) -> str:
        """Determine appropriate validation context"""
        if is_new:
            return 'business_rules'
        
        # Check if this is a migration context
        if hasattr(record, '_migration_context') and record._migration_context:
            print(f"🔧 MIGRATION MODE: Using migration validation context")
            return 'migration'
        
        # Determine if partial update
        is_partial_update = len(changed_fields) <= 3 and len(changed_fields) > 0
        return 'storage' if is_partial_update else 'business_rules'
    
    def validate_and_merge_data(self, record, change_context: ChangeContext):
        """Validate record data and merge with existing data"""
        
        # 🔍 DEBUG: Enhanced logging for field-specific issues
        print(f"🔍 VALIDATION DEBUG: Starting validation")
        print(f"   🆔 Record: {'NEW' if change_context.is_new else record.id}")
        print(f"   📊 Context: {change_context.validation_context}")
        print(f"   📦 Input data: {record.data}")
        if record.data:
            print(f"   🔑 Input field types: {[(k, type(v).__name__) for k, v in record.data.items()]}")
        
        # Get all pipeline fields for comparison
        pipeline_fields = {f.slug: f.field_type for f in record.pipeline.fields.all()}
        print(f"   🏗️  Pipeline expects {len(pipeline_fields)} fields: {list(pipeline_fields.keys())}")
        
        # Use optimized validation with dependency tracking
        validation_result = record.pipeline.validate_record_data_optimized(
            record.data, 
            change_context.validation_context, 
            changed_field_slug=change_context.changed_field_slug
        )
        
        # 🔍 DEBUG: Detailed validation result analysis
        print(f"🔍 VALIDATION RESULT:")
        print(f"   ✅ Valid: {validation_result['is_valid']}")
        if not validation_result['is_valid']:
            print(f"   ❌ Errors: {validation_result['errors']}")
        
        print(f"   📦 Cleaned data: {validation_result.get('cleaned_data', {})}")
        cleaned_data = validation_result.get('cleaned_data', {})
        if cleaned_data:
            print(f"   🔑 Cleaned field count: {len(cleaned_data)}")
            print(f"   🔑 Cleaned field types: {[(k, type(v).__name__) for k, v in cleaned_data.items()]}")
            
            # Compare with expected pipeline fields
            missing_fields = set(pipeline_fields.keys()) - set(cleaned_data.keys())
            if missing_fields:
                print(f"   ⚠️  MISSING from cleaned: {list(missing_fields)}")
            
            extra_fields = set(cleaned_data.keys()) - set(pipeline_fields.keys())
            if extra_fields:
                print(f"   ⚠️  EXTRA in cleaned: {list(extra_fields)}")
        
        if not validation_result['is_valid']:
            # Flatten validation errors for Django ValidationError
            error_messages = []
            for field_name, field_errors in validation_result['errors'].items():
                if isinstance(field_errors, list):
                    error_messages.extend([f"{field_name}: {error}" for error in field_errors])
                else:
                    error_messages.append(f"{field_name}: {field_errors}")
            print(f"   🚨 RAISING ValidationError: {error_messages}")
            raise ValidationError(error_messages)
        
        # Update cleaned data - MERGE with existing data to prevent data loss
        if not change_context.is_new and change_context.original_data:
            # Merge validated fields with existing data
            merged_data = change_context.original_data.copy()
            merged_data.update(validation_result['cleaned_data'])
            record.data = merged_data
            print(f"   🔄 MERGE: Combined {len(change_context.original_data)} existing + {len(validation_result['cleaned_data'])} validated = {len(merged_data)} total fields")
        else:
            # New records or full updates can replace data entirely
            record.data = validation_result['cleaned_data']
            print(f"   🆕 NEW RECORD: Using cleaned data directly ({len(record.data)} fields)")
        
        print(f"🟢 DATABASE STEP 2: After Validation")
        print(f"   📦 Final record data: {record.data}")
        if record.data:
            print(f"   🔑 Final contains {len(record.data)} field(s): [{', '.join(record.data.keys())}]")
            null_fields = [k for k, v in record.data.items() if v is None]
            if null_fields:
                print(f"   ⚠️  Final contains {len(null_fields)} NULL fields: [{', '.join(null_fields)}]")


class RecordAIProcessor:
    """Handles AI processing logic"""
    
    def should_trigger_ai_processing(self, record, change_context: ChangeContext) -> bool:
        """Determine if AI processing should be triggered"""
        if change_context.is_new:
            print(f"   ⏸️  Skipping AI processing: Record is new")
            return False
        
        if getattr(record, '_skip_ai_processing', False):
            print(f"   ⏸️  Skipping AI processing: _skip_ai_processing is True")
            return False
        
        return True
    
    def trigger_ai_updates(self, record, changed_fields: List[str]):
        """Trigger AI field updates using the unified AI system"""
        print(f"🤖 AI STEP 1: Starting AI Processing Chain")
        print(f"   📋 Record ID: {record.id}")
        print(f"   🔄 Changed Fields: {changed_fields}")
        print(f"   📊 Total Fields in Record: {len(record.data)}")
        
        try:
            from ai.integrations import trigger_field_ai_processing
            
            print(f"🤖 AI STEP 2: AI Integration Module Loaded")
            logger.info(f"🤖 AI STEP 1: Starting AI Processing Chain")
            logger.info(f"   📋 Record ID: {record.id}")
            logger.info(f"   🔄 Changed Fields: {changed_fields}")
            logger.info(f"   📊 Total Fields in Record: {len(record.data)}")
            
            # Get the user who made the change (if available)
            user = getattr(record, '_current_user', None) or record.updated_by
            if not user:
                logger.warning(f"❌ AI STEP 1 FAILED: No user context for AI processing on record {record.id}")
                logger.warning(f"   _current_user: {getattr(record, '_current_user', 'NOT_SET')}")
                logger.warning(f"   updated_by: {record.updated_by}")
                return
            
            logger.info(f"🤖 AI STEP 2: User Context Validated")
            logger.info(f"   👤 User: {user.email} (ID: {user.id})")
            logger.info(f"   🔑 User Type: {user.user_type.name if hasattr(user, 'user_type') and user.user_type else 'Unknown'}")
            
            # Trigger AI processing using the new unified system
            logger.info(f"🤖 AI STEP 3: Calling trigger_field_ai_processing")
            result = trigger_field_ai_processing(record, changed_fields, user)
            
            logger.info(f"🤖 AI STEP 4: Processing Complete")
            logger.info(f"   ✅ Triggered Jobs: {len(result.get('triggered_jobs', []))}")
            logger.info(f"   📋 Job Details: {result.get('triggered_jobs', [])}")
            
            if result.get('triggered_jobs'):
                for job in result.get('triggered_jobs', []):
                    logger.info(f"   🔧 AI Job Created: Field '{job.get('field')}', Job ID: {job.get('job_id', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"❌ AI PROCESSING FAILED for record {record.id}: {e}")
            import traceback
            logger.error(f"   📋 Full traceback: {traceback.format_exc()}")


class RecordPostProcessor:
    """Handles post-save operations"""
    
    def update_search_vector(self, record):
        """Update full-text search vector"""
        from django.contrib.postgres.search import SearchVector
        from django.db import models
        
        # Get searchable field values
        searchable_text = []
        
        for field in record.pipeline.fields.filter(is_searchable=True):
            value = record.data.get(field.slug)
            if value:
                if isinstance(value, (list, dict)):
                    searchable_text.append(str(value))
                else:
                    searchable_text.append(str(value))
        
        # Add title and tags
        if record.title:
            searchable_text.append(record.title)
        if record.tags:
            searchable_text.extend(record.tags)
        
        # Update search vector
        if searchable_text:
            search_text = ' '.join(searchable_text)
            # Import here to avoid circular import
            from .models import Record
            Record.objects.filter(id=record.id).update(
                search_vector=SearchVector('title') + SearchVector(models.Value(search_text))
            )
    
    def update_pipeline_stats(self, record):
        """Update pipeline statistics for new records"""
        from django.db import models
        # Import here to avoid circular import
        from .models import Pipeline
        
        Pipeline.objects.filter(id=record.pipeline_id).update(
            record_count=models.F('record_count') + 1,
            last_record_created=timezone.now()
        )
    
    def broadcast_changes(self, record, original_data: Dict[str, Any], is_new: bool):
        """Broadcast record changes via real-time system"""
        # Skip broadcasting if requested
        if hasattr(record, '_skip_broadcast') and record._skip_broadcast:
            return
        
        try:
            from api.events import broadcaster
            import asyncio
            
            changes = RecordUtils.get_changed_fields(original_data, record.data) if not is_new and original_data else None
            
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(broadcaster.broadcast_record_update(
                    record, 
                    event_type="created" if is_new else "updated",
                    user_id=getattr(record, '_current_user_id', None),
                    changes=changes
                ))
            else:
                broadcaster.sync_broadcast_record_update(
                    record, 
                    event_type="created" if is_new else "updated",
                    user_id=getattr(record, '_current_user_id', None),
                    changes=changes
                )
        except Exception:
            pass  # Don't fail save if broadcast fails


class RecordOperationManager:
    """
    Single entry point for ALL record operations
    
    Replaces complex Record.save() method with clean, organized components.
    """
    
    def __init__(self, record):
        self.record = record
        self.change_manager = RecordChangeManager()
        self.ai_processor = RecordAIProcessor()
        self.post_processor = RecordPostProcessor()
        self._operation_counter = 0
    
    def _generate_operation_id(self) -> str:
        """Generate unique operation ID for tracking"""
        self._operation_counter += 1
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        return f"record_op_{self.record.id or 'NEW'}_{timestamp}_{self._operation_counter}"
    
    def process_record_save(self, *args, **kwargs) -> SaveResult:
        """
        Single entry point for record save processing
        
        This replaces the complex Record.save() method with organized components.
        """
        operation_id = self._generate_operation_id()
        logger.info(f"[{operation_id}] Starting record save processing")
        
        try:
            with transaction.atomic():
                # Step 1: Detect changes and create context
                change_context = self.change_manager.detect_changes(self.record)
                
                # Step 2: Validate and merge data
                self.change_manager.validate_and_merge_data(self.record, change_context)
                
                # Step 3: Generate title if not provided
                if not self.record.title:
                    self.record.title = RecordUtils.generate_title(
                        self.record.data, 
                        self.record.pipeline.name
                    )
                
                # Step 4: Update version if data changed
                if not change_context.is_new and change_context.original_data != self.record.data:
                    self.record.version += 1
                
                # Step 5: Process AI updates BEFORE database save to avoid race conditions
                if self.ai_processor.should_trigger_ai_processing(self.record, change_context):
                    if change_context.changed_fields:
                        print(f"   ✅ Calling AI processing with fields: {list(change_context.changed_fields)}")
                        self.ai_processor.trigger_ai_updates(self.record, list(change_context.changed_fields))
                    else:
                        print(f"   ❌ No changed fields detected, skipping AI processing")
                
                # Step 6: Perform the actual database save
                print(f"🟢 DATABASE STEP 3: Saving to Database")
                print(f"   📦 Final data before save: {self.record.data}")
                
                # Call Django's Model.save() method directly (fixing the broken super() call)
                from django.db import models
                models.Model.save(self.record, *args, **kwargs)
                
                print(f"🟢 DATABASE STEP 3.1: Django save() completed successfully")
                print(f"   ✅ Database save complete for record {self.record.pk}")
                print(f"   📦 Final data after save: {self.record.data}")
                
                # Step 7: Post-save operations
                self.post_processor.update_search_vector(self.record)
                
                if change_context.is_new:
                    self.post_processor.update_pipeline_stats(self.record)
                
                self.post_processor.broadcast_changes(
                    self.record, 
                    change_context.original_data, 
                    change_context.is_new
                )
                
                logger.info(f"[{operation_id}] Record save processing completed successfully")
                
                return SaveResult(
                    success=True,
                    record=self.record,
                    operation_id=operation_id,
                    metadata={
                        'operation_type': 'create' if change_context.is_new else 'update',
                        'changed_fields': list(change_context.changed_fields),
                        'validation_context': change_context.validation_context
                    }
                )
                
        except Exception as e:
            logger.error(f"[{operation_id}] Record save processing failed: {str(e)}")
            return SaveResult(
                success=False,
                operation_id=operation_id,
                errors=[f"Record save processing failed: {str(e)}"]
            )


# =============================================================================
# FACTORY FUNCTIONS - Convenient access to RecordOperationManager instances
# =============================================================================

def get_record_operation_manager(record) -> RecordOperationManager:
    """Get RecordOperationManager instance for a record"""
    return RecordOperationManager(record)