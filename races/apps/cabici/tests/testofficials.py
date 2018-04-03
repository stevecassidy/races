from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django_webtest import WebTest
from django.core import mail

from races.apps.cabici.models import Club, RaceCourse, Race
from races.apps.cabici.usermodel import Rider, RaceStaff, Membership, ClubRole, UserRole, RaceResult
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

        self.ogeofficial = User(username="ogeofficial", email='oge@here.com', password="hello", first_name="OGE", last_name="Official")
        self.ogeofficial.save()
        self.movofficial = User(username="movofficial", email='mov@here.com', password="hello", first_name="MOV", last_name="Official")
        self.movofficial.save()

        self.ogeofficial.rider = Rider(official=True, club=self.oge)
        self.ogeofficial.rider.save()

        endofyear = datetime.date(day=31, month=12, year=datetime.date.today().year)

        # make sure all riders are current members
        self.racers = []
        self.riders = []
        for rider in self.oge.rider_set.all():
            if random.random() > 0.2:
                category = 'race'
                self.racers.append(rider)
            else:
                category = 'ride'
                self.riders.append(rider)

            m = Membership(rider=rider, club=rider.club, date=endofyear, category=category)
            m.save()

    def make_races(self, past=False):
        """Make some races for testing
        if past=True make races in the past 6 months"""

        # give us some races
        races = []
        if past:
            when = datetime.date.today() - datetime.timedelta(days=150)
        else:
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

    def test_club_get_officials_ordered(self):
        """Test creation of a list of riders to be allocated
        to a role"""

        races = self.make_races()

        self.oge.create_duty_helpers()
        dutyhelper, created = ClubRole.objects.get_or_create(name="Duty Helper")

        dhs = self.oge.rider_set.filter(user__userrole__role__exact=dutyhelper)

        # allocate a few to races
        for race in races[:3]:
            rs = RaceStaff(rider=dhs[0], race=race, role=dutyhelper)
            rs.save()
            rs = RaceStaff(rider=dhs[1], race=race, role=dutyhelper)
            rs.save()

        counted_helpers = self.oge.get_officials_with_counts('Duty Helper')

        self.assertEqual(len(dhs), len(counted_helpers))
        # all should be zero except for dhs[0] and dhs[1]
        for rc in counted_helpers:

            if rc[1] in [dhs[0], dhs[1]]:
                self.assertEqual(3, rc[0])
            else:
                self.assertEqual(0, rc[0])
        # and it should be ordered
        self.assertListEqual(counted_helpers, sorted(counted_helpers))


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

    def test_club_allocate_officials_avoid_duplicates(self):
        """Allocate officials to a race but ensure that we can't
        allocate the same person twice"""

        races = self.make_races()

        race = races[0]

        # get the race page
        url = reverse('race', kwargs={'slug': self.oge.slug, 'pk': race.id})
        response = self.app.get(url, user=self.ogeofficial)

        form = response.forms['accountLogOutForm']
        csrftoken = str(form['csrfmiddlewaretoken'].value)
        headers = {'X-CSRFToken': csrftoken}

        url = reverse('race_officials', kwargs={'pk': race.id})

        # try to add the same person as commissaire twice
        data = {
            'commissaire': [{'id': self.ogeofficial.rider.id, 'name': str(self.ogeofficial)},
                            {'id': self.ogeofficial.rider.id, 'name': str(self.ogeofficial)}],
            'dutyhelper': [],
            'dutyofficer': [{'id': self.ogeofficial.rider.id, 'name': str(self.ogeofficial)}]
        }

        response = self.app.post_json(url, params=data, user=self.ogeofficial, headers = headers)

        respinfo = response.json

        self.assertEqual(respinfo['dutyhelper'], [])
        # should be just one commissaire
        self.assertEqual(1, len(respinfo['commissaire']))

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

        self.assertEqual(len(mail.outbox), 13)

        # to should be empty, member emails are in bcc
        self.assertEqual(len(mail.outbox[0].to), 1)

        recipients = [x.to[0] for x in mail.outbox]
        self.assertEqual(len(recipients), members.count())
        for m in members:
            self.assertIn(m.user.email, recipients)

        self.assertEqual(mail.outbox[0].subject, subject)
        self.assertIn(body, mail.outbox[0].body)
        self.assertIn("you are a member of %s" % (self.oge.name,), mail.outbox[0].body)

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
        self.assertEqual(len(mail.outbox[0].to), 1)
        self.assertIn(body, mail.outbox[0].body)
        self.assertIn("you are sending a test email for %s" % (self.oge.name,), mail.outbox[0].body, )

    def test_club_official_email_pastriders(self):
        """Member email form can send mail to all past riders"""

        emailurl = reverse('club_email', kwargs={'slug': self.oge.slug})
        response = self.app.get(emailurl, user=self.ogeofficial)
        form = response.forms['emailmembersform']

        # need some riders to have raced with OGE recently
        riders = Rider.objects.all()[:10]
        races = self.make_races(past=True)
        for race in races:
            for rider in riders:
                result = RaceResult(race=race, rider=rider, grade='A')
                result.save()

        # fill the form and submit
        subject = "test email subject"
        body = "xyzzy1234 message body"
        form['sendto'] = 'pastriders'
        form['subject'] = subject
        form['message'] = body
        response = form.submit()

        # check that emails are sent
        self.assertEqual(len(mail.outbox), len(riders))

        recipients = [x.to[0] for x in mail.outbox]
        self.assertEqual(len(recipients), riders.count())
        for m in riders:
            self.assertIn(m.user.email, recipients)

        self.assertEqual(mail.outbox[0].subject, subject)
        self.assertIn(body, mail.outbox[0].body)
        self.assertIn("you have raced with %s in the past year." % (self.oge.name,), mail.outbox[0].body, )

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

    def test_club_riders_excel(self):
        """The excel view downloads a complete list of riders
        as an excel spreadsheet"""

        response = self.client.get(reverse('club_riders_excel', kwargs={'slug': self.oge.slug}))

        self.assertEqual(response['Content-Type'], 'application/octet-stream')

        import pyexcel
        from StringIO import StringIO

        # should be able to read the response as an xls sheet
        buf = StringIO(response.content)
        ws = pyexcel.get_sheet(file_content=buf, file_type="xls")
        ws.name_columns_by_row(0)

        # the spreadsheet contains all rider licence numbers
        riderlicences = sorted(ws.column["LicenceNo"])

        riders = Rider.objects.all()
        targetlicences = sorted([r.licenceno for r in riders])

        self.assertEqual(len(targetlicences), len(riderlicences))

        self.assertListEqual(targetlicences, riderlicences)

        # event number can be parsed as an integer
        # and every row has an id that matches a rider
        for row in ws.rows():
            if row[12] != 'EventNo':
                # just force coercion to int, will raise an exception if it's bad
                self.assertEqual(row[12], str(int(row[12])))
                id = row[11]
                rider = Rider.objects.get(id=id)
                self.assertEqual(rider.licenceno, row[8])

        buf.close()
