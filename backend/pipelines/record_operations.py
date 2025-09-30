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
    def generate_title(record_data: Dict[str, Any], pipeline_name: str, pipeline=None) -> str:
        """Generate display title from record data using configurable template"""
        import re
        
        # Get the title template from pipeline settings
        if pipeline:
            template = pipeline.get_title_template()
        else:
            # Fallback if no pipeline provided (shouldn't happen in normal usage)
            template = '{name}'
        
        # Get field definitions for proper formatting
        field_definitions = {}
        if pipeline:
            for field in pipeline.fields.all():
                field_definitions[field.slug] = field
        
        # Replace {field_name} placeholders with actual values or empty strings
        title = template
        for field_name, value in record_data.items():
            placeholder = f'{{{field_name}}}'
            if placeholder in title:
                # Get field definition for proper formatting
                field_def = field_definitions.get(field_name)
                field_value = RecordUtils._format_field_value_for_title(value, field_def)
                title = title.replace(placeholder, field_value)
        
        # Clean up any remaining unreplaced placeholders (for fields that don't exist)
        title = re.sub(r'\{[^}]+\}', '', title)
        
        # If title is empty or just whitespace, use pipeline name as fallback
        title = title.strip()
        if not title:
            return f"{pipeline_name} Record"
        
        # Truncate to max length
        return title[:500]
    
    @staticmethod
    def _format_field_value_for_title(value, field_def=None) -> str:
        """Format a field value for display in record title"""
        if value is None or value == '':
            return ''
        
        field_type = field_def.field_type if field_def else None
        
        # Handle different field types
        if field_type == 'user':
            # User field: resolve user IDs to names
            if isinstance(value, (int, str)):
                # Single user ID - resolve to name
                try:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    user = User.objects.get(id=int(value))
                    return user.first_name + ' ' + user.last_name if user.first_name else user.email
                except:
                    return f"User #{value}"
            elif isinstance(value, list) and len(value) > 0:
                # Multiple user IDs - resolve all users and return separated by | for frontend chip parsing
                try:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    user_names = []
                    for user_id in value:
                        try:
                            user = User.objects.get(id=int(user_id))
                            user_name = user.first_name + ' ' + user.last_name if user.first_name else user.email
                            user_names.append(user_name)
                        except:
                            user_names.append(f"User #{user_id}")
                    return ' | '.join(user_names)
                except:
                    # Fallback to user IDs
                    user_fallbacks = [f"User #{uid}" for uid in value]
                    return ' | '.join(user_fallbacks)
            elif isinstance(value, dict):
                return value.get('name') or value.get('email') or value.get('username') or str(value.get('id', ''))
            return str(value)
        
        elif field_type == 'select':
            # Select field: show the actual option value
            if isinstance(value, dict):
                return value.get('label') or value.get('value') or str(value)
            return str(value)
        
        elif field_type == 'multiselect':
            # Multiselect: return all items separated by | for frontend chip parsing
            if isinstance(value, list):
                if len(value) == 0:
                    return ''
                # Extract labels/values and return as separate parts for individual chips
                items = []
                for item in value:
                    if isinstance(item, dict):
                        items.append(item.get('label') or item.get('value') or str(item))
                    else:
                        items.append(str(item))
                return ' | '.join(items)
            return str(value)
        
        elif field_type == 'tags':
            # Tags: return all items separated by | for frontend chip parsing
            if isinstance(value, list):
                if len(value) == 0:
                    return ''
                # Return each tag as a separate part that will become individual chips
                return ' | '.join(str(tag) for tag in value)
            return str(value)
        
        elif field_type == 'relation' or field_type == 'relationship':
            # Relation field: resolve related record IDs using configured display field
            # Get the configured display field from field configuration
            display_field = 'title'  # Default fallback
            if field_def and field_def.field_config:
                display_field = field_def.field_config.get('display_field', 'title')
                print(f"🔍 RELATION DEBUG: field_def.slug='{field_def.slug}', field_config={field_def.field_config}, display_field='{display_field}'")
            
            def get_relation_display_value(record_id):
                """Get display value for a single related record - matches frontend getDisplayValue logic"""
                try:
                    from .models import Record
                    related_record = Record.objects.get(id=int(record_id))
                    
                    # Try to get the configured display field from record.data (like frontend line 165)
                    if display_field and related_record.data and display_field in related_record.data:
                        value = related_record.data[display_field]
                        
                        # Handle different value types properly (like frontend lines 169-172)
                        if value is None or value == '' or value == '':
                            # Fallback if field is empty (like frontend line 170)
                            return related_record.title or f"Record #{record_id}"
                        
                        # Recursively format the display field value if it's complex
                        # Get the field definition for the display field in the target pipeline
                        target_field_def = None
                        try:
                            target_field_def = related_record.pipeline.fields.get(slug=display_field)
                        except:
                            pass
                        return RecordUtils._format_field_value_for_title(value, target_field_def)
                    
                    # Try to find the field by searching for similar names (like frontend lines 176-191)
                    if display_field and related_record.data:
                        data_keys = list(related_record.data.keys())
                        
                        # Look for exact match (case insensitive) (like frontend line 180)
                        exact_match = next((key for key in data_keys if key.lower() == display_field.lower()), None)
                        if exact_match and related_record.data[exact_match] not in [None, '', '']:
                            value = related_record.data[exact_match]
                            try:
                                target_field_def = related_record.pipeline.fields.get(slug=exact_match)
                            except:
                                target_field_def = None
                            return RecordUtils._format_field_value_for_title(value, target_field_def)
                        
                        # Look for slug-like match (convert display name to slug) (like frontend line 186)
                        import re
                        slugified = re.sub(r'[^a-z0-9]', '_', display_field.lower())
                        slugified = re.sub(r'_+', '_', slugified)
                        slug_match = next((key for key in data_keys if key == slugified), None)
                        if slug_match and related_record.data[slug_match] not in [None, '', '']:
                            value = related_record.data[slug_match]
                            try:
                                target_field_def = related_record.pipeline.fields.get(slug=slug_match)
                            except:
                                target_field_def = None
                            return RecordUtils._format_field_value_for_title(value, target_field_def)
                    
                    # Fallback to record.title if it exists (like frontend line 194)
                    if related_record.title:
                        return related_record.title
                    
                    # Final fallback to record ID (like frontend line 199)
                    return f"Record #{record_id}"
                except:
                    return f"Record #{record_id}"
            
            if isinstance(value, (int, str)):
                # Single relation ID
                return get_relation_display_value(value)
            elif isinstance(value, list):
                if len(value) == 0:
                    return ''
                elif len(value) == 1:
                    # Single item in list
                    item = value[0]
                    if isinstance(item, (int, str)):
                        return get_relation_display_value(item)
                    elif isinstance(item, dict):
                        return item.get('title') or item.get('name') or str(item.get('id', ''))
                    return str(item)
                else:
                    # Multiple relations: return all items separated by | for frontend chip parsing
                    relation_titles = []
                    for item in value:
                        if isinstance(item, (int, str)):
                            relation_titles.append(get_relation_display_value(item))
                        elif isinstance(item, dict):
                            relation_titles.append(item.get('title') or item.get('name') or str(item.get('id', '')))
                        else:
                            relation_titles.append(str(item))
                    return ' | '.join(relation_titles)
            elif isinstance(value, dict):
                return value.get('title') or value.get('name') or str(value.get('id', ''))
            return str(value)
        
        elif field_type == 'currency':
            # Currency: add currency symbol
            if isinstance(value, dict):
                amount = value.get('amount', 0)
                currency = value.get('currency', 'USD')
                return f"{currency} {amount}"
            return str(value)
        
        elif field_type == 'address':
            # Address: show street + city or formatted address
            if isinstance(value, dict):
                if 'formatted' in value:
                    return value['formatted']
                elif 'street' in value and 'city' in value:
                    return f"{value['street']}, {value['city']}"
                elif 'street' in value:
                    return value['street']
                elif 'city' in value:
                    return value['city']
            return str(value)
        
        elif field_type == 'file':
            # File: show filename
            if isinstance(value, dict):
                return value.get('name') or value.get('filename') or 'File'
            elif isinstance(value, list) and len(value) > 0:
                # Multiple files - return all file names separated by | for frontend chip parsing
                file_names = []
                for file_item in value:
                    if isinstance(file_item, dict):
                        file_name = file_item.get('name') or file_item.get('filename') or 'File'
                    else:
                        file_name = 'File'
                    file_names.append(file_name)
                return ' | '.join(file_names)
            return 'File'
        
        elif field_type == 'date' or field_type == 'datetime':
            # Date: format nicely
            if isinstance(value, str):
                try:
                    from datetime import datetime
                    if 'T' in value:  # ISO datetime
                        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        return dt.strftime('%Y-%m-%d %H:%M')
                    else:  # Date only
                        dt = datetime.fromisoformat(value)
                        return dt.strftime('%Y-%m-%d')
                except:
                    pass
            return str(value)
        
        elif field_type == 'boolean':
            # Boolean: show Yes/No
            if isinstance(value, bool):
                return 'Yes' if value else 'No'
            return str(value)
        
        else:
            # Default: convert to string
            if isinstance(value, (dict, list)):
                # For complex objects, try to find a meaningful representation
                if isinstance(value, dict):
                    # Try common display fields
                    for key in ['name', 'title', 'label', 'display_name', 'value']:
                        if key in value and value[key]:
                            return str(value[key])
                    # Fallback to first non-id field
                    for key, val in value.items():
                        if key != 'id' and val:
                            return str(val)
                elif isinstance(value, list) and len(value) > 0:
                    # Show all items separated by | for frontend chip parsing
                    formatted_items = []
                    for item in value:
                        formatted_item = RecordUtils._format_field_value_for_title(item, field_def)
                        if formatted_item:  # Only add non-empty items
                            formatted_items.append(formatted_item)
                    return ' | '.join(formatted_items) if formatted_items else str(value[0])
                
                return str(value)
            
            return str(value)
    
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
        # Track relation field updates
        self._relation_updates = {}
    
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

                # Step 2.5: Extract relation fields from data (they'll be synced after save)
                self._extract_relation_fields(self.record)
                print(f"   📦 After extraction, _relation_updates has {len(self._relation_updates)} items")

                # Step 3: Title generation removed - titles are now fully dynamic
                # Titles are generated on-the-fly in serializers/views for consistency
                # This eliminates sync issues between stored titles and changing data/templates
                # Leave title empty in database to indicate dynamic generation
                if not self.record.title:
                    self.record.title = ""  # Empty string indicates dynamic title
                
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

                # Store user if provided for relation syncing
                user = kwargs.pop('user', None)
                if user:
                    self.record._current_user = user

                # Filter kwargs to only include valid Django save parameters
                valid_save_kwargs = {}
                for key in ['force_insert', 'force_update', 'using', 'update_fields']:
                    if key in kwargs:
                        valid_save_kwargs[key] = kwargs[key]

                # Set flag to prevent recursive save
                self.record._in_operation_manager = True

                try:
                    # Call Django's Model.save() method directly (fixing the broken super() call)
                    from django.db import models
                    models.Model.save(self.record, **valid_save_kwargs)
                except Exception as e:
                    print(f"   ❌ Django save failed: {e}")
                    raise
                finally:
                    # Clear flag after save
                    self.record._in_operation_manager = False
                
                print(f"🟢 DATABASE STEP 3.1: Django save() completed successfully")
                print(f"   ✅ Database save complete for record {self.record.pk}")
                print(f"   📦 Final data after save: {self.record.data}")

                # Step 6.5: Extract and sync relation fields to Relationship table
                print(f"   📦 Before sync, _relation_updates has {len(self._relation_updates)} items")
                self._sync_relation_fields(change_context)

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

    def _extract_relation_fields(self, record):
        """Extract relation fields from data and store for later sync"""
        relation_fields = record.pipeline.fields.filter(field_type='relation')

        for field in relation_fields:
            if field.slug in record.data:
                # Extract and store relation value
                value = record.data.pop(field.slug)
                self._relation_updates[field] = value
                print(f"   → Extracted relation field '{field.slug}': {value}")

    def _sync_relation_fields(self, change_context: ChangeContext):
        """Sync extracted relation fields to Relationship table"""
        if not self._relation_updates:
            print(f"   ⚠️ No relation updates to sync")
            return

        print(f"🔗 Syncing {len(self._relation_updates)} relation field(s) to Relationship table")
        print(f"   📦 Updates to sync: {[(f.slug, v) for f, v in self._relation_updates.items()]}")

        from .relation_field_handler import sync_relation_field

        user = getattr(self.record, '_current_user', None)

        for field, value in self._relation_updates.items():
            try:
                result = sync_relation_field(self.record, field, value, user)
                print(f"   ✓ Synced '{field.slug}': {result}")
            except Exception as e:
                print(f"   ❌ Failed to sync '{field.slug}': {e}")
                # Don't fail the save if relation sync fails
                logger.error(f"Failed to sync relation field {field.slug}: {e}")

        # Clear updates after sync
        self._relation_updates.clear()


# =============================================================================
# FACTORY FUNCTIONS - Convenient access to RecordOperationManager instances
# =============================================================================

def get_record_operation_manager(record) -> RecordOperationManager:
    """Get RecordOperationManager instance for a record"""
    return RecordOperationManager(record)