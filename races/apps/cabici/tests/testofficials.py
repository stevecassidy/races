from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django_webtest import WebTest
from django.core import mail

from races.apps.cabici.models import Club, RaceCourse, Race
from races.apps.cabici.usermodel import Rider, ClubGrade, Membership, ClubRole, UserRole
import datetime
import re
import random

class OfficialsTests(WebTest):
    """Tests related to allocation of club officials """

    fixtures = ['clubs', 'courses', 'users', 'riders', 'races']

    def setUp(self):

        self.oge = Club.objects.get(slug='OGE')
        self.mov = Club.objects.get(slug='MOV')

        self.oge.manage_members = True
        self.oge.manage_races = True

        self.oge.save()

        self.ogeofficial = User(username="ogeofficial", password="hello", first_name="OGE", last_name="Official")
        self.ogeofficial.save()
        self.movofficial = User(username="movofficial", password="hello", first_name="MOV", last_name="Official")
        self.movofficial.save()

        self.ogeofficial.rider = Rider(official=True, club=self.oge)
        self.ogeofficial.rider.save()

        thisyear = datetime.date.today().year

        # make sure all riders are current members
        racers = 0
        riders = 0
        for rider in self.oge.rider_set.all():
            if random.random() > 0.2:
                category = 'race'
                racers += 1
            else:
                category = 'ride'
                riders += 1

            m = Membership(rider=rider, club=rider.club, year=thisyear, category=category)
            m.save()

    def make_races(self):
        """Make some races for testing"""

        # give us some races
        races = []
        when = datetime.date.today()
        where = RaceCourse.objects.all()[0]
        for r in ['one', 'two', 'three']:
            when = when + datetime.timedelta(days=7)
            race = Race(club=self.oge, title=r, date=when, location=where, signontime="06:00", starttime="6 ish")
            race.save()
            races.append(race)
        return races

    def make_role(self, club, n, rolename):
        """Choose n members to have the given role,
         return a list of riders"""

        role, created = ClubRole.objects.get_or_create(name=rolename)

        riders = []
        mm = Membership.objects.filter(club__exact=club, category__exact='race')[:n]
        for m in mm:
            ur = UserRole(user=m.rider.user, club=club, role=role)
            ur.save()
            riders.append(ur.user.rider)

        print role, riders
        return riders

    def test_club_create_officials(self):
        """Test creation of various roles"""

        dofficers = self.make_role(self.oge, 3, "Duty Officer")

        self.oge.create_duty_helpers()
        helpers = self.oge.userrole_set.filter(role__name__exact="Duty Helper")
        racers = self.oge.membership_set.filter(category__exact='race').count()
        self.assertEqual(racers-3, helpers.count())
        # no dofficers should be helpers
        for rider in dofficers:
            ur = self.oge.userrole_set.filter(role__name__exact="Duty Helper", user__rider__exact=rider).count()
            self.assertEqual(0, ur)

    def test_club_allocate_officials(self):
        """Allocate officials to a set of races"""

        races = self.make_races()

        self.oge.create_duty_helpers()

        self.oge.allocate_officials("Duty Helper", 2, races)

        # each race should have two helpers
        helpers1 = []
        for race in races:
            self.assertEqual(2, race.officials.all().count())
            helpers1.extend([off.rider for off in race.officials.all()])

        # do it again,
        self.oge.allocate_officials("Duty Helper", 2, races, replace=True)

        helpers2 = []
        for race in races:
            self.assertEqual(2, race.officials.all().count())
            helpers2.extend([off.rider for off in race.officials.all()])

        self.assertNotEqual(helpers1, helpers2)

        newraces = self.make_races()

        # allocate the first two
        self.oge.allocate_officials("Duty Helper", 2, newraces[:2])

        who1 = list(newraces[0].officials.all())

        # now all of them, the first two should not be reallocated
        self.oge.allocate_officials("Duty Helper", 2, newraces)
        helpers3 = []
        for race in newraces:
            self.assertEqual(2, race.officials.all().count())
            helpers3.extend([off.rider for off in race.officials.all()])

        # alloc of first race should not have changed
        self.assertListEqual(who1, list(newraces[0].officials.all()))

        # no rider should have more than 3 allocations if we're doing it right
        for rider in self.oge.rider_set.filter(user__userrole__role__name__exact='Duty Helper'):
            c = self.oge.races.filter(officials__rider__exact=rider).count()
            self.assertLessEqual(c,3)

    def test_view_club_official_allocate_randomly(self):
        """When I am logged in as a club official, I see a
        button on the club race listing page to allocate
        officials randomly. This links to a modal that
        will achieve this allocation."""

        self.oge.create_duty_helpers()

        races = self.make_races()

        url = reverse('club_races', kwargs={'slug': self.oge.slug})
        response = self.app.get(url, user=self.ogeofficial)

        # there is a button labelled "Randomly Allocate Officials"
        button = response.html.find_all('button', string=re.compile("Randomly Allocate Officials"))

        self.assertEqual(1, len(button))

        # there is a form with id allocateForm
        self.assertTrue('allocateForm' in response.forms)

        form = response.forms['allocateForm']
        # submit it
        response = form.submit()

        # should get a redirect response
        self.assertRedirects(response, '/clubs/OGE/races/')

        # now we have officials allocated to our races
        for race in races:
            off = race.officials.all()
            self.assertEqual(2, len(off))

    def test_club_official_email_members(self):
        """Dashboard has a button to email members, leading to a
        page with a form to send an email"""

        # first test with movistar where we don't manage members
        dashboard_url = reverse('club_dashboard', kwargs={'slug': self.mov.slug})
        emailurl = reverse('club_email', kwargs={'slug': self.oge.slug})

        response = self.app.get(dashboard_url, user=self.ogeofficial)

        # there is no link with the email URL
        link = response.html.find_all('a', href=emailurl)

        self.assertEqual(0, len(link))

        # now with  membership management for OGE
        dashboard_url = reverse('club_dashboard', kwargs={'slug': self.oge.slug})
        emailurl = reverse('club_email', kwargs={'slug': self.oge.slug})

        # now the link is there
        response = self.app.get(dashboard_url, user=self.ogeofficial)
        link = response.html.find_all('a', href=emailurl)
        self.assertEqual(1, len(link))

        # follow the link
        response = self.app.get(emailurl, user=self.ogeofficial)
        # check for the form
        self.assertTrue('emailmembersform' in response.forms)
        form = response.forms['emailmembersform']
        self.assertEqual('POST', form.method)

        # fill the form and submit
        subject = "test email subject"
        body = "xyzzy1234 message body"
        form['sendto'] = 'members'
        form['subject'] = subject
        form['message'] = body
        response = form.submit()

        self.assertRedirects(response, dashboard_url)

        # check that emails are 'sent'

        members = self.oge.rider_set.all()

        self.assertEqual(len(mail.outbox), 1)

        # to should be empty, member emails are in bcc
        self.assertEqual(len(mail.outbox[0].to), 0)

        recipients = mail.outbox[0].bcc
        self.assertEqual(len(mail.outbox[0].bcc), members.count())
        for m in members:
            self.assertIn(m.user.email, recipients)

        self.assertEqual(mail.outbox[0].subject, subject)
        self.assertEqual(mail.outbox[0].body, body)

    def test_club_official_email_members_self(self):
        """Member email form can send mail to myself"""

        emailurl = reverse('club_email', kwargs={'slug': self.oge.slug})
        response = self.app.get(emailurl, user=self.ogeofficial)
        form = response.forms['emailmembersform']

        # fill the form and submit
        subject = "test email subject"
        body = "xyzzy1234 message body"
        form['sendto'] = 'self'
        form['subject'] = subject
        form['message'] = body
        response = form.submit()

        # check that emails are 'sent'
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].to), 0)
        self.assertEqual(mail.outbox[0].bcc, [self.ogeofficial.email])

    def test_club_official_email_members_reject_attack(self):
        """I can't inject headers into an email message"""

        emailurl = reverse('club_email', kwargs={'slug': self.oge.slug})
        response = self.app.get(emailurl, user=self.ogeofficial)
        form = response.forms['emailmembersform']

        # fill in the form, try to inject a To header via the subject
        subject = "test email subject\nTo: somebody@evil.org"
        body = "xyzzy1234 message body"
        form['sendto'] = 'self'
        form['subject'] = subject
        form['message'] = body
        response = form.submit(expect_errors=True)

        self.assertEqual('400 Bad Request', response.status)
        # check that no emails are 'sent'
        self.assertEqual(len(mail.outbox), 0)
