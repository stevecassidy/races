'''
Created on August 18, 2015

@author: steve
'''

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
import csv
import random

from races.apps.site.usermodel import Rider, RaceResult
from races.apps.site.models import Race

class Command(BaseCommand):


    def handle(self, *args, **options):

        # generate some randomised race results
        # for each grade, choose some riders to ride the grade
        # for each race, choose the first five riders, create results

        riders = list(Rider.objects.all())
        random.shuffle(riders)
        k = len(riders)/4
        grades = {'A': [], 'B': [], 'C': [], 'D': []}

        for grade in grades.keys():
            for i in range(k-1):
                grades[grade].append(riders.pop())


        for race in Race.objects.all():
            for grade in grades.keys():
                who = random.sample(grades[grade], random.randint(k/2, k-1))
                number = 0
                place = 0
                for rider in who:
                    number += 1
                    place += 1
                    if place <= 5:
                        result = RaceResult(race=race, rider=rider, grade=grade, number=number, place=place)
                    else:
                        result = RaceResult(race=race, rider=rider, grade=grade, number=number, place=0)
                    result.save()
