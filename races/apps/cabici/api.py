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

"""Serializers for the REST API"""
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers, generics, permissions, relations
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.pagination import PageNumberPagination
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import APIException

import os, json, time, datetime
from django.http import Http404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.conf import settings

from .models import Club, Race, RaceCourse
from .usermodel import Rider, PointScore, RaceResult, RaceStaff, ClubRole, UserRole, ClubGrade, Membership


class StandardResultsSetPagination(PageNumberPagination):
    """Pagination class for requests that return large numbers of results"""

    page_size = 200
    page_size_query_param = 'page_size'
    max_page_size = 1000


@api_view(('GET',))
@permission_classes((permissions.AllowAny,))
def api_root(request, format=None):
    return Response({
        'clubs': reverse('club-list', request=request, format=format),
        'races': reverse('race-list', request=request, format=format),
        'racecourses': reverse('racecourse-list', request=request, format=format),
        'riders': reverse('rider-list', request=request, format=format),
        'pointscores': reverse('pointscore-list', request=request, format=format),
        'raceresults': reverse('raceresult-list', request=request, format=format),
        })


class CustomAuthTokenSerializer(serializers.Serializer):
    """Provide a custom response to a request for an auth token
    uses email rather than username to authenticate and
    returns a slightly richer JSON response than the
    default"""

    email = serializers.CharField(label=_("Email"))
    password = serializers.CharField(
        label=_("Password"),
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:

            user_from_email = User.objects.get(email__iexact=email)
            if not user_from_email:
                msg = _("Email not valid")
                raise serializers.ValidationError(msg, code='authorization')

            username = user_from_email.username

            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)
            # The authenticate call simply returns None for is_active=False
            # users. (Assuming the default ModelBackend authentication
            # backend.)
            if not user:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = _('Must include "username" and "password".')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs


class CustomAuthToken(ObtainAuthToken):
    """Define a custom response to token authentication request
    Use email rather than username and return some additional user
    information"""

    serializer_class = CustomAuthTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'club': user.rider.club.slug,
            'official': user.rider.official
        })


# TODO: authentication for create/update/delete views
# ---------------Permissions-----------------

class ClubOfficialPermission(permissions.BasePermission):
    """Permission only for officials of a club"""

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.method in permissions.SAFE_METHODS:
            return True

        # anonymous user can't do anything unsafe
        if not request.user.is_authenticated:
            return False

        # superuser can do anything
        if request.user.is_superuser:
            return True

        # user should be an official of the club referenced in the view
        if not request.user.rider.official:
            return False

        return True

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.method in permissions.SAFE_METHODS:
            return True

        # anonymous user can't do anything unsafe
        if not request.user.is_authenticated:
            return False

        # superuser can do anything
        if request.user.is_superuser:
            return True

        # user should be an official of the club referenced in the view
        if not request.user.rider.official:
            return False

        # if they are an official then they can operate on their club
        # races or members
        if isinstance(obj, Race) or isinstance(obj, Rider):
            club = obj.club
        elif isinstance(obj, RaceResult):
            club = obj.race.club
        elif isinstance(obj, UserRole):
            club = obj.club
        else: 
            return False

        return request.user.rider.club == club

# ---------------Club------------------


class ClubSerializer(serializers.HyperlinkedModelSerializer):

    races = serializers.HyperlinkedRelatedField(many=True, queryset=Race.objects.all(), view_name='race-detail')
    url = relations.HyperlinkedIdentityField(lookup_field='slug', view_name='club-detail')

    class Meta:
        model = Club
        fields = ('url', 'name', 'slug', 'website', 'races')


class ClubBriefSerializer(serializers.ModelSerializer):

    class Meta:
        model = Club
        fields = ('name', 'id', 'slug', 'manage_members')


class ClubList(generics.ListCreateAPIView):
    queryset = Club.objects.all()
    serializer_class = ClubSerializer


class ClubDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Club.objects.all()
    serializer_class = ClubSerializer
    lookup_field = 'slug'

class UserRoleSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserRole
        fields = ('id', 'user', 'club', 'role')
    
    def to_representation(self, instance):
        result = super().to_representation(instance)
        result['role'] = instance.role.name
        result['club'] = instance.club.slug
        return result

    def to_internal_value(self, data):
        role, created = ClubRole.objects.get_or_create(name=data['role'])

        rider = Rider.objects.filter(pk=data['rider'])
        club = Club.objects.filter(slug=data['club'])

        errors = {}
        if rider.count() == 0:
            errors['rider'] = 'invalid rider id'
        if club.count() == 0:
            errors['club'] = 'invalid club id'
        if errors != {}:
            raise serializers.ValidationError(errors)

        return {'user': rider[0].user, 'club': club[0], 'role': role}

