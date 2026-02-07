from __future__ import annotations

from django.test import TestCase
from django.urls import reverse

from ..models import PostComment
from ..testing_utils import add_member, create_group, create_post, create_product, create_user


class LikeAndCommentTests(TestCase):
    def setUp(self):
        self.owner = create_user(custom_user_id="U800", username="owner")
        self.member = create_user(custom_user_id="U801", username="member")
        self.outsider = create_user(custom_user_id="U802", username="outsider")

        self.g = create_group(name="G800", creator=self.owner)
        add_member(group=self.g, user=self.member)

        p = create_product(group=self.g, product_code="P800", name="P800")
        self.post = create_post(user=self.owner, group=self.g, product=p)

    def test_like_toggles(self):
        self.client.force_login(self.member)
        url = reverse("mysfa:like_post", kwargs={"post_id": self.post.id})

        res1 = self.client.post(url)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertTrue(data1["liked"])
        self.assertEqual(data1["likes_count"], 1)

        res2 = self.client.post(url)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertFalse(data2["liked"])
        self.assertEqual(data2["likes_count"], 0)

    def test_comment_create_requires_group_membership(self):
        url = reverse("mysfa:post_comment_create", kwargs={"post_id": self.post.id})

        self.client.force_login(self.outsider)
        res = self.client.post(url, {"body": "hi"})
        self.assertEqual(res.status_code, 403)

    def test_comment_delete_allowed_for_author_or_post_owner(self):
        self.client.force_login(self.member)
        create_url = reverse("mysfa:post_comment_create", kwargs={"post_id": self.post.id})
        res = self.client.post(create_url, {"body": "hello"}, follow=True)
        self.assertEqual(res.status_code, 200)

        c = PostComment.objects.get(post=self.post)

        delete_url = reverse(
            "mysfa:post_comment_delete",
            kwargs={"post_id": self.post.id, "comment_id": c.id},
        )

        self.client.force_login(self.outsider)
        res2 = self.client.post(delete_url)
        self.assertEqual(res2.status_code, 403)

        self.client.force_login(self.owner)
        res3 = self.client.post(delete_url)
        self.assertEqual(res3.status_code, 302)
        self.assertFalse(PostComment.objects.filter(pk=c.pk).exists())

