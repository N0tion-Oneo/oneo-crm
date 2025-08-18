"""
Django management command for manual contact resolution
Allows administrators to manually trigger contact resolution for unconnected conversations
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django_tenants.utils import get_tenant_model, schema_context
from communications.services.auto_resolution import UnconnectedConversationResolver
from communications.models import Conversation
import json


class Command(BaseCommand):
    help = 'Manually resolve unconnected conversations to existing contact records'
    
    def add_arguments(self, parser):
        """Add command arguments"""
        parser.add_argument(
            '--tenant',
            type=str,
            help='Tenant schema name to process (if not provided, processes all tenants)'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of conversations to process (default: 50)'
        )
        
        parser.add_argument(
            '--conversation-ids',
            type=str,
            help='Comma-separated list of specific conversation IDs to resolve'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be resolved without making changes'
        )
        
        parser.add_argument(
            '--stats-only',
            action='store_true',
            help='Show statistics about unconnected conversations only'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed progress and results'
        )
        
        parser.add_argument(
            '--format',
            choices=['text', 'json'],
            default='text',
            help='Output format (default: text)'
        )
    
    def handle(self, *args, **options):
        """Execute the command"""
        try:
            if options['tenant']:
                # Process specific tenant
                self._process_tenant(options['tenant'], options)
            else:
                # Process all tenants
                self._process_all_tenants(options)
                
        except Exception as e:
            if options['format'] == 'json':
                self.stdout.write(json.dumps({
                    'success': False,
                    'error': str(e)
                }, indent=2))
            else:
                raise CommandError(f"Command failed: {e}")
    
    def _process_all_tenants(self, options):
        """Process all tenants"""
        tenant_model = get_tenant_model()
        tenants = tenant_model.objects.exclude(schema_name='public')
        
        if options['format'] == 'json':
            all_results = {
                'tenants_processed': 0,
                'tenant_results': []
            }
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Processing {len(tenants)} tenants for contact resolution"
                )
            )
        
        for tenant in tenants:
            try:
                result = self._process_tenant(tenant.schema_name, options, part_of_batch=True)
                
                if options['format'] == 'json':
                    all_results['tenants_processed'] += 1
                    all_results['tenant_results'].append({
                        'tenant_name': tenant.name,
                        'schema_name': tenant.schema_name,
                        'result': result
                    })
                else:
                    self.stdout.write(
                        f"✓ {tenant.name} ({tenant.schema_name}): {result.get('summary', 'processed')}"
                    )
                    
            except Exception as e:
                if options['format'] == 'json':
                    all_results['tenant_results'].append({
                        'tenant_name': tenant.name,
                        'schema_name': tenant.schema_name,
                        'result': {'success': False, 'error': str(e)}
                    })
                else:
                    self.stdout.write(
                        self.style.ERROR(f"✗ {tenant.name}: {e}")
                    )
        
        if options['format'] == 'json':
            self.stdout.write(json.dumps(all_results, indent=2))
        else:
            self.stdout.write(
                self.style.SUCCESS("All tenants processed")
            )
    
    def _process_tenant(self, tenant_schema: str, options, part_of_batch: bool = False):
        """Process a specific tenant"""
        with schema_context(tenant_schema):
            # Get tenant ID
            tenant_id = connection.tenant.id if hasattr(connection, 'tenant') else None
            if not tenant_id:
                raise CommandError(f"Could not determine tenant ID for schema {tenant_schema}")
            
            # Initialize resolver
            resolver = UnconnectedConversationResolver(tenant_id=tenant_id)
            
            # Stats only mode
            if options['stats_only']:
                stats = resolver.get_unconnected_conversation_stats()
                
                if options['format'] == 'json':
                    return {
                        'tenant_schema': tenant_schema,
                        'mode': 'stats_only',
                        'statistics': stats
                    }
                else:
                    if not part_of_batch:
                        self._print_stats(stats, tenant_schema)
                    return {'summary': f"{stats.get('total_unconnected', 0)} unconnected conversations"}
            
            # Dry run mode - show candidates
            if options['dry_run']:
                return self._handle_dry_run(resolver, options, tenant_schema)
            
            # Actual resolution
            if options['conversation_ids']:
                # Resolve specific conversations
                conversation_ids = [
                    id.strip() for id in options['conversation_ids'].split(',')
                ]
                result = resolver.resolve_specific_conversations(conversation_ids)
            else:
                # Batch resolution
                result = resolver.resolve_batch(
                    limit=options['limit'],
                    priority_recent=True
                )
            
            if options['format'] == 'json':
                result['tenant_schema'] = tenant_schema
                if not part_of_batch:
                    self.stdout.write(json.dumps(result, indent=2))
                return result
            else:
                if not part_of_batch:
                    self._print_results(result, tenant_schema, options['verbose'])
                return result
    
    def _handle_dry_run(self, resolver, options, tenant_schema):
        """Handle dry run mode"""
        if options['conversation_ids']:
            # Specific conversations
            conversation_ids = [
                id.strip() for id in options['conversation_ids'].split(',')
            ]
            candidates_info = []
            
            for conv_id in conversation_ids:
                try:
                    conversation = Conversation.objects.get(id=conv_id)
                    candidates = resolver.get_resolution_candidates(conversation, limit=3)
                    candidates_info.append({
                        'conversation_id': conv_id,
                        'candidates': candidates
                    })
                except Conversation.DoesNotExist:
                    candidates_info.append({
                        'conversation_id': conv_id,
                        'error': 'Conversation not found'
                    })
        else:
            # Get sample of unconnected conversations
            conversations = Conversation.objects.filter(
                primary_contact_record__isnull=True,
                status='active'
            ).order_by('-last_message_at')[:min(options['limit'], 10)]
            
            candidates_info = []
            for conversation in conversations:
                candidates = resolver.get_resolution_candidates(conversation, limit=3)
                candidates_info.append({
                    'conversation_id': str(conversation.id),
                    'conversation_subject': conversation.subject or 'No subject',
                    'candidates': candidates
                })
        
        result = {
            'tenant_schema': tenant_schema,
            'mode': 'dry_run',
            'conversation_candidates': candidates_info
        }
        
        if options['format'] == 'json':
            return result
        else:
            self._print_dry_run_results(candidates_info, tenant_schema)
            return {'summary': f"Analyzed {len(candidates_info)} conversations"}
    
    def _print_stats(self, stats, tenant_schema):
        """Print statistics in text format"""
        self.stdout.write(
            self.style.SUCCESS(f"\nUnconnected Conversation Statistics - {tenant_schema}")
        )
        self.stdout.write("=" * 60)
        
        self.stdout.write(f"Total unconnected: {stats.get('total_unconnected', 0)}")
        self.stdout.write(f"Recent unconnected (7 days): {stats.get('recent_unconnected', 0)}")
        self.stdout.write(f"Auto-resolved total: {stats.get('auto_resolved_total', 0)}")
        
        if stats.get('by_channel_type'):
            self.stdout.write("\nBy channel type:")
            for channel_data in stats['by_channel_type']:
                self.stdout.write(
                    f"  {channel_data['channel__channel_type']}: {channel_data['count']}"
                )
    
    def _print_results(self, result, tenant_schema, verbose):
        """Print resolution results in text format"""
        if 'statistics' in result:
            stats = result['statistics']
            self.stdout.write(
                self.style.SUCCESS(f"\nResolution Results - {tenant_schema}")
            )
            self.stdout.write("=" * 50)
            self.stdout.write(f"Processed: {stats['processed']}")
            self.stdout.write(f"Resolved: {stats['resolved']}")
            self.stdout.write(f"Resolution rate: {result.get('resolution_rate', '0%')}")
            
            if verbose:
                self.stdout.write(f"Skipped - no contact data: {stats['skipped_no_contact_data']}")
                self.stdout.write(f"Skipped - no matches: {stats['skipped_no_matches']}")
                self.stdout.write(f"Skipped - domain validation failed: {stats['skipped_domain_validation_failed']}")
                self.stdout.write(f"Errors: {stats['errors']}")
        
        if 'conversation_results' in result and verbose:
            self.stdout.write("\nIndividual results:")
            for conv_result in result['conversation_results']:
                status = conv_result['status']
                conv_id = conv_result['conversation_id']
                
                if status == 'resolved':
                    contact_id = conv_result['result']['contact_id']
                    self.stdout.write(f"  ✓ {conv_id} → Contact {contact_id}")
                elif status == 'already_connected':
                    contact_id = conv_result['contact_id']
                    self.stdout.write(f"  ~ {conv_id} (already → Contact {contact_id})")
                else:
                    self.stdout.write(f"  ✗ {conv_id} ({status})")
    
    def _print_dry_run_results(self, candidates_info, tenant_schema):
        """Print dry run results in text format"""
        self.stdout.write(
            self.style.WARNING(f"\nDry Run Results - {tenant_schema}")
        )
        self.stdout.write("=" * 50)
        
        for info in candidates_info:
            conv_id = info['conversation_id']
            self.stdout.write(f"\nConversation {conv_id}:")
            
            if 'error' in info:
                self.stdout.write(f"  Error: {info['error']}")
                continue
            
            candidates = info.get('candidates', [])
            if not candidates:
                self.stdout.write("  No potential matches found")
                continue
            
            self.stdout.write(f"  Found {len(candidates)} potential matches:")
            for candidate in candidates:
                score = candidate['match_score']
                record_title = candidate['record_title']
                pipeline_name = candidate['pipeline_name']
                domain_status = "✓" if candidate['domain_validated'] else "✗"
                
                self.stdout.write(
                    f"    {score:.2f} - {record_title} ({pipeline_name}) {domain_status}"
                )
                
                if candidate['contact_data_matched']:
                    matched = ", ".join(candidate['contact_data_matched'])
                    self.stdout.write(f"      Matched: {matched}")