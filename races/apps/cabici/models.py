#!/usr/bin/python
#
# Copyright 2023 Steve Cassidy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime

import ngram
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from races.apps.cabici.geoposition import GeopositionField


class ClubManager(models.Manager):

    pass


class Club(models.Model):

    objects = ClubManager()

    name = models.CharField(max_length=100)
    website = models.URLField(max_length=400)
    slug = models.SlugField()  # short name eg. WVCC, MWCC for use in URL
    contact = models.EmailField(blank=True)
    manage_races = models.BooleanField(default=False)
    manage_members = models.BooleanField(default=False)
    manage_results = models.BooleanField(default=False)

    def __str__(self):
        return self.slug

    class Meta:
        ordering = ["name"]

    def graded_riders(self):
        """Return a list of riders with grades assigned"""

        clubgrades = self.clubgrade_set.all()
        return [cg.rider for cg in clubgrades]

    def statistics(self):
        """Return a dictionary of statistics for this club"""

        from .usermodel import Membership, Rider, UserRole

        today = datetime.date.today()

        dd = dict()
        dd["currentmembers"] = Membership.objects.filter(rider__club__exact=self, date__gte=today).count()
        dd["racemembers"] = Membership.objects.filter(rider__club__exact=self, date__gte=today, category="race").count()
        dd["ridemembers"] = Membership.objects.filter(rider__club__exact=self, date__gte=today, category="ride").count()
        dd["nonridingmembers"] = Membership.objects.filter(
            rider__club__exact=self, date__gte=today, category="non-riding"
        ).count()

        # roles
        dd["commissaires"] = (
            Rider.objects.filter(club__exact=self)
            .exclude(commissaire__exact="")
            .exclude(commissaire__exact=0)
            .select_related("user")
        )
        dd["roles"] = UserRole.objects.filter(club__exact=self).order_by("role").select_related("user", "role")

        return dd

    def recent_races(self):
        """Return a list of the most recent races
        most recent first"""

        return self.races.filter(date__lte=datetime.date.today()).order_by("-date")[:5]

    def get_officials_with_counts(self, role, skip_club_filter=False):
        """Get a list of people who can fill a given role ordered
        by the number of times they have done so in the last year

        role - a role, eg. 'Duty Helper'

        Returns: a list of tuples (count, rider)
        where rider is a Rider instance, count is a count
        of the number of times they have been allocated to this role
        ordered by count, smallest first
        """

        import random

        from .usermodel import Rider

        # candidates are all riders with a UserRole for this club
        candidates = Rider.objects.filter(user__userrole__role__name__exact=role).distinct()

        if not skip_club_filter:
            candidates = candidates.filter(user__userrole__club__exact=self)

        # candidates = self.rider_set.filter(user__userrole__role__name__exact=role).distinct()

        # if we have no candidates we can't do anything
        if candidates.count() == 0:
            return []

        # order candidates by number of recent duty assignments
        ordered = []
        epoch = datetime.date.today() - datetime.timedelta(days=365)

        for rider in candidates:
            c = self.races.filter(officials__rider__exact=rider, date__gte=epoch).count()
            ordered.append((c, rider))

        # shuffle to get a randomish distribution before sorting
        random.shuffle(ordered)

        # order on count
        ordered.sort(key=lambda x: x[0])

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

        from .usermodel import ClubRole, RaceStaff, UserRole

        clubrole, created = ClubRole.objects.get_or_create(name=role)

        ordered = self.get_officials_with_counts(role)
        # can't allocate if there are no candidates
        if len(ordered) == 0:
            return

        for race in races:
            existing = RaceStaff.objects.filter(race=race, role=clubrole)
            if replace:
                existing.delete()
            else:
                # remove any that aren't in this role any more
                for staff in existing:
                    if UserRole.objects.filter(user=staff.rider.user, club=self, role=clubrole).count() == 0:
                        staff.delete()
                # refresh existing in case we removed someone
                existing = RaceStaff.objects.filter(race=race, role=clubrole)

            # allocate more if there are less than number already allocated
            for _ in range(max(0, number - existing.count())):
                c, rider = ordered.pop(0)
                rs = RaceStaff(rider=rider, race=race, role=clubrole)
                rs.save()
                # requeue the rider
                ordered.append((c, rider))

    def performancereport(self, rider, when=None):
        """Generate a rider performance report for this club,
        if the when arg is provided it should be a date
        and the performance report is generated as if on
        that date. Otherwise it is generated as of today."""

        # number of races
        # number of wins/places in last 12 months
        # wins in grade
        # places in grade (> 3rd place)

        info = dict()

        if when is None:
            when = datetime.date.today()

        # get the rider's current grade with this club, if we have one
        grade = self.grade(rider)

        startdate = when - datetime.timedelta(days=365)
        info["recent"] = rider.raceresult_set.filter(
            race__club__exact=self, place__lte=5, race__date__gt=startdate, race__date__lt=when
        )
        info["places"] = info["recent"].filter(place__lte=3, place__gt=0, grade__exact=grade).count()
        info["wins"] = info["recent"].filter(place__exact=1, place__gt=0, grade__exact=grade).count()

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

        return grade != "A" and ((perf["wins"] >= 3) or (perf["places"] >= 7))

    def promotable(self):
        """Return a list of riders who might be eligible for
        promotion based on results in races run by this club."""

        from races.apps.cabici.usermodel import RaceResult

        oneyearago = datetime.date.today() - datetime.timedelta(days=365)

        winresults = RaceResult.objects.filter(race__club__exact=self, race__date__gt=oneyearago, place=1)
        riders = {res.rider for res in winresults}
        promotable = []
        for rider in riders:
            if self.promotion(rider):
                promotable.append(rider)

        promotable.sort(key=lambda x: x.user.last_name)
        return promotable

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
            if Race.objects.filter(hash=r["hash"]).count() == 0:
                location = RaceCourse.objects.find_location(r["location"])

                # title may need truncating
                if len(r["title"]) > 100:
                    r["title"] = r["title"][:99]

                try:
                    race = Race(
                        title=r["title"],
                        date=r["date"],
                        starttime=r["time"],
                        club=self,
                        location=location,
                        website=r["url"],
                        hash=r["hash"],
                    )

                    race.save()
                    racelist.append(race)
                except ValidationError as e:
                    # report the error?
                    errors.append(str(e))
                    # print "Race ingest error: ", e
        # else:
        # print "Race duplicate", r['title'], r['date']

        return (racelist, errors)


