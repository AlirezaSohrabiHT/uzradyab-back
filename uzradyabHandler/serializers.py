from rest_framework import serializers
from django.utils import timezone
from .models import ExpiredDevice

class ExpiredDeviceSerializer(serializers.ModelSerializer):
    is_recently_expired = serializers.ReadOnlyField()
    days_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = ExpiredDevice
        fields = [
            'id', 'device_id', 'name', 'uniqueid', 'phone', 'expirationtime',
            'user_emails', 'user_phones', 'status', 'description', 'created_at', 
            'updated_at', 'notification_sent_at', 'notes', 'is_recently_expired', 
            'days_expired'
        ]
    
    def get_days_expired(self, obj):
        if obj.expirationtime:
            return (timezone.now() - obj.expirationtime).days
        return None