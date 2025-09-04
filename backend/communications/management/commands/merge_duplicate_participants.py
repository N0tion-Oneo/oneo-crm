"""
Management command to merge duplicate participants who represent the same person
across different communication channels (email, LinkedIn, WhatsApp, etc.)
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q, Count
from django_tenants.utils import schema_context
from communications.models import (
    Participant, ConversationParticipant, Message, 
    Conversation
)
from tenants.models import Tenant
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Merge duplicate participants who represent the same person across different channels'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Tenant schema name to merge participants in',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be merged without making changes',
        )
        parser.add_argument(
            '--auto-merge',
            action='store_true',
            help='Automatically merge participants with matching names',
        )
    
    def handle(self, *args, **options):
        tenant_schema = options.get('tenant')
        dry_run = options.get('dry_run', False)
        auto_merge = options.get('auto_merge', False)
        
        if tenant_schema:
            tenants = [Tenant.objects.get(schema_name=tenant_schema)]
        else:
            tenants = Tenant.objects.exclude(schema_name='public')
        
        for tenant in tenants:
            self.stdout.write(f"\nProcessing tenant: {tenant.schema_name}")
            with schema_context(tenant.schema_name):
                self.merge_participants_for_tenant(dry_run, auto_merge)
    
    def merge_participants_for_tenant(self, dry_run=False, auto_merge=False):
        """Find and merge duplicate participants within a tenant"""
        
        # Find potential duplicates by name
        duplicates = self.find_duplicate_participants()
        
        if not duplicates:
            self.stdout.write("No duplicate participants found")
            return
        
        self.stdout.write(f"Found {len(duplicates)} groups of potential duplicate participants")
        
        for name, participants in duplicates.items():
            self.stdout.write(f"\nPotential duplicates for: {name}")
            
            # Display participant details
            for p in participants:
                channels = []
                if p.email:
                    channels.append(f"email:{p.email}")
                if p.phone:
                    channels.append(f"phone:{p.phone}")
                if p.linkedin_member_urn:
                    channels.append(f"linkedin:{p.linkedin_member_urn[:20]}...")
                
                self.stdout.write(f"  - {p.id}: {', '.join(channels)}")
                self.stdout.write(f"    Conversations: {p.conversation_memberships.count()}")
                self.stdout.write(f"    Messages: {Message.objects.filter(sender_participant=p).count()}")
                self.stdout.write(f"    Linked to record: {p.contact_record_id is not None}")
            
            if auto_merge or self.confirm_merge(participants):
                if not dry_run:
                    self.merge_participants(participants)
                    self.stdout.write(self.style.SUCCESS(f"Merged {len(participants)} participants for {name}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Would merge {len(participants)} participants for {name}"))
    
    def find_duplicate_participants(self):
        """Find participants with the same name but different channel identifiers"""
        
        # Get all participants with names
        participants_with_names = Participant.objects.exclude(
            Q(name='') | Q(name__isnull=True)
        ).order_by('name')
        
        # Group by name
        duplicates = {}
        for p in participants_with_names:
            name = p.name.strip()
            if name:
                if name not in duplicates:
                    duplicates[name] = []
                duplicates[name].append(p)
        
        # Filter to only keep groups with multiple participants
        duplicates = {
            name: participants 
            for name, participants in duplicates.items() 
            if len(participants) > 1
        }
        
        # Additional check: Look for participants where one has email and another has LinkedIn
        # but they might be the same person (even with slightly different names)
        self.find_cross_channel_duplicates(duplicates)
        
        return duplicates
    
    def find_cross_channel_duplicates(self, existing_duplicates):
        """Find participants that might be the same person across channels"""
        
        # Get all participants with email
        email_participants = Participant.objects.exclude(
            Q(email='') | Q(email__isnull=True)
        )
        
        # Get all participants with LinkedIn
        linkedin_participants = Participant.objects.exclude(
            Q(linkedin_member_urn='') | Q(linkedin_member_urn__isnull=True)
        )
        
        # Check if any email participant has a similar name to a LinkedIn participant
        for email_p in email_participants:
            if not email_p.name:
                continue
                
            email_name_parts = set(email_p.name.lower().split())
            
            for linkedin_p in linkedin_participants:
                if not linkedin_p.name or email_p.id == linkedin_p.id:
                    continue
                
                linkedin_name_parts = set(linkedin_p.name.lower().split())
                
                # Check for name overlap (at least 2 matching parts)
                overlap = email_name_parts & linkedin_name_parts
                if len(overlap) >= 2:
                    # Found potential match
                    key = f"{email_p.name} / {linkedin_p.name}"
                    if key not in existing_duplicates:
                        # Check if they're not already in a group
                        already_grouped = False
                        for group in existing_duplicates.values():
                            if email_p in group or linkedin_p in group:
                                # Add the other one to the existing group
                                if email_p not in group:
                                    group.append(email_p)
                                if linkedin_p not in group:
                                    group.append(linkedin_p)
                                already_grouped = True
                                break
                        
                        if not already_grouped:
                            existing_duplicates[key] = [email_p, linkedin_p]
    
    def confirm_merge(self, participants):
        """Ask user to confirm merge"""
        response = input(f"Merge these {len(participants)} participants? (y/n): ")
        return response.lower() == 'y'
    
    @transaction.atomic
    def merge_participants(self, participants):
        """Merge multiple participants into one"""
        
        if len(participants) < 2:
            return
        
        # Sort by creation date and number of conversations to pick the primary
        participants = sorted(
            participants, 
            key=lambda p: (
                p.contact_record_id is not None,  # Prioritize linked participants
                p.conversation_memberships.count(),  # Then by conversation count
                p.first_seen  # Then by earliest seen
            ),
            reverse=True
        )
        
        primary = participants[0]
        to_merge = participants[1:]
        
        self.stdout.write(f"Primary participant: {primary.id} ({primary.name})")
        
        # Merge all channel identifiers into the primary participant
        for p in to_merge:
            # Merge email
            if p.email and not primary.email:
                primary.email = p.email
                self.stdout.write(f"  Added email: {p.email}")
            
            # Merge phone
            if p.phone and not primary.phone:
                primary.phone = p.phone
                self.stdout.write(f"  Added phone: {p.phone}")
            
            # Merge LinkedIn URN (check for conflicts)
            if p.linkedin_member_urn and not primary.linkedin_member_urn:
                # Check if another participant already has this LinkedIn URN
                existing = Participant.objects.filter(
                    linkedin_member_urn=p.linkedin_member_urn
                ).exclude(id__in=[primary.id, p.id]).exists()
                
                if not existing:
                    primary.linkedin_member_urn = p.linkedin_member_urn
                    self.stdout.write(f"  Added LinkedIn URN: {p.linkedin_member_urn[:30]}...")
                else:
                    self.stdout.write(f"  WARNING: Cannot add LinkedIn URN (already exists): {p.linkedin_member_urn[:30]}...")
            
            # Merge other social identifiers
            if p.instagram_username and not primary.instagram_username:
                primary.instagram_username = p.instagram_username
            if p.facebook_id and not primary.facebook_id:
                primary.facebook_id = p.facebook_id
            if p.telegram_id and not primary.telegram_id:
                primary.telegram_id = p.telegram_id
            if p.twitter_handle and not primary.twitter_handle:
                primary.twitter_handle = p.twitter_handle
            
            # Merge metadata
            if p.metadata:
                primary.metadata.update(p.metadata)
            
            # Use the best name (longest, most complete)
            if p.name and len(p.name) > len(primary.name or ''):
                primary.name = p.name
            
            # Keep the best avatar URL
            if p.avatar_url and not primary.avatar_url:
                primary.avatar_url = p.avatar_url
            
            # Keep the linked record if the primary doesn't have one
            if p.contact_record_id and not primary.contact_record_id:
                primary.contact_record_id = p.contact_record_id
                primary.resolution_confidence = p.resolution_confidence
                primary.resolution_method = p.resolution_method
                primary.resolved_at = p.resolved_at
            
            # Update conversation participants
            ConversationParticipant.objects.filter(participant=p).update(participant=primary)
            
            # Update messages
            Message.objects.filter(sender_participant=p).update(sender_participant=primary)
            
            # Update statistics
            primary.total_conversations += p.total_conversations
            primary.total_messages += p.total_messages
            
            # Keep earliest first_seen
            if p.first_seen < primary.first_seen:
                primary.first_seen = p.first_seen
            
            # Keep latest last_seen  
            if p.last_seen > primary.last_seen:
                primary.last_seen = p.last_seen
        
        # Save the primary participant with all merged data
        primary.save()
        
        # Delete the merged participants
        for p in to_merge:
            self.stdout.write(f"  Deleting participant: {p.id}")
            p.delete()
        
        self.stdout.write(self.style.SUCCESS(f"Successfully merged {len(participants)} participants into {primary.id}"))