from __future__ import annotations

from datetime import datetime

from django.test import TestCase
from django.urls import reverse

from ..models import Post
from ..testing_utils import create_group, create_industry, create_post, create_product, create_user


class SearchProductsViewTests(TestCase):
    def setUp(self):
        self.u = create_user(custom_user_id="U400", username="u400")
        self.g1 = create_group(name="G1", creator=self.u)
        self.g2 = create_group(name="G2", creator=self.u)
        self.client.force_login(self.u)

        p1 = create_product(group=self.g1, product_code="COKE01", name="Coca Cola", category_main="飲料", category_sub="炭酸")
        p2 = create_product(group=self.g2, product_code="WATER01", name="Mineral Water", category_main="飲料", category_sub="水")
        ind = create_industry(group=self.g1, name="居酒屋")

        create_post(
            user=self.u,
            group=self.g1,
            product=p1,
            industry=ind,
            status=Post.Status.ADOPTED,
            created_at=datetime(2026, 2, 1, 10, 0, 0),
        )
        create_post(
            user=self.u,
            group=self.g2,
            product=p2,
            industry=None,
            status=Post.Status.ADOPTED,
            created_at=datetime(2026, 2, 3, 10, 0, 0),
        )

    def test_no_params_did_search_false(self):
        url = reverse("mysfa:search_products")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.context["did_search"])

    def test_filter_by_group_custom_id(self):
        url = reverse("mysfa:search_products")
        res = self.client.get(url, {"group": self.g1.custom_id})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.context["did_search"])
        posts = list(res.context["object_list"])
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].group_id, self.g1.id)

    def test_query_partial_matches_product_code(self):
        url = reverse("mysfa:search_products")
        res = self.client.get(url, {"q": "COKE"})
        self.assertEqual(res.status_code, 200)
        posts = list(res.context["object_list"])
        self.assertEqual(len(posts), 1)
        self.assertIn("COKE01", posts[0].product.product_code)

    def test_query_exact_matches_product_name(self):
        url = reverse("mysfa:search_products")
        res = self.client.get(url, {"q": "Mineral Water", "match": "exact"})
        self.assertEqual(res.status_code, 200)
        posts = list(res.context["object_list"])
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].product.name, "Mineral Water")

    def test_category_filters_respect_match_mode(self):
        url = reverse("mysfa:search_products")
        res = self.client.get(
            url,
            {"group": self.g1.custom_id, "category_main": "飲", "match": "partial"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(list(res.context["object_list"])), 1)

        res2 = self.client.get(
            url,
            {"group": self.g1.custom_id, "category_main": "飲", "match": "exact"},
        )
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(len(list(res2.context["object_list"])), 0)

    def test_date_range_filters(self):
        url = reverse("mysfa:search_products")
        res = self.client.get(url, {"start_date": "2026-02-02", "end_date": "2026-02-10"})
        self.assertEqual(res.status_code, 200)
        posts = list(res.context["object_list"])
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].product.product_code, "WATER01")


class SearchCustomersViewTests(TestCase):
    def setUp(self):
        self.u = create_user(custom_user_id="U410", username="u410")
        self.g = create_group(name="G410", creator=self.u)
        self.client.force_login(self.u)

        ind1 = create_industry(group=self.g, name="カフェ")
        ind2 = create_industry(group=self.g, name="居酒屋")
        p = create_product(group=self.g, product_code="P", name="p")

        create_post(user=self.u, group=self.g, product=p, industry=ind1, created_at=datetime(2026, 2, 1, 10, 0, 0))
        create_post(user=self.u, group=self.g, product=p, industry=ind2, created_at=datetime(2026, 2, 5, 10, 0, 0))

    def test_partial_and_exact(self):
        url = reverse("mysfa:search_customers")
        res = self.client.get(url, {"q": "カ"})
        self.assertEqual(len(list(res.context["object_list"])), 1)

        res2 = self.client.get(url, {"q": "カ", "match": "exact"})
        self.assertEqual(len(list(res2.context["object_list"])), 0)

        res3 = self.client.get(url, {"q": "カフェ", "match": "exact"})
        self.assertEqual(len(list(res3.context["object_list"])), 1)

