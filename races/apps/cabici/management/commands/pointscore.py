#!/usr/bin/python
#
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''
Created on August 18, 2015

@author: steve
'''

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from races.apps.cabici.usermodel import PointScore, PointscoreTally, Rider

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('name', nargs='?', type=str)
        parser.add_argument('--list', dest='list', action='store_const', const=True, default=False)

    def handle(self, *args, **options):

        if options['list']:
            pointscores = PointScore.objects.all()
            for p in pointscores:
                print(p)
        elif options['name']:
            pointscores = PointScore.objects.filter(name__contains=options['name'])

            if pointscores.count() == 0:
                print("No pointscore matches", options['name'])
            else:
                for p in pointscores:
                    print("Rescoring", p)
                    p.recalculate()

        else:
            pointscores = PointScore.objects.all()
            for p in pointscores:
                if p.current():
                    print("Rescoring", p)
                    p.recalculate()
                else:
                    print("Not rescoring", p)


