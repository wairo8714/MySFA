from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Group, Post

User = get_user_model()


class MySFATestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            custom_user_id="testuser",
        )
        self.client.login(username="testuser", password="testpass123")

    def test_home_page_loads(self):
        """ホームページが正常に読み込まれることをテスト"""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "MySFA")

    def test_user_registration(self):
        """ユーザー登録が正常に動作することをテスト"""
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "newuser",
                "custom_user_id": "newuser",
                "password1": "newpass123",
                "password2": "newpass123",
                "question": "Test question",
                "answer": "Test answer",
            },
        )
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertTrue(User.objects.filter(custom_user_id="newuser").exists())

    def test_post_creation(self):
        """投稿作成が正常に動作することをテスト"""
        # グループを作成してから投稿を作成
        group = Group.objects.create(
            name="Test Group",
            creator=self.user,
            custom_id="test123",
        )
        # ユーザーをグループに追加
        group.users.add(self.user)
        self.user.groups.add(group)

        response = self.client.post(
            reverse("mysfa:timeline"),
            {
                "product_name": "Test Product",
                "customer_category": "Test Category",
                "contents": "This is a test post",
                "group": group.id,
            },
        )
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertTrue(Post.objects.filter(product_name="Test Product").exists())

    def test_group_creation(self):
        """グループ作成が正常に動作することをテスト"""
        response = self.client.post(
            reverse("mysfa:create_group"),
            {"name": "Test Group"},
        )
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertTrue(Group.objects.filter(name="Test Group").exists())
