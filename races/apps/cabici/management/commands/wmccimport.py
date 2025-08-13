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
Import data from the WMCC database CSV dumps

@author: steve
'''

import django.db.utils

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils.text import slugify

import csv
import os
import datetime
import random

from races.apps.cabici.usermodel import Rider, RaceResult, ClubGrade, Membership, UserRole, ClubRole, RaceStaff, PointScore
from races.apps.cabici.models import Club, Race, RaceCourse

CLUBMAP = {'ACT': 'ATTANSW',
 'ACTVCC': 'ArmidaleCC',
 'ADCC': 'ArmidaleCC',
 'ADF': 'AustralianDefenceCC',
 'ADF Cycling': 'AustralianDefenceCC',
 'ADF Nowra': 'AustralianDefenceCC',
 'ADFCC': 'AustralianDefenceCC',
 'Atomic Brooks': 'None',
 'Audax Australia': 'CentralCoastCC',
 'Aust Def Club': 'AustralianDefenceCC',
 'Australian Army Cycling Club': 'AustralianDefenceCC',
 'Australian Defence': 'AustralianDefenceCC',
 'Australian Defence CC': 'AustralianDefenceCC',
 'Australian Defence Force CC': 'AustralianDefenceCC',
 'BCRI': 'None',
 'BRAT': 'None',
 'BSCC': 'None',
 'Balmoral [Qld]': 'BalmoralCC',
 'Bike Barn': 'ParramattaCC',
 'CATS': 'CessnockCC',
 'CCCC': 'CentralCoastCC',
 'Canberra': 'CanberraCC',
 'Canberra CC': 'CanberraCC',
 'Caulfield': 'CaulfieldCC',
 'Clarence St': 'None',
 'Clarence St Cyclery Club': 'None',
 'Clarence St. Cyclery': 'None',
 'Clarence Street': 'None',
 'Coffs Harbour': 'CoffsHarbourCC',
 'Cootamundra': 'CootamundraCC',
 'Coutamundra CC': 'CootamundraCC',
 'DABC': 'DulwichHillBC',
 'DHBC': 'DulwichHillBC',
 'Daegu Korea': 'None',
 'Dubbo CC': 'DubboCC',
 'ESCC': 'EasternSuburbsCC',
 'East Sydney CC': 'EasternSuburbsCC',
 'Eurobodalla': 'EurobodallaCC',
 'Footscray': 'FootscrayCC',
 'Giant': 'GiantCCSydney',
 'Giant Cycling Club Sydney': 'GiantCCSydney',
 'Gold Coast': 'None',
 'Gold Coast Stars': 'None',
 'Gold Star': 'None',
 'HPRW': 'None',
 'Hamilton Pine Rivers Wheelers': 'None',
 'KDCC': 'DubboCC',
 'LACC': 'LidcombeAuburnCC',
 'Lagny Pontcarre Cyclisme': 'None',
 'Leppington': 'None',
 'MCC': 'MudgeeCC',
 'MCCC': 'None',
 'MFCC': 'None',
 'MTBA': 'None',
 'MVCC': 'None',
 'MVVCC': 'None',
 'MWCC': 'ManlyWarringahCC',
 'Manley ': 'ManlyWarringahCC',
 'Marybrough': 'None',
 'Melbourne Uni': 'CoffsHarbourCC',
 'Mudgee': 'MudgeeCC',
 'Murrarrie': 'ManlyWarringahCC',
 'Murwillumbah CC': 'MudgeeCC',
 'Muwillumbah': 'MudgeeCC',
 'NSCC': 'DubboCC',
 'NWSCC': 'DubboCC',
 'Nepean': 'NarBUG',
 'North Harbour': 'None',
 'Northcote CC': 'None',
 'Not Recorded': 'None',
 'P.E. Club': 'None',
 'PTC': 'PenrithCC',
 'RBCC': 'RandwickBotanyCC',
 'Ride It': 'None',
 'SCC': 'SydneyCC',
 'SSCC': 'SydneyCC',
 'SU Velo': 'SydneyUniVeloClub',
 'SUV': 'SydneyUniVeloClub',
 'SUVC': 'SydneyUniVeloClub',
 'SUVELO': 'SydneyUniVeloClub',
 'SUVelo': 'SydneyUniVeloClub',
 'South Sydney CC': 'SydneyCC',
 'St Kilda': 'None',
 'SuVelo': 'SydneyUniVeloClub',
 'Sunshine Coast': 'None',
 'Surrey Hills': 'None',
 'Suvelo': 'SydneyUniVeloClub',
 'Syd Uni': 'SydneyUniVeloClub',
 'Sydney Cycle Club': 'SydneyCC',
 'Sydney Uni': 'SydneyCC',
 'Sydney Uni Velo': 'SydneyUniVeloClub',
 'Sydney University': 'SydneyUniVeloClub',
 'Sydney Velo': 'SydneyUniVeloClub',
 'TVCC': 'None',
 'Tan van Aichel': 'None',
 'Townsville': 'None',
 'Tread teh Thunder': 'None',
 'Turramurra': 'ParramattaCC',
 'USA Club': 'None',
 'Velosophy': 'None',
 'Viking': 'None',
 'Waratah - left for Parramatta?': 'ParramattaCC',
 'West Sydney MTB': 'WesternSydneyCyclingNetwork',
 'Western Sydney Cycling Network': 'WesternSydneyCyclingNetwork',
 'Willesden CC (England)': 'None',
 'rbcc': 'RandwickBotanyCC'}


def import_races(csvdir, waratahs, usermap):

    # delete races from waratahs only
    Race.objects.filter(club=waratahs).delete()

    ps, created = PointScore.objects.get_or_create(club=waratahs, name="2016 Pointscore")

    # import races from events.csv
    with open(os.path.join(csvdir, 'events.csv'), 'rU') as fd:
        reader = csv.DictReader(fd)

        # remember the race identifiers
        racedict = dict()

        for row in reader:
            # csv fields
            # id,"dd","mm","yyyy","eventname","eventno","eventdate","starttime",
            # "venue","performancereport","mainpointscore","dutyofficer","dutyofficerother",
            # "commissaire","commissaireother","helpers","helpersother","sponsor"

            # model fields
            # title, date, time, club, status=published
            time = "06:30"
            location = RaceCourse.objects.find_location(row['venue'])

            race = Race(title=row['eventname'], date=row['eventdate'],
                        club=waratahs, starttime=row['starttime'],
                        signontime=time, location=location, status='p', licencereq='m.mw')
            race.save()

            if race.date.startswith("2016") and row['mainpointscore']:
                ps.races.add(race)

            racedict[row['eventno']] = race

            role_comm, created = ClubRole.objects.get_or_create(name="Commissaire")
            role_do, created = ClubRole.objects.get_or_create(name="Duty Officer")
            role_dh, created = ClubRole.objects.get_or_create(name="Duty Helper")
            # associate officials with the race
            if row['commissaire'] is not '' and int(row['commissaire']) in usermap:
                comm_rider = usermap[int(row['commissaire'])].rider
                comm = RaceStaff(race=race, role=role_comm, rider=comm_rider)
                comm.save()
            elif row['commissaire'] is not '':
                print("Commissaire not found", row['commissaire'])

            if row['dutyofficer'] is not '' and int(row['dutyofficer']) in usermap:
                do_rider = usermap[int(row['dutyofficer'])].rider
                do = RaceStaff(race=race, role=role_do, rider=do_rider)
                do.save()
            elif row['dutyofficer'] is not '':
                print("Duty Officer not found: '%s'" % row['dutyofficer'])

            for dh_id in row['helpers'].split(','):
                try:
                    if int(dh_id) in usermap:
                        dh_rider = usermap[int(dh_id)].rider
                        dh = RaceStaff(race=race, role=role_dh, rider=dh_rider)
                        dh.save()
                    else:
                        print("Duty Helper not found", dh_id)
                except:
                    pass

        print("Imported %d races" % len(racedict))
        print("POINTSCORE: ", ps.races.all().count(), "races")
        return racedict

def import_users(csvdir, waratahs):

    # delete riders except for officials and staff, other models will cascade
    deleted = User.objects.filter(rider__official__exact=False).filter(is_staff__exact=False).delete()
    print("DELETED: ", deleted)

    usermap = dict()
    # import riders from register.csv
    with open(os.path.join(csvdir, 'register.csv'), 'rU') as fd:
        reader = csv.DictReader(fd)

        usercount = 0
        for row in reader:

            username = Rider.objects.make_username(row['firstname'], row['lastname'], row['licenceno'])

            user, created = User.objects.get_or_create(username=username)

            if created:
                user.first_name = row['firstname']
                user.last_name = row['lastname']
                user.email = row['email']
                user.save()

            # add rider info
            if not hasattr(user, 'rider') and row['licenceno'] != "":
                user.rider = Rider()
                user.rider.licenceno = row['licenceno']
                if row['gender'] in ['M', 'F']:
                    user.rider.gender = row['gender']

                if row['club'] in CLUBMAP:
                    if CLUBMAP[row['club']] == 'None':
                        row['club'] = None
                    else:
                        row['club'] = CLUBMAP[row['club']]

                club = Club.objects.closest(row['club'])
                user.rider.club = club
                user.rider.streetaddress = row['streetaddress1']
                user.rider.suburb = row['suburbtown']
                if len(row['postcode']) == 4:
                    user.rider.postcode = row['postcode']
                user.rider.phone = row['phone']
                user.rider.emergencyname = row['emergencyname']
                user.rider.emergencyphone = row['emergencyphone']
                user.rider.emergencyrelationship = row['emergencyrelationship'][:19]

                try:
                    user.rider.dob = datetime.date(day=int(row['dobdd']), month=int(row['dobmm']), year=int(row['dobyyyy']))
                except:
                    pass

                user.rider.save()

                #print "Rider: ", user.rider

                # grade and state handicap
                grade = ClubGrade(club=waratahs, rider=user.rider, grade=row['grade'])
                grade.save()

                # membership history
                for year in range(1995,2017):
                    field = 'w'+str(year)[2:]
                    status = row[field].strip()
                    if status == 'Y':
                        memb = Membership(rider=user.rider, club=waratahs, year=year, category='race')
                        memb.save()

                # duty officer
                if row['dutyofficer']=='yes':
                    dutyofficer, created = ClubRole.objects.get_or_create(name="Duty Officer")
                    role = UserRole(user=user, club=waratahs, role=dutyofficer)
                    role.save()

            usermap[int(row['id'])] = user

            usercount += 1

        waratahs.create_duty_helpers()

        print("Imported %d riders" % usercount)
        return usermap

def import_roles(csvdir, waratahs):

    usermap = dict()
    # import riders from register.csv
    with open(os.path.join(csvdir, 'contacts.csv'), 'rU') as fd:
        reader = csv.DictReader(fd)

        for row in reader:
            users = User.objects.filter(email=row['email'])
            if users.count() > 1:
                print(users)
            user = users[0]

            if '/' in row['position']:
                roles = row['position'].split('/')
            else:
                roles = row['position'].split('and')

            for role in roles:
                role = role.strip()
                rolename, created = ClubRole.objects.get_or_create(name=role)
                userrole = UserRole(user=user, club=waratahs, role=rolename)
                userrole.save()

            # also make this user an officer in the club
            user.rider.official = True
            user.rider.save()

            print("Role: ", user, [r.role for r in user.userrole_set.all()])

    print("Imported roles")


def import_points(csvdir, waratahs, usermap, racedict):

    RaceResult.objects.all().delete()

    # import results from points.csv
    with open(os.path.join(csvdir, 'points.csv'), 'rU') as fd:
        reader = csv.DictReader(fd)

        for row in reader:

            if int(row['registerid']) not in usermap:
                #print "Unknown rider", row
                continue

            user = usermap[int(row['registerid'])]

            race = racedict[row['eventno']]

            # work out place from points - actually need to account for small grades (E, F)
            points = int(row['points'])
            if points == 2:
                place = None
            elif points > 0:
                place = 8-points

            try:
                number = int(row['shirtno'])
            except:
                number = None

            if number > 500 and race.date.startswith('2016'):
                # this is a placeholder for points for a duty helper
                # create a result in grade "Helper"
                number = number + random.randint(1,100)
                result = RaceResult(race=race, rider=user.rider, grade="Helper", number=number, place=None)
            else:

                # check that this shirtno isn't already used
                if number != None and RaceResult.objects.filter(race=race, grade=row['grade'], number=number).count() > 0:
                    # increment the number to avoid the clash
                    number = number + 200 + random.randint(1,100)

                result = RaceResult(race=race, rider=user.rider,
                                    usual_grade=row['registergrade'],
                                    grade=row['grade'], number=number, place=place)

            try:
                result.save()
            except django.db.utils.IntegrityError as e:
                # print "Duplicate result", e
                # print row
                # print race
                # print number
                # print RaceResult.objects.filter(race=race,  rider=user.rider)
                # print '---------------'
                pass

    # fix up races with small fields - points/place calculation is incorrect
    for race in Race.objects.all():
        race.fix_small_races()

    ps, created = PointScore.objects.get_or_create(club=waratahs, name="2016 Pointscore")
    ps.recalculate()


class Command(BaseCommand):


    def add_arguments(self, parser):
        parser.add_argument('directory', type=str)


    def handle(self, *args, **options):

        csvdir = options['directory']

        try:
            waratahs = Club.objects.get(slug='WaratahMastersCC')
        except:
            print("You need to create the WaratahMastersCC club first")
            exit()

        usermap = import_users(csvdir, waratahs)

        racedict = import_races(csvdir, waratahs, usermap)

        import_roles(csvdir, waratahs)

        import_points(csvdir, waratahs, usermap, racedict)
