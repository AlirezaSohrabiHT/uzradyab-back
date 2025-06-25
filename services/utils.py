# services/utils.py
from django.utils import timezone
from datetime import timedelta
from services.models import CreditTransaction

def use_service(user, service, device):
    if user.credit < service.credit_cost:
        raise ValueError("Credit is not enough")

    # Deduct credit
    user.credit -= service.credit_cost
    user.save()

    # Log transaction
    CreditTransaction.objects.create(
        user=user,
        service=service,
        transaction_type='USE',
        amount=service.credit_cost,
        description=f"Used service '{service.name}' on device {device.name}"
    )

    # Extend device expirationTime
    if device.expiration_time:
        device.expiration_time += timedelta(days=service.duration_days)
    else:
        device.expiration_time = timezone.now() + timedelta(days=service.duration_days)

    device.save()
    return device.expiration_time
