'''
Created on Apr 17, 2013

@author: steve
'''

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from races.ingest.csvingest import ingest
from races.apps.site.models import Club

class Command(BaseCommand):

    def handle(self, *args, **options):
        
        for csvfile in args:
            races = ingest(csvfile)
            
            for racedict in races:
                club = Club.objects.get(slug=racedict['club'])
                races = club.ingest_race_list([racedict])
                if races != []:
                    print races[0]
            