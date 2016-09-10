from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.text import slugify

import datetime
from djangoyearlessdate.models import YearField

from races.apps.cabici.models import Club, Race
import csv
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
            if headers[i] == None:
                continue
            value = cells[i].string
            # turn date fields into dates
            if value != None and ('Date' in headers[i] or headers[i] == "DOB"):
                value = datetime.datetime.strptime(value, "%d-%b-%Y").date()
            # capitalise names
            if value != None and 'Name' in headers[i]:
                value = value.capitalize()
            d[headers[i]] = value
        yield d

IMG_MAP = {
     u'Address1': ('rider', 'streetaddress'),
     u'DOB': ('rider', 'dob'),
     u'Email Address': ('user', 'email'),
     u'Emergency Contact Number': ('rider', 'emergencyphone'),
     u'Emergency Contact Person': ('rider', 'emergencyname'),
     u'First Name': ('user', 'first_name'),
     u'Last Name': ('user', 'last_name'),
     u'Member Number': ('rider', 'licenceno'),
     u'Postcode': ('rider', 'postcode'),
     u'State': ('rider', 'state'),
     u'Suburb': ('rider', 'suburb'),
     u'Commissaire Level (e.g. 2 Road Track MTB)': ('rider', 'commissaire'),
     u'Commissaire Accreditation Expiry Date': ('rider', 'commissaire_valid'),
}


class RiderManager(models.Manager):
    """Manager for riders"""

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

    def update_from_spreadsheet(self, club, rows):
        """Update the membership list for a club,
        return a list of updated riders"""

        cyclingnsw, created = Club.objects.get_or_create(name="CyclingNSW", slug="CNSW")
        updated = []
        added = []

        # get the current member list for this year, check that all are in the spreadsheet
        thisyear = datetime.date.today().year
        currentmembers = list(User.objects.filter(rider__club__exact=club, rider__membership__year__exact=thisyear))

        for row in rows:

            #print "ROW:", row['Email Address'], row['Member Number'], row['Financial Date']

            if row['Financial Date'] == None or row['Financial Date'] < datetime.date.today():
                # don't import old membership records
                continue

            # grab all values from row that are not None, map them
            # to the keys via IMG_MAP
            riderinfo = dict()
            for key in row.keys():
                if key in IMG_MAP:
                    if row[key] != None and row[key] != '':
                        riderinfo[IMG_MAP[key]] = row[key]
            # riderinfo is our updated information

            user = self.find_user(row['Email Address'], row['Member Number'])
            updating = False

            if user != None:
                try:
                    user.rider
                except ObjectDoesNotExist:
                    user.rider = Rider()

                updating = True
            else:
                # new rider
                username = slugify(row['First Name']+row['Last Name']+row['Member Number'])[:30]
                if row['Email Address'] == None:
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
            for key in riderinfo.keys():
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

            user.rider.club = club

            user.save()
            user.rider.save()

            # membership category = Member Types, Financial Date
            memberdate = row['Financial Date']
            # Member Types: RACING Membership, RIDE Membership, NON-RIDING Membership
            if 'RACING' in row['Member Types']:
                category = 'race'
            elif 'RIDE' in row['Member Types']:
                category = 'ride'
            elif 'NON-RIDING' in row['Member Types']:
                category = 'non-riding'

            # update membership if it is for this year
            if memberdate is not None and memberdate > datetime.date.today():
                mm = Membership.objects.filter(rider=user.rider, club=club, year=memberdate.year)
                if len(mm) == 0:
                    m = Membership(rider=user.rider, club=club, year=memberdate.year, category=category)
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
            if row['NSW Road Handicap Data'] != None:
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
                updated.append(user)

            # u'NSW Track Handicap Data'

        # check for any left over members in the currentmembers list
        # we need to revoke the member record for these
        revoked = currentmembers
        for user in currentmembers:
            m = user.rider.membership_set.get(year=thisyear)
            m.delete()

        return {'added': added, 'updated': updated, 'revoked': revoked}


