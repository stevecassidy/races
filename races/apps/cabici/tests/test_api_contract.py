#!/usr/bin/python

from rest_framework.test import APITestCase

from races.apps.cabici.models import Club, PointScore


class V1ContractTests(APITestCase):
    fixtures = ["clubs", "courses", "races", "users", "riders", "clubroles"]

    def test_v1_root_returns_expected_resources(self):
        response = self.client.get("/api/v1/")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertIn("clubs", payload)
        self.assertIn("riders", payload)
        self.assertIn("races", payload)
        self.assertIn("pointscores", payload)
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

    def test_schema_is_served(self):
        response = self.client.get("/api/v1/schema/", HTTP_ACCEPT="application/json")

        self.assertEqual(200, response.status_code)
        schema = response.json()
        self.assertIn("openapi", schema)
        self.assertIn("components", schema)
        self.assertIn("/clubs/", schema["paths"])
        self.assertIn("/pointscores/", schema["paths"])
        self.assertNotIn("/api/clubs/", schema["paths"])