class UserRolesView(generics.ListCreateAPIView):
    
    serializer_class = UserRoleSerializer 

    def get_queryset(self):
        
        slug = self.request.resolver_match.kwargs['slug']
        return UserRole.objects.filter(club__slug__exact=slug)

@permission_classes((ClubOfficialPermission,))
class UserRoleDestroyView(generics.RetrieveDestroyAPIView):
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer


# ---------------RaceCourse------------------


class RaceCourseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = RaceCourse
        fields = '__all__'


class RaceCourseBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = RaceCourse
        fields = '__all__'


class RaceCourseList(generics.ListCreateAPIView):
    queryset = RaceCourse.objects.all()
    serializer_class = RaceCourseSerializer


class RaceCourseDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = RaceCourse.objects.all()
    serializer_class = RaceCourseSerializer

# ---------------Race------------------


class RaceOfficialField(serializers.Field):
    """Custom field to return a representation of officials at a race
    note: read only, to modify officials use racesstaff-detail view"""

    def to_representation(self, obj):

        result = dict()
        for role in obj.distinct():
            entry = {'id': role.rider.id, 'name': role.rider.user.first_name + " " + role.rider.user.last_name}
            if role.role.name not in result:
                result[role.role.name] = [entry]
            else:
                result[role.role.name].append(entry)

        return result

    def to_internal_value(self, data):

        print("TIV", data)

        return []


class RaceSerializer(serializers.ModelSerializer):
    # TODO: we want these fields to be expanded when we read the data
    # but we only want to specify the ID when we update/create
    club = ClubBriefSerializer(read_only=True)
    location = RaceCourseBriefSerializer(read_only=True)
    officials = RaceOfficialField(read_only=True)

    discipline = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    licencereq = serializers.SerializerMethodField()
    pointscore = serializers.SerializerMethodField()


    class Meta:
        model = Race
        fields = ('id', 'url', 'club', 'location', 'title', 'date', 'signontime', 'starttime', 'website', 'status', 'description', 'officials', 'discipline', 'category', 'licencereq', 'grading', 'pointscore')

    def get_discipline(self, obj):
        return {'key': obj.discipline, 'display': obj.get_discipline_display()}

    def get_category(self, obj):
        return {'key': obj.category, 'display': obj.get_category_display()}

    def get_licencereq(self, obj):
        return {'key': obj.licencereq, 'display': obj.get_licencereq_display()}

    def get_pointscore(self, obj):
        pointscore = obj.pointscore_set.all()
        if pointscore.count() > 0:
           return {'key': pointscore[0].id, 'display': str(pointscore[0])}
        else:
            return {'key': None, 'display': ''}


@permission_classes((ClubOfficialPermission,))
class RaceList(generics.ListCreateAPIView):
    serializer_class = RaceSerializer

    def get_queryset(self):

        clubslug = self.request.query_params.get('club', None)
        select = self.request.query_params.get('select', None)
        count = self.request.query_params.get('count', None)

        races = Race.objects.all()

        # if user is a club official, include draft races
        if getattr(self.request.user, 'rider', None) is not None and self.request.user.rider.official:
            pass
        else:
            # no draft or withdrawn races
            races = races.exclude(status__exact="d").exclude(status__exact="w")

        if clubslug is not None:
            races = races.filter(club__slug__exact=clubslug)

        if select == 'future':
            races = races.filter(date__gte=datetime.date.today())
        elif select == 'recent':
            races = races.filter(date__lte=datetime.date.today()).order_by('-date')
        elif select == 'raceday':
            today = datetime.date.today()
            future = today + datetime.timedelta(days=30)
            past = today - datetime.timedelta(days=30)
            races = races.filter(date__lte=future, date__gte=past).order_by('-date')
        elif select == 'results':
            races = races.filter(raceresult__rider__isnull=False).distinct().order_by('-date')

        # count needs to be an integer
        if count is not None:
            try:
                count = int(count)
                races = races[:count]
            except:
                pass

        return races


