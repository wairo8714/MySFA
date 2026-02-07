from __future__ import annotations

from django.test import TestCase
from django.urls import reverse

from .utils import create_group, create_post, create_product, create_user


class TimelineAndMyPostTests(TestCase):
    def setUp(self):
        self.u = create_user(custom_user_id="U850", username="u850")
        self.g1 = create_group(name="TG1", creator=self.u)
        self.g2 = create_group(name="TG2", creator=self.u)
        self.client.force_login(self.u)

        p1 = create_product(group=self.g1, product_code="TP1", name="tp1")
        p2 = create_product(group=self.g2, product_code="TP2", name="tp2")
        create_post(user=self.u, group=self.g1, product=p1, contents="in g1")
        create_post(user=self.u, group=self.g2, product=p2, contents="in g2")

    def test_timeline_shows_posts_from_all_user_groups(self):
        url = reverse("mysfa:timeline")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        posts = list(res.context["object_list"])
        self.assertEqual(len(posts), 2)

    def test_timeline_can_filter_by_group_custom_id(self):
        url = reverse("mysfa:timeline")
        res = self.client.get(url, {"custom_id": self.g1.custom_id})
        self.assertEqual(res.status_code, 200)
        posts = list(res.context["object_list"])
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].contents, "in g1")

    def test_mypost_page_loads(self):
        url = reverse("mysfa:mypost", kwargs={"custom_user_id": self.u.custom_user_id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

