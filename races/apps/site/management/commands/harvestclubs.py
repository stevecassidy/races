'''
Created on August 18, 2015

@author: steve
'''

from bs4 import BeautifulSoup
from urllib2 import urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from races.apps.site.models import Club

NSW_CLUBS_URL = 'http://www.nsw.cycling.org.au/Contact/Club-Pages/'

class Command(BaseCommand):


    def handle(self, *args, **options):

        Club.objects.all().delete()


        h = urlopen(NSW_CLUBS_URL)
        page = h.read()
        h.close()
        bs = BeautifulSoup(page, 'lxml')

        clubs = [(a.text, a['href']) for a in bs.find(id='dnn_ctl03').find(class_='pane').find_all('a')]

        for clubname, url in clubs:
            h = urlopen(url)
            page = h.read()
            h.close()
            bs = BeautifulSoup(page, 'lxml')

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
            print club
