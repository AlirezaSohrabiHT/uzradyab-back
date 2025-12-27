from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'credit', 'phone', 'is_active', 'user_type']


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users with user_type"""
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'password', 'user_type']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer including user type information"""
    is_support = serializers.ReadOnlyField()
    is_admin = serializers.ReadOnlyField()
    is_customer = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'credit', 'phone', 
            'is_active', 'user_type', 'is_support', 'is_admin', 
            'is_customer', 'is_staff', 'is_superuser'
        ]
        read_only_fields = ['id', 'is_staff', 'is_superuser']