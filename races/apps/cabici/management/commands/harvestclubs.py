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

from bs4 import BeautifulSoup
from urllib.request import urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from races.apps.cabici.models import Club

NSW_CLUBS_URL = 'http://www.nsw.cycling.org.au/Contact/Club-Pages/'


class Command(BaseCommand):

    def handle(self, *args, **options):

        Club.objects.all().delete()

        h = urlopen(NSW_CLUBS_URL)
        page = h.read()
        h.close()
        bs = BeautifulSoup(page, 'html.parser')

        clubs = [(a.text, a['href']) for a in bs.find(id='dnn_ctl03').find(class_='pane').find_all('a')]

        for clubname, url in clubs:
            h = urlopen(url)
            page = h.read()
            h.close()
            bs = BeautifulSoup(page, 'html.parser')

            try:
                jersey =  bs.find(class_='pane_layout_right_sidebar').find('img')['src']
            except:
                jersey = None

            try:
                website = bs.find(class_='pane_layout_right_sidebar').contents[1].find('a', class_="action-btn")['href']
            except:
                website = url


            slug = clubname.replace(' ', '')
            club = Club(name=clubname, slug=slug, website=website)
            club.save()
            print(club)
