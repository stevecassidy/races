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
        (location, created) = RaceCourse.objects.get_or_create(name="Lansdowne Park", location="somewhere")
        for r in waratahs.ingest():
            (location, created) = RaceCourse.objects.get_or_create(name=r['location'], location="somewhere")
            race = Race(title=r['title'], date=r['date'], time=r['time'], club=club, location=location, url=r['url'])
            race.save()

        (club, created) = Club.objects.get_or_create(name="Paramatta Cycling Club", url="http://www.parramattacycling.com.au/")
        for r in csvingest.ingest():
            (location, created) = RaceCourse.objects.get_or_create(name=r['location'], location="somewhere")
            race = Race(title=r['title'], date=r['date'], time=r['time'], club=club, location=location, url=r['url'])
            race.save()