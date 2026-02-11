from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.test import TestCase


class CustomUserModelTests(TestCase):
    def test_answer_is_hashed_on_save(self):
        User = get_user_model()
        u = User.objects.create_user(
            custom_user_id="U900",
            username="u900",
            password="pass12345",
            question="q",
            answer="secret-answer",
        )
        self.assertNotEqual(u.answer, "secret-answer")
        self.assertTrue(check_password("secret-answer", u.answer))
