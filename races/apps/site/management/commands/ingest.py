'''
Created on Apr 17, 2013

@author: steve
'''

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from races.apps.site.models import Club




class Command(BaseCommand):

    def handle(self, *args, **options):
        
        for club in Club.objects.all():
            try:
                (races, errors) = club.ingest()
                print "Club: ", club, "found", len(races), "races"
            except Exception as e:
                print "Club: ", club, "error:", e
            