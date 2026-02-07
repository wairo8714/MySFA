from __future__ import annotations

from datetime import datetime

from django.test import TestCase
from django.urls import reverse

from ..models import Post
from .utils import create_group, create_post, create_product, create_user


class SalesReportViewTests(TestCase):
    def setUp(self):
        self.u = create_user(custom_user_id="U500", username="u500")
        self.g = create_group(name="G500", creator=self.u)
        self.client.force_login(self.u)

    def test_requires_dates(self):
        url = reverse("mysfa:sales_report")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 400)

    def test_invalid_date_returns_400(self):
        url = reverse("mysfa:sales_report")
        res = self.client.get(url, {"start_date": "bad", "end_date": "2026-01-01"})
        self.assertEqual(res.status_code, 400)

    def test_group_sales_report_counts_only_adopted_and_aggregates_other(self):
        products = []
        for i in range(1, 8):
            products.append(create_product(group=self.g, product_code=f"P{i:03d}", name=f"Prod{i}"))

        counts = [6, 5, 4, 3, 2, 1, 1]
        for prod, n in zip(products, counts, strict=True):
            for k in range(n):
                create_post(
                    user=self.u,
                    group=self.g,
                    product=prod,
                    industry=None,
                    status=Post.Status.ADOPTED,
                    created_at=datetime(2026, 2, 2, 10, 0, k),
                )

        create_post(
            user=self.u,
            group=self.g,
            product=products[0],
            industry=None,
            status=Post.Status.NEGOTIATING,
            created_at=datetime(2026, 2, 2, 12, 0, 0),
        )

        url = reverse("mysfa:group_sales_report", kwargs={"group_id": self.g.custom_id})
        res = self.client.get(url, {"start_date": "2026-02-01", "end_date": "2026-02-10"})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        product_data = data["product_data"]
        self.assertEqual(len(product_data), 6)
        self.assertEqual(data["total_posts"], sum(counts))

        other = [x for x in product_data if x.get("label") == "その他"]
        self.assertEqual(len(other), 1)
        self.assertEqual(other[0]["count"], 2)

    def test_accepts_slash_date_format(self):
        p = create_product(group=self.g, product_code="P999", name="P999")
        create_post(
            user=self.u,
            group=self.g,
            product=p,
            industry=None,
            status=Post.Status.ADOPTED,
            created_at=datetime(2026, 2, 2, 10, 0, 0),
        )
        url = reverse("mysfa:group_sales_report", kwargs={"group_id": self.g.custom_id})
        res = self.client.get(url, {"start_date": "2026/02/01", "end_date": "2026/02/10"})
        self.assertEqual(res.status_code, 200)

