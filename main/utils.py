# utils.py
from requests.auth import HTTPBasicAuth
from django.contrib.auth import get_user_model
from traccar_calls.views import UpdateDeviceView
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from datetime import datetime, timedelta, timezone
import requests
import logging

logger = logging.getLogger('django')

User = get_user_model()

def update_expiration(device_id, duration_days):

    logger.info(f"device_id {device_id} and duration { duration_days}")
    
    """
    Call UpdateDeviceView.put directly to set a new expiration date.
    """
    
    
    new_expiration = (datetime.now(timezone.utc) + timedelta(days=duration_days)).isoformat(timespec="milliseconds")
    url = f"{settings.TRACCAR_API_URL}/devices/{device_id}"
    headers = {
            "Authorization": f"Bearer e8fbe7c116e452ed8c666790cfb5ba30ed7e8f97"
        }
    data = {
        "expirationTime": new_expiration
    }
    try:
        # Step 1: GET full device
        resp = requests.get(
            url,
            auth=HTTPBasicAuth(settings.TRACCAR_API_USERNAME, settings.TRACCAR_API_PASSWORD),
            timeout=30
        )
        if resp.status_code != 200:
            return Response({"error": f"GET failed: {resp.text}"}, status=resp.status_code)

        device = resp.json()

        # Step 2: update expirationTime
        device["expirationTime"] = new_expiration

        # Step 3: PUT full device with Basic Auth
        r = requests.put(
            url,
            json=device,
            auth=HTTPBasicAuth(settings.TRACCAR_API_USERNAME, settings.TRACCAR_API_PASSWORD),
            timeout=30
        )

        if r.status_code == 200:
            return Response(r.json(), status=200)
        return Response({"detail": r.text}, status=r.status_code)

    except Exception as e:
        return Response({"error": str(e)}, status=500)