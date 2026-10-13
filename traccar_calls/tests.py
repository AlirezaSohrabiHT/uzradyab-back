from types import SimpleNamespace
from unittest.mock import Mock, patch

from rest_framework.test import APIRequestFactory, APISimpleTestCase, force_authenticate

from .views import CheckUserExistsView, FetchDevicesView, TraccarSessionView
from .client import traccar_request
import requests


class TraccarSessionViewTests(APISimpleTestCase):
    @patch("traccar_calls.views.requests.post")
    def test_session_uses_password_from_request_body(self, post):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"id": 123}

        request = APIRequestFactory().post(
            "/api/traccar/session/",
            {"password": "plain-pass"},
            format="json",
        )
        user = SimpleNamespace(phone="09123456789", is_authenticated=True)
        force_authenticate(request, user=user)

        response = TraccarSessionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs["json"]["password"], "plain-pass")


class CheckUserExistsViewTests(APISimpleTestCase):
    @patch("traccar_calls.views.requests.get")
    def test_check_user_exists_matches_phone_field(self, get):
        get.return_value = Mock(
            status_code=200,
            json=Mock(return_value=[
                {"id": 1, "email": "other@example.com", "phone": "09154284393"}
            ]),
        )

        request = APIRequestFactory().get(
            "/api/traccar/check-user-exists/",
            {"phone": "09154284393"},
        )

        response = CheckUserExistsView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"exists": True})


class RejectedTraccarTokenTests(APISimpleTestCase):
    @patch("accounts.models.User.objects.filter")
    @patch("traccar_calls.client.requests.get")
    def test_device_401_clears_only_rejected_token(self, get, user_filter):
        get.return_value = Mock(status_code=401, text="Unauthorized")
        user = SimpleNamespace(pk=7, is_authenticated=True, traccar_token="old-token")
        request = APIRequestFactory().get("/api/traccar/devices/")
        force_authenticate(request, user=user)
        response = FetchDevicesView.as_view()(request)
        self.assertEqual(response.status_code, 401)
        self.assertIsNone(user.traccar_token)
        user_filter.assert_called_once_with(pk=7, traccar_token="old-token")
        user_filter.return_value.update.assert_called_once_with(traccar_token=None)

    @patch("accounts.models.User.objects.filter")
    @patch("traccar_calls.client.requests.get")
    def test_other_failures_preserve_token(self, get, user_filter):
        user = SimpleNamespace(pk=7, traccar_token="old-token")
        for code in (200, 403, 404, 500):
            get.return_value = Mock(status_code=code)
            response = traccar_request(user, "get", "https://traccar.example/api/devices")
            self.assertEqual(response.status_code, code)
            self.assertEqual(user.traccar_token, "old-token")
        get.side_effect = requests.Timeout()
        with self.assertRaises(requests.Timeout):
            traccar_request(user, "get", "https://traccar.example/api/devices")
        self.assertEqual(user.traccar_token, "old-token")
        user_filter.assert_not_called()
