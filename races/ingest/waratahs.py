'''
Created on Apr 15, 2013

@author: steve
'''
WARATAH_URL = 'http://www.waratahmasters.com.au/eventsmenu.cfm'

import urllib2
from bs4 import BeautifulSoup
import datetime
import re


def ingest():
    """Return a list of dictionaries, one for each race"""

    webtext = urllib2.urlopen(WARATAH_URL).read()
    soup = BeautifulSoup(webtext)

    table = soup.find_all('table', class_='raceroster_table')[0]


    TIME_GRADED = re.compile(r'([0-9.]+)am ([AC]-[BF])')

    races = []

    for row in table.find_all('tr'):

        cells = row.find_all('td')
        if len(cells) == 4:
            dateinfo =  [c for c in cells[0].children]
            times = dateinfo[2].strip()

            date = datetime.datetime.strptime(dateinfo[0], "%d %b %Y")

            if times.find('All Grades') >= 0:
                times = [times.split()[0]]
            else:
                times = times.split(':')

            title = cells[1]('strong')[0].string

            for time in times:
                time = time.strip()
                match = TIME_GRADED.match(time)
                if match != None:
                    time = match.group(1)
                    # time is 9 or 7.45
                    if time == u'9':
                        time = '09:00'
                    elif time == u'7.45':
                        time = '07:45'
                    grades = match.group(2)
                    racetitle = title + " Grades " + grades
                else:
                    # time is 0800
                    if time == '0800':
                        time = '08:00'
                    racetitle = title

                race = {}
                race['date'] = date.date().isoformat()
                race['time'] = time
                race['title'] = str(racetitle)
                race['id'] = str(cells[1]('span')[0].string)
                race['location'] = str(cells[2].string)
                race['url'] = WARATAH_URL

                races.append(race)
    return races



if __name__ == '__main__':

    for race in ingest():
        print race