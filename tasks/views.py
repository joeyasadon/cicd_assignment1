from rest_framework import status, permissions, generics, filters, pagination
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.models import User
from django.db import models
from .models import Task
from .serializers import TaskSerializer, TaskCreateSerializer, SimpleTaskCreateSerializer, UserSerializer


class TaskPagination(pagination.PageNumberPagination):
    """
    Custom pagination for tasks
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class TaskListCreateView(generics.ListCreateAPIView):
    """
    GET: List all tasks for authenticated user with advanced filtering
    POST: Create a new task
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskSerializer
    pagination_class = TaskPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'assigned_to', 'category', 'is_completed']
    search_fields = ['title', 'description', 'tags']
    ordering_fields = ['created_at', 'updated_at', 'due_date', 'priority', 'title']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Return tasks owned by or assigned to the authenticated user
        """
        user = self.request.user
        
        # Base queryset - tasks owned by or assigned to user
        queryset = Task.objects.filter(
            models.Q(owner=user) | models.Q(assigned_to=user)
        ).select_related('owner', 'assigned_to').distinct()
        
        # Additional filtering by query parameters
        status_filter = self.request.query_params.get('status', None)
        priority_filter = self.request.query_params.get('priority', None)
        category_filter = self.request.query_params.get('category', None)
        is_completed_filter = self.request.query_params.get('is_completed', None)
        overdue_filter = self.request.query_params.get('overdue', None)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
            
        if category_filter:
            queryset = queryset.filter(category__icontains=category_filter)
            
        if is_completed_filter is not None:
            is_completed = is_completed_filter.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(is_completed=is_completed)
            
        if overdue_filter is not None:
            if overdue_filter.lower() in ('true', '1', 'yes'):
                queryset = queryset.filter(
                    models.Q(due_date__lt=models.functions.Now()) & 
                    models.Q(is_completed=False)
                )
        
        return queryset
    
    def get_serializer_class(self):
        """
        Use different serializers for GET and POST
        """
        if self.request.method == 'POST':
            return TaskCreateSerializer
        return TaskSerializer
    
    def list(self, request, *args, **kwargs):
        """
        Override list method to provide enhanced response
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'message': 'Tasks retrieved successfully',
                'tasks': serializer.data,
                'filters': {
                    'status': request.query_params.get('status', 'all'),
                    'priority': request.query_params.get('priority', 'all'),
                    'category': request.query_params.get('category', 'all'),
                    'is_completed': request.query_params.get('is_completed', 'all'),
                    'overdue': request.query_params.get('overdue', 'all'),
                    'search': request.query_params.get('search', 'none')
                }
            })
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'message': 'Tasks retrieved successfully',
            'tasks': serializer.data,
            'total_count': queryset.count()
        })


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific task
    PUT/PATCH: Update a task
    DELETE: Delete a task
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskSerializer
    
    def get_queryset(self):
        """
        Return tasks owned by or assigned to the authenticated user
        """
        user = self.request.user
        return Task.objects.filter(
            models.Q(owner=user) | models.Q(assigned_to=user)
        ).select_related('owner', 'assigned_to').distinct()
    
    def retrieve(self, request, *args, **kwargs):
        """
        Override retrieve method to provide enhanced response
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'message': 'Task retrieved successfully',
            'task': serializer.data
        })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def task_statistics(request):
    """
    Get task statistics for the authenticated user
    """
    user = request.user
    user_tasks = Task.objects.filter(
        models.Q(owner=user) | models.Q(assigned_to=user)
    )
    
    stats = {
        'total_tasks': user_tasks.count(),
        'completed_tasks': user_tasks.filter(is_completed=True).count(),
        'pending_tasks': user_tasks.filter(is_completed=False).count(),
        'overdue_tasks': user_tasks.filter(
            models.Q(due_date__lt=models.functions.Now()) & 
            models.Q(is_completed=False)
        ).count(),
        'by_status': {},
        'by_priority': {},
        'by_category': {}
    }
    
    # Status breakdown
    for status_choice, _ in Task.STATUS_CHOICES:
        stats['by_status'][status_choice] = user_tasks.filter(status=status_choice).count()
    
    # Priority breakdown
    for priority_choice, _ in Task.PRIORITY_CHOICES:
        stats['by_priority'][priority_choice] = user_tasks.filter(priority=priority_choice).count()
    
    # Category breakdown
    categories = user_tasks.values_list('category', flat=True).distinct()
    for category in categories:
        if category:
            stats['by_category'][category] = user_tasks.filter(category=category).count()
    
    return Response({
        'message': 'Task statistics retrieved successfully',
        'statistics': stats
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_simple_task(request):
    """
    Create a simple task with just title and description
    Perfect for quick task creation and organization
    """
    serializer = SimpleTaskCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        task = serializer.save()
        
        # Return full task details
        task_serializer = TaskSerializer(task)
        return Response({
            'message': 'Simple task created successfully',
            'task': task_serializer.data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_task(request):
    """
    Create a new task with full details (alternative endpoint)
    """
    serializer = TaskCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        task = serializer.save()
        
        # Return full task details
        task_serializer = TaskSerializer(task)
        return Response({
            'message': 'Task created successfully',
            'task': task_serializer.data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_dashboard(request):
    """
    Get user dashboard with task overview and quick stats
    """
    user = request.user
    
    # Get user's tasks (owned + assigned)
    user_tasks = Task.objects.filter(
        models.Q(owner=user) | models.Q(assigned_to=user)
    ).select_related('owner', 'assigned_to').distinct()
    
    # Recent tasks (last 5)
    recent_tasks = user_tasks.order_by('-created_at')[:5]
    
    # Tasks due soon (next 7 days)
    from django.utils import timezone
    import datetime
    next_week = timezone.now() + datetime.timedelta(days=7)
    due_soon_tasks = user_tasks.filter(
        due_date__lte=next_week,
        is_completed=False
    ).order_by('due_date')[:5]
    
    # Overdue tasks
    overdue_tasks = user_tasks.filter(
        due_date__lt=timezone.now(),
        is_completed=False
    ).order_by('due_date')[:5]
    
    # Today's tasks
    today = timezone.now().date()
    today_tasks = user_tasks.filter(
        due_date__date=today,
        is_completed=False
    ).order_by('priority')
    
    # Quick stats
    stats = {
        'total_tasks': user_tasks.count(),
        'owned_tasks': user_tasks.filter(owner=user).count(),
        'assigned_tasks': user_tasks.filter(assigned_to=user).count(),
        'completed_tasks': user_tasks.filter(is_completed=True).count(),
        'pending_tasks': user_tasks.filter(is_completed=False).count(),
        'overdue_tasks': overdue_tasks.count(),
        'due_today': today_tasks.count(),
        'due_this_week': user_tasks.filter(
            due_date__lte=next_week,
            due_date__date__gte=today,
            is_completed=False
        ).count()
    }
    
    # Serialize the task lists
    recent_serializer = TaskSerializer(recent_tasks, many=True)
    due_soon_serializer = TaskSerializer(due_soon_tasks, many=True)
    overdue_serializer = TaskSerializer(overdue_tasks, many=True)
    today_serializer = TaskSerializer(today_tasks, many=True)
    
    return Response({
        'message': 'User dashboard retrieved successfully',
        'dashboard': {
            'stats': stats,
            'recent_tasks': recent_serializer.data,
            'due_soon_tasks': due_soon_serializer.data,
            'overdue_tasks': overdue_serializer.data,
            'today_tasks': today_serializer.data
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_tasks_enhanced(request):
    """
    Enhanced view for user's owned tasks with advanced filtering
    """
    user = request.user
    queryset = Task.objects.filter(owner=user).select_related('assigned_to')
    
    # Advanced filtering
    status_filter = request.query_params.get('status')
    priority_filter = request.query_params.get('priority')
    category_filter = request.query_params.get('category')
    is_completed_filter = request.query_params.get('is_completed')
    date_filter = request.query_params.get('date_filter')  # today, week, month
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if priority_filter:
        queryset = queryset.filter(priority=priority_filter)
    
    if category_filter:
        queryset = queryset.filter(category__icontains=category_filter)
    
    if is_completed_filter is not None:
        is_completed = is_completed_filter.lower() in ('true', '1', 'yes')
        queryset = queryset.filter(is_completed=is_completed)
    
    if date_filter:
        from django.utils import timezone
        import datetime
        today = timezone.now().date()
        
        if date_filter == 'today':
            queryset = queryset.filter(due_date__date=today)
        elif date_filter == 'week':
            week_start = today - datetime.timedelta(days=today.weekday())
            week_end = week_start + datetime.timedelta(days=6)
            queryset = queryset.filter(due_date__date__range=[week_start, week_end])
        elif date_filter == 'month':
            queryset = queryset.filter(due_date__year=today.year, due_date__month=today.month)
    
    # Sorting
    ordering = request.query_params.get('ordering', '-created_at')
    if ordering:
        queryset = queryset.order_by(ordering)
    
    # Apply pagination
    paginator = TaskPagination()
    page = paginator.paginate_queryset(queryset, request)
    
    if page:
        serializer = TaskSerializer(page, many=True)
        return paginator.get_paginated_response({
            'message': 'Your tasks retrieved successfully',
            'tasks': serializer.data,
            'filters_applied': {
                'status': status_filter or 'all',
                'priority': priority_filter or 'all',
                'category': category_filter or 'all',
                'is_completed': is_completed_filter or 'all',
                'date_filter': date_filter or 'all',
                'ordering': ordering
            }
        })
    
    serializer = TaskSerializer(queryset, many=True)
    return Response({
        'message': 'Your tasks retrieved successfully',
        'tasks': serializer.data,
        'total_count': queryset.count(),
        'filters_applied': {
            'status': status_filter or 'all',
            'priority': priority_filter or 'all',
            'category': category_filter or 'all',
            'is_completed': is_completed_filter or 'all',
            'date_filter': date_filter or 'all',
            'ordering': ordering
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def task_progress(request):
    """
    Get task progress and completion trends
    """
    user = request.user
    user_tasks = Task.objects.filter(
        models.Q(owner=user) | models.Q(assigned_to=user)
    )
    
    # Progress by status
    status_progress = {}
    for status_choice, _ in Task.STATUS_CHOICES:
        count = user_tasks.filter(status=status_choice).count()
        total = user_tasks.count()
        status_progress[status_choice] = {
            'count': count,
            'percentage': round((count / total * 100), 1) if total > 0 else 0
        }
    
    # Progress by priority
    priority_progress = {}
    for priority_choice, _ in Task.PRIORITY_CHOICES:
        count = user_tasks.filter(priority=priority_choice).count()
        total = user_tasks.count()
        priority_progress[priority_choice] = {
            'count': count,
            'percentage': round((count / total * 100), 1) if total > 0 else 0
        }
    
    # Completion timeline (last 30 days)
    from django.utils import timezone
    import datetime
    thirty_days_ago = timezone.now() - datetime.timedelta(days=30)
    
    completed_tasks = user_tasks.filter(
        completed_at__gte=thirty_days_ago
    ).order_by('completed_at')
    
    timeline = []
    for task in completed_tasks:
        timeline.append({
            'date': task.completed_at.date(),
            'task_id': task.id,
            'task_title': task.title,
            'priority': task.priority
        })
    
    # Time tracking
    total_estimated = user_tasks.aggregate(
        total=models.Sum('estimated_hours')
    )['total'] or 0
    
    total_actual = user_tasks.aggregate(
        total=models.Sum('actual_hours')
    )['total'] or 0
    
    return Response({
        'message': 'Task progress retrieved successfully',
        'progress': {
            'by_status': status_progress,
            'by_priority': priority_progress,
            'completion_timeline': timeline,
            'time_tracking': {
                'total_estimated_hours': float(total_estimated),
                'total_actual_hours': float(total_actual),
                'efficiency': round((total_actual / total_estimated * 100), 1) if total_estimated > 0 else 0
            }
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def task_calendar(request):
    """
    Get tasks in calendar format for a specific month
    """
    user = request.user
    year = request.query_params.get('year')
    month = request.query_params.get('month')
    
    if not year or not month:
        # Default to current month
        from django.utils import timezone
        today = timezone.now().date()
        year = today.year
        month = today.month
    else:
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            return Response({
                'error': 'Invalid year or month format'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get tasks for the specified month
    user_tasks = Task.objects.filter(
        models.Q(owner=user) | models.Q(assigned_to=user)
    ).filter(
        due_date__year=year,
        due_date__month=month
    ).select_related('owner', 'assigned_to').order_by('due_date')
    
    # Organize tasks by date
    calendar_data = {}
    for task in user_tasks:
        date_key = task.due_date.date().isoformat()
        if date_key not in calendar_data:
            calendar_data[date_key] = []
        
        task_data = {
            'id': task.id,
            'title': task.title,
            'priority': task.priority,
            'status': task.status,
            'is_completed': task.is_completed,
            'owner': task.owner.first_name,
            'assigned_to': task.assigned_to.first_name if task.assigned_to else None
        }
        
        calendar_data[date_key].append(task_data)
    
    return Response({
        'message': 'Task calendar retrieved successfully',
        'calendar': {
            'year': year,
            'month': month,
            'tasks_by_date': calendar_data,
            'total_tasks': user_tasks.count(),
            'completed_tasks': user_tasks.filter(is_completed=True).count()
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_tasks(request):
    """
    Get tasks owned by the authenticated user (original endpoint preserved)
    """
    tasks = Task.objects.filter(owner=request.user).select_related('assigned_to')
    
    # Apply pagination
    paginator = TaskPagination()
    page = paginator.paginate_queryset(tasks, request)
    
    if page:
        serializer = TaskSerializer(page, many=True)
        return paginator.get_paginated_response({
            'message': 'Owned tasks retrieved successfully',
            'tasks': serializer.data
        })
    
    serializer = TaskSerializer(tasks, many=True)
    return Response({
        'message': 'Owned tasks retrieved successfully',
        'tasks': serializer.data,
        'total_count': tasks.count()
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def assigned_tasks(request):
    """
    Get tasks assigned to the authenticated user
    """
    tasks = Task.objects.filter(assigned_to=request.user).select_related('owner')
    
    # Apply pagination
    paginator = TaskPagination()
    page = paginator.paginate_queryset(tasks, request)
    
    if page:
        serializer = TaskSerializer(page, many=True)
        return paginator.get_paginated_response({
            'message': 'Assigned tasks retrieved successfully',
            'tasks': serializer.data
        })
    
    serializer = TaskSerializer(tasks, many=True)
    return Response({
        'message': 'Assigned tasks retrieved successfully',
        'tasks': serializer.data,
        'total_count': tasks.count()
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_tasks(request):
    """
    Search tasks by title, description, or tags
    """
    query = request.GET.get('q', '').strip()
    
    if not query:
        return Response({
            'error': 'Search query is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    tasks = Task.objects.filter(
        models.Q(owner=user) | models.Q(assigned_to=user)
    ).filter(
        models.Q(title__icontains=query) |
        models.Q(description__icontains=query) |
        models.Q(tags__icontains=query)
    ).select_related('owner', 'assigned_to').distinct()
    
    # Apply pagination
    paginator = TaskPagination()
    page = paginator.paginate_queryset(tasks, request)
    
    if page:
        serializer = TaskSerializer(page, many=True)
        return paginator.get_paginated_response({
            'message': f'Found {tasks.count()} tasks matching "{query}"',
            'tasks': serializer.data,
            'search_query': query
        })
    
    serializer = TaskSerializer(tasks, many=True)
    return Response({
        'message': f'Found {tasks.count()} tasks matching "{query}"',
        'tasks': serializer.data,
        'search_query': query
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_task_categories(request):
    """
    Get all unique categories for the authenticated user
    """
    user = request.user
    categories = Task.objects.filter(
        models.Q(owner=user) | models.Q(assigned_to=user)
    ).values_list('category', flat=True).distinct()
    
    # Remove empty categories and sort
    categories = sorted([cat for cat in categories if cat])
    
    return Response({
        'message': 'Categories retrieved successfully',
        'categories': categories,
        'total_count': len(categories)
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_task_tags(request):
    """
    Get all unique tags for the authenticated user
    """
    user = request.user
    tasks = Task.objects.filter(
        models.Q(owner=user) | models.Q(assigned_to=user)
    ).exclude(tags='')
    
    all_tags = set()
    for task in tasks:
        if task.tags:
            all_tags.update(task.get_tags_list)
    
    tags = sorted(list(all_tags))
    
    return Response({
        'message': 'Tags retrieved successfully',
        'tags': tags,
        'total_count': len(tags)
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def users_for_assignment(request):
    """
    Get list of users that can be assigned tasks
    """
    users = User.objects.all().exclude(id=request.user.id)
    serializer = UserSerializer(users, many=True)
    return Response({
        'message': 'Users retrieved successfully',
        'users': serializer.data,
        'total_count': users.count()
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def tasks_by_date_range(request):
    """
    Get tasks within a specific date range
    """
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date or not end_date:
        return Response({
            'error': 'Both start_date and end_date are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from django.utils.dateparse import parse_datetime
        start = parse_datetime(start_date)
        end = parse_datetime(end_date)
        
        if not start or not end:
            raise ValueError("Invalid date format")
    except ValueError:
        return Response({
            'error': 'Invalid date format. Use ISO format: YYYY-MM-DDTHH:MM:SS'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    tasks = Task.objects.filter(
        models.Q(owner=user) | models.Q(assigned_to=user)
    ).filter(
        created_at__gte=start,
        created_at__lte=end
    ).select_related('owner', 'assigned_to').distinct()
    
    serializer = TaskSerializer(tasks, many=True)
    return Response({
        'message': f'Found {tasks.count()} tasks between {start_date} and {end_date}',
        'tasks': serializer.data,
        'date_range': {
            'start': start_date,
            'end': end_date
        },
        'total_count': tasks.count()
    })
