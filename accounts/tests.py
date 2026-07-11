from types import SimpleNamespace
from unittest.mock import patch

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
