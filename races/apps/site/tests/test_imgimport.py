from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django_webtest import WebTest
from webtest import Upload
import datetime

from races.apps.site.models import Club, RaceCourse, Race
from races.apps.site.usermodel import Rider, parse_img_members

TESTFILE = "races/apps/site/tests/imgsample.xls"


class IMGTests(TestCase):

    fixtures = ['clubs', 'users', 'riders']

    def test_readfile(self):
        """We can read a file downloaded from IMG
        and return an iterator over the rows"""

        count = 0
        with open(TESTFILE, 'r') as fd:
            for row in parse_img_members(fd):
                count += 1
                self.assertEqual(dict, type(row))
                self.assertIn("First Name", row.keys())
                self.assertIn("Member Number", row.keys())
                if row['First Name'] is 'Anthony':
                    self.assertEqual('DULWICH HILL', row['Suburb'])
                if row['First Name'] is 'Stephen':
                    self.assertEqual('123457', row['Member Number'])

            # expect two rows
            self.assertEqual(3, count)

    def test_find_user(self):
        """Find a user from their email address or licence number"""

        valverde = User.objects.get(pk=2531)

        # find by email
        user = Rider.objects.find_user("valverde@worldtour.com", "")
        self.assertEqual(user, valverde)

        # find by Licence
        user = Rider.objects.find_user("", "ESP19800425")
        self.assertEqual(user, valverde)

        # missing user
        user = Rider.objects.find_user("jeronimo@here.com", "12345")
        self.assertEqual(user, None)


    def test_update_from_spreadsheet(self):
        """Update user data from a spreadsheet from IMG Sports"""

        club = Club.objects.get(slug="MOV")
        valverde = User.objects.get(pk=2531)
        usernodob = User(first_name="No", last_name="DOB", username="NoDOB", email="nodob@example.com")
        usernodob.save()
        usernodob.rider = Rider(user=usernodob, licenceno="1234567")
        usernodob.rider.save()

        with open(TESTFILE, 'r') as fd:
            from imgsampledict import rows
            result = Rider.objects.update_from_spreadsheet(club, rows)

        self.assertEqual(dict, type(result))
        self.assertIn('updated', result)
        self.assertIn('added', result)

        # Valverde should be updated
        self.assertIn(valverde, result['updated'])

        # expect two new riders
        self.assertEqual(2, len(result['added']))

        self.assertIn(usernodob, result['updated'])
        # usernodob's DOB should now be set
        # nee to requery so that we get the updated object
        usernodob = User.objects.get(username="NoDOB")
        self.assertEqual(datetime.date(1975, 6, 7), usernodob.rider.dob)

        # user anotherrider@worldtour.com should be down as a commissaire
        anotherrider = User.objects.get(email='anotherrider@worldtour.com')
        self.assertEqual('1 R,T', anotherrider.rider.commissaire)
        self.assertEqual(datetime.date(datetime.date.today().year+1, 12, 31), anotherrider.rider.commissaire_valid)
        


class IMGWebTests(WebTest):
    """Test the views for uploading IMG spreadsheets"""

    fixtures = ['clubs', 'users', 'riders']

    def test_uplaodfile(self):
        """The club dashboard page has a button
        to upload the IMG spreadsheet, doing so
        adds new riders to the database
        or updates the details of those that are
        already present."""

        self.oge = Club.objects.get(slug='OGE')
        self.mov = Club.objects.get(slug='MOV')

        self.ogeofficial = User(username="ogeofficial", password="hello", first_name="OGE", last_name="Official")
        self.ogeofficial.save()

        valverde = User.objects.get(pk=2531)

        ogerider = Rider(user=self.ogeofficial, gender="M", licenceno="987655", club=self.oge, official=True)
        ogerider.save()

        response = self.app.get(reverse('club_dashboard', kwargs={'slug': 'OGE'}), user=self.ogeofficial)

        # look for the button
        buttons = response.html.find_all('button', attrs={'data-target': "#IMGUploadModal"})
        self.assertEqual(1, len(buttons))
        self.assertIn("Upload IMG Spreadsheet", buttons[0].string)

        form = response.forms['imgssform']
        self.assertNotEqual(None, form)
        self.assertEqual(reverse('club_riders', kwargs={'slug': self.oge.slug}), form.action)
        self.assertEqual("IMG", form['fileformat'].value)


        # fill the form to upload the file
        form['memberfile'] = Upload(TESTFILE)

        response = form.submit()

        # response is a page reporting on the riders added or modified
        # should contain mention of just two riders, one added, one updated
        # ogeofficial should not be mentioned

        self.assertContains(response, valverde.first_name) # updated rider
        self.assertContains(response, 'Stephen')  # added rider
