from django.test import SimpleTestCase


class ApiDocumentationTests(SimpleTestCase):
    def test_swagger_ui(self):
        response = self.client.get('/api/docs/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SwaggerUIBundle')

    def test_openapi_covers_backend(self):
        response = self.client.get('/api/schema/', HTTP_ACCEPT='application/vnd.oai.openapi+json')
        self.assertEqual(response.status_code, 200)
        schema = response.json()
        for path in ('/api/accounts/login/', '/api/accounts/check-traccar-token/',
                     '/api/accounts/generate-traccar-token/', '/api/traccar/devices/',
                     '/api/services/', '/buy-package/'):
            self.assertTrue(any(p.startswith(path.rstrip('/')) for p in schema['paths']), path)
        self.assertIn('tokenAuth', schema['components']['securitySchemes'])