class RaceCourseManager(models.Manager):

    def find_location(self, name):
        """Find a RaceCourse using an approximate match to
        the given name, return the best matching RaceCourse instance"""

        courses = self.all()

        ng = ngram.NGram(courses, key=str)

        location = ng.finditem(name)

        if location is None:
            location, created = self.get_or_create(name="Unknown")

        return location


class RaceCourse(models.Model):
    """A place where a race happens"""

    objects = RaceCourseManager()

    name = models.CharField(max_length=100)
    shortname = models.CharField(max_length=20, default="")
    location = GeopositionField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


STATUS_CHOICES = (("d", "Draft"), ("p", "Published"), ("w", "Withdrawn"), ("c", "Cancelled"))

CATEGORY_CHOICES = (
    ("1", "Category 1 Open and State Championships"),
    ("2", "Category 2 Open/Masters Open/Junior Open"),
    ("3", "Category 3 Club/Inter-Club"),
    ("Junior", "Junior Club"),
    ("Rec", "Recreational/Timed Rides"),
)

DISCIPLINE_CHOICES = (("r", "Road"), ("t", "Track"), ("cx", "Cyclocross"), ("mtb", "MTB"), ("bmx", "BMX"))

LICENCE_CHOICES = (
    ("e.m", "Elite Men"),
    ("e.w", "Elite Women"),
    ("e.mw", "Elite Men & Women"),
    ("m.mw", "Masters Men & Women"),
    ("m.m", "Masters Men"),
    ("m.w", "Masters Women"),
    ("em.mw", "Elite or Masters Men & Women"),
    ("em.m", "Elite or Masters Men"),
    ("em.w", "Elite or Masters Women"),
    ("j.mw", "Junior"),
    ("k.mw", "Kids"),
    ("p.mw", "Para-cyclist Men & Women"),
    ("p.m", "Para-cyclist Men"),
    ("p.w", "Para-cyclist Women"),
)


class Race(models.Model):

    # empty help texts here to force help element in forms
    title = models.CharField(max_length=100)
    date = models.DateField(help_text=" ")
    signontime = models.TimeField(help_text="")
    starttime = models.CharField(max_length=100, help_text="")
    club = models.ForeignKey(Club, related_name="races", help_text=" ", on_delete=models.CASCADE)
    website = models.URLField(blank=True, max_length=400, help_text=" ")
    location = models.ForeignKey(RaceCourse, help_text=" ", on_delete=models.CASCADE)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="p", help_text=" ")
    description = models.TextField(default="", blank=True, help_text=" ")
    hash = models.CharField(max_length=100, blank=True)

    # Offical category of the race
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default="3")
    # Discipline
    discipline = models.CharField(max_length=10, choices=DISCIPLINE_CHOICES, default="r")
    # Licence - format is ll.gg where l are licence types (emjkp), g are genders (mw)
    licencereq = models.CharField(max_length=10, choices=LICENCE_CHOICES, default="em.mw")

    grading = models.CharField(max_length=50, default="A,A2,B,C,D,E,F")

    class Meta:
        ordering = ["date", "signontime"]

    def __str__(self):
        return self.title + ", " + str(self.date)

    def get_absolute_url(self):
        return reverse("race", kwargs={"pk": self.id, "slug": self.club.slug})

    def duplicate(self):
        """Create a race just like this one with a slightly modified title
        but make it draft"""

        pass

    def fix_small_races(self):
        """fix up races with small fields after import
        - points/place calculation is incorrect"""

        for grade in ["A", "B", "C", "D", "E", "F"]:
            results = self.raceresult_set.filter(grade=grade, place__gt=0)
            ingrade = self.raceresult_set.filter(grade=grade).count()

            if ingrade < 12:
                # if the smallest place is not 1
                places = [r.place for r in results]
                if places != [] and min(places) > 1:
                    fudge = min(places) - 1
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
