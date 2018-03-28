'''
Created on August 18, 2015

@author: steve
'''

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
import csv
from races.apps.cabici.usermodel import Rider
from races.apps.cabici.models import Club

class Command(BaseCommand):


    def add_arguments(self, parser):
        parser.add_argument('csvfile', nargs='+', type=str)


    def handle(self, *args, **options):

#        unknown, created = Club.objects.get_or_create(name="Unknown Club", slug="Unknown")
        Club.objects.all().delete()

        for csvfile in options['csvfile']:
            with open(csvfile, 'rU') as fd:
                reader = csv.DictReader(fd)

                for row in reader:
                    if row['email'] != '':
                        user, created = User.objects.get_or_create(email=row['email'], username=row['email'])
                        if created:
                            user.first_name = row['firstname']
                            user.last_name = row['lastname']
                            user.save()

                        # add rider info
                        if not hasattr(user, 'rider') and row['licenceno'] != "":
                            user.rider = Rider()
                            user.rider.licenceno = row['licenceno']
                            user.rider.gender = row['gender']

                            club,created = Club.objects.get_or_create(slug=row['club'], name=row['clubslug'])
                            user.rider.club = club

                            if 0:
                                clubs = Club.objects.filter(slug=row['club'])
                                if len(clubs) == 1:
                                    user.rider.club = clubs[0]
                                else:
                                    user.rider.club = unknown
                            user.rider.save()
