"""
Automatic Contact Resolution Service
Handles the intelligent resolution of unconnected conversations to existing contact records
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q, Count
from django.db import transaction

from communications.models import Conversation, Message
from communications.resolvers.contact_identifier import ContactIdentifier
from communications.resolvers.relationship_context import RelationshipContextResolver
from pipelines.models import Record

logger = logging.getLogger(__name__)


class UnconnectedConversationResolver:
    """
    Service for automatically resolving unconnected conversations to existing contact records
    """
    
    def __init__(self, tenant_id: int):
        """
        Initialize the resolver with tenant context
        
        Args:
            tenant_id: Tenant ID for multi-tenant operations
        """
        self.tenant_id = tenant_id
        self.contact_identifier = ContactIdentifier(tenant_id=tenant_id)
        self.relationship_resolver = RelationshipContextResolver(tenant_id=tenant_id)
        
        # Resolution statistics
        self.stats = {
            'processed': 0,
            'resolved': 0,
            'skipped_no_contact_data': 0,
            'skipped_no_matches': 0,
            'skipped_domain_validation_failed': 0,
            'errors': 0
        }
    
    def resolve_batch(self, limit: int = 50, priority_recent: bool = True) -> Dict[str, Any]:
        """
        Resolve a batch of unconnected conversations
        
        Args:
            limit: Maximum number of conversations to process
            priority_recent: Whether to prioritize recent conversations
            
        Returns:
            dict: Resolution results and statistics
        """
        logger.info(f"Starting batch resolution with limit {limit}, priority_recent={priority_recent}")
        
        # Reset statistics
        self._reset_stats()
        
        # Get unconnected conversations
        conversations = self._get_unconnected_conversations(limit, priority_recent)
        
        if not conversations:
            logger.info("No unconnected conversations found")
            return self._get_results_summary()
        
        logger.info(f"Processing {len(conversations)} unconnected conversations")
        
        # Process each conversation
        for conversation in conversations:
            try:
                self._process_conversation(conversation)
            except Exception as e:
                logger.error(f"Error processing conversation {conversation.id}: {e}")
                self.stats['errors'] += 1
                continue
        
        results = self._get_results_summary()
        logger.info(f"Batch resolution completed: {results}")
        
        return results
    
    def resolve_specific_conversations(self, conversation_ids: List[str]) -> Dict[str, Any]:
        """
        Resolve specific conversations by ID
        
        Args:
            conversation_ids: List of conversation UUIDs to process
            
        Returns:
            dict: Resolution results for specific conversations
        """
        logger.info(f"Resolving {len(conversation_ids)} specific conversations")
        
        # Reset statistics
        self._reset_stats()
        
        results = {
            'conversation_results': [],
            'summary': {}
        }
        
        for conversation_id in conversation_ids:
            try:
                conversation = Conversation.objects.get(id=conversation_id)
                
                # Skip if already connected
                if conversation.primary_contact_record:
                    results['conversation_results'].append({
                        'conversation_id': conversation_id,
                        'status': 'already_connected',
                        'contact_id': conversation.primary_contact_record.id
                    })
                    continue
                
                # Process the conversation
                resolution_result = self._process_conversation(conversation)
                results['conversation_results'].append({
                    'conversation_id': conversation_id,
                    'status': 'processed',
                    'result': resolution_result
                })
                
            except Conversation.DoesNotExist:
                logger.warning(f"Conversation {conversation_id} not found")
                results['conversation_results'].append({
                    'conversation_id': conversation_id,
                    'status': 'not_found',
                    'error': 'Conversation not found'
                })
                self.stats['errors'] += 1
                
            except Exception as e:
                logger.error(f"Error processing conversation {conversation_id}: {e}")
                results['conversation_results'].append({
                    'conversation_id': conversation_id,
                    'status': 'error',
                    'error': str(e)
                })
                self.stats['errors'] += 1
        
        results['summary'] = self._get_results_summary()
        return results
    
    def get_resolution_candidates(self, conversation: Conversation, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get potential contact resolution candidates for a conversation without resolving
        
        Args:
            conversation: Conversation to analyze
            limit: Maximum number of candidates to return
            
        Returns:
            list: List of potential contact candidates with scores
        """
        # Get recent inbound message
        recent_message = conversation.messages.filter(
            direction='inbound'
        ).order_by('-created_at').first()
        
        if not recent_message:
            return []
        
        # Extract contact data
        contact_data = self._extract_contact_data_from_message(recent_message)
        
        if not contact_data:
            return []
        
        # Find potential matches using contact identifier
        # This is a simplified version - the full ContactIdentifier has more sophisticated matching
        candidates = []
        
        try:
            # Get all pipelines with duplicate rules
            from pipelines.models import Pipeline
            from duplicates.models import DuplicateRule
            
            pipelines_with_rules = Pipeline.objects.filter(
                duplicate_rules__action_on_duplicate='detect_only'
            ).distinct()
            
            for pipeline in pipelines_with_rules:
                # Get potential matches in this pipeline
                pipeline_records = Record.objects.filter(
                    pipeline=pipeline,
                    is_deleted=False
                )
                
                for record in pipeline_records:
                    score = self._calculate_match_score(contact_data, record.data)
                    if score > 0.5:  # Threshold for consideration
                        # Get domain validation info
                        relationship_context = self.relationship_resolver.get_relationship_context(
                            contact_record=record,
                            message_email=contact_data.get('email')
                        )
                        
                        candidates.append({
                            'record_id': record.id,
                            'pipeline_id': pipeline.id,
                            'pipeline_name': pipeline.name,
                            'record_title': record.title,
                            'match_score': score,
                            'domain_validated': relationship_context.get('domain_validated', True),
                            'validation_status': relationship_context.get('validation_status'),
                            'contact_data_matched': self._get_matched_fields(contact_data, record.data)
                        })
            
            # Sort by match score and return top candidates
            candidates.sort(key=lambda x: x['match_score'], reverse=True)
            return candidates[:limit]
            
        except Exception as e:
            logger.error(f"Error getting resolution candidates: {e}")
            return []
    
    def _get_unconnected_conversations(self, limit: int, priority_recent: bool) -> List[Conversation]:
        """Get unconnected conversations for processing"""
        queryset = Conversation.objects.filter(
            primary_contact_record__isnull=True,
            status='active',
            last_message_at__isnull=False
        ).select_related('channel')
        
        if priority_recent:
            # Prioritize conversations with recent activity (last 7 days)
            recent_cutoff = timezone.now() - timedelta(days=7)
            queryset = queryset.order_by(
                # Recent conversations first
                '-last_message_at'
            ).extra(
                select={'is_recent': f"last_message_at > '{recent_cutoff}'"},
                order_by=['-is_recent', '-last_message_at']
            )
        else:
            queryset = queryset.order_by('-last_message_at')
        
        return list(queryset[:limit])
    
    def _process_conversation(self, conversation: Conversation) -> Dict[str, Any]:
        """Process a single conversation for contact resolution"""
        self.stats['processed'] += 1
        
        # Get the most recent inbound message
        recent_message = conversation.messages.filter(
            direction='inbound'
        ).order_by('-created_at').first()
        
        if not recent_message:
            self.stats['skipped_no_contact_data'] += 1
            return {'status': 'skipped', 'reason': 'no_inbound_messages'}
        
        # Extract contact data
        contact_data = self._extract_contact_data_from_message(recent_message)
        
        if not contact_data:
            self.stats['skipped_no_contact_data'] += 1
            return {'status': 'skipped', 'reason': 'no_contact_data'}
        
        # Attempt contact resolution
        contact_record = self.contact_identifier.identify_contact(contact_data)
        
        if not contact_record:
            self.stats['skipped_no_matches'] += 1
            return {'status': 'skipped', 'reason': 'no_matches_found'}
        
        # Validate domain relationship context
        relationship_context = self.relationship_resolver.get_relationship_context(
            contact_record=contact_record,
            message_email=contact_data.get('email')
        )
        
        domain_validated = relationship_context.get('domain_validated', True)
        validation_status = relationship_context.get('validation_status')
        
        # Only auto-connect if domain validation passes
        if not domain_validated or validation_status == 'domain_mismatch_warning':
            self.stats['skipped_domain_validation_failed'] += 1
            return {
                'status': 'skipped',
                'reason': 'domain_validation_failed',
                'validation_status': validation_status,
                'contact_id': contact_record.id
            }
        
        # Connect the conversation
        with transaction.atomic():
            result = self._connect_conversation_to_contact(
                conversation, contact_record, relationship_context, recent_message
            )
        
        if result['success']:
            self.stats['resolved'] += 1
            return {
                'status': 'resolved',
                'contact_id': contact_record.id,
                'contact_pipeline_id': contact_record.pipeline.id,
                'domain_validated': True
            }
        else:
            self.stats['errors'] += 1
            return {'status': 'error', 'error': result['error']}
    
    def _connect_conversation_to_contact(
        self, 
        conversation: Conversation, 
        contact_record: Record, 
        relationship_context: Dict[str, Any],
        recent_message: Message
    ) -> Dict[str, Any]:
        """Connect conversation to contact record with metadata"""
        try:
            # Update conversation
            conversation.primary_contact_record = contact_record
            
            # Update metadata with resolution info
            if not conversation.metadata:
                conversation.metadata = {}
            
            conversation.metadata.update({
                'auto_resolved': True,
                'auto_resolved_at': timezone.now().isoformat(),
                'resolution_method': 'automatic_service',
                'contact_record_id': contact_record.id,
                'contact_pipeline_id': contact_record.pipeline.id,
                'domain_validated': True,
                'relationship_context': relationship_context,
                'resolver_tenant_id': self.tenant_id
            })
            
            conversation.save()
            
            # Update the message
            recent_message.contact_record = contact_record
            
            if not recent_message.metadata:
                recent_message.metadata = {}
            recent_message.metadata.update({
                'auto_resolved': True,
                'auto_resolved_at': timezone.now().isoformat()
            })
            
            recent_message.save()
            
            logger.info(f"Successfully connected conversation {conversation.id} to contact {contact_record.id}")
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error connecting conversation {conversation.id} to contact {contact_record.id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_contact_data_from_message(self, message: Message) -> Dict[str, Any]:
        """Extract contact data from message (wrapper for task function)"""
        from communications.tasks import extract_contact_data_from_message
        return extract_contact_data_from_message(message)
    
    def _calculate_match_score(self, contact_data: Dict[str, Any], record_data: Dict[str, Any]) -> float:
        """
        Calculate a simple match score between contact data and record data
        
        Args:
            contact_data: Contact data from message
            record_data: Record data from database
            
        Returns:
            float: Match score between 0.0 and 1.0
        """
        if not contact_data or not record_data:
            return 0.0
        
        score = 0.0
        matches = 0
        total_checks = 0
        
        # Email match (highest weight)
        if 'email' in contact_data:
            total_checks += 1
            contact_email = str(contact_data['email']).lower().strip()
            
            for field_name in ['email', 'email_address', 'contact_email', 'business_email']:
                if field_name in record_data:
                    record_email = str(record_data[field_name]).lower().strip()
                    if contact_email == record_email:
                        score += 0.5  # High weight for email match
                        matches += 1
                        break
        
        # Phone match
        if 'phone' in contact_data:
            total_checks += 1
            contact_phone = str(contact_data['phone']).strip()
            
            for field_name in ['phone', 'phone_number', 'contact_phone', 'mobile']:
                if field_name in record_data:
                    record_phone = str(record_data[field_name]).strip()
                    if contact_phone == record_phone:
                        score += 0.3  # Medium weight for phone match
                        matches += 1
                        break
        
        # Name match (fuzzy)
        if 'name' in contact_data:
            total_checks += 1
            contact_name = str(contact_data['name']).lower().strip()
            
            for field_name in ['name', 'full_name', 'contact_name', 'first_name', 'last_name']:
                if field_name in record_data:
                    record_name = str(record_data[field_name]).lower().strip()
                    if contact_name in record_name or record_name in contact_name:
                        score += 0.2  # Lower weight for name match
                        matches += 1
                        break
        
        # Return normalized score
        return min(score, 1.0) if total_checks > 0 else 0.0
    
    def _get_matched_fields(self, contact_data: Dict[str, Any], record_data: Dict[str, Any]) -> List[str]:
        """Get list of fields that match between contact data and record data"""
        matched_fields = []
        
        # Check email matches
        if 'email' in contact_data:
            contact_email = str(contact_data['email']).lower()
            for field_name in ['email', 'email_address', 'contact_email', 'business_email']:
                if field_name in record_data:
                    record_email = str(record_data[field_name]).lower()
                    if contact_email == record_email:
                        matched_fields.append(f"email({field_name})")
                        break
        
        # Check phone matches
        if 'phone' in contact_data:
            contact_phone = str(contact_data['phone'])
            for field_name in ['phone', 'phone_number', 'contact_phone', 'mobile']:
                if field_name in record_data:
                    record_phone = str(record_data[field_name])
                    if contact_phone == record_phone:
                        matched_fields.append(f"phone({field_name})")
                        break
        
        return matched_fields
    
    def _reset_stats(self):
        """Reset resolution statistics"""
        self.stats = {
            'processed': 0,
            'resolved': 0,
            'skipped_no_contact_data': 0,
            'skipped_no_matches': 0,
            'skipped_domain_validation_failed': 0,
            'errors': 0
        }
    
    def _get_results_summary(self) -> Dict[str, Any]:
        """Get summary of resolution results"""
        total_processed = self.stats['processed']
        resolution_rate = (self.stats['resolved'] / total_processed * 100) if total_processed > 0 else 0
        
        return {
            'success': True,
            'statistics': self.stats.copy(),
            'resolution_rate': f"{resolution_rate:.1f}%",
            'summary': f"Processed {total_processed}, resolved {self.stats['resolved']}"
        }
    
    def get_unconnected_conversation_stats(self) -> Dict[str, Any]:
        """
        Get statistics about unconnected conversations
        
        Returns:
            dict: Statistics about unconnected conversations
        """
        try:
            # Total unconnected conversations
            total_unconnected = Conversation.objects.filter(
                primary_contact_record__isnull=True,
                status='active'
            ).count()
            
            # Unconnected with recent activity (last 7 days)
            recent_cutoff = timezone.now() - timedelta(days=7)
            recent_unconnected = Conversation.objects.filter(
                primary_contact_record__isnull=True,
                status='active',
                last_message_at__gte=recent_cutoff
            ).count()
            
            # Unconnected by channel type
            from django.db.models import Count
            by_channel_type = list(
                Conversation.objects.filter(
                    primary_contact_record__isnull=True,
                    status='active'
                ).values('channel__channel_type').annotate(
                    count=Count('id')
                ).order_by('-count')
            )
            
            # Auto-resolved conversations (have auto_resolved metadata)
            auto_resolved_count = Conversation.objects.filter(
                primary_contact_record__isnull=False,
                metadata__auto_resolved=True
            ).count()
            
            return {
                'total_unconnected': total_unconnected,
                'recent_unconnected': recent_unconnected,
                'auto_resolved_total': auto_resolved_count,
                'by_channel_type': by_channel_type,
                'last_updated': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting unconnected conversation stats: {e}")
            return {
                'error': str(e),
                'last_updated': timezone.now().isoformat()
            }