from django.test import TestCase
from django.core.urlresolvers import reverse

from races.apps.cabici.models import Club, RaceCourse, Race
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

		race = Race(title=title, date=date, signontime="08:00", club=club, location=loc)
		race.save()

		self.assertTrue(unicode(race).startswith(slug))
		self.assertTrue(unicode(race).find(title) >= 0)

		self.assertEqual(race.get_absolute_url(), "/races/TEST/1")


import random, datetime

class ClubTests(TestCase):

	fixtures = ['users', 'clubs', 'races', 'riders']

	def test_club_create_officials(self):
		"""Test creation of various roles"""

		club = Club.objects.get(slug="BMC")

		thisyear = datetime.date.today().year

		# make sure all riders are current members
		racers = 0
		riders = 0
		for rider in club.rider_set.all():
			if random.random() > 0.8:
				category = 'race'
				racers += 1
			else:
				category = 'ride'
				riders += 1

			m = Membership(rider=rider, club=club, year=thisyear, category=category)
			m.save()

		club.create_duty_helpers()
		helpers = club.clubrole_set.filter(role="Duty Helper")
		self.assertEqual(riders, helpers.count())