class Rider(models.Model):
    """Model for extra information associated with a club member (rider)
    minimal model with just enough information to support race results"""

    objects = RiderManager()

    user = models.OneToOneField(User)
    licenceno = models.CharField("Licence Number", max_length=20)
    gender = models.CharField("Gender", max_length=2, choices=(("M", "M"), ("F", "F")))
    dob = models.DateField("Date of Birth", default=datetime.date(1970, 1, 1))
    streetaddress = models.CharField("Address", max_length=100, default='')
    suburb = models.CharField("Suburb", max_length=100, default='')
    state = models.CharField("State", choices=STATE_CHOICES, max_length=10, default='NSW')
    postcode = models.CharField("Postcode", max_length=4, default='')
    phone = models.CharField("Phone", max_length=50, default='')

    commissaire = models.CharField("Commissaire Level", max_length=10, default='0',
                                   help_text="0 if not a Commissaire, otherwise eg. 1, RT")
    commissaire_valid = models.DateField("Commissaire Valid To", null=True, blank=True)

    emergencyname = models.CharField("Emergency Contact Name", max_length=100, default='')
    emergencyphone = models.CharField("Emergency Contact Phone", max_length=50, default='')
    emergencyrelationship =  models.CharField("Emergency Contact Relationship", max_length=20, default='')

    official = models.BooleanField("Club Official", default=False,
                                    help_text="Officials can view and edit member details, schedule races, upload results")

    club = models.ForeignKey(Club, null=True)

    def get_absolute_url(self):

        return reverse('rider', kwargs={'pk': self.user.pk})

    def __unicode__(self):
        return self.user.first_name + " " + self.user.last_name

    @property
    def member_category(self):
        """Return the category from the most recent membership year"""

        m = self.membership_set.all().order_by('-year')
        if m:
            return m[0].get_category_display()
        else:
            return ''

    @property
    def member_year(self):
        """Return the year from the most recent membership year"""

        m = self.membership_set.all().order_by('-year')
        if m:
            return m[0].year
        else:
            return ''

    def performancereport(self):
        """Generate a rider performance report"""

        # number of races
        # number of wins/places in last 12 months
        # wins in grade
        # places in grade

        info = dict()

        today = datetime.date.today()
        startdate = today - datetime.timedelta(days=365)
        info['recent'] = self.raceresult_set.filter(place__lt=5, race__date__gt=startdate)
        info['places'] = info['recent'].filter(place__gt=1).count()
        info['wins'] = info['recent'].filter(place__exact=1).count()

        return info

MEMBERSHIP_CATEGORY_CHOICES = (('Ride', 'ride'), ('Race', 'race'), ('Non-riding', 'non-riding'))

class Membership(models.Model):
    """Membership of a club in a given year"""

    rider = models.ForeignKey(Rider)
    club = models.ForeignKey(Club, null=True)
    year = YearField(null=True, blank=True)
    category = models.CharField(max_length=10, choices=MEMBERSHIP_CATEGORY_CHOICES)

class ClubRole(models.Model):
    """The name of a role that someone can hold in a club"""

    name = models.CharField("Name", max_length=100)

    def __unicode__(self):
        return self.name

class UserRole(models.Model):
    """A role held by a person in a club, eg. president, handicapper, duty officer
    """

    user = models.ForeignKey(User)
    club = models.ForeignKey(Club)
    role = models.ForeignKey(ClubRole)


class RaceStaff(models.Model):
    """A person associated with a race in some role, eg. Commissaire, Duty Officer
    """

    rider = models.ForeignKey(Rider)
    race = models.ForeignKey(Race, related_name='officials')
    role = models.ForeignKey(ClubRole)

    def __unicode__(self):
        return "%s: %s" % (self.role.name, self.rider.user)

class ClubGrade(models.Model):
    """A rider will be assigned a grade by a club, different
    clubs might have different grading"""

    class Meta:
        ordering = ['rider', 'grade']

    club = models.ForeignKey(Club)
    rider = models.ForeignKey(Rider)
    grade = models.CharField("Grade", max_length=10)

    def __unicode__(self):
        return " - ".join((self.grade, unicode(self.rider), unicode(self.club)))

    def save(self, *args, **kwargs):
        """A rider can only have one grade for each club"""

        cg = ClubGrade.objects.filter(rider=self.rider, club=self.club)
        if self in cg:
            cg = list(cg).remove(self)
        if cg is not None and len(cg) > 0:
            raise ValidationError("A rider can only have one grade for each club")

        super(ClubGrade, self).save(*args, **kwargs)




