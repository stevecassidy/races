'''
Created on August 18, 2015

@author: steve
'''

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
import csv
from races.apps.site.usermodel import Rider
from races.apps.site.models import Race

class Command(BaseCommand):


    def add_arguments(self, parser):
        parser.add_argument('csvfile', nargs='+', type=str)


    def handle(self, *args, **options):

        racepk = 1

        for csvfile in options['csvfile']:

            race = Race.objects.get(pk=racepk)

            race.load_csv_results(csvfile)
