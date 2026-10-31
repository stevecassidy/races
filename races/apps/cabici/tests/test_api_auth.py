#!/usr/bin/python

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
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

    def test_register_creates_user_and_rider(self):
        payload = {
            "username": "new-user",
            "email": "new-user@example.com",
            "password": "new-user-password-123",
            "first_name": "New",
            "last_name": "User",
        }
        response = self.client.post("/api/v1/auth/register/", payload, format="json")

        self.assertEqual(201, response.status_code)
        body = response.json()
        self.assertEqual("new-user", body["username"])
        created_user = User.objects.get(username="new-user")
        self.assertTrue(Rider.objects.filter(user=created_user).exists())

    def test_register_rejects_duplicate_username(self):
        payload = {
            "username": "auth-user",
            "email": "duplicate@example.com",
            "password": "duplicate-user-password-123",
        }
        response = self.client.post("/api/v1/auth/register/", payload, format="json")
        self.assertEqual(400, response.status_code)

    def test_profile_requires_authentication(self):
        response = self.client.get("/api/v1/auth/profile/")
        self.assertEqual(401, response.status_code)

    def test_profile_get_and_patch(self):
        access, _ = self._obtain_access_token("auth-user")
        headers = {"HTTP_AUTHORIZATION": f"Bearer {access}"}

        get_response = self.client.get("/api/v1/auth/profile/", **headers)
        self.assertEqual(200, get_response.status_code)
        self.assertEqual("auth-user", get_response.json()["username"])

        patch_response = self.client.patch(
            "/api/v1/auth/profile/",
            {"first_name": "Updated", "last_name": "Name"},
            format="json",
            **headers,
        )
        self.assertEqual(200, patch_response.status_code)
        updated = patch_response.json()
        self.assertEqual("Updated", updated["first_name"])
        self.assertEqual("Name", updated["last_name"])

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

    def test_password_reset_request_returns_success_for_unknown_email(self):
        response = self.client.post(
            "/api/v1/auth/password-reset/",
            {"email": "missing@example.com"},
            format="json",
        )
        self.assertEqual(200, response.status_code)

    def test_password_reset_confirm_rejects_invalid_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            {"uid": uid, "token": "invalid-token", "new_password": "new-password-123"},
            format="json",
        )
        self.assertEqual(400, response.status_code)

    def test_password_reset_confirm_changes_password(self):
        old_password = self.password
        new_password = "changed-password-123"
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            {"uid": uid, "token": token, "new_password": new_password},
            format="json",
        )
        self.assertEqual(200, response.status_code)

        old_login = self.client.post(
            "/api/v1/auth/token/",
            {"username": "auth-user", "password": old_password},
            format="json",
        )
        self.assertEqual(401, old_login.status_code)

        new_login = self.client.post(
            "/api/v1/auth/token/",
            {"username": "auth-user", "password": new_password},
            format="json",
        )
        self.assertEqual(200, new_login.status_code)
