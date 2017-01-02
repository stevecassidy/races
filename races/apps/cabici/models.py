from django.db import models
from geoposition.fields import GeopositionField
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from importlib import import_module
from django.contrib.auth.models import User
from django.db import transaction

import icalendar
import pytz
from urllib2 import urlopen, HTTPError, URLError, Request
import datetime
import hashlib
import ngram
import csv


class ClubManager(models.Manager):

    def closest(self, name):
        """Find a Club using an approximate match to
        the given name, return the best matching Club instance"""

        clubs = self.all()

        ng = ngram.NGram(clubs, key=str)

        club = ng.finditem(name)

        if club is None:
            unknown_club, created = Club.objects.get_or_create(name="Unknown Club", slug="Unknown")
            club = unknown_club

        return club

class Club(models.Model):

    objects = ClubManager()

    name = models.CharField(max_length=100)
    website = models.URLField(max_length=400)
    slug = models.SlugField()  # short name eg. WVCC, MWCC for use in URL
    contact = models.EmailField(blank=True)
    icalurl = models.URLField(max_length=400, blank=True, default='')
    icalpatterns = models.CharField(max_length=100, blank=True, default='')
    # flags for club capabilities
    manage_races = models.BooleanField(default=False)
    manage_members = models.BooleanField(default=False)
    manage_results = models.BooleanField(default=False)

    def __unicode__(self):
        return self.slug

    class Meta:
        ordering = ['name']

    def graded_riders(self):
        """Return a list of riders with grades assigned"""

        clubgrades = self.clubgrade_set.all()
        return [cg.rider for cg in clubgrades]

    def statistics(self):
        """Return a dictionary of statistics for this club"""

        from usermodel import Membership, Rider, UserRole

        thisyear = datetime.date.today().year

        dd = dict()
        dd['currentmembers'] = Membership.objects.filter(rider__club__exact=self, year__exact=thisyear).count()
        dd['racemembers'] = Membership.objects.filter(rider__club__exact=self, year__exact=thisyear, category='race').count()
        dd['ridemembers'] = Membership.objects.filter(rider__club__exact=self, year__exact=thisyear, category='ride').count()
        dd['nonridingmembers'] = Membership.objects.filter(rider__club__exact=self, year__exact=thisyear, category='non-riding').count()

        # roles
        dd['commissaires'] = Rider.objects.filter(club__exact=self).exclude(commissaire__exact='').exclude(commissaire__exact=0)
        dd['roles'] = UserRole.objects.filter(club__exact=self).order_by('role')

        return dd

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

    def recent_races(self):
        """Return a list of the most recent races
        most recent first"""

        return self.races.filter(date__lte=datetime.date.today()).order_by('-date')[:5]

    def create_duty_helpers(self):
        """Add all current race members as duty helpers"""

        from .usermodel import ClubRole, Membership, UserRole

        dutyhelper, created = ClubRole.objects.get_or_create(name="Duty Helper")
        thisyear = datetime.date.today().year

        # remove all current helpers
        self.userrole_set.filter(role=dutyhelper).delete()

        # get the duty officers
        dutyofficer, created = ClubRole.objects.get_or_create(name="Duty Officer")
        dofficers = [ur.user for ur in UserRole.objects.filter(club=self, role=dutyofficer)]

        members = self.membership_set.filter(year__gte=thisyear, category='race')
        for membership in members:
            user = membership.rider.user
            # don't duplicate (eg. member current for this year and next)
            existing = self.userrole_set.filter(role=dutyhelper, user=user)
            if existing.count() == 0 and not user in dofficers:
                role = UserRole(user=user, club=self, role=dutyhelper)
                role.save()

    def allocate_officials(self, role, number, races, replace=False):
        """Allocate people to fill the given roles for
        the given races.

        role - a role to allocate to, eg. 'Duty Helper'
        number - number to allocate to each race
        races - list (or result set) of races to allocate
        replace - if True, replace any existing officials for each race

        Select people at random from the eligebility list weighted
        by the number of times they have served in this role
        recently.
        """

        self.create_duty_helpers()

        from .usermodel import RaceStaff, ClubRole
        clubrole, created = ClubRole.objects.get_or_create(name=role)

        import random
        # candidates are those members with a ClubRole with the
        # corresponding role
        candidates = self.rider_set.filter(user__userrole__role__name__exact=role)

        # if we have no candidates we can't do anything
        if candidates.count() == 0:
            return

        # order candidates by number of recent duty assignments
        ordered = []
        epoch = datetime.date.today() - datetime.timedelta(days=365)

        for rider in candidates:
            c = self.races.filter(officials__rider__exact=rider, date__gte=epoch).count()
            ordered.append((c,rider))

        random.shuffle(ordered)

        ordered.sort()

        for race in races:
            existing = RaceStaff.objects.filter(race=race, role=clubrole)
            if replace:
                existing.delete()

            # allocate more if there are less than number already allocated
            for n in range(max(0,number-existing.count())):
                c, rider = ordered.pop(0)
                rs = RaceStaff(rider=rider, race=race, role=clubrole)
                rs.save()
                # requeue the rider
                ordered.append((c,rider))


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
                                starttime=r['time'],
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
            print "UNKNOWN LOCATION", name
            location, created = self.get_or_create(name="Unknown")

        return location

class RaceCourse(models.Model):
    """A place where a race happens"""

    objects = RaceCourseManager()

    name = models.CharField(max_length=100)
    shortname = models.CharField(max_length=20, default='')
    location = GeopositionField()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']

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
    ('c', 'Cancelled')
)

CATEGORY_CHOICES = (
    ('1', 'Category 1 Open and State Championships'),
    ('2', 'Category 2 Open/Masters Open/Junior Open'),
    ('3', 'Category 3 Club/Inter-Club'),
    ('Junior', 'Junior Club'),
    ('Rec', 'Recreational/Timed Rides')
)

