'''
Created on August 18, 2015

@author: steve
'''

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
import csv
import random

from races.apps.cabici.usermodel import Rider, RaceResult, ClubGrade
from races.apps.cabici.models import Race

class Command(BaseCommand):


    def handle(self, *args, **options):

        # generate some randomised race results
        # for each grade, choose some riders to ride the grade
        # for each race, choose the first five riders, create results

        RaceResult.objects.all().delete()
        ClubGrade.objects.all().delete()

        riders = list(Rider.objects.all())
        random.shuffle(riders)
        k = len(riders)/4
        grades = {'A': [], 'B': [], 'C': [], 'D': []}

        for grade in list(grades.keys()):
            for i in range(k-1):
                rider = riders.pop()
                grades[grade].append(rider)



        for race in Race.objects.all():
            for grade in list(grades.keys()):
                who = random.sample(grades[grade], random.randint(k/2, k-1))
                numbers = list(range(100))
                random.shuffle(numbers)
                place = 0
                for rider in who:
                    place += 1
                    if place <= 5:
                        result = RaceResult(race=race, rider=rider, grade=grade, number=numbers.pop(), place=place)
                    else:
                        result = RaceResult(race=race, rider=rider, grade=grade, number=numbers.pop(), place=0)
                    result.save()

                    grading, ignore = ClubGrade.objects.get_or_create(rider=rider, club=race.club, grade=grade)
