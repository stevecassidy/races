'''
Created on August 18, 2015

@author: steve
'''

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from races.apps.cabici.usermodel import PointScore, Rider, PointscoreTally
from races.apps.cabici.models import Race

class Command(BaseCommand):


    def add_arguments(self, parser):
        parser.add_argument('--rider', dest='rider' )
        parser.add_argument('--merge', dest='merge')
        parser.add_argument('--search', dest='search')

    def handle(self, *args, **options):

        if options['search']:
            riders = Rider.objects.filter(user__last_name__icontains=options['search'])
            if riders.count() == 0:
                print("No riders matched")
            else:
                for rider in riders:
                    print(rider.user.pk, rider)
        else:
            if options['rider']:

                rider = Rider.objects.get(user__id__exact=options['rider'])
                print("Rider:", rider)

                if options['merge']:
                    mergerider = Rider.objects.get(user__id__exact=options['merge'])
                    print("Merge with: ", mergerider)

                    mergeresults = mergerider.raceresult_set.all()
                    for result in mergeresults:
                        print(result)

                    print("\nAll race results for '"+str(mergerider)+"' will be moved over to '"+str(rider)+"'")
                    response = input("Continue? [y/N]")

                    if response is 'y':
                        for result in mergeresults:
                            result.rider = rider
                            result.save()

                        mergerider.user.delete()
                        mergerider.delete()
                        
                        print("\nResults for ", rider)
                        for result in rider.raceresult_set.all():
                            print(result)

                    else:
                        print("ok, no action")
