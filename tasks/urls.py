from django.urls import path
from . import views

urlpatterns = [
    # Class-based views
    path('', views.TaskListCreateView.as_view(), name='task_list_create'),
    path('<int:pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    
    # Task creation endpoints
    path('create/', views.create_task, name='create_task'),
    path('simple/', views.create_simple_task, name='create_simple_task'),
    
    # User-centric task viewing
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('my-tasks/', views.my_tasks, name='my_tasks'),
    path('my-tasks/enhanced/', views.my_tasks_enhanced, name='my_tasks_enhanced'),
    path('assigned/', views.assigned_tasks, name='assigned_tasks'),
    path('progress/', views.task_progress, name='task_progress'),
    path('calendar/', views.task_calendar, name='task_calendar'),
    
    # Task retrieval and organization
    path('search/', views.search_tasks, name='search_tasks'),
    path('statistics/', views.task_statistics, name='task_statistics'),
    path('categories/', views.get_task_categories, name='get_task_categories'),
    path('tags/', views.get_task_tags, name='get_task_tags'),
    path('date-range/', views.tasks_by_date_range, name='tasks_by_date_range'),
    
    # Task management
    path('<int:task_id>/status/', views.update_task_status, name='update_task_status'),
    path('<int:task_id>/edit/', views.edit_task, name='edit_task'),
    path('<int:task_id>/quick-edit/', views.quick_edit_task, name='quick_edit_task'),
    
    # User management
    path('users/', views.users_for_assignment, name='users_for_assignment'),
]
