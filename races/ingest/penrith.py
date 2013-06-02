'''
Created on Apr 15, 2013

@author: steve
'''
CALENDAR_URL = 'http://penrithp.ipower.com/calendar.php'
LOCATION = "Penrith Regatta Centre"

import urllib2
from bs4 import BeautifulSoup
import datetime
import re


def ingest():
    """Return a list of dictionaries, one for each race"""

    webtext = urllib2.urlopen(CALENDAR_URL).read()
    soup = BeautifulSoup(webtext, "lxml")
    tables = soup.find_all('table')

    if len(tables) < 6:
        print "No events found in Penrith's web page"
        return []
    
    cal_table = tables[5]

    events = cal_table.find_all('tr')

    races = []

    for event in events:
        race = {}
        cells = event.find_all('td', class_='calendarRaces')

        if len(cells) == 0:
            continue
                
        dateinfo = cells[0].string.strip()
        info = cells[1].string.strip()
        
        # 18/02/2013
        try:
            d = datetime.datetime.strptime(dateinfo, "%d/%m/%Y")
            race['date'] = d.strftime("%Y-%m-%d")
        except:
            print "Unknown date for Penrith race: '%s' " % dateinfo
        
        
        race['url'] = CALENDAR_URL
        
        if 'Winter' in info:
            race['time'] = "7:30"
        elif 'Summer' in info:
            race['time'] = "18:00"
        else:
            race['time'] = "7:30"
        
        race['title'] = info
        race['location'] = LOCATION
        
        races.append(race)
        
    return races



if __name__ == '__main__':

    races = ingest()
    #print races[0]
    
    for race in ingest():
        print "RACE: ", race
        