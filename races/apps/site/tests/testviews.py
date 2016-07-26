from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
import os

from races.apps.site.models import Club, RaceCourse, Race
from races.apps.site.usermodel import PointScore, Rider
from datetime import datetime, timedelta, date



class ViewTests(TestCase):

    fixtures = ['clubs', 'courses', 'users', 'riders']

    def setUp(self):

        today = datetime.today()
        yesterday = today - timedelta(1)
        tomorrow = today + timedelta(1)
        nextweek = today + timedelta(7)
        nextfortnight = today + timedelta(14)
        nextthreeweeks = today + timedelta(21)


        self.oge = Club.objects.get(slug='OGE')
        self.bmc = Club.objects.get(slug='BMC')

        self.lansdowne = RaceCourse.objects.get(name='Lansdowne Park')
        self.sop = RaceCourse.objects.get(name='Tennis Centre, SOP')

        r = []
        r.append(Race(title='Yesterday 1 W', date=yesterday, club=self.oge, signontime="7:00", status='p', website=self.oge.website, location=self.lansdowne))
        r.append(Race(title='Today 2 W', date=today, club=self.oge, signontime="7:00", status='p', website=self.oge.website, location=self.lansdowne))
        r.append(Race(title='Tomorrow 3 W', date=tomorrow, club=self.oge, signontime="7:00", status='p', website=self.oge.website, location=self.lansdowne))
        r.append(Race(title='Next Week 4 W', date=nextweek, club=self.oge, signontime="7:00", status='p', website=self.oge.website, location=self.lansdowne))
        r.append(Race(title='Fortnight 5 W', date=nextfortnight, club=self.oge, signontime="7:00", status='p', website=self.oge.website, location=self.lansdowne))
        r.append(Race(title='Three Weeks 6 W', date=nextthreeweeks, club=self.oge, signontime="7:00", status='p', website=self.oge.website, location=self.lansdowne))
        r.append(Race(title='Not Published', date=tomorrow, club=self.oge, signontime="7:00", status='d', website=self.oge.website, location=self.lansdowne))


        r.append(Race(title='Yesterday 1 L', date=yesterday, club=self.bmc, signontime="8:00", status='p', website=self.bmc.website, location=self.sop))
        r.append(Race(title='Today 2 L', date=today, club=self.bmc, signontime="8:00", status='p', website=self.bmc.website, location=self.sop))
        r.append(Race(title='Tomorrow 3 L', date=tomorrow, club=self.bmc, signontime="8:00", status='p', website=self.bmc.website, location=self.sop))
        r.append(Race(title='Next Week 4 L', date=nextweek, club=self.bmc, signontime="8:00", status='p', website=self.bmc.website, location=self.sop))
        r.append(Race(title='Fortnight 5 L', date=nextfortnight, club=self.bmc, signontime="8:00", status='p', website=self.bmc.website, location=self.sop))
        r.append(Race(title='Three Weeks 6 L', date=nextthreeweeks, club=self.bmc, signontime="8:00", status='p',  website=self.bmc.website, location=self.sop))


        for race in r:
            race.save()

    def test_home_page(self):
        """The home page returns a 200 response"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        #self.assertContains(response, "About cabici", 1, 200)

    def test_home_page_race_list(self):
        """Test that the home page lists the next two
        weeks of races, starting from today"""


        response = self.client.get(reverse('home'))
        self.assertNotContains(response, "Yesterday 1 W")
        self.assertContains(response, "Today 2 W")
        self.assertContains(response, "Tomorrow 3 W")
        self.assertContains(response, "Next Week 4 W")
        self.assertNotContains(response, "Fortnight 5 W")
        self.assertNotContains(response, "Three Weeks 6 W")

        # draft races shouldn't appear
        self.assertNotContains(response, "Not Published")


    def test_race_list_page(self):
        """Test that the race list page has all future
        races including today"""

        response = self.client.get(reverse('races'))

        self.assertNotContains(response, "Yesterday 1 W")
        self.assertContains(response, "Today 2 W")
        self.assertContains(response, "Today 2 L")
        self.assertContains(response, "Tomorrow 3 W")
        self.assertContains(response, "Next Week 4 W")
        self.assertContains(response, "Fortnight 5 W")
        self.assertContains(response, "Three Weeks 6 W")
        self.assertContains(response, "Three Weeks 6 L")


    def test_race_list_page_month(self):
        """Test that the race list page for a given month works"""

        today = datetime.today()
        url = today.strftime('/races/%Y/%m/')
        response = self.client.get(url)

        # just check for today - should check more TODO
        self.assertContains(response, "Today 2 W")
        self.assertContains(response, "Today 2 L")


    def test_club_page(self):
        """Test that the club page has all future
        races for the club including today"""

        response = self.client.get(reverse('club', kwargs={'slug': self.oge.slug}))

        self.assertNotContains(response, "Yesterday 1 W")
        self.assertContains(response, "Today 2 W")
        self.assertContains(response, "Tomorrow 3 W")
        self.assertContains(response, "Next Week 4 W")
        self.assertContains(response, "Fortnight 5 W")
        self.assertContains(response, "Three Weeks 6 W")
        self.assertNotContains(response, "Today 2 L")


    def test_club_riders(self):
        """The club riders page lists the riders for
        this club"""

        response = self.client.get(reverse('club_riders', kwargs={'slug': self.oge.slug}))

        # should contain all rider names
        for rider in Rider.objects.filter(club__exact=self.oge):
            self.assertContains(response, rider.user.first_name + " " + rider.user.last_name)

        # but not riders from any other club
        for rider in Rider.objects.exclude(club__exact=self.oge):
            self.assertNotContains(response, rider.user.first_name + " " + rider.user.last_name)


    def test_club_riders_excel(self):
        """The excel view downloads a complete list of riders
        as an excel spreadsheet"""

        response = self.client.get(reverse('club_riders_excel', kwargs={'slug': self.oge.slug}), {'eventno': 666})

        self.assertEqual(response['Content-Type'], 'application/vnd-ms.excel')

        import pyexcel
        from StringIO import StringIO

        # should be able to read the response as an xls sheet
        buf = StringIO(response.content)
        ws = pyexcel.get_sheet(file_content=buf, file_type="xls")
        ws.name_columns_by_row(0)

        # the spreadsheet contains all rider licence numbers
        riderlicences = ws.column["LicenceNo"]
        for rider in Rider.objects.all():
            self.assertIn(rider.licenceno, riderlicences)
        # event number is present in every row (except the header)
        for row in ws.rows():
            if row[12] != 'EventNo':
                self.assertEqual('666', row[12])

        buf.close()

    def test_upload_excel_results(self):
        """Test that we can upload an Excel spreasheet of results"""

        date = datetime.today()
        loc = RaceCourse.objects.all()[0]

        race = Race(title="Test", date=date, signontime="08:00", club=self.oge, location=loc)
        race.save()

        url = reverse('race_results_excel',  kwargs={'slug': self.oge.slug, 'pk': race.id})

        with open(os.path.join(os.path.dirname(__file__), 'Waratahresults201536.xls'), 'rb') as fd:
            response = self.client.post(url, {'excelfile': fd})

        self.assertRedirects(response, reverse('race', kwargs={'slug': self.oge.slug, 'pk': race.id}))

        # there should be some results for this race
        self.assertEqual(len(race.raceresult_set.all()), 116)