DISCIPLINE_CHOICES = (
    ('r', 'Road'),
    ('t', 'Track'),
    ('cx', 'Cyclocross'),
    ('mtb', 'MTB'),
    ('bmx', 'BMX')
)

LICENCE_CHOICES = (
    ('e.m', 'Elite Men'),
    ('e.w', 'Elite Women'),
    ('e.mw', 'Elite Men & Women'),
    ('m.mw', 'Masters Men & Women'),
    ('m.m', 'Masters Men'),
    ('m.w', 'Masters Women'),
    ('em.mw', 'Elite or Masters Men & Women'),
    ('em.m', 'Elite or Masters Men'),
    ('em.w', 'Elite or Masters Women'),
    ('j.mw', 'Junior'),
    ('k.mw', 'Kids'),
    ('p.mw', 'Para-cyclist Men & Women'),
    ('p.m', 'Para-cyclist Men'),
    ('p.w', 'Para-cyclist Women'),
)

class Race(models.Model):

    # empty help texts here to force help element in forms
    title = models.CharField(max_length=100)
    date = models.DateField(help_text=" ")
    signontime = models.TimeField(help_text="")
    starttime = models.CharField(max_length=100, help_text="")
    club = models.ForeignKey(Club, related_name='races', help_text=" ")
    website  = models.URLField(blank=True, max_length=400, help_text=" ")
    location = models.ForeignKey(RaceCourse, help_text=" ")
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='p', help_text=" ")
    description = models.TextField(default="", blank=True, help_text=" ")
    hash = models.CharField(max_length=100, blank=True)

    # Offical category of the race
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default="3")
    # Discipline
    discipline = models.CharField(max_length=10, choices=DISCIPLINE_CHOICES, default='r')
    # Licence - format is ll.gg where l are licence types (emjkp), g are genders (mw)
    licencereq = models.CharField(max_length=10, choices=LICENCE_CHOICES, default="em.mw")


    class Meta:
        ordering = ['date', 'signontime']

    def __unicode__(self):
        return unicode(self.club) + u": " + self.title + ", " + str(self.date)

    def get_absolute_url(self):
        return reverse('race', kwargs={'pk': self.id, 'slug': self.club.slug})

    def duplicate(self):
        """Create a race just like this one with a slightly modified title
        but make it draft"""

        pass


    def load_excel_results(self, fd, extension):
        """Load race results from a file handle pointing to an Excel file"""

        from races.apps.cabici.usermodel import RaceResult, Rider, Membership
        import pyexcel

        # delete any existing results for this race
        previousresults = RaceResult.objects.filter(race=self).count()
        RaceResult.objects.filter(race=self).delete()

        content = fd.read()

        rows = pyexcel.get_records(file_content=content, file_type=extension)

        for row in rows:

            if row['LicenceNo'] == 0:
                # create a temporary licence number so that we can record the result
                row['LicenceNo'] = 'temp'+str(hash(str(row)))[1:10]

            try:
                rider = Rider.objects.get(licenceno=row['LicenceNo'])
            except:
                user, created = User.objects.get_or_create(first_name=row['FirstName'], last_name=row['LastName'], username=row['FirstName']+row['LastName'])

                if row['Email'] != '':
                    user.email = row['Email']
                user.save()

                club = Club.objects.closest(row['Club'])
                if created:
                    # make the rider record
                    rider = Rider(licenceno=row['LicenceNo'], club=club, user=user)
                else:
                    # we didn't find this person by licence number so set it if we have it
                    if row['LicenceNo'] != '':
                        rider.licenceno = row['LicenceNo']
                    if club.slug != 'Unknown':
                        rider.club = club

                rider.save()

                # we know that this rider is a current member of their club
                thisyear = datetime.date.today().year
                m = Membership(rider=rider, club=club, year=thisyear, category='race')
                m.save()

            # fix xP grades
            if row['Grade'].endswith('P'):
                row['Grade'] = row['Grade'][0]

            # work out place from points - actually need to account for small grades (E, F)
            points = int(row['Points'])
            if points == 2:
                result = RaceResult(rider=rider, race=self,  grade=row['Grade'], number=row['ShirtNo'])
            elif points > 0:
                place = 8-points
                result = RaceResult(rider=rider, race=self, place=place, grade=row['Grade'], number=row['ShirtNo'])

            while True:
                try:
                    with transaction.atomic():
                        result.save()
                        break
                except IntegrityError as e:
                    # duplicate race/grade/number
                    # probably wrong number entered so we can recover by fixing the number
                    result.number = result.number + 200



        self.fix_small_races()

        # once results are in place, we tally the pointscores for this race
        if previousresults > 0:
            # need to recalculate pointscores since we've deleted results
            for ps in self.pointscore_set.all():
                ps.recalculate()
        else:
            # can just tally these results
            self.tally_pointscores()

    def fix_small_races(self):
        """fix up races with small fields after import
        - points/place calculation is incorrect"""

        for grade in ['A', 'B', 'C', 'D', 'E', 'F']:
            results = self.raceresult_set.filter(grade=grade, place__isnull=False)
            ingrade = self.raceresult_set.filter(grade=grade).count()

            if ingrade < 12:
                # if the smallest place is not 1
                places = [r.place for r in results]
                if places != [] and min(places) > 1:
                    fudge = min(places)-1
                    for result in results:
                        result.place -= fudge
                        result.save()


    def tally_pointscores(self):
        """Tally all points for this race
        called when all results for this race are loaded
        so that we know how many riders there were per grade"""

        for ps in self.pointscore_set.all():
            for result in self.raceresult_set.all():
                ps.tally(result)
