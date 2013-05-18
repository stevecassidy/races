'''
Created on Apr 17, 2013

@author: steve
'''

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from races.apps.site.models import Race, RaceCourse, Club
import races.ingest.waratahs as waratahs
import races.ingest.csvingest as csvingest

class Command(BaseCommand):

    def handle(self, *args, **options):

        Race.objects.all().delete()
        (club, created) = Club.objects.get_or_create(name="Waratah Masters Cycling Club", url="http://www.waratahmasters.com.au/")
        print "made club", club
        for r in waratahs.ingest():
            print "RACE:", r
            (location, created) = RaceCourse.objects.get_or_create(name=r['location'])

            race = Race(title=r['title'], date=r['date'], time=r['time'], club=club, location=location, url=r['url'])
            race.save()

        (parra, created) = Club.objects.get_or_create(name="Parramatta Cycling Club", url="http://www.parramattacycling.com.au/")
        (suvelo, created) = Club.objects.get_or_create(name="SUVelo", url="http://www.suvelo.com.au/")
        (bankstown, created) = Club.objects.get_or_create(name="Bankstown", url="http://bankstownsportscycling.com/")
        for r in csvingest.ingest():
            (location, created) = RaceCourse.objects.get_or_create(name=r['location'])
            location.location="-33.8, 151.22"
            location.save()
            
            club = Club.objects.get(name=r['club'])
 
            race = Race(title=r['title'], date=r['date'], time=r['time'], club=club, location=location, url=r['url'])
            race.save()
            