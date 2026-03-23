from django.urls import path
from . import views

urlpatterns = [
    # Class-based views
    path('', views.TaskListCreateView.as_view(), name='task_list_create'),
    path('<int:pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    
    # Task creation endpoints
    path('create/', views.create_task, name='create_task'),
    path('simple/', views.create_simple_task, name='create_simple_task'),
    
    # Task organization and search
    path('my-tasks/', views.my_tasks, name='my_tasks'),
    path('assigned/', views.assigned_tasks, name='assigned_tasks'),
    path('search/', views.search_tasks, name='search_tasks'),
    path('categories/', views.get_task_categories, name='get_task_categories'),
    path('tags/', views.get_task_tags, name='get_task_tags'),
    
    # User management
    path('users/', views.users_for_assignment, name='users_for_assignment'),
]
