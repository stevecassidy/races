from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.urls import reverse
from django.utils.text import slugify
from django.utils.functional import cached_property

import json
import datetime
import csv

from races.apps.cabici.models import Club, Race
from bs4 import BeautifulSoup


def save_rider(backend, user, response, *args, **kwargs):
    """Create a rider object for a user, part of the
    social authentication flow. Adds fields from the Strava
    auth response to the Rider object."""

    if backend.name == 'strava':
        try:
            rider = user.rider
        except ObjectDoesNotExist:
            rider = Rider(user=user)

        # set gender if we're given it by strava
        if response.get('sex') is not None:
            rider.gender = response.get('sex')
        rider.save()


STATE_CHOICES = (('ACT', 'Australian Capital Territory'),
                 ('NSW', 'New South Wales'),
                 ('NT', 'Northern Territory'),
                 ('QLD', 'Queensland'),
                 ('SA', 'South Australia'),
                 ('TAS', 'Tasmania'),
                 ('VIC', 'Victoria'),
                 ('WA', 'Western Australia'))


def parse_img_members(fd):
    """Parse the membership list downloaded from IMG Sports
    which is an HTML table with one row per member.
    Return an iterator over the rows, each row returned
    as a dictionary."""

    bs = BeautifulSoup(fd, "html.parser")
    # get header
    headers = []
    for cell in bs.table.tr.find_all('td'):
        headers.append(cell.string)

    first = True
    for row in bs.table.find_all('tr'):
        if first:
            first = False
            continue
        cells = row.find_all('td')
        d = dict()
        for i in range(len(cells)):
            if headers[i] is None:
                continue
            value = cells[i].string
            # turn date fields into dates
            if value is not None and ('Date' in headers[i] or headers[i] == "DOB"):
                value = datetime.datetime.strptime(value, "%d-%b-%Y").date()
            # capitalise names
            if value is not None and 'Name' in headers[i]:
                value = value.capitalize()
            d[headers[i]] = value
        yield d


IMG_MAP = {
    'Address1': ('rider', 'streetaddress'),
    'DOB': ('rider', 'dob'),
    'Email Address': ('user', 'email'),
    'Emergency Contact Number': ('rider', 'emergencyphone'),
    'Emergency Contact Person': ('rider', 'emergencyname'),
    'First Name': ('user', 'first_name'),
    'Last Name': ('user', 'last_name'),
    'Member Number': ('rider', 'licenceno'),
    'Postcode': ('rider', 'postcode'),
    'State': ('rider', 'state'),
    'Suburb': ('rider', 'suburb'),
    'Commissaire Level (e.g. 2 Road Track MTB)': ('rider', 'commissaire'),
    'Commissaire Accreditation Expiry Date': ('rider', 'commissaire_valid'),
}



