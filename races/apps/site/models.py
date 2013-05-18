from django.db import models
from geoposition.fields import GeopositionField

class Club(models.Model):

    name = models.CharField(max_length=100)
    url = models.URLField()

    def __unicode__(self):
        return self.name

class RaceCourse(models.Model):

    name = models.CharField(max_length=100)
    location = GeopositionField()

    def __unicode__(self):
        return self.name


class Race(models.Model):

    title = models.CharField(max_length=100)
    date = models.DateField()
    time = models.TimeField()
    club = models.ForeignKey(Club)
    url  = models.URLField(blank=True)
    location = models.ForeignKey(RaceCourse)

    class Meta:
        ordering = ['date', 'time']

    def __unicode__(self):
        return unicode(self.club) + u": " + self.title + ", " + str(self.date)