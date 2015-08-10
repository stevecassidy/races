from django.contrib.auth.models import User
from django.db import models

from races.apps.site.models import Club, Race

class Rider(models.Model):
    """Model for extra information associated with a club member (rider)
    minimal model with just enough information to support race results"""

    user = models.OneToOneField(User)
    licenceno = models.CharField("Licence Number", max_length=20)
    gender = models.CharField("Gender", max_length=2, choices=(("M", "M"), ("F", "F")))


    # could be that these are club specific fields
    #grade = models.CharField("Grade", max_length=2)
    #handicap = models.CharField("Handicap", max_length=5)

    club = models.ForeignKey(Club)


class RaceResult(models.Model):
    """Model of a rider competing in a race"""

    class Meta:
        unique_together = (('grade', 'number'), ('race', 'rider'))
        ordering = ['race', 'grade', 'number']

    def __unicode__(self):
        return "%s - %s Grade, %s" % (str(self.race), self.grade, str(self.rider))

    race = models.ForeignKey(Race)
    rider = models.ForeignKey(User)

    grade = models.CharField("Grade", max_length="10")
    number = models.IntegerField("Bib Number")  # unique together with grade

    place = models.IntegerField("Place", default=0, help_text="Enter finishing position (eg. 1-5) or 0 for a result out of the placings.")
    dnf = models.BooleanField("DNF", default=False)
