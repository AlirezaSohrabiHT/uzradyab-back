from django.db import models
import random

class OTP(models.Model):
    phone = models.CharField(max_length=15, unique=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_otp(self):
        """Generate a random 6-digit OTP"""
        self.otp_code = str(random.randint(100000, 999999))
        self.save()

    def __str__(self):
        return f"{self.phone} - {self.otp_code}"
