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
        print(race)