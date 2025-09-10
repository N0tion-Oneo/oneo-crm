"""
Scheduling models for meeting bookings and availability management
Integrated with the communications system for unified participant and conversation tracking
"""
import uuid
from datetime import timedelta
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

from communications.models import Channel, Conversation, Participant, UserChannelConnection
from pipelines.models import Pipeline, Record

User = get_user_model()


class SchedulingProfile(models.Model):
    """
    User availability settings for scheduling
    Each user can have one profile per calendar connection
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User and calendar connection via UniPile
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scheduling_profiles')
    calendar_connection = models.ForeignKey(
        UserChannelConnection,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        limit_choices_to={'channel_type__in': ['calendar', 'gmail', 'outlook']},
        related_name='scheduling_profile',
        help_text="User's connected calendar account (Google/Outlook via UniPile)"
    )
    
    # Timezone and basic settings
    timezone = models.CharField(max_length=100, default='UTC')
    buffer_minutes = models.IntegerField(
        default=15,
        validators=[MinValueValidator(0), MaxValueValidator(120)],
        help_text="Buffer time between meetings in minutes"
    )
    min_notice_hours = models.IntegerField(
        default=24,
        validators=[MinValueValidator(0), MaxValueValidator(168)],
        help_text="Minimum advance notice required for bookings"
    )
    max_advance_days = models.IntegerField(
        default=60,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        help_text="Maximum days in advance for bookings"
    )
    
    # Slot interval for incremental time slot generation
    slot_interval_minutes = models.IntegerField(
        default=30,
        choices=[
            (15, '15 minutes'),
            (20, '20 minutes'),
            (30, '30 minutes'),
            (45, '45 minutes'),
            (60, '60 minutes'),
        ],
        validators=[MinValueValidator(15), MaxValueValidator(60)],
        help_text="Time interval for generating available slots"
    )
    
    # Working hours configuration
    # Format: {"monday": [{"start": "09:00", "end": "17:00"}], ...}
    working_hours = models.JSONField(
        default=dict,
        help_text="Working hours per day of week"
    )
    
    # Availability preferences
    calendar_sync_enabled = models.BooleanField(
        default=True,
        help_text="Check calendar for conflicts when calculating availability"
    )
    show_busy_slots = models.BooleanField(
        default=False,
        help_text="Show busy slots to external users (privacy setting)"
    )
    
    # Override dates (for holidays, time off, etc.)
    blocked_dates = models.JSONField(
        default=list,
        help_text="List of dates when unavailable"
    )
    override_dates = models.JSONField(
        default=dict,
        help_text="Specific date overrides with custom hours"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['calendar_connection']),
            models.Index(fields=['user'], name='scheduling_user_idx'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Scheduling Profile"
    
    def get_default_working_hours(self):
        """Return default working hours if not configured"""
        if not self.working_hours:
            return {
                "monday": [{"start": "09:00", "end": "17:00"}],
                "tuesday": [{"start": "09:00", "end": "17:00"}],
                "wednesday": [{"start": "09:00", "end": "17:00"}],
                "thursday": [{"start": "09:00", "end": "17:00"}],
                "friday": [{"start": "09:00", "end": "17:00"}],
                "saturday": [],
                "sunday": []
            }
        return self.working_hours


class MeetingType(models.Model):
    """
    Meeting templates that define duration, location, and booking forms
    Each meeting type has its own booking URL and calendar configuration
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Owner and basic info
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meeting_types')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, help_text="Clean URL for this meeting type")
    description = models.TextField(blank=True)
    
    # Calendar configuration - uses specific calendar from user's profile connection
    calendar_id = models.CharField(
        max_length=255,
        blank=True,  # Temporarily blank for migration
        default='',  # Default empty string for migration
        help_text="Specific calendar ID within the account for this meeting type"
    )
    calendar_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Name of the selected calendar for display purposes"
    )
    
    # Duration and scheduling
    duration_minutes = models.IntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(480)]
    )
    
    # Location configuration
    LOCATION_TYPES = [
        ('zoom', 'Zoom Meeting'),
        ('google_meet', 'Google Meet'),
        ('teams', 'Microsoft Teams'),
        ('phone', 'Phone Call'),
        ('in_person', 'In Person'),
        ('custom', 'Custom Location'),
    ]
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPES, default='google_meet')
    location_details = models.JSONField(
        default=dict,
        help_text="Additional location configuration (room, address, etc.)"
    )
    
    # Pipeline integration
    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Pipeline for creating/updating records"
    )
    pipeline_stage = models.CharField(
        max_length=100,
        blank=True,
        help_text="Stage to set for new records"
    )
    
    # Booking form configuration
    booking_form_config = models.JSONField(
        default=dict,
        help_text="Which pipeline fields to show on booking form"
    )
    custom_questions = models.JSONField(
        default=list,
        help_text="Additional questions for booking form"
    )
    required_fields = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        help_text="Required pipeline fields for booking"
    )
    
    # Templates
    confirmation_template = models.TextField(
        blank=True,
        help_text="Email template for booking confirmation"
    )
    reminder_template = models.TextField(
        blank=True,
        help_text="Email template for meeting reminders"
    )
    cancellation_template = models.TextField(
        blank=True,
        help_text="Email template for cancellations"
    )
    
    # Settings
    allow_rescheduling = models.BooleanField(default=True)
    allow_cancellation = models.BooleanField(default=True)
    cancellation_notice_hours = models.IntegerField(
        default=24,
        validators=[MinValueValidator(0), MaxValueValidator(168)]
    )
    send_reminders = models.BooleanField(default=True)
    reminder_hours = ArrayField(
        models.IntegerField(),
        default=list,
        help_text="Hours before meeting to send reminders (e.g., [24, 1])"
    )
    
    # Analytics
    total_bookings = models.IntegerField(default=0)
    total_completed = models.IntegerField(default=0)
    total_cancelled = models.IntegerField(default=0)
    total_no_shows = models.IntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'slug']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['pipeline']),
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.duration_minutes} min)"
    
    @property
    def calendar_connection(self):
        """Get calendar connection from user's scheduling profile"""
        try:
            profile = self.user.scheduling_profiles.filter(is_active=True).first()
            if profile:
                return profile.calendar_connection
        except Exception:
            pass
        return None
    
    def get_calendar_connection(self):
        """Get calendar connection from user's active scheduling profile"""
        return self.calendar_connection
    
    def save(self, *args, **kwargs):
        """Auto-generate slug if not provided"""
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            # Ensure slug is unique for this user
            while MeetingType.objects.filter(user=self.user, slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    def get_booking_url(self):
        """Get the clean public booking URL for this meeting type"""
        # Format: /book/[firstname-lastname]/[meeting-type-slug]
        # Create a URL-safe version of the user's name
        first_name = self.user.first_name.lower().replace(' ', '-') if self.user.first_name else ''
        last_name = self.user.last_name.lower().replace(' ', '-') if self.user.last_name else ''
        
        # Use username as fallback if no first/last name
        if first_name and last_name:
            user_slug = f"{first_name}-{last_name}"
        else:
            user_slug = self.user.username.lower()
        
        return f"/book/{user_slug}/{self.slug}"
    
    def get_full_booking_url(self, request=None):
        """Get the full URL including domain"""
        from django.conf import settings
        if request:
            host = request.get_host()
            # If this is a backend request (port 8000), use frontend port instead
            if ':8000' in host:
                host = host.replace(':8000', ':3000')
        else:
            # Use tenant domain if available
            from django.db import connection
            if hasattr(connection, 'tenant'):
                domain = connection.tenant.get_primary_domain().domain
                # Ensure we're using frontend port
                if ':8000' in domain:
                    host = domain.replace(':8000', ':3000')
                else:
                    host = f"{domain}:3000" if 'localhost' in domain else domain
            else:
                host = 'localhost:3000'
        
        protocol = 'https' if not host.startswith('localhost') and not '127.0.0.1' in host else 'http'
        return f"{protocol}://{host}{self.get_booking_url()}"
    
    def get_default_reminder_hours(self):
        """Return default reminder hours if not configured"""
        if not self.reminder_hours:
            return [24, 1]  # 24 hours and 1 hour before
        return self.reminder_hours


class SchedulingLink(models.Model):
    """
    Public booking links that allow external users to schedule meetings
    Each link creates a conversation for tracking all interactions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link configuration
    meeting_type = models.ForeignKey(MeetingType, on_delete=models.CASCADE, related_name='scheduling_links')
    slug = models.UUIDField(default=uuid.uuid4, unique=True, help_text="Public URL slug")
    
    # Name and description for the link
    name = models.CharField(max_length=255, help_text="Internal name for this link")
    public_name = models.CharField(max_length=255, blank=True, help_text="Public-facing name")
    public_description = models.TextField(blank=True, help_text="Public-facing description")
    
    # Associated conversation for tracking
    conversation = models.OneToOneField(
        Conversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scheduling_link',
        help_text="Conversation for tracking bookings"
    )
    
    # Pipeline configuration
    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Target pipeline for creating records"
    )
    auto_create_record = models.BooleanField(
        default=True,
        help_text="Automatically create/update records from bookings"
    )
    field_mapping = models.JSONField(
        default=dict,
        help_text="Map booking form fields to pipeline fields"
    )
    
    # Availability settings (can override user's profile)
    override_availability = models.JSONField(
        default=dict,
        help_text="Custom availability for this link"
    )
    
    # Restrictions
    expires_at = models.DateTimeField(null=True, blank=True)
    max_bookings = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of bookings allowed"
    )
    password = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional password protection"
    )
    allowed_emails = ArrayField(
        models.EmailField(),
        default=list,
        blank=True,
        help_text="Restrict to specific email addresses"
    )
    
    # Analytics
    view_count = models.IntegerField(default=0)
    booking_count = models.IntegerField(default=0)
    conversion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Booking rate percentage"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['meeting_type', 'is_active']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.meeting_type.name}"
    
    def is_expired(self):
        """Check if the link has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def has_reached_limit(self):
        """Check if booking limit has been reached"""
        if self.max_bookings:
            return self.booking_count >= self.max_bookings
        return False
    
    def can_book(self, email=None):
        """Check if a booking can be made"""
        if not self.is_active:
            return False, "Link is not active"
        if self.is_expired():
            return False, "Link has expired"
        if self.has_reached_limit():
            return False, "Booking limit reached"
        if self.allowed_emails and email and email not in self.allowed_emails:
            return False, "Email not authorized"
        return True, "Can book"
    
    def increment_view(self):
        """Increment view count and update conversion rate"""
        self.view_count += 1
        if self.view_count > 0:
            self.conversion_rate = (self.booking_count / self.view_count) * 100
        self.save(update_fields=['view_count', 'conversion_rate'])
    
    def increment_booking(self):
        """Increment booking count and update conversion rate"""
        self.booking_count += 1
        if self.view_count > 0:
            self.conversion_rate = (self.booking_count / self.view_count) * 100
        self.save(update_fields=['booking_count', 'conversion_rate'])


class ScheduledMeeting(models.Model):
    """
    Confirmed meetings that have been booked
    Links to conversations for communication tracking
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Meeting configuration
    meeting_type = models.ForeignKey(MeetingType, on_delete=models.CASCADE, related_name='scheduled_meetings')
    scheduling_link = models.ForeignKey(
        SchedulingLink,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scheduled_meetings'
    )
    
    # Conversation and participant tracking
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='scheduled_meetings',
        help_text="Conversation for this meeting"
    )
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='scheduled_meetings',
        help_text="External participant"
    )
    host = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='hosted_meetings',
        help_text="Meeting host"
    )
    
    # Pipeline record (if created/linked)
    record = models.ForeignKey(
        Record,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scheduled_meetings',
        help_text="Associated pipeline record"
    )
    
    # Meeting details
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    timezone = models.CharField(max_length=100, default='UTC')
    
    # Calendar integration
    calendar_event_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="UniPile calendar event ID"
    )
    calendar_sync_status = models.CharField(
        max_length=50,
        default='pending',
        choices=[
            ('pending', 'Pending Sync'),
            ('synced', 'Synced'),
            ('failed', 'Sync Failed'),
        ]
    )
    
    # Meeting location/link
    meeting_url = models.URLField(blank=True)
    meeting_location = models.TextField(blank=True)
    meeting_password = models.CharField(max_length=100, blank=True)
    
    # Booking data
    booking_data = models.JSONField(
        default=dict,
        help_text="Form data captured during booking"
    )
    booking_ip = models.GenericIPAddressField(null=True, blank=True)
    booking_user_agent = models.TextField(blank=True)
    
    # Status tracking
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('reminder_sent', 'Reminder Sent'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Cancellation/rescheduling
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_meetings'
    )
    cancellation_reason = models.TextField(blank=True)
    rescheduled_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rescheduled_from'
    )
    
    # Reminders
    reminder_sent_at = models.JSONField(
        default=list,
        help_text="List of timestamps when reminders were sent"
    )
    
    # Meeting notes
    pre_meeting_notes = models.TextField(blank=True)
    post_meeting_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['start_time', 'status']),
            models.Index(fields=['participant']),
            models.Index(fields=['host', 'start_time']),
            models.Index(fields=['record']),
            models.Index(fields=['status']),
            models.Index(fields=['calendar_event_id']),
            GinIndex(fields=['booking_data']),
        ]
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.meeting_type.name} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def duration(self):
        """Calculate meeting duration"""
        return self.end_time - self.start_time
    
    def is_past(self):
        """Check if meeting is in the past"""
        return timezone.now() > self.end_time
    
    def is_upcoming(self):
        """Check if meeting is upcoming"""
        return timezone.now() < self.start_time
    
    def is_in_progress(self):
        """Check if meeting is currently in progress"""
        now = timezone.now()
        return self.start_time <= now <= self.end_time
    
    def can_cancel(self):
        """Check if meeting can be cancelled"""
        if self.status in ['cancelled', 'completed', 'no_show']:
            return False
        if not self.meeting_type.allow_cancellation:
            return False
        
        # Check cancellation notice
        hours_until = (self.start_time - timezone.now()).total_seconds() / 3600
        if hours_until < self.meeting_type.cancellation_notice_hours:
            return False
        
        return True
    
    def can_reschedule(self):
        """Check if meeting can be rescheduled"""
        if self.status in ['cancelled', 'completed', 'no_show']:
            return False
        if not self.meeting_type.allow_rescheduling:
            return False
        
        # Check if too close to meeting time
        hours_until = (self.start_time - timezone.now()).total_seconds() / 3600
        if hours_until < self.meeting_type.cancellation_notice_hours:
            return False
        
        return True
    
    def mark_completed(self):
        """Mark meeting as completed"""
        self.status = 'completed'
        self.save(update_fields=['status', 'updated_at'])
        
        # Update meeting type analytics
        self.meeting_type.total_completed += 1
        self.meeting_type.save(update_fields=['total_completed'])
    
    def mark_no_show(self):
        """Mark meeting as no-show"""
        self.status = 'no_show'
        self.save(update_fields=['status', 'updated_at'])
        
        # Update meeting type analytics
        self.meeting_type.total_no_shows += 1
        self.meeting_type.save(update_fields=['total_no_shows'])
    
    def cancel(self, cancelled_by=None, reason=''):
        """Cancel the meeting"""
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancelled_by = cancelled_by
        self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancelled_at', 'cancelled_by', 'cancellation_reason', 'updated_at'])
        
        # Update meeting type analytics
        self.meeting_type.total_cancelled += 1
        self.meeting_type.save(update_fields=['total_cancelled'])


class AvailabilityOverride(models.Model):
    """
    Specific date/time overrides for availability
    Can be used for holidays, special hours, or blocked times
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    profile = models.ForeignKey(SchedulingProfile, on_delete=models.CASCADE, related_name='availability_overrides')
    
    # Date and type
    date = models.DateField()
    override_type = models.CharField(
        max_length=20,
        choices=[
            ('blocked', 'Completely Blocked'),
            ('custom_hours', 'Custom Hours'),
            ('extended_hours', 'Extended Hours'),
        ]
    )
    
    # Custom hours (if override_type is custom_hours or extended_hours)
    # Format: [{"start": "09:00", "end": "17:00"}]
    time_slots = models.JSONField(default=list)
    
    # Reason (optional)
    reason = models.CharField(max_length=255, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['profile', 'date']
        indexes = [
            models.Index(fields=['profile', 'date']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.profile.user.username} - {self.date} ({self.override_type})"