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

        today = datetime.date.today()

        dd = dict()
        dd['currentmembers'] = Membership.objects.filter(rider__club__exact=self, date__gte=today).count()
        dd['racemembers'] = Membership.objects.filter(rider__club__exact=self, date__gte=today, category='race').count()
        dd['ridemembers'] = Membership.objects.filter(rider__club__exact=self, date__gte=today, category='ride').count()
        dd['nonridingmembers'] = Membership.objects.filter(rider__club__exact=self, date__gte=today, category='non-riding').count()

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
        today = datetime.date.today()

        # remove all current helpers
        self.userrole_set.filter(role=dutyhelper).delete()

        # get the duty officers
        dutyofficer, created = ClubRole.objects.get_or_create(name="Duty Officer")
        dofficers = [ur.user for ur in UserRole.objects.filter(club=self, role=dutyofficer)]

        members = self.membership_set.filter(date__gte=today, category='race')
        for membership in members:
            user = membership.rider.user
            # don't duplicate (eg. member current for this year and next)
            existing = self.userrole_set.filter(role=dutyhelper, user=user)
            if existing.count() == 0 and not user in dofficers:
                role = UserRole(user=user, club=self, role=dutyhelper)
                role.save()

    def get_officials_with_counts(self, role):
        """Get a list of people who can fill a given role ordered
        by the number of times they have done so in the last year

        role - a role, eg. 'Duty Helper'

        Returns: a list of tuples (count, rider)
        where rider is a Rider instance, count is a count
        of the number of times they have been allocated to this role
        ordered by count, smallest first
        """

        import random
        # candidates are those members with a ClubRole with the
        # corresponding role
        candidates = self.rider_set.filter(user__userrole__role__name__exact=role)

        # if we have no candidates we can't do anything
        if candidates.count() == 0:
            return []

        # order candidates by number of recent duty assignments
        ordered = []
        epoch = datetime.date.today() - datetime.timedelta(days=365)

        for rider in candidates:
            c = self.races.filter(officials__rider__exact=rider, date__gte=epoch).count()
            ordered.append((c,rider))

        # shuffle to get a randomish distribution before sorting
        random.shuffle(ordered)

        # order on count
        ordered.sort()

        return ordered

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

        ordered = self.get_officials_with_counts(role)
        # can't allocate if there are no candidates
        if len(ordered) == 0:
            return

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

    def performancereport(self, rider, when=None):
        """Generate a rider performance report for this club,
        if the when arg is provided it should be a date
        and the performance report is generated as if on
        that date. Otherwise it is generated as of today."""

        # number of races
        # number of wins/places in last 12 months
        # wins in grade
        # places in grade

        info = dict()

        if when is None:
            when = datetime.date.today()

        # get the rider's current grade with this club, if we have one
        grade = self.grade(rider)

        startdate = when - datetime.timedelta(days=365)
        info['recent'] = rider.raceresult_set.filter(race__club__exact=self, place__lte=5, race__date__gt=startdate, race__date__lt=when)
        info['places'] = info['recent'].filter(place__lte=3, grade__exact=grade).count()
        info['wins'] = info['recent'].filter(place__exact=1, grade__exact=grade).count()

        return info

    def grade(self, rider):
        """Get the current grade of this rider, if we have one
        return the string grade name or None if there is no grade recorded"""

        # get the rider's current grade with this club, if we have one
        grades = rider.clubgrade_set.filter(club=self)
        if len(grades) == 1:
            return grades[0].grade
        else:
            return None

    def promotion(self, rider, when=None):
        """Is this rider eligible for promotion according to the
        WaratahCC rules
        More than 3 wins in grade or more than 7 placings in last 12 months.
        If the when argument is given, the calculation is done at that time.
        Return True if eligible, false otherwise."""

        perf = self.performancereport(rider, when=when)
        grade = self.grade(rider)

        return grade != 'A' and ((perf['wins'] >= 3) or (perf['places'] >= 7))

    def promotable(self):
        """Return a list of riders who might be eligible for
        promotion based on results in races run by this club."""

        from races.apps.cabici.usermodel import RaceResult

        thisyear = datetime.date.today().year
        oneyearago = datetime.date.today()-datetime.timedelta(days=365)

        winresults = RaceResult.objects.filter(race__club__exact=self, race__date__gt=oneyearago, place=1)
        riders = set([res.rider for res in winresults])
        promotable = []
        for rider in riders:
            if self.promotion(rider):
                promotable.append(rider)

        promotable.sort(key=lambda x: x.user.last_name)
        return promotable

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

        content = fd.read()

        try:
            rows = pyexcel.get_records(file_content=content, file_type=extension)
        except:
            # file format problem
            raise Exception('Error reading uploaded file, please check the file format.')

        # validate the file format
        if 'LicenceNo' not in rows[0] or 'LastName' not in rows[0] or 'Grade' not in rows[0]:
            raise Exception('Error in spreadsheet format, required columns missing.')

        # now that we have new data, delete any existing results for this race
        # but first count them so we can see if we need to recompute points below
        previousresults = RaceResult.objects.filter(race=self).count()
        RaceResult.objects.filter(race=self).delete()

        messages = []
        for row in rows:
            message = []

            if type(row['Id']) != int:
                # this should be a new rider, but it could be someone we know who
                # wasn't in the spreadsheet
                username = Rider.objects.make_username(row['FirstName'],
                                                       row['LastName'],
                                                       str(row['LicenceNo']))

                # just in case we know them already we use get_or_create
                user, created = User.objects.get_or_create(first_name=row['FirstName'],
                                                           last_name=row['LastName'],
                                                           username=username)

                if row['Email'] != '':
                    user.email = row['Email']
                    user.save()

                club = Club.objects.closest(row['Club'])
                if created:
                    # make the rider record
                    rider = Rider(licenceno=row['LicenceNo'], club=club, user=user)
                    message.append('Added new rider record for %s %s' % (row['FirstName'], row['LastName']))
                else:
                    # we didn't find this person by licence number so set it if we have it
                    rider = user.rider
                    if row['LicenceNo'] != '':
                        rider.licenceno = str(row['LicenceNo'])
                        message.append('Updated Licence Number to %s' % (row['LicenceNo'],))
                    if club.slug != 'Unknown':
                        rider.club = club
                        message.append('Updated Club to %s' % (club.slug,))

                rider.save()
            else:
                try:
                    rider = Rider.objects.get(id=int(row['Id']))
                except:
                    messages.append("Rider Id '%s' not found in database " % row['Id'])
                    continue

                # validate a bit
                if row['LastName'] != rider.user.last_name:
                    messages.append("Rider with Id %s has wrong last name, expected %s but found %s." % (row['Id'], rider.user.last_name, row['LastName']))
                    continue

            # ok, we now have our rider, either existing or new

            # update licenceno if we didn't know it before
            if rider.licenceno == '0' and row['LicenceNo'] != '0':
                rider.licenceno = row['LicenceNo']
                rider.save()
                message.append("Updated licence number for %s %s to %s" % (rider.user.first_name, rider.user.last_name, rider.licenceno))


            # we know that this rider is a current member of their club if the Regd field is R
            if row['Regd'] == 'R':
                endofyear = datetime.date(day=31, month=12, year=datetime.date.today().year)

                m,created = Membership.objects.get_or_create(rider=rider,
                                                             club=rider.club,
                                                             date=endofyear,
                                                             category='race')
                if created:
                    message.append('Updated membership of rider %s of club %s to %s' % (str(rider), rider.club.slug, endofyear))

            # deal with grades
            grading, created = rider.clubgrade_set.get_or_create(club=self.club, rider=rider)
            if created:
                # allocate the grade they raced this time
                grading.grade = row['Grade']
                grading.save()

            usual_grade = grading.grade

            # a grade ending in P means the rider is being permanently re-graded
            # so we should change their recorded grade
            if row['Grade'].endswith('P'):
                # get the real grade for the result
                row['Grade'] = row['Grade'][0]
                grading.grade = row['Grade']
                grading.save()
                message.append('Updated grade of %s to %s' % (str(rider), grading.grade))
            elif not row['Grade'] == usual_grade:
                message.append('%s rode in grade %s but is usually %s grade' % (str(rider), row['Grade'], usual_grade))

            # work out place from points - actually need to account for small grades (E, F)
            points = int(row['Points'])
            if points == 2:
                place = None
            elif points > 0:
                place = 8-points

            if row['ShirtNo'] == '':
                shirtno = 0
            else:
                shirtno = int(row['ShirtNo'])

            # special case of number 999 indicates a helper, change the 'grade'
            if shirtno == 999:
                row['Grade'] = "Helper"
                message.append('%s recorded as a Helper' % (str(rider),))

            result = RaceResult(rider=rider, race=self, place=place,
                                usual_grade=usual_grade, grade=row['Grade'],
                                number=shirtno)

            # check for duplicate race number
            while RaceResult.objects.filter(race=self, number=result.number).count() == 1:
                result.number = result.number + 200

            # check for duplicate race/rider
            if RaceResult.objects.filter(race=self, rider=result.rider).count() == 1:
                # not much we can do here
                message.append("Error: duplicate result discarded for rider %s" % (str(rider)))
            else:
                try:
                    with transaction.atomic():
                        result.save()
                except IntegrityError as e:
                    message.append("Error saving result for rider %s: %s" % (str(rider), e,))

            if message != []:
                messages.append('\n'.join(message))

        self.fix_small_races()

        # once results are in place, we tally the pointscores for this race
        if previousresults > 0:
            # need to recalculate pointscores since we've deleted results
            for ps in self.pointscore_set.all():
                ps.recalculate()
        else:
            # can just tally these results
            self.tally_pointscores()

        return messages

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
