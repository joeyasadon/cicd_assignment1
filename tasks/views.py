from rest_framework import status, permissions, generics, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.models import User
from django.db import models
from .models import Task
from .serializers import TaskSerializer, TaskCreateSerializer, UserSerializer


class TaskListCreateView(generics.ListCreateAPIView):
    """
    GET: List all tasks for authenticated user
    POST: Create a new task
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'assigned_to', 'category']
    search_fields = ['title', 'description', 'tags']
    ordering_fields = ['created_at', 'due_date', 'priority', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Return tasks owned by or assigned to the authenticated user
        """
        user = self.request.user
        return Task.objects.filter(
            models.Q(owner=user) | models.Q(assigned_to=user)
        ).select_related('owner', 'assigned_to').distinct()
    
    def get_serializer_class(self):
        """
        Use different serializers for GET and POST
        """
        if self.request.method == 'POST':
            return TaskCreateSerializer
        return TaskSerializer


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


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_tasks(request):
    """
    Get tasks owned by the authenticated user
    """
    tasks = Task.objects.filter(owner=request.user).select_related('assigned_to')
    serializer = TaskSerializer(tasks, many=True)
    return Response({
        'message': 'Tasks retrieved successfully',
        'tasks': serializer.data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def assigned_tasks(request):
    """
    Get tasks assigned to the authenticated user
    """
    tasks = Task.objects.filter(assigned_to=request.user).select_related('owner')
    serializer = TaskSerializer(tasks, many=True)
    return Response({
        'message': 'Assigned tasks retrieved successfully',
        'tasks': serializer.data
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
        'users': serializer.data
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_task(request):
    """
    Create a new task (alternative endpoint)
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
