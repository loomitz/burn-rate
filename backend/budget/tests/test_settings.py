from django.contrib.auth.models import User
from django.test import Client
from django.test import SimpleTestCase
from django.test import TestCase
from django.test import override_settings

from config import settings as project_settings


class SettingsDefaultsTests(SimpleTestCase):
    def test_local_vite_fallback_port_is_allowed_by_default(self):
        self.assertIn("http://localhost:5174", project_settings.DEFAULT_CORS_ALLOWED_ORIGINS)
        self.assertIn("http://localhost:5174", project_settings.DEFAULT_CSRF_TRUSTED_ORIGINS)

    def test_local_container_origin_remains_trusted_by_default(self):
        self.assertIn("http://localhost:8000", project_settings.DEFAULT_CSRF_TRUSTED_ORIGINS)


@override_settings(CSRF_TRUSTED_ORIGINS=project_settings.DEFAULT_CSRF_TRUSTED_ORIGINS)
class LoginCsrfOriginTests(TestCase):
    def test_login_accepts_local_vite_fallback_origin(self):
        User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="testpass123",
        )
        client = Client(enforce_csrf_checks=True)

        csrf_response = client.get("/api/auth/csrf/", HTTP_ORIGIN="http://localhost:5174")
        token = csrf_response.cookies["csrftoken"].value
        response = client.post(
            "/api/auth/login/",
            data='{"email": "admin@example.com", "password": "testpass123"}',
            content_type="application/json",
            HTTP_ORIGIN="http://localhost:5174",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 200)
