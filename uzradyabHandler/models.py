# models.py
from django.db import models
from django.utils import timezone

class ExpiredDevice(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار بررسی'),
        ('notified', 'بررسی شده'),
        ('renewed', 'تکمیل شده'),
    ]
    
    # Original device data
    device_id = models.IntegerField()  # Reference to original tc_devices.id
    name = models.CharField(max_length=255)
    uniqueid = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True, null=True)
    expirationtime = models.DateTimeField()
    
    # User information (denormalized for easier querying)
    user_emails = models.JSONField(default=list)  # Store list of user emails
    user_phones = models.JSONField(default=list)  # Store list of user phones
    
    # Additional fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField(blank=True, help_text='توضیحات اضافی در مورد دستگاه')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notification_sent_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'expired_devices'
        unique_together = ['device_id', 'expirationtime']  # Prevent duplicates
        ordering = ['-expirationtime']
    
    def __str__(self):
        return f"{self.name} ({self.uniqueid}) - {self.status}"
    
    @property
    def is_recently_expired(self):
        """Check if device expired within last 30 days"""
        if self.expirationtime:
            days_expired = (timezone.now() - self.expirationtime).days
            return days_expired <= 30
        return False