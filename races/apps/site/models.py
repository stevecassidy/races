from django.db import models
from geoposition.fields import GeopositionField
from django.core.urlresolvers import reverse

class Club(models.Model):

    name = models.CharField(max_length=100)
    url = models.URLField(max_length=400)
    slug = models.SlugField()  # short name eg. WVCC, MWCC for use in URL
    contact = models.EmailField(null=True)
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class RaceCourse(models.Model):
    """A place where a race happens"""
    
    name = models.CharField(max_length=100)
    location = GeopositionField()

    def __unicode__(self):
        return self.name

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
)

class Race(models.Model):

    title = models.CharField(max_length=100)
    date = models.DateField()
    time = models.TimeField()
    club = models.ForeignKey(Club)
    url  = models.URLField(blank=True, max_length=400)
    location = models.ForeignKey(RaceCourse)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='d')
    description = models.TextField(default="")
    
    
    class Meta:
        ordering = ['date', 'time']

    def __unicode__(self):
        return unicode(self.club) + u": " + self.title + ", " + str(self.date)
    
    def get_absolute_url(self):
        return reverse('site:race', kwargs={'pk': self.id})
    