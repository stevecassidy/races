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
import json

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_comma_separated_integer_list
from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import slugify

from races.apps.cabici.models import Club, Race

STATE_CHOICES = (
    ("ACT", "Australian Capital Territory"),
    ("NSW", "New South Wales"),
    ("NT", "Northern Territory"),
    ("QLD", "Queensland"),
    ("SA", "South Australia"),
    ("TAS", "Tasmania"),
    ("VIC", "Victoria"),
    ("WA", "Western Australia"),
)


class RiderManager(models.Manager):
    """Manager for riders"""

    def make_username(self, firstname, lastname, licenceno):
        """Generate a suitable username for a rider"""

        return slugify(firstname + lastname + licenceno)[:30]


GENDER_CHOICES = (("M", "Male"), ("F", "Female"), ("O", "Other"))


class Rider(models.Model):
    """Model for extra information associated with a club member (rider)"""

    objects = RiderManager()

    # an auto updated datetime field to record time of last update to this rider
    updated = models.DateTimeField(auto_now=True)

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    licenceno = models.CharField("Licence Number", max_length=20, blank=True, default="")
    gender = models.CharField("Gender", max_length=2, choices=GENDER_CHOICES, blank=True, default="M")
    dob = models.DateField("Date of Birth", default=datetime.date(1970, 1, 1), blank=True)
    streetaddress = models.CharField("Address", max_length=100, default="", blank=True)
    suburb = models.CharField("Suburb", max_length=100, default="", blank=True)
    state = models.CharField("State", choices=STATE_CHOICES, max_length=10, default="NSW", blank=True)
    postcode = models.CharField("Postcode", max_length=4, default="", blank=True)
    phone = models.CharField("Phone", max_length=50, default="", blank=True)

    commissaire = models.CharField(
        "Commissaire Level",
        max_length=10,
        default="0",
        blank=True,
        help_text="0 if not a Commissaire, otherwise eg. 1, RT",
    )
    commissaire_valid = models.DateField("Commissaire Valid To", null=True, blank=True)

    emergencyname = models.CharField("Emergency Contact Name", max_length=100, default="", blank=True)
    emergencyphone = models.CharField("Emergency Contact Phone", max_length=50, default="", blank=True)
    emergencyrelationship = models.CharField("Emergency Contact Relationship", max_length=20, default="", blank=True)

    official = models.BooleanField(
        "Club Official",
        default=False,
        help_text="Officials can view and edit member details, schedule races, upload results",
    )

    club = models.ForeignKey(Club, null=True, on_delete=models.CASCADE)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]

    def get_absolute_url(self):
        return reverse("rider", kwargs={"pk": self.user.pk})

    def __str__(self):
        return self.user.first_name + " " + self.user.last_name

    @cached_property
    def current_membership(self):

        m = self.membership_set.all().order_by("-date")
        if m:
            return m[0]

    @property
    def member_category(self):
        """Return the category from the most recent membership year"""

        m = self.current_membership
        if m:
            return m.get_category_display()
        else:
            return ""

    @property
    def member_date(self):
        """Return the year from the most recent membership year"""

        m = self.current_membership
        if m:
            return m.date
        else:
            return ""

    @property
    def member_add_on(self):
        """Return the boolean addon flag from the current membership year"""

        m = self.current_membership
        if m:
            return m.add_on
        else:
            return False

    @property
    def classification(self):
        """Return the racing classification for this rider based
        on their DOB"""

        # classes with upper bound + 1 for each group in order
        classes = (
            ("Kidz", 7),
            ("U9", 9),
            ("U11", 11),
            ("U13 Boys", 13),
            ("U15 Men", 15),
            ("U17 Men", 17),
            ("U19 Men", 19),
            ("U23 Men", 23),
            ("Elite Men", 30),
            ("M1", 35),
            ("M2", 40),
            ("M3", 45),
            ("M4", 50),
            ("M5", 55),
            ("M6", 60),
            ("M7", 65),
            ("M8", 70),
            ("M9", 75),
            ("M10", 81),
            ("M11", 110),
        )

        age = datetime.datetime.now().year - self.dob.year

        for cat, cutoff in classes:
            if age < cutoff:
                if self.gender == "F":
                    if cat.startswith("M"):
                        cat = cat.replace("M", "W")
                    elif cat == "Elite Men":
                        cat = cat.replace("Men", "Women")
                    elif cat == "U23 Men":
                        cat = "Elite Women"
                    elif cat.startswith("U"):
                        cat = cat.replace("Men", "Women")
                        cat = cat.replace("Boys", "Girls")
                return cat

    @property
    def grades(self):
        """Return a dictionary of grades for
        different clubs for this rider, key is the
        club slug"""

        result = {}
        grades = self.clubgrade_set.all()
        for grade in grades:
            result[grade.club.slug] = grade.grade

        return result

    @property
    def roles(self):
        """Return a list of the roles that this rider has"""

        result = {}
        roles = self.user.userrole_set.all()
        for role in roles:
            result[role.role.shortname] = role.id
        return result

    def performancereport(self, when=None):
        """Generate a rider performance report for all clubs
        if the when arg is provided it should be a date
        and the performance report is generated as if on
        that date. Otherwise it is generated as of today."""

        # note that this duplicates logic in Club.performancereport but for all
        # clubs, we use it in generating the rider details page

        # number of races
        # number of wins/places in last 12 months
        # wins in grade
        # places in grade

        info = dict()
        startdate = datetime.date.today() - datetime.timedelta(days=365)
        info["recent"] = self.raceresult_set.filter(place__lte=5, place__gt=0, race__date__gt=startdate)
        info["places"] = info["recent"].filter(place__lte=3, place__gt=0).count()
        info["wins"] = info["recent"].filter(place__exact=1).count()

        return info


