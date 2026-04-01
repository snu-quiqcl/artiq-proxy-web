from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

User = get_user_model()


class AuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="alice",
            password="secret-pass",
        )

    def test_login_returns_token_shape(self):
        response = self.client.post(
            "/api/login/",
            {"username": "alice", "password": "secret-pass"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data.keys()),
            {"token", "username", "user_id"},
        )
        self.assertEqual(response.data["username"], "alice")
        self.assertEqual(response.data["user_id"], self.user.pk)
        self.assertTrue(Token.objects.filter(user=self.user).exists())

    def test_login_invalid_credentials(self):
        response = self.client.post(
            "/api/login/",
            {"username": "alice", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_deletes_token(self):
        login = self.client.post(
            "/api/login/",
            {"username": "alice", "password": "secret-pass"},
            format="json",
        )
        token = login.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        out = self.client.post("/api/logout/", {}, format="json")
        self.assertEqual(out.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_logout_without_token(self):
        response = self.client.post("/api/logout/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
