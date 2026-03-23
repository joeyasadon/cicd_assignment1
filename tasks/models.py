from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Task(models.Model):
    """
    Task model for the task management application
    """
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('review', 'Under Review'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic task information
    title = models.CharField(max_length=200, verbose_name="Task Title")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Task ownership and assignment
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='owned_tasks',
        verbose_name="Task Owner"
    )
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_tasks',
        verbose_name="Assigned To"
    )
    
    # Task scheduling
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    due_date = models.DateTimeField(null=True, blank=True, verbose_name="Due Date")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Completed At")
    
    # Task properties
    priority = models.CharField(
        max_length=10, 
        choices=PRIORITY_CHOICES, 
        default='medium',
        verbose_name="Priority"
    )
    status = models.CharField(
        max_length=15, 
        choices=STATUS_CHOICES, 
        default='todo',
        verbose_name="Status"
    )
    
    # Task metadata
    is_completed = models.BooleanField(default=False, verbose_name="Is Completed")
    estimated_hours = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Estimated Hours"
    )
    actual_hours = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Actual Hours"
    )
    
    # Tags and categorization
    tags = models.CharField(
        max_length=500, 
        blank=True, 
        help_text="Comma-separated tags",
        verbose_name="Tags"
    )
    category = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name="Category"
    )
    
    class Meta:
        verbose_name = "Task"
        verbose_name_plural = "Tasks"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Auto-update completed_at when status changes to completed
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
            self.is_completed = True
        elif self.status != 'completed' and self.completed_at:
            self.completed_at = None
            self.is_completed = False
        
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if self.due_date and not self.is_completed:
            return timezone.now() > self.due_date
        return False
    
    @property
    def days_until_due(self):
        """Calculate days until due date"""
        if self.due_date:
            delta = self.due_date - timezone.now()
            return delta.days
        return None
    
    @property
    def get_tags_list(self):
        """Return tags as a list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []
