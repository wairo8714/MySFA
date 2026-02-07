from __future__ import annotations

from django.test import TestCase
from django.urls import reverse

from ..models import Group
from .utils import create_user


class BasicViewAuthTests(TestCase):
    def setUp(self):
        self.u = create_user(custom_user_id="U600", username="u600")

    def test_timeline_requires_login(self):
        url = reverse("mysfa:timeline")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)

    def test_timeline_ok_when_logged_in(self):
        self.client.force_login(self.u)
        url = reverse("mysfa:timeline")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("form", res.context)

    def test_create_group_requires_login(self):
        url = reverse("mysfa:create_group")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)

    def test_create_group_post_creates_and_redirects(self):
        self.client.force_login(self.u)
        url = reverse("mysfa:create_group")
        res = self.client.post(url, {"name": "New Group"})
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Group.objects.filter(name="New Group").exists())
