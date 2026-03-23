from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    """
    Serializer for Task model
    """
    owner_name = serializers.CharField(source='owner.first_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.first_name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_until_due = serializers.IntegerField(read_only=True)
    tags_list = serializers.ListField(source='get_tags_list', read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'owner', 'owner_name', 
            'assigned_to', 'assigned_to_name', 'created_at', 'updated_at',
            'due_date', 'completed_at', 'priority', 'status', 'is_completed',
            'estimated_hours', 'actual_hours', 'tags', 'tags_list', 'category',
            'is_overdue', 'days_until_due'
        ]
        read_only_fields = [
            'id', 'owner', 'created_at', 'updated_at', 'completed_at',
            'is_completed', 'is_overdue', 'days_until_due'
        ]
    
    def validate_due_date(self, value):
        """Validate that due_date is not unreasonably in the past"""
        from django.utils import timezone
        import datetime
        
        if value:
            # Convert to date if it's a datetime
            if isinstance(value, datetime.datetime):
                check_date = value.date()
            else:
                check_date = value
            
            # Get today's date
            today = timezone.now().date()
            
            # Allow dates up to 1 year in the past (for system date issues)
            one_year_ago = today - datetime.timedelta(days=365)
            
            # Only reject dates more than 1 year in the past
            if check_date < one_year_ago:
                raise serializers.ValidationError(f"Due date cannot be more than 1 year in the past. Due: {check_date}, Today: {today}")
        
        return value
    
    def validate_estimated_hours(self, value):
        """Validate estimated hours is positive"""
        if value and value <= 0:
            raise serializers.ValidationError("Estimated hours must be positive.")
        return value
    
    def validate_actual_hours(self, value):
        """Validate actual hours is positive"""
        if value and value <= 0:
            raise serializers.ValidationError("Actual hours must be positive.")
        return value
    
    def validate_assigned_to(self, value):
        """Handle assigned_to field - accept user ID or username"""
        if value is None:
            return value
        
        # If it's already an integer, treat as user ID
        if isinstance(value, int):
            try:
                user = User.objects.get(id=value)
                return user
            except User.DoesNotExist:
                raise serializers.ValidationError("User with this ID does not exist.")
        
        # If it's a string, treat as username or first name
        if isinstance(value, str):
            try:
                # Try to find by username first
                user = User.objects.get(username=value)
                return user
            except User.DoesNotExist:
                try:
                    # Try to find by first name (case insensitive)
                    user = User.objects.get(first_name__iexact=value)
                    return user
                except User.DoesNotExist:
                    raise serializers.ValidationError(f"User '{value}' not found.")
        
        return value
    
    def create(self, validated_data):
        """Create task with authenticated user as owner"""
        # Set owner to authenticated user
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class TaskCreateSerializer(serializers.ModelSerializer):
    """
    Enhanced serializer for task creation with focus on titles and descriptions
    """
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'assigned_to', 'due_date', 'priority',
            'status', 'estimated_hours', 'tags', 'category'
        ]
    
    def validate_title(self, value):
        """Enhanced title validation"""
        if not value or not value.strip():
            raise serializers.ValidationError("Title is required and cannot be empty.")
        
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters long.")
        
        if len(value) > 200:
            raise serializers.ValidationError("Title cannot exceed 200 characters.")
        
        # Check for common title patterns that might indicate low quality
        value = value.strip()
        if value.lower() in ['task', 'todo', 'do this', 'work', 'task1', 'test']:
            raise serializers.ValidationError("Please provide a more descriptive title.")
        
        return value.strip()
    
    def validate_description(self, value):
        """Enhanced description validation"""
        if value:
            value = value.strip()
            if len(value) < 10:
                raise serializers.ValidationError("Description must be at least 10 characters long if provided.")
            
            if len(value) > 2000:
                raise serializers.ValidationError("Description cannot exceed 2000 characters.")
        
        return value.strip() if value else ""
    
    def validate_tags(self, value):
        """Enhanced tags validation"""
        if value:
            value = value.strip()
            tags = [tag.strip() for tag in value.split(',')]
            
            # Remove empty tags
            tags = [tag for tag in tags if tag]
            
            # Limit number of tags
            if len(tags) > 10:
                raise serializers.ValidationError("Cannot have more than 10 tags.")
            
            # Validate individual tag length
            for tag in tags:
                if len(tag) > 30:
                    raise serializers.ValidationError(f"Tag '{tag}' is too long. Maximum 30 characters per tag.")
            
            return ', '.join(tags)
        
        return value
    
    def validate_category(self, value):
        """Enhanced category validation"""
        if value:
            value = value.strip()
            if len(value) < 2:
                raise serializers.ValidationError("Category must be at least 2 characters long.")
            if len(value) > 50:
                raise serializers.ValidationError("Category cannot exceed 50 characters.")
            return value
        
        return value
    
    def validate_assigned_to(self, value):
        """Handle assigned_to field - accept user ID or username"""
        if value is None:
            return value
        
        # If it's already an integer, treat as user ID
        if isinstance(value, int):
            try:
                user = User.objects.get(id=value)
                return user
            except User.DoesNotExist:
                raise serializers.ValidationError("User with this ID does not exist.")
        
        # If it's a string, treat as username or first name
        if isinstance(value, str):
            try:
                # Try to find by username first
                user = User.objects.get(username=value)
                return user
            except User.DoesNotExist:
                try:
                    # Try to find by first name (case insensitive)
                    user = User.objects.get(first_name__iexact=value)
                    return user
                except User.DoesNotExist:
                    raise serializers.ValidationError(f"User '{value}' not found.")
        
        return value
    
    def validate_due_date(self, value):
        """Validate that due_date is not unreasonably in the past"""
        from django.utils import timezone
        import datetime
        
        if value:
            # Convert to date if it's a datetime
            if isinstance(value, datetime.datetime):
                check_date = value.date()
            else:
                check_date = value
            
            # Get today's date
            today = timezone.now().date()
            
            # Allow dates up to 1 year in the past (for system date issues)
            one_year_ago = today - datetime.timedelta(days=365)
            
            # Only reject dates more than 1 year in the past
            if check_date < one_year_ago:
                raise serializers.ValidationError(f"Due date cannot be more than 1 year in the past. Due: {check_date}, Today: {today}")
        
        return value
    
    def validate_estimated_hours(self, value):
        """Validate estimated hours is positive"""
        if value and value <= 0:
            raise serializers.ValidationError("Estimated hours must be positive.")
        return value
    
    def create(self, validated_data):
        """Create task with authenticated user as owner"""
        validated_data['owner'] = self.context['request'].user
        
        # Auto-set priority based on description length and due date
        if not validated_data.get('priority'):
            if validated_data.get('due_date'):
                from django.utils import timezone
                days_until_due = (validated_data['due_date'] - timezone.now()).days
                if days_until_due <= 1:
                    validated_data['priority'] = 'urgent'
                elif days_until_due <= 3:
                    validated_data['priority'] = 'high'
                else:
                    validated_data['priority'] = 'medium'
            else:
                validated_data['priority'] = 'medium'
        
        return super().create(validated_data)