@permission_classes((ClubOfficialPermission,))
class RaceDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Race.objects.all()
    serializer_class = RaceSerializer

# ---------------RaceStaff------------------


class RaceStaffSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = RaceStaff
        fields = '__all__'

    role = serializers.SlugRelatedField(slug_field='name', queryset=ClubRole.objects.all())


class RaceStaffList(generics.ListCreateAPIView):
    queryset = RaceStaff.objects.all()
    serializer_class = RaceStaffSerializer


@permission_classes((ClubOfficialPermission,))
class RaceStaffDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = RaceStaff.objects.all()
    serializer_class = RaceStaffSerializer


# ---------------Rider------------------

class RiderSerializer(serializers.HyperlinkedModelSerializer):

    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    club = serializers.CharField(source="club.name", read_only=True)
    clubslug = serializers.CharField(source="club.slug", read_only=True)

    class Meta:
        model = Rider
        fields = ('id', 'first_name', 'last_name', 'club', 'clubslug', 'licenceno',
                  'classification',
                  'member_category',
                  'member_date',
                  'grades',
                  'gender', 'emergencyphone', 'emergencyname', 'updated' )


class RiderList(generics.ListCreateAPIView):
    # require authentication to access rider list API
    permission_classes = (IsAuthenticated, )
    queryset = Rider.objects.all()
    serializer_class = RiderSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):

        clubid = self.request.query_params.get('club', None)
        commissaire = self.request.query_params.get('commissaire', None)
        prefix = self.request.query_params.get('prefix', None)
        changed = self.request.query_params.get('changed', None)

        if clubid is not None:
            if commissaire is not None:
                riders = Rider.objects.filter(club__pk__exact=clubid, commissaire_valid__gt=datetime.date.today())
            else:
                riders = Rider.objects.filter(club__pk__exact=clubid)
        else:
            riders = Rider.objects.all()

        if prefix is not None:
            riders = riders.filter(user__last_name__istartswith=prefix)

        if changed:
            try:
                changed = datetime.datetime.fromtimestamp(int(changed), datetime.timezone.utc)
                riders = riders.filter(user__rider__updated__gt=changed)
            except ValueError:
                raise APIException("Bad timestamp format for changed argument")

        riders = riders.select_related('user', 'club')

        return riders.order_by('user__last_name')


@permission_classes((ClubOfficialPermission,))
class RiderDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Rider.objects.all()
    serializer_class = RiderSerializer


# ---------------PointScore------------------

class PointScoreBriefSerializer(serializers.HyperlinkedModelSerializer):

    club = ClubBriefSerializer(read_only=True)

    class Meta:
        model = PointScore
        fields = ('url', 'club', 'name')


class PointScoreList(generics.ListCreateAPIView):
    serializer_class = PointScoreBriefSerializer

    def get_queryset(self):
        """Allow filtering of queryset by a URL query
        parameter ?club=SLUG
        """

        clubslug = self.request.query_params.get('club', None)
        ps = PointScore.objects.all()

        if clubslug is not None:
            ps = ps.filter(club__slug__exact=clubslug)

        return ps


class PointScoreSerializer(serializers.HyperlinkedModelSerializer):

    results = serializers.SerializerMethodField('result_list')
    club = serializers.SerializerMethodField('club_name')

    def club_name(self, ps):
        return ps.club.name

    def result_list(self, ps):

        queryset = ps.tabulate()

        return [{'rider': " ".join((tally.rider.user.first_name, tally.rider.user.last_name)),
                'riderid': tally.rider.user.id,
                'club': tally.rider.club.slug if tally.rider.club else "Unknown",  # avoid crash if no club
                'grade': tally.pointscore.club.grade(tally.rider),
                'points': tally.points,
                'eventcount': tally.eventcount}
                for tally in queryset]

    class Meta:
        model = PointScore
        fields = ('name', 'club', 'results')


@permission_classes((ClubOfficialPermission,))
class PointScoreDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = PointScore.objects.all()
    serializer_class = PointScoreSerializer

# ---------------RaceResult------------------


class RaceResultSerializer(serializers.ModelSerializer):

    rider_name = serializers.CharField(source="rider", read_only=True)
    rider = serializers.SerializerMethodField('rider_name')
    riderid = serializers.SerializerMethodField('rider_id')
    club = serializers.SerializerMethodField('club_name')

    def club_name(self, result):
        if result.rider.club != None:
            return result.rider.club.name
        else:
            return "Unknown"

    def rider_name(self, result):
        return str(result.rider)

    def rider_id(self, result):
        return result.rider.id

    class Meta:
        model = RaceResult
        fields = '__all__'


