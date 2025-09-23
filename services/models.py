# services/models.py
from django.db import models
from django.conf import settings

class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    credit_cost = models.PositiveIntegerField()  # e.g., 100
    duration_days = models.PositiveIntegerField()  # e.g., 365
    price = models.BigIntegerField()
    

    def __str__(self):
        return f"{self.name} ({self.credit_cost} credits)"


class CreditTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('USE', 'Use'),
        ('ADD', 'Add'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    service = models.ForeignKey('Service', on_delete=models.SET_NULL, null=True, blank=True)
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.phone} - {self.transaction_type} - {self.amount}"
