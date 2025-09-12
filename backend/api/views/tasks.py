"""
Task management views and API endpoints
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from tasks.models import Task, TaskComment, TaskAttachment, TaskChecklistItem
from tasks.serializers import (
    TaskSerializer,
    TaskCreateSerializer,
    TaskStatusUpdateSerializer,
    TaskListSerializer,
    TaskCommentSerializer,
    TaskAttachmentSerializer,
    TaskChecklistItemSerializer
)
from pipelines.models import Record


class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for task management
    """
    queryset = Task.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return TaskCreateSerializer
        elif self.action == 'update_status':
            return TaskStatusUpdateSerializer
        elif self.action == 'list':
            return TaskListSerializer
        return TaskSerializer
    
    def get_queryset(self):
        """Filter tasks based on user permissions"""
        queryset = Task.objects.all()
        
        # Prefetch related data for performance
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                'comments__user',
                'attachments__uploaded_by'
            )
        
        # Filter by record if specified
        record_id = self.request.query_params.get('record_id')
        if record_id:
            queryset = queryset.filter(record_id=record_id)
        
        # Filter by assigned user
        assigned_to = self.request.query_params.get('assigned_to')
        if assigned_to:
            if assigned_to == 'me':
                queryset = queryset.filter(assigned_to=self.request.user)
            else:
                queryset = queryset.filter(assigned_to_id=assigned_to)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            if ',' in status_filter:
                statuses = status_filter.split(',')
                queryset = queryset.filter(status__in=statuses)
            else:
                queryset = queryset.filter(status=status_filter)
        
        # Filter by priority
        priority = self.request.query_params.get('priority')
        if priority:
            if ',' in priority:
                priorities = priority.split(',')
                queryset = queryset.filter(priority__in=priorities)
            else:
                queryset = queryset.filter(priority=priority)
        
        # Filter overdue tasks
        overdue = self.request.query_params.get('overdue')
        if overdue == 'true':
            queryset = queryset.filter(
                due_date__lt=timezone.now(),
                status__in=['pending', 'in_progress']
            )
        
        # Search in title and description
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.select_related('record', 'assigned_to', 'created_by')
    
    @action(detail=False, methods=['get'], url_path='record/(?P<record_id>[^/.]+)')
    def record_tasks(self, request, record_id=None):
        """Get all tasks for a specific record"""
        # Verify record exists and user has access
        record = get_object_or_404(Record, id=record_id, is_deleted=False)
        
        # TODO: Check user permissions for this record
        # For now, just check if user is authenticated
        
        tasks = Task.objects.filter(record=record).select_related(
            'assigned_to', 'created_by'
        ).prefetch_related('comments', 'attachments', 'checklist_items')
        
        # Apply status filter if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            tasks = tasks.filter(status=status_filter)
        
        serializer = TaskSerializer(tasks, many=True, context={'request': request})
        
        return Response({
            'tasks': serializer.data,
            'count': tasks.count(),
            'record_id': record_id
        })
    
    @action(detail=False, methods=['post'], url_path='create')
    def create_task(self, request):
        """Create a new task (custom endpoint for frontend compatibility)"""
        serializer = TaskCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            task = serializer.save()
            # Return full task data
            return Response(
                TaskSerializer(task, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        """Quick status update endpoint"""
        task = self.get_object()
        serializer = TaskStatusUpdateSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get', 'post'], url_path='comments')
    def comments(self, request, pk=None):
        """Get or add comments for a task"""
        task = self.get_object()
        
        if request.method == 'POST':
            # Add a comment
            serializer = TaskCommentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(task=task, user=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            # List comments
            comments = task.comments.all()
            serializer = TaskCommentSerializer(comments, many=True, context={'request': request})
            return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='my-tasks')
    def my_tasks(self, request):
        """Get tasks assigned to the current user"""
        tasks = Task.objects.filter(
            assigned_to=request.user
        ).exclude(
            status__in=['completed', 'cancelled']
        ).select_related('record', 'created_by')
        
        serializer = TaskListSerializer(tasks, many=True, context={'request': request})
        return Response({
            'tasks': serializer.data,
            'count': tasks.count()
        })
    
    @action(detail=False, methods=['get'], url_path='upcoming')
    def upcoming_tasks(self, request):
        """Get upcoming tasks (due in next 7 days)"""
        end_date = timezone.now() + timezone.timedelta(days=7)
        tasks = Task.objects.filter(
            due_date__lte=end_date,
            due_date__gte=timezone.now(),
            status__in=['pending', 'in_progress']
        ).select_related('record', 'assigned_to', 'created_by')
        
        serializer = TaskListSerializer(tasks, many=True, context={'request': request})
        return Response({
            'tasks': serializer.data,
            'count': tasks.count()
        })
    
    @action(detail=False, methods=['get'], url_path='overdue')
    def overdue_tasks(self, request):
        """Get overdue tasks"""
        tasks = Task.objects.filter(
            due_date__lt=timezone.now(),
            status__in=['pending', 'in_progress']
        ).select_related('record', 'assigned_to', 'created_by')
        
        serializer = TaskListSerializer(tasks, many=True, context={'request': request})
        return Response({
            'tasks': serializer.data,
            'count': tasks.count()
        })
    
    @action(detail=True, methods=['get', 'post'], url_path='checklist')
    def checklist(self, request, pk=None):
        """Get or add checklist items for a task"""
        task = self.get_object()
        
        if request.method == 'POST':
            # Add a checklist item
            serializer = TaskChecklistItemSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(task=task)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            # List checklist items
            items = task.checklist_items.all()
            serializer = TaskChecklistItemSerializer(items, many=True, context={'request': request})
            return Response(serializer.data)
    
    @action(detail=True, methods=['patch', 'delete'], url_path='checklist/(?P<item_id>[^/.]+)')
    def checklist_item(self, request, pk=None, item_id=None):
        """Update or delete a specific checklist item"""
        task = self.get_object()
        item = get_object_or_404(TaskChecklistItem, id=item_id, task=task)
        
        if request.method == 'DELETE':
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            # Update checklist item
            serializer = TaskChecklistItemSerializer(item, data=request.data, partial=True)
            if serializer.is_valid():
                # If marking as completed, set completed_by
                if 'is_completed' in request.data and request.data['is_completed']:
                    serializer.save(completed_by=request.user)
                else:
                    serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def perform_create(self, serializer):
        """Set created_by when creating a task"""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Handle status changes and other updates"""
        task = serializer.save()
        
        # If status changed to completed, set completed_at
        if task.status == 'completed' and not task.completed_at:
            task.completed_at = timezone.now()
            task.save()


class TaskCommentViewSet(viewsets.ModelViewSet):
    """ViewSet for task comments"""
    queryset = TaskComment.objects.all()
    serializer_class = TaskCommentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter comments by task if specified"""
        queryset = TaskComment.objects.all()
        task_id = self.request.query_params.get('task_id')
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        return queryset.select_related('user', 'task')
    
    def perform_create(self, serializer):
        """Set user when creating a comment"""
        serializer.save(user=self.request.user)