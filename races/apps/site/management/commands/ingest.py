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

class Command(BaseCommand):

    def handle(self, *args, **options):
        
        (wmcc, created) = Club.objects.get_or_create(name="Waratah Masters Cycling Club", slug='WMCC', url="http://www.waratahmasters.com.au/")
        (lacc, created) = Club.objects.get_or_create(name="Lidcombe Auburn Cycling Club", slug='LACC', url="http://www.lacc.org.au/")
        (parra, created) = Club.objects.get_or_create(name="Parramatta Cycling Club", slug='PCC', url="http://www.parramattacycling.com.au/")
        (suvelo, created) = Club.objects.get_or_create(name="SUVelo", slug="SUVELO", url="http://www.suvelo.com.au/")
        (bankstown, created) = Club.objects.get_or_create(name="Bankstown", slug="BSCC", url="http://bankstownsportscycling.com/")
        (penrithcc, created) = Club.objects.get_or_create(name="Penrith Cycling Club", slug="PenCC", url="http://www.penrithcyclingclub.com/")
        (stgeorgecc, created) = Club.objects.get_or_create(name="St George Cycling Club", slug="STGEORGE", url="http://www.stgeorge.cycling.org.au/")
 
        Race.objects.all().delete()
        
        for r in waratahs.ingest():
            location = find_location(r['location'])

            try:
                race = Race(title=r['title'], date=r['date'], time=r['time'], club=wmcc, location=location, url=r['url'])
                race.save()
            except Exception as e:
                print "problem with WVCC race: ", r
                print e


        location = find_location('Lansdowne Park')
        for r in laccm.ingest():
            
            try:
                race = Race(title=r['title'], date=r['date'], time=r['time'], club=lacc, url=r['url'], location=location)
                race.save()
            except Exception as e:
                print "Problem with LACC race: ", r
                print e
        
        location = find_location('Penrith Regatta Centre')
        for r in penrith.ingest():
            
            try:
                race = Race(title=r['title'], date=r['date'], time=r['time'], club=penrithcc, url=r['url'], location=location)
                race.save()
            except Exception as e:
                print "Problem with Penrith race: ", r
                print e
        

        for r in csvingest.ingest():
            location = find_location(r['location'])
            
            club = Club.objects.get(name=r['club'])
 
            race = Race(title=r['title'], date=r['date'], time=r['time'], club=club, location=location, url=r['url'])
            race.save()
            