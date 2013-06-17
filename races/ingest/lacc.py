'''
Created on Apr 15, 2013

@author: steve
'''
LACC_URL = 'http://lacc.org.au/index.php?option=com_jevents&task=year.listevents&year=2013'

import urllib2
from urlparse import urljoin
from bs4 import BeautifulSoup
import datetime
import re
from races.apps.site.models import Club
from util import find_location


def ingest():
    """Return a list of dictionaries, one for each race"""

    #(lacc, created) = Club.objects.get_or_create(name="Lidcombe Auburn Cycling Club", slug='LACC', url="http://www.lacc.org.au/")

    webtext = urllib2.urlopen(LACC_URL).read()
    soup = BeautifulSoup(webtext, "lxml")
    events = soup.find_all('li', class_='ev_td_li')

    if len(events) == 0:
        print "No events found in LACC's web page"
        return []

    races = []

    for event in events:
        race = {}
        dateinfo = event.contents[0].strip()
        
        if '-' in dateinfo:
            dateinfo = dateinfo.split('-')[0].strip()
        
        #race['date'] = dateinfo
        # Saturday 21 December 2013 07:30 - 11:00
        try:
            d = datetime.datetime.strptime(dateinfo, "%A %d %B %Y %H:%M")
            race['date'] = d.strftime("%Y-%m-%d")
            race['time'] = datetime.time(d.hour, d.minute).strftime("%H:%M")
        except:
            try:
                d = datetime.datetime.strptime(dateinfo, "%A %d %B %Y")
                race['date'] = d.strftime("%Y-%m-%d")
                race['time'] = datetime.time(d.hour, d.minute).strftime("%H:%M")
            except:
                race['date'] = dateinfo
                race['time'] = "9:00"
        
        info = event.find_all('a', class_='ev_link_row')
        if len(info) > 0:
            race['url'] = urljoin(LACC_URL, info[0]['href'])
            race['title'] = info[0].text
        info = event.find_all('a', class_='ev_link_cat')
        if len(info) > 0:
            race['type'] = info[0].text
        
        # use title for location since it's generally in there
        race['location'] = race['title']
        
        if race['type'] != 'Meeting' and not 'Training' in race['type']:
            races.append(race)
            
    return races


