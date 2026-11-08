#!/usr/bin/python

from rest_framework.test import APITestCase

from races.apps.cabici.models import Club, ClubRole, PointScore, Race, Rider, UserRole


class V1ContractTests(APITestCase):
    fixtures = ["clubs", "courses", "races", "users", "riders", "clubroles"]

    def test_v1_root_returns_expected_resources(self):
        response = self.client.get("/api/v1/")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertIn("clubs", payload)
        self.assertIn("club_roles", payload)
        self.assertIn("riders", payload)
        self.assertIn("user_roles", payload)
        self.assertIn("races", payload)
        self.assertIn("race_courses", payload)
        self.assertIn("race_results", payload)
        self.assertIn("pointscores", payload)
        self.assertIn("auth_token", payload)
        self.assertIn("auth_refresh", payload)
        self.assertIn("auth_logout", payload)
        self.assertIn("auth_me", payload)
        self.assertIn("auth_register", payload)
        self.assertIn("auth_profile", payload)
        self.assertIn("auth_password_reset", payload)
        self.assertIn("auth_password_reset_confirm", payload)
        self.assertIn("schema", payload)

    def test_v1_clubs_endpoint_is_available(self):
        response = self.client.get("/api/v1/clubs/")

        self.assertEqual(200, response.status_code)
        clubs = response.json()
        self.assertGreater(len(clubs), 0)
        self.assertIn("slug", clubs[0])

    def test_races_endpoint_supports_filters(self):
        response = self.client.get("/api/v1/races/?status=d")

        self.assertEqual(200, response.status_code)
        races = response.json()
        self.assertTrue(races)
        self.assertTrue(all(race["status"] == "d" for race in races))

    def test_pointscores_endpoint_exposes_domain_action(self):
        club = Club.objects.first()
        pointscore = PointScore.objects.create(club=club, name="Season Points")

        response = self.client.post(f"/api/v1/pointscores/{pointscore.pk}/recalculate/")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(pointscore.pk, payload["pointscore"])
        self.assertEqual("Season Points", payload["name"])
        self.assertIn("tallies", payload)

    def test_racecourses_endpoint_supports_filters(self):
        response = self.client.get("/api/v1/racecourses/?name__icontains=sydney")

        self.assertEqual(200, response.status_code)
        courses = response.json()
        self.assertTrue(courses)
        self.assertTrue(all("sydney" in course["name"].lower() for course in courses))

    def test_race_results_resource_supports_create_and_filters(self):
        race = Race.objects.first()
        rider = Rider.objects.exclude(raceresult__race=race).first()
        self.assertIsNotNone(rider)
        payload = {
            "race": race.pk,
            "rider": rider.pk,
            "grade": "C",
            "usual_grade": "C",
            "number": 42,
            "place": 1,
            "dnf": False,
        }

        create = self.client.post("/api/v1/race-results/", payload, format="json")
        self.assertEqual(201, create.status_code)

        response = self.client.get(f"/api/v1/race-results/?race={race.pk}")
        self.assertEqual(200, response.status_code)
        results = response.json()
        self.assertTrue(results)
        self.assertTrue(all(result["race_id"] == race.pk for result in results))
        self.assertIn("grade_change", results[0])

    def test_user_roles_resource_supports_create_and_filters(self):
        rider = Rider.objects.first()
        role = ClubRole.objects.create(name="Contract test role")
        payload = {
            "user": rider.user_id,
            "club": rider.club_id,
            "role": role.pk,
        }

        create = self.client.post("/api/v1/user-roles/", payload, format="json")
        self.assertEqual(201, create.status_code)
        user_role_id = create.json()["id"]

        response = self.client.get(f"/api/v1/user-roles/?club={rider.club_id}")
        self.assertEqual(200, response.status_code)
        user_roles = response.json()
        self.assertTrue(any(item["id"] == user_role_id for item in user_roles))
        self.assertTrue(any(item["club_id"] == rider.club_id for item in user_roles))

        self.assertTrue(UserRole.objects.filter(pk=user_role_id).exists())

    def test_schema_is_served(self):
        response = self.client.get("/api/v1/schema/", HTTP_ACCEPT="application/json")

        self.assertEqual(200, response.status_code)
        schema = response.json()
        self.assertIn("openapi", schema)
        self.assertIn("components", schema)
        self.assertIn("/api/v1/clubs/", schema["paths"])
        self.assertIn("/api/v1/racecourses/", schema["paths"])
        self.assertIn("/api/v1/race-results/", schema["paths"])
        self.assertIn("/api/v1/user-roles/", schema["paths"])
        self.assertIn("/api/v1/pointscores/", schema["paths"])
        self.assertIn("/api/v1/auth/token/", schema["paths"])
        self.assertIn("/api/v1/auth/token/refresh/", schema["paths"])
        self.assertIn("/api/v1/auth/logout/", schema["paths"])
        self.assertIn("/api/v1/auth/me/", schema["paths"])
        self.assertIn("/api/v1/auth/register/", schema["paths"])
        self.assertIn("/api/v1/auth/profile/", schema["paths"])
        self.assertIn("/api/v1/auth/password-reset/", schema["paths"])
        self.assertIn("/api/v1/auth/password-reset/confirm/", schema["paths"])
        self.assertNotIn("/api/clubs/", schema["paths"])

        me_security = schema["paths"]["/api/v1/auth/me/"]["get"]["security"]
        self.assertIn("jwtAuth", me_security)
        self.assertIn("tokenAuth", me_security)
        self.assertIn("cookieAuth", me_security)
        self.assertNotIn({}, me_security)

        password_reset_security = schema["paths"]["/api/v1/auth/password-reset/"]["post"].get("security")
        self.assertIsNone(password_reset_security)

        logout_security = schema["paths"]["/api/v1/auth/logout/"]["post"]["security"]
        self.assertIn("jwtAuth", logout_security)
