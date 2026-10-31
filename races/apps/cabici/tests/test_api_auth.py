#!/usr/bin/python

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from races.apps.cabici.models import Club, Rider


class V1AuthTests(APITestCase):
    fixtures = ["clubs"]

    def setUp(self):
        self.password = "test-password-123"
        self.user = User.objects.create_user(
            username="auth-user",
            password=self.password,
            email="auth-user@example.com",
            first_name="Auth",
            last_name="User",
        )
        club = Club.objects.first()
        self.rider = Rider.objects.create(user=self.user, club=club, official=True)

        self.user_without_rider = User.objects.create_user(
            username="no-rider-user",
            password=self.password,
            email="no-rider@example.com",
        )

    def _obtain_access_token(self, username):
        response = self.client.post(
            "/api/v1/auth/token/",
            {"username": username, "password": self.password},
            format="json",
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertIn("access", payload)
        self.assertIn("refresh", payload)
        return payload["access"], payload["refresh"]

    def test_token_obtain_and_refresh_endpoints(self):
        access, refresh = self._obtain_access_token("auth-user")
        self.assertTrue(access)
        self.assertTrue(refresh)

        refresh_response = self.client.post("/api/v1/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(200, refresh_response.status_code)
        refreshed = refresh_response.json()
        self.assertIn("access", refreshed)

    def test_token_obtain_rejects_invalid_credentials(self):
        response = self.client.post(
            "/api/v1/auth/token/",
            {"username": "auth-user", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(401, response.status_code)

    def test_auth_me_requires_authentication(self):
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(401, response.status_code)

    def test_auth_me_returns_user_and_rider_fields(self):
        access, _ = self._obtain_access_token("auth-user")
        response = self.client.get("/api/v1/auth/me/", HTTP_AUTHORIZATION=f"Bearer {access}")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(self.user.id, payload["id"])
        self.assertEqual("auth-user", payload["username"])
        self.assertEqual(self.rider.id, payload["rider_id"])
        self.assertEqual(self.rider.club_id, payload["club_id"])
        self.assertTrue(payload["official"])

    def test_auth_me_handles_user_without_rider(self):
        access, _ = self._obtain_access_token("no-rider-user")
        response = self.client.get("/api/v1/auth/me/", HTTP_AUTHORIZATION=f"Bearer {access}")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(self.user_without_rider.id, payload["id"])
        self.assertIsNone(payload["rider_id"])
        self.assertIsNone(payload["club_id"])
        self.assertFalse(payload["official"])
