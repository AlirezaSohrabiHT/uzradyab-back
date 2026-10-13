from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests
from django.test import override_settings

from rest_framework.test import APISimpleTestCase


class ResetPasswordTests(APISimpleTestCase):
    @patch("otpmanager.utils.send_otp", return_value=(True, "sent"))
    @patch("accounts.views.User.objects.get")
    def test_reset_password_uses_otp_helper_for_send_step(self, user_get, send_otp):
        user_get.return_value = SimpleNamespace(id=1)

        response = self.client.post(
            "/api/accounts/reset-password/",
            {"phoneNumber": "09123456789"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        send_otp.assert_called_once_with("09123456789")


@override_settings(TRACCAR_API_URL="https://traccar.example/api")
class CheckTraccarTokenTests(APISimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(pk=1, is_authenticated=True, traccar_token="test-token")
        self.client.force_authenticate(user=self.user)

    @patch("accounts.models.User.objects.filter")
    @patch("accounts.views.requests.get")
    def test_rejected_token_requires_regeneration(self, get, user_filter):
        get.return_value = Mock(status_code=401)
        response = self.client.get("/api/accounts/check-traccar-token/")
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.data.get("valid"), False)
        self.assertIs(response.data["requires_regeneration"], True)
        self.assertIn("invalid or expired", response.data["message"])
        user_filter.assert_called_once_with(pk=1, traccar_token="test-token")
        user_filter.return_value.update.assert_called_once_with(traccar_token=None)
        self.assertIsNone(self.user.traccar_token)
        get.assert_called_once_with(
            "https://traccar.example/api/devices",
            headers={"Authorization": "Bearer test-token"},
            params={"id": 0}, timeout=10, allow_redirects=False,
        )

    @patch("accounts.views.requests.get")
    def test_valid_token(self, get):
        get.return_value = Mock(status_code=200)
        response = self.client.get("/api/accounts/check-traccar-token/")
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.data["valid"], True)
        self.assertIs(response.data["requires_regeneration"], False)

    @patch("accounts.views.requests.get")
    def test_missing_token_skips_traccar(self, get):
        self.user.traccar_token = None
        response = self.client.get("/api/accounts/check-traccar-token/")
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.data["valid"], False)
        self.assertIs(response.data["requires_regeneration"], True)
        get.assert_not_called()

    @patch("accounts.views.requests.get")
    def test_timeout_does_not_report_expired_token(self, get):
        get.side_effect = requests.Timeout()
        response = self.client.get("/api/accounts/check-traccar-token/")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("requires_regeneration", response.data)

    @patch("accounts.views.requests.get")
    def test_unexpected_status_does_not_report_expired_token(self, get):
        for code in (302, 403, 404, 500):
            with self.subTest(code=code):
                get.return_value = Mock(status_code=code)
                response = self.client.get("/api/accounts/check-traccar-token/")
                self.assertEqual(response.status_code, 502)
                self.assertNotIn("requires_regeneration", response.data)

    @patch("accounts.views.requests.get")
    def test_requires_backend_authentication(self, get):
        response = self.client_class().get("/api/accounts/check-traccar-token/")
        self.assertEqual(response.status_code, 401)
        get.assert_not_called()
