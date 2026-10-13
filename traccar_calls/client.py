import requests
from django.contrib.auth import get_user_model


def traccar_request(user, method, url, **kwargs):
    token = user.traccar_token
    response = getattr(requests, method)(url, **kwargs)
    if response.status_code == 401 and token:
        # Clear only the rejected token; preserve a concurrently regenerated token.
        get_user_model().objects.filter(pk=user.pk, traccar_token=token).update(
            traccar_token=None,
        )
        user.traccar_token = None
    return response
