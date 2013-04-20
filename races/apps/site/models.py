from django.db import models


class Club(models.Model):

    name = models.CharField(max_length=100)
    url = models.URLField()

    def __unicode__(self):
        return self.name

class RaceCourse(models.Model):

    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)

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