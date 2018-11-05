'''
Created on Apr 15, 2013

@author: steve
'''
WARATAH_URL = 'http://www.waratahmasters.com.au/eventsmenu.cfm'

import urllib.request, urllib.error, urllib.parse
from bs4 import BeautifulSoup
import datetime
import re
import hashlib


def parse_times(times):
    """Given a time string from the web page, return a list of
    pairs (time, grades)"""

    # 7.45am C/F-9am A/B
    # E/F-7.30am B/D-8.15am A/C-9.15am
    # 7:00am all grades
    # 9.00am-2.00pm
    # 8.00am All Grades
    

    if times == "7.45am C/F-9am A/B":
        return [('07:45', 'C/F Grade'), ('09:00', 'A/B Grade')]
    elif times == 'E/F-7.30am B/D-8.15am A/C-9.15am':
        return [('07:30', 'E/F Grade'), ('08:15', 'B/D Grade'), ('09:15', 'A/C Grade')]
    elif times == '7:00am all grades':
        return [('07:00', '')]
    elif times == '8.00am All Grades':
        return [('08:00', '')]
    elif times == '9.00am-2.00pm':
        return [('09:00', '')]
    else:
        print("Unkown time format: ", times)
        return []


    
    
def parse_web_text(webtext):
    """Parse the content scraped from the Waratahs web page and return
    a list of dictionaries, one for each race"""
    
    soup = BeautifulSoup(webtext, "lxml")
    tables = soup.find_all('table', class_='raceroster_table')

    if len(tables) == 0:
        print("No table found in Waratah's web page")
        return []
    
    table = tables[0]

    
    races = []

    for row in table.find_all('tr'):
        
        cells = row.find_all('td')
        if len(cells) == 4:
            dateinfo =  [c for c in cells[0].children]
            times = parse_times(dateinfo[2].strip())

            date = datetime.datetime.strptime(dateinfo[0], "%d %b %Y")

            title = cells[1]('strong')[0].string

            for time in times:

                race = {}
                race['date'] = date.date().isoformat()
                race['time'] = time[0]
                race['title'] = title + " " + time[1]
                race['id'] = str(cells[1]('span')[0].string)
                race['location'] = str(cells[2].string)
                race['url'] = WARATAH_URL
                # hash will change if this row changes, include time since we split some rows
                # into two races
                race['hash'] = hashlib.sha1(str(row)+time[0]).hexdigest()
                
                races.append(race)
    return races



def ingest():
    """Return a list of dictionaries, one for each race"""

    try:
        webtext = urllib.request.urlopen(WARATAH_URL).read()
        return parse_web_text(webtext)
    except urllib.error.HTTPError as e:
        content = e.read()
        print("HTTP Error: ", content)
        return []
    except urllib.error.URLError as e:
        print("URLError: ", e)
        return []
        

if __name__ == '__main__':

    import pprint
    
    races = ingest()
    
    pprint.pprint(races)
    
    