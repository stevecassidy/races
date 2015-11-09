from django.db import models
from geoposition.fields import GeopositionField
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from importlib import import_module
from django.contrib.auth.models import User

import icalendar
import pytz
from urllib2 import urlopen, HTTPError, URLError, Request
import datetime
import hashlib
import ngram
import csv


class Club(models.Model):

    name = models.CharField(max_length=100)
    website = models.URLField(max_length=400)
    slug = models.SlugField()  # short name eg. WVCC, MWCC for use in URL
    contact = models.EmailField(blank=True)
    icalurl = models.URLField(max_length=400, blank=True, default='')
    icalpatterns = models.CharField(max_length=100, blank=True, default='')

    def __unicode__(self):
        return self.slug

    class Meta:
        ordering = ['name']

    def graded_riders(self):
        """Return a list of riders with grades assigned"""

        clubgrades = self.clubgrade_set.all()
        return [cg.rider for cg in clubgrades]


    def ingest(self):
        """Try a couple of ingest methods.
        Return a tuple (races, errormsg) where races is a list
        of Race instances and errormsg is an error message if any."""

        if self.icalurl != '':
            return self.ingest_ical()
        else:
            return self.ingest_by_module()


    def ingest_by_module(self):
        """Try to find a module named for the (lowercased) slug field
        of this club. If found call the ingest procedure
        to generate a list of races and pass it to ingest_race_list.
        Return a tuple (races, errormsg) where races is a list
        of Race instances and errormsg is an error message if any."""

        modulename = self.slug.lower()

        # do we have this module inside ingest?
        try:

            mod = import_module("races.ingest."+modulename)
            # now invoke the ingest procedure
            racedict = mod.ingest()

            (races, error) = self.ingest_race_list(racedict)

        except ImportError:
            races = []
            error = 'No ingest module for club "' + modulename + '"'

        return (races, error)




    def ingest_ical(self):
        """Import races from an icalendar feed
        Return a tuple (races, errormsg) where races is a list
        of Race instances and errormsg is an error message if any."""

        if self.icalurl == '':
            return ([], "No icalendar URL")

        try:
            req = Request(self.icalurl)
            req.add_header('User-Agent', 'cabici/1.0 event harvester http://cabici.net/')
            h = urlopen(req)
            ical_text = h.read()
            h.close()
        except HTTPError as e:
            content = e.read()
            return ([], "Error reading icalendar URL:" + content)
        except URLError as e:
            return ([], "Bad URL: " + self.icalurl)


        try:
            cal = icalendar.Calendar.from_ical(ical_text)
        except ValueError:
            return ([], "Error reading icalendar file")

        patterns = [p.strip() for p in self.icalpatterns.split(',')]
        tz = pytz.timezone('Australia/Sydney')

        races = []
        for component in cal.walk():

            if component.has_key('DTSTART'):
                start = component.decoded('DTSTART')
                title = component.get('SUMMARY', '')
                description = component.get('DESCRIPTION', '')
                website = component.get('URL', '')

                # CCCC at least has quoted chars in the description
                # this removes them
                description = icalendar.parser.unescape_char(description)
                description = description.replace(r'\:', r':')

                if patterns == [''] or any([title.find(p) >- 0 for p in patterns]):

                    calstring = "%s%s%s%s" % (str(start), title, description, website)
                    # need to fix encoding to ascii before calculating the hash
                    calstring = calstring.encode('ascii', errors='replace')
                    racehash = hashlib.sha1(calstring).hexdigest()

                    # do we already have this race?
                    if Race.objects.filter(hash=racehash).count() == 0:

                        location = RaceCourse.objects.find_location(title)

                        if type(start) == datetime.datetime:

                            start = start.astimezone(tz)

                            startdate = start.date().isoformat()
                            starttime = start.time().isoformat()
                        elif type(start) == datetime.date:

                            startdate = start.isoformat()
                            starttime = "0:0"
                        else:

                            startdate = start
                            starttime = "0:0"

                        race = Race(date=startdate,
                                    time=starttime,
                                    title=str(title),
                                    website=website,
                                    description=unicode(description),
                                    location=location,
                                    club=self,
                                    hash=racehash)
                        race.save()
                        races.append(race)

        return (races, "")


    def ingest_race_list(self, races):
        """Create races from a list of dictionaries containing
        the race properties
        Required properties are:
        title
        date - ISO date string YYYY-MM-DD
        time - ISO time string HH:MM
        location - a string that we can use to guess the race course
        url
        hash - unique has for the race to spot duplicates

        Return a tuple of (races, errors) where races is a list of
        Race instances and errors is a list of any errors produced
        during the process

        """

        racelist = []
        errors = []
        for r in races:
            # do we already have this race?
            if Race.objects.filter(hash=r['hash']).count() == 0:
                location = RaceCourse.objects.find_location(r['location'])

                # title may need truncating
                if len(r['title']) > 100:
                    r['title'] = r['title'][:99]

                try:
                    race = Race(title=r['title'],
                                date=r['date'],
                                time=r['time'],
                                club=self,
                                location=location,
                                website=r['url'],
                                hash=r['hash'])

                    race.save()
                    racelist.append(race)
                except ValidationError as e:
                    # report the error?
                    errors.append(str(e))
                    #print "Race ingest error: ", e
           # else:
                #print "Race duplicate", r['title'], r['date']


        return (racelist, errors)






