'''
Created on Apr 15, 2013

@author: steve
'''

import datetime, time

year = datetime.date.fromtimestamp(time.time()).year
LACC_URL = 'http://lacc.org.au/index.php?option=com_jevents&task=year.listevents&year=%s' % year

import urllib.request, urllib.error, urllib.parse
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import re
import hashlib


def ingest():
    """Return a list of dictionaries, one for each race"""

    #(lacc, created) = Club.objects.get_or_create(name="Lidcombe Auburn Cycling Club", slug='LACC', url="http://www.lacc.org.au/")
    
    try:
        req = urllib.request.Request(LACC_URL)
        req.add_header('User-Agent', 'cabici/1.0 event harvester http://cabici.net/')
        h = urllib.request.urlopen(req)
        webtext = h.read()
        h.close()
    except urllib.error.HTTPError as e:
        content = e.read()
        if e.code == 418:
            webtext = content
        else:  
            return ([], "Error reading icalendar URL:" + content[1:20])
    except urllib.error.URLError as e:
        return ([], "Bad URL: " + self.icalurl)
        

    soup = BeautifulSoup(webtext, "lxml")
    events = soup.find_all('li', class_='ev_td_li')
    
    
    if len(events) == 0:
        print("No events found in LACC's web page")
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
        
        race['hash'] = hashlib.sha1(str(race)).hexdigest()
        
        if race['type'] != 'Meeting' and not 'Training' in race['type']:
            races.append(race)
            
    return races


