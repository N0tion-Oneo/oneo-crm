"""
Contact Management Node Processors - Contact resolution, creation, and updates
"""
import logging
from typing import Dict, Any, Optional, List
from django.utils import timezone
from asgiref.sync import sync_to_async
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class ContactResolveProcessor(AsyncNodeProcessor):
    """Process contact resolution/creation nodes"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["pipeline_id"],
        "properties": {
            "pipeline_id": {
                "type": "string",
                "description": "Pipeline to search/create contact in",
                "ui_hints": {
                    "widget": "pipeline_select"
                }
            },
            "email": {
                "type": "string",
                "format": "email",
                "description": "Email address to search for",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "{{form.email}} or john@example.com"
                }
            },
            "phone": {
                "type": "string",
                "description": "Phone number to search for",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "{{form.phone}} or +1234567890"
                }
            },
            "name": {
                "type": "string",
                "description": "Contact name",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "{{form.name}} or John Doe"
                }
            },
            "linkedin_url": {
                "type": "string",
                "format": "uri",
                "description": "LinkedIn profile URL",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "linkedin.com/in/johndoe"
                }
            },
            "create_if_not_found": {
                "type": "boolean",
                "default": True,
                "description": "Create new contact if not found"
            },
            "merge_strategy": {
                "type": "string",
                "enum": ["update_existing", "keep_existing", "merge_fields"],
                "default": "update_existing",
                "description": "How to handle existing contacts",
                "ui_hints": {
                    "widget": "radio"
                }
            },
            "additional_fields": {
                "type": "object",
                "description": "Additional fields for contact",
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 4,
                    "section": "advanced"
                }
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "resolve_contact"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process contact resolution/creation node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Extract contact identification fields
        email = self._format_template(config.get('email', ''), context) or self._get_nested_value(context, 'email')
        phone = self._format_template(config.get('phone', ''), context) or self._get_nested_value(context, 'phone')
        name = self._format_template(config.get('name', ''), context) or self._get_nested_value(context, 'name')
        linkedin_url = self._format_template(config.get('linkedin_url', ''), context) or self._get_nested_value(context, 'linkedin_url')

        # Configuration
        pipeline_id = config.get('pipeline_id')
        create_if_not_found = config.get('create_if_not_found', True)
        additional_fields = config.get('additional_fields', {})
        merge_strategy = config.get('merge_strategy', 'update_existing')  # update_existing, keep_existing, merge_fields
        
        # Get execution context
        execution = context.get('execution')
        
        # Validate required fields
        if not any([email, phone, linkedin_url]):
            raise ValueError("Contact resolution requires at least one identifier: email, phone, or linkedin_url")
        
        if not pipeline_id:
            raise ValueError("Contact resolution requires pipeline_id")
        
        try:
            # Get pipeline
            from pipelines.models import Pipeline
            pipeline = await sync_to_async(Pipeline.objects.get)(id=pipeline_id)
            
            # Try to find existing contact
            existing_contact = await self._find_existing_contact(
                pipeline, email, phone, linkedin_url
            )
            
            if existing_contact:
                # Found existing contact
                updated_contact = await self._handle_existing_contact(
                    existing_contact, email, phone, name, linkedin_url, 
                    additional_fields, merge_strategy, execution
                )
                
                return {
                    'success': True,
                    'contact_id': str(updated_contact.id),
                    'created': False,
                    'updated': updated_contact != existing_contact,
                    'contact_data': updated_contact.data,
                    'resolution_method': 'found_existing'
                }
            
            elif create_if_not_found:
                # Create new contact
                new_contact = await self._create_new_contact(
                    pipeline, email, phone, name, linkedin_url, 
                    additional_fields, execution
                )
                
                return {
                    'success': True,
                    'contact_id': str(new_contact.id),
                    'created': True,
                    'updated': False,
                    'contact_data': new_contact.data,
                    'resolution_method': 'created_new'
                }
            
            else:
                # Contact not found and creation disabled
                return {
                    'success': False,
                    'contact_id': None,
                    'created': False,
                    'updated': False,
                    'error': 'Contact not found and create_if_not_found is disabled',
                    'resolution_method': 'not_found'
                }
                
        except Exception as e:
            logger.error(f"Contact resolution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'contact_id': None,
                'resolution_identifiers': {
                    'email': email,
                    'phone': phone,
                    'linkedin_url': linkedin_url
                }
            }
    
    async def _find_existing_contact(
        self, 
        pipeline, 
        email: Optional[str], 
        phone: Optional[str], 
        linkedin_url: Optional[str]
    ):
        """Find existing contact by identifiers"""
        
        try:
            from pipelines.models import Record
            from django.db.models import Q
            
            # Build search query
            query = Q(pipeline=pipeline, is_deleted=False)
            identifier_query = Q()
            
            if email:
                identifier_query |= Q(data__email__iexact=email)
            
            if phone:
                # Clean phone number for comparison
                cleaned_phone = self._clean_phone_number(phone)
                identifier_query |= Q(data__phone__icontains=cleaned_phone)
            
            if linkedin_url:
                identifier_query |= Q(data__linkedin_url__iexact=linkedin_url)
            
            if not identifier_query:
                return None
            
            query &= identifier_query
            
            # Execute query
            existing_contact = await sync_to_async(
                Record.objects.filter(query).select_related('pipeline').first
            )()
            
            return existing_contact
            
        except Exception as e:
            logger.error(f"Failed to find existing contact: {e}")
            return None
    
    async def _handle_existing_contact(
        self,
        existing_contact,
        email: Optional[str],
        phone: Optional[str],
        name: Optional[str],
        linkedin_url: Optional[str],
        additional_fields: Dict[str, Any],
        merge_strategy: str,
        execution
    ):
        """Handle updates to existing contact"""
        
        try:
            if merge_strategy == 'keep_existing':
                # Don't update existing contact
                return existing_contact
            
            # Prepare update data
            update_data = {}
            
            # Update basic fields
            if email and (merge_strategy == 'update_existing' or not existing_contact.data.get('email')):
                update_data['email'] = email  
            
            if phone and (merge_strategy == 'update_existing' or not existing_contact.data.get('phone')):
                update_data['phone'] = phone
            
            if name and (merge_strategy == 'update_existing' or not existing_contact.data.get('name')):
                update_data['name'] = name
            
            if linkedin_url and (merge_strategy == 'update_existing' or not existing_contact.data.get('linkedin_url')):
                update_data['linkedin_url'] = linkedin_url
            
            # Handle additional fields
            for field_key, field_value in additional_fields.items():
                formatted_value = self._format_template(str(field_value), {'contact': existing_contact})
                
                if merge_strategy == 'update_existing':
                    update_data[field_key] = formatted_value
                elif merge_strategy == 'merge_fields':
                    # Merge lists/arrays, update other types
                    existing_value = existing_contact.data.get(field_key)
                    if isinstance(existing_value, list) and isinstance(formatted_value, list):
                        update_data[field_key] = list(set(existing_value + formatted_value))
                    elif not existing_value:
                        update_data[field_key] = formatted_value
            
            # Update contact if there are changes
            if update_data:
                existing_contact.data.update(update_data)
                existing_contact.updated_by = execution.triggered_by if execution else None
                await sync_to_async(existing_contact.save)()
                
                logger.info(f"Contact updated - ID: {existing_contact.id}, Fields: {list(update_data.keys())}")
            
            return existing_contact
            
        except Exception as e:
            logger.error(f"Failed to handle existing contact: {e}")
            return existing_contact
    
    async def _create_new_contact(
        self,
        pipeline,
        email: Optional[str],
        phone: Optional[str],
        name: Optional[str],
        linkedin_url: Optional[str],
        additional_fields: Dict[str, Any],
        execution
    ):
        """Create new contact record"""
        
        try:
            from pipelines.models import Record
            
            # Prepare contact data
            contact_data = {}
            
            if email:
                contact_data['email'] = email
            if phone:
                contact_data['phone'] = phone
            if name:
                contact_data['name'] = name
            if linkedin_url:
                contact_data['linkedin_url'] = linkedin_url
            
            # Add additional fields
            for field_key, field_value in additional_fields.items():
                formatted_value = self._format_template(str(field_value), {})
                contact_data[field_key] = formatted_value
            
            # Add metadata
            contact_data['created_via_workflow'] = True
            contact_data['created_at'] = timezone.now().isoformat()
            
            # Create contact record
            new_contact = await sync_to_async(Record.objects.create)(
                pipeline=pipeline,
                data=contact_data,
                created_by=execution.triggered_by if execution else None
            )
            
            logger.info(f"New contact created - ID: {new_contact.id}, Email: {email}, Phone: {phone}")
            
            return new_contact
            
        except Exception as e:
            logger.error(f"Failed to create new contact: {e}")
            raise
    
    def _clean_phone_number(self, phone: str) -> str:
        """Clean phone number for consistent comparison"""
        
        if not phone:
            return ''
        
        # Remove common formatting characters
        cleaned = phone.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '').replace('.', '')
        
        # Keep only digits
        cleaned = ''.join(char for char in cleaned if char.isdigit())
        
        return cleaned
    
    def _format_template(self, template: str, context: Dict[str, Any]) -> str:
        """Format template string with context variables"""
        if not template:
            return ''
        
        try:
            return template.format(**context)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template
        except Exception as e:
            logger.error(f"Template formatting error: {e}")
            return template
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate contact resolution node inputs"""
        node_data = node_config.get('data', {})
        
        # Check required fields
        if not node_data.get('pipeline_id'):
            return False
        
        # Validate merge strategy
        merge_strategy = node_data.get('merge_strategy', 'update_existing')
        valid_strategies = ['update_existing', 'keep_existing', 'merge_fields']
        if merge_strategy not in valid_strategies:
            return False
        
        # Validate boolean flags
        create_if_not_found = node_data.get('create_if_not_found', True)
        if not isinstance(create_if_not_found, bool):
            return False
        
        # Validate additional fields
        additional_fields = node_data.get('additional_fields', {})
        if not isinstance(additional_fields, dict):
            return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for contact resolution node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        
        # Resolve identifiers for checkpoint
        email = self._format_template(node_data.get('email', ''), context) or self._get_nested_value(context, 'email')
        phone = self._format_template(node_data.get('phone', ''), context) or self._get_nested_value(context, 'phone')
        name = self._format_template(node_data.get('name', ''), context) or self._get_nested_value(context, 'name')
        
        checkpoint.update({
            'contact_resolution_config': {
                'pipeline_id': node_data.get('pipeline_id'),
                'identifiers': {
                    'email': email,
                    'phone': phone,
                    'name': name,
                    'linkedin_url': self._format_template(node_data.get('linkedin_url', ''), context)
                },
                'create_if_not_found': node_data.get('create_if_not_found', True),
                'merge_strategy': node_data.get('merge_strategy', 'update_existing'),
                'additional_fields_count': len(node_data.get('additional_fields', {}))
            }
        })
        
        return checkpoint