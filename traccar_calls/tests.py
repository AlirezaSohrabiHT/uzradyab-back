from types import SimpleNamespace
from unittest.mock import Mock, patch

from rest_framework.test import APIRequestFactory, APISimpleTestCase, force_authenticate

from .views import CheckUserExistsView, TraccarSessionView


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
