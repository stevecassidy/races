'''
Created on Apr 17, 2013

@author: steve
'''

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from races.apps.site.models import Race, RaceCourse, Club
import races.ingest.waratahs as waratahs
import races.ingest.csvingest as csvingest
import races.ingest.lacc as laccm
import races.ingest.penrith as penrith
from races.ingest import find_location


def ingest_club(races, club=None):
    
    for r in races:

        try:
            location = find_location(r['location'])
            if club == None:
                thisclub = Club.objects.get(slug=r['club'])
            else:
                thisclub = club
            
            if len(r['title']) > 100:
                r['title'] = r['title'][:99]
            
            race = Race(title=r['title'], date=r['date'], time=r['time'], club=thisclub, location=location, url=r['url'])
            race.save()
        except Exception as e:
            print "problem with", club, "race: ", r
            print e


class Command(BaseCommand):

    def handle(self, *args, **options):
        
        (wmcc, created) = Club.objects.get_or_create(name="Waratah Masters Cycling Club", slug='WMCC', url="http://www.waratahmasters.com.au/")
        (lacc, created) = Club.objects.get_or_create(name="Lidcombe Auburn Cycling Club", slug='LACC', url="http://www.lacc.org.au/")
        (parra, created) = Club.objects.get_or_create(name="Parramatta Cycling Club", slug='Parramatta', url="http://www.parramattacycling.com.au/")
        (suvelo, created) = Club.objects.get_or_create(name="SUVelo", slug="SUVelo", url="http://www.suvelo.com.au/")
        (bankstown, created) = Club.objects.get_or_create(name="Bankstown Sports Cycling Club", slug="Bankstown", url="http://bankstownsportscycling.com/")
        (penrithcc, created) = Club.objects.get_or_create(name="Penrith Cycling Club", slug="Penrith", url="http://www.penrithcyclingclub.com/")
        (stgeorgecc, created) = Club.objects.get_or_create(name="St George Cycling Club", slug="StGeorge", url="http://www.stgeorge.cycling.org.au/")
        (marconi, created) = Club.objects.get_or_create(name="Marconi Cycling Club", slug="Marconi", url="http://www.marconicyclingclub.com/")
  
        Race.objects.all().delete()
        
        ingest_club(waratahs.ingest(), wmcc)
        ingest_club(laccm.ingest(), lacc)
        ingest_club(penrith.ingest(), penrithcc)
        ingest_club(csvingest.ingest())

            