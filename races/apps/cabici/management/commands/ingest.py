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
                print("Club: ", club, "found", len(races), "races")
            except Exception as e:
                print("Club: ", club, "error:", e)
            