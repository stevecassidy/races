from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ObjectDoesNotExist

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



class Rider(models.Model):
    """Model for extra information associated with a club member (rider)
    minimal model with just enough information to support race results"""

    user = models.OneToOneField(User)
    licenceno = models.CharField("Licence Number", max_length=20)
    gender = models.CharField("Gender", max_length=2, choices=(("M", "M"), ("F", "F")))

    official = models.BooleanField("Club Official", default=False)

    # could be that these are club specific fields
    #grade = models.CharField("Grade", max_length=2)
    #handicap = models.CharField("Handicap", max_length=5)

    club = models.ForeignKey(Club, null=True)

    def __unicode__(self):
        return self.user.first_name + " " + self.user.last_name

class RaceResult(models.Model):
    """Model of a rider competing in a race"""

    class Meta:
        unique_together = (('race', 'grade', 'number'), ('race', 'rider'))
        ordering = ['race', 'grade', 'place', 'number']

    def __unicode__(self):
        return "%s - %s-%d/%s, %s" % (str(self.race), self.grade, self.number, self.place or '-', str(self.rider))

    race = models.ForeignKey(Race)
    rider = models.ForeignKey(Rider)

    grade = models.CharField("Grade", max_length="10")
    number = models.IntegerField("Bib Number")  # unique together with grade

    place = models.IntegerField("Place", blank=True, null=True, help_text="Enter finishing position (eg. 1-5), leave blank for a result out of the placings.")
    dnf = models.BooleanField("DNF", default=False)
