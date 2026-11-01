from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from .views import AdminDashboardView


class DashboardAuthorizationTests(SimpleTestCase):
    def test_non_admin_cannot_access_dashboard(self):
        request = APIRequestFactory().get("/api/admin/analytics/")
        user = type("User", (), {"id": "u", "role": "user", "is_authenticated": True})()
        force_authenticate(request, user=user)
        self.assertEqual(AdminDashboardView.as_view()(request).status_code, 403)
