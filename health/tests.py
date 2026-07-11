from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from managerPanel import settings


class AppConfigEndpointTests(SimpleTestCase):
    @override_settings(
        APP_NEW_RELEASE=True,
        APP_NEW_RELEASE_CODE="123",
        APP_NEW_RELEASE_DESCRIPTION=[
            {"key": "1", "value": "fix ui bug"},
            {"key": "2", "value": "fix payment"},
        ],
        APP_ALTERNATIVE_MAP=True,
        APP_ALTERNATIVE_MAP_URL="https://map.domain.com",
    )
    def test_app_config_endpoint_is_public_and_returns_release_flags(self):
        response = self.client.get("/api/app-config/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "new_release": True,
                "new_release_code": "123",
                "new_release_description": [
                    {"key": "1", "value": "fix ui bug"},
                    {"key": "2", "value": "fix payment"},
                ],
                "alternative_map": True,
                "alternative_map_url": "https://map.domain.com",
            },
        )

    def test_release_description_env_value_is_parsed_as_key_value_list(self):
        with patch.dict(
            "os.environ",
            {
                "APP_NEW_RELEASE_DESCRIPTION": '[{"key":"1","value":"fix ui bug"},{"key":"2","value":"fix payment"}]',
            },
        ):
            self.assertEqual(
                settings.env_key_value_list("APP_NEW_RELEASE_DESCRIPTION"),
                [
                    {"key": "1", "value": "fix ui bug"},
                    {"key": "2", "value": "fix payment"},
                ],
            )
