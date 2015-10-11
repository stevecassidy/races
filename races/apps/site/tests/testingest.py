from django.test import TestCase
from django.core.urlresolvers import reverse
import vcr

from races.apps.site.models import Club, RaceCourse, Race
from races.ingest import lacc
from datetime import datetime, timedelta


class IngestTests(TestCase):

    fixtures = ['clubs', 'courses']

    def test_ical_ingest(self):
        """Ingest from an ical file"""

        cccc = Club(slug='CCCC', name="Central Coast Cycling Club")
        # modify the ical url to our local copy
        cccc.icalurl = "file:races/apps/site/tests/cccc.ical"

        (races, error) = cccc.ingest_ical()

        self.assertEqual(len(races), 3)

        races_stored = Race.objects.filter(club=cccc)
        self.assertEqual(len(races_stored), 3)

        # ingest from a second file should just add one race
        cccc.icalurl = "file:races/apps/site/tests/cccc2.ical"

        (races, error) = cccc.ingest_ical()

        self.assertEqual(len(races), 1)

        races_stored = Race.objects.filter(club=cccc)
        self.assertEqual(len(races_stored), 4)

    @vcr.use_cassette('fixtures/vcr_cassettes/manly.yaml')
    def test_ical_ingest_manly(self):
        """Ingest from an ical file - this time manly"""

        # we'll use CCCC again but point to the manly ics file this time
        cccc = Club(slug='CCCC', name="Central Coast Cycling Club")
        cccc.icalurl = "https://www.google.com/calendar/ical/account%40manlywarringahcc.org.au/public/basic.ics"
        cccc.icalpatterns = "Race"
        cccc.save()

        (races, error) = cccc.ingest_ical()

        self.assertEqual(len(races), 48)

        races_stored = Race.objects.filter(club=cccc)
        self.assertEqual(len(races_stored), 48)
        cccc.delete()


    @vcr.use_cassette('fixtures/vcr_cassettes/nscc.yaml')
    def test_event_timezone(self):

        # we'll use CCCC again but point to the manly ics file this time
        cccc = Club(slug='NSCC', name="North Sydney Cycling Club")
        cccc.icalurl = "http://northernsydneycyclingclub.org.au/calendar/ical"
        cccc.icalpatterns = "Worlds"
        cccc.save()


        (races, error) = cccc.ingest_ical()

        self.assertEqual(7, len(races))

        self.assertEqual("Beauie Worlds Crit", races[0].title)
        # check date, should be converted to our timezone
        self.assertEqual("2015-04-19", races[0].date)
        self.assertEqual("08:15:00", races[0].time)

        cccc.delete()



    @vcr.use_cassette('fixtures/vcr_cassettes/nonical.yaml')
    def test_ical_ingest_for_non_ical_club(self):

        wmcc = Club(slug='WMCC', name="Waratah Masters Cycling Club")

        (races, error) = wmcc.ingest_ical()

        self.assertEqual(races, [])
        self.assertEqual(error, "No icalendar URL")

        wmcc.icalurl = "http://google.com/"

        (races, error) = wmcc.ingest_ical()

        self.assertEqual(races, [])
        self.assertEqual(error, "Error reading icalendar file")


    @vcr.use_cassette('fixtures/vcr_cassettes/badurl.yaml')
    def test_ical_ingest_bad_url(self):

        wmcc = Club(slug='WMCC', name="Waratah Masters Cycling Club")
        wmcc.icalurl = "http://google.com/"

        (races, error) = wmcc.ingest_ical()

        self.assertEqual(races, [])


    def test_ingest_race_list(self):
        """Test ingesting a list of races from a list of dictionaries"""

        racedicts = [
                  {'date': '2013-09-29',
                  'hash': '7823305046c8a4a5fd1a71405b9fe36ec7bbe2e5',
                  'location': 'Lansdowne Park',
                  'time': u'07:45',
                  'title': 'Criterium Race Grades C-F',
                  'url': 'http://www.waratahmasters.com.au/eventsmenu.cfm'},

                 {'date': '2013-09-29',
                  'hash': '5aa36abebcf11c45679e3f800a7a9f19a147f100',
                  'location': 'Lansdowne Park',
                  'time': u'09:00',
                  'title': 'Criterium Race Grades A-B',
                  'url': 'http://www.waratahmasters.com.au/eventsmenu.cfm'},

                 {'date': '2013-10-06',
                  'hash': 'c0fb7620efe9e21273293ad9dbdf2a2be5758bd0',
                  'location': 'Sydney Dragway Full',
                  'time': u'08:00',
                  'title': 'This title is really long and will be truncated because we only allow titles up to one hundred characters and this is a bit longer than that in fact it is quite a bit longer',
                  'url': 'http://www.waratahmasters.com.au/eventsmenu.cfm'},

                 {'date': '2013-10-07',
                  'hash': '450cf08fc916bfe323825a6370836fb2da2feb36',
                  'location': 'SMSP Full GP Circuit, Eastern Creek (MONDAY)',
                  'time': u'07:00',
                  'title': 'Ashfield Cycles / Specialized Cup - Graded Scratch',
                  'url': 'http://www.waratahmasters.com.au/eventsmenu.cfm'}
                 ]

        wmcc = Club(slug='WMCC', name="Waratah Masters Cycling Club")
        wmcc.save()

        # ingest the first three
        (races, errors) = wmcc.ingest_race_list(racedicts[:3])

        self.assertEqual(len(races), 3)
        self.assertEqual(errors, [])

        for i in range(len(racedicts)-1):
            self.assertEqual(races[i].title, racedicts[i]['title'])

        # check location
        loc = races[0].location
        self.assertEqual(loc.name, "Lansdowne Park")

        # now do the whole list, check we don't get duplicates
        (races, errors)  = wmcc.ingest_race_list(racedicts)

        self.assertEqual(len(races), 1)
        self.assertEqual(errors, [])

        loc = races[0].location
        self.assertEqual(loc.name, u'SMSP Full GP Circuit, Eastern Creek')

        # try one with a malformed time
        badrace = racedicts[0]
        badrace['time'] = "8 o'clock in the morning"
        badrace['hash'] = 'newhash'

        (races, errors) = wmcc.ingest_race_list([badrace])

        self.assertEqual(races, [])
        self.assertEqual(len(errors), 1)

        self.assertEqual(errors[0],
                         '[u\"\'8 o\'clock in the morning\' value has an invalid format. It must be in HH:MM[:ss[.uuuuuu]] format.\"]')

        #wmcc.delete()



    @vcr.use_cassette('fixtures/vcr_cassettes/module_waratahs.yaml')
    def test_ingest_by_module_waratahs(self):
        """ingest_by_module should be able to find a module
        for some clubs and call the ingest procedure in it
        this test for the WMCC club"""


        wmcc = Club(slug='WMCC', name="Waratah Masters Cycling Club")

        (races, errors) = wmcc.ingest_by_module()

        # now this is accessing the real website so we don't know
        # exactly what results we'll get
        # so we'll just assert that we get some races back

        self.assertGreater(len(races), 0, "No races returned by Waratahs ingest module")

        # and that the club is WMCC
        self.assertEqual(races[0].club, wmcc, "Wrong club in race returned by ingest_by_module")

        # try one that won't work
        wmcc = Club(slug='CCCC', name="Central Coast Cycling Club")

        (races, errors) = cccc.ingest_by_module()

        self.assertEqual(races, [])


    @vcr.use_cassette('fixtures/vcr_cassettes/lacc.yaml')
    def test_lacc(self):

        races = lacc.ingest()

        self.assertEqual(33, len(races))

        self.assertEqual("Seniors Track Training", races[0]['title'])
