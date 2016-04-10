'''
Import data from the WMCC database CSV dumps

@author: steve
'''

import django.db.utils

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
import csv
import os
import datetime

from races.apps.site.usermodel import Rider, RaceResult, ClubGrade
from races.apps.site.models import Club, Race, RaceCourse

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


def import_races(csvdir, waratahs):

    Race.objects.all().delete()

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
                        signontime=time, location=location, status='p')
            race.save()

            racedict[row['eventno']] = race

        print "Imported %d races" % len(racedict)
        return racedict

def import_users(csvdir, waratahs):

    User.objects.filter(is_staff__exact=False).delete()
    ClubGrade.objects.all().delete()

    stateclub, created = Club.objects.get_or_create(name='Cycling NSW', slug="CyclingNSW")

    usermap = dict()
    # import riders from register.csv
    with open(os.path.join(csvdir, 'register.csv'), 'rU') as fd:
        reader = csv.DictReader(fd)

        usercount = 0
        for row in reader:
            if row['email'] == '':
                username = row['firstname']+row['lastname']+row['id'].replace(' ', '')
            else:
                username = row['email']

            user, created = User.objects.get_or_create(email=row['email'], username=username)

            if created:
                user.first_name = row['firstname']
                user.last_name = row['lastname']
                user.save()

            # add rider info
            if not hasattr(user, 'rider') and row['licenceno'] != "":
                user.rider = Rider()
                user.rider.licenceno = row['licenceno']
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
                user.rider.postcode = row['postcode']
                user.rider.phone = row['phone']
                user.rider.emergencyname = row['emergencyname']
                user.rider.emergencyphone = row['emergencyphone']
                user.rider.emergencyrelationship = row['emergencyrelationship']

                try:
                    user.rider.dob = datetime.date(day=int(row['dobdd']), month=int(row['dobmm']), year=int(row['dobyyyy']))
                except:
                    pass

                user.rider.save()

                #print "Rider: ", user.rider

                # grade and state handicap
                grade = ClubGrade(club=waratahs, rider=user.rider, grade=row['grade'])
                grade.save()
                stategrade = ClubGrade(club=stateclub, rider=user.rider, grade=row['handicap'])
                stategrade.save()

                # membership history

            usermap[int(row['id'])] = user

            usercount += 1

        print "Imported %d riders" % usercount
        return usermap

def import_points(csvdir, waratahs, usermap, racedict):

    RaceResult.objects.all().delete()

    # import results from points.csv
    with open(os.path.join(csvdir, 'points.csv'), 'rU') as fd:
        reader = csv.DictReader(fd)

        for row in reader:

            if int(row['registerid']) not in usermap:
                print "Unknown rider", row
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

            result = RaceResult(race=race, rider=user.rider, grade=row['grade'], number=number, place=place)

            try:
                result.save()
            except django.db.utils.IntegrityError:
                print "Duplicate result"
                print row, race, number
                print RaceResult.objects.filter(race=race, grade=row['grade'], number=number)

    if False:
        # fix up races with small fields - points/place calculation is incorrect
        for race in Race.objects.all():
            for grade in ['A', 'B', 'C', 'D', 'E', 'F']:
                if RaceResult.objects.filter(race=race, grade=grade, place__isnull=False).count() < 5:
                    # subtract 2 from the places
                    for result in RaceResult.objects.filter(race=race, grade=grade, place__isnull=False):
                        print "Fixing result", result.place
                        result.place -= 2
                        result.save()


class Command(BaseCommand):


    def add_arguments(self, parser):
        parser.add_argument('directory', type=str)


    def handle(self, *args, **options):

        csvdir = options['directory']

        try:
            waratahs = Club.objects.get(slug='WaratahMastersCC')
        except:
            print "You need to create the WMCC club first"
            exit()

        racedict = import_races(csvdir, waratahs)

        usermap = import_users(csvdir, waratahs)

        import_points(csvdir, waratahs, usermap, racedict)
