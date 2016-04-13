from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.urlresolvers import reverse, reverse_lazy

import datetime
from djangoyearlessdate.models import YearField

from races.apps.site.models import Club, Race
import csv

def save_rider(backend, user, response, *args, **kwargs):
    """Create a rider object for a user, part of the
    social authentication flow. Adds fields from the Strava
    auth response to the Rider object."""

    if backend.name == 'strava':
        try:
            rider = user.rider
        except ObjectDoesNotExist:
            rider = Rider(user=user)

        rider.gender = response.get('sex')
        rider.save()



STATE_CHOICES = (('ACT', 'Australian Capital Territory'),
                 ('NSW', 'New South Wales'),
                 ('NT', 'Northern Territory'),
                 ('QLD', 'Queensland'),
                 ('SA', 'South Australia'),
                 ('TAS', 'Tasmania'),
                 ('VIC', 'Victoria'),
                 ('WA', 'Western Australia'))


class Rider(models.Model):
    """Model for extra information associated with a club member (rider)
    minimal model with just enough information to support race results"""

    user = models.OneToOneField(User)
    licenceno = models.CharField("Licence Number", max_length=20)
    gender = models.CharField("Gender", max_length=2, choices=(("M", "M"), ("F", "F")))
    dob = models.DateField("Date of Birth", default=datetime.date(1970, 1, 1))
    streetaddress = models.CharField("Address", max_length=100, default='')
    suburb = models.CharField("Suburb", max_length=100, default='')
    state = models.CharField("State", choices=STATE_CHOICES, max_length=10, default='NSW')
    postcode = models.CharField("Postcode", max_length=4, default='')
    phone = models.CharField("Phone", max_length=20, default='')

    emergencyname = models.CharField("Emergency Contact Name", max_length=100, default='')
    emergencyphone = models.CharField("Emergency Contact Phone", max_length=20, default='')
    emergencyrelationship =  models.CharField("Emergency Contact Relationship", max_length=20, default='')

    official = models.BooleanField("Club Official", default=False)

    club = models.ForeignKey(Club, null=True)

    def get_absolute_url(self):

        return reverse('rider', kwargs={'pk': self.user.pk})

    def __unicode__(self):
        return self.user.first_name + " " + self.user.last_name

    def performancereport(self):
        """Generate a rider performance report"""

        # number of races
        # number of wins/places in last 12 months
        # wins in grade
        # places in grade

        info = dict()

        today = datetime.date.today()
        startdate = today - datetime.timedelta(days=365)
        info['recent'] = self.raceresult_set.filter(place__lt=5, race__date__gt=startdate)
        info['places'] = info['recent'].filter(place__gt=1).count()
        info['wins'] = info['recent'].filter(place__exact=1).count()

        return info


class Membership(models.Model):
    """Membership of a club in a given year"""

    rider = models.ForeignKey(Rider)
    club = models.ForeignKey(Club, null=True)
    year = YearField(null=True, blank=True)


class UserRole(models.Model):
    """A role held by a person in a club, eg. president, handicapper, duty officer
    """

    user = models.ForeignKey(User)
    club = models.ForeignKey(Club)
    role = models.CharField("Role", max_length=50)


class ClubGrade(models.Model):
    """A rider will be assigned a grade by a club, different
    clubs might have different grading"""

    class Meta:
        ordering = ['rider', 'grade']

    club = models.ForeignKey(Club)
    rider = models.ForeignKey(Rider)
    grade = models.CharField("Grade", max_length=10)

    def __unicode__(self):
        return " - ".join((self.grade, unicode(self.rider), unicode(self.club)))

    def save(self, *args, **kwargs):
        """A rider can only have one grade for each club"""

        cg = ClubGrade.objects.filter(rider=self.rider, club=self.club)
        if len(cg) > 0:
            raise ValidationError("A rider can only have one grade for each club")

        super(ClubGrade, self).save(*args, **kwargs)




