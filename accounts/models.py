from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin
)


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('The phone number must be set')
        user = self.model(phone=phone, **extra_fields)
        user.raw_password = password or ''  # <-- set raw password here
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'admin')  # Set admin type for superusers
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    # User type choices
    USER_TYPE_CHOICES = [
        ('customer', 'Customer'),
        ('support', 'Support'),
        ('admin', 'Admin'),
    ]

    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=15, unique=True)
    credit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    traccar_token = models.CharField(max_length=512, blank=True, null=True)
    traccar_id = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # New user_type field
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='customer',
        help_text='Designates the type of user account.'
    )

    objects = UserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_support(self):
        """Check if user is a support user"""
        return self.user_type == 'support'

    @property
    def is_admin(self):
        """Check if user is an admin user"""
        return self.user_type == 'admin'

    @property
    def is_customer(self):
        """Check if user is a customer"""
        return self.user_type == 'customer'

    def __str__(self):
        return self.phone