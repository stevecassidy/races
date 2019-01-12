from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django_webtest import WebTest
from webtest import Upload
import datetime
import csv
import tempfile
import random

from races.apps.cabici.models import Club, RaceCourse, Race
from races.apps.cabici.usermodel import Rider, parse_img_members

TESTFILE = "races/apps/cabici/tests/imgsample.xls"


def write_imgsample(outfile, rows):
    """Write out a sample IMG import file from a row dictionary"""

    with open(outfile, 'w') as fd:

        fd.write('\n<table border="1">\n')
        # header row
        keys = list(rows[0].keys())
        fd.write('\n<tr valign="top">\n')
        for key in keys:
            fd.write('\t<td valign="top">%s</td>\n' % key)
        fd.write('</tr>\n\n')

        for row in rows:
            fd.write('\n<tr valign="top">\n')
            for key in keys:
                if isinstance(row[key], datetime.date):
                    value = row[key].strftime('%d-%b-%Y')
                elif row[key] is None:
                    value = ''
                else:
                    value = row[key]

                fd.write('\t<td valign="top">%s</td> <!-- %s -->\n' % (value, key))
            fd.write('</tr>\n\n')

        fd.write('</table>\n')


def write_tidyhq_sample(outfile, rows):
    """Write out a sample TidyHQ csv file for testing"""

    mmap = {
        'RACING Membership': 'Race - Masters U65 - Annual',
        'RIDE Membership': 'Ride - Adult (19-64) - Annual',
        'NON-RIDING Membership': 'Non Riding Member - Annual'
    }

    with open(outfile, 'w') as fd:

        writer = csv.DictWriter(fd, ['Contact', 'Id', 'Email', 'Phone ', 'Membership Level', 'Membership Status', 'Subscription End Date', 'Gender ', 'Birthday '])
        writer.writeheader()

        for row in rows:

            if row['Status'] == 'Active':
                status = 'Activated'
            else:
                status = 'Expired'

            memberdate = row['Financial Date'].strftime('%d %b %Y')

            trow = {
                'Contact': row['First Name'] + " " + row['Last Name'],
                'Id': "CA"+row['Member Number'],
                'Email': row['Email Address'],
                'Phone ': row['Mobile'],
                'Membership Level': mmap[row['Member Types']],
                'Membership Status': status,
                'Subscription End Date': memberdate,
                'Gender ': row['Gender'],
                'Birthday ': row['DOB'].strftime('%Y-%m-%d'),
            }
            writer.writerow(trow)


class IMGTests(TestCase):

    fixtures = ['clubs', 'users', 'riders']

    def test_readfile(self):
        """We can read a file downloaded from IMG
        and return an iterator over the rows"""

        from .imgsampledict import rows
        write_imgsample(TESTFILE, rows)

        count = 0
        with open(TESTFILE, 'r') as fd:
            for row in parse_img_members(fd):
                count += 1
                self.assertEqual(dict, type(row))
                self.assertIn("First Name", list(row.keys()))
                self.assertIn("Member Number", list(row.keys()))
                if row['First Name'] is 'Anthony':
                    self.assertEqual('DULWICH HILL', row['Suburb'])
                if row['First Name'] is 'Stephen':
                    self.assertEqual('123457', row['Member Number'])

            # expect two rows
            self.assertEqual(6, count)

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
        cyclingnsw, created = Club.objects.get_or_create(name="CyclingNSW", slug="CNSW")

        valverde = User.objects.get(pk=2531)

        usernodob = User(first_name="No", last_name="DOB", username="NoDOB", email="nodob@example.com")
        usernodob.save()
        usernodob.rider = Rider(user=usernodob, licenceno="1234567")
        usernodob.rider.save()

        # use pre-parsed rows
        from .imgsampledict import rows
        result = Rider.objects.update_from_img_spreadsheet(club, rows)

        self.assertEqual(dict, type(result))
        self.assertIn('updated', result)
        self.assertIn('added', result)

        updated_users = [u['user'] for u in result['updated']]

        # Valverde should be updated
        self.assertIn(valverde, updated_users)

        # expect two new riders
        self.assertEqual(2, len(result['added']))

        self.assertIn(usernodob, updated_users)
        # usernodob's DOB should now be set
        # need to requery so that we get the updated object
        usernodob = User.objects.get(username="NoDOB")
        self.assertEqual(datetime.date(1975, 6, 7), usernodob.rider.dob)

        # user anotherrider@worldtour.com should be down as a commissaire
        anotherrider = User.objects.get(email='anotherrider@worldtour.com')
        self.assertEqual('1 R,T', anotherrider.rider.commissaire)
        self.assertEqual(datetime.date(datetime.date.today().year+1, 12, 31), anotherrider.rider.commissaire_valid)

        # membership should be updated
        mems = anotherrider.rider.membership_set.filter(date__gte=datetime.date.today())
        self.assertEqual(1, len(mems))

        # grading is updated
        grade = valverde.rider.clubgrade_set.get(club=cyclingnsw)
        self.assertEqual("A1", grade.grade)


