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
from django.contrib.auth.models import User
import csv
from races.apps.cabici.usermodel import Rider
from races.apps.cabici.models import Race

class Command(BaseCommand):


    def add_arguments(self, parser):
        parser.add_argument('csvfile', nargs='+', type=str)


    def handle(self, *args, **options):

        racepk = 1

        for csvfile in options['csvfile']:

            race = Race.objects.get(pk=racepk)

            race.load_csv_results(csvfile)
