# utils.py
from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model
from traccar_calls.views import UpdateDeviceView

User = get_user_model()

def update_expiration(device_id, period, user):
    """
    Call UpdateDeviceView.put directly to set a new expiration date.
    """
    from datetime import datetime, timedelta
    new_expiration = (datetime.utcnow() + timedelta(days=period)).strftime('%Y-%m-%dT%H:%M:%SZ')

    # Create a fake DRF request
    factory = APIRequestFactory()
    data = {
        "attributes": {
            "expiration": new_expiration
        }
    }
    request = factory.put(f'/devices/{device_id}', data, format='json')
    request.user = user  # Attach authenticated user

    # Call the view method directly
    view = UpdateDeviceView.as_view()
    response = view(request, device_id=device_id)

    return response
