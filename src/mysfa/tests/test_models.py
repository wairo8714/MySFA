from __future__ import annotations

from django.db import IntegrityError, transaction
from django.test import TestCase

from ..models import GroupMembership
from ..testing_utils import create_group, create_industry, create_product, create_user


class GroupModelTests(TestCase):
    def test_custom_id_is_generated_and_8_digits(self):
        u = create_user(custom_user_id="U100", username="u100")
        g = create_group(name="G100", creator=u)
        self.assertTrue(g.custom_id)
        self.assertEqual(len(g.custom_id), 8)
        self.assertTrue(g.custom_id.isdigit())


class MasterConstraintsTests(TestCase):
    def setUp(self):
        self.u = create_user(custom_user_id="U200", username="u200")
        self.g = create_group(name="G200", creator=self.u)

    def test_product_code_unique_within_group(self):
        create_product(group=self.g, product_code="P001", name="A")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                create_product(group=self.g, product_code="P001", name="B")

    def test_industry_name_unique_within_group(self):
        create_industry(group=self.g, name="X")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                create_industry(group=self.g, name="X")

    def test_group_membership_unique(self):
        u2 = create_user(custom_user_id="U201", username="u201")
        GroupMembership.objects.create(group=self.g, user=u2, role=GroupMembership.Role.MEMBER, is_active=True)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                GroupMembership.objects.create(group=self.g, user=u2, role=GroupMembership.Role.MEMBER, is_active=True)

