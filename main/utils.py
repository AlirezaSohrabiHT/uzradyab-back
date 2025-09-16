# utils.py
from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model
from traccar_calls.views import UpdateDeviceView
import logging

logger = logging.getLogger('django')

User = get_user_model()

def update_expiration(device_id, duration_days):

    logger.info(f"device_id {device_id} and duration { duration_days}")
    
    """
    Call UpdateDeviceView.put directly to set a new expiration date.
    """
    from datetime import datetime, timedelta
    
    new_expiration = (datetime.utcnow() + timedelta(days=duration_days)).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # Get or create a system user for automated operations
    # Use 'phone' instead of 'username' since that's your User model's identifier
    system_user, created = User.objects.get_or_create(
        phone='system_payment',  # Changed from username to phone
        defaults={
            'is_staff': True,
        }
    )
    
    # Create a fake DRF request
    factory = APIRequestFactory()
    data = {
        "attributes": {
            "expiration": new_expiration
        }
    }
    request = factory.put(f'/devices/{device_id}', data, format='json')
    request.user = system_user
    
    # Call the view method directly
    view = UpdateDeviceView.as_view()
    response = view(request, device_id=device_id)
    return response