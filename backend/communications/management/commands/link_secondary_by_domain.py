"""
Management command to link participants to records as secondary (company) based on domain.
Uses duplicate rule configuration to detect domain fields.
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from django_tenants.utils import schema_context, get_tenant_model
from pipelines.models import Record, Pipeline
from communications.models import Participant
from communications.record_communications.storage import ParticipantLinkManager
from communications.record_communications.signals import get_identifier_fields_from_duplicate_rules


class Command(BaseCommand):
    help = 'Link participants to company records based on domain matching'

    def add_arguments(self, parser):
        parser.add_argument(
            '--record-id',
            type=int,
            help='Specific record ID to process'
        )
        parser.add_argument(
            '--pipeline',
            type=str,
            help='Pipeline slug to process all records in that pipeline'
        )
        parser.add_argument(
            '--tenant',
            type=str,
            required=True,
            help='Tenant schema name'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be linked without making changes'
        )
        parser.add_argument(
            '--force-relink',
            action='store_true',
            help='Relink participants even if they already have a secondary record'
        )
        parser.add_argument(
            '--confidence',
            type=float,
            default=0.8,
            help='Confidence score for domain matches (default: 0.8)'
        )

    def handle(self, *args, **options):
        tenant_schema = options['tenant']
        record_id = options.get('record_id')
        pipeline_slug = options.get('pipeline')
        dry_run = options.get('dry_run', False)
        force_relink = options.get('force_relink', False)
        confidence = options.get('confidence', 0.8)
        
        # Personal email domains to skip
        PERSONAL_EMAIL_DOMAINS = [
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'icloud.com', 'me.com', 'aol.com', 'msn.com', 'live.com'
        ]
        
        # Initialize link manager
        link_manager = ParticipantLinkManager()
        
        with schema_context(tenant_schema):
            # Determine which records to process
            if record_id:
                records = Record.objects.filter(id=record_id)
                if not records.exists():
                    self.stdout.write(self.style.ERROR(f'Record {record_id} not found'))
                    return
            elif pipeline_slug:
                pipeline = Pipeline.objects.filter(slug=pipeline_slug).first()
                if not pipeline:
                    self.stdout.write(self.style.ERROR(f'Pipeline {pipeline_slug} not found'))
                    return
                records = Record.objects.filter(pipeline=pipeline)
            else:
                # Process all records with domain fields
                records = Record.objects.all()
            
            total_linked = 0
            records_processed = 0
            
            for record in records:
                # Get identifier fields from duplicate rules
                identifier_fields_info = get_identifier_fields_from_duplicate_rules(record.pipeline)
                if not identifier_fields_info:
                    continue
                
                # Check if any field uses url_normalized with domain extraction
                from duplicates.models import URLExtractionRule
                domain_fields = []
                for field_slug, field_info in identifier_fields_info.items():
                    if field_info.get('match_type') == 'url_normalized':
                        # Check if this field has URL extraction rules for domains
                        url_rule_ids = field_info.get('url_extraction_rules', [])
                        if url_rule_ids:
                            # Check if any of the rules are domain extraction rules
                            domain_rules = URLExtractionRule.objects.filter(
                                id__in=url_rule_ids,
                                template_type='domain',
                                is_active=True
                            ).exists()
                            if domain_rules:
                                domain_fields.append(field_slug)
                        else:
                            # No specific rules, but url_normalized fields can contain domains
                            domain_fields.append(field_slug)
                
                if not domain_fields:
                    continue
                
                # Extract domains from the record
                domains = set()
                for field_slug in domain_fields:
                    domain_value = record.data.get(field_slug)
                    if domain_value:
                        # Clean the domain (remove www., lowercase)
                        clean_domain = str(domain_value).lower().strip()
                        if clean_domain.startswith('www.'):
                            clean_domain = clean_domain[4:]
                        if clean_domain:
                            domains.add(clean_domain)
                
                if not domains:
                    continue
                
                records_processed += 1
                record_linked = 0
                
                self.stdout.write(f"\nProcessing record {record.id} ({record.pipeline.name})")
                self.stdout.write(f"  Domains: {', '.join(domains)}")
                
                # Process each domain
                for domain in domains:
                    # Skip personal domains
                    if domain in PERSONAL_EMAIL_DOMAINS:
                        self.stdout.write(f"  Skipping personal domain: {domain}")
                        continue
                    
                    # Find participants with this email domain
                    if force_relink:
                        participants = Participant.objects.filter(
                            email__iendswith=f"@{domain}"
                        )
                    else:
                        participants = Participant.objects.filter(
                            email__iendswith=f"@{domain}",
                            secondary_record__isnull=True
                        )
                    
                    for participant in participants:
                        if dry_run:
                            self.stdout.write(
                                f"  [DRY RUN] Would link participant {participant.id} "
                                f"({participant.email}) to record {record.id}"
                            )
                        else:
                            # Link as secondary (company) record
                            if link_manager.link_participant_to_record(
                                participant=participant,
                                record=record,
                                confidence=confidence,
                                method='domain_match_manual',
                                as_secondary=True
                            ):
                                record_linked += 1
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"  Linked participant {participant.id} "
                                        f"({participant.email}) to record {record.id}"
                                    )
                                )
                
                if record_linked > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  Total linked for record {record.id}: {record_linked}"
                        )
                    )
                total_linked += record_linked
            
            # Summary
            self.stdout.write("\n" + "="*50)
            self.stdout.write(self.style.SUCCESS(
                f"Summary: Processed {records_processed} records, "
                f"linked {total_linked} participants"
            ))
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        "\nThis was a dry run - no changes were made. "
                        "Remove --dry-run to apply changes."
                    )
                )