# admin.py
from django.contrib import admin
from .models import ExpiredUser

@admin.register(ExpiredUser)
class ExpiredUserAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'email', 
        'phone', 
        'expiration_time', 
        'detected_at', 
        'sms_status',
        'is_processed'
    ]
    list_filter = [
        'administrator', 
        'disabled', 
        'is_processed', 
        'detected_at',
        'expiration_time',
        'sms_3_days_before_sent',
        'sms_expire_day_sent', 
        'sms_3_days_after_sent',
        'sms_30_days_after_sent'
    ]
    search_fields = ['name', 'email', 'phone']
    readonly_fields = ['traccar_user_id', 'detected_at']
    list_per_page = 50
    
    fieldsets = (
        ('User Information', {
            'fields': ('traccar_user_id', 'name', 'email', 'phone')
        }),
        ('Permissions', {
            'fields': ('administrator', 'disabled', 'device_limit', 'user_limit')
        }),
        ('Tracking', {
            'fields': ('expiration_time', 'detected_at', 'is_processed')
        }),
        ('SMS Notifications', {
            'fields': (
                'sms_3_days_before_sent',
                'sms_expire_day_sent', 
                'sms_3_days_after_sent',
                'sms_30_days_after_sent'
            )
        }),
    )
    
    def sms_status(self, obj):
        """Show SMS sending status"""
        status = []
        if obj.sms_3_days_before_sent:
            status.append("3d-before")
        if obj.sms_expire_day_sent:
            status.append("expire-day")
        if obj.sms_3_days_after_sent:
            status.append("3d-after")
        if obj.sms_30_days_after_sent:
            status.append("30d-after")
        
        return ", ".join(status) if status else "None"
    sms_status.short_description = "SMS Sent"