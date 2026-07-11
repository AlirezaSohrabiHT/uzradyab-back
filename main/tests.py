from types import SimpleNamespace
from unittest.mock import patch

from rest_framework.test import APIRequestFactory, APISimpleTestCase, force_authenticate

from .models import AccountCharge
from .views import buy_package


class BuyPackageTests(APISimpleTestCase):
    @patch("main.views.AccountCharge.objects.get", side_effect=AccountCharge.DoesNotExist)
    @patch("main.views.requests.get")
    def test_missing_package_returns_404(self, get, account_charge_get):
        get.return_value.status_code = 200
        get.return_value.json.return_value = {
            "id": 10,
            "name": "Device",
            "uniqueId": "abc",
        }

        request = APIRequestFactory().post(
            "/buy-package/",
            {"deviceId": 10, "packageId": 999},
            format="json",
        )
        user = SimpleNamespace(
            is_authenticated=True,
            id=1,
            phone="09123456789",
            traccar_token="token",
            credit=0,
        )
        force_authenticate(request, user=user)

        response = buy_package(request)

        self.assertEqual(response.status_code, 404)
