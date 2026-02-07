from __future__ import annotations

from django.test import TestCase
from django.urls import reverse

from .utils import create_group, create_industry, create_product, create_user


class MyGroupsApiTests(TestCase):
    def test_requires_login(self):
        url = reverse("mysfa:my_groups_api")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)

    def test_returns_only_active_groups_for_user(self):
        u = create_user(custom_user_id="U300", username="u300")
        g1 = create_group(name="A", creator=u, is_active=True)
        g2 = create_group(name="B", creator=u, is_active=False)

        self.client.force_login(u)
        url = reverse("mysfa:my_groups_api")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        ids = [x["custom_id"] for x in data.get("results", [])]
        self.assertIn(g1.custom_id, ids)
        self.assertNotIn(g2.custom_id, ids)


class ProductCategoryOptionsApiTests(TestCase):
    def setUp(self):
        self.u = create_user(custom_user_id="U310", username="u310")
        self.g = create_group(name="G310", creator=self.u)
        self.client.force_login(self.u)

    def test_requires_membership(self):
        other = create_user(custom_user_id="U311", username="u311")
        other_group = create_group(name="G311", creator=other)
        url = reverse("mysfa:product_category_options_api", kwargs={"custom_id": other_group.custom_id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)

    def test_returns_distinct_sorted_categories(self):
        create_product(group=self.g, product_code="P1", name="n1", category_main="飲料", category_sub="炭酸")
        create_product(group=self.g, product_code="P2", name="n2", category_main="飲料", category_sub="水")
        create_product(group=self.g, product_code="P3", name="n3", category_main="菓子", category_sub="")
        create_product(group=self.g, product_code="P4", name="n4", category_main=None, category_sub=None)

        url = reverse("mysfa:product_category_options_api", kwargs={"custom_id": self.g.custom_id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["category_main"], ["菓子", "飲料"])
        self.assertEqual(data["category_sub"], ["炭酸", "水"])


class MasterSearchApiTests(TestCase):
    def setUp(self):
        self.u = create_user(custom_user_id="U320", username="u320")
        self.g = create_group(name="G320", creator=self.u)
        self.client.force_login(self.u)

        create_product(group=self.g, product_code="AAA", name="Alpha")
        create_product(group=self.g, product_code="BBB", name="Bravo")
        create_industry(group=self.g, name="居酒屋")
        create_industry(group=self.g, name="カフェ")

    def test_product_master_search_api_filters_by_q(self):
        url = reverse("mysfa:product_master_api", kwargs={"custom_id": self.g.custom_id})
        res = self.client.get(url, {"q": "AA", "limit": 50})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        labels = [x["label"] for x in data.get("results", [])]
        self.assertTrue(any("AAA" in s for s in labels))
        self.assertFalse(any("BBB" in s for s in labels))

    def test_industry_master_search_api_filters_by_q(self):
        url = reverse("mysfa:industry_master_api", kwargs={"custom_id": self.g.custom_id})
        res = self.client.get(url, {"q": "カ", "limit": 50})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        names = [x["name"] for x in data.get("results", [])]
        self.assertIn("カフェ", names)
        self.assertNotIn("居酒屋", names)

    def test_search_api_requires_membership(self):
        other = create_user(custom_user_id="U321", username="u321")
        other_group = create_group(name="G321", creator=other)
        url = reverse("mysfa:product_master_api", kwargs={"custom_id": other_group.custom_id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)

