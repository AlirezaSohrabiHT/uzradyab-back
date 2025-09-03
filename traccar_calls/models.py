# traccar_calls/models.py - Updated model for device-based tracking

from django.db import models
from django.utils import timezone

class ExpiredDevice(models.Model):
    # User information
    user_id = models.IntegerField()
    user_name = models.CharField(max_length=200, blank=True)
    user_email = models.EmailField(blank=True)
    user_phone = models.CharField(max_length=20, blank=True)
    administrator = models.BooleanField(default=False)
    user_disabled = models.BooleanField(default=False)
    
    # Device information  
    device_id = models.IntegerField()
    device_name = models.CharField(max_length=200, blank=True)
    device_uniqueid = models.CharField(max_length=200, blank=True)
    device_phone = models.CharField(max_length=20, blank=True)
    device_disabled = models.BooleanField(default=False)
    device_status = models.CharField(max_length=50, blank=True)
    
    # Expiration tracking
    expiration_time = models.DateTimeField()
    detected_at = models.DateTimeField(default=timezone.now)
    
    # SMS tracking - per device
    sms_3_days_before_sent = models.BooleanField(default=False)
    sms_expire_day_sent = models.BooleanField(default=False)
    sms_3_days_after_sent = models.BooleanField(default=False)
    sms_30_days_after_sent = models.BooleanField(default=False)
    
    # SMS sent dates for tracking
    sms_3_days_before_date = models.DateTimeField(null=True, blank=True)
    sms_expire_day_date = models.DateTimeField(null=True, blank=True)
    sms_3_days_after_date = models.DateTimeField(null=True, blank=True)
    sms_30_days_after_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user_id', 'device_id')
        ordering = ['-expiration_time']
        
    def __str__(self):
        return f"{self.user_name} - {self.device_name} (Expires: {self.expiration_time})"
    
    def get_phone_number(self):
        """Get phone number - prioritize user phone, fallback to device phone"""
        if self.user_phone:
            phone = self.user_phone.strip()
            if phone.startswith('0'):
                phone = '98' + phone[1:]
            elif not phone.startswith('98'):
                phone = '98' + phone
            return phone
        elif self.device_phone:
            phone = self.device_phone.strip()
            if phone.startswith('0'):
                phone = '98' + phone[1:]
            elif not phone.startswith('98'):
                phone = '98' + phone
            return phone
        return None
    
    @property
    def days_to_expire(self):
        """Calculate days until expiration (negative if expired)"""
        today = timezone.now().date()
        exp_date = self.expiration_time.date()
        return (exp_date - today).days
    
    @property
    def is_expired(self):
        """Check if device is expired"""
        return self.expiration_time <= timezone.now()
    
    def reset_sms_flags(self):
        """Reset all SMS flags - useful for testing"""
        self.sms_3_days_before_sent = False
        self.sms_expire_day_sent = False
        self.sms_3_days_after_sent = False
        self.sms_30_days_after_sent = False
        self.sms_3_days_before_date = None
        self.sms_expire_day_date = None
        self.sms_3_days_after_date = None
        self.sms_30_days_after_date = None
        self.save()