MEMBERSHIP_CATEGORY_CHOICES = (("Ride", "ride"), ("Race", "race"), ("Non-riding", "non-riding"))


class Membership(models.Model):
    """Membership of a club with a given expiry date"""

    rider = models.ForeignKey(Rider, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, null=True, on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True)  # membership valid to this date
    category = models.CharField(max_length=10, choices=MEMBERSHIP_CATEGORY_CHOICES)
    add_on = models.BooleanField(default=False)

    # AusCycling validation fields
    last_validated = models.DateTimeField(
        null=True, blank=True, help_text="Last time membership was validated with AusCycling API"
    )
    validation_error = models.TextField(blank=True, default="", help_text="Last validation error message if any")

    def is_valid_on(self, check_date=None):
        """Check if membership is valid on the given date (default: today)"""
        if check_date is None:
            check_date = datetime.date.today()
        return self.date and self.date >= check_date

    class Meta:
        ordering = ["date", "category"]


class ClubRole(models.Model):
    """The name of a role that someone can hold in a club"""

    name = models.CharField("Name", max_length=100)

    def __str__(self):
        return self.name

    @property
    def shortname(self):
        return self.name.replace(" ", "").lower()


class UserRole(models.Model):
    """A role held by a person in a club, eg. president, handicapper, duty officer"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    role = models.ForeignKey(ClubRole, on_delete=models.CASCADE)

    def __str__(self):
        return "Role: " + "::".join((str(self.user), self.club.slug, self.role.name))


class RaceStaff(models.Model):
    """A person associated with a race in some role, eg. Commissaire, Duty Officer"""

    rider = models.ForeignKey(Rider, on_delete=models.CASCADE)
    race = models.ForeignKey(Race, related_name="officials", on_delete=models.CASCADE)
    role = models.ForeignKey(ClubRole, on_delete=models.CASCADE)

    def __str__(self):
        return "%s: %s" % (self.role.name, self.rider.user)

    class Meta:
        # should only assign each person once to a role in a race
        unique_together = (("rider", "race", "role"),)


class ClubGrade(models.Model):
    """A rider will be assigned a grade by a club, different
    clubs might have different grading"""

    class Meta:
        ordering = ["rider", "grade"]

    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE)
    grade = models.CharField("Grade", max_length=10)

    def __str__(self):
        return " - ".join((self.grade, str(self.rider), str(self.club)))

    def save(self, *args, **kwargs):
        """A rider can only have one grade for each club"""

        cg = ClubGrade.objects.filter(rider=self.rider, club=self.club)
        if self in cg:
            cg = list(cg)
            cg.remove(self)
        if cg is not None and len(cg) > 0:
            raise ValidationError("A rider can only have one grade for each club")

        super().save(*args, **kwargs)


class RaceResult(models.Model):
    """Model of a rider competing in a race"""

    class Meta:
        unique_together = (("race", "grade", "number"), ("race", "rider"))
        ordering = ["race", "grade", "place", "number"]

    def __str__(self):
        return "%s - %s-%d/%s, %s" % (str(self.race), self.grade, self.number or 0, self.place or "-", str(self.rider))

    race = models.ForeignKey(Race, on_delete=models.CASCADE)
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE)

    grade = models.CharField("Grade", max_length=10)
    usual_grade = models.CharField("Usual Grade", max_length=10)
    number = models.IntegerField("Bib Number", blank=True, null=True)  # unique together with grade

    place = models.IntegerField(
        "Place",
        blank=True,
        null=True,
        help_text="Enter finishing position (eg. 1-5), leave blank for a result out of the placings.",
    )
    dnf = models.BooleanField("DNF", default=False)


POINTSCORE_METHODS = (("WMCC", "WMCC"), ("LACC", "LACC"))


class PointScore(models.Model):
    """A pointscore is a series of races where points are accumulated"""

    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    points = models.CharField(
        "Points for larger races",
        max_length=100,
        default="7,6,5,4,3",
        validators=[validate_comma_separated_integer_list],
    )
    smallpoints = models.CharField(
        "Points for small races", max_length=100, default="5,4", validators=[validate_comma_separated_integer_list]
    )
    smallthreshold = models.IntegerField("Small Race Threshold", default=12)
    participation = models.IntegerField("Points for participation", default=2)
    races = models.ManyToManyField(Race, blank=True)
    method = models.CharField("Pointscore Method", default="WMCC", choices=POINTSCORE_METHODS, max_length=10)

    def __str__(self):
        return str(str(self.club) + " " + self.name)

    def current(self):
        """Does this pointscore contain current and future races"""

        startdate = datetime.date.today() - datetime.timedelta(days=8)
        return self.races.filter(date__gt=startdate).count() > 0

    def score(self, result, numberriders):
        """Calculate the points for this placing
        according to the Waratah CC pointscore rules

        Return a tuple: (points, reason)
        where reason is a string explaining the score
        """

        points = [7, 6, 5, 4, 3]
        smallpoints = [5, 4]
        participation = 2
        # is the rider eligible for promotion or riding down a grade
        promote = result.race.club.promotion(result.rider, when=result.race.date)

        if not result.place:
            return participation, "Participation"
        if promote:
            return participation, "Rider eligible for promotion"
        if result.grade > result.usual_grade:
            return participation, "Riding below normal grade"
        if numberriders < 6:
            # only 3 points to the winner
            if result.place == 1:
                return 3, "Placed 1 in small race < 6 riders"
            return participation, "Participation, small race < 6 riders"
        if numberriders <= 12:
            if result.place - 1 < len(smallpoints):
                return smallpoints[result.place - 1], "Placed %s in race <= 12 riders" % result.place
            return participation, "Participation, race <= 12 riders"
        else:
            if result.place - 1 < len(points):
                return points[result.place - 1], "Placed %s in race" % result.place
            return participation, "Participation"

    def get_points(self):
        "Return a list of integers from the points field"

        if not hasattr(self, "pointslist"):
            self.pointslist = [int(n.strip()) for n in self.points.split(",")]

        return self.pointslist

    def get_smallpoints(self):
        "Return a list of integers from the smallpoints field"

        if not hasattr(self, "smallpointslist"):
            self.smallpointslist = [int(n.strip()) for n in self.smallpoints.split(",")]

        return self.smallpointslist

    def tally(self, result):
        """Add points for this result to the tally"""

        # check that this race is part of this pointscore
        if self.races.filter(pk=result.race.pk).count() == 0:
            return

        number_in_grade = RaceResult.objects.filter(race=result.race, grade=result.grade).count()
        points, reason = self.score(result, number_in_grade)

        tally, created = PointscoreTally.objects.get_or_create(rider=result.rider, pointscore=self)

        reason += " : " + str(result.race)

        tally.add(points, reason)

    def tally_helpers(self, race):
        """Add points for helpers in this race to the pointscore"""

        # no points if there are no results for this race yet
        results = race.raceresult_set.all()
        if results.count() == 0:
            return

        for staff in RaceStaff.objects.filter(race=race):
            tally, created = PointscoreTally.objects.get_or_create(rider=staff.rider, pointscore=self)

            in_this_race = False
            if not created:
                # staff has some results already, check if they are in this race
                for reason in tally.audit_trail():
                    if str(race) in reason[1]:
                        in_this_race = True
            # if staff also got points for the race, they get a max
            # of 3 points for helping
            if in_this_race:
                points = 3 - tally.points
            else:
                points = 3

            if points > 0:
                reason = staff.role.name + " in race: " + str(race)
                tally.add(points, reason)

    def recalculate(self):
        """Recalculate all points from scratch"""

        PointscoreTally.objects.filter(pointscore=self).delete()

        for race in self.races.all().order_by("date"):
            for result in race.raceresult_set.all():
                self.tally(result)
            # add points for helpers in this race
            self.tally_helpers(race)

    def tabulate(self):
        """Generate a queryset of point tallys in order"""

        return self.results.all()

    def audit(self, rider):
        """Generate an audit report for this rider on this pointscore"""

        try:
            tally = PointscoreTally.objects.get(pointscore=self, rider=rider)
            return tally.audit_trail()
        except PointscoreTally.DoesNotExist:
            return []


class PointscoreTally(models.Model):
    """An entry in the pointscore table for a rider"""

    class Meta:
        ordering = ["-points", "eventcount"]

    rider = models.ForeignKey(Rider, on_delete=models.CASCADE)
    pointscore = models.ForeignKey(PointScore, related_name="results", on_delete=models.CASCADE)
    points = models.IntegerField(default=0)
    eventcount = models.IntegerField(default=0)
    audit = models.TextField(default="[]")

    def __str__(self):
        return str(self.rider) + " " + str(self.points)

    def _add_reason(self, points, reason):
        """Add a new reason to the audit trail"""

        reasons = self.audit_trail()

        reasons.append((points, reason))
        self.audit = json.dumps(reasons)
        self.save()

    def audit_trail(self):
        """Return a list of reasons justifying the
        points for this tally"""

        reasons = json.loads(self.audit)
        if reasons is None:
            reasons = []
        return reasons

    def add(self, points, reason):
        """Add points to the tally for a rider and record the reason"""

        self.points += points
        self._add_reason(points, reason)
        self.eventcount += 1
        self.save()
