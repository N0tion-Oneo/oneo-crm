"""
Admin interface for task management
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Task, TaskComment, TaskAttachment


class TaskCommentInline(admin.TabularInline):
    """Inline admin for task comments"""
    model = TaskComment
    extra = 0
    readonly_fields = ('user', 'created_at', 'updated_at')
    fields = ('comment', 'user', 'created_at')


class TaskAttachmentInline(admin.TabularInline):
    """Inline admin for task attachments"""
    model = TaskAttachment
    extra = 0
    readonly_fields = ('uploaded_by', 'uploaded_at')
    fields = ('file', 'filename', 'uploaded_by', 'uploaded_at')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Admin interface for tasks"""
    list_display = [
        'title', 'priority_badge', 'status_badge', 
        'record_link', 'assigned_to', 'due_date_display', 
        'is_overdue_display', 'created_at'
    ]
    list_filter = ['status', 'priority', 'created_at', 'due_date']
    search_fields = ['title', 'description', 'record__id']
    readonly_fields = ['created_at', 'updated_at', 'completed_at', 'created_by']
    inlines = [TaskCommentInline, TaskAttachmentInline]
    
    fieldsets = (
        ('Task Details', {
            'fields': ('title', 'description', 'priority', 'status')
        }),
        ('Dates', {
            'fields': ('due_date', 'reminder_at', 'completed_at')
        }),
        ('Relationships', {
            'fields': ('record', 'assigned_to', 'created_by')
        }),
        ('Metadata', {
            'fields': ('metadata', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def priority_badge(self, obj):
        """Display priority as colored badge"""
        colors = {
            'urgent': 'red',
            'high': 'orange',
            'medium': 'yellow',
            'low': 'gray'
        }
        color = colors.get(obj.priority, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    
    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'pending': '#FFA500',
            'in_progress': '#007BFF',
            'completed': '#28A745',
            'cancelled': '#6C757D'
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def record_link(self, obj):
        """Link to the associated record"""
        if obj.record:
            return format_html(
                '<a href="/admin/pipelines/record/{}/change/">Record #{}</a>',
                obj.record.id, obj.record.id
            )
        return '-'
    record_link.short_description = 'Record'
    
    def due_date_display(self, obj):
        """Display due date with overdue indicator"""
        if not obj.due_date:
            return '-'
        
        if obj.is_overdue:
            return format_html(
                '<span style="color: red;">{}</span>',
                obj.due_date.strftime('%Y-%m-%d %H:%M')
            )
        return obj.due_date.strftime('%Y-%m-%d %H:%M')
    due_date_display.short_description = 'Due Date'
    
    def is_overdue_display(self, obj):
        """Display overdue status"""
        if obj.is_overdue:
            return format_html('<span style="color: red;">✗ Overdue</span>')
        elif obj.status == 'completed':
            return format_html('<span style="color: green;">✓ Completed</span>')
        elif obj.due_date and obj.due_date > timezone.now():
            return format_html('<span style="color: gray;">On track</span>')
        return '-'
    is_overdue_display.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        """Set created_by when creating new task"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    """Admin interface for task comments"""
    list_display = ['task', 'user', 'comment_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['comment', 'task__title', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    def comment_preview(self, obj):
        """Show preview of comment"""
        return obj.comment[:100] + '...' if len(obj.comment) > 100 else obj.comment
    comment_preview.short_description = 'Comment'


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    """Admin interface for task attachments"""
    list_display = ['filename', 'task', 'uploaded_by', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['filename', 'task__title', 'uploaded_by__email']
    readonly_fields = ['uploaded_at']