class SimpleTaskCreateSerializer(serializers.ModelSerializer):
    """
    Simplified task creation serializer focused on title and description
    """
    class Meta:
        model = Task
        fields = ['title', 'description']
    
    def validate_title(self, value):
        """Enhanced title validation for simple creation"""
        if not value or not value.strip():
            raise serializers.ValidationError("Title is required and cannot be empty.")
        
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters long.")
        
        if len(value) > 200:
            raise serializers.ValidationError("Title cannot exceed 200 characters.")
        
        return value.strip()
    
    def validate_description(self, value):
        """Enhanced description validation"""
        if value:
            value = value.strip()
            if len(value) < 10:
                raise serializers.ValidationError("Description must be at least 10 characters long if provided.")
            if len(value) > 2000:
                raise serializers.ValidationError("Description cannot exceed 2000 characters.")
        
        return value.strip() if value else ""
    
    def create(self, validated_data):
        """Create simple task with default values"""
        validated_data['owner'] = self.context['request'].user
        validated_data['priority'] = 'medium'
        validated_data['status'] = 'todo'
        
        return super().create(validated_data)


class TaskStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer specifically for updating task status
    """
    class Meta:
        model = Task
        fields = ['status']
    
    def validate_status(self, value):
        """Validate that the status is one of the allowed choices"""
        valid_statuses = [choice[0] for choice in Task.STATUS_CHOICES]
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return value


class UserSerializer(serializers.ModelSerializer):
    """
    Simple user serializer for task assignment
    """
    value = serializers.IntegerField(source='id')
    label = serializers.CharField(source='first_name')
    
    class Meta:
        model = User
        fields = ['value', 'label']
