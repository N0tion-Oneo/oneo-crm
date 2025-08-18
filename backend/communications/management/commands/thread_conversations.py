"""
Management command for conversation threading operations
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db import models
from communications.services.conversation_threading import conversation_threading_service
from pipelines.models import Record, Pipeline
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create conversation threads for Records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--record-id',
            type=int,
            help='Thread conversations for a specific Record ID'
        )
        
        parser.add_argument(
            '--pipeline',
            type=str,
            help='Thread conversations for all Records in a specific pipeline (by name)'
        )
        
        parser.add_argument(
            '--all',
            action='store_true',
            help='Thread conversations for all Records with communication activity'
        )
        
        parser.add_argument(
            '--force-rethread',
            action='store_true',
            help='Force re-threading of existing conversation threads'
        )
        
        parser.add_argument(
            '--analyze-only',
            action='store_true',
            help='Only analyze threading opportunities without creating threads'
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Batch size for processing Records (default: 50)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        """Handle the management command"""
        
        # Validate arguments
        if not any([options['record_id'], options['pipeline'], options['all']]):
            raise CommandError('Must specify --record-id, --pipeline, or --all')
        
        if sum(bool(opt) for opt in [options['record_id'], options['pipeline'], options['all']]) > 1:
            raise CommandError('Can only specify one of --record-id, --pipeline, or --all')
        
        # Get Records to process
        records = self._get_records_to_process(options)
        
        if not records:
            self.stdout.write(self.style.WARNING('No Records found matching criteria'))
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'Found {len(records)} Records to process')
        )
        
        # Process Records
        if options['analyze_only']:
            self._analyze_threading_opportunities(records, options)
        else:
            self._create_conversation_threads(records, options)

    def _get_records_to_process(self, options):
        """Get the Records to process based on command options"""
        
        if options['record_id']:
            # Single Record
            try:
                record = Record.objects.get(id=options['record_id'], is_deleted=False)
                return [record]
            except Record.DoesNotExist:
                raise CommandError(f'Record {options["record_id"]} not found')
        
        elif options['pipeline']:
            # Records in specific pipeline
            try:
                pipeline = Pipeline.objects.get(name=options['pipeline'])
                return list(Record.objects.filter(pipeline=pipeline, is_deleted=False))
            except Pipeline.DoesNotExist:
                raise CommandError(f'Pipeline "{options["pipeline"]}" not found')
        
        elif options['all']:
            # All Records with communication activity
            records = Record.objects.filter(
                is_deleted=False
            ).filter(
                # Records that have conversations or messages
                models.Q(primary_conversations__isnull=False) |
                models.Q(message_contact_records__isnull=False)
            ).distinct()
            
            return list(records)
        
        return []

    def _analyze_threading_opportunities(self, records, options):
        """Analyze threading opportunities for Records"""
        
        self.stdout.write(
            self.style.SUCCESS(f'Analyzing threading opportunities for {len(records)} Records...')
        )
        
        analysis_results = []
        
        for record in records:
            self.stdout.write(f'Analyzing Record {record.id}: {record.title}')
            
            try:
                conversations = conversation_threading_service._get_record_conversations(record)
                messages = conversation_threading_service._get_record_messages(record)
                
                if not conversations and not messages:
                    self.stdout.write(f'  No communication activity found')
                    continue
                
                analysis = conversation_threading_service._analyze_threading_opportunities(
                    record, conversations, messages
                )
                
                analysis_results.append({
                    'record': record,
                    'analysis': analysis
                })
                
                # Display analysis summary
                self._display_analysis_summary(record, analysis)
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  Error analyzing Record {record.id}: {e}')
                )
        
        # Display overall summary
        self._display_overall_analysis_summary(analysis_results)

    def _display_analysis_summary(self, record, analysis):
        """Display analysis summary for a Record"""
        
        self.stdout.write(f'  Conversations: {analysis["total_conversations"]}')
        self.stdout.write(f'  Messages: {analysis["total_messages"]}')
        self.stdout.write(f'  Channels: {", ".join(analysis["channels_involved"])}')
        
        if analysis['time_span']:
            duration = analysis['time_span']['duration_days']
            self.stdout.write(f'  Time span: {duration} days')
        
        # Threading signals
        signals = analysis['threading_signals']
        self.stdout.write('  Threading signals:')
        
        for signal_type, signal_data in signals.items():
            potential = signal_data.get('threading_potential', 'unknown')
            if potential != 'low':
                self.stdout.write(f'    {signal_type}: {potential}')
        
        # Potential threads
        potential_threads = analysis['potential_threads']
        if potential_threads:
            self.stdout.write(f'  Potential threads: {len(potential_threads)}')
            for thread in potential_threads:
                confidence = thread.get('confidence', 0)
                self.stdout.write(
                    f'    {thread["type"]}: {confidence:.1%} confidence'
                )

    def _display_overall_analysis_summary(self, analysis_results):
        """Display overall analysis summary"""
        
        if not analysis_results:
            return
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('OVERALL ANALYSIS SUMMARY'))
        self.stdout.write('='*50)
        
        total_records = len(analysis_results)
        total_conversations = sum(r['analysis']['total_conversations'] for r in analysis_results)
        total_messages = sum(r['analysis']['total_messages'] for r in analysis_results)
        
        self.stdout.write(f'Total Records analyzed: {total_records}')
        self.stdout.write(f'Total Conversations: {total_conversations}')
        self.stdout.write(f'Total Messages: {total_messages}')
        
        # High-potential threading candidates
        high_potential = [
            r for r in analysis_results 
            if any(thread.get('confidence', 0) >= 0.7 for thread in r['analysis']['potential_threads'])
        ]
        
        medium_potential = [
            r for r in analysis_results 
            if any(0.4 <= thread.get('confidence', 0) < 0.7 for thread in r['analysis']['potential_threads'])
        ]
        
        self.stdout.write(f'High threading potential: {len(high_potential)} Records')
        self.stdout.write(f'Medium threading potential: {len(medium_potential)} Records')
        
        if high_potential:
            self.stdout.write('\nHigh-potential Records:')
            for result in high_potential[:10]:  # Show top 10
                record = result['record']
                self.stdout.write(f'  {record.id}: {record.title}')

    def _create_conversation_threads(self, records, options):
        """Create conversation threads for Records"""
        
        batch_size = options['batch_size']
        force_rethread = options['force_rethread']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Creating conversation threads for {len(records)} Records '
                f'(batch size: {batch_size})...'
            )
        )
        
        successful_threads = 0
        failed_threads = 0
        total_messages_threaded = 0
        
        # Process in batches
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(records) + batch_size - 1) // batch_size
            
            self.stdout.write(f'Processing batch {batch_num}/{total_batches}...')
            
            for record in batch:
                try:
                    if dry_run:
                        # Just analyze for dry run
                        conversations = conversation_threading_service._get_record_conversations(record)
                        messages = conversation_threading_service._get_record_messages(record)
                        
                        if conversations or messages:
                            self.stdout.write(
                                f'  Would thread Record {record.id}: {record.title} '
                                f'({len(conversations)} conversations, {len(messages)} messages)'
                            )
                        continue
                    
                    # Create threads
                    result = conversation_threading_service.create_unified_conversation_thread(
                        record=record,
                        force_rethread=force_rethread
                    )
                    
                    if result['success']:
                        successful_threads += 1
                        messages_threaded = result.get('messages_threaded', 0)
                        total_messages_threaded += messages_threaded
                        
                        self.stdout.write(
                            f'  ✓ Record {record.id}: {result["threads_created"]} threads, '
                            f'{messages_threaded} messages'
                        )
                    else:
                        failed_threads += 1
                        error = result.get('error', 'Unknown error')
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ Record {record.id}: {error}')
                        )
                
                except Exception as e:
                    failed_threads += 1
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Record {record.id}: {e}')
                    )
                    logger.error(f'Error threading Record {record.id}: {e}')
        
        # Display final summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('THREADING SUMMARY'))
        self.stdout.write('='*50)
        
        if not dry_run:
            self.stdout.write(f'Records processed: {len(records)}')
            self.stdout.write(f'Successful threads: {successful_threads}')
            self.stdout.write(f'Failed threads: {failed_threads}')
            self.stdout.write(f'Total messages threaded: {total_messages_threaded}')
            
            if len(records) > 0:
                success_rate = (successful_threads / len(records)) * 100
                self.stdout.write(f'Success rate: {success_rate:.1f}%')
        else:
            self.stdout.write('Dry run completed - no changes made')