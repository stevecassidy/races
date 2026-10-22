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
from django.core.validators import validate_comma_separated_integer_list
from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import slugify

from races.apps.cabici.geoposition import GeopositionField


class Club(models.Model):

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
        constraints = [
            models.UniqueConstraint(fields=["slug"], name="cabici_club_slug_uniq"),
        ]

    def graded_riders(self):
        """Return a list of riders with grades assigned"""

        clubgrades = self.clubgrade_set.all()
        return [cg.rider for cg in clubgrades]

    def statistics(self):
        """Return a dictionary of statistics for this club"""

        today = datetime.date.today()

        dd = dict()
        dd["currentmembers"] = Membership.objects.filter(rider__club__exact=self, date__gte=today).count()
        # racing entitlement covers both racing categories
        dd["racemembers"] = Membership.objects.filter(
            rider__club__exact=self, date__gte=today, category__in=RACING_CATEGORIES
        ).count()
        dd["ridemembers"] = Membership.objects.filter(
            rider__club__exact=self, date__gte=today, category=MEMBERSHIP_CATEGORY_RIDE
        ).count()

        # roles
        dd["commissaires"] = Rider.objects.filter(club__exact=self).exclude(commissaire="").select_related("user")
        dd["roles"] = UserRole.objects.filter(club__exact=self).order_by("role").select_related("user", "role")

        return dd

    def recent_races(self):
        """Return a list of the most recent races
        most recent first"""

        return self.races.filter(date__lte=datetime.date.today()).order_by("-date")[:5]

    def grade(self, rider):
        """Get the current grade of this rider, if we have one
        return the string grade name or None if there is no grade recorded"""

        # get the rider's current grade with this club, if we have one
        grades = rider.clubgrade_set.filter(club=self)
        if len(grades) == 1:
            return grades[0].grade
        else:
            return None


class RaceCourse(models.Model):
    """A place where a race happens"""

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


def default_grading():
    """The default set of grades a new race runs."""

    return ["A", "A2", "B", "C", "D", "E", "F"]


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

    grading = models.JSONField(default=default_grading, blank=True)

    class Meta:
        ordering = ["date", "signontime"]
        indexes = [
            models.Index(fields=["date", "status"], name="cabici_race_date_status_idx"),
        ]

    def __str__(self):
        return self.title + ", " + str(self.date)

    def get_absolute_url(self):
        # the template race page is retired; point at the API resource so the
        # admin "View on site" shortcut does not raise NoReverseMatch (A3)
        return reverse("race-detail", kwargs={"pk": self.id})

    def duplicate(self):
        """Create a race just like this one with a slightly modified title
        but make it draft"""

        pass


# ---------------------------------------------------------------------------
# Merged from the former usermodel.py (C1). The Club/Race vs rider/membership
# split was arbitrary and forced function-level circular imports between the
# two modules; a single module removes them.
# ---------------------------------------------------------------------------

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
    dob = models.DateField("Date of Birth", null=True, blank=True)
    streetaddress = models.CharField("Address", max_length=100, default="", blank=True)
    suburb = models.CharField("Suburb", max_length=100, default="", blank=True)
    state = models.CharField("State", choices=STATE_CHOICES, max_length=10, default="NSW", blank=True)
    postcode = models.CharField("Postcode", max_length=4, default="", blank=True)
    phone = models.CharField("Phone", max_length=50, default="", blank=True)

    commissaire = models.CharField(
        "Commissaire Level",
        max_length=10,
        default="",
        blank=True,
        help_text="Empty if not a Commissaire, otherwise the level/qualifications, eg. 1, RT",
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
        # the template rider page is retired; point at the API resource so the
        # admin "View on site" shortcut does not raise NoReverseMatch (A3)
        return reverse("rider-detail", kwargs={"pk": self.pk})

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


# AusCycling membership categories, as the new provider names them.
# 'Race' and 'Club' entitle the holder to race; 'Ride' does not.
# Values are the stored form and must match what the provider exposes.
# (Replaces the previous tuple, which was inverted - value 'Ride' against label
# 'ride' - so admin writes were invisible to the category filters; A2.)
MEMBERSHIP_CATEGORY_RIDE = "Ride"
MEMBERSHIP_CATEGORY_CLUB = "Club"
MEMBERSHIP_CATEGORY_RACE = "Race"

MEMBERSHIP_CATEGORY_CHOICES = (
    (MEMBERSHIP_CATEGORY_RIDE, "Ride"),
    (MEMBERSHIP_CATEGORY_CLUB, "Club"),
    (MEMBERSHIP_CATEGORY_RACE, "Race"),
)

# the categories that permit racing
RACING_CATEGORIES = (MEMBERSHIP_CATEGORY_RACE, MEMBERSHIP_CATEGORY_CLUB)


class Membership(models.Model):
    """Membership of a club with a given expiry date"""

    rider = models.ForeignKey(Rider, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True)  # membership valid to this date
    category = models.CharField(max_length=10, choices=MEMBERSHIP_CATEGORY_CHOICES)
    add_on = models.BooleanField(default=False)

    # AusCycling validation fields
    last_validated = models.DateTimeField(
        null=True, blank=True, help_text="Last time membership was validated with AusCycling API"
    )
    validation_error = models.TextField(blank=True, default="", help_text="Last validation error message if any")

    @property
    def allows_racing(self):
        """Does this membership category entitle the holder to race?"""

        return self.category in RACING_CATEGORIES

    def is_valid_on(self, check_date=None):
        """Check if membership is valid on the given date (default: today)"""
        if check_date is None:
            check_date = datetime.date.today()
        return self.date and self.date >= check_date

    class Meta:
        ordering = ["date", "category"]
        constraints = [
            models.UniqueConstraint(fields=["rider", "club", "category", "date"], name="cabici_membership_uniq"),
        ]


class ClubRole(models.Model):
    """The name of a role that someone can hold in a club"""

    name = models.CharField("Name", max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["name"], name="cabici_clubrole_name_uniq"),
        ]

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

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "club", "role"], name="cabici_userrole_uniq"),
        ]

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
        constraints = [
            models.UniqueConstraint(fields=["rider", "club"], name="cabici_clubgrade_uniq"),
        ]

    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE)
    grade = models.CharField("Grade", max_length=10)

    def __str__(self):
        return " - ".join((self.grade, str(self.rider), str(self.club)))


class RaceResult(models.Model):
    """Model of a rider competing in a race"""

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["race", "rider"], name="cabici_raceresult_rider_uniq"),
            # only non-blank bibs must be unique: several riders may have no number
            models.UniqueConstraint(
                fields=["race", "grade", "number"],
                condition=models.Q(number__isnull=False),
                name="cabici_raceresult_bib_uniq",
            ),
        ]
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

    def __str__(self):
        return str(str(self.club) + " " + self.name)

    def current(self):
        """Does this pointscore contain current and future races"""

        startdate = datetime.date.today() - datetime.timedelta(days=8)
        return self.races.filter(date__gt=startdate).count() > 0

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
        constraints = [
            models.UniqueConstraint(fields=["pointscore", "rider"], name="cabici_tally_uniq"),
        ]
        indexes = [
            models.Index(fields=["pointscore", "-points"], name="cabici_tally_points_idx"),
        ]

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
