from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class AccountsBasicTest(TestCase):
    """Accountsアプリの基本的なテスト"""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser",
            custom_user_id="TEST001",
            email="test@example.com",
            password="testpass123",
            question="テスト質問",
            answer="テスト回答",
        )

    def test_signup_page_loads(self):
        """サインアップページが正常に読み込まれるかテスト"""
        response = self.client.get(reverse("accounts:signup"))
        self.assertEqual(response.status_code, 200)

    def test_login_page_loads(self):
        """ログインページが正常に読み込まれるかテスト"""
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_user_can_login(self):
        """ユーザーログインが正常に動作するかテスト"""
        login_data = {"username": "testuser", "password": "testpass123"}
        response = self.client.post(reverse("login"), login_data)
        self.assertEqual(response.status_code, 302)