class RaceCourseManager(models.Manager):


    def find_location(self, name):
        """Find a RaceCourse using an approximate match to
        the given name, return the best matching RaceCourse instance"""

        courses = self.all()

        ng = ngram.NGram(courses, key=str)

        location = ng.finditem(name)

        if location == None:
            location = self.get(name="Unknown")

        return location

class RaceCourse(models.Model):
    """A place where a race happens"""

    objects = RaceCourseManager()

    name = models.CharField(max_length=100)
    location = GeopositionField()

    def __unicode__(self):
        return self.name

class RacePrototype(models.Model):
    """A race prototype describes a race that
    happens often - it includes all details except
    the date"""
    title = models.CharField(max_length=100)
    time = models.TimeField()
    club = models.ForeignKey(Club)
    location = models.ForeignKey(RaceCourse)

    def __unicode__(self):
        return unicode(self.club) + u": " + self.title

STATUS_CHOICES = (
    ('d', 'Draft'),
    ('p', 'Published'),
    ('w', 'Withdrawn'),
)

class Race(models.Model):

    title = models.CharField(max_length=100)
    date = models.DateField()
    time = models.TimeField()
    club = models.ForeignKey(Club, related_name='races')
    website  = models.URLField(blank=True, max_length=400)
    location = models.ForeignKey(RaceCourse)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='d')
    description = models.TextField(default="", blank=True)
    hash = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['date', 'time']

    def __unicode__(self):
        return unicode(self.club) + u": " + self.title + ", " + str(self.date)

    def get_absolute_url(self):
        return reverse('race', kwargs={'pk': self.id, 'slug': self.club.slug})

    def duplicate(self):
        """Create a race just like this one with a slightly modified title
        but make it draft"""

        pass

    def load_csv_results(self, fd):
        """Load race results from a file handle pointing to a CSV file"""

        from races.apps.site.usermodel import RaceResult, Rider

        unknown_club, created = Club.objects.get_or_create(name="Unknown Club", slug="Unknown")

        # delete any existing results for this race
        RaceResult.objects.filter(race=self).delete()

        reader = csv.DictReader(fd)

        for row in reader:

            if not 'LicenceNo' in row or row['LicenceNo'] == '0':
                continue

            riders = Rider.objects.filter(licenceno=row['LicenceNo'])
            if len(riders) == 0:
                user, created = User.objects.get_or_create(first_name=row['FirstName'], last_name=row['LastName'], username=row['FirstName']+row['LastName'])
                user.save()
                clubs = Club.objects.filter(slug=row['Club'])
                if len(clubs) == 1:
                    club = clubs[0]
                else:
                    club = unknown_club
                rider = Rider(licenceno=row['LicenceNo'], club=club, user=user)
                rider.save()
            else:
                # take the first rider if we have them already (should be just one)
                rider = riders[0]

            # work out place from points - actually need to account for small grades (E, F)
            points = int(row['Points'])
            if points == 2:
                result = RaceResult(rider=rider, race=self,  grade=row['Grade'], number=row['ShirtNo'])
            elif points > 0:
                place = 8-points
                result = RaceResult(rider=rider, race=self, place=place, grade=row['Grade'], number=row['ShirtNo'])

            result.save()
