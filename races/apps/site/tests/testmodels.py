from django.test import TestCase
from django.core.urlresolvers import reverse

from races.apps.site.models import Club, RaceCourse, Race
from datetime import datetime, timedelta

class ModelTests(TestCase):


	def test_club(self):
		"""Test creation of clubs and some methods"""

		name = "test club"
		website = "http://example.com/"
		slug = "TEST"
		club = Club(name=name, website=website, slug=slug)

		# string version of club is the slug
		self.assertEqual(unicode(club), slug)


		# test failure modes of ingest
		# this triggers ingest_by_module which fails because there is no module
		self.assertEqual(club.ingest(), ([], 'No ingest module for club "test"'))


	def test_race(self):
		"""Test creation of race and some methods"""

		clubname = "test club"
		website = "http://example.com/"
		slug = "TEST"
		club = Club(name=clubname, website=website, slug=slug)
		club.save()

		loc = RaceCourse(name="Test Course")
		loc.save()

		title = "Race Title"
		date = datetime.today()



		race = Race(title=title, date=date, time=date, club=club, location=loc)
		race.save()

		self.assertTrue(unicode(race).startswith(slug))
		self.assertTrue(unicode(race).find(title) >= 0)

		self.assertEqual(race.get_absolute_url(), "/races/TEST/1")