class TidyHQTests(TestCase):

    fixtures = ['clubs', 'users', 'riders']

    def test_update_from_spreadsheet(self):
        """Update user data from a spreadsheet from IMG Sports"""

        club = Club.objects.get(slug="MOV")
        cyclingnsw, created = Club.objects.get_or_create(name="CyclingNSW", slug="CNSW")

        valverde = User.objects.get(pk=2531)

        usernodob = User(first_name="No", last_name="DOB", username="NoDOB", email="nodob@example.com")
        usernodob.save()
        usernodob.rider = Rider(user=usernodob, licenceno="1234567")
        usernodob.rider.save()

        from .imgsampledict import rows
        with tempfile.NamedTemporaryFile() as temp:
            csvfile = temp.name
            write_tidyhq_sample(csvfile, rows)
            with open(csvfile) as fd:
                result = Rider.objects.update_from_tidyhq_spreadsheet(club, fd)

            self.assertEqual(dict, type(result))
            self.assertIn('updated', result)
            self.assertIn('added', result)

            updated_users = [u['user'] for u in result['updated']]

            # Valverde should be updated
            self.assertIn(valverde, updated_users)

            # expect two new riders
            self.assertEqual(2, len(result['added']))

            # re-fetch this user to check db updates
            usernodob = User.objects.get(last_name="DOB")
            self.assertIn(usernodob, updated_users)
            self.assertEqual('F', usernodob.rider.gender)
            self.assertEqual('0415 999999', usernodob.rider.phone)


class IMGWebTests(WebTest):
    """Test the views for uploading IMG spreadsheets"""

    fixtures = ['clubs', 'users', 'riders']

    def test_upload_img_file(self):
        """The club dashboard page has a button
        to upload the IMG spreadsheet, doing so
        adds new riders to the database
        or updates the details of those that are
        already present."""

        self.oge = Club.objects.get(slug='OGE')
        self.mov = Club.objects.get(slug='MOV')
        self.oge.manage_members = True
        self.oge.save()

        self.ogeofficial = User(username="ogeofficial", password="hello", first_name="OGE", last_name="Official")
        self.ogeofficial.save()

        valverde = User.objects.get(pk=2531)

        ogerider = Rider(user=self.ogeofficial, gender="M", licenceno="987655", club=self.oge, official=True)
        ogerider.save()

        response = self.app.get(reverse('club_dashboard', kwargs={'slug': 'OGE'}), user=self.ogeofficial)

        # look for the button
        buttons = response.html.find_all('a', attrs={'data-target': "#IMGUploadModal"})
        self.assertEqual(1, len(buttons))
        self.assertIn("TidyHQ Upload", str(buttons[0]))

        form = response.forms['imgssform']
        form['fileformat'] = 'IMG'
        self.assertNotEqual(None, form)
        self.assertEqual(reverse('club_riders', kwargs={'slug': self.oge.slug}), form.action)

        from .imgsampledict import rows
        write_imgsample(TESTFILE, rows)

        # fill the form to upload the file
        form['memberfile'] = Upload(TESTFILE)

        response = form.submit()

        # response is a page reporting on the riders added or modified
        # should contain mention of just two riders, one added, one updated
        # ogeofficial should not be mentioned

        self.assertContains(response, valverde.first_name) # updated rider
        self.assertContains(response, 'Stephen')  # added rider

    def test_upload_tidyhq_file(self):
        """The club dashboard page has a button
        to upload the TidyHQ spreadsheet, doing so
        adds new riders to the database
        or updates the details of those that are
        already present."""

        self.oge = Club.objects.get(slug='OGE')
        self.mov = Club.objects.get(slug='MOV')
        self.oge.manage_members = True
        self.oge.save()

        self.ogeofficial = User(username="ogeofficial", password="hello", first_name="OGE", last_name="Official")
        self.ogeofficial.save()

        valverde = User.objects.get(pk=2531)

        ogerider = Rider(user=self.ogeofficial, gender="M", licenceno="987655", club=self.oge, official=True)
        ogerider.save()

        response = self.app.get(reverse('club_dashboard', kwargs={'slug': 'OGE'}), user=self.ogeofficial)

        # look for the button
        buttons = response.html.find_all('a', attrs={'data-target': "#IMGUploadModal"})
        self.assertEqual(1, len(buttons))
        self.assertIn("TidyHQ Upload", str(buttons[0]))

        form = response.forms['imgssform']
        form['fileformat'] = 'THQ'
        self.assertNotEqual(None, form)
        self.assertEqual(reverse('club_riders', kwargs={'slug': self.oge.slug}), form.action)

        from .imgsampledict import rows
        write_tidyhq_sample(TESTFILE, rows)

        # fill the form to upload the file
        form['memberfile'] = Upload(TESTFILE)

        response = form.submit()

        # response is a page reporting on the riders added or modified
        # should contain mention of just two riders, one added, one updated
        # ogeofficial should not be mentioned

        self.assertContains(response, valverde.first_name) # updated rider
        self.assertContains(response, 'Stephen')  # added rider
