'''
Created on August 18, 2015

@author: steve
'''

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
import csv
from races.apps.cabici.usermodel import PointScore, Rider, PointscoreTally
from races.apps.cabici.models import Race

class Command(BaseCommand):


    def add_arguments(self, parser):
        parser.add_argument('name', nargs='?', type=str)
        parser.add_argument('--rider', dest='rider' )
        parser.add_argument('--list', dest='list', action='store_const', const=True, default=False)
        parser.add_argument('--rescore', dest='rescore', action='store_const', const=True, default=False)

    def handle(self, *args, **options):

        if options['list']:
            ps = PointScore.objects.all()
            for p in ps:
                print p
        else:
            ps = PointScore.objects.filter(name__contains=options['name'])
            if ps.count() == 0:
                print "No pointscore matches", options['name']
            elif ps.count() == 1:
                if options['rescore']:
                    print "Rescoring ", ps[0]
                    ps[0].recalculate()
                elif options['rider']:
                    riders = Rider.objects.filter(user__last_name__icontains=options['rider'])
                    if riders.count() == 0:
                        print "Rider %s not found" % options['rider']
                        exit()

                    for rider in riders:
                        print rider
                        try:
                            tally = PointscoreTally.objects.get(pointscore=ps[0], rider=rider)
                            print "Total: ", tally.points
                            audit = ps[0].audit(rider)
                            for reason in sorted(audit):
                                print '\t', reason[0], reason[1]
                        except:
                            print "\tNo Points"
            else:
                print "more than one pointscore matches", options['name'], ":"
                for p in ps:
                    print p