class RaceResultList(generics.ListCreateAPIView):

    serializer_class = RaceResultSerializer

    def get_queryset(self):

        raceid = self.request.query_params.get('race', None)
        placed = self.request.query_params.get('placed', None)

        try:
            if raceid is not None:
                if placed is not None:
                    return RaceResult.objects.filter(race__pk__exact=raceid, place__gt=0).select_related('rider', 'rider__user')
                else:
                    return RaceResult.objects.filter(race__pk__exact=raceid).select_related('rider', 'rider__user')
            else:
                # should be all results but that would be too many
                # and we'd never actually want that so return nothing
                return RaceResult.objects.none()

        except ValueError:
            # given a non integer for raceid
            raise Http404("Invalid Race ID")

    def post(self, request, *args, **kwargs):
        """Handle post payload containing entries and new riders"""

        messages = []  # error messages

        data = request.data
        if 'race' in data:
            raceid = data['race']
        else:
            raise APIException("Invalid JSON for race results: require 'race'")

        try:
            race = Race.objects.get(id=raceid)
        except Race.DoesNotExist:
            raise APIException("Invalid Race ID in JSON upload")

        # stash the payload in a file for later analysis
        if settings.SAVE_RESULT_UPLOADS:
            if not os.path.exists(settings.SAVE_RESULT_UPLOADS_DIR):
                os.makedirs(settings.SAVE_RESULT_UPLOADS_DIR)
            filename = os.path.join(settings.SAVE_RESULT_UPLOADS_DIR, "{}-{}.json".format(race.id, time.time()))
            with open(filename, 'w') as fd:
                json.dump(data, fd, indent=2)

        ridermap = {}  # will hold a mapping between temporary and real ids for riders

        # handle new and updated riders
        for record in data.get('riders', []):
            # new rider id starts with "ID"
            if str(record['id']).startswith("ID"):
                # create a new rider record with these details
                username = Rider.objects.make_username(record['first_name'],
                                                       record['last_name'],
                                                       str(record['licenceno']))

                # just in case we know them already we use get_or_create
                user, created = User.objects.get_or_create(username=username)
                # add user details
                user.first_name = record['first_name']
                user.last_name = record['last_name']
                if 'email' in record:
                    user.email = record['email']
                user.save()

                try:
                    club = Club.objects.get(slug=record['clubslug'])
                except Club.DoesNotExist:
                    messages.append("Unknown club '%s' in rider record ignored" % (record['clubslug']))
                    club = Club.objects.get(slug='Unknown')

                if not created:
                    # guard against recreating the rider
                    rider = user.rider
                    if not rider.club == club:
                        rider.club = club
                        rider.save()
                else:
                    rider = Rider(licenceno=record['licenceno'], club=club, user=user)
                    rider.save()

                # membership
                if 'member_date' in record:
                    memberdate = datetime.date.fromisoformat(record['member_date'])

                    current = rider.current_membership

                    if not current:
                        m = Membership(rider=rider,
                                       club=rider.club,
                                       date=memberdate,
                                       category='race')
                        m.save()

                # grade
                if 'grade' in record:
                    cg = rider.clubgrade_set.filter(club=race.club)
                    if cg:
                        cg[0].grade = record['grade']
                        cg[0].save()
                    else:
                        ClubGrade(rider=rider, club=race.club, grade=record['grade']).save()

                if 'dob' in record:
                    # validate date format
                    try:
                        dob = datetime.date.fromisoformat(record['dob'])
                        rider.dob = dob
                    except ValueError:
                        messages.append("Bad DOB date format (%s) ignored" % record['dob'])

                if 'gender' in record and record['gender'] in ['M', 'F']:
                    rider.gender = record['gender']
                if 'phone' in record:
                    rider.phone = record['phone']

                rider.save()
                # now remember the id of this rider for the results entry later
                ridermap[record['id']] = rider.id
            else:
                # existing rider updated
                try:
                    rider = Rider.objects.get(id=record['id'])
                except Rider.DoesNotExist:
                    messages.append("Ignored new rider record with unknown temporary rider ID (%s)" % record)
                    continue

                # membership: club and date
                if 'clubslug' in record:
                    try:
                        record['club'] = Club.objects.get(slug=record['clubslug'])
                    except Club.DoesNotExist:
                        messages.append("Unknown club '%s' in rider record ignored" % (record['clubslug']))
                        record['club'] = Club.objects.get(slug='Unknown')

                # try to parse the member date string
                if 'member_date' in record:
                    try:
                        record['member_date'] = datetime.date.fromisoformat(record['member_date'])
                    except ValueError:
                        del record['member_date']

                m = rider.current_membership
                if m:
                    # update club if different
                    if 'club' in record and m.club != record['club']:
                        m.club = record['club']
                        m.save()
                        rider.club = record['club']
                        rider.save()

                    # update membership date if more recent
                    if 'member_date' in record:
                        if record['member_date'] > m.date:
                            # actually make a new membership
                            mnew = Membership(rider=rider, club=rider.club, category='race', date=record['member_date'])
                            mnew.save()
                            rider.save() # to trigger timestamp update
                elif 'club' in record and 'member_date' in record:
                    # no current membership so make one
                    m = Membership(rider=rider, club=record['club'], date=record['member_date'])
                    m.save()
                    rider.club = record['club']
                    rider.save()

                # licenceno
                if 'licenceno' in record and rider.licenceno != record['licenceno']:
                    rider.licenceno = record['licenceno']
                    rider.save()

                # name
                if 'first_name' in record and rider.user.first_name != record['first_name']:
                    rider.user.first_name = record['first_name']
                    rider.user.save()

                if 'last_name' in record and rider.user.last_name != record['last_name']:
                    rider.user.last_name = record['last_name']
                    rider.user.save()

        # handle entries, first remove any existing results for this race
        # then create one result for each entry
        entryfields = ['rider', 'grade']

        # count how many results we have already, if non zero we need to
        # recalculate all of the pointscore, if zero we only need to do this one
        previousresults = race.raceresult_set.all().count()

        race.raceresult_set.all().delete()
        for entry in data.get('entries', []):

            # ensure all required fields
            if not all([f in entry for f in entryfields]):
                raise APIException("Missing fields in JSON entry")

            if str(entry['rider']).startswith("ID"):
                if entry['rider'] in ridermap:
                    entry['rider'] = ridermap[entry['rider']]
                else:
                    grade = entry.get('grade','Unknown')
                    number = entry.get('number', 'Unknown')
                    messages.append("Ignored result record with unknown temporary rider ID (%s/%s)" % (grade, number))
                    continue

            try:
                rider = Rider.objects.get(id=entry['rider'])
            except Rider.DoesNotExist:
                grade = entry.get('grade','Unknown')
                number = entry.get('number', 'Unknown')
                messages.append("Rider (id=%s) not found for result (%s/%s)" % (entry['rider'], grade, number))
                continue

            if race.club.slug in rider.grades:
                usual_grade = rider.grades[race.club.slug]
            else:
                usual_grade = entry['grade']
                # create a rider grade
                ClubGrade(rider=rider, club=race.club, grade=usual_grade).save()
                rider.save() # to trigger timestamp update

            if not usual_grade == entry['grade'] and 'grade_change' in entry and entry['grade_change'] == 'y':
                # update rider grade
                grade = ClubGrade.objects.get(rider=rider, club=race.club)
                grade.grade = entry['grade']
                grade.save()
                rider.save() # to trigger timestamp update

            if 'dnf' in entry and entry['dnf']:
                dnf = True
            else:
                dnf = False

            result = RaceResult(rider=rider, race=race,
                                grade=entry['grade'],
                                number=entry.get('number', 999),
                                usual_grade=usual_grade,
                                place=entry.get('place', 0),
                                dnf=dnf)
            try:
                result.save()
            except IntegrityError:
                # since we deleted all entries for this race at the start of the loop
                # the most likely cause of this error is two upload requests running
                # at the same time, so we just ignore this error assuming that
                # the existing record is the same as this one
                pass

        # once results are in place, we tally the pointscores for this race
        if previousresults > 0:
            # need to recalculate pointscores since we've deleted results
            for ps in race.pointscore_set.all():
                ps.recalculate()
        else:
            # can just tally these results
            race.tally_pointscores()

        return Response({
                        'message': 'race results uploaded',
                        'errors': messages,
                        'ridermap': ridermap,
                        })


class RaceResultDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = RaceResult.objects.all()
    serializer_class = RaceResultSerializer
