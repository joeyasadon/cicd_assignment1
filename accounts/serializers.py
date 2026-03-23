from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    display_name = serializers.CharField(max_length=100)
    token = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'confirm_password', 'display_name', 'token')

    def validate_email(self, value):
        """Validate that email is unique"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        """Validate that passwords match"""
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs

    def create(self, validated_data):
        """Create user and token"""
        validated_data.pop('confirm_password')
        
        user = User.objects.create_user(
            username=validated_data['email'],  # Use email as username
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['display_name']
        )
        
        # Create token for the user
        token = Token.objects.create(user=user)
        
        return {
            'user': user,
            'token': token.key
        }