class RaceResult(models.Model):
    """Model of a rider competing in a race"""

    class Meta:
        unique_together = (('race', 'grade', 'number'), ('race', 'rider'))
        ordering = ['race', 'grade', 'place', 'number']

    def __unicode__(self):
        return "%s - %s-%d/%s, %s" % (str(self.race), self.grade, self.number or 0, self.place or '-', str(self.rider))

    race = models.ForeignKey(Race)
    rider = models.ForeignKey(Rider)

    grade = models.CharField("Grade", max_length=10)
    number = models.IntegerField("Bib Number", blank=True, null=True)  # unique together with grade

    place = models.IntegerField("Place", blank=True, null=True, help_text="Enter finishing position (eg. 1-5), leave blank for a result out of the placings.")
    dnf = models.BooleanField("DNF", default=False)

    def pointscores(self):
        """Return a list of ResultPoints from all PointScores this race is part of"""

        return self.resultpoints_set.all()



class PointScore(models.Model):
    """A pointscore is a series of races where points are accumulated"""

    club = models.ForeignKey(Club)
    name = models.CharField(max_length=100)
    points = models.CommaSeparatedIntegerField("Points for larger races", max_length=100, default="7,6,5,4,3")
    smallpoints = models.CommaSeparatedIntegerField("Points for small races", max_length=100, default="5,4")
    smallthreshold = models.IntegerField("Small Race Threshold", default=12)
    participation = models.IntegerField("Points for participation", default=2)
    races = models.ManyToManyField(Race, blank=True)

    def __unicode__(self):
        return unicode(unicode(self.club) + " " + self.name)

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

    def score(self, place, numberriders):
        """Return the points corresponding to this place in the race
        and this number of riders"""

        if place is None:
            return self.participation

        if numberriders < self.smallthreshold:
            if place-1 < len(self.get_smallpoints()):
                return self.get_smallpoints()[place-1]
            else:
                return self.participation

        else:
            if place-1 < len(self.get_points()):
                return self.get_points()[place-1]
            else:
                return self.participation


    def tally(self, result, reporton=None):
        """Add points for this result to the tally"""

        # check that this race is part of this pointscore
        if self.races.filter(pk=result.race.pk).count() == 0:
            return

        number_in_grade = RaceResult.objects.filter(race=result.race, grade=result.grade).count()
        points = self.score(result.place, number_in_grade)

        tally, created = PointscoreTally.objects.get_or_create(rider=result.rider, pointscore=self)

        if result.grade == "Helper" and tally.eventcount > 0:
            # points is average points so far for this rider
            points = int(round(float(tally.points)/float(tally.eventcount)))
            #print "Helper", result, "\t", points

        tally.add(points)

        if reporton != None and result.rider.id == reporton:
            print result.race, ",\t", points

    def recalculate(self, reporton=None):
        """Recalculate all points from scratch"""

        PointscoreTally.objects.filter(pointscore=self).delete()

        for race in self.races.all().order_by('date'):
            for result in race.raceresult_set.all():
                self.tally(result, reporton)

    def tabulate(self):
        """Generate a queryset of point tallys in order"""

        return self.results.all()


class PointscoreTally(models.Model):
    """An entry in the pointscore table for a rider"""

    class Meta:
        ordering = ['-points', 'eventcount']

    rider = models.ForeignKey(Rider)
    pointscore = models.ForeignKey(PointScore, related_name='results')
    points = models.IntegerField(default=0)
    eventcount = models.IntegerField(default=0)

    def __unicode__(self):
        return str(self.rider) + " " + str(self.points)

    def add(self, points):
        """Add points to the tally for a rider"""

        self.points += points
        self.eventcount += 1
        self.save()