class RaceResult(models.Model):
    """Model of a rider competing in a race"""

    class Meta:
        unique_together = (('race', 'grade', 'number'), ('race', 'rider'))
        ordering = ['race', 'grade', 'place', 'number']

    def __unicode__(self):
        return "%s - %s-%d/%s, %s" % (str(self.race), self.grade, self.number or 0, self.place or '-', str(self.rider))

    race = models.ForeignKey(Race)
    rider = models.ForeignKey(Rider)

    grade = models.CharField("Grade", max_length=10)
    number = models.IntegerField("Bib Number", blank=True, null=True)  # unique together with grade

    place = models.IntegerField("Place", blank=True, null=True, help_text="Enter finishing position (eg. 1-5), leave blank for a result out of the placings.")
    dnf = models.BooleanField("DNF", default=False)

    def pointscores(self):
        """Return a list of ResultPoints from all PointScores this race is part of"""

        return self.resultpoints_set.all()




class PointScore(models.Model):
    """A pointscore is a series of races where points are accumulated"""

    club = models.ForeignKey(Club)
    name = models.CharField(max_length=100)
    points = models.CommaSeparatedIntegerField("Points for larger races", max_length=100, default="7,6,5,4,3")
    smallpoints = models.CommaSeparatedIntegerField("Points for small races", max_length=100, default="5,3")
    smallthreshold = models.IntegerField("Small Race Threshold", default=12)
    participation = models.IntegerField("Points for participation", default=2)
    races = models.ManyToManyField(Race, blank=True)  # a pointscore contains many races and a race can be in many pointscores

    def __unicode__(self):
        return unicode(unicode(self.club) + " " + self.name)

    def get_points(self):
        "Return a list of integers from the points field"

        if not hasattr(self, 'pointslist'):

            self.pointslist = [int(n.strip()) for n in self.points.split(',')]

        return self.pointslist

    def get_smallpoints(self):
        "Return a list of integers from the smallpoints field"

        if not hasattr(self, 'smallpointslist'):
            self.smallpointslist = [int(n.strip()) for n in self.smallpoints.split(',')]

        return self.smallpointslist

    def score(self, place, numberriders):
        """Return the points corresponding to this place in the race
        and this number of riders"""

        if place is None:
            return self.participation

        if numberriders < self.smallthreshold:
            if place-1 < len(self.get_smallpoints()):
                return self.get_smallpoints()[place-1]
            else:
                return self.participation

        else:
            if place-1 < len(self.get_points()):
                return self.get_points()[place-1]
            else:
                return self.participation

    def tabulate(self):
        """Generate a table of points per rider for this pointscore"""

        self.calculate()

        table = dict()
        for race in self.races.all():
            for result in race.raceresult_set.all():
                points = ResultPoints.objects.get(pointscore=self, result=result)
                if result.rider.pk in table:
                    table[result.rider.pk] += points.points
                else:
                    table[result.rider.pk] = points.points
        pointstable = []
        for pk, points in table.items():
            pointstable.append({'rider': Rider.objects.get(pk=pk), 'points': points})

        # sort by points

        return sorted(pointstable, cmp=lambda a,b: cmp(b['points'],a['points']))

    def calculate(self):
        """Calculate the points for all riders in all races we have results for"""

        for race in self.races.all():
            for result in race.raceresult_set.all():
                rp = ResultPoints.create(result, self)


class ResultPoints(models.Model):
    """Points from a pointscore for a race result"""

    result = models.ForeignKey(RaceResult)
    pointscore = models.ForeignKey(PointScore)
    points = models.IntegerField()

    @classmethod
    def create(cls, result, pointscore):
        """Create a ResultPoints instance, fill in the points field
        if there is already an instance for this result, just recalculate
        the score"""

        number_in_grade = RaceResult.objects.filter(race=result.race, grade=result.grade).count()
        points = pointscore.score(result.place, number_in_grade)

        try:
            rp = ResultPoints.objects.get(result=result, pointscore=pointscore)
            rp.points = points
        except:
            rp = cls(result=result, pointscore=pointscore, points=points)
        rp.save()

        return rp
