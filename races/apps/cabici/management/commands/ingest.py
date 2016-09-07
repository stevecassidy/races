'''
Created on Apr 17, 2013

@author: steve
'''

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from races.apps.cabici.models import Club




class Command(BaseCommand):

    def handle(self, *args, **options):
        
        if len(args) > 0:
            clubs = []
            for arg in args:
                clubs.append(Club.objects.get(slug=arg))
        else:
            clubs = Club.objects.all()
        
        
        for club in clubs:
            try:
                (races, errors) = club.ingest()
                print "Club: ", club, "found", len(races), "races"
            except Exception as e:
                print "Club: ", club, "error:", e
            