class RiderManager(models.Manager):
    """Manager for riders"""

    def make_username(self, firstname, lastname, licenceno):
        """Generate a suitable username for a rider"""

        return slugify(firstname + lastname + licenceno)[:30]

    def find_user(self, email, licenceno):
        """Find an existing user with this email or licenceno
        return the user or None if not found"""

        # search by licenceno
        users = User.objects.filter(rider__licenceno__exact=licenceno)
        if len(users) == 1:
            return users[0]

        # search by email Address
        users = User.objects.filter(email__exact=email)
        if len(users) == 1:
            return users[0]
        else:
            return None

    def update_from_img_spreadsheet(self, club, rows):
        """Update the membership list for a club,
        return a list of updated riders"""

        cyclingnsw, created = Club.objects.get_or_create(name="CyclingNSW", slug="CNSW")
        updated = []
        added = []

        # get the current member list, check that all are in the spreadsheet
        today = datetime.date.today()
        currentmembers = list(User.objects.filter(rider__club__exact=club, rider__membership__date__gte=today).distinct())

        for row in rows:
           # print("ROW:", row['Email Address'], row['Member Number'], row['Financial Date'])

            # we will import old membership records if present to ensure database is complete
            # but we don't want any with no financial date (usually 3-race memberships)
            if row['Financial Date'] is None:
                continue

            # grab all values from row that are not None, map them
            # to the keys via IMG_MAP
            riderinfo = dict()
            for key in list(row.keys()):
                if key in IMG_MAP:
                    if row[key] is not None and row[key] != '':
                        riderinfo[IMG_MAP[key]] = row[key]
            # riderinfo is our updated information

            user = self.find_user(row['Email Address'], row['Member Number'])
            updating = False

            if user is not None:
                try:
                    user.rider
                except ObjectDoesNotExist:
                    user.rider = Rider()

                updating = True
            else:
                # new rider
                username = slugify(row['First Name'] + row['Last Name'] + row['Member Number'])[:30]

                if row['Email Address'] is None:
                    email = ''
                else:
                    email = row['Email Address']
                user = User(first_name=row['First Name'],
                            last_name=row['Last Name'],
                            email=email,
                            username=username)
                user.save()
                user.rider = Rider()

                added.append(user)

            userchanges = []
            # add data from spreadsheet only if current entry is empty
            for key in list(riderinfo.keys()):
                if key[0] == 'user':
                    if getattr(user, key[1]) == '':
                        setattr(user, key[1], riderinfo[key])
                        userchanges.append(key[1])
                else:
                    if getattr(user.rider, key[1]) in ['', None, '0', datetime.date(1970, 1, 1)]:
                        setattr(user.rider, key[1], riderinfo[key])
                        userchanges.append(key[1])

            # some special cases that need reformatting
            if user.rider.phone == '':
                user.rider.phone = row['Mobile'] or row['Direct'] or row['Private']
                userchanges.append('phone')
            if user.rider.streetaddress == '':
                user.rider.streetaddress = ' '.join([row['Address1'] or '', row['Address2'] or ''])
                userchanges.append('streetaddress')

            if user.rider.gender == '':
                user.rider.gender = row['Gender'][0]
                userchanges.append('gender')

            # update commissaire data

            if ('rider', 'commissaire') in riderinfo and riderinfo[('rider', 'commissaire')] != '0':
                user.rider.commissaire = riderinfo[('rider', 'commissaire')]
                userchanges.append('commissaire')
            if ('rider', 'commissaire_valid') in riderinfo:
                user.rider.commissaire_valid = riderinfo[('rider', 'commissaire_valid')]
                userchanges.append('commissaire_valid')

            user.rider.club = club

            user.save()
            user.rider.save()

            # membership category = Member Types, Financial Date
            memberdate = row['Financial Date']
            category = 'race'
            # Member Types: RACING Membership, RIDE Membership, NON-RIDING Membership
            if 'RACING' in row['Member Types']:
                category = 'race'
            elif 'RIDE' in row['Member Types']:
                category = 'ride'
            elif 'NON-RIDING' in row['Member Types']:
                category = 'non-riding'

            # update membership record
            if memberdate is not None:
                mm = Membership.objects.filter(rider=user.rider, club=club, date=memberdate)
                if len(mm) == 0:
                    m = Membership(rider=user.rider, club=club, date=memberdate, category=category)
                    m.save()
                    userchanges.append('membership')
                else:
                    # check the category?
                    m = mm[0]
                    if m.category != category:
                        m.category = category
                        userchanges.append('membership')
                        m.save()

                # remove this user from the currentmembers list
                if user in currentmembers:
                    currentmembers.remove(user)

            # u'NSW Road Handicap Data'
            if row['NSW Road Handicap Data'] is not None:
                stategrade = row['NSW Road Handicap Data']
                try:
                    grading = ClubGrade.objects.get(rider=user.rider, club=cyclingnsw)
                    if grading.grade != stategrade:
                        grading.grade = stategrade
                        userchanges.append('stategrade')
                except ObjectDoesNotExist:
                    grading = ClubGrade(rider=user.rider, club=cyclingnsw, grade=stategrade)
                    userchanges.append('stategrade')
                grading.save()

            if updating and userchanges != []:
                updated.append({'user': user, 'changes': userchanges})

                # u'NSW Track Handicap Data'

        # check for any left over members in the currentmembers list
        # we need to revoke the member record for these
        revoked = currentmembers
        for user in currentmembers:
            mm = user.rider.membership_set.filter(date__gte=today)
            for m in mm:
                m.delete()

        return {'added': added, 'updated': updated, 'revoked': revoked}

    def update_from_tidyhq_spreadsheet(self, club, csvfile):
        """Update the membership list for a club, from a spreadsheet
        downloaded from TidyHQ return a list of updated riders"""

        updated = []
        added = []

        # get the current member list, check that all are in the spreadsheet
        today = datetime.date.today()
        currentmembers = list(User.objects.filter(rider__club__exact=club, rider__membership__date__gte=today).distinct())

        for row in csv.DictReader(csvfile):

            if 'Subscription End Date' not in row or \
                    row['Subscription End Date'] is None or \
                    row['Membership Status'] != 'Active':
                continue

            # remove 'CA' from the licence number
            licenceno = row['ID'][2:]
            user = self.find_user(row['Email'], licenceno)
            updating = False

            if user is not None:
                try:
                    user.rider
                except ObjectDoesNotExist:
                    user.rider = Rider()

                updating = True
            else:
                # new rider
                username = slugify(row['Contact'] + licenceno)[:30]

                # just in case we have used this username before
                # it wasn't found above so can't be a complete record, so
                # just re-use it and update
                user, created = User.objects.get_or_create(username=username)

                if row['Email'] is None:
                    email = ''
                else:
                    email = row['Email']

                # try to guess first and last names
                first_name, last_name = row['Contact'].split(' ', 1)
                # but use the fields if they are present
                if 'First Name' in row:
                    first_name = row['First Name']
                if 'Last Name' in row:
                    first_name = row['Last Name']

                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.save()

                try:
                    user.rider
                except ObjectDoesNotExist:
                    user.rider = Rider()
                    user.rider.save()

                added.append(user)

            userchanges = []

            # look for some optional fields in the csv
            # Gender
            # Birthday
            # Phone
            if 'Gender ' in row and row['Gender '] != '':
                gender = row['Gender '][0]  # M/F
                if user.rider.gender != gender:
                    user.rider.gender = gender
                    userchanges.append('Gender')

            if 'Birthday ' in row and row['Birthday '] != '':
                try:
                    dob = datetime.date.fromisoformat(row['Birthday '])
                    if dob != user.rider.dob:
                        user.rider.dob = dob
                        userchanges.append('DOB')
                except ValueError:
                    pass

            if 'Phone ' in row:
                phone = row['Phone '].strip()
                if user.rider.phone != phone:
                    user.rider.phone = phone
                    userchanges.append('Phone')

            # membership category = Member Types, Financial Date
            memberdate = row['Subscription End Date']

            if 'Race' in row['Membership Level']:
                category = 'race'
            elif 'Ride' in row['Membership Level']:
                category = 'ride'
            elif 'Non Riding' in row['Membership Level']:
                category = 'non-riding'

            # update membership record
            if memberdate is not '':
                # dates are '1-Jan-19', convert to 2019-12-31
                memberdate = datetime.datetime.strptime(memberdate, '%d %b %Y').strftime("%Y-%m-%d")
                mm = Membership.objects.filter(rider=user.rider, club=club, date=memberdate)
                if len(mm) == 0:
                    m = Membership(rider=user.rider, club=club, date=memberdate, category=category)
                    m.save()
                    userchanges.append('Membership')
                else:
                    # check the category?
                    m = mm[0]
                    if m.category != category:
                        m.category = category
                        userchanges.append('Membership')
                        m.save()

                # remove this user from the currentmembers list
                if user in currentmembers:
                    currentmembers.remove(user)

            if userchanges:
                user.rider.save()

            if updating and userchanges != []:
                updated.append({'user': user, 'changes': userchanges})

        # check for any left over members in the currentmembers list
        # we need to revoke the member record for these
        revoked = currentmembers
        for user in currentmembers:
            mm = user.rider.membership_set.filter(date__gte=today)
            for m in mm:
                m.delete()

        return {'added': added, 'updated': updated, 'revoked': revoked}


GENDER_CHOICES = (("M", "Male"),
                  ("F", "Female"))


class Rider(models.Model):
    """Model for extra information associated with a club member (rider)
    """

    objects = RiderManager()

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    licenceno = models.CharField("Licence Number", max_length=20, blank=True, default='')
    gender = models.CharField("Gender", max_length=2, choices=GENDER_CHOICES, blank=True, default='M')
    dob = models.DateField("Date of Birth", default=datetime.date(1970, 1, 1), blank=True)
    streetaddress = models.CharField("Address", max_length=100, default='', blank=True)
    suburb = models.CharField("Suburb", max_length=100, default='', blank=True)
    state = models.CharField("State", choices=STATE_CHOICES, max_length=10, default='NSW', blank=True)
    postcode = models.CharField("Postcode", max_length=4, default='', blank=True)
    phone = models.CharField("Phone", max_length=50, default='', blank=True)

    commissaire = models.CharField("Commissaire Level", max_length=10, default='0', blank=True,
                                   help_text="0 if not a Commissaire, otherwise eg. 1, RT")
    commissaire_valid = models.DateField("Commissaire Valid To", null=True, blank=True)

    emergencyname = models.CharField("Emergency Contact Name", max_length=100, default='', blank=True)
    emergencyphone = models.CharField("Emergency Contact Phone", max_length=50, default='', blank=True)
    emergencyrelationship = models.CharField("Emergency Contact Relationship", max_length=20, default='', blank=True)

    official = models.BooleanField("Club Official", default=False,
                                   help_text="Officials can view and edit member details, schedule races, upload results")

    club = models.ForeignKey(Club, null=True, on_delete=models.CASCADE)

    class Meta:
        ordering = ['user__last_name', 'user__first_name']

    def get_absolute_url(self):

        return reverse('rider', kwargs={'pk': self.user.pk})

    def __str__(self):
        return self.user.first_name + " " + self.user.last_name

    @cached_property
    def current_membership(self):

        m = self.membership_set.all().order_by('-date')
        if m:
            return m[0]

    @property
    def member_category(self):
        """Return the category from the most recent membership year"""

        m = self.current_membership
        if m:
            return m.get_category_display()
        else:
            return ''

    @property
    def member_date(self):
        """Return the year from the most recent membership year"""

        m = self.current_membership
        if m:
            return m.date
        else:
            return ''

    @property
    def classification(self):
        """Return the racing classification for this rider based
        on their DOB"""

        # classes with upper bound + 1 for each group in order
        classes = (("Kidz", 7),
                   ("U9", 9),
                   ("U11", 11),
                   ("U13 Boys", 13),
                   ("U15 Men", 15),
                   ("U17 Men", 17),
                   ("U19 Men", 19),
                   ("U23 Men", 23),
                   ("Elite Men", 30),
                   ("M1", 35),
                   ("M2", 40),
                   ("M3", 45),
                   ("M4", 50),
                   ("M5", 55),
                   ("M6", 60),
                   ("M7", 65),
                   ("M8", 70),
                   ("M9", 75),
                   ("M10", 81),
                   ("M11", 110))

        age = datetime.datetime.now().year - self.dob.year

        for cat, cutoff in classes:
            if age < cutoff:
                if self.gender == "F":
                    if cat.startswith("M"):
                        cat = cat.replace("M", "W")
                    elif cat == "Elite Men":
                        cat = cat.replace("Men", "Women")
                    elif cat == "U23 Men":
                        cat = "Elite Women"
                    elif cat.startswith("U"):
                        cat = cat.replace("Men", "Women")
                        cat = cat.replace("Boys", "Girls")
                return cat

    @property
    def grades(self):
        """Return a dictionary of grades for
        different clubs for this rider, key is the
        club slug"""

        result = {}
        grades = self.clubgrade_set.all()
        for grade in grades:
            result[grade.club.slug] = grade.grade

        return result

    def performancereport(self, when=None):
        """Generate a rider performance report for all clubs
        if the when arg is provided it should be a date
        and the performance report is generated as if on
        that date. Otherwise it is generated as of today."""

        # note that this duplicates logic in Club.performancereport but for all
        # clubs, we use it in generating the rider details page

        # number of races
        # number of wins/places in last 12 months
        # wins in grade
        # places in grade

        info = dict()
        startdate = datetime.date.today() - datetime.timedelta(days=365)
        info['recent'] = self.raceresult_set.filter(place__lte=5, place__gt=0, race__date__gt=startdate)
        info['places'] = info['recent'].filter(place__lte=3, place__gt=0).count()
        info['wins'] = info['recent'].filter(place__exact=1).count()

        return info


