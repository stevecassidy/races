from django.db import models
from geoposition.fields import GeopositionField
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from importlib import import_module

import icalendar
from urllib2 import urlopen, HTTPError
import datetime
import hashlib
import ngram


class Club(models.Model):

    name = models.CharField(max_length=100)
    url = models.URLField(max_length=400)
    slug = models.SlugField()  # short name eg. WVCC, MWCC for use in URL
    contact = models.EmailField(blank=True)
    icalurl = models.URLField(max_length=400, blank=True, default='')
    icalpatterns = models.CharField(max_length=100, blank=True, default='')
    
    def __unicode__(self):
        return self.slug
    
    class Meta:
        ordering = ['name']
        
    
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
            error = ''
        
        return (races, error)
        
        
        
        
    def ingest_ical(self):
        """Import races from an icalendar feed
        Return a tuple (races, errormsg) where races is a list
        of Race instances and errormsg is an error message if any."""
    
        if self.icalurl == '':
            return ([], "No icalendar URL")
    
        try:    
            h = urlopen(self.icalurl)
            ical_text = h.read()
            h.close()
        except HTTPError as e:
            content = e.read()
            return ([], "Error reading icalendar URL:" + content)
        
        try:
            cal = icalendar.Calendar.from_ical(ical_text)
        except ValueError:
            return ([], "Error reading icalendar file")
        
        patterns = [p.strip() for p in self.icalpatterns.split(',')]

        races = []
        for component in cal.walk():  
            
            if component.has_key('DTSTART'):
                start = component.decoded('DTSTART')
                title = component.get('SUMMARY', '')
                description = component.get('DESCRIPTION', '')
                url = component.get('URL', '')
                
                # CCCC at least has quoted chars in the description
                # this removes them
                description = icalendar.parser.unescape_char(description)
                description = description.replace(r'\:', r':')
                
                
                
                if any([title.find(p) >- 0 for p in patterns]):
                
                    calstring = "%s%s%s%s" % (str(start), title, description, url)
                    # need to fix encoding to ascii before calculating the hash
                    calstring = calstring.encode('ascii', errors='replace')
                    racehash = hashlib.sha1(calstring).hexdigest()

                    # do we already have this race?
                    if Race.objects.filter(hash=racehash).count() == 0:
                        
                
                        location = RaceCourse.objects.find_location(title)
                        
                        if type(start) == datetime.datetime:
                        
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
                                    url=url, 
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
                                time=r['time'], 
                                club=self, 
                                location=location,
                                url=r['url'],
                                hash=r['hash'])
                    
                    race.save()
                    racelist.append(race)
                except ValidationError as e:
                    # report the error?
                    errors.append(str(e))

        return (racelist, errors)
    
class RaceCourseManager(models.Manager):


    def find_location(self, name):
        """Find a RaceCourse using an approximate match to
        the given name, return the best matching RaceCourse instance"""
        
        courses = self.all()
        
        ng = ngram.NGram(courses, key=str)
        
        location = ng.finditem(name)
    
        if location == None:
            location = self.get(name="Unknown")
            
        return location

class RaceCourse(models.Model):
    """A place where a race happens"""
    
    objects = RaceCourseManager()
    
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
    description = models.TextField(default="", blank=True)
    hash = models.CharField(max_length=100, blank=True)
    
    
    class Meta:
        ordering = ['date', 'time']

    def __unicode__(self):
        return unicode(self.club) + u": " + self.title + ", " + str(self.date)
    
    def get_absolute_url(self):
        return reverse('site:race', kwargs={'pk': self.id, 'slug': self.club.slug})
    
    def duplicate(self):
        """Create a race just like this one with a slightly modified title 
        but make it draft"""
        
        pass
    
    
    