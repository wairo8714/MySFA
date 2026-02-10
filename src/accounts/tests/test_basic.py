from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class AccountsBasicTest(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="TEST001",
            custom_user_id="TEST001",
            password="testpass123",
            question="テスト質問",
            answer="テスト回答",
        )

    def test_signup_page_loads(self):
        response = self.client.get(reverse("accounts:signup"))
        self.assertEqual(response.status_code, 200)

    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_user_can_login(self):
        login_data = {"username": "TEST001", "password": "testpass123"}
        response = self.client.post(reverse("login"), login_data)
        self.assertEqual(response.status_code, 302)
