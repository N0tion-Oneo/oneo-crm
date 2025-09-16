"""
Management command to fix missing meeting URLs for scheduled meetings
Attempts to retrieve meeting URLs from calendar events or generate fallback URLs
"""
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from communications.scheduling.models import ScheduledMeeting
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fix missing meeting URLs for scheduled meetings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--meeting-id',
            type=str,
            help='Specific meeting ID to fix',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )

    def handle(self, *args, **options):
        meeting_id = options.get('meeting_id')
        dry_run = options.get('dry_run', False)

        if meeting_id:
            meetings = ScheduledMeeting.objects.filter(id=meeting_id)
        else:
            # Find all meetings with Google Meet/Teams/Zoom but no URL
            meetings = ScheduledMeeting.objects.filter(
                meeting_type__location_type__in=['google_meet', 'teams', 'zoom'],
                meeting_url__in=['', None],
                calendar_event_id__isnull=False
            )

        self.stdout.write(f"Found {meetings.count()} meetings to check")

        fixed_count = 0
        for meeting in meetings:
            self.stdout.write(f"\nChecking meeting {meeting.id}")
            self.stdout.write(f"  Meeting Type: {meeting.meeting_type.name}")
            self.stdout.write(f"  Location Type: {meeting.meeting_type.location_type}")
            self.stdout.write(f"  Calendar Event ID: {meeting.calendar_event_id}")
            self.stdout.write(f"  Current URL: '{meeting.meeting_url}'")

            # Try to get URL from various sources
            meeting_url = None

            # 1. Check if URL is in booking_data
            if meeting.booking_data:
                meeting_url = meeting.booking_data.get('meeting_url') or meeting.booking_data.get('meeting_link')

            # 2. If this is a Google Meet and we have the calendar event ID,
            #    we can construct the calendar event URL as a fallback
            if not meeting_url and meeting.meeting_type.location_type == 'google_meet' and meeting.calendar_event_id:
                # Google Calendar event URL format
                calendar_url = f"https://calendar.google.com/calendar/event?eid={meeting.calendar_event_id}"
                self.stdout.write(f"  Generated calendar URL: {calendar_url}")

                # Note: This is a calendar event link, not a direct Meet link
                # Users will need to open the calendar event to join the meeting
                meeting_url = calendar_url

                # Also update calendar sync status if it's still pending
                if meeting.calendar_sync_status == 'pending':
                    if not dry_run:
                        meeting.calendar_sync_status = 'synced'

            if meeting_url and meeting_url != meeting.meeting_url:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Found URL: {meeting_url}"))
                if not dry_run:
                    meeting.meeting_url = meeting_url
                    meeting.save(update_fields=['meeting_url', 'calendar_sync_status'])
                    fixed_count += 1
                else:
                    self.stdout.write(self.style.WARNING("  [DRY RUN] Would update URL"))
            else:
                self.stdout.write(self.style.WARNING(f"  ✗ No URL found"))

        if dry_run:
            self.stdout.write(self.style.WARNING(f"\n[DRY RUN] Would fix {fixed_count} meetings"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n✓ Fixed {fixed_count} meetings"))