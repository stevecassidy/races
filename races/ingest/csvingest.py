'''
Created on Apr 15, 2013

@author: steve
'''

import datetime
import re
import csv
import hashlib

def ingest(csvfile):
    """Return a list of dictionaries, one for each race"""

    races = []
    h = open(csvfile, 'rU')
    reader = csv.DictReader(h)

    for row in reader:

        race = {}
        date = datetime.datetime.strptime(row['Date'], "%d/%m/%y")
        race['date'] = date.date().isoformat()
        race['time'] = row['Time']
        race['title'] = row['Title']
        race['location'] = row['Location']
        race['url'] = row['url']
        race['club'] = row['Club']
        race['hash'] = hashlib.sha1(str(race)).hexdigest()
        
        races.append(race)
    return races



if __name__ == '__main__':

    for race in ingest():
        print race