# models.py - Update your ExpiredUser model
from django.db import models
from django.utils import timezone

class ExpiredUser(models.Model):
    # User data from Traccar
    traccar_user_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    administrator = models.BooleanField(default=False)
    disabled = models.BooleanField(default=False)
    expiration_time = models.DateTimeField()
    device_limit = models.IntegerField(default=0)
    user_limit = models.IntegerField(default=0)
    
    # Tracking fields
    detected_at = models.DateTimeField(default=timezone.now)
    is_processed = models.BooleanField(default=False)
    
    # SMS tracking fields
    sms_3_days_before_sent = models.BooleanField(default=False)
    sms_expire_day_sent = models.BooleanField(default=False)
    sms_3_days_after_sent = models.BooleanField(default=False)
    sms_30_days_after_sent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-detected_at']
        verbose_name = "Expired User"
        verbose_name_plural = "Expired Users"
    
    def __str__(self):
        return f"{self.name} ({self.email}) - Expired: {self.expiration_time}"
        
    def get_phone_number(self):
        """Get phone number, fallback to email if phone is empty"""
        return self.phone if self.phone else self.email