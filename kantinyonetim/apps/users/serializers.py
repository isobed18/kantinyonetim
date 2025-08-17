from rest_framework import serializers
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import User, AuditLog, Notification


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # Expose all fields but keep password write-only to avoid leaking hashes
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True},
            'id': {'read_only': True},
            'is_superuser': {'read_only': True},
            'is_staff': {'read_only': True},
            'groups': {'read_only': True},
            'user_permissions': {'read_only': True},
        }

    def validate_username(self, value):
        # Sanitize username
        value = value.strip().lower()
        
        # Check length
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long.")
        
        # Check for valid characters
        if not value.replace('_', '').replace('-', '').isalnum():
            raise serializers.ValidationError("Username can only contain letters, numbers, underscores, and hyphens.")
        
        # Check if username already exists for update (ignore self)
        if self.instance and User.objects.exclude(pk=self.instance.pk).filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        elif not self.instance and User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        
        return value

    def validate_email(self, value):
        if value:
            value = value.strip().lower()
            try:
                validate_email(value)
            except ValidationError:
                raise serializers.ValidationError("Please enter a valid email address.")
            
            # Check if email already exists for update (ignore self)
            if self.instance and User.objects.exclude(pk=self.instance.pk).filter(email=value).exists():
                raise serializers.ValidationError("Email already exists.")
            elif not self.instance and User.objects.filter(email=value).exists():
                raise serializers.ValidationError("Email already exists.")
        
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        
        if not any(c.isupper() for c in value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")
        
        if not any(c.islower() for c in value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter.")
        
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError("Password must contain at least one number.")
        
        if not any(c in '!@#$%^&*(),.?":{}|<>' for c in value):
            raise serializers.ValidationError("Password must contain at least one special character.")
        
        return value

    def validate_role(self, value):
        valid_roles = ['customer', 'staff', 'admin']
        if value not in valid_roles:
            raise serializers.ValidationError(f"Role must be one of: {', '.join(valid_roles)}")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class AuditLogSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)

    class Meta:
        model = Notification
        fields = '__all__'