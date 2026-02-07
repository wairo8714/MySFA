from __future__ import annotations

from django.test import TestCase
from django.urls import reverse

from ..testing_utils import add_member, create_group, create_user


class SearchGroupViewTests(TestCase):
    def setUp(self):
        self.u = create_user(custom_user_id="U700", username="u700")
        self.client.force_login(self.u)

        self.joined_open = create_group(name="JoinedOpen", creator=self.u, is_locked=False)
        self.joined_locked = create_group(name="JoinedLocked", creator=self.u, is_locked=True)

        other = create_user(custom_user_id="U701", username="u701")
        self.not_joined_open = create_group(name="OtherOpen", creator=other, is_locked=False)
        self.not_joined_locked = create_group(name="OtherLocked", creator=other, is_locked=True)

    def test_membership_filters(self):
        url = reverse("mysfa:search_group")

        res = self.client.get(url, {"membership": "joined"})
        names = [g.name for g in res.context["groups"]]
        self.assertIn(self.joined_open.name, names)
        self.assertIn(self.joined_locked.name, names)
        self.assertNotIn(self.not_joined_open.name, names)

        res2 = self.client.get(url, {"membership": "not_joined"})
        names2 = [g.name for g in res2.context["groups"]]
        self.assertIn(self.not_joined_open.name, names2)
        self.assertNotIn(self.joined_open.name, names2)

    def test_lock_filters(self):
        url = reverse("mysfa:search_group")
        res = self.client.get(url, {"lock": "locked"})
        names = [g.name for g in res.context["groups"]]
        self.assertIn(self.joined_locked.name, names)
        self.assertIn(self.not_joined_locked.name, names)
        self.assertNotIn(self.joined_open.name, names)


class SearchUsersViewTests(TestCase):
    def setUp(self):
        self.u = create_user(custom_user_id="U710", username="owner")
        self.g = create_group(name="G710", creator=self.u)
        self.client.force_login(self.u)

        self.u2 = create_user(custom_user_id="ABC123", username="Alice")
        self.u3 = create_user(custom_user_id="XYZ999", username="Bob")
        add_member(group=self.g, user=self.u2)

    def test_query_partial_and_exact(self):
        url = reverse("mysfa:search_users")

        res = self.client.get(url, {"q": "Ali"})
        ids = [u.custom_user_id for u in res.context["object_list"]]
        self.assertIn("ABC123", ids)
        self.assertNotIn("XYZ999", ids)

        res2 = self.client.get(url, {"q": "Ali", "match": "exact"})
        self.assertEqual(len(list(res2.context["object_list"])), 0)

        res3 = self.client.get(url, {"q": "Alice", "match": "exact"})
        ids3 = [u.custom_user_id for u in res3.context["object_list"]]
        self.assertIn("ABC123", ids3)

    def test_group_filter_limits_to_selected_group(self):
        url = reverse("mysfa:search_users")
        res = self.client.get(url, {"group": self.g.custom_id})
        ids = [u.custom_user_id for u in res.context["object_list"]]
        self.assertIn("ABC123", ids)
        self.assertNotIn("XYZ999", ids)

    def test_unknown_group_is_ignored(self):
        url = reverse("mysfa:search_users")
        res = self.client.get(url, {"group": "nope"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["selected_group_custom_id"], "")