MEMBERSHIP_CATEGORY_CHOICES = (('Ride', 'ride'), ('Race', 'race'), ('Non-riding', 'non-riding'))


class Membership(models.Model):
    """Membership of a club with a given expiry date"""

    rider = models.ForeignKey(Rider, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, null=True, on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True)
    category = models.CharField(max_length=10, choices=MEMBERSHIP_CATEGORY_CHOICES)

    class Meta:
        ordering = ['date', 'category']


class ClubRole(models.Model):
    """The name of a role that someone can hold in a club"""

    name = models.CharField("Name", max_length=100)

    def __str__(self):
        return self.name


class UserRole(models.Model):
    """A role held by a person in a club, eg. president, handicapper, duty officer
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    role = models.ForeignKey(ClubRole, on_delete=models.CASCADE)

    def __str__(self):
        return "Role: " + '::'.join((str(self.user), self.club.slug, self.role.name))


class RaceStaff(models.Model):
    """A person associated with a race in some role, eg. Commissaire, Duty Officer
    """

    rider = models.ForeignKey(Rider, on_delete=models.CASCADE)
    race = models.ForeignKey(Race, related_name='officials', on_delete=models.CASCADE)
    role = models.ForeignKey(ClubRole, on_delete=models.CASCADE)

    def __str__(self):
        return "%s: %s" % (self.role.name, self.rider.user)

    class Meta:
        # should only assign each person once to a role in a race
        unique_together = (('rider', 'race', 'role'),)


class ClubGrade(models.Model):
    """A rider will be assigned a grade by a club, different
    clubs might have different grading"""

    class Meta:
        ordering = ['rider', 'grade']

    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE)
    grade = models.CharField("Grade", max_length=10)

    def __str__(self):
        return " - ".join((self.grade, str(self.rider), str(self.club)))

    def save(self, *args, **kwargs):
        """A rider can only have one grade for each club"""

        cg = ClubGrade.objects.filter(rider=self.rider, club=self.club)
        if self in cg:
            cg = list(cg)
            cg.remove(self)
        if cg is not None and len(cg) > 0:
            raise ValidationError("A rider can only have one grade for each club")

        super(ClubGrade, self).save(*args, **kwargs)


class RaceResult(models.Model):
    """Model of a rider competing in a race"""

    class Meta:
        unique_together = (('race', 'grade', 'number'), ('race', 'rider'))
        ordering = ['race', 'grade', 'place', 'number']

    def __str__(self):
        return "%s - %s-%d/%s, %s" % (str(self.race), self.grade, self.number or 0, self.place or '-', str(self.rider))

    race = models.ForeignKey(Race, on_delete=models.CASCADE)
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE)

    grade = models.CharField("Grade", max_length=10)
    usual_grade = models.CharField("Usual Grade", max_length=10)
    number = models.IntegerField("Bib Number", blank=True, null=True)  # unique together with grade

    place = models.IntegerField("Place", blank=True, null=True,
                                help_text="Enter finishing position (eg. 1-5), leave blank for a result out of the placings.")
    dnf = models.BooleanField("DNF", default=False)

    def pointscores(self):
        """Return a list of ResultPoints from all PointScores this race is part of"""

        return self.resultpoints_set.all()

from django.core.validators import validate_comma_separated_integer_list

POINTSCORE_METHODS = (("WMCC", "WMCC"), ("LACC", "LACC"))


class PointScore(models.Model):
    """A pointscore is a series of races where points are accumulated"""

    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    points = models.CharField("Points for larger races", max_length=100, default="7,6,5,4,3", validators=[validate_comma_separated_integer_list])
    smallpoints = models.CharField("Points for small races", max_length=100, default="5,4", validators=[validate_comma_separated_integer_list])
    smallthreshold = models.IntegerField("Small Race Threshold", default=12)
    participation = models.IntegerField("Points for participation", default=2)
    races = models.ManyToManyField(Race, blank=True)
    method = models.CharField("Pointscore Method", default="WMCC", choices=POINTSCORE_METHODS, max_length=10)

    def __str__(self):
        return str(str(self.club) + " " + self.name)

    def score(self, result, numberriders):
        """Calculate points for this placing according
        to some rules defined by method
        """

        if self.method == "LACC":
            return self.score_lacc(result)
        else:
            return self.score_wmcc(result, numberriders)

    def score_wmcc(self, result, numberriders):
        """Calculate the points for this placing
        according to the Waratah CC pointscore rules

        Return a tuple: (points, reason)
        where reason is a string explaining the score
        """
        # TODO: we might want to generalise this if some other
        # club want's to run a different kind of pointscore

        points = [7, 6, 5, 4, 3]
        smallpoints = [5, 4]
        participation = 2

        # is the rider eligible for promotion or riding down a grade
        promote = result.race.club.promotion(result.rider, when=result.race.date)

        if not result.place:
            return participation, "Participation"
        elif promote:
            return participation, "Rider eligible for promotion"
        elif result.grade > result.usual_grade:
            return participation, "Riding below normal grade"
        elif numberriders < 6:
            # only 3 points to the winner
            if result.place == 1:
                return 3, "Placed 1 in small race < 6 riders"
            else:
                return participation, "Participation, small race < 6 riders"
        elif numberriders <= 12:
            if result.place - 1 < len(smallpoints):
                return smallpoints[result.place - 1], "Placed %s in race <= 12 riders" % result.place
            else:
                return participation, "Participation, race <= 12 riders"
        else:
            if result.place - 1 < len(points):
                return points[result.place - 1], "Placed %s in race" % result.place
            else:
                return participation, "Participation"

    def score_lacc(self, result):
        """Calculate the points for this placing
        according to the LACC pointscore rules

        Return a tuple: (points, reason)
        where reason is a string explaining the score
        """

        points = [int(x) for x in self.points.split(',')]

        if not result.place:
            return self.participation, "Participation"
        else:
            if result.place - 1 < len(points):
                return points[result.place - 1], "Placed %s in race" % result.place
            else:
                return self.participation, "Participation"

    def get_points(self):
        "Return a list of integers from the points field"

        if not hasattr(self, 'pointslist'):
            self.pointslist = [int(n.strip()) for n in self.points.split(',')]

        return self.pointslist

    def get_smallpoints(self):
        "Return a list of integers from the smallpoints field"

        if not hasattr(self, 'smallpointslist'):
            self.smallpointslist = [int(n.strip()) for n in self.smallpoints.split(',')]

        return self.smallpointslist

    def default_score(self, place, numberriders):
        """Return the points corresponding to this place in the race
        and this number of riders"""

        if place is None:
            return self.participation

        if numberriders < self.smallthreshold:
            if place - 1 < len(self.get_smallpoints()):
                return self.get_smallpoints()[place - 1]
            else:
                return self.participation

        else:
            if place - 1 < len(self.get_points()):
                return self.get_points()[place - 1]
            else:
                return self.participation

    def tally(self, result):
        """Add points for this result to the tally"""

        # check that this race is part of this pointscore
        if self.races.filter(pk=result.race.pk).count() == 0:
            return

        number_in_grade = RaceResult.objects.filter(race=result.race, grade=result.grade).count()
        points, reason = self.score(result, number_in_grade)

        tally, created = PointscoreTally.objects.get_or_create(rider=result.rider, pointscore=self)

        if result.grade == "Helper" and tally.eventcount > 0:
            # points is average points so far for this rider
            points = int(round(float(tally.points) / float(tally.eventcount)))
            reason = "Helper " + str(points)

        reason += " : " + str(result.race)

        tally.add(points, reason)

    def recalculate(self):
        """Recalculate all points from scratch"""

        PointscoreTally.objects.filter(pointscore=self).delete()

        for race in self.races.all().order_by('date'):
            for result in race.raceresult_set.all():
                self.tally(result)

    def tabulate(self):
        """Generate a queryset of point tallys in order"""

        return self.results.all()

    def audit(self, rider):
        """Generate an audit report for this rider on this pointscore"""

        try:
            tally = PointscoreTally.objects.get(pointscore=self, rider=rider)
            return tally.audit_trail()
        except:
            return []


class PointscoreTally(models.Model):
    """An entry in the pointscore table for a rider"""

    class Meta:
        ordering = ['-points', 'eventcount']

    rider = models.ForeignKey(Rider, on_delete=models.CASCADE)
    pointscore = models.ForeignKey(PointScore, related_name='results', on_delete=models.CASCADE)
    points = models.IntegerField(default=0)
    eventcount = models.IntegerField(default=0)
    audit = models.TextField(default='[]')

    def __str__(self):
        return str(self.rider) + " " + str(self.points)

    def _add_reason(self, points, reason):
        """Add a new reason to the audit trail"""

        reasons = self.audit_trail()

        reasons.append((points, reason))
        self.audit = json.dumps(reasons)
        self.save()

    def audit_trail(self):
        """Return a list of reasons justifying the
        points for this tally"""

        reasons = json.loads(self.audit)
        if reasons is None:
            reasons = []
        return reasons

    def add(self, points, reason):
        """Add points to the tally for a rider and record the reason"""

        # print "POINTS", points, reason
        self.points += points
        self._add_reason(points, reason)
        self.eventcount += 1
        self.save()
