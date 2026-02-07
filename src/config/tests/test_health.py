from __future__ import annotations

from django.test import TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    def test_health_endpoint(self):
        res = self.client.get(reverse("health"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json().get("status"), "healthy")

    def test_api_health_endpoint(self):
        res = self.client.get(reverse("api_health"))
        self.assertEqual(res.status_code, 200